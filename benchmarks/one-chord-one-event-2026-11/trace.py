"""2.300 trace: for named cells, print Q.EVENT / Q.VOICES verdicts and the exporter's events.
    PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/trace.py PLATE PAGES page/system/staff/cell ...
"""
import os
import pathlib
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import conservation as C, export as E  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

CAP = {}
_o = E._place_notes


def _w(rec, runs, *a, **k):
    CAP["rec"] = rec
    return _o(rec, runs, *a, **k)


E._place_notes = _w
_ev = E._voice_split


def _vs(rec, run, ci, events, why=None):
    r = _ev(rec, run, ci, events, why)
    CAP.setdefault("ev", {})[(run.page, run.system, run.staff, ci)] = (events, r, list(why or []))
    return r


E._voice_split = _vs
plate, pages = sys.argv[1], [int(x) for x in sys.argv[2].split(",")]
rows = C.load_pages(plate, pages, C.DEFAULT_TAG)
log, _ = RR.rebuild_gather(rows)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
E.to_musicxml(result)
rec = CAP["rec"]
for k in sys.argv[3:]:
    p, s, st, c = [int(x) for x in k.split("/")]
    print("=== cell", k)
    print("VOICES", (lambda v: v and (v.get("outcome"), v.get("reason"), v.get("value")))(rec.verdict(Q.VOICES, "cell/%s" % k)))
    cellsub = "cell/%s" % k
    for o in rec.obs_of(Q.STEM):
        if o["subject"] == cellsub:
            print(" STEM", o["id"], [round(v) for v in o["value"]] if isinstance(o["value"], (list, tuple)) else o["value"])
    for o in rec.obs_of(Q.GLYPH_BOX):
        if o["subject"].startswith("glyph/%s/" % k) and rec.obs(Q.NOTEHEAD_CLASS, o["subject"]):
            hs = rec.verdict(Q.HEAD_STEM, o["subject"]) or {}
            print(" HEAD", o["subject"], "canon", [round(v) for v in o["value"][1:5]], "page", [round(v) for v in E._page_box_of(o)], hs.get("outcome"), hs.get("reason"), hs.get("value"), (hs.get("detail") or {}).get("x_frac"))
    ev = CAP["ev"].get((p, s, st, c))
    if ev:
        events, r, why = ev
        for e in events:
            print(" EVENT", e["kind"], e["x_position"], e["duration_beats"],
                  [(n.get("glyph"), n.get("pitch"), n.get("stem_direction")) for n in e.get("noteheads", [])]
                  or (e["rest"] or {}).get("glyph"))
        print(" voice_split ->", None if r is None else [[(e["kind"], e["x_position"]) for e in s_] for s_ in r], why)
