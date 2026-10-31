"""Why the hairpin witness is (nearly) silent: for each hairpin span between two staves, how many head marks stand in its x span, how many of those in the
stretch of the two staves, how many outside both staves' bands, how many wholly above / below its rows.
    python3 benchmarks/page-ledger-2026-10/s3/hairpin_diag.py REC PAGES"""
import collections
import sys

from tools.omr.staged import cell_map as CM
from tools.omr.staged import claim_readout as CR
from tools.omr.staged import page_marks as PM
from tools.omr.staged import page_owner as PO

rec, pages = sys.argv[1], [int(p) for p in sys.argv[2].split(",")]
src = CR.resolve_source(rec)
rows_all = CR.read_rows(src, pages)
pdf = CR.LIB / CR.edition_info(rows_all)["edition_path"]
tot = collections.Counter()
for pg in pages:
    prows = {k: [r for r in v if CR.page_of_subject(r.get("subject", "")) in (None, pg)] for k, v in rows_all.items()}
    pws, cells, local, views, _v = PM.page_views(prows, pdf, pg, CM.ROOT_DEFAULT)
    ink = pws.page.binary == 0
    boxes = PM.boxes_from_rows(prows, pg, cells, local, views, ink)
    marks = PM.link(boxes, pieces=True)
    frames = PO.staff_frames(cells, local)
    sp = PO.page_spans(marks, boxes, PO._rows_of(prows, "system_arc"), PO._rows_of(prows, "wedge_box"))
    own = PO.owners(marks, boxes, frames, PO.SliceRows(prows), ())
    hps = PO.hairpin_boxes(sp["spans"])
    heads = [(r["box"], r) for r in own.values() if r["family"] == "head"]
    for hb in hps:
        tot["hairpins"] += 1
        sys_of = None
        for k in frames:
            b = PO.lines_at(frames, k, (hb[0] + hb[2]) / 2.0)
            if b is not None and b.ys[0] - 4 * b.sp <= (hb[1] + hb[3]) / 2.0 <= b.ys[-1] + 4 * b.sp:
                sys_of = "/".join(k.split("/")[:3]) + "/"
        br = PO.bracketing(frames, sys_of, (hb[0] + hb[2]) / 2.0, (hb[1] + hb[3]) / 2.0) if sys_of else []
        if len(br) != 2:
            tot["hairpin_not_between_two_staves"] += 1
            continue
        tot["hairpin_between_two_staves"] += 1
        up, dn = PO.lines_at(frames, br[0], (hb[0] + hb[2]) / 2.0), PO.lines_at(frames, br[1], (hb[0] + hb[2]) / 2.0)
        for bx, r in heads:
            cx, cy = (bx[0] + bx[2]) / 2.0, (bx[1] + bx[3]) / 2.0
            if not (hb[0] <= cx <= hb[2]) or PO._staff_of_glyph(r["members"][0]) not in br:
                continue
            tot["heads_in_x_span_of_the_system"] += 1
            if not (up.ys[0] <= cy <= dn.ys[-1]):
                continue
            tot["... in the stretch"] += 1
            if r["reason"] == "inside_staff":
                tot["... but inside a staff's band (rule 1 decides)"] += 1
                continue
            if bx[3] < hb[1] or bx[1] > hb[3]:
                tot["... outside the bands and wholly above/below the hairpin: the witness speaks"] += 1
            else:
                tot["... outside the bands, level with the hairpin: silent"] += 1
    del pws, cells, views, ink
print(dict(tot))
