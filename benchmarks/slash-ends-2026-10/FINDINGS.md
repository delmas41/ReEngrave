# 2.214 -- one tremolo-slash test from the stroke's ends: STOPPED at step 1 (no separation)

STAGED GATHER (`Q.STROKE`, `stroke_map.py`) read only; nothing built, no flag added.

## Cause and process lesson (first)
The ends cannot be read off the stroke because **the stroke is not the mark**. Cropped on Sean's 8 answered 2.210 tiles plus 42
more cases (8 Litolff / 9 Brahms old-reader slashes, 16 kept heads, 6 chord heads): the two true slashes (tiles 5, 12, Brahms) are
fused to a beam stub / stem foot above them; five of the six notes the 2.205 rule calls slashes (tiles 3, 6, 7, 9, 10) are a head
fused to a ledger rung, beam or stem foot, a `horizontal` piece 2.9-3.2 sp long (the true slashes are 1.6-1.7). Heads beside a
stem lose that side to the stem cut: a flat edge with two ~90 degree corners, exactly what a slash end looks like. At 100 px/sp a
1.3 x 0.9 sp oval is 4-8 chords after a 0.06 sp polygon fit, so "straight share" is a resolution artefact (round heads score
0.9-1.0).
Process lesson: Sean's convention (square ends vs oval) is a property of ONE printed mark; every measure we have works on a
piece of ink that Litolff MERGES / the stem cut TRIMS. Isolate the mark first (ink claiming, 2.194 line), then ask about its ends.
A convention that needs the whole outline cannot be tested on an outline we have already cut.

## Measures tried (scripts here; all on full-resolution masks of the covered non-vertical strokes)
| measure | true slashes (t5, t12) | judged notes (t2-4, 6-10) | separates? |
|---|---|---|---|
| width-profile plateau (share of axis with width >= 0.85 max) | 0.32, 0.28 | 0.20-0.60 | no |
| end width / max width | 0.21, 0.21 | 0.10-0.35 | no |
| hull solidity | 0.92, 0.91 | 0.72-0.91 | no |
| straight share of polygon outline | 0.80, 0.86 | 0.65-0.83 | no (heads 0.9-1.0) |
| sharp corners (<125 deg), whole outline | 5, 4 | 1-7 | no |
| same, outline away from other strokes | 5, 2 | 3-6 | no |
Only length (slash 1.6-1.7 sp vs 2.9-3.2 fused notes) and thickness separate the 8 tiles, and that is a cut tuned on 2 examples
(CLAUDE section 4) which says nothing about ends, so it is not proposed here.

## Result
Does not separate cleanly. No code, no flag. The two slash tests are unchanged. Brahms p12 `glyph/12/0/10/5/8` remains written
as a note. Next real step is upstream: a mark-isolated mask (2.194 ink claiming) before any outline question.
Files: `probe.py` (cuts cell + masks), `sheet.py`/`sheet_cases.png` (crops, orange box), `measure_*.py`, `extract_boxes.py`.
Not done by design (STOP rule): lane_report, 12 blind tiles, judged right->wrong (0 changes, file byte-identical).
