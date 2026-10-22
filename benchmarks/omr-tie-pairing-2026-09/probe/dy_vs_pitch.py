"""Does the GEOMETRY agree with the PITCHES? The test that separates the two.

A tie joins one pitch to itself, and one pitch is one STAFF POSITION — so the
two heads of a correct tie sit at the SAME y. That gives a second reading of
the same link, off the boxes rather than off `pitch_resolver`, and the two
readings disagree in a way that names the culprit:

  dy ~ 0, pitches DIFFER   the pairing picked two heads at the same staff
                           position and the PITCHES disagree anyway. The
                           pairing is right; the pitch reading (or its
                           spelling) is what is wrong.
  dy ~ one step, pitches a step apart
                           the two readings AGREE that the arc spans a step.
                           A tie cannot; so the arc's CLASS is the suspect,
                           not the pairing and not the pitch.
  dy large                 the two heads are far apart on the staff. Only here
                           is the PAIRING the leading suspect.

⚠️ This does not adjudicate any single arc — a head misread by one staff
position lands in the middle band too. It separates POPULATIONS, which is what
the boundary case needed and what a pooled different-pitch rate cannot give.

⚠️ The unit is the average NOTEHEAD HEIGHT of the staff, which is one staff
space, so one diatonic step is 0.5. Taken from the same average
`_pair_ties_in_staff` computes its own `y_tol` from, so the two cannot drift.

    python3 .../dy_vs_pitch.py <dir-or-file>...
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from geometry import walk  # noqa: E402
from split_causes import classify  # noqa: E402

#: Half a staff space is one diatonic step. A pair inside this reads as ONE
#: staff position; beyond `_STEP_MAX` it is more than a step apart. Both are
#: read off the measured distribution this probe prints, never set in advance.
_SAME_MAX = 0.25
_STEP_MAX = 0.75


def band(dy_spaces: float) -> str:
    a = abs(dy_spaces)
    if a <= _SAME_MAX:
        return "dy~0"
    if a <= _STEP_MAX:
        return "dy~step"
    return "dy_WIDE"


def main() -> int:
    files: list[pathlib.Path] = []
    for a in sys.argv[1:]:
        p = pathlib.Path(a)
        files += sorted(p.glob("*.omr.json")) if p.is_dir() else [p]
    if not files:
        sys.stderr.write("FATAL: no `.omr.json`\n")
        return 2
    grid: collections.Counter = collections.Counter()
    for f in files:
        for r in walk(json.loads(f.read_text())):
            left, right = r["pick_l"], r["pick_r"]
            if left is None or right is None or left[2] is right[2]:
                continue
            pl, pr = left[2].get("pitch"), right[2].get("pitch")
            kind = "same" if (pl is not None and pl == pr) else classify(pl, pr)
            dy = (left[1] - right[1]) / r["avg_nh_h"]
            grid[(kind, band(dy))] += 1
    kinds = ["same", "SPELLING", "STEP_APART", "WIDE", "UNREADABLE"]
    bands = ["dy~0", "dy~step", "dy_WIDE"]
    print(f"{'pitch verdict':14s} " + " ".join(f"{b:>9s}" for b in bands)
          + f" {'total':>7s}")
    for k in kinds:
        row = [grid[(k, b)] for b in bands]
        if not any(row):
            continue
        print(f"{k:14s} " + " ".join(f"{v:9d}" for v in row)
              + f" {sum(row):7d}")
    total = sum(grid.values())
    print(f"{'TOTAL':14s} " + " ".join(
        f"{sum(grid[(k, b)] for k in kinds):9d}" for b in bands)
        + f" {total:7d}")
    if not total:
        sys.stderr.write("⚠️ ZERO paired links — a dead instrument.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
