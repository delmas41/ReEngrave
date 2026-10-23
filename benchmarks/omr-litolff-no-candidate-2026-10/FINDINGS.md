# 2.200 -- WHY LITOLFF FINDS NO NOTE FOR ITS ACCIDENTALS (read-only; no code under tools/ changed; STAGED, ADJUDICATE `accidental_owner` = `no_candidate`)

## CAUSE AND LESSON (plain words)
1. **More than half of Litolff's `no_candidate` refusals are not accidentals at all.** Of the 167 `no_candidate` boxes on the 8 current-tree pages, **I looked at every one** (my look, not blind to the mechanical stratum, not Sean's): 96 (57%) are not an accidental -- 45 stem tips / stem pieces (the detector reads a lone thin stem top as a flat's ascender: 44 of them boxed accidentalFlat), 26 rests (17 of 22 doubleSharp-class boxes are 8th/quarter rests; Beethoven 5 i has no double sharp), 13 ink fragments, 8 barline slivers, 3 dynamic/text letter pieces, 1 clef curl. For these `no_candidate` is the CORRECT answer. The "only 46% written" of 2.197 divides by a pool that is over half junk boxes.
2. A further 21 (13%) are **duplicates**: the same ink boxed in the neighbouring staff's cell, whose copy DECIDED and was written (15 real accidentals, 6 pieces of them). Harmless.
3. What is really lost is **~56 of 167 (34%)**: real accidentals (46 whole + 11 cropped to the ascender, minus twins) and 14 merged boxes. Their causes, split mechanically after my look (table below): **natural boxed as flat so the flat anchor (0.715) misses the head (12-22 of the real ones; lane 2.199 owns this)**, **the fitting head exists but was refused** (`stacked_head_duplicate`, `owned_by_another_staff`, `on_a_dynamic_letter`, `tremolo_slash_crosses_stem`), and **the head was never boxed** (Litolff's slanted hollow heads, the lower head of a chord or a head touching a slur/stem: seen on the tiles with no box on the oval at all).
4. **Staff tilt is not a cause.** The cell grid is localised per cell (`OMR_CELL_LINE_TRACE`, default ON, rigid shift) and accidental and head are read on the same cell grid; the owner's window is <= 1.75 sp wide, so even a 1 degree tilt moves the comparison by ~0.5 px (0.03 sp) against a 0.7 sp bound. (A computation from the code, not a measurement of tilt.)
5. **Process lesson.** A funnel rate ("46% written, 35% no_candidate") was read as "the owner fails on accidentals". The census never asked what the denominator IS. Looking at the refusals one by one -- cheap, 167 tiles -- shows the refusal is mostly right and the loss is a third of it, with three different causes in three different stages (detector junk, ownership class anchor, head reading/refusal). Rule: **before a refusal bucket opens a lane, say what fraction of it is the refusal being correct.** (Extends rule 7: a count from another stratum, here "boxes" for "accidentals".)

## WHICH TREE (every number says)
- **Tree S8** = `out/2.197-replay/B_litolff_s8.view.json`: Litolff pages 2,4,6,8,9,10,11,16 gathered on branch lane-2.195-stroke-map 242487eeb (OMR_STROKE_MAP=0; main with 2.186/2.190/2.192 ON; **2.193 not confirmed**). 167 `no_candidate` of 681 accidental-class boxes (matches the record's own `accidental_reading.no_candidate`). All looks are on this tree.
- **Tree NIGHT** = whole movement, `beethoven5-litolff-mvt1-whole-20261020-night.record.json` (tree f1db97989, BEFORE 2.186/2.190/2.192): 702 `no_candidate`. Only mechanical splits are reported on it; the look rates come from S8. It has no 2.186 merge, which is why 36% of its refusals (253) are decided-twin duplicates vs 13% on S8.
- No gathers were run. Pages are PDF indices of the imslp984073 Litolff scan at 600 dpi (16 px = 1 sp).

## TABLE 1 -- my look at all 167 (S8), precedence: duplicate > not-accidental > real > merged
| bucket | n | what | what it points to |
|---|---|---|---|
| 0 duplicate (twin in another cell DECIDED) | 21 | same ink, the written copy exists | count as `duplicate_of_written`, not as a loss |
| 1 not an accidental | 90 (96 before the twin rule) | stem tip/piece 41, rest 26, fragment 11, barline sliver 8, dynamic/text letter 3, clef 1 | detector false positive: report as `not_an_accidental` (box refusal), not `no_candidate`; a stem tip is a thin (w<1 sp) box over the top of a stem, a rest is a blob with legs inside the staff |
| 2 real accidental, whole box | 36 | see Table 2 | |
| 2' real accidental, box is a cropped piece (ascender/top only, h<1.2 sp) | 6 | box lies off the cell's staff (8 of 11 with twins) and the 0.715/0.5 anchor lands on the piece, not the glyph | box height from ink (2.194 ink map direction) |
| 4 merged / cannot tell | 14 | one box over accidental + head + slur/stem (h 2.6-6.2 sp), or unclear | box shape from ink; no rule from height |
Unexplained remainder: none by bucket (every box has a look); 3 `unclear` looks and 1 `flat?` are my uncertain calls.

## TABLE 2 -- the 56 real/cropped/merged non-duplicates by mechanical cause (S8; `data/final_s8.json`, `n7_final.py`)
| cause | real | cropped | merged |
|---|---|---|---|
| class anchor: head fits at BOX CENTRE, not at the class anchor (natural boxed as flat) | 12 | 0 | 1 |
| fitting head refused: stacked_head_duplicate | 4 | 0 | 1 |
| fitting head refused: owned_by_another_staff | 1 | 2 | 0 |
| fitting head refused: on_a_dynamic_letter / tremolo_slash / clipped_fragment | 2 | 1 | 0 |
| heads in window, none at the glyph's height (head never boxed or boxed on only one of a stacked pair) | 9 (3 with the box off this staff) | 3 | 9 |
| no head box in the cell / heads only to its left / > 1.75 sp right | 7 | 2 | 3 |
| owner would fit by my recompute (not reproduced; 2) | 2 | 0 | 0 |
Tiles (my look, `data/` specs; images not committed): `dy>3` sheet -- 7 of 12 show a real natural at the height of the LOWER head of a chord whose lower head has no box at all or only the upper head is boxed; `refused` sheet -- the natural's head is the upper member of a pair of slanted hollow heads, boxed twice, the upper refused `stacked_head_duplicate`, the lower (wrong height) live; `nohead` sheet -- real naturals with an unboxed slanted oval right beside them.
Flat anchor is also biased: in the 106 DECIDED flat pairs the head sits a median 0.42 positions above the 0.715 anchor (naturals 0.00, sharps 0.05), so the flat's window is 0.98 wide on one side, not 1.4 (`n4_signed.py`).

## WHOLE MOVEMENT (tree NIGHT, 702; mechanical strata only, `n8_mech.py`)
decided-twin duplicates 253; short < 1.6 sp 140 (115 flat-class); thin-tall 18; doublesharp-class normal size 34; huge/merged 28; normal flat/natural/sharp-class 229 -- of which class-anchor 85, fitting head refused 31 (stacked_head_duplicate 9, owned_by_another_staff 11, dynamic letter 5, other 6), heads in window none at height 48, no head / left / > 1.75 sp 65. On S8 the same strata read (twin removed) short 59, thin-tall 8, doublesharp 21, huge 9, normal 49 -- and my look puts ~88% of short, 100% of thin-tall, 86% of doublesharp-class, ~11% of huge and ~15% of normal-size boxes in "not an accidental" (stem/rest/fragment/bar/letter). **If those rates carry to the whole movement (an estimate, one plate): ~190 of the 449 non-duplicate NIGHT refusals are not accidentals, ~190 are real accidentals lost, ~60 merged.** Not measured whole-movement by look.

## BRAHMS (brief; no Brahms crops by me -- 2.197's numbers, tree B 8 pages)
Brahms `no_candidate` 236: height off 1.4-2.0 pos 79 (the class-anchor effect), short box 39 (17%, vs 35-42% on Litolff), height off >2 32, head > 1.75 sp 46, head to its left 30. So Litolff-specific: the stem-tip/ rest/ barline junk boxes (short + doublesharp-class + thin-tall = 55% of S8 vs 17% short on Brahms), merged boxes, and unboxed slanted heads. Shared: the class anchor.

## WHAT EACH POINTS TO (nothing built)
- Junk (bucket 1, 54%): upstream false positives. A box over a stem top / rest shape / barline should leave as a counted `not_an_accidental`; doublesharp-class boxes on this work are 86% rests. Needs Sean's confirmation of the convention (no double sharps in Beethoven 5 i) and a few blind tiles before any rule (rule 7).
- Duplicates (13% S8, 36% night): count, do not call a loss; 2.186-like merge across neighbouring cells.
- Class anchor (12-22): lane 2.199 (class-agnostic owner anchor). Overlap noted, not fixed. The flat anchor bias (-0.42) says the flat bound should be re-centred, not widened.
- Refused fitting heads (stacked_head_duplicate, owned_by_another_staff...): a head-reading question (2.129/2.132 chords of seconds/thirds, Litolff slanted heads), not an owner question.
- Heads never boxed at the glyph's height (~15 S8): detector recall on slanted hollow heads in chords/touching slurs; a head-row question, upstream of ownership.
- Cropped/merged boxes (20): box shape from ink; no height threshold.

## FILES
`n1_features.py` (per-box features, re-implements the owner window), `n2_buckets.py`, `n3_tiles.py` / `n3b_heads.py` (contact sheets), `n4_signed.py`, `n5_sub.py`, `n6_twins.py`, `n7_final.py`, `n8_mech.py`, `looks1.py`/`looks2.py` (my look per tile -> `data/looks_all.json`), `data/final_s8.json`, `data/spec*.json`. Records live under out/ and library/_shared-records (not committed).
