"""Print beam boxes + notehead centres/levels for one staff's measures.

Usage: probe_measure.py <omr.json> <part-name-substring> [measure_index]
"""
import json
import sys

d = json.load(open(sys.argv[1]))
want = sys.argv[2].lower()
mwant = int(sys.argv[3]) if len(sys.argv) > 3 else None
for page in d['pages']:
    for s in page['systems']:
        for staff in s['staves']:
            label = (staff.get('part_name') or staff.get('label') or '')
            ctx = staff.get('contextual') or {}
            name = (label or ctx.get('part_name') or '')
            if want not in str(name).lower():
                continue
            print('staff', name)
            for m in staff['measures']:
                if mwant is not None and m['measure_index'] != mwant:
                    continue
                beams = [tuple(round(v, 1) for v in det['bbox_page'])
                         for det in m['detections']
                         if det.get('category') == 'structural'
                         and det.get('class') == 'beam']
                heads = [(round(det['bbox_page'][0] + det['bbox_page'][2] / 2),
                          round(det['bbox_page'][2]),
                          det.get('beam_levels'))
                         for det in m['detections']
                         if det.get('category') == 'notehead']
                print(' m', m['measure_index'], 'beams:', beams)
                print('   heads(cx,w,levels):', heads)
