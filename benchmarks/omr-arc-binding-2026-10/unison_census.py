"""ROADMAP 2.252 r3 -- ties at UNISONS: census and per-end trace (STAGED).

A unison = a head whose `Q.HEAD_STEM` reads `unison_two_voices` (one head, a stem each way, 2.175). Its TIE-END SLOTS
are (side above/below) x (direction before/after): above = the up-stem voice, below = the down-stem voice (Sean
2026-11-02, r2 tile 4; page-facts: an arc is OVER its notes, 2.75 arc side). A slot is FOUND where an arc box of the
same staff (this bar or the next/previous) has an end within 2.5 spaces of the head in x and lies wholly on one side
of the head centre in y within 4 spaces. Each found slot is traced to the stage that kept it out of the file.

    python3 benchmarks/omr-arc-binding-2026-10/unison_census.py RECORD.json --json OUT.json

Run with the arm's flags in the environment. Prints a line per slot and a count by cause. A slot is MY reading of
where an arc meets a head (geometry), not Sean's: it says where to look, never what is right.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as E          # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

ARC_CLASSES = ("tie", "slur")


def _parts(key: str):
    p = str(key).split("/")
    return tuple(int(x) for x in p[1:])


def written_by_glyph(xml: str):
    """glyph -> every <note rg=...> written for it: voice, stem, tie types."""
    out = collections.defaultdict(list)
    for n in ET.fromstring(xml).iter("note"):
        rg = n.get("rg")
        if rg:
            out[rg].append(dict(voice=n.findtext("voice"), stem=n.findtext("stem"),
                                tie=[t.get("type") for t in n.findall("tie")],
                                slur=[s.get("type") for s in n.iter("slur")], type=n.findtext("type")))
    return out


def _standing(rec, q):
    return {v["subject"]: v for v in rec.verdicts_of(q) if rec.verdict(q, v["subject"]) is v}


def census(result, xml, sp=15.75):
    rec = E.Record(result)
    wr = written_by_glyph(xml)
    head_stem = _standing(rec, "head_stem")
    unison = _standing(rec, "unison_voices")
    kinds = _standing(rec, "arc_kind")
    tiep = _standing(rec, "tie_pair")
    notarc = _standing(rec, "arc_is_not_an_arc")
    sys_abst = {a["subject"]: a for a in rec.abstentions if a.get("quantity") == "system_arc"}
    sys_obs = {}
    for o in rec.observations:
        if o["quantity"] == "system_arc":
            for p in (o.get("detail") or {}).get("pieces") or [o["subject"]]:
                sys_obs[p] = o
    boxes = {}
    for o in rec.observations:
        if o["quantity"] == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                boxes[o["subject"]] = (str((o.get("value") or [None])[0]), bp)
    arcs_by_staff = collections.defaultdict(list)
    for g, (cls, bp) in boxes.items():
        if cls in ARC_CLASSES:
            arcs_by_staff[_parts(g)[:3]].append(g)
    heads = sorted(g for g, v in head_stem.items() if str(v.get("reason")) == "unison_two_voices")
    slots = []
    used_one = {}
    for h in heads:
        cls, hb = boxes.get(h, (None, None))
        if hb is None:
            continue
        hyc = (hb[1] + hb[3]) / 2.0
        cell = _parts(h)[3]
        found = collections.defaultdict(list)
        for a in arcs_by_staff[_parts(h)[:3]]:
            if abs(_parts(a)[3] - cell) > 1:
                continue
            _c, ab = boxes[a]
            side = "above" if ab[3] <= hyc + 0.3 * sp else ("below" if ab[1] >= hyc - 0.3 * sp else None)
            if side is None or min(abs(ab[1] - hyc), abs(ab[3] - hyc)) > 4 * sp:
                continue
            if abs(ab[0] - hb[2]) <= 2.5 * sp or (ab[0] >= hb[0] - 0.5 * sp and ab[0] <= hb[2] + 2.5 * sp):
                found[(side, "after")].append(a)
            elif abs(ab[2] - hb[0]) <= 2.5 * sp or (ab[2] <= hb[2] + 0.5 * sp and ab[2] >= hb[0] - 2.5 * sp):
                found[(side, "before")].append(a)
        notes = wr.get(h, [])
        up = notes[:1] if len(notes) == 2 else []          # 2.175 writes the UP voice first, its twin (DOWN) after
        down = notes[1:2] if len(notes) == 2 else []
        for (side, dirn), arcs in sorted(found.items()):
            want = "start" if dirn == "after" else "stop"
            voice_notes = (up if side == "above" else down) or ([] if len(notes) > 1 else notes)
            other_notes = (down if side == "above" else up)
            on_voice = any(want in n["tie"] for n in voice_notes)
            on_other = any(want in n["tie"] for n in other_notes) if len(notes) > 1 else False
            slurred = any(want.replace("stop", "stop") in n["slur"] or ("start" if dirn == "after" else "stop") in n["slur"]
                          for n in notes)
            fates = []
            for a in arcs:
                k, t = kinds.get(a), tiep.get(a)
                pb = ((k or {}).get("detail") or {}).get("page_binding") or {}
                fates.append(dict(arc=a, cls=boxes[a][0],
                                  not_arc=(notarc.get(a) or {}).get("value"),
                                  kind=(k or {}).get("value"), kind_reason=(k or {}).get("reason"),
                                  pb_rule=pb.get("rule"), pb_steps=(pb.get("start_step"), pb.get("stop_step")),
                                  pb_heads=(pb.get("start"), pb.get("stop")),
                                  tie_pair=(t or {}).get("outcome"), tie_reason=(t or {}).get("reason"),
                                  tie_value=(t or {}).get("value"),
                                  system_arc=("joined" if a in sys_obs else
                                              ((sys_abst.get(a) or {}).get("detail") or {}).get("note", "none"))))
            decided = any(f["tie_pair"] == "decided" for f in fates)
            if not notes:
                cause = "EXPORT: head not written"
            elif not decided:
                cause = _cause(fates, notes, unison.get(h), want)
            elif len(notes) == 1:
                taken = used_one.get((h, dirn))
                if any(want in n["tie"] for n in notes) and not taken:
                    used_one[(h, dirn)] = side
                    cause = "written (unison written as ONE note)"
                else:
                    cause = "EXPORT: unison written as one note, its second voice's tie has no note"
            elif on_voice:
                cause = "written"
            elif on_other:
                cause = "EXPORT: written on the other voice (the twin carries no tie)"
            else:
                cause = "EXPORT: decided, not written on either voice"
            slots.append(dict(head=h, side=side, dirn=dirn, cause=cause, notes=len(notes),
                              unison=(unison.get(h) or {}).get("outcome"),
                              unison_reason=(unison.get(h) or {}).get("reason"), fates=fates))
    # one MARK read by two boxes (2.58b mark groups) is one head: its slots are counted once, on the box the file wrote
    members = collections.defaultdict(list)
    for o in rec.observations:
        if o["quantity"] == "mark_group":
            members[str(o["value"])].append(o["subject"])
    alias = {}
    for subs in members.values():
        w = [s for s in subs if s in wr]
        for s in subs:
            alias[s] = w[0] if len(w) == 1 else min(subs)
    rank = lambda c: (0 if c.startswith("written") else 3 if "head not written" in c else 1 if c.startswith("EXPORT") else 2)
    best = {}
    for s in slots:
        key = (alias.get(s["head"], s["head"]), s["side"], s["dirn"])
        s["mark"] = key[0]
        if key not in best or rank(s["cause"]) < rank(best[key]["cause"]):
            best[key] = s
    return list(best.values())


def _cause(fates, notes, uni, want):
    if not notes:
        return "EXPORT: head not written"
    for f in fates:
        if f["tie_pair"] == "decided":
            v = f["tie_value"] or {}
            return "EXPORT: decided pair not written on this voice (%s)" % (
                "twin missing: unison not two notes" if len(notes) < 2 else "same-glyph pair merged onto the up voice")
    for f in fates:
        if f["not_arc"] is True:
            continue
        if f["kind"] == "slur" and f["pb_rule"]:
            return "ADJUDICATE kind slur: %s" % f["pb_rule"]
    for f in fates:
        if f["tie_pair"] == "narrowed":
            return "ADJUDICATE tie pair narrowed: %s" % f["tie_reason"]
        if f["kind"] == "tie" and f["tie_pair"] == "abstained":
            return "ADJUDICATE tie pair refused: %s" % f["tie_reason"]
    for f in fates:
        if f["kind"] == "slur":
            return "ADJUDICATE kind slur (no page binding; system arc: %s)" % (
                "joined" if f["system_arc"] == "joined" else "not joined")
    if all(f["not_arc"] is True for f in fates):
        return "ADJUDICATE not an arc"
    return "other"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default="")
    ap.add_argument("--xml", default="")
    ap.add_argument("--sp", type=float, default=15.75, help="one staff space in px (Litolff 15.75, Brahms 32)")
    a = ap.parse_args()
    result = load_record(a.record)
    if "record" not in result:
        result = {"record": result, "summary": {}}
    if a.xml:
        xml = pathlib.Path(a.xml).read_text()
    else:
        from tools.omr.staged.lane_report import traced_export
        with traced_export():
            xml, _report = E.to_musicxml(result)
        if a.json:
            pathlib.Path(a.json).with_suffix(".musicxml").write_text(xml)
    slots = census(result, xml, a.sp)
    for s in slots:
        print("%-22s %-5s %-6s n=%d %-9s | %s" % (s["head"], s["side"], s["dirn"], s["notes"], s["unison"], s["cause"]))
    c = collections.Counter(s["cause"] for s in slots)
    heads = {s["head"] for s in slots}
    print("unison heads with an arc end beside them: %d; slots: %d" % (len(heads), len(slots)))
    for k, n in c.most_common():
        print("  %3d  %s" % (n, k))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(dict(slots=slots, counts=c), default=str, indent=1))


if __name__ == "__main__":
    main()
