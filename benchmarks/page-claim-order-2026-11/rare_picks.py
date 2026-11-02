"""ROADMAP 2.253 step 0 -- detector boxes of the 'read by nothing' classes on the frozen sample, as look-sheet picks.

    python3 benchmarks/page-claim-order-2026-11/rare_picks.py     # writes rare_picks.json (look.py input)
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count as C  # noqa: E402

RARE = ("ottava", "keyboardPedal", "segno", "coda", "ornamentTrill", "wiggle")
picks = []
for plate, (_, pages) in C.EDITIONS.items():
    for o in C.rows(C.SLICES / plate):
        if o["quantity"] != "glyph_box" or not o["value"][0].startswith(RARE):
            continue
        p = int(o["subject"].split("/")[1])
        if p not in pages:
            continue
        b = o["detail"]["bbox_page_px"]
        picks.append({"plate": plate, "page": p, "pb": b, "subject": o["subject"], "cls": o["value"][0],
                      "caption": "%s p%d %s %.2f" % (plate[:3], p, o["value"][0][:14], o["score"])})
(HERE / "rare_picks.json").write_text(json.dumps(picks, indent=1))
for i, k in enumerate(picks, 1):
    print(i, k["caption"], k["subject"], [round(v) for v in k["pb"]])
