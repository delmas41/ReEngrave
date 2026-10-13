"""2.80 blind print tiles for Sean.

    python3 .../2.80_tiles.py BRAHMS_REC.json LITOLFF_REC.json OUTDIR

Each tile is one BAR cut from the plate at the gather's own 600 dpi (in
`render_page`'s deskewed frame), phone-sized (about 900 px wide), a big tile
number on a banner, a RED corner bracket on the bar (following the staff, not
the padded cell), a BLUE corner bracket on the subject (the note a rule
re-read, or the ink nobody explains). Nothing of ours is written on the image:
our reading is in `manifest.json` only.

Frame control (it can fail): the five staff lines the record filed must carry
>= 2x the ink of the rows between them, and the same test shifted half a space
(the NEGATIVE control) must fail -- asserted per tile.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import consequences as C, record as R  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
brahms_rec, litolff_rec, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)


def load(path):
    doc = load_record(path)
    rec = doc["record"] if "record" in doc else doc
    log, _ = rerun.rebuild_gather(rec)
    rerun.run_stages(log)
    return rec, log


def geometry(rec, page, system):
    cell_box, lines = {}, {}
    for o in rec["observations"]:
        p = o["subject"].split("/")
        if len(p) > 3 and p[1] == str(page) and p[2] == str(system):
            if o["quantity"] == "cell_box" and p[0] == "cell":
                cell_box[(int(p[3]), int(p[4]))] = o["value"]
            elif o["quantity"] == "staff_lines" and p[0] == "staff":
                lines[int(p[3])] = o["value"]
    return cell_box, lines


def bracket(arr, x0, y0, x1, y1, colour, arm=40, thick=6):
    h, w = arr.shape[:2]
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1),
                             (x0, y1, 1, -1), (x1, y1, -1, -1)):
        xa, xb = sorted((cx, cx + dx * arm))
        ya, yb = sorted((cy, cy + dy * arm))
        arr[max(cy - thick // 2, 0):cy + thick // 2 + 1, max(xa, 0):min(xb, w)] = colour
        arr[max(ya, 0):min(yb, h), max(cx - thick // 2, 0):cx + thick // 2 + 1] = colour


def frame_control(ink, box, lines, shift=0.0):
    x0, x1 = int(box[0]) + 40, int(box[2]) - 40
    sp = float(np.mean(np.diff(lines)))
    rows = [int(round(y + shift * sp)) for y in lines]
    mids = [int(round((a + b) / 2 + shift * sp)) for a, b in zip(lines[:-1], lines[1:])]
    on = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in rows]))
    off = float(np.mean([ink[r - 1:r + 2, x0:x1].mean() for r in mids]))
    return {"ratio": round(on / max(off, 1e-6), 2), "passes": bool(on >= 2.0 * off)}


recs = {"brahms": load(brahms_rec), "litolff": load(litolff_rec)}
pages = {}

# (doc, cell key, role). role: refused / landed / ink
TILES = [
    ("brahms", "cell/1/0/13/5", "refused"),   # Contrabass bar 13
    ("brahms", "cell/1/0/12/5", "landed"),    # Cello bar 13
    ("litolff", "cell/2/1/6/9", "landed"),
    ("litolff", "cell/2/1/10/3", "landed"),
    ("litolff", "cell/2/1/10/4", "landed"),
    ("litolff", "cell/2/1/10/5", "landed"),
    ("litolff", "cell/3/0/7/15", "landed"),
]
# three Brahms cells the witness calls unexplained but nobody asked about:
rec, log = recs["brahms"]
extra = []
for o in rec["observations"]:
    if o["quantity"] != R.Q.CELL_INK_PIECES:
        continue
    cell = R.Subject.from_key(o["subject"])
    out = []
    ans, left = C._missed_rest_witness(log, cell, pieces_out=out)
    if ans == C.WITNESS_UNEXPLAINED and left in (1, 2) and cell.page == 1:
        extra.append(o["subject"])
step = max(1, len(extra) // 12)
for k in extra[::step]:
    TILES.append(("brahms", k, "ink"))

try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
except Exception:
    font = ImageFont.load_default()

manifest = {"dpi": 600, "question": "For the bar inside the RED corners: what is printed "
            "in it, in order (notes and rests, with their values)? The BLUE corners mark "
            "the thing we want you to look at.", "tiles": []}
n = 0
n_ink = 0
for (doc, key, role) in TILES:
    if role == "ink" and n_ink >= 3:
        break
    n_next = n + 1
    rec, log = recs[doc]
    cell = R.Subject.from_key(key)
    page, system, staff, c = cell.page, cell.system, cell.staff, cell.cell
    if (doc, page) not in pages:
        pages[(doc, page)] = np.asarray(
            Image.fromarray(render_page(PDFS[doc], page, dpi=600).rgb).convert("RGB"))
    img = pages[(doc, page)].copy()
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    cell_box, lines = geometry(rec, page, system)
    bar = cell_box[(staff, c)]
    sp = float(np.mean(np.diff(lines[staff])))
    pad = int(max(2.5 * sp, (14 * sp - (bar[2] - bar[0])) / 2))   # >= 14 spaces wide
    wx0, wx1 = int(bar[0]) - pad, int(bar[2]) + pad
    wy0, wy1 = int(lines[staff][0] - 4.5 * sp), int(lines[staff][-1] + 4.5 * sp)
    fc, neg = frame_control(ink, bar, lines[staff]), frame_control(ink, bar, lines[staff], 0.5)
    if role == "ink" and not fc["passes"]:
        print("skipped (frame control failed, as it must be able to):", key, fc)
        continue
    assert fc["passes"], (key, fc)
    assert not neg["passes"], ("the control cannot fail", key, neg)
    n = n_next
    n_ink += role == "ink"
    bracket(img, int(bar[0]) + 6, int(lines[staff][0] - 1.3 * sp),
            int(bar[2]) - 6, int(lines[staff][-1] + 1.3 * sp), (220, 0, 0))
    subject = []
    if role == "landed":
        for v in log.to_json()["verdicts"]:
            if v.get("decider") == "reconcile_duration" and \
                    v["subject"].startswith(f"glyph/{page}/{system}/{staff}/{c}/"):
                subject.append(v["subject"])
        for g in subject:
            for o in rec["observations"]:
                if o["subject"] == g and o["quantity"] == "glyph_box":
                    b = o["detail"]["bbox_page_px"]
                    bracket(img, int(b[0]) - 6, int(b[1]) - 6, int(b[2]) + 6,
                            int(b[3]) + 6, (0, 70, 230), arm=18, thick=5)
    else:
        pcs = []
        C._missed_rest_witness(log, cell, pieces_out=pcs)
        for b in pcs:
            bracket(img, int(b[0]) - 6, int(b[1]) - 6, int(b[2]) + 6,
                    int(b[3]) + 6, (0, 70, 230), arm=18, thick=5)
        subject = [list(map(round, b)) for b in pcs]
    crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
    scale = 900.0 / crop.width
    crop = crop.resize((900, max(1, int(crop.height * scale))), Image.LANCZOS)
    banner = Image.new("RGB", (900, 130), (255, 255, 255))
    ImageDraw.Draw(banner).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
    tile.paste(banner, (0, 0))
    tile.paste(crop, (0, 130))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    changed = []
    for v in log.to_json()["verdicts"]:
        if v.get("decider") == "reconcile_duration" and \
                v["subject"].startswith(f"glyph/{page}/{system}/{staff}/{c}/"):
            changed.append({"subject": v["subject"], "beats": v["value"].get("beats")})
    manifest["tiles"].append({
        "n": n, "file": name, "document": doc, "cell": key, "role": role,
        "subject": subject, "reconcile_duration_landing_in_this_bar": changed,
        "frame_control": fc, "frame_control_negative": neg,
        "page_box_600dpi": [wx0, wy0, wx1, wy1]})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote", len(manifest["tiles"]), "tiles to", OUT)
