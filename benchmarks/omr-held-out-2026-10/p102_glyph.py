"""ROADMAP 2.102 probe: every row a glyph subject holds, and its cell's boxes.

    python3 benchmarks/omr-held-out-2026-10/p102_glyph.py REC glyph/p/s/st/c/g
"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

r = load_record(sys.argv[1])["record"]
subj = sys.argv[2]
cell = "cell/" + "/".join(subj.split("/")[1:5])
for o in r["observations"]:
    if o["subject"] == subj:
        d = {k: v for k, v in (o.get("detail") or {}).items()
             if not isinstance(v, (list, dict)) or len(str(v)) < 120}
        print("OBS", o["quantity"], str(o["value"])[:90], str(d)[:260])
for a in r.get("abstentions", []):
    if a["subject"] == subj:
        print("ABS", a["quantity"], a["reason"])
for v in r["verdicts"]:
    if v["subject"] == subj and v["quantity"] in (
            "duration", "notehead_is_not_a_notehead", "head_stem", "stem_value"):
        print("VRD", v["quantity"], v["outcome"], str(v["value"])[:80],
              v["decider"], v["reason"])
print("-- cell", cell)
for o in r["observations"]:
    if o["quantity"] == "glyph_box" and o["subject"].startswith(cell + "/"):
        print(o["subject"].split("/")[-1], o["value"])
