"""THE FLOOR, IN ONE PLACE.

⚠️ THE MUTATION BATTERY FOUND THIS AND NOTHING ELSE WOULD HAVE. `FLOOR = 1.0`
was restated in FIVE probe files, so the arm that moved it in `score.py`
SURVIVED: `issues.py` reproduced the stroke lane's 44 / 576 off its own copy
of the constant and never noticed. That is this repo's own anti-drift fault --
*a constant this project paid to measure once, held in five places* -- arriving
inside the instrument built to price it.

Every probe imports it from here now, so moving it moves every table at once
and the battery arm can go red.

⚠️ IT IS NOT THIS JOB'S CONSTANT. It is inherited unchanged from
`benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §2 (*"a floor at width <
1.0 spaces catches 39 of the 46 at a cost of 0 of 63 real stems"*) and from
`benchmarks/omr-stem-stroke-2026-09/stroke_arm.py:387` (`NOTEHEAD_MIN_W =
1.0`). It was not fitted here and is not moved to improve any number.
"""
from __future__ import annotations

# width in STAFF SPACES below which a box is too narrow to be a notehead.
FLOOR = 1.0
