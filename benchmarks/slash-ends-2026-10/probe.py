"""ROADMAP 2.214 step 1 (read-only): cut the cell under a page-px box, run the stroke map, and dump every non-vertical stroke the box
covers (>= COVER_SHARE_MIN of its ink inside) with its full-res mask, so outline measures can be tried on it.
usage: probe.py CASES.json OUT.pkl      CASES = [{"id","plate","page","box":[x0,y0,x1,y1],"label"}]"""
import json, pickle, sys
sys.path.insert(0, ".")
import cv2, numpy as np
from tools.omr.staged import pipeline, gather as G, stroke_map as S
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDF = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}

def cut(plate, page, cache):
    k = (plate, page)
    if k not in cache:
        pws, cells = pipeline.prepare_pages(PDF[plate], [page], dpi=600)[0]
        cache[k] = (cells, G.gather_geometry(G.Log(), pws))
    return cache[k]

def fullres_mask(res, i, shape, erased):
    """the stroke's mask back at canonical px: reduced mask upsampled, AND the real ink (so edges come from the raster)"""
    m, x0, y0 = res.masks[i]
    inv = 1.0 / res.scale
    big = np.zeros(shape, np.uint8)
    h, w = m.shape
    X0, Y0 = int(round(x0 * inv)), int(round(y0 * inv))
    up = cv2.resize(m.astype(np.uint8), (int(round(w * inv)), int(round(h * inv))), interpolation=cv2.INTER_NEAREST)
    # pad one reduced pixel of slack, then keep only real ink
    up = cv2.dilate(up, np.ones((3, 3), np.uint8))
    hh, ww = up.shape
    y1, x1 = min(shape[0], Y0 + hh), min(shape[1], X0 + ww)
    big[max(0, Y0):y1, max(0, X0):x1] = up[max(0, -Y0):y1 - Y0, max(0, -X0):x1 - X0]
    return (big.astype(bool) & (erased == 0))

def main():
    cases = json.load(open(sys.argv[1]))
    cache, out = {}, []
    for c in cases:
        cells, loc = cut(c["plate"], c["page"], cache)
        bx = c["box"]
        found = None
        for cell in cells:
            cb, up = getattr(cell, "bbox_page_px", None), getattr(cell, "upscale_factor", None)
            if not cb or not up:
                continue
            if cb[0] <= (bx[0] + bx[2]) / 2 <= cb[2] and cb[1] <= (bx[1] + bx[3]) / 2 <= cb[3]:
                found = cell
                break
        if found is None:
            print("NO CELL", c["id"]); continue
        cb, up = found.bbox_page_px, found.upscale_factor
        canon = [(bx[0] - cb[0]) * up, (bx[1] - cb[1]) * up, (bx[2] - cb[0]) * up, (bx[3] - cb[1]) * up]
        g = G._cell_grid(found)
        res = S.map_strokes(found.image_no_staff, g[1] * 2.0, found.staff_line_ys_canonical, found.binary)
        got = [(i, sh) for i, sh in S.strokes_in_box(res, canon) if sh >= S.COVER_SHARE_MIN]
        rec = dict(c, canon=canon, sp=g[1] * 2.0, image=found.image_no_staff.copy(), strokes=[])
        for i, sh in S.strokes_in_box(res, canon):
            st = res.strokes[i]
            rec["strokes"].append(dict(i=i, share=sh, kind=st.kind, box=st.box, length_sp=st.length_sp, thick=st.thickness_sp,
                                       angle=st.angle_deg, area=st.area_sp2, touches=st.touches,
                                       mask=fullres_mask(res, i, found.image_no_staff.shape, found.image_no_staff)))
        rec["all"] = [(s.kind, s.box) for s in res.strokes]
        out.append(rec)
        print(c["id"], c["label"], [(s["i"], s["kind"], s["share"], s["length_sp"], s["thick"], s["angle"]) for s in rec["strokes"]])
    pickle.dump(out, open(sys.argv[2], "wb"))
main()
