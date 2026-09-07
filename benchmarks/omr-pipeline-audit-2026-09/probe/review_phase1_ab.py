"""Independent A/B of the barline-evidence change, PHASE 1 ONLY.

Targets the actual risk directly rather than a downstream proxy: if a barline
moved, or a cell boundary moved, the change altered a verdict. Needs no YOLO
weights, so it can cover many more pages than a full-transcribe arm.

Compared per page: staff count, each staff's (system, group, line_ys, x_start,
x_end), the sorted barline x list per system, and every cell's bbox_page_px +
canonical staff-line ys. Anything that moves is a behaviour change.
"""
import sys, json, hashlib
from pathlib import Path

tree, out_path, jobs_json = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tree)
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import detect_barlines, extract_measures

def fingerprint(pdf, page_index, dpi=600):
    pws = detect_barlines(detect_staves(render_page(pdf, page_index, dpi=dpi)))
    cells = extract_measures(pws)
    return {
        "n_staves": len(pws.staves),
        "staves": [[s.staff_index, s.system_index, s.group_index,
                    list(s.line_ys), s.x_start, s.x_end] for s in pws.staves],
        "barlines": sorted([b.system_index, b.x, b.y_top, b.y_bottom]
                           for b in pws.barlines),
        "cells": sorted([c.system_index, c.staff_index, c.measure_index,
                         list(c.bbox_page_px), list(c.staff_line_ys_canonical)]
                        for c in cells),
    }

res = {}
for name, pdf, pg in json.loads(Path(jobs_json).read_text()):
    try:
        res[name] = fingerprint(pdf, pg)
    except Exception as e:
        res[name] = {"ERROR": f"{type(e).__name__}: {e}"}
    print(f"  {name}: done", flush=True)
Path(out_path).write_text(json.dumps(res, sort_keys=True))
