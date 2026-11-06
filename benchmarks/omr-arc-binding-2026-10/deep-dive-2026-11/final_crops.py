"""The 12 crops of the biggest loss buckets (6 Litolff, 6 Brahms): one staff, the WHOLE arc boxed (thin orange), both ends and notes in view, nothing of
ours drawn. Picks come from the ledger buckets by curve id (the ids are printed in key.json, kept OUT of the pictures). Measure only.
python3 final_crops.py"""
import json
import pathlib
import subprocess
import sys

D = pathlib.Path("scratch/dd")
PICKS = [   # (plate, ledger, curve id, bucket)
    ("litolff", "glyph/2/0/8/10/2", "slur box path: ends 1-2 sp past the box (over-joined chain, binder refused the curve)"),
    ("litolff", "glyph/16/0/1/13/1", "end > 4 sp from any head: arc boxed in part (cut at the barline, no neighbour box)"),
    ("litolff", "glyph/2/1/0/10/6", "tie_pair local flank search: no_head_near_the_arc (tie under a dyad)"),
    ("litolff", "glyph/10/0/0/1/0", "arc bound right, its end head is the twin box; the exporter wrote the other twin (tie_end_not_in_file)"),
    ("litolff", "glyph/9/0/2/14/0", "tie_pair not_adjacent (a note stands between two same-pitch ends: a slur)"),
    ("litolff", "glyph/16/0/10/0/7", "tie enters from the previous system (tie_pair enters_from_previous_system)"),
    ("brahms", "glyph/0/0/12/3/0", "slur cut at the barline: box covers the right part, the arc runs on to the left (written to the wrong note)"),
    ("brahms", "glyph/0/0/12/3/15", "long phrase slur boxed in part, ends > 4 sp from any head"),
    ("brahms", "glyph/5/1/13/8/8", "tie_pair not_adjacent (notes between the same-pitch ends)"),
    ("brahms", "glyph/5/0/2/1/14", "tie bound right; its start note never written (duration_narrowed)"),
    ("brahms", "glyph/5/1/8/7/0", "slur bound right; its start chord never written (chord_value_undecided)"),
    ("brahms", "glyph/0/0/12/4/7", "half arc at a barline (binder refused: joined_not_at_a_barline)"),
]
spec = []
for i, (plate, curve, note) in enumerate(PICKS, 1):
    led = json.load(open(D / ("%s.base.ledger.json" % plate)))
    r = next(r for r in led["rows"] if r["curve"] == curve)
    box = list(r["box"])
    if r.get("x_left") is not None:
        box[0], box[2] = min(box[0], r["x_left"]), max(box[2], r["x_right"])
    spec.append(dict(n=i, plate=plate, page=r["page"], box=box, sp=r["sp"], curve=curve, bucket=note, fate=r["fate"], lost=[r.get("lost_at"), r.get("lost_rule")]))
json.dump(spec, open(D / "spec_final.json", "w"), indent=1)
out = sys.argv[1] if len(sys.argv) > 1 else "out/print/arc-deep-dive"
subprocess.check_call([sys.executable, str(pathlib.Path(__file__).parent / "crops.py"), str(D / "spec_final.json"), out])
