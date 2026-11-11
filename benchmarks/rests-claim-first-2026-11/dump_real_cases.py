"""ROADMAP 2.288 round 4 -- turn Sean's answered rest tiles into REAL fixtures: during a normal page gather (flag `OMR_PAGE_CLAIM_RESTS` ON), after `gather_page_claim_boxes` has run, save for
every case of `real_cases.json` on the page the detector rest box(es) it meets, the page strokes round them (kind, box, size, what they touch, their pixel masks) and the page raster crop,
so that `tools/omr/tests/test_rests_real_cases_2_288_r4.py` replays the box through the very function the gather calls (`page_claim_names.rest_box_verdict`) with no gather.
Also writes, for EVERY rest-family box on the page, the verdict and the two shared measures (`diag`), so a lane can count a signature without re-gathering.

    OMR_PAGE_CLAIM_RESTS=1 python3 benchmarks/rests-claim-first-2026-11/dump_real_cases.py OUT_DIR PDF PAGES [--cell-map DIR] [--detector-cache DIR] [-- extra args of tools.omr.staged]

Writes OUT_DIR/cases/<case id>.npz (arrays: meta = json text, raw = binary crop, m_<ordinal> = masks) and OUT_DIR/diag-p<page>.json. Never edits the pipeline: it wraps one function in-process."""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, ".")
HERE = pathlib.Path(__file__).parent
CASES = json.load(open(HERE / "real_cases.json"))
KEYS = ("kind", "box", "area_sp2", "length_sp", "angle_deg", "thickness_sp", "thickness_spread_sp", "staff_space_local", "fill", "component")


def overlap(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    return w * h / float(min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


def install(out_dir, plate_hint):
    from tools.omr.staged import page_claim_names as PCN
    from tools.omr.staged import ink_attachment as IA
    from tools.omr.staged import stroke_map as SM
    from tools.omr.staged import record as R
    from tools.omr.staged.record import Q
    orig = PCN.gather_page_claim_boxes
    out = pathlib.Path(out_dir)
    (out / "cases").mkdir(parents=True, exist_ok=True)

    def wrapped(log, pws, cells, local, detections, page_map, **kw):
        res = orig(log, pws, cells, local, detections, page_map, **kw)
        if page_map is None or not getattr(page_map, "strokes", None) or detections is None:
            return res
        p = int(getattr(pws.page, "page_index", 0))
        raw = pws.page.binary
        index = PCN.StrokeIndex(*PCN._boxes_of(page_map))
        diag = []
        s = float(page_map.scale)
        for c in cells:
            key = local.get(c.staff_index)
            rect, up = getattr(c, "bbox_page_px", None), getattr(c, "upscale_factor", None)
            if key is None or not rect or not up:
                continue
            csub = R.cell(c.page_index, key[0], key[1], c.measure_index)
            for gi, d in enumerate(detections.get(csub.to_key()) or ()):
                cls = str(getattr(d, "smufl_name", ""))
                owner = PCN.box_owner(cls, getattr(d, "category", None), True)
                if owner not in PCN.REST_FAMILIES:
                    continue
                x, y, w, h = float(d.x_canonical), float(d.y_canonical), float(d.width_canonical), float(d.height_canonical)
                pb = (rect[0] + x / up, rect[1] + y / up, rect[0] + (x + w) / up, rect[1] + (y + h) / up)
                rr = log.rows(Q.REST_INK_CONTACT, R.glyph(c.page_index, key[0], key[1], c.measure_index, gi))
                detail = rr[-1].detail if rr else None
                v = PCN.rest_box_verdict(page_map, index, raw, pb, cls, owner, detail)
                diag.append(dict(cls=cls, box=[round(q, 1) for q in pb], cell=csub.to_key(), standing=v["standing"], why=v["why"], ids=v["ids"],
                                 attachment=v["attachment"], sides=({k: v["sides"][k] for k in ("both_sides", "two_lines")} if v["sides"] else None),
                                 own_h_sp=[PCN.own_block_height_sp(page_map, i, raw) for i in v["ids"]]))
                for cs in CASES:
                    if cs["page"] != p or cs["plate"] != plate_hint or overlap(pb, cs["box"]) < 0.5:
                        continue
                    sp_px = float(next((getattr(page_map.strokes[i], "staff_space_local", None) for i in v["ids"] if i < len(page_map.strokes)), None) or page_map.sp)
                    reg = (pb[0] - 4 * sp_px, pb[1] - 4 * sp_px, pb[2] + 4 * sp_px, pb[3] + 4 * sp_px)
                    near = [i for i in index.meeting(reg) if i < len(page_map.strokes)]
                    keep = set(near)
                    for i in near:
                        keep.update(j for j in IA.neighbours(page_map, i) if 0 <= j < len(page_map.strokes))
                    arrays, strokes = {}, {}
                    x0 = y0 = 10 ** 9
                    x1 = y1 = 0
                    for i in sorted(keep):
                        st = page_map.strokes[i]
                        strokes[str(i)] = {k: (list(getattr(st, k)) if k == "box" else getattr(st, k, None)) for k in KEYS}
                        strokes[str(i)]["touches"] = [[int(j), float(cc)] for j, cc in (st.touches or ())]
                        strokes[str(i)]["joined_to"] = [[int(j), str(h_)] for j, h_ in (st.joined_to or ())]
                        m, mx, my = page_map.masks[i]
                        arrays["m_%d" % i] = np.asarray(m, dtype=bool)
                        strokes[str(i)]["mask_xy"] = [int(mx), int(my)]
                        bx, by, bw, bh = st.box
                        x0, y0, x1, y1 = min(x0, int(bx)), min(y0, int(by)), max(x1, int(bx + bw)), max(y1, int(by + bh))
                    x0, y0 = max(0, x0 - 10), max(0, y0 - 10)
                    x1, y1 = min(raw.shape[1], x1 + 10), min(raw.shape[0], y1 + 10)
                    meta = dict(case=cs["id"], plate=cs["plate"], page=p, cell=csub.to_key(), cls=cls, owner=owner, box=list(pb), detail=detail, scale=s, sp=float(page_map.sp),
                                page_shape=list(raw.shape), raw_origin=[x0, y0], strokes=strokes, sean=cs["sean"], is_rest=cs["is_rest"],
                                verdict=dict(standing=v["standing"], why=v["why"], ids=v["ids"]))
                    np.savez_compressed(out / "cases" / (cs["id"] + ".npz"), meta=np.array(json.dumps(meta)), raw=np.asarray(raw[y0:y1, x0:x1], dtype=np.uint8), **arrays)
        (out / ("diag-p%d.json" % p)).write_text(json.dumps(diag))
        return res

    PCN.gather_page_claim_boxes = wrapped


def main():
    argv = sys.argv[1:]
    out_dir, pdf, pages = argv[0], argv[1], argv[2]
    plate = "brahms" if "brahms" in pdf.lower() else "litolff"
    rest = argv[3:]
    install(out_dir, plate)
    from tools.omr.staged.__main__ import main as staged_main
    sys.exit(staged_main([pdf, "--pages", pages, "--dpi", "600", "--weights", "auto", "--route-weights", "--out", str(pathlib.Path(out_dir) / "gathered.record.json")] + rest))


if __name__ == "__main__":
    main()
