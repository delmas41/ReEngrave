"""IF THE CONVENTION IS STRONG, THE BOUNDARY IT IMPLIES MUST BE THE MIDDLE LINE.

Sean, 2026-09-17: *"The convention is strong. The failure is elsewhere."*

⚠️⚠️ THE THREE READINGS DO NOT FAIL INDEPENDENTLY, AND THAT IS THE CLUE. The
PROJECTION reads where a stem's ink overhangs; the BEAM MATE reads what ink
hangs from one stroke. **Both are readings of INK inside the measure cell.**
The CONVENTION is the only one of the three that depends on where the STAFF
LINES are -- it asks `Q.NOTEHEAD_STAFF_POSITION`, which is
`(y_center - top_y) / half_step`. So if the cell's five-line grid is off, the
convention reads wrong while the two ink readings agree with each other, which
is EXACTLY the shape measured: where the projection and the convention
disagree, the beam sides with the projection 79 times in 83.

⚠️ That shape is evidence about the GRID, not about the convention -- and this
project has already paid for it twice: `OMR_CELL_LINE_TRACE` exists because a
scanned staff tilts 8-17 px across its width, and the phantom-note session
measured an absolute staff step DRIFTING 1.4 STEPS ACROSS ONE SYSTEM.

So: invert the question. Take the convention as TRUE and ask what boundary the
directions imply. `Q.NOTEHEAD_STAFF_POSITION` is in STEPS down from the top
line, so a five-line staff's lines are 0, 2, 4, 6, 8 and the middle line is 4.

  * if the implied boundary is 4 everywhere, the convention is simply weaker
    here and the grid is fine;
  * if it is a DIFFERENT constant per staff or per cell, the grid is offset
    and the convention is a RULER for that offset rather than a reader of
    stems.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record import Kind, Subject                # noqa: E402

MIDDLE_LINE = 4.0


def best_split(samples):
    """The boundary `b` maximising agreement with `pos <= b -> down`.

    Returns `(b, agreement, n)`. Ties resolve to the boundary nearest the
    middle line, so a population that does not care reports 4.0 rather than
    an arbitrary end of the plateau.
    """
    if not samples:
        return None, 0.0, 0
    cuts = sorted({round(p * 2) / 2 for p, _ in samples} | {MIDDLE_LINE})
    best = None
    for b in cuts:
        ok = sum(1 for p, d in samples
                 if (d == "down") == (p <= b))
        score = ok / len(samples)
        key = (score, -abs(b - MIDDLE_LINE))
        if best is None or key > best[0]:
            best = (key, b, score)
    return best[1], best[2], len(samples)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "boundary-fit.json"))
    a = ap.parse_args()
    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    pos_of = {}
    for o in rec["observations"]:
        if o["quantity"] == "notehead_staff_position":
            try:
                pos_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
    proj = {v["subject"]: v["value"] for v in rec["verdicts"]
            if v["quantity"] == "stem_direction"
            and v["reason"] == "stem_projection"}

    samples = [(pos_of[s], d) for s, d in proj.items() if s in pos_of]
    print(f"heads with a position and a projected direction: {len(samples)}")

    b, acc, n = best_split(samples)
    at4 = sum(1 for p, d in samples if (d == "down") == (p <= MIDDLE_LINE))
    print(f"\n── ONE boundary for the whole document")
    print(f"   at the middle line (4.0): {at4 / n:.3f}")
    print(f"   best single boundary    : {b}  ->  {acc:.3f}")

    def group(kind):
        out = collections.defaultdict(list)
        for s, d in proj.items():
            if s not in pos_of:
                continue
            out[Subject.from_key(s).at(kind).to_key()].append((pos_of[s], d))
        return out

    result = {"n": n, "at_middle_line": round(at4 / n, 4),
              "best_single": {"boundary": b, "accuracy": round(acc, 4)}}

    for kind, label, floor in ((Kind.STAFF, "per STAFF", 12),
                               (Kind.CELL, "per CELL", 6)):
        fits, weighted_ok, weighted_n, bounds = [], 0, 0, []
        for key, s in group(kind).items():
            if len(s) < floor:
                continue
            bb, aa, nn = best_split(s)
            fits.append((key, bb, aa, nn))
            weighted_ok += aa * nn
            weighted_n += nn
            bounds.append(bb)
        if not fits:
            continue
        print(f"\n── a boundary fitted {label} (>= {floor} heads)")
        print(f"   groups fitted            : {len(fits)}")
        print(f"   heads covered            : {weighted_n}")
        print(f"   agreement at 4.0         : "
              f"{sum(1 for k, _, _, _ in fits for p, d in group(kind)[k] if (d == 'down') == (p <= MIDDLE_LINE)) / max(1, weighted_n):.3f}")
        print(f"   agreement at the FIT     : {weighted_ok / max(1, weighted_n):.3f}")
        print(f"   boundary median          : {statistics.median(bounds)}")
        print(f"   boundary p10..p90        : "
              f"{sorted(bounds)[int(0.1 * len(bounds))]} .. "
              f"{sorted(bounds)[int(0.9 * len(bounds))]}")
        print(f"   share fitting EXACTLY 4.0: "
              f"{sum(1 for x in bounds if abs(x - 4.0) < 1e-9) / len(bounds):.3f}")
        result[label] = {
            "groups": len(fits), "heads": weighted_n,
            "accuracy_at_fit": round(weighted_ok / max(1, weighted_n), 4),
            "boundary_median": statistics.median(bounds),
            "share_exactly_4": round(
                sum(1 for x in bounds if abs(x - 4.0) < 1e-9) / len(bounds), 4),
        }

    Path(a.json).write_text(json.dumps(result, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
