# Verdict rules, written and committed BEFORE the numbers were computed (2026-11-06)

HYPOTHESIS 1 (Sean): "the cutoff of the orange boxes is with the barlines. That goes against the page wide read."
  HOLDS: share of arc-box ends at a barline / cell edge >= 2x the chance share, AND most barline-crossing arcs are boxed as two or more pieces.
  FAILS: share within 1.3x of chance.  In between: mixed.

HYPOTHESIS 2 (Sean): "since we are trying to connect the arcs to notes and notes are read at the cell level that is why this is happening."
  The arc is broken because the BINDING is per cell (end notes looked up in the arc's own cell / keyed to one cell), even when box or page curve is whole.
  Per barline-crossing arc, the stage that FIRST breaks it: D detection (the other half never boxed), G trace (both halves boxed, page curve not joined),
  B binding (curve whole, ADJUDICATE binds/pairs no pair), X export pairing (pair decided, not written whole).
  HOLDS: among LOST crossing arcs whose page curve is whole, a majority first break at B or X, AND the code that failed searches only the arc's own cell
  (or measure). FAILS: the binder searches page/staff-wide AND most lost crossing arcs first break at D or G. Otherwise mixed; counts are reported.
