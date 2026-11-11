"""2.291 capture (MEASURE ONLY, STAGED ADJUDICATE..EXPORT replay of the saved gather slice; nothing in tools/ changes).

    PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/capture.py PLATE PAGES OUTDIR

Replays like `tools.omr.staged.conservation` and keeps, for EVERY bar the export did not write plain (red / partial / held):
  its export numbers (want, counted per voice, `_partial_bar_plan` `why`, unread glyphs), its events, the page box of its cell, its staff lines,
  EVERY glyph box of the cell with its export fate, class (head / rest / other), duration verdict, owner verdict, and the system's meter verdict.
Writes OUTDIR/PLATE.bars.json, PLATE.report.json, PLATE.musicxml.
"""
import collections
import json
import os
import pathlib
import sys
import time

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import conservation as C   # noqa: E402
from tools.omr.staged import export as E         # noqa: E402
from tools.omr.staged.record import Q            # noqa: E402
from tools.omr.staged.review import rerun as RR   # noqa: E402

CAP = {}
_orig = E._place_notes


def _wrap(rec, runs, *a, **k):
    CAP["rec"] = rec
    CAP["fates"] = k.get("fates")
    return _orig(rec, runs, *a, **k)


E._place_notes = _wrap


def vd(rec, q, sub):
    v = rec.verdict(q, sub)
    if v is None:
        return None
    return {"outcome": v.get("outcome"), "reason": v.get("reason"), "decider": v.get("decider")}


def main():
    plate, pages_s, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
    pages = [int(x) for x in pages_s.split(",")]
    out.mkdir(parents=True, exist_ok=True)
    rows = C.load_pages(plate, pages, C.DEFAULT_TAG)
    t0 = time.time()
    log, _ = RR.rebuild_gather(rows)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    xml, report = E.to_musicxml(result)
    rec, fates = CAP["rec"], CAP["fates"]
    (out / (plate + ".musicxml")).write_text(xml)
    json.dump(report, open(out / (plate + ".report.json"), "w"), default=str)

    # every glyph of every cell
    by_cell = collections.defaultdict(list)
    for o in rec.obs_of(Q.GLYPH_BOX):
        s = E._parse_subject(o["subject"])
        if s["glyph"] is None:
            continue
        sub = o["subject"]
        nh = rec.obs(Q.NOTEHEAD_CLASS, sub)
        isr = bool(rec.obs(Q.REST, sub))
        own = rec.verdict(Q.GLYPH_OWNER, sub) or {}
        by_cell[(s["page"], s["system"], s["staff"], s["cell"])].append({
            "sub": sub, "fate": fates.get(sub), "box": E._page_box_of(o), "cls": o["value"][0], "conf": o.get("score"),
            "head": bool(nh), "rest": isr, "duration": vd(rec, Q.DURATION, sub),
            "stem_dir": (rec.verdict(Q.STEM_DIRECTION, sub) or {}).get("value"), "head_stem": vd(rec, Q.HEAD_STEM, sub),
            "not_a_notehead": vd(rec, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub), "owner": own.get("value") if own.get("outcome") == "decided" else None,
            "owner_reason": own.get("reason")})
    cellbox = {}
    for o in rec.obs_of("cell_box"):
        p = o["subject"].split("/")
        cellbox[tuple(int(x) for x in p[1:5])] = o["value"]
    staves = {}
    for o in rec.obs_of(Q.STAFF_LINES):
        p = o["subject"].split("/")
        staves[tuple(int(x) for x in p[1:4])] = o.get("value")

    bars = []
    pb = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in report["partial_bars"]["bars"]}
    red = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in report["bars_written_red"]["bars_list"]}
    held = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in report.get("held_bars_list", [])}
    for key in sorted(set(pb) | set(red)):
        p, s, st, c = key
        b = {"plate": plate, "key": list(key), "status": (pb.get(key) or {}).get("status"),
             "why": (pb.get(key) or {}).get("why"), "unread_glyphs": (pb.get(key) or {}).get("unread_glyphs"),
             "measure": (pb.get(key) or red.get(key) or {}).get("measure"),
             "rows_in_gap": (pb.get(key) or {}).get("rows_in_gap"), "gap_quarters": (pb.get(key) or {}).get("gap_quarters"),
             "red": ({k: v for k, v in red[key].items() if k != "rows"} if key in red else None),
             "red_rows": red[key]["rows"] if key in red else None,
             "cell_box": cellbox.get(key), "staff_lines": staves.get((p, s, st)),
             "glyphs": by_cell.get(key, [])}
        m = rec.verdict(Q.METER, "system/%d/%d" % (p, s))
        if m:
            b["meter"] = {"outcome": m.get("outcome"), "reason": m.get("reason"), "decider": m.get("decider"), "value": m.get("value")}
        bars.append(b)
    json.dump(bars, open(out / (plate + ".bars.json"), "w"), default=str)
    print(plate, pages, "%.0fs" % (time.time() - t0), "bars", len(bars), collections.Counter(b["status"] for b in bars))
    print(C.block(plate, pages, {"report": report, "seconds": time.time() - t0}))


main()
