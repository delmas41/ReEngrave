"""usage: python3 showrec.py DOC PAGE SUBJECT_PREFIX   -- print the record's glyph_box rows."""
import sys
sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import recordrows as rr

doc, pg, pre = sys.argv[1], int(sys.argv[2]), sys.argv[3]
for o in rr.rows(doc, pg, subject_prefix=pre):
    print(o['subject'], o['value'][0], o['reader'], o['score'] and round(o['score'], 3), [round(v) for v in o['detail'].get('bbox_page_px', [])],
          {k: v for k, v in o['detail'].items() if k not in ('bbox_page_px', 'x_center_page', 'y_center_page', 'category')})
