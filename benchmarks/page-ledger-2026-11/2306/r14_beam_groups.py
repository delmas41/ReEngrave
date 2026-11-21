"""2.306 r14: how the exporter grouped each written short note under a beam -- under a read beam box, or in a SYNTHETIC run (consecutive notes
that carry a level and sit under no box; `export.annotate_beams`), or not grouped. Taps `annotate_beams` (reads only). Run from the tree that
made the record, with its flags.

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-11/2306/r14_beam_groups.py REC.record.json OUT.json
"""
import json
import sys

from tools.omr.staged import export as E
from tools.omr import export as L
from tools.omr.staged.record_io import load_record

res = load_record(sys.argv[1])
out = {}
orig_pick = L._pick_beam_box
orig = L.annotate_beams


picks = {}


def tap_pick(c, boxes, suspect, nh_width):
    bi = orig_pick(c, boxes, suspect, nh_width)
    picks[(round(c[0], 1), round(c[1], 1))] = None if bi is None else dict(box=[round(v) for v in boxes[bi]], suspect=bi in suspect)
    return bi


L._pick_beam_box = tap_pick


def tapped(events, detections):
    boxes = [d["bbox_page"] for d in detections if d.get("category") == "structural" and d.get("class") == "beam"]
    picks.clear()
    orig(events, detections)
    for i, ev in enumerate(events):
        for h in ev.get("noteheads") or ():
            k = h.get("glyph") or h.get("subject") or h.get("key") or h.get("rg")
            if k is None:
                continue
            hb0 = (ev.get("noteheads") or [{}])[0].get("bbox_page") or ()
            ck = (round(hb0[0] + hb0[2] / 2.0, 1), round(hb0[1] + hb0[3] / 2.0, 1)) if len(hb0) == 4 else None
            out[str(k)] = dict(levels=int(h.get("beam_levels") or 0), states=ev.get("beam_states"), n_boxes=len(boxes),
                               pick=("synthetic" if ck in picks and picks[ck] is None else picks.get(ck, "not_asked")),
                               boxes=[[round(v) for v in b] for b in boxes], head=[round(v) for v in (h.get("bbox_page") or ())],
                               head_keys=sorted(h.keys())[:40])


L.annotate_beams = tapped
E._legacy.annotate_beams = tapped
E.to_musicxml(res)
json.dump(out, open(sys.argv[2], "w"))
print("events", len(out))
