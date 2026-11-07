# 2.274 round 2: pages and verdict rule, written and committed BEFORE any round-2 code or number (2026-11-06)

Sean 2026-11-06 ("2"): fix the ink read first so it reaches the bar on its own, before combining it with the detector. His process: read each arc as ONE
ink run on the page, attach it to notes, never cut it up. Round 1 (out of sample) covered 81.0% of detector-kept curves whole; the bar is 95%.

DEVELOP (may be looked at, may tune on): Brahms p5, p19, p4; Litolff p4, p16.
HOLD OUT (not looked at, not run for any decision, until the code and constants are frozen at the end): Brahms p7, p22; Litolff p6, p12.
Round 1 already looked at Brahms p12, p14 and Litolff p8, p10 (it confirmed a constant on them), so they are NOT usable as hold-out. Brahms p0 is in-sample.
The hold-out pages are not in the saved 20261104-night slice; their slices are cut from the same saved night record (same rows, only more pages), so the
detector curves are the same night's. If a hold-out page turns out to have fewer than 150 detector slur/tie boxes it is swapped, BEFORE any reader run on it,
for the unused page of the same plate with the most boxes (box counts only), and the swap is written here.

VERDICT (hold-out pages only, pooled; definitions exactly those of RULES-step1.md): GOOD if
1. runs cover WHOLE (one run >= 80% of the curve's x span, within 0.6 sp) at least 95% of the detector curves that are real (kept, not
   `refused_not_an_arc`; covered curves taken as real, uncovered ones read from a crop look), AND
2. the runs with no witnessing detector box (NEW) are real arcs by a crop look (all when under 30, else a sample of 30), AND
3. fakes (hairpin leg, line residue, ledger pair, frame, any run that is not an arc, by look) are under 3 per page over the NEW runs and 20 sampled witnessed runs.
Otherwise NOT GOOD, and the report says which of the three failed. Per-page numbers are reported next to the pooled ones. Dev numbers are reported apart.
No constant is changed after the hold-out is run; if it fails, it fails.
