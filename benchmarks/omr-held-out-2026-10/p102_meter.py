"""ROADMAP 2.102 probe: meter-sign boxes of one system, in page px.

    python3 benchmarks/omr-held-out-2026-10/p102_meter.py REC page system
"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

r = load_record(sys.argv[1])["record"]
pre = f"glyph/{sys.argv[2]}/{sys.argv[3]}/"
for o in r["observations"]:
    if (o["quantity"] == "glyph_box" and o["subject"].startswith(pre)
            and str(o["value"][0]).startswith("timeSig")):
        d = o.get("detail") or {}
        print(o["subject"], o["value"][0], "xc_page", round(d.get("x_center_page", -1)),
              "yc", round(d.get("y_center_page", -1)))
