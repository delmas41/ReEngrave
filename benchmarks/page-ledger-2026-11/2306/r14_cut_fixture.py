"""2.306 r14: cut the fast-tier fixture for the flag rule from a REAL record -- the beam-grouping call's input (each voice's events: head glyph,
page box, beam level; the cell's beam boxes in page px) and each head's duration detail (flag / beam evidence), for the named cells.
Usage (cwd = tree, OMR_PAGE_STEMS=1): r14_cut_fixture.py REC.json OUT.json cell/0/0/1/6 cell/0/0/0/3 ..."""
import json
import sys

from tools.omr.staged import export as E
from tools.omr.staged.record_io import load_record

res = load_record(sys.argv[1])
want = set(sys.argv[3:])
out = {}
orig = E._annotate_beams_for
KEEP = ("flags_attached", "flag_levels", "beams_by_stem", "levels_certain", "levels_possible")


def tap(rec, run, cell_index, stream, counters):
    key = E.R_cell_key(run, cell_index)
    if key in want:
        cell = run.cells.get(cell_index)
        boxes = (getattr(rec, "_beam_box_cache", None) or E._beam_boxes_by_cell(rec)).get(key) or []
        dets = E._beam_detections_page(cell, boxes) if cell is not None and boxes else []
        evs = []
        for ev in stream:
            hs = []
            for h in ev.get("noteheads") or ():
                d = ((rec.verdict(E.Q.DURATION, h.get("glyph")) or {}).get("detail")) or {}
                hs.append(dict(glyph=h.get("glyph"), bbox_page=h.get("bbox_page"), beam_levels=h.get("beam_levels"),
                               duration_detail={k: d.get(k) for k in KEEP if k in d}))
            evs.append(dict(kind=ev.get("kind"), noteheads=hs))
        out.setdefault(key, []).append(dict(events=evs, dets=[dict(category=d["category"], **{"class": d["class"]}, bbox_page=d["bbox_page"]) for d in dets]))
    return orig(rec, run, cell_index, stream, counters)


E._annotate_beams_for = tap
E.to_musicxml(res)
json.dump(out, open(sys.argv[2], "w"), indent=1)
print({k: len(v) for k, v in out.items()})
