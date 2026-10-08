from tools.omr.staged import record_io
import sys

path = sys.argv[1]
d = record_io.load_record(path)
obs = d['record']['observations']
cellbox = {r['subject']: r['value'] for r in obs if r.get('quantity') == 'cell_box'}
ink = [r for r in obs if r.get('quantity') == 'ink' and isinstance(r.get('detail'), dict)
       and 'ink_bbox_canonical' in r['detail']]


def cell_key_of(subj):
    parts = subj.split('/')
    return '/'.join(['cell'] + parts[1:5])


near_edge = 0
total_line_like = 0
for r in ink:
    d2 = r['detail']
    cov = d2.get('ink_detector_coverage', 0.0)
    w, h = d2.get('width_spaces'), d2.get('height_spaces')
    if w is None or h is None:
        continue
    if not (w > 0 and h > 0 and (w / h >= 3.0 or h / w >= 3.0)):
        continue
    if cov > 0.1:
        continue
    total_line_like += 1
    cb = cellbox.get(cell_key_of(r['subject']))
    if cb is None:
        continue
    pb = d2.get('bbox_page_px')
    if pb is None:
        continue
    tol = 20
    if abs(pb[0] - cb[0]) <= tol or abs(pb[2] - cb[2]) <= tol:
        near_edge += 1
print('total line_like(cov<0.1)', total_line_like, 'near cell edge', near_edge)
