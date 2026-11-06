# Verdict rule for 2.274 step 1, written and committed BEFORE any out-of-sample number was computed (2026-11-06)

Pages (out of sample: the run settings were tuned four times on Brahms p0, so p0 is excluded): Brahms p5 and the two other Brahms pages of the saved
20261104-night slice (pages 4, 8, 12, 14, 19, 25) with the MOST detector slur/tie boxes (chosen by that count alone, before any run was read); Litolff p4 and p16.

GOOD if, over the out-of-sample pages together:
1. the runs cover WHOLE (one run covers >= 80% of the curve's x span, matched within 0.6 sp) at least 95% of the detector curves that are REAL arcs
   (a detector curve = a `Q.SYSTEM_ARC` row not refused as `refused_not_an_arc`; real/fake of every UNCOVERED curve is read from a crop look; a covered
   curve is taken as real), counted BEFORE and AFTER the seeded local read (the seeded rescue is reported apart: the box chose where to look); AND
2. the runs with no witnessing detector box (NEW) include real arcs, by a crop look at a sample (all of them when under 30); AND
3. fakes (a run that is not an arc, by look: ledger pair, hairpin leg, line residue, other mark) are under 3 per page, counted over the NEW runs and a
   random sample of 20 witnessed runs per page.
Otherwise NOT GOOD, and the report says which of the three failed. Per-page numbers are reported as well as the pooled ones.

Chosen by detector slur/tie box count (glyph_box rows, twins included) before any run was read: page 0: 348 (in-sample, excluded), 4: 714, 5: 737, 8: 382, 12: 674, 14: 424, 19: 716, 25: 635. So the Brahms pages are 5, 19 and 4.
