"""frame-drop experiments. Arms (all: FarHeadPage, scorer's page shape, record boxes):
  A    fitz render, UNDESKEWED raster, boxes/lines left in the DESKEWED frame (the scorers' arm; frames disagree)
  B    gather raster (deskewed), boxes/lines as recorded (frames agree)             (the product)
  A2   undeskewed raster, boxes and staff lines MAPPED into the undeskewed frame (frames agree)
  B-nn/B-cub/B-lanczos  deskew the fitz gray ourselves with another interpolation (frames agree)
"""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np, cv2
import frame_drop_arms as F
import edge_census as ec


def rot(L):
    h, w = L["gray_A"].shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), L["pi"].skew_correction_deg, 1.0)
    return M, cv2.invertAffineTransform(M)


def map_pt(Mi, x, y):
    return (Mi[0, 0] * x + Mi[0, 1] * y + Mi[0, 2], Mi[1, 0] * x + Mi[1, 1] * y + Mi[1, 2])


def mapped(L, Mi):
    """heads / page_boxes / staff_lines moved from the deskewed frame to the original raster frame."""
    def mbox(b):
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        nx, ny = map_pt(Mi, cx, cy)
        return (b[0] + nx - cx, b[1] + ny - cy, b[2] + nx - cx, b[3] + ny - cy)

    def mlines(b, lines):
        cx = (b[0] + b[2]) / 2
        return [map_pt(Mi, cx, y)[1] for y in lines]
    heads = [dict(h, box=mbox(h["box"]), global_lines=mlines(h["box"], h["global_lines"])) for h in L["heads"]]
    pbs = [(s, c, mbox(b)) for (s, c, b) in L["page_boxes"]]
    sl = {k: [map_pt(Mi, L["gray_A"].shape[1] / 2, y)[1] for y in v] for k, v in L["staff_lines"].items()}
    return heads, pbs, sl, mbox, mlines


def read_arm(L, gray, heads, pbs, sl, far_map, shape):
    fp = F.FH.FarHeadPage(gray, heads, pbs, sl)
    fp.adopt(shape, "scorer")
    out = {}
    for h in L["D"]["far"]:
        if h["page"] != F.PAGE:
            continue
        box, lines = far_map(h)
        r = fp.read(h["subject"], box, h["cls"], lines)
        out[h["subject"]] = dict(r, v=ec.verdict(r["pos"], h["truth"]), truth=h["truth"])
    return out, fp


def run(L=None):
    L = L or F.load()
    shp = L["D"]["shapes"][F.PAGE]
    shape = dict(width_sp=shp["width_sp"], height_sp=shp["height_sp"], tilt_deg=shp["tilt_deg"])
    sk = lambda s: "staff/" + "/".join(s.split("/")[1:4])
    ident = lambda h: (h["box"], L["staff_lines"][sk(h["subject"])])
    res = {}
    res["A"], _ = read_arm(L, L["gray_A"], L["heads"], L["page_boxes"], L["staff_lines"], ident, shape)
    res["B"], _ = read_arm(L, L["gray_B"], L["heads"], L["page_boxes"], L["staff_lines"], ident, shape)
    M, Mi = rot(L)
    heads2, pbs2, sl2, mbox, mlines = mapped(L, Mi)

    def far2(h):
        return mbox(h["box"]), mlines(h["box"], L["staff_lines"][sk(h["subject"])])
    res["A2"], _ = read_arm(L, L["gray_A"], heads2, pbs2, sl2, far2, shape)
    h_, w_ = L["gray_A"].shape
    for name, flag in (("B-nn", cv2.INTER_NEAREST), ("B-cub", cv2.INTER_CUBIC), ("B-lanczos", cv2.INTER_LANCZOS4)):
        g = cv2.warpAffine(L["gray_A"], M, (w_, h_), flags=flag, borderMode=cv2.BORDER_CONSTANT, borderValue=255)
        res[name], _ = read_arm(L, g, L["heads"], L["page_boxes"], L["staff_lines"], ident, shape)
    return L, res


if __name__ == "__main__":
    L, res = run()
    SEAN = {"glyph/3/0/0/6/2": [-6]}
    for k, r in res.items():
        vs = [ec.verdict(x["pos"], SEAN.get(s, x["truth"])) for s, x in r.items()]
        print(f"{k:10} as scored {ec.tally([x['v'] for x in r.values()])}   vs Sean {ec.tally(vs)}")
    subs = list(res["A"])
    print("\nheads where any arm differs:")
    for s in subs:
        reads = {k: (res[k][s]["pos"]) for k in res}
        if len(set(reads.values())) > 1:
            print(s, "ref", res["A"][s]["truth"], reads)
