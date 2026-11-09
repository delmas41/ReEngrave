"""2.279b: heads dropped as `no_pitch`, by staff: the staff's clef verdict, whether a notehead_staff_position row exists for the head,
and what the head's own pitch / position verdicts say. READ-ONLY re-export of the saved record.
usage: nopitch.py RECORD OUT.json [slim]"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT           # noqa: E402
from tools.omr.staged.record_io import load_record, expand_result  # noqa: E402
from tools.omr.staged.record import Q                    # noqa: E402

rec_path, out = sys.argv[1], sys.argv[2]
d = load_record(rec_path)
CAP = {}
orig = EXPORT._place_notes


def place(rec, runs, **kw):
    CAP["rec"] = rec
    CAP["fates"] = kw.get("fates")
    return orig(rec, runs, **kw)


EXPORT._place_notes = place
xml, report = EXPORT.to_musicxml(d)
rec, fates = CAP["rec"], CAP["fates"]
rows = []
for sub, f in fates.items():
    if f != "no_pitch":
        continue
    p = sub.split("/")
    staff = "staff/%s/%s/%s" % (p[1], p[2], p[3])
    cl = rec.verdict(Q.CLEF, staff)
    pos_rows = rec.obs(Q.NOTEHEAD_STAFF_POSITION, sub)
    far = rec.verdict(Q.NOTEHEAD_POSITION, sub)
    pv = rec.verdict(Q.PITCH, sub)
    rows.append(dict(sub=sub, staff=staff,
                     clef=(cl or {}).get("outcome") + ":" + str((cl or {}).get("value") or [c.get("value") for c in (cl or {}).get("candidates") or ()]),
                     clef_decider=(cl or {}).get("decider"), clef_reason=(cl or {}).get("reason"),
                     n_pos_rows=len(pos_rows or []), far=(far or {}).get("outcome"), pitch=(pv or {}).get("outcome"),
                     pitch_reason=(pv or {}).get("reason")))
json.dump(rows, open(out, "w"), indent=0, default=str)
c = collections.Counter((r["staff"], r["clef"], r["n_pos_rows"] > 0, r["far"], r["pitch"]) for r in rows)
for k, n in sorted(c.items(), key=lambda kv: -kv[1]):
    print(n, k)
print("heads", len(rows))
