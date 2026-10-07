"""ROADMAP 2.59 (lane-dot-not-a-note) -- GATHER+ADJUDICATE replay of a saved record,
ONE flag state, dots and dot-sized boxes only, compact JSON out.  READ ONLY on the record
(`record_io` streaming of the GATHER rows of the named pages; never `--through evaluate`).

    OMR_DOT_FOLLOWS_NOTE=1 python3 dot_not_a_note_replay.py REC.json OUT.json --pages 5,7,18

Writes {"dots": {key: {...}}, "boxes": {key: {...}}, "census": {...}} for the pages given.
`dots`  = every `Q.AUG_DOT` glyph: its role verdict (+ the note it names), its owner verdict, its page box,
          the duration of every notehead is NOT here -- this is a reading-of-the-dot table.
`boxes` = every notehead-class glyph: class, size in staff spaces (w, h), the not-a-notehead verdict, owner, page box.
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import mark_identity_rebuild as M                                 # noqa: E402
from tools.omr.staged import adjudicate                           # noqa: E402
from tools.omr.staged import adjudicators                         # noqa: E402,F401
from tools.omr.staged.record import Kind, Q, Outcome              # noqa: E402


def _v(v):
    if v is None:
        return None
    return {"o": v.outcome.value if hasattr(v.outcome, "value") else str(v.outcome),
            "v": v.value if isinstance(v.value, (str, int, float, bool, type(None))) else str(v.value)[:80],
            "r": v.reason, "d": {k: x for k, x in (v.detail or {}).items() if k in ("head", "was", "twin_of_a_dot")}}


def extract(log):
    dots, boxes = {}, {}
    for sub in log.subjects(Kind.GLYPH):
        key = sub.to_key()
        gb = log.rows(Q.GLYPH_BOX, sub)
        if not gb:
            continue
        pb = (gb[-1].detail or {}).get("bbox_page_px")
        cls = gb[-1].value[0] if isinstance(gb[-1].value, (list, tuple)) and gb[-1].value else None
        if log.rows(Q.AUG_DOT, sub):
            dots[key] = {"cls": cls, "box": pb, "role": _v(log.verdict(Q.DOT_ROLE, sub)),
                         "own": _v(log.verdict(Q.GLYPH_OWNER, sub))}
        elif log.rows(Q.NOTEHEAD_CLASS, sub):
            sp = None
            for r in log.rows(Q.CELL_STAFF_SPACE, sub.at(Kind.CELL), scope=__import__("tools.omr.staged.record", fromlist=["Scope"]).Scope.SELF_AND_ANCESTORS):
                sp = float(r.value)
            w = h = None
            if sp and isinstance(gb[-1].value, (list, tuple)) and len(gb[-1].value) == 5:
                w, h = gb[-1].value[3] / sp, gb[-1].value[4] / sp
            boxes[key] = {"cls": cls, "box": pb, "w": w, "h": h,
                          "np": _v(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)),
                          "own": _v(log.verdict(Q.GLYPH_OWNER, sub)),
                          "dur": _v(log.verdict(Q.DURATION, sub))}
    inst, lines = {}, {}
    for sub in log.subjects(Kind.STAFF):
        v = log.verdict(Q.INSTRUMENT, sub)
        if v is not None and v.outcome is Outcome.DECIDED and isinstance(v.value, dict):
            inst[sub.to_key()] = v.value.get("name")
        rr = log.rows(Q.STAFF_LINES, sub)
        if rr:
            lines[sub.to_key()] = list(rr[-1].value)
    return dots, boxes, inst, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("out")
    ap.add_argument("--pages", required=True)
    a = ap.parse_args()
    pages = set(int(x) for x in a.pages.split(","))
    t0 = time.time()
    res = M.load_pages_streaming(a.record, pages)
    log = M.rebuild(res["record"], pages)
    print(f"rebuilt {len(res['record']['observations'])} obs in {time.time() - t0:.0f}s", flush=True)
    t1 = time.time()
    adjudicate.run(log)
    print(f"adjudicate {time.time() - t1:.0f}s", flush=True)
    dots, boxes, inst, lines = extract(log)
    Path(a.out).write_text(json.dumps({"pages": sorted(pages), "dots": dots, "boxes": boxes,
                                       "inst": inst, "staff_lines": lines}))
    print("wrote", a.out, len(dots), "dots", len(boxes), "boxes", flush=True)


if __name__ == "__main__":
    main()
