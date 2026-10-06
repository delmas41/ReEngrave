"""lane-owner-by-ledgers (2026-10-05): which staff owns a far head, read off its LEDGERS (ROADMAP 2.56b).
READ ONLY -- no gather. The 10-04 run-2 records (boxes, staff lines + extents, geometry positions, recorded
`glyph_owner` verdicts) with the page re-rendered in the gather's own frame at 600 dpi, the page head shape pooled
over the document where a page has < 8 clean heads (exactly `farhead_note_first_oos.py`).

For every far head (outside its OWN staff's first space) the note-first look is run toward its own staff and toward
the next staff beyond it (`tools.omr.annotate.far_head_owner`); exactly one fitting staff owns it.

  python3 farhead_owner_by_ledgers.py run litolff 4 16 out.json     # every far head of the page range
  python3 farhead_owner_by_ledgers.py run brahms 2 26 out.json
  python3 farhead_owner_by_ledgers.py report litolff out.json       # tallies vs the recorded owner
  python3 farhead_owner_by_ledgers.py controls                      # the 12 abstain-sheet heads + the 44+11 truth set
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import truth_set_2_44c as ts
import farhead_note_first_oos as OOS
from frame import render_page_matching_gather
from tools.omr.annotate import far_head_reader as FH, far_head_owner as FO, ledger_grid as lg
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

SHARED = OOS.SHARED
TRUTHSET = SHARED / "truthset-2.44c-20260930"


def staff_key(subject):
    return "staff/" + "/".join(subject.split("/")[1:4])


def staves_on_page(rec, page):
    lines, ext = {}, {}
    for o in rec.observations:
        if not o["subject"].startswith("staff/%d/" % page) or not o.get("value"):
            continue
        if o["quantity"] == Q.STAFF_LINES:
            lines[o["subject"]] = [float(v) for v in o["value"]]
        elif o["quantity"] == Q.STAFF_EXTENT:
            ext[o["subject"]] = [float(v) for v in o["value"]]
    return [dict(key=k, lines=lines[k], x0=ext[k][0], x1=ext[k][1]) for k in lines if k in ext and len(lines[k]) >= 2]


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def slim(read):
    nf = read.get("note_first") or {}
    return dict(fits=bool(read["fits"]), pos=read["pos"], reason=read["reason"], how=read["how"],
                geometry_position=read.get("geometry_position"), edge_y=read.get("edge_y"),
                line_y=nf.get("line_y"), between=nf.get("between"), gaps=nf.get("gaps"), k=nf.get("k"),
                kind=nf.get("kind"), box_used=read.get("box_used"))


def glyph_rows(rec):
    glyphs = collections.defaultdict(list)
    for o in rec.observations:
        if o["quantity"] != Q.GLYPH_BOX or not o.get("value"):
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        if pb:
            glyphs[int(o["subject"].split("/")[1])].append(
                (o["subject"], o["value"][0], tuple(float(v) for v in pb),
                 float(o.get("score") if o.get("score") is not None else 1.0)))
    return glyphs


def run_doc(which, p0, p1):
    doc, fname = OOS.RECORDS[which]
    cfg = ts.DOCS[doc]
    print("loading", fname, flush=True)
    rec = EXP.Record(load_record(SHARED / fname))
    glyphs = glyph_rows(rec)
    ctxs, pool = {}, []
    for page in range(p0, p1 + 1):
        if page not in glyphs:
            continue
        heads, staff_lines, page_boxes = OOS.page_inputs(rec, page, glyphs[page])
        far = [h for h in heads if lg.far_head_needs_ledger_read(h["pos"])]
        if not far:
            continue
        gray = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
        ctx = FH.FarHeadPage(gray, heads, page_boxes, staff_lines)
        pool.extend(ctx.samples)
        ctxs[page] = (ctx, far, staves_on_page(rec, page), page_boxes)
        print(which, "page", page, "far", len(far), flush=True)
    pooled = FH.pooled_shape(pool)
    FH.READER_KEYWORDS["note_first"] = True
    rows = []
    for page, (ctx, far, staves, page_boxes) in ctxs.items():
        if ctx.shape is None and pooled is not None:
            ctx.adopt(pooled, f"document pool n={len(pool)}")
        nh = [(s, b) for (s, c, b) in page_boxes if c.startswith("notehead")]
        for h in far:
            own = staff_key(h["subject"])
            if ctx.shape is None or not any(s["key"] == own for s in staves):
                continue
            r = FO.owner_by_ledgers(ctx, h["subject"], h["box"], h["cls"], own, staves)
            ov = rec.verdict(Q.GLYPH_OWNER, h["subject"])
            twin = None
            if r["owner"] and r["owner"] != own:
                twin = any(staff_key(s) == r["owner"] and iou(b, h["box"]) > 0.3 for s, b in nh)
            rows.append(dict(
                doc=which, subject=h["subject"], page=page, box=list(h["box"]), cls=h["cls"], own=own,
                geometry=h["pos"], owner=r["owner"], word=r["word"], neighbour=r["neighbour"],
                cands={k: slim(v) for k, v in r["candidates"].items()},
                old_outcome=ov["outcome"] if ov else None, old_value=ov.get("value") if ov else None,
                old_reason=ov.get("reason") if ov else None, twin_on_new_owner=twin))
    return rows


def redecide(r):
    """Re-apply the CURRENT decision (`far_head_owner.decide` + `is_unread`) to a stored row's per-candidate reads, so
    a refinement of the decision does not need the 40-minute re-read. Returns the row with `owner`/`word` replaced."""
    cands = {}
    for k, c in r["cands"].items():
        unread = c["reason"] in ("no_page_shape", "no_staff_lines", "bad_spacing") if c["how"] != "geometry" else False
        unread = (not c["fits"]) and FO.is_unread(c["reason"], {"gaps": c.get("gaps")})
        cands[k] = dict(fits=c["fits"], unread=unread)
    if len(cands) > 1:
        owner, word = FO.decide(cands)
    else:
        k = r["own"]
        owner, word = ((k, "one_candidate") if cands[k]["fits"]
                       else (None, "unread" if cands[k]["unread"] else "neither_fits"))
    return dict(r, owner=owner, word=word)


def report(which, rows):
    rows = [redecide(r) for r in rows]
    n = len(rows)
    print(f"== {which}: far heads {n}")
    wc = collections.Counter(r["word"] for r in rows)
    print("   witness:", dict(wc))
    movers = [r for r in rows if r["owner"] and r["owner"] != r["own"]]
    print(f"   names the NEIGHBOUR staff (own does not fit): {len(movers)}")
    oc = collections.Counter((r["old_outcome"], r["old_reason"]) for r in movers)
    print("   ...of those, the recorded verdict was:", dict(oc))
    print("   ...old owner already = the witness's:", sum(r["old_value"] == r["owner"] for r in movers),
          "| old said own / abstained / no verdict:",
          sum(r["old_value"] == r["own"] for r in movers), sum(r["old_outcome"] == "abstained" for r in movers),
          sum(r["old_outcome"] is None for r in movers))
    print("   ...a twin box exists on the new owner:", sum(bool(r["twin_on_new_owner"]) for r in movers), "of", len(movers))
    keep = [r for r in rows if r["owner"] == r["own"]]
    print(f"   names the OWN staff: {len(keep)}; of those the recorded owner is another staff:",
          sum(1 for r in keep if r["old_outcome"] == "decided" and r["old_value"] != r["own"]))
    flips = [r for r in rows if r["owner"] and r["old_outcome"] == "decided" and r["old_value"] != r["owner"]]
    print(f"   DECIDED recorded owner overturned: {len(flips)}")
    chg = [r for r in rows if r["owner"] and r["owner"] != (r["old_value"] if r["old_outcome"] == "decided" else r["own"])]
    print(f"   CHANGES (witness owner != recorded owner, filing staff where it abstained): {len(chg)}"
          f" -- of them decided->different {len([r for r in chg if r['old_outcome'] == 'decided'])}, "
          f"abstained/none->a staff {len([r for r in chg if r['old_outcome'] != 'decided'])}")
    mv = [r for r in chg if r["owner"] != r["own"]]
    print(f"      ...that move the head OFF its filing staff: {len(mv)}; a twin box exists on the new owner for "
          f"{sum(bool(r['twin_on_new_owner']) for r in mv)} (the rest would be DROPPED with no copy on the new staff)")
    print("      by the recorded reason:", dict(collections.Counter(r["old_reason"] for r in chg)))
    nb = [r for r in rows if r["neighbour"] is None]
    print("   no neighbour staff to read toward:", len(nb))


def pick_tiles():
    old = {w: json.loads((HERE / f"farhead_note_first_oos_{w}.json").read_text()) for w in ("litolff", "brahms")}
    rng = random.Random(20261005)
    picks = []
    for rk in ("no_line_at_the_note_box", "no_rungs", "count_does_not_fit"):
        for w in ("litolff", "brahms"):
            pool = sorted(r["subject"] for r in old[w] if r["new"]["pos"] is None and OOS.reason_key(r["new"]["reason"]) == rk)
            for s in rng.sample(pool, 2):
                picks.append((w, s))
    return picks


SEAN_OTHER = {3, 4, 6, 9, 10, 11}


def controls(litolff_json, brahms_json):
    """(a) the 12 abstain-sheet heads: what the ledger rule says on each, against Sean's verdict
    (tiles 3,4,6,9,10,11 belong to ANOTHER staff, 2 and 12 to their own; 1,5,7,8 not adjudicated).
    (b) the truth-set far heads (Litolff p3, Brahms p1): the rule must keep their owner -- 0 moved."""
    rows = {}
    for w, pth in (("litolff", litolff_json), ("brahms", brahms_json)):
        for r in json.loads(Path(pth).read_text()):
            rows[(w, r["subject"])] = redecide(r)
    print("== (a) the 12 note-first abstain-sheet heads")
    right = wrong = silent = 0
    for no, (w, sub) in enumerate(pick_tiles(), 1):
        r = rows.get((w, sub))
        if r is None:
            print(f"  tile {no:2d} {w} {sub}: NOT in the run")
            continue
        said = ("NEIGHBOUR" if r["owner"] and r["owner"] != r["own"] else "own" if r["owner"]
                else "silent (" + r["word"] + ")")
        sean = "other staff" if no in SEAN_OTHER else "own staff" if no in (2, 12) else "(not adjudicated)"
        ok = None
        if no in SEAN_OTHER or no in (2, 12):
            ok = (said == "NEIGHBOUR") if no in SEAN_OTHER else (said == "own")
            right += bool(ok)
            silent += said.startswith("silent")
            wrong += (not ok and not said.startswith("silent"))
        c = {("own" if k == r["own"] else "nb"): (v["fits"], v["pos"], (v["reason"] or "")[:44])
             for k, v in r["cands"].items()}
        print(f"  tile {no:2d} {w:7s} {sub:20s} Sean: {sean:18s} rule: {said:28s} "
              f"{'' if ok is None else ('OK' if ok else '--')}  {c}")
    print(f"  of the 8 Sean adjudicated: right {right}, wrong {wrong}, silent {silent}")
    print("== (b) truth-set far heads (their own staff is the reference): none may change owner")
    import jut_from_ink_eval as J
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        ts.DOCS[doc]["record"] = TRUTHSET / ("beethoven5-litolff-p3.record.json" if "litolff" in doc
                                             else "brahms1-breitkopf-p1.record.json")
        L, fp, far = J.prepare(doc, page)
        st = staves_on_page(L["rec"], page)
        kept = moved = silent = 0
        for h in far:
            own = staff_key(h["subject"])
            r = FO.owner_by_ledgers(fp, h["subject"], h["box"], h["cls"], own, st)
            if r["owner"] == own:
                kept += 1
            elif r["owner"] is None:
                silent += 1
                print("    silent:", h["subject"], r["word"])
            else:
                moved += 1
                print("    MOVED:", h["subject"], r["owner"])
        print(f"  {doc} p{page}: far heads {len(far)}; owner kept {kept}, silent {silent}, MOVED {moved}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "run":
        rows = run_doc(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
        Path(sys.argv[5]).write_text(json.dumps(rows))
        report(sys.argv[2], rows)
    elif cmd == "controls":
        controls(sys.argv[2], sys.argv[3])
    elif cmd == "report":
        report(sys.argv[2], json.loads(Path(sys.argv[3]).read_text()))
