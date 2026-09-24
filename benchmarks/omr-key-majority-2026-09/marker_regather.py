"""ROADMAP 2.9b — price the GATHER widening off a saved record.

    python3 benchmarks/omr-key-majority-2026-09/marker_regather.py <record.json>

⚠️⚠️ **THIS IS A GATHER CHANGE AND `readjudicate.py` IS STRUCTURALLY BLIND TO
IT** (CLAUDE.md §4d): it rebuilds a Log from the record's OWN rows, so a
marker row the shipped gather never filed does not exist for it and a zero
from it is not evidence. What makes the change priceable without a 13-hour
re-gather is that the detector's boxes ARE on the record — `Q.GLYPH_BOX`
carries `(smufl_name, x_canonical, y_canonical, w, h)` for every detection —
so the marker rows can be recomputed from the same input the gather had.

⚠️ AND IT IS STILL A SIMULATION. It calls `gather._gather_keysig_markers`
itself, so the shipped code is what runs, but the boxes come from the record
rather than from the detector. `FINDINGS.md` §2.9b names the ONE real
`--pages 3` gather that confirms it.

What it prints: header cells that gain a slot, runs that change value, and
the 53 / 84 cells that carry an accidental-class box and NO key-class box at
all — the population the class-name filter was silently dropping.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from tools.omr.staged import gather as G                     # noqa: E402
from tools.omr.staged import record as R                     # noqa: E402
from tools.omr.staged.record import Log, Q, READERS          # noqa: E402
from tools.omr.staged.record_io import load_record           # noqa: E402
from tools.omr.staged.adjudicators import header as H        # noqa: E402


class _Box:
    def __init__(self, name, x, conf):
        self.smufl_name = name
        self.x_canonical = float(x)
        self.y_center = 0.0
        self.confidence = float(conf)


def _fields(subject: str):
    p = subject.split("/")
    return tuple(int(x) for x in p[1:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    a = ap.parse_args()
    rec = load_record(a.record)
    rec = rec["record"] if "record" in rec else rec

    # ── the detector's boxes in every staff's cell 0, and the cell's unit ────
    boxes: dict = collections.defaultdict(list)
    space: dict = {}
    for o in rec["observations"]:
        if o["quantity"] == Q.CELL_STAFF_SPACE:
            page, system, staff, cell = _fields(o["subject"])[:4]
            if cell == 0:
                try:
                    space[(page, system, staff)] = float(o["value"])
                except (TypeError, ValueError):
                    pass
        elif o["quantity"] == Q.GLYPH_BOX:
            f = _fields(o["subject"])
            if len(f) < 5 or f[3] != 0:
                continue
            name = o["value"][0]
            if not (name in G._KEYSIG_CLASSES or name in G._ACCIDENTAL_SHAPE):
                continue
            boxes[f[:3]].append(_Box(name, o["value"][1], o.get("score") or 0.0))

    old = new = 0
    gained = collections.Counter()
    moved = collections.Counter()
    accidental_only = 0
    classes = collections.Counter()
    for key in sorted(set(boxes) | set(space)):
        page, system, staff = key
        here = boxes.get(key, [])
        for b in here:
            classes[b.smufl_name] += 1
        if here and not any(b.smufl_name in G._KEYSIG_CLASSES for b in here):
            accidental_only += 1

        def run(admit_accidentals: bool):
            log = Log()
            cell = R.cell(page, system, staff, 0)
            if key in space:
                log.observe(cell, Q.CELL_STAFF_SPACE, space[key],
                            reader=READERS.GEOMETRY, frame="cell:0")
            sub = R.staff(page, system, staff)
            dets = here if admit_accidentals else [
                b for b in here if b.smufl_name in G._KEYSIG_CLASSES]
            G._gather_keysig_markers(log, sub, {cell.to_key(): dets}, page,
                                     (system, staff))
            rows = log.rows(Q.KEYSIG_MARKER, sub)
            return H._marker_run(rows, space.get(key, 0.0))

        was, was_reason, was_detail = run(False)
        now, now_reason, now_detail = run(True)
        old += 1 if was is not None else 0
        new += 1 if now is not None else 0
        if was is None and now is not None:
            gained[f"{was_reason} -> {now} ({now_reason})"] += 1
        elif was is not None and now is not None and was != now:
            moved[f"{was} -> {now}"] += 1
        elif was is not None and now is None:
            moved[f"{was} -> None ({now_reason})"] += 1

    print(f"header cells with an accidental-shaped box: {len(boxes)}")
    print(f"   classes: {dict(classes.most_common())}")
    print(f"   cells with an accidental-class box and NO key-class box: "
          f"{accidental_only}")
    print(f"runs read: {old} -> {new}")
    print(f"   newly read: {dict(gained.most_common(10))}")
    print(f"   value moved: {dict(moved.most_common(10))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
