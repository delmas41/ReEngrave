# Verdict rule, written and committed BEFORE any number was computed (2026-11-06)

Feasibility of reading arcs ink-first (docs/plan-2026-11-06-page-ink-arcs.md), Brahms p0 (Sean's hand arcs) and Litolff p16.

PROMISING if the ink-first runs find WHOLE at least as many hand arcs as today's detector-first path on the same page, AND fake runs are
under 5 per page. Otherwise NOT PROMISING (say which half failed).

Definitions (fixed now):
- A printed arc = Sean's hand boxes (one per cell) of one staff in neighbouring bars whose facing edges meet within 1.5 sp and whose
  y ranges overlap -- the cell pieces of one arc joined back; an arc broken by a system break stays two printed arcs (one per system).
- A run/curve is ON a printed arc when >= 70% of its points (detector path: its box centre and x span) lie inside the arc's hand boxes
  grown by 0.5 sp.
- WHOLE: one run on the arc covers >= 80% of its x span. PIECES: no single run does, the runs on it together do. SHORT: the best union
  covers 30-80%. MISSED: under 30%.
- FAKE: a run on no printed arc. Its cause is read from a look at its crop (letter, hairpin, beam, line residue, other mark's ink, a real
  arc Sean never boxed).
- Detector-first path = the page curves (`Q.SYSTEM_ARC`, over-joined chains split into their boxes) of the saved 20261104-night gather,
  as the deep-dive ledger holds them (`results/brahms.base.ledger.json`, `litolff.base.ledger.json`), refused-as-not-an-arc left out.
- Litolff p16 has no hand truth: fakes are counted from a look at every ink-first run that no kept detector curve overlaps, and
  "whole" is reported against the detector path's own curves only as agreement, not as truth.
