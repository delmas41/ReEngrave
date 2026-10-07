"""lane-arc-not-a-line (STAGED, GATHER only, READ ONLY): re-measure `Q.ARC_INK_SHAPE` for EVERY arc of a shared record by calling the REAL
`gather.gather_arc_ink` on the page's own raster and staves (`detect_staves(render_page(...))`, the production recipe's first step; no
detector run -- the arc boxes come out of the record's own `arc_box` rows, in page pixels).

  python3 arc_line_replay.py <pkl from arc_line_extract.py> <pdf> <out.json>

CONTROLS (must be able to fail):
  (a) the fresh page's staff lines must equal the record's own `staff_lines` (max |diff| <= 1 px) -- the frame is the record's;
  (b) the SAME arcs re-measured with every box shifted 2 staff spaces DOWN must read differently (a measurement that does not move when
      the box moves is a constant); the mean coverage of both is printed per page-run.
Any (a) mismatch means nothing else here is evidence."""
import json, pickle, sys, collections, types
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log


def measure(pws, local, arcs_by_cell, sp_of, shift_sp=0.0):
    cells, dets = [], {}
    inv = {v: k for k, v in local.items()}
    for (page, s, st, ci), gis in arcs_by_cell.items():
        sp = sp_of[(page, s, st)]
        cells.append(types.SimpleNamespace(
            page_index=page, staff_index=inv[(s, st)], measure_index=ci, bbox_page_px=(0.0, 0.0, 1.0, 1.0), upscale_factor=1.0,
            staff_line_ys_canonical=[i * sp for i in range(5)]))
        n_g = max(gis) + 1
        dets[R.cell(page, s, st, ci).to_key()] = [gis[i] if i in gis else types.SimpleNamespace(smufl_name='x') for i in range(n_g)]
        for gi, o in gis.items():
            b = o['detail']['bbox_page_px']
            dy = shift_sp * sp
            gis[gi] = o
            dets[R.cell(page, s, st, ci).to_key()][gi] = types.SimpleNamespace(
                smufl_name=o['value'], x_canonical=b[0], y_canonical=b[1] + dy, width_canonical=b[2] - b[0], height_canonical=b[3] - b[1])
    log = Log()
    G.gather_arc_ink(log, pws, cells, local, dets)
    out = {}
    for o in log._obs.values():
        if o.quantity == R.Q.ARC_INK_SHAPE:
            out[o.subject.to_key()] = dict(coverage=o.value, **{k: (o.detail or {})[k] for k in ('tall_cols', 'lines_in_box', 'width_spaces', 'height_spaces')})
    return out


def main(pkl, pdf, out):
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    d = pickle.load(open(pkl, 'rb'))
    arcs = [o for o in d['obs'] if o['quantity'] == 'arc_box' and o['detail'].get('bbox_page_px')]
    rec_lines = {o['subject']: [float(v) for v in o['value']] for o in d['obs'] if o['quantity'] == 'staff_lines'}
    rec_sp = {o['subject']: float(o['value']) for o in d['obs'] if o['quantity'] == 'staff_spacing'}
    by_page = collections.defaultdict(list)
    for o in arcs:
        by_page[int(o['subject'].split('/')[1])].append(o)
    res, bad_lines, shifted = {}, [], []
    for page in sorted(by_page):
        pws = detect_staves(render_page(pdf, page, dpi=600))
        local = G._system_local(pws.staves)
        for st in pws.staves:
            k = 'staff/%d/%d/%d' % ((page,) + local[st.staff_index])
            if k in rec_lines and max(abs(a - b) for a, b in zip(rec_lines[k], st.line_ys)) > 1.0:
                bad_lines.append(k)
        arcs_by_cell, sp_of = collections.defaultdict(dict), {}
        for o in by_page[page]:
            _, p, s, st, ci, gi = o['subject'].split('/')
            sk = 'staff/%s/%s/%s' % (p, s, st)
            if sk not in rec_sp:
                continue
            sp_of[(int(p), int(s), int(st))] = rec_sp[sk]
            arcs_by_cell[(int(p), int(s), int(st), int(ci))][int(gi)] = o
        sh = measure(pws, local, {k: dict(v) for k, v in arcs_by_cell.items()}, sp_of, shift_sp=2.0)
        r = measure(pws, local, arcs_by_cell, sp_of)
        res.update(r)
        common = [a for a in r if a in sh]
        shifted.append((sum(r[a]['coverage'] for a in common) / max(1, len(common)), sum(sh[a]['coverage'] for a in common) / max(1, len(common)),
                        sum(1 for a in common if abs(r[a]['coverage'] - sh[a]['coverage']) > 0.05), len(common)))
        print('page', page, 'arcs', len(by_page[page]), 'measured so far', len(res), 'mean coverage real/shifted %.3f/%.3f' % shifted[-1][:2], flush=True)
    moved = sum(s[2] for s in shifted)
    tot = sum(s[3] for s in shifted)
    print('CONTROL (a) staff-line mismatches:', len(bad_lines), bad_lines[:3], '| CONTROL (b) arcs whose reading moved when the box moved 2 spaces:', moved, 'of', tot)
    json.dump(dict(rows=res, bad_lines=bad_lines, arcs=len(arcs), control_b_moved=moved, control_b_total=tot), open(out, 'w'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
