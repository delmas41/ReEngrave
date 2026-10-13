"""2.80b blind print tiles for Sean: every narrow box read as an eighth rest,
plus controls.

    python3 .../2.80b_tiles.py BRAHMS_REC.json LITOLFF_REC.json OUTDIR

Roles (never printed on the image; `manifest.json` only):
  reinstated  -- every box `adjudicate_narrow_box_is_an_eighth_rest` decided True
  duplicate   -- decided False `ink_already_read_as_a_glyph` (a SECOND box over a
                 rest the detector already boxed): sample
  not_rest    -- decided False `not_rest_shaped` (a real narrow non-rest): sample
  abstained   -- abstained `claimed_by_another_class` / `shape_cannot_tell`: sample
Each tile: one bar, phone-sized (900 px wide), a big tile number, RED corner
bracket on the bar, BLUE corner bracket on the narrow box's ink. Same frame
control as 2.80_tiles.py (asserted per tile, with its negative control).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
brahms_rec, litolff_rec, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
MAX_TILES = 12


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

pool = {"reinstated": [], "duplicate": [], "not_rest": [], "abstained": []}
for doc, (rec, log) in recs.items():
    for v in log.to_json()["verdicts"]:
        if v["quantity"] != Q.NOTEHEAD_IS_AN_EIGHTH_REST:
            continue
        item = (doc, v["subject"], v["reason"])
        if v["outcome"] == "decided" and v["value"] is True:
            pool["reinstated"].append(item)
        elif v["outcome"] == "decided" and v["reason"] == "ink_already_read_as_a_glyph":
            pool["duplicate"].append(item)
        elif v["outcome"] == "decided" and v["reason"] == "not_rest_shaped":
            pool["not_rest"].append(item)
        elif v["outcome"] == "abstained" and v["reason"] in (
                "claimed_by_another_class", "shape_cannot_tell"):
            pool["abstained"].append(item)


def sample(items, k):
    items = sorted(items)
    step = max(1, len(items) // max(k, 1))
    return items[::step][:k]


chosen = list(pool["reinstated"])
room = MAX_TILES - len(chosen)
quota = {"duplicate": min(3, room), "not_rest": min(3, room),
         "abstained": min(2, room)}
for role in ("duplicate", "not_rest", "abstained"):
    chosen += [(d, s, r_) for (d, s, r_) in sample(pool[role], quota[role])]
roles = {}
for role, items in pool.items():
    for it in items:
        roles[it[:2]] = role

try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 90)
except Exception:
    font = ImageFont.load_default()

pages = {}
manifest = {"dpi": 600, "pool_sizes": {k: len(v) for k, v in pool.items()},
            "question": "For the bar inside the RED corners: what is the mark inside the "
                        "BLUE corners (a note, a rest -- which -- or something else)?",
            "tiles": []}
n = 0
for (doc, subject, reason) in chosen:
    if n >= MAX_TILES:
        break
    rec, log = recs[doc]
    g = R.Subject.from_key(subject)
    page, system, staff, c = g.page, g.system, g.staff, g.cell
    shape = log.rows(Q.NARROW_BOX_SHAPE, g)
    box = (shape[-1].detail or {}).get("bbox_page_px") if shape else None
    if not box:
        gb = log.rows(Q.GLYPH_BOX, g)
        box = (gb[-1].detail or {}).get("bbox_page_px") if gb else None
    if not box:
        continue
    if (doc, page) not in pages:
        pages[(doc, page)] = np.asarray(
            Image.fromarray(render_page(PDFS[doc], page, dpi=600).rgb).convert("RGB"))
    img = pages[(doc, page)].copy()
    ink = 255.0 - np.asarray(Image.fromarray(img).convert("L")).astype(float)
    recd = rec["record"] if "record" in rec else rec
    cell_box, lines = geometry(recd, page, system)
    if (staff, c) not in cell_box or staff not in lines:
        continue
    bar, ln = cell_box[(staff, c)], lines[staff]
    sp = float(np.mean(np.diff(ln)))
    # ⚠️ THE RECORD'S STAFF LINES ARE IDEAL ROWS AND A SCANNED STAFF WANDERS
    # (system 1 of Brahms p1 sits 9 px = a third of a space off at this x), so
    # the frame is first CALIBRATED by the best vertical shift within +/-0.4
    # space, and the control is then run at that shift (must pass) and half a
    # space further (the negative control, must FAIL). Reported in the manifest.
    cal = max((k / 20.0 for k in range(-8, 9)),
              key=lambda t: frame_control(ink, bar, ln, t)["ratio"])
    fc = frame_control(ink, bar, ln, cal)
    neg = frame_control(ink, bar, ln, cal + 0.5)
    if not fc["passes"] or neg["passes"]:
        print("skipped (frame control):", subject, fc, neg)
        continue
    n += 1
    pad = int(max(2.5 * sp, (14 * sp - (bar[2] - bar[0])) / 2))
    wx0, wx1 = int(bar[0]) - pad, int(bar[2]) + pad
    wy0, wy1 = int(ln[0] - 4.5 * sp), int(ln[-1] + 4.5 * sp)
    bracket(img, int(bar[0]) + 6, int(ln[0] - 1.3 * sp), int(bar[2]) - 6,
            int(ln[-1] + 1.3 * sp), (220, 0, 0))
    bracket(img, int(box[0]) - 6, int(box[1]) - 6, int(box[2]) + 6,
            int(box[3]) + 6, (0, 70, 230), arm=18, thick=5)
    crop = Image.fromarray(img[wy0:wy1, wx0:wx1])
    crop = crop.resize((900, max(1, int(crop.height * 900.0 / crop.width))), Image.LANCZOS)
    tile = Image.new("RGB", (900, 130 + crop.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 15), f"Tile {n}", fill=(0, 0, 0), font=font)
    tile.paste(crop, (0, 130))
    name = f"tile_{n:02d}.png"
    tile.save(OUT / name)
    v = log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, g)
    manifest["tiles"].append({
        "n": n, "file": name, "document": doc, "glyph": subject,
        "role": roles.get((doc, subject)), "our_reading": {
            "outcome": v.outcome.value, "value": v.value, "reason": v.reason,
            "detail": v.detail},
        "frame_control": fc, "frame_control_negative": neg,
        "calibration_shift_spaces": cal,
        "page_box_600dpi": [wx0, wy0, wx1, wy1]})
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
print("wrote", n, "tiles to", OUT, manifest["pool_sizes"])
