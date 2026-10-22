"""2.114 round 2 item 3: crops of tiles 1, 8, 14 with the cell's own staff and the staff the ownership reader picked drawn and named."""
import json, sys
from pathlib import Path
import cv2
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import record_io
LIT = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRA = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
CASES = [(1, "lit", LIT, 1, "glyph/1/0/9/14/8", "glyph/1/0/10/14/3", "staff/1/0/9", "staff/1/0/10"),
         (8, "bra", BRA, 0, "glyph/0/0/6/5/4", "glyph/0/0/5/5/6", "staff/0/0/6", "staff/0/0/5"),
         (14, "lit", LIT, 1, "glyph/1/0/9/7/5", "glyph/1/0/10/7/1", "staff/1/0/9", "staff/1/0/10")]
out = Path("out/print/2.114-round2"); out.mkdir(parents=True, exist_ok=True)
imgs = {}
for tile, tag, pdf, pg, g2, gp, own, picked in CASES:
    r = record_io.load_record(f"runs/2.114/ab/rec-{tag}-on.json")["record"]["observations"]
    by = {}
    for o in r:
        if o["subject"] in (g2, gp, own, picked): by.setdefault((o["subject"], o["quantity"]), []).append(o)
    sb = by[(g2, "glyph_box")][0]["detail"]["bbox_page_px"]
    pb = by[(gp, "glyph_box")][0]["detail"]["bbox_page_px"]
    sp = by[(own, "staff_spacing")][0]["value"]
    if pdf not in imgs: imgs[pdf] = render_page(Path(pdf), pg, dpi=600).rgb
    img = imgs[pdf]
    cx = (sb[0] + sb[2]) / 2; ax0, ax1 = int(cx - 8 * sp), int(cx + 8 * sp)
    ys = by[(own, "staff_lines")][0]["value"] + by[(picked, "staff_lines")][0]["value"]
    ay0, ay1 = int(min(ys + [sb[1]]) - 1 * sp), int(max(ys + [sb[3]]) + 1 * sp)
    # tall page span: only draw the part near the head
    cy = (sb[1] + sb[3]) / 2; ay0 = int(max(ay0, cy - 9 * sp)); ay1 = int(min(ay1, cy + 9 * sp))
    crop = cv2.cvtColor(img[ay0:ay1, ax0:ax1].copy(), cv2.COLOR_RGB2BGR)
    s = 24.0 / sp * 1.0
    crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    T = lambda x, y: (int((x - ax0) * s), int((y - ay0) * s))
    for name, col in ((own, (255, 0, 0)), (picked, (0, 160, 0))):
        for y in by[(name, "staff_lines")][0]["value"]:
            if ay0 <= y <= ay1:
                cv2.line(crop, T(ax0, y), T(ax1, y), col, 1)
    cv2.rectangle(crop, T(sb[0], sb[1]), T(sb[2], sb[3]), (200, 0, 200), 2)   # second detector box (BGR magenta)
    cv2.rectangle(crop, T(pb[0], pb[1]), T(pb[2], pb[3]), (0, 140, 255), 2)   # production twin box (orange)
    cv2.imwrite(str(out / f"owner-tile{tile}.png"), crop)
    print(tile, crop.shape)
