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
out/print/2.247-tiles (key outside tiles/): 3 places where the written alteration changed, 3 boxes now unclear, 5 class-vs-strokes disagreements, tile 12 = the 2.242 r2 tile 1 place. Sean's answers pending.
