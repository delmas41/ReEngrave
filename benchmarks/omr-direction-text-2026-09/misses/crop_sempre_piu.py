"""Print crops for ROADMAP 2.68's `sempre piu p` (Litolff p8): the OLD candidate
box in red, the NEW box in green, cut from the PDF at the gather's own DPI (600)
with the staff lines either side of the gap drawn by the print itself.

python3 crop_sempre_piu.py <summary.json AFTER> <outdir> <summary.json BEFORE>
Pickles are looked for in each directory of $DT_PICKLE_DIRS (default /private/tmp/dtmiss)."""
import json, os, pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
import cv2, numpy as np
from tools.omr import direction_text as DT
from tools.omr.preprocessing import render_page

TAG = "lit_8"
PDF = ("library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
dirs = os.environ.get("DT_PICKLE_DIRS", "/private/tmp/dtmiss").split(":")
pkl = next(Path(d) / f"{TAG}.pkl" for d in dirs if (Path(d) / f"{TAG}.pkl").exists())
pws, pd = pickle.load(open(pkl, "rb"))
summary = json.load(open(sys.argv[1]))
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)

# FRAME CONTROL: the page we cut from must be the page the gather saw (same pixels
# size, same spacing) -- a crop from another render would commit to nothing.
page = render_page(ROOT / PDF, 8, 600)
assert page.rgb.shape == pws.page.rgb.shape, (page.rgb.shape, pws.page.rgb.shape)
assert float(np.abs(page.rgb.astype(int) - pws.page.rgb.astype(int)).mean()) < 1.0
sp = float(np.median([DT._spacing(s) for s in pws.staves]))

new = DT.find_candidates(pws, pd, refine_boxes=True)
old_summary = json.load(open(sys.argv[3]))            # run_pages.py summary of the tree BEFORE the change
read_now = {tuple(w[6]): w[3] for w in summary[TAG]["words"]}
staff_sys = {s.staff_index: s.system_index for s in pws.staves}

tiles = []
for w in sorted(old_summary[TAG]["words"], key=lambda w: (w[0], w[2])):
    if not (w[3].lower().startswith("sempre") and w[3].lower().endswith(" p") and w[2] >= 1480):
        continue                       # the marking's own boxes (not the sibling windows)
    ob = tuple(w[6])
    near = [c for c in new if abs(c.bbox_page[0] - ob[0]) < 40 and abs(c.bbox_page[1] - ob[1]) < 30]
    if not near:
        continue
    c = near[0]
    x0, y0, x1, y1 = c.bbox_page
    hits = [(t, b) for b, t in read_now.items() if abs(b[0] - x0) < 40 and abs(b[1] - y0) < 30]
    text = hits[0][0] if hits else None
    if hits:
        x1 = max(x1, hits[0][1][2])       # the box the reading was joined over
        c = DT.TextCandidate(c.staff_index, c.measure_index, (x0, y0, x1, y1), c.placement, c.n_components)
    c_staff, c_bar = w[0], w[1]
    old_text = w[3].replace('\u00f9', 'u')
    padx, pady = int(1.5 * sp), int(4.2 * sp)
    cx0, cy0, cx1, cy1 = max(0, x0 - padx), max(0, y0 - pady), x1 + 3 * padx, y1 + pady
    img = np.ascontiguousarray(page.rgb[cy0:cy1, cx0:cx1])
    k = 2
    img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    def rect(b, colour, grow):
        cv2.rectangle(img, ((b[0] - cx0) * k - grow, (b[1] - cy0) * k - grow),
                      ((b[2] - cx0) * k + grow, (b[3] - cy0) * k + grow), colour, 2)
    rect(ob, (220, 0, 0), 4)             # OLD, red (the page is RGB)
    rect(c.bbox_page, (0, 150, 0), 8)    # NEW, green
    img = cv2.copyMakeBorder(img, 0, 0, 0, max(0, 1100 - img.shape[1]), cv2.BORDER_CONSTANT, value=(255, 255, 255))
    head = np.full((70, img.shape[1], 3), 255, np.uint8)
    cv2.putText(head, f"Litolff p8 (pdf index 8), 600 dpi -- filed on staff {c_staff} "
                f"(system {staff_sys[c_staff]}), bar {c_bar}",
                (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    cv2.putText(head, f"RED = old box, read '{old_text}'   GREEN = new box   now reads: "
                f"{(text or 'nothing (abstains)').replace(chr(0xf9), 'u')}", (6, 54),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 90, 0), 1)
    tiles.append(np.vstack([head, img, np.full((8, img.shape[1], 3), 120, np.uint8)]))
W = max(1100, max(t.shape[1] for t in tiles))
tiles = [cv2.copyMakeBorder(t, 0, 0, 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
         for t in tiles]
cv2.imwrite(str(out / "sempre_piu_p_old_red_new_green.png"), cv2.cvtColor(np.vstack(tiles), cv2.COLOR_RGB2BGR))
print(len(tiles), "tiles")
