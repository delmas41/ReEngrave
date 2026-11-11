# 2.292 — Why key and clef are inferred when they are printed (2026-11-10)

STAGED, measure only. Branch `lane-2.292-why-key-clef-inferred` ce04ca9fb. Written by the manager from the lane report (the lane's own Write was refused by a hook). Scripts are on the lane branch named below.

## Cause and process lesson
The filled keys and clefs are almost always RIGHT; the notes are blue because ADJUDICATE abstained and INFER
(`fill_part_key`, `fill_clef_gap`) supplied the answer. There is no cross-system carry to stop: each staff-system's
clef and key is read from its own header (clef read on 181 of 184 Litolff staff-systems, key on 137). Main cause:
`adjudicators/header.py:_marker_run` takes both the COUNT and the KIND of the key from the detector's key boxes; on
Litolff the flats are crushed, so boxes are missing or classed natural/sharp and the staff abstains — while on 15 of
31 such staff-systems the GATHER key object (2.187) already had the right count on the same raster.
Lesson: ask of every blue mark whether the answer was already in hand on this raster.

## Size (20261104-night slices)
Blue for pitch: Litolff p1-2 15.0% of notes; nine Litolff pages 8.1% of notes (45% of the blue), page by page 0-18%;
Brahms p0,4 none. Causes over nine Litolff pages (368 notes): crushed flats, marker run short (15 staff-systems,
129 notes); flats read as natural/sharp or mixed (9, 107); clef unread → clef filled and key `needs_clef` (3, 90);
printed key with no marker box (3, 34); right count but no peer in the system check (2, 8).
Not found: a stopped carry, an unidentified staff, a transposing part's key voted away, out-of-order slots.

## Sean's tiles (answers/answers-2.292-r1.json)
Every filled key he could judge equals the printed one (11/11); both filled clefs match; one tile was cut off by our
crop and is unjudged.

## Proposed (not built)
A. Take the key's KIND from the slot steps of the key object's measured slots (flats and sharps sit on different staff
steps in their fixed order) — ~236 notes. B. A header-clef read for the merged C clefs and one F clef (90 notes).
Neither promotes a guess; both make a printed mark count as read.

## Not verified
Brahms on two pages only (the 8-page replay was too slow and was killed); the slice predates this week's landings.
