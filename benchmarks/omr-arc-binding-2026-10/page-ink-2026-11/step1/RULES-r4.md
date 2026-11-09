# 2.274 round 4: pages and verdict rule, written and committed BEFORE any round-4 code or number (2026-11-07)

Sean 2026-11-07, on the round-3 crops (10 of 12 whole; tiles 6 and 11 were cut short): "Tile 6 and 11 are not the full arc - all the rest are. Keep going do another round.
We can get this". His process: read each arc as ONE ink run on the page, attach it to notes, never cut it up. Round 3 held out at 90.0% of detector-kept curves whole
(91.3% of the real ones; 94.7% counting two-run curves), NEW runs 12 fakes in 30 sampled (about 4-5 a page); witnessed runs 0 fakes in 20. Bars: 95% / under 3 / 0.

DEVELOP (looked at, may tune on): Brahms p0, p4, p5, p7, p9, p12, p14, p19, p22, p25; Litolff p3, p4, p6, p8, p9, p10, p12, p16 (every earlier hold-out is now develop).
NEW HOLD-OUT (not looked at by any reader of this lane; not run for any decision until the code and constants are frozen): Brahms p11 (653 detector slur/tie boxes, 358 curves)
and p20 (283 boxes, 140 curves); Litolff p5 (143 boxes, 182 curves) and p13 (277 boxes, 308 curves). Each has well over 60 arcs, so NO swap is made (box and curve counts
only were read; no reader ran on any of them). Spares, unused: Brahms p8, p10, p15, p17, p18, p21; Litolff p7, p11, p14, p15.
The slices are cut from the same saved 20261104-night record as every earlier round (`build_slices_r4.py`), so the detector curves are the same night's.

VERDICT (hold-out pages only, pooled; counting exactly as RULES-r3.md): GOOD if
1. runs cover WHOLE (one run >= 80% of the curve's x span, matched within 0.6 sp) at least 95% of the detector-kept REAL arcs. How non-arcs are excluded, fixed now:
   a detector curve is real unless, on a crop look at EVERY uncovered kept curve (the covered ones are taken as real), it is a hairpin leg or other long thin straight line,
   a flag / hook / fermata / letter, or staff / ledger / beam residue. The strict share (no exclusion: covered / kept) is reported next to it.
   MEETING PAIRS: a detector curve that joins two arcs meeting at a note is NOT counted covered by its two runs for the verdict (the one-run rule) and is NOT
   excluded as a non-arc; it stays in the denominator. It is reported apart ("with meeting pairs counted covered") exactly as in round 3, so the two readings compare.
2. NEW runs (no witnessing detector box) are real arcs by a crop look (all when under 30, else a seeded sample of 30);
3. fakes (hairpin leg, beam piece, line residue, ledger pair, frame, a digit or letter, any run that is not an arc, by look) are under 3 per page over the NEW runs,
   AND witnessed runs stay at 0 fakes in a seeded sample of 20.
Otherwise NOT GOOD, naming which of the three failed. Per-page numbers next to pooled ones; develop numbers reported apart. No constant is changed after the hold-out is run.
Gates: export byte-identical flag ON vs OFF; fast tier; `check` no higher than main + the existing 3; 12 crops from the new hold-out pages (long flat slurs and meeting pairs among them).
Controls that can fail: each mechanism ships with a drawn case it fixes and the same case with the property removed, which it must NOT fix (a straight uniform line is
not a slur; a beam is not an arc; two arcs that meet are split and one arc through a head is not).

FROZEN: reader and constants as of commit 6a64c47b8 (page_arcs.py), committed and pushed BEFORE the hold-out pages were read, measured or looked at. Develop-page numbers at the freeze (18 pages): strict one-run whole 2281 of 2458 (92.8%; the round-3 reader on the same pages 2243, 91.3%), union (meeting pairs counted) 2330 (94.8%); NEW runs 238 (round 3: 301).
