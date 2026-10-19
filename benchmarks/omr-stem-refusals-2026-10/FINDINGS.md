# ROADMAP 2.169: the stem finder refuses real stems (STAGED GATHER + ADJUDICATE; flag `OMR_STEM_PAIR_AT_HEAD`, default OFF)

Records: 20261016-night (main 1d42c4aa); tree merged with main 261495f1 for tests; replays ran on the pre-merge tree, both arms alike.
Probes: `probe/` (`extract_rows`, `reach_2_169`, `causes_2_169`, `replay_2_169`, `tiles_2_169`, `sheet_2_169`, `run_all.sh`).

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
**ASSUMED:** a stem is the line a notehead hangs from: it ENDS at its head (up-stem on the right, down-stem on the left). An accidental's
strokes do not end at a head: a sharp/natural is two verticals ~0.5 space apart reaching past the head at both ends, a flat's stroke
stands clear on the left. A chord stem runs past the head it is read at, to the far head, and is longer than any accidental (taller than
~3.5 spaces; the 3.5 is a figure from the engraving literature, not measured on a second publisher, so it can only NARROW).
**FALSIFIED BY:** a stroke with an end in a detected head's rows and columns that is an accidental's (a head box swallowing its sharp;
NEW adds 0 strokes on an accidental box on both plates, GATE adds 2 on Brahms), or Sean reading a rescued note as unstemmed.
**NOT CONFIRMED:** the tall-stroke clause beyond Litolff tile 3; Sean has not seen the 2.169 tiles.
**Confirmed by Sean (2026-10-18, 2.167 tiles):** the refused "paired with a neighbour" strokes on tiles 1, 3, 7, 9 are real left stems (4/4).

## What `OMR_STEM_NOTEHEAD_GATE` is, and why it was never put to Sean
STAGED+LEGACY shared `line_detection._drop_paired_strokes`, behind a flag wired in `gather_cv_lines` (heads handed over always; flag read in
`detect_stems`). ON: a stroke whose box overlaps ANY detected head box is never pair-deleted (benchmarks/omr-stem-notehead-gate-2026-09).
Built 2026-09-20, default OFF; the lane that built it recorded its own objections: it couples Q.STEM to the detector and the reference
sheet's page total did not improve (27 = 27), and it was never put to Sean as tiles. On the 2.167 sample and whole movement it does what
this item needs (below); NEW is the same idea stated as the convention (ends at its head) instead of "overlaps a head box".

## The rule behind "paired with a neighbour", and why it misfires
LEGACY+STAGED `_drop_paired_strokes`: two vertical strokes within 0.9 space, overlapping vertically >= 60% of the shorter, are an
accidental's two strokes; BOTH are deleted ("successive notes are set further apart than an accidental's own strokes"). A human tells them apart
by what they touch: a stem is attached to a head; an accidental stands apart. The premise (note spacing > 0.9 space) is a cut-off tuned
where the rule was proved (a LilyPond sheet; 14 hand cells); on Litolff notes and chords of seconds are set closer (62 of 80 pair-deleted
strokes that carry a head were paired with another that carries one). CLAUDE.md section 4: a cut-off is a measurement and may only narrow.
The fix narrows it by the convention: a stroke is exempt (as the SUBJECT only; as a partner it still condemns a sharp's stroke) when one END
stands in a detected head's rows (+- 0.25 space, the 2.155 slack) and its columns overlap that head's, and it is not on an accidental/key box;
or it is taller than 3.5 spaces and runs through a head's columns with that head's centre inside it (a chord stem).

## Reach (whole movement, no re-gather; `reach_2_169.py`; CONTROL: OFF arm = the record's stored Q.STEM rows)
| | Litolff | Brahms |
|---|--:|--:|
| cells faithful | 5,376 of 5,377 | 6,685 of 6,685 |
| NEW strokes added (cells) | 358 (213) | 233 (178) |
| ... on an accidental/key box | 0 | 0 |
| ... touching no head by the contact test | 0 | 6 |
| no_stem heads gaining a stem (unique heads) | 346 of 2,630 | 280 of 7,475 |
| GATE (old flag) strokes added | 390 | 271 (2 on an accidental) |
Litolff, causes (`causes_2_169.py`, nearest refused run beside each of the 2,630 no_stem heads): paired 310 (NEW connects 306), too short 425
(connects 8), too tall 330 (4), too wide 222 (25), cell edge 100 (1), accepted-but-fails-contact 125 (2), no run beside 1,118 (copies owned by
another staff, whole notes, rests, non-notes). So the PAIRED cause is closed (306 of 310); the others are separate items. NEW is within
the GATE's reach (346 vs 347) and, unlike it, never keeps an accidental's stroke.

## Sean's 2.167 tiles scored by the rule (Litolff; Sean's reading in brackets)
Real stems: tile 1 (yes L), 3 (yes L), 5 (yes L), 7 (yes L), 9 (yes L): NEW connects all 5. Tile 4 (real R stem, accepted by the finder but
failing the contact test) is a different cause and stays. Not a note: tile 2 (too wide), tile 6 (accepted), rest tile 8: NONE connected. Tile 3
needed the tall-stroke clause (a 7.7-space stem whose chord's far head is missed: first version missed it).

## Replay, GATHER + ADJUDICATE, ARM vs CONTROL (`replay_2_169.py`; slice = systems holding a changed cell; ADD-ONLY injection)
New stems' own rows (stem, tip ink, slash, beam join, new beam strokes) are added; every old row keeps its id. LIMIT: rows other gather
functions derive FROM stems (`notehead_stem_cross_ink`, `stacked_head_fit`, `beam_stem_levels`) are not re-derived. CONTROL vs the stored
first duration verdict: Litolff 19 of 14,404 differ (restricted-re-decide noise), Brahms 0 of 26,273. A first version that removed old
stem rows left dangling ids (another reader's rows pointed at them) and was discarded.
| | Litolff (30 systems, 719 glyphs in changed cells) | Brahms (178 changed cells, 1,408 glyphs) |
|---|--:|--:|
| head_stem no_stem -> a stem (decided) | 313 | 270 |
| head_stem no_stem -> narrowed (two_stems / unison) | 33 | 10 |
| decided one_stem -> narrowed (neighbour now two stems) | 16 | 5 |
| duration verdicts changed | 136 | 266 |
| narrowed -> decided / decided -> narrowed | 53 / 17 | 103 / 30 |
| decided -> decided (different value) | 60 (45 quarter->half) | 133 |
| decided -> abstained | 5 | 0 |
**Judged tiles (`judged score`, same slice both arms):** Litolff 0 of 7 judged glyphs in changed cells changed (202 judged glyphs in
the slice, totals identical). Brahms 3 changed of 11: one narrowed->right (2.81 tile 14), two right->narrowed holding Sean's value (2.162 tile 18,
rhythm-leftovers-review 4). **No right->wrong on either plate.** Judged coverage of the changed notes is tiny (18 of 2,127), so the 60 + 133
decided->decided moves are UNJUDGED: the tiles below test them.
Reading of the 45 Litolff quarter->half: a hollow head with a stem is a half note; before, with no stem, it was read quarter (my eye on a few crops, not evidence).

## Tiles for Sean: `out/print/2.169-review/` (11 blind tiles; key `out/2.169/tiles-key.json`; tiles and key from one run, asserted equal)
Blue box on one note, nothing else drawn. Question: "What is the written value of the note in the blue box (4, dotted 4, 8, 16 ...)?"
Roles: 5 changed value (arm differs from control), 3 changed but same value, 2 untouched notes in changed cells, 1 ordinary note elsewhere
(the controls can fail: our reading may be wrong). Not asked again: Sean's 11 answered 2.167 tiles.

## Tests and check
`tools/omr/tests/test_stem_pair_at_head_2_169.py` 15 pass (flag off = shipped finder; sharp beside a stem still condemned; a crossing stroke
shorter than 3.5 spaces is not exempt; accidental box never exempt). Fast tier on the merged tree: 8,493 passed, 12 skipped, 2 xfailed.

## Limits / next
Contact-failure (tile 4), too short/tall/wide and "never a candidate" are untouched (3-5 of the 40). Rule on a third publisher unmeasured. The
tall clause's 3.5 is a literature figure. Flag stays OFF; landing needs Sean's tiles. Bar-sum / narrowed buckets of 2.167 shrink only through
the no_stem -> stem moves counted above.
