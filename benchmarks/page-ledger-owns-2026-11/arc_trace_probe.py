"""2.283 probe (READ-ONLY): why does the ARC claim hold head ink?  usage: arc_trace_probe.py SLICE_DIR PAGE [PAGE ...] > out.json

For every stroke of every cell that the register's arc claim names (Q.CLAIMED_AREA owner arc, unit ink: value [[cell, ordinal]], detail.shares = the
share of the STROKE's ink that lies along the traced curve), measure: the stroke's ink (px, reduced frame), the share on the trace, the OFF-trace ink
the claim takes anyway, and the detector head boxes whose strokes include this stroke (glyph_strokes), with the box's share of that stroke.
Uses claim_readout's own readers (read_rows, the master cell map, stroke_map.map_strokes re-cut and matched against the record). Files nothing.
"""
import collections
import json
import os
import pathlib
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import claim_readout as CR              # noqa: E402
from tools.omr.staged import cell_map as CM                   # noqa: E402
from tools.omr.staged import gather as G                      # noqa: E402
from tools.omr.staged import stroke_map as SM                 # noqa: E402

src = pathlib.Path(sys.argv[1])
pages = [int(p) for p in sys.argv[2:]]
rows = CR.read_rows(src, pages)
ed = CR.edition_info(rows)
pdf = CR.LIB / ed["edition_path"]
out = []
for page in pages:
    obs = [o for o in rows["observations"] if CR.page_of_subject(o.get("subject", "")) in (None, page)]
    arc = {}                                    # (page,sys,staff,cell,ord) -> share of the stroke's ink on the trace
    for o in obs:
        d = o.get("detail") or {}
        if o["quantity"] == "claimed_area" and d.get("owner") == "arc" and d.get("unit") == "ink":
            p = o["subject"].split("/")
            for (cell, ordinal), sh in zip(o["value"], d.get("shares") or []):
                arc[(int(p[1]), int(p[2]), int(p[3]), int(cell), int(ordinal))] = sh
    boxes = {o["subject"]: o["value"][0] for o in obs if o["quantity"] == "glyph_box"}
    gs = collections.defaultdict(list)          # (page,sys,staff,cell,ord) -> [(box subject, class, box's share of the stroke's ink)]
    for o in obs:
        if o["quantity"] == "glyph_strokes" and o["subject"] in boxes:
            p = o["subject"].split("/")
            for ordinal, sh in zip(o["value"], (o.get("detail") or {}).get("shares") or []):
                gs[(int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(ordinal))].append((o["subject"], boxes[o["subject"]], sh))
    rec_boxes = collections.defaultdict(dict)
    keep_whole, touch = {}, {}
    for o in obs:
        if o.get("quantity") == "stroke":
            g = int(o["subject"].split("/")[5])
            if g >= CR.STROKE_BASE:
                ck = CR.cell_key(o["subject"])
                rec_boxes[ck][g - CR.STROKE_BASE] = (o.get("detail") or {}).get("stroke_box")
                if (o.get("detail") or {}).get("cell_keep_whole"):
                    keep_whole[ck] = o["detail"]["cell_keep_whole"]
                if (o.get("detail") or {}).get("cell_touch_boxes"):
                    touch[ck] = o["detail"]["cell_touch_boxes"]
    (pws, cells), = CM.load_prepared(pdf, [page], root=CM.ROOT_DEFAULT)
    local = G._system_local(pws.staves)
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        ck = (c.page_index, key[0], key[1], c.measure_index)
        grid = G._cell_grid(c)
        img = getattr(c, "image_no_staff", None)
        if grid is None or img is None:
            continue
        if not any(k[:4] == ck for k in arc):
            continue
        res = SM.map_strokes(img, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None),
                             keep_whole=keep_whole.get(ck, ()), touch_boxes=touch.get(ck, ()))
        if not res or {i: list(s.box) for i, s in enumerate(res.strokes)} != {i: list(b) for i, b in rec_boxes.get(ck, {}).items()}:
            out.append({"page": page, "cell": list(ck), "mismatch": True})
            continue
        spc = float(res.sp_canonical)
        for i, (m, x0, y0) in enumerate(res.masks):
            k = ck + (i,)
            if k not in arc:
                continue
            ink = int(m.sum())
            x, y, w, h = res.strokes[i].box
            heads = [(s, cl, round(sh, 3)) for (s, cl, sh) in gs.get(k, []) if cl.startswith("notehead")]
            up = float(c.upscale_factor)
            pb = [round(c.bbox_page_px[0] + x / up), round(c.bbox_page_px[1] + y / up), round(c.bbox_page_px[0] + (x + w) / up), round(c.bbox_page_px[1] + (y + h) / up)]
            out.append({"page": page, "cell": list(ck), "ord": i, "page_box": pb, "ink": ink, "trace_share": arc[k], "off_trace_ink": round(ink * (1 - arc[k])),
                        "w_sp": round(w / spc, 2), "h_sp": round(h / spc, 2), "shape": res.strokes[i].kind, "touches": bool(res.strokes[i].touches),
                        "heads": heads, "other_boxes": [(cl, round(sh, 3)) for (s, cl, sh) in gs.get(k, []) if not cl.startswith("notehead")]})
json.dump(out, sys.stdout)
