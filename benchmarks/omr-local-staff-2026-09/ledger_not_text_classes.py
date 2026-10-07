"""lane-ledger-not-text (2026-10-05): which detector classes the Brahms record holds near the tile-12 head, and the
classes of the whole record (read only).  python3 ledger_not_text_classes.py"""
import sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.staged import export as EXP
from tools.omr.staged.record import Q
from tools.omr.staged.record_io import load_record

S = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
rec = EXP.Record(load_record(S / "brahms1-breitkopf-mvt1-whole-20261004-farhead-all.record.json"))
c = collections.Counter(); near = []
for o in rec.observations:
    if o["quantity"] != Q.GLYPH_BOX or not o.get("value"):
        continue
    c[o["value"][0]] += 1
    pb = (o.get("detail") or {}).get("bbox_page_px")
    if o["subject"].split("/")[1] == "5" and pb and abs((pb[0] + pb[2]) / 2 - 2635) < 200 and pb[3] > 1700 and pb[1] < 1900:
        near.append((o["subject"], o["value"][0], [round(v) for v in pb]))
print(sorted(c.items(), key=lambda t: -t[1]))
for n in near:
    print(n)
print(sorted({o["quantity"] for o in rec.observations}))
