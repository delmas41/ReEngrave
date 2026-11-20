# Which readers are tuned to one publisher (ROADMAP 2.325), 2026-11-19

STAGED path and the shared readers it calls. Read-only audit by an agent, filed by the manager; the
per-constant table is `INVENTORY.md` (71 hand-checked rows marked `*`). Asked for by Sean (DECISIONS
2026-11-19, "NO READER TUNED TO ONE PUBLISHER"). **How far to trust it:** classes and plates come from each
constant's own comment by keyword (about 35 checked against the commit that set the number); for 1,004 of
1,535 constants what happens at the boundary is not known; no benchmark was re-read for whether both sides of
a boundary were measured. It is a map of where to look, not a measurement.

## Cause, and what it teaches

Nearly every cut-off is in staff spaces. That evens out page size and DPI; it does nothing about SHAPE. The
fragile numbers measure one publisher's glyph proportions -- C-clef bar thickness, head width, the size of a
head's hole, flag and rest shapes, a flat's stem, digit shapes -- each set on the one or two plates where a
lane found its fault, often only on the side of the boundary that lane was fixing. Lesson: "in staff spaces"
has been taken for "general", and "only narrows" for "safe"; with page-wide readers and no old reader kept
beside them, a refusal now LOSES the mark (2.324 r1: Brahms's tenor clef).

## Counts (agent's, by keyword)

1,535 named constants (+105 inline, unclassified). Rests on a convention 110; relative to the page's own ink
or local staff 238; an absolute figure tuned on our plates 937 (catch-all, over-counts); names a plate or is
publisher-specific 165; depends on pixels/scan 45. Decides 243, refuses 190, narrows 98, unknown 1,004. Tuned
figures that DECIDE or REFUSE (against CLAUDE.md §4): at least 298. 168 comments name a plate (Litolff 79,
Brahms 56, both 33). No reader branches on a plate name, document id or page number.

## The most likely to fail on a third publisher (agent's ranking)

1. Notehead fill (hollow vs solid): hole-size shares, one pair from Brahms p0 only -> half vs quarter written
   plain and wrong. Musician's test: compare with this page's own solid heads.
2. C-clef thick bar (page-wide reader, Litolff only) -> clef lost (being fixed in 2.324 r2).
3. C-clef locator (symmetry, width, height from a Litolff sweep) -- still feeds `Q.CLEF` today.
4. Rest sizes (heights from Brahms tiles; one Litolff case) -- and a CONVENTION gap: some 19th-century French
   and English plates print the quarter rest as a mirrored eighth rest.
5. Flags at the stem tip (~15 constants, several from single Brahms cases) -> eighth vs sixteenth decided.
6. Beam thickness as an absolute (the 1.75 x local line rule is robust; keep that one).
7. Counting key flats (flat stem run from 56 Litolff stems; slot spacing).
8. Meter digits matched to a modern font (Bravura); a Litolff "3" matches its "6".
9. Head width floors -> cue and grace heads refused.
10. Stems: "longer than 8 spaces is a barline" (Litolff only); attach tolerances.
11. Arc stroke thickness -> a heavier slur never traced.
12. Arc binding reach. 13. Hairpins (one Brahms page). 14. Dynamic letters. 15. Direction lexicon (Italian
plus a little German/French). 16. Ledger rungs. 17. Barlines: two RAW-PIXEL constants unchanged since May.
18. Staff finding pixels (low risk). 19. Header window (a pixel figure from a Litolff layout). 20. Accidentals.
21. Augmentation dots. 22. Tremolo end test (no source named). 23. Pixel floors restated from the old reader.

## Already robust (the patterns to copy)

A cut from the convention with both populations measured and a gap between them (`ink_attachment`); the
F-clef second witness using the page's own F clef as template; beam vs the local line; the stroke map reduced
to a fixed number of pixels per staff space; line positions measured locally; staff detection swept on seven
or more works; arc thickness against the trace's own median; agreement across staves.

## Outcome

No fix in this item. The list is input for choosing what to make relative to the page's own ink, largest
risk first; and it says a third publisher's plate in the acceptance set would test all of it at once.
