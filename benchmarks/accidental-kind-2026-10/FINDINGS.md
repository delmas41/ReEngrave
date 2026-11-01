# ROADMAP 2.247 -- accidentals labelled by their shape (STAGED)

2026-10-31, branch `lane-2.247-accidental-kind` c3eb17b6e (Opus), flag `OMR_ACCIDENTAL_KIND` default OFF. Written by the manager from the lane's report (the lane's own write was refused by the hook). Scripts in this directory are on the branch.

## Cause and process lesson
- The detector class does NOT decide the written kind. 2.242 r2 tile 1 (Litolff p2 `glyph/2/1/3/4/5`, class `accidentalFlat`) traced GATHER -> file: the 2.201 stroke reader reads two stems (the right one 1.12 sp lower at the top, only 0.18 sp lower at the bottom -- Sean's faint lower stroke) and the file writes a NATURAL (blue) on F4. Tiles 7 and 9 likewise. Tile 2's mark is read natural but the following note gets no accidental (an owner problem). The "flat" on Sean's tiles was the tile key's `cls`, not what we wrote (`trace_tiles.py`).
- Where the kind DOES go wrong: 2.201's flat test is "one stem plus any piece low and to its right", so a PIECE of a natural (a stub of the left upright plus some bar, the right upright faint or cut by the box/cell edge) reads as a flat (2.201's own tile 2, left open). Second route: where the strokes are unclear, the class writes the kind with only itself as a candidate.
- Lesson: a tile key's `cls` is the detector's label -- trace the place to the exported file before opening a lane on "the reader trusts the class". A shape test that names a kind because something is MISSING (no second stem) must also see that kind's own mark at its own size.

## How often (2.201 type vs class, per box, 20261029-night slices, frozen sample; `census.py`)
- Litolff: flat->natural 89, flat->unclear 179, sharp->unclear 67, natural->flat 5, sharp->flat 8.
- Brahms: flat->natural 154, sharp->natural 93, flat->unclear 128, sharp->unclear 122, natural->flat 6, sharp->flat 10.
- Written file (2.242 r2 ON arm, L p2,4 / B p4,5; `written_join.py`): the class decides the kind for 8 of ~51 written accidentals on Litolff, ~11 on Brahms.
- Lane's own crop look (not evidence): Brahms class-flat/sharp written-natural cases look like real naturals; ~4 of 6 Brahms natural->flat look like naturals; 9 of 11 natural->flat boxes are stubs (stem 1.2-1.5 sp, piece 0.5-0.75 sp) where Sean's 71 hand-box flats have stems >= 1.88 sp.

## What was built (`accidental_family.read_type` / `guess_of`; gather.py unchanged)
- A flat must be flat-sized: with the flag, a one-stem flat needs a stem >= 0.7 x the SMuFL flat height (1.72 sp) and bowl pieces >= 0.84 sp tall, else `unclear` (`flat_too_small`).
- Faint lower stroke on a two-stem natural: right stem starting lower at the top but stopping well above the left at the bottom -> `unclear` (`right_stem_lower_bottom_short`).
- Both cases carry natural AND flat as candidates; `guess_of` writes them GUESSED (blue) beside the class; the written value stays the class's type with both kinds attached; nothing is decided natural (the cut-offs only narrow).
- Dropped: a "rounded bowl shoulder" test lost 53 of Sean's 71 hand-box flats (the printed bowl rises to the right).
- Known limit, pinned by a test: a full-size natural whose whole lower stroke is lost still reads flat.

## Numbers
- Sean's 142 hand boxes (Brahms pp.0-3): ~1 of 71 flats under the floor (not re-run with the final rule -- not a measured figure).
- 2.201 per-box type control: 21 boxes changed (L 14, B 7), all flat -> unclear; written alteration changes in 3 (a sharp class -> #, a double-sharp class -> ##, a natural class -> natural) (`type_control.py`).
- Lane report (2-page control, `--from gather --cell-map master`): before merging main L blue +4, B unchanged; on the merged tree (2.242 ON) the exported file is UNCHANGED on both plates; judged right->wrong 0, unwritten->wrong 0.
- Fast tier 9,513 passed before the main merge; after it only the accidental + flag-triage tests (60 passed).

## Double sharps (2.245 hand-off, not built here)
Litolff p4 `glyph/4/0/8/5/13`: strokes see a 1.75 sp stem and no bowl; an x has no stem -> unclear -> the class writes ##. Most double-sharp boxes are far taller than the glyph (> 1.5 x its 1.0 sp): L 42 of 51, B 82 of 108, almost all unclear; the files carry 3 (L) and 2 (B) double sharps on the 2-page subset, probably all false. A wrong-kind box -> 2.245; a per-class "box at most k x its glyph" ceiling is available from `size_census.py`.

## Prior work
2.196 (natural offered 52% vs flat 79%); 2.197 (Brahms naturals boxed as another class 12 of 27); 2.201 (its tile 2 is this case, left open); 2.190 corner densities (superseded); ink-rules and page-facts: no kind rule; LEGACY: class only.

## Tiles
out/print/2.247-tiles (key outside tiles/): 3 places where the written alteration changed, 3 boxes now unclear, 5 class-vs-strokes disagreements, tile 12 = the 2.242 r2 tile 1 place. Sean's answers 2026-10-31 (answers.json; DECISIONS): right 1, 4, 9, 10, 11, 12; wrong 2, 3 (half a natural -> flat), 5 (slash -> #), 6 (sharp -> ##), 7 (real flat -> unclear, box cuts its stem), 8 (flat -> natural). Sean: the boxes sit a little high; measure accidentals from their own ink as with notes.

## Round 2 (2026-10-31, lane-2.247-accidental-kind 17a9a6861; written by the manager from the lane report)
### Cause and process lesson
Sean's "a little bit high" is a box CUT short of its mark, not shifted: accidental-class boxes stopping >= 0.5 sp short of the ink at top or bottom: Litolff 18 of 183, Brahms 84 of 1,057; a box shifted whole off its mark: L 0, B 2 (`offset_census.py`, r2 control pages). A one-stem test on the upper part reads a flat (r1 tiles 2, 3, 11). Lesson: give a reader the WHOLE mark before it reads; the box is only where to start looking (as with noteheads) -- 2.242 had built that for accidentals and the kind reader was not using it.
### Built (accidental_family.py; gather_accidental_positions)
1. Kind from the ink: `ink_members_and_extent` grows from every stroke the box touches along touching strokes within one accidental's SMuFL size (~1.3 x 3.9 sp); no head-owned strokes, none > 3.7 sp, no partial strokes touching a head; a 2.242 whole stroke read by its parts; staff-position anchor on the ink. key* boxes keep the 2.201 extent (growing them lost 4 Litolff keys in the first control).
2. The class's sign is not written on unclear strokes when the shape excludes it or the box is > 1.5 x its glyph height (2.245's double sharp) -> abstain (r1 tiles 5, 6). A lower size bound was tried and dropped (lost 34 written flats).
3. Tile 8 (flat read natural): the bowl's right side read as a second stem; a right "stem" no taller than a flat's bowl (1.2 sp) that ends level -> unclear, GUESSED with both kinds. The 2.242 r2 tile 1 natural (right stem 2.0 sp) still reads natural.
### Sean's r1 places (ON arm)
2 natural read (fixed); 3, 11 natural blue (fixed); 5 nothing written (fixed); 8 flat blue (fixed); 4 flat blue (fine); 7 flat blue, still flat_too_small -- the master-cell stroke map gives no ink above the box (re-cut cells read a full 1.94 sp flat); 6 nothing written (abstains, does not read the sharp); 12 flat blue with natural as candidate (still wrong kind).
### Numbers
- 2.201 type control (L 314, B 1,515 boxes): L flat_too_small 14, right_stem_bowl_sized 9, 5 now natural; B 36, 24, 8 others; one-arm-only rows L 28, B 68 (`data/type_control_r2.json`).
- Three measures (L p2,4,10 / B p4,5,12,19; --from gather --cell-map master): L accidentals +1 -8, pitches ~55, blue -43, clefs +9, keys +10 -7; B accidentals +7 -18, pitches ~31, blue +9 -22; judged right->wrong 0, unwritten->wrong 0.
- WARNING: the OFF arm did not reproduce on Litolff -- the same OFF code gave 41 clefs in one run and 32 in the next, with different key signatures at bars 1, 18, 33, 63, 77 (the second run's ON keys equal the first's OFF). The Litolff clef/key/pitch deltas are largely run-to-run noise. Not yet explained (the manager deleted the session scratchpad mid-run at ~13:45; whether that or something else made two gathers differ is NOT checked).
- Fast tier 9,531 passed before the last main merge; after it the accidental + flag-triage tests (64).
### Tiles
out/print/2.247-r2-tiles: places of r1 tiles 7, 5, 3, 8, 2, 6 + 6 places where the written alteration changed (5 natural -> flat by the bowl rule, 1 flat -> sharp). The lane's own look: tile 12 (natural -> flat) may be a real natural.

### Sean's r2 answers (2026-10-31)
Right 10/12: 1, 4 flats; 2 slash (nothing written); 3, 5 half naturals (natural); 6 sharp (b -> #); 8-11 flats (bowl rule natural -> b, 4 of 5 right). Wrong 12 (most of a natural, bowl rule wrote b). Missed 7 (a sharp under an oversized double-sharp box: nothing written).

## Round 3 (2026-10-31, be772cfbf; manager from the lane report)
Tile 12 (Brahms p4 glyph/4/1/8/6/7) is a natural with its lower stroke lost: right upright 1.06 sp, ends level, so the r2 bowl-side rule caught it. What separates it from flats 8-11 is where the right stroke STARTS below the left stem's top: 0.82 sp (natural) vs 1.19-1.31 sp (flats). Rule narrowed: the bowl-side reading applies only where the right stroke starts >= `BOWL_SIDE_TOP_MIN_SP` = 1.0 sp below (a two-plate cut-off; it only narrows). Moves vs r2: 7 rows back to 2.201's natural, written sign flat -> natural at 3 (tile 12, Brahms glyph/12/1/11/1/1, Litolff glyph/4/0/5/10/3) -- Sean: both naturals. Type control r3: L 289 same, flat_too_small 14, bowl-side 6, 5 natural; B 1,452 same, 36, 20, 6 others. Three measures: L accidentals +1 -8, pitches ~15, blue -26 (no clef/key changes this run); B +8 -18, ~32, blue +10 -22; judged right->wrong 0. LANDED ON 2026-10-31.
