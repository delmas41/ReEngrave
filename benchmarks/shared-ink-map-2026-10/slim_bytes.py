"""ROADMAP 2.198: bytes a page of the `Q.STROKE` rows, 2.195 form vs the slimmed form, on the SAME strokes (the map re-run on the page raster, no detector).
usage: slim_bytes.py PLATE PAGE [PAGE...]   -> per page: rows, compact-JSON bytes of the observation rows OLD / NEW (the file is written compact).
The OLD form is the 2.195 `gather_stroke_map` filing copied here verbatim; the NEW form is the real `gather.gather_stroke_map`. Control: the NEW bytes of a page
are compared by the caller with the same page's stroke rows in a gathered ON record (`record_bytes`)."""
import json, os, sys
sys.path.insert(0, ".")
from tools.omr.staged import pipeline, gather as G, stroke_map as SM
from tools.omr.staged.record import Q, READERS, ABSTAIN
R = G.R
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDF = {"litolff": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}


def old_form(log, cells, local):
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        frame = G.frame_cell(c.measure_index)
        grid = G._cell_grid(c)
        if getattr(c, "image_no_staff", None) is None or grid is None:
            continue
        res = SM.map_strokes(c.image_no_staff, grid[1] * 2.0, list(getattr(c, "staff_line_ys_canonical", None) or []), getattr(c, "binary", None))
        if res is None or not res.strokes:
            continue
        up, cell_box = getattr(c, "upscale_factor", None), getattr(c, "bbox_page_px", None)
        page_ok = bool(up) and bool(cell_box) and len(cell_box or ()) == 4
        for i, st in enumerate(res.strokes):
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, G._STROKE_GLYPH_BASE + i)
            optional = {}
            if st.sagitta_sp is not None:
                optional["sagitta_spaces"] = st.sagitta_sp
            if st.hole_share is not None:
                optional["hole_share"] = st.hole_share
            if st.lines_right != st.lines_left:
                optional["staff_lines_right"] = st.lines_right
            if page_ok:
                x, y, w, h = st.box
                optional["bbox_page_px"] = [round(cell_box[0] + x / up, 1), round(cell_box[1] + y / up, 1),
                                            round(cell_box[0] + (x + w) / up, 1), round(cell_box[1] + (y + h) / up, 1)]
            log.observe(g, Q.STROKE, st.kind, reader=READERS.CV_STROKE, frame=frame,
                        stroke_box=list(st.box), area_sp2=st.area_sp2, length_spaces=st.length_sp, angle_deg=st.angle_deg,
                        thickness_spaces=st.thickness_sp, thickness_spread_spaces=st.thickness_spread_sp, fill=st.fill,
                        ends=[list(st.ends[0]), list(st.ends[1])], end_steps_from_top=list(st.end_steps),
                        profile_sixteenths=st.profile, touches=[[j, ct] for j, ct in st.touches],
                        component=st.component, component_n_strokes=st.component_n_strokes,
                        staff_lines_left=st.lines_left, staff_space_local_px=st.staff_space_local,
                        staff_local=res.staff_local, cell_n_below_floor=res.n_below_floor, **optional)


def nbytes(log):
    d = log.to_json()
    obs = [o for o in d["observations"] if o["quantity"] == "stroke"]
    return len(obs), len(json.dumps(obs, separators=(",", ":"), default=str))


if __name__ == "__main__":
    os.environ[G.STROKE_MAP_ENV] = "1"
    plate = sys.argv[1]
    tot = [0, 0, 0]
    for pg in map(int, sys.argv[2:]):
        pws, cells = pipeline.prepare_pages(PDF[plate], [pg], dpi=600)[0]
        loc = G.gather_geometry(G.Log(), pws)
        lo, ln = G.Log(), G.Log()
        old_form(lo, cells, loc)
        G.gather_stroke_map(ln, cells, loc)
        (n0, b0), (n1, b1) = nbytes(lo), nbytes(ln)
        print("%s page %d: rows %d/%d  OLD %d B  NEW %d B  (%.1f%%)" % (plate, pg, n0, n1, b0, b1, 100.0 * (b1 - b0) / b0), flush=True)
        tot = [tot[0] + n1, tot[1] + b0, tot[2] + b1]
    print("%s TOTAL rows %d OLD %d B NEW %d B  saved %.1f%%  | per page OLD %.2f MB NEW %.2f MB" % (
        plate, tot[0], tot[1], tot[2], 100.0 * (tot[1] - tot[2]) / tot[1], tot[1] / 1e6 / (len(sys.argv) - 2), tot[2] / 1e6 / (len(sys.argv) - 2)))
