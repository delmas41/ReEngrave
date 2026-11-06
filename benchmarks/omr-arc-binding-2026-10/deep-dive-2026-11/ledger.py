"""FATE LEDGER (measure only). Every arc on the sample pages, ink to file, the PAGE CURVE as its identity.

    python3 ledger.py ARCS.json MUSICXML [--out ledger.json]

Identity: a curve is one `Q.SYSTEM_ARC` row (its `pieces` are detector boxes); a detector box with no curve row is its own identity.
A curve whose every piece ADJUDICATE refused as not-an-arc is "not_an_arc" (a staff line / barline: not an arc at all). For the rest the
first rule that lost it is read down the pipeline in order:

    S  gather: no curve traced for the box (SYSTEM_ARC abstained)       [counted; the box still goes on]
    A  adjudicate_arc_is_not_an_arc   (every piece refused)
    K  adjudicate_arc_kind            (abstained: arc_ends_unread, same_pitch_accidental_unread, stack_slur...) + page_binding.why
    P  adjudicate_tie_pair            (a decided tie that paired nothing)  + its reason
    X  export                         (decided and paired but not in the file: tie pitch contradiction, ends in 2 voices, not in file, fewer than 2 notes)

WRITTEN is judged from the file (written.py): a tie by its (start, stop) heads; a slur by any written slur on the curve's owner staff whose
two ends sit within WINDOW_SP of the curve's two ends ('written'), whose ends miss them ('wrong_note'), or two slurs that split the curve
('two_arcs': neither spans both ends, each lies inside the curve's x extent). The kind of the written arc vs. the detector class / the
curve's pitch rule gives 'wrong_kind' where the two disagree on a curve both read. These are MEASURES AGAINST OUR OWN FILE, not truth:
truth is Sean's hand arcs (Brahms p0, handscore.py) and his tiles.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Tuple

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import written as W      # noqa: E402

WINDOW_SP = 3.0


def page_of(key: str) -> Optional[int]:
    try:
        return int(key.split("/")[1])
    except Exception:
        return None


def staff_of(key: str) -> str:
    return "/".join(key.split("/")[1:4])        # p/sys/staff


def load(path):
    return json.loads(pathlib.Path(path).read_text())


def build(dump: dict, xml_text: str) -> Dict[str, Any]:
    wr = W.parse(xml_text)
    cp = set(dump["pages"])
    boxes = {o["subject"]: o for o in dump["arc_box"]}
    curve_of: Dict[str, str] = {}
    curves: Dict[str, dict] = {}
    for o in dump["system_arc"]:
        d = o["detail"]
        for p in d.get("pieces") or ():
            curve_of[p] = o["subject"]
        curves[o["subject"]] = o
    ver: Dict[str, Dict[str, dict]] = collections.defaultdict(dict)
    for v in dump["verdicts"]:
        ver[v["quantity"]][v["subject"]] = v
    heads = {h["subject"]: h for h in dump["heads"]}
    # groups: curve id -> piece keys; uncurved boxes alone
    groups: Dict[str, List[str]] = collections.OrderedDict()
    for k in boxes:
        groups.setdefault(curve_of.get(k, k), []).append(k)
    # ⚠️ AN OVER-JOINED CURVE IS NOT ONE ARC. `join_traces` also joins arcs that MEET end to start at a note (a chain of slurs/ties); the binder then
    # refuses the curve (`joined_not_at_a_barline`) and the old per-box path decides each piece. Its pieces are separate arcs: they are separate rows
    # here (the curve row is kept as `overjoined_from`), or a 9-piece chain would count as one arc and hide eight.
    split: Dict[str, List[str]] = collections.OrderedDict()
    for gid, pcs in groups.items():
        why = None
        for p in pcs:
            kv = ver["arc_kind"].get(p)
            pb_ = ((kv or {}).get("detail") or {}).get("page_binding") or {}
            if pb_.get("why") == "joined_not_at_a_barline":
                why = pb_["why"]
                break
        if why and len(pcs) > 1:
            for p in pcs:
                split[p] = [p]
        else:
            split[gid] = pcs
    overjoined = {p for gid, pcs in groups.items() for p in pcs if gid not in split}
    groups = split
    sp_by_page: Dict[int, float] = {}
    out = []
    # written arcs in the counted pages
    w_ties = [(a, b) for a, b in wr["ties"] if page_of(a) in cp]
    w_slurs = [(a, b) for a, b in wr["slurs"] if page_of(a) in cp]

    def hx(k):
        h = heads.get(k)
        if not h or not h["box"]:
            return None
        b = h["box"]
        return (b[0] + b[2]) / 2.0

    slur_by_staff: Dict[str, List[Tuple[str, str]]] = collections.defaultdict(list)
    for a, b in w_slurs:
        slur_by_staff[staff_of(a)].append((a, b))
    tie_set = set(w_ties)
    used_slur = set()
    refusal_of: Dict[str, List[str]] = collections.defaultdict(list)
    for sbj, rsn in dump.get("refusals") or ():
        refusal_of[sbj].append(rsn)
    notes = wr["notes"]
    # a <slur> hangs off the chord's REPRESENTATIVE note (export: `voicing`), not the member the binder named: compare slurs by chord representative
    rep: Dict[str, str] = {}
    first_of: Dict[Any, str] = {}
    for rg_, nt in notes.items():
        rep[rg_] = first_of.setdefault((nt.get("part"), nt.get("grp")), rg_)
    nrm = lambda pr: (rep.get(pr[0], pr[0]), rep.get(pr[1], pr[1]))      # noqa: E731
    w_slur_set = {nrm(p_) for p_ in w_slurs}

    def xwhy(pr, kind):
        """Why a decided pair (start, stop) is not a written arc: the heads, not the arc, when a head was never written."""
        a, b = pr
        miss = [(e, k) for e, k in (("start", a), ("stop", b)) if k not in notes]
        if miss:
            return "%s_head_not_written(%s)" % ("+".join(e for e, _ in miss), "/".join(sorted({r for _, k in miss for r in refusal_of.get(k, ["no_refusal_logged"])})))
        na, nb = notes[a], notes[b]
        if na["voice"] != nb["voice"] or na.get("part") != nb.get("part"):
            return "ends_in_two_voices"
        if na.get("grp") == nb.get("grp"):
            return "ends_in_one_chord"
        if kind == "tie" and na["pitch"] != nb["pitch"]:
            return "tie_pitch_contradiction"
        return "both_heads_in_file_arc_not_marked"
    for gid, pieces in groups.items():
        c = curves.get(gid) if gid not in boxes or gid in curves else None
        if pieces[0] in overjoined:
            c = None            # a piece of an over-joined chain: its own box extent, no curve row
        d = (c or {}).get("detail") or {}
        sp = float(d.get("space_page_px") or 15.75)
        first = boxes[pieces[0]]
        pg = page_of(pieces[0])
        rec = dict(curve=gid, pieces=pieces, page=pg, has_curve=c is not None, n_pieces=len(pieces), overjoined=pieces[0] in overjoined,
                   classes=[boxes[p]["value"] for p in pieces],
                   x_left=d.get("x_left_page"), x_right=d.get("x_right_page"), sp=sp,
                   cells=d.get("cells"), cut=d.get("cut_at_barline"), shape=(c or {}).get("value"),
                   y_left=d.get("y_left_page"), y_right=d.get("y_right_page"), staff=staff_of(pieces[0]),
                   stroke_left=d.get("stroke_left_page"), stroke_right=d.get("stroke_right_page"),
                   beyond=d.get("beyond_boxes_spaces"), page_strokes=d.get("page_strokes"),
                   box=[min(boxes[p]["detail"]["bbox_page_px"][0] for p in pieces), min(boxes[p]["detail"]["bbox_page_px"][1] for p in pieces),
                        max(boxes[p]["detail"]["bbox_page_px"][2] for p in pieces), max(boxes[p]["detail"]["bbox_page_px"][3] for p in pieces)],
                   owner=((ver["arc_owner"].get(pieces[0]) or {}).get("value")))
        # A: refused by every piece
        refused = [ver["arc_is_not_an_arc"].get(p) for p in pieces]
        ref_reasons = [r["reason"] for r in refused if r and r["outcome"] == "decided" and r["value"] is True]
        if len(ref_reasons) == len(pieces):
            rec.update(fate="not_an_arc", lost_at="A", lost_rule="not_an_arc:" + ref_reasons[0])
            out.append(rec)
            continue
        live = [p for p in pieces if p not in {q for q, r in zip(pieces, refused) if r and r["outcome"] == "decided" and r["value"] is True}]
        kinds = [ver["arc_kind"].get(p) for p in live]
        decided = [k for k in kinds if k and k["outcome"] == "decided"]
        dkinds = {k["value"] for k in decided}
        rec["kind_values"] = sorted(dkinds)
        # binding evidence from any live piece
        pb = None
        for k in decided + [k for k in kinds if k]:
            pbk = ((k.get("detail") or {}).get("page_binding"))
            if pbk:
                pb = pbk
                break
        rec["binding"] = pb
        if pb:
            rec["bound_start"], rec["bound_stop"] = pb.get("start"), pb.get("stop")
        if not decided:
            why = (pb or {}).get("why")
            reasons = sorted({k["reason"] for k in kinds if k})
            rec.update(fate="dropped", lost_at="K", lost_rule="arc_kind:" + "/".join(reasons) + (("(%s)" % why) if why else ""))
            out.append(rec)
            continue
        kind = "tie" if "tie" in dkinds else "slur"
        rec["kind"] = kind
        # which end heads are expected
        pairs = [ver["tie_pair"].get(p) for p in live]
        dpairs = [x for x in pairs if x and x["outcome"] == "decided" and isinstance(x["value"], dict)]
        rec["tie_pair_reason"] = sorted({x["reason"] for x in pairs if x})
        if kind == "tie":
            if not dpairs:
                rec.update(fate="dropped", lost_at="P", lost_rule="tie_pair:" + "/".join(sorted({x["reason"] for x in pairs if x})))
                out.append(rec)
                continue
            pr = (dpairs[0]["value"]["start"], dpairs[0]["value"]["stop"])
            rec["pair"] = pr
            if pr in tie_set:
                rec["fate"] = "written"
            else:
                # written as a slur on the same two heads? or tie to other heads?
                as_slur = nrm(pr) in w_slur_set
                rec.update(fate="written_as_slur" if as_slur else "dropped", lost_at=None if as_slur else "X",
                           lost_rule=None if as_slur else "export:tie_not_in_file:" + xwhy(pr, "tie"))
            out.append(rec)
            continue
        # slur
        if pb and pb.get("kind") == "slur" and pb.get("start") and pb.get("stop"):
            pr = (pb["start"], pb["stop"])
            rec["pair"] = pr
            if nrm(pr) in w_slur_set or pr in set(w_slurs):
                rec["fate"] = "written"
                used_slur.add(pr)
            elif pr in tie_set:
                rec["fate"] = "written_as_tie"
            else:
                rec.update(fate="dropped", lost_at="X", lost_rule="export:slur_bound_not_in_file:" + xwhy(pr, "slur"))
            out.append(rec)
            continue
        # box-path slur: judge by the written slurs on the staff within the curve's extent
        xl, xr = d.get("x_left_page"), d.get("x_right_page")
        if xl is None:
            bb = [boxes[p]["detail"]["bbox_page_px"] for p in live]
            xl, xr = min(b[0] for b in bb), max(b[2] for b in bb)
        own = ver["arc_owner"].get(live[0])
        home = (own or {}).get("value") if own and own.get("outcome") == "decided" else None
        cand = []
        for st_key in {staff_of(live[0]), staff_of(home) if home else staff_of(live[0])}:
            cand += slur_by_staff.get(st_key, [])
        inside, spanning, ends_ok = [], [], []
        for a, b in cand:
            xa, xb = hx(a), hx(b)
            if xa is None or xb is None:
                continue
            if xb < xl - WINDOW_SP * sp or xa > xr + WINDOW_SP * sp:
                continue
            both = abs(xa - xl) <= WINDOW_SP * sp and abs(xb - xr) <= WINDOW_SP * sp
            if both:
                ends_ok.append((a, b))
            elif xa >= xl - WINDOW_SP * sp and xb <= xr + WINDOW_SP * sp:
                inside.append((a, b))
            else:
                spanning.append((a, b))
        if ends_ok:
            rec["fate"] = "written"
            rec["pair"] = ends_ok[0]
        elif len(inside) >= 2:
            rec["fate"] = "two_arcs"
            rec["pair"] = inside
        elif inside:
            rec["fate"] = "wrong_note"
            rec["pair"] = inside[0]
        elif spanning:
            rec["fate"] = "wrong_note"
            rec["pair"] = spanning[0]
        else:
            rec.update(fate="dropped", lost_at="X", lost_rule="export:arc_binds_fewer_than_two_notes_or_not_in_file")
        out.append(rec)
    return {"rows": out, "written": {"ties": len(w_ties), "slurs": len(w_slurs)}, "report_arc": dump.get("report_arc")}


def summarize(res: dict, pages: List[int]) -> str:
    rows = res["rows"]
    c = collections.Counter(r["fate"] for r in rows)
    npg = max(1, len(pages))
    L = ["curves %d (%.1f/page); boxes %d" % (len(rows), len(rows) / npg, sum(r["n_pieces"] for r in rows))]
    real = [r for r in rows if r["fate"] != "not_an_arc"]
    L.append("not_an_arc (staff lines/barlines/key slot) %d; real arc curves %d (%.1f/page)" % (c["not_an_arc"], len(real), len(real) / npg))
    for f in ("written", "written_as_slur", "written_as_tie", "wrong_note", "two_arcs", "dropped"):
        L.append("  %-16s %4d  %.1f/page" % (f, c[f], c[f] / npg))
    lost = collections.Counter((r["lost_at"], r["lost_rule"]) for r in rows if r.get("lost_at") and r["fate"] == "dropped")
    L.append("FIRST RULE THAT LOST A DROPPED CURVE:")
    for (st, rule), n in lost.most_common():
        L.append("  %s %-70s %4d  %.1f/page" % (st, rule, n, n / npg))
    return "\n".join(L)


if __name__ == "__main__":
    dump = load(sys.argv[1])
    xml = pathlib.Path(sys.argv[2]).read_text()
    res = build(dump, xml)
    print(summarize(res, dump["pages"]))
    if "--out" in sys.argv:
        pathlib.Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(res, default=str))
