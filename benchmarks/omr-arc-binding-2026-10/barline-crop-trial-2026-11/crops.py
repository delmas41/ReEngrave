"""Crops for the LOOK (a control, not evidence).

    python3 crops.py RES_PREFIX OUTDIR            # RES_PREFIX.<plate>.json from analyze.py

12 crops of B / C boxes that far-cover a barline-crossing arc (6 Litolff, 6 Brahms, arms alternating B, C; the first two per plate chosen WHOLE),
each the whole arc and the barline, ONE thin red box per box drawn (the arm's box), nothing else; and up to 10 per plate of the NEW arc boxes
(no record arc box under them) in out/print/.../newboxes/ for the false-box look. Page raster = `render_page(pdf, p, 600).rgb`, the frame the boxes are in.
"""
import json
import os
import random
import sys

import cv2

ROOT = "/Users/seanjohnson/Desktop/ReEngrave/"
sys.path.insert(0, ROOT + ".claude/worktrees/agent-aca2654680d85413f")
os.chdir(ROOT + ".claude/worktrees/agent-aca2654680d85413f")
PDF = {
    "litolff": ROOT + "library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": ROOT + "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
SC = 4


def crop(rgb, boxes, sp, pad_x=1.5, pad_y=2.0):
    x0 = min(b[0] for b in boxes) - pad_x * sp
    x1 = max(b[2] for b in boxes) + pad_x * sp
    y0 = min(b[1] for b in boxes) - pad_y * sp
    y1 = max(b[3] for b in boxes) + pad_y * sp
    h, w = rgb.shape[:2]
    X0, X1, Y0, Y1 = max(0, int(x0)), min(w, int(x1)), max(0, int(y0)), min(h, int(y1))
    im = cv2.resize(rgb[Y0:Y1, X0:X1].copy(), None, fx=SC, fy=SC, interpolation=cv2.INTER_CUBIC)
    for b in boxes:
        cv2.rectangle(im, (int((b[0] - X0) * SC), int((b[1] - Y0) * SC)), (int((b[2] - X0) * SC), int((b[3] - Y0) * SC)), (0, 0, 255), 1)
    return im


def main():
    pref, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(outdir + "/newboxes", exist_ok=True)
    from tools.omr.preprocessing import render_page
    rng = random.Random(11)
    cache = {}

    def page_rgb(plate, p):
        if (plate, p) not in cache:
            cache.clear()
            cache[(plate, p)] = render_page(PDF[plate], p, dpi=600).rgb
        return cache[(plate, p)]

    manifest = []
    for plate in ("litolff", "brahms"):
        d = json.load(open("%s.%s.json" % (pref, plate)))
        items = d["items"]
        arms = [a for a in ("B", "C")]
        cand = {a: [(i, it) for i, it in enumerate(items) if it["cover"].get(a)] for a in arms}
        picks = []
        for k in range(6):
            a = arms[k % 2]
            pool = [(i, it) for i, it in cand[a] if (it["cover"][a]["whole"] if k < 2 else True) and (a, i) not in [(x[0], x[1]) for x in picks]]
            if not pool:
                continue
            i, it = rng.choice(pool)
            picks.append((a, i, it))
        for n, (a, i, it) in enumerate(sorted(picks, key=lambda t: t[2]["page"])):
            rgb = page_rgb(plate, it["page"])
            cv = it["cover"][a]
            # window: the arm's box and the A box K (K only sets the window, it is not drawn)
            win = [cv["box"], it["K"]] + ([it["P"]] if it["P"] else [])
            h, w = rgb.shape[:2]
            sp = it["sp"]
            X0 = max(0, int(min(b[0] for b in win) - 1.5 * sp))
            Y0 = max(0, int(min(b[1] for b in win) - 2.0 * sp))
            X1 = min(w, int(max(b[2] for b in win) + 1.5 * sp))
            Y1 = min(h, int(max(b[3] for b in win) + 2.0 * sp))
            im = cv2.resize(rgb[Y0:Y1, X0:X1].copy(), None, fx=SC, fy=SC, interpolation=cv2.INTER_CUBIC)
            b = cv["box"]
            cv2.rectangle(im, (int((b[0] - X0) * SC), int((b[1] - Y0) * SC)), (int((b[2] - X0) * SC), int((b[3] - Y0) * SC)), (0, 0, 255), 1)
            name = "%s_p%d_%s_%s_%02d.png" % (plate, it["page"], a, "whole" if cv["whole"] else "far", n)
            cv2.imwrite(os.path.join(outdir, name), im)
            manifest.append(dict(file=name, arm=a, plate=plate, page=it["page"], bar=it["bar"], K=it["K"], arm_box=cv["box"], conf=cv["conf"], whole=cv["whole"], pair=bool(it["P"])))
        # new boxes
        for a in ("B", "C"):
            lst = d["newlist"][a]
            for n, x in enumerate(rng.sample(lst, min(5, len(lst)))):
                rgb = page_rgb(plate, x["page"])
                sp = 16.0
                b = x["box"]
                X0, Y0 = max(0, int(b[0] - 3 * sp)), max(0, int(b[1] - 3 * sp))
                X1, Y1 = min(rgb.shape[1], int(b[2] + 3 * sp)), min(rgb.shape[0], int(b[3] + 3 * sp))
                im = cv2.resize(rgb[Y0:Y1, X0:X1].copy(), None, fx=SC, fy=SC, interpolation=cv2.INTER_CUBIC)
                cv2.rectangle(im, (int((b[0] - X0) * SC), int((b[1] - Y0) * SC)), (int((b[2] - X0) * SC), int((b[3] - Y0) * SC)), (0, 0, 255), 1)
                name = "%s_p%d_%s_new%d_%s.png" % (plate, x["page"], a, n, x["cls"])
                cv2.imwrite(os.path.join(outdir, "newboxes", name), im)
                manifest.append(dict(file="newboxes/" + name, arm=a, plate=plate, page=x["page"], arm_box=b, cls=x["cls"], conf=x["conf"], on_A_glyph=x["on_A_glyph"]))
    json.dump(manifest, open(os.path.join(outdir, "manifest.json"), "w"), indent=1)
    print(len(manifest), "crops")


if __name__ == "__main__":
    main()
