"""2.279 explore: print the verdict structure for a few dropped real-note heads (READ-ONLY).

usage: python3 probe/2.279/explore.py RECORD INK.json
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT          # noqa: E402
from tools.omr.staged.record_io import load_record      # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402

rec_path, ink_path = sys.argv[1], sys.argv[2]
t = time.time()
d = load_record(rec_path)
print("loaded", round(time.time() - t), flush=True)
CAP = {}
orig = EXPORT._place_notes


def place(rec, runs, **kw):
    CAP["rec"] = rec
    CAP["runs"] = runs
    CAP["fates"] = kw.get("fates")
    return orig(rec, runs, **kw)


EXPORT._place_notes = place
xml, report = EXPORT.to_musicxml(d)
rec = CAP["rec"]
print("exported", round(time.time() - t), report["notes_not_written_total"], flush=True)
ink = json.load(open(ink_path))
for b in ("refused:duration_narrowed", "refused:chord_value_undecided", "refused:no_pitch"):
    for sub in ink["members"][b][:2]:
        print("=====", b, sub)
        for q in (Q.DURATION, Q.STEM_VALUE, Q.PITCH, Q.EVENT, Q.HEAD_STEM):
            try:
                v = rec.verdict(q, sub)
            except Exception as e:
                v = repr(e)
            print(q, json.dumps(v, default=str)[:1500])
        p = sub.split("/")
        print("METER sys", json.dumps(rec.verdict(Q.METER, "system/%s/%s" % (p[1], p[2])), default=str)[:600])
print(sorted(report.keys()))
print(json.dumps(report["partial_bars"]["bars"][:2], default=str)[:600])
print(json.dumps(report["bars_written_red"]["bars_list"][:2], default=str)[:800])
print(json.dumps(report["bars_held_out_sum"]["held"][:2], default=str)[:600])
