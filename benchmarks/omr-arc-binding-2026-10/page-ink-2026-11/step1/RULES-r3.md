# 2.274 round 3: pages and verdict rule, written and committed BEFORE any round-3 code or number (2026-11-06)

Sean 2026-11-06, on tiles of what the ink reader misses: "Make that the 3rd round." Round 2 held out at 87.9% of detector-kept curves whole (91.4% of the real
ones); bar 95%. All twelve miss tiles share one cause: the reader loses an arc WHERE IT TOUCHES OTHER INK (a staff line, a barline, a stem or head, a word's foot).
Round 3 reads through those touches on the arc's own slope and judges the line band on the UNERASED raster, against the line's own local thickness.

DEVELOP (looked at, may tune on): Brahms p4, p5, p19, p7, p22; Litolff p4, p16, p6, p12 (round 1's and round 2's develop AND round 2's hold-out pages, which round 2 looked at).
NEW HOLD-OUT (not looked at by this reader; not run for any decision until the code and constants are frozen): Brahms p9 (556 detector slur/tie boxes) and p25 (635);
Litolff p3 (253) and p9 (157). SWAP, written before any reader run: the drawn Litolff p14 has 125 boxes (< 150, thin), so it is swapped for the unused Litolff page with
the most boxes among the pages cut for this round (p9, 157; box counts only, no reader run on any of them). Brahms p9 / p25 and Litolff p3 are untouched by this reader.
Brahms p12, p14, p8, p10 and Litolff p8, p10, p11 were cut as spares and stay unused. Brahms p0 is in-sample.
The hold-out slices are cut from the same saved 20261104-night record as the develop pages (`build_slices_r3.py`), so the detector curves are the same night's.

VERDICT (hold-out pages only, pooled; counting exactly as RULES-r2.md): GOOD if
1. runs cover WHOLE (one run >= 80% of the curve's x span, matched within 0.6 sp) at least 95% of the detector-kept REAL arcs. How non-arcs are excluded, fixed now:
   a detector curve is real unless, on a crop look at EVERY uncovered kept curve (the covered ones are taken as real), it is a hairpin leg or other long thin straight line,
   a flag / hook / fermata, or staff / ledger / beam residue. The strict share (no exclusion: covered / kept) is reported next to it. Two arcs that meet at a note and are
   covered by their two runs are NOT counted covered in the verdict (reported apart);
2. the NEW runs (no witnessing detector box) are real arcs by a crop look (all when under 30, else a sample of 30), AND
3. fakes (hairpin leg, line residue, ledger pair, frame, a crook label, any run that is not an arc, by look) are under 3 per page over the NEW runs and 20 sampled witnessed runs.
Otherwise NOT GOOD, naming which of the three failed. Per-page numbers next to pooled ones; develop numbers reported apart. No constant is changed after the hold-out is run.
Gates: export byte-identical flag ON vs OFF; fast tier; `check` not above round 2's +3 against main; the 12 round-2 miss tiles re-run.
Controls that can fail: each new mechanism ships with a drawn case it fixes and the same case with the touching ink removed (or the ink made not arc-like), which it must NOT fix
(a straight line on a staff line is not read as an arc; a stem is not bridged into a run that has no arc on its other side).
