# 2.183 -- the key signature as an area claim (claimed-area step 3)

Path: STAGED (GATHER files, ADJUDICATE consults). Flag `OMR_KEY_SIGNATURE_CLAIM`, default OFF, needs `OMR_CLAIMED_REGISTER`. Branch
`lane-2.183-key-signature-claim`. Measured on the 20261020-night records (main f1db97989) replayed from per-page slices (`replay_2_183.py`,
`compare_2_183.py`); OFF == main as recorded.

## 1. THE CAUSE (read this first)

**Twenty Litolff key-signature flats and four Brahms ones are written into the file as rests. The "2" was the tip.**
Census, not a diff: every cell-0 box written as a rest standing 3-10 staff spaces right of the cell edge, each looked at in a crop
(`out/print/` tiles, `key_flats_written_as_rests_litolff.json`): Litolff 20 of 20 are the bowl of a key flat (18 `rest8th`, 2 `restQuarter`);
Brahms 8 found, 4 flat bowls (`5/0/1/0/7`, `15/0/0/0/11`, `21/0/9/0/3`, `24/1/4/0/16`) and 4 real quarter rests after the signature (`7/0/*/0`).
The "2" (`glyph/15/1/7/0/1`, `15/1/8/0/3`) are the only two of the 20 that the 2.100-era 18-space `meter_column` happened to refuse as
`rest_is_a_meter_digit`; 2.177 retired that column and exposed them. The other 18 were never caught.

**Why the detector boxed them.** All 20 are PRODUCTION detector boxes (`reader=detector`; none is a 2.172 small-view box, `yolo_detector_view`),
class `rest8th`/`restQuarter` at confidence 0.26-0.77 (median ~0.4). The same ink also wears other names: 9 of 20 are doubled by another box
(`arpeggiato` 2, `accidentalFlat` 1, `noteheadBlackOnLine` 2, a second `rest8th` 4). They are the same glyph keys, same class, in every record
back to 20260930b, 20261010, 20261016, 20261018: not new, not caused by 2.172/2.177. Why the detector reads a flat's bowl as an eighth-rest
body is a training matter (class confusion on a shattered/merged flat): NOT explained here.

**Why the existing `in_a_key_signature_slot` gates missed them** (the window is `key_slots.key_slot_window`, drawn from the detector's own
key-class boxes on THAT staff), of the 20:
- 8: no window at all (the detector boxed no `key*` / accidental-shaped box near the clef on that staff);
- 11: a window exists but this flat stands beyond its last drawn slot (centre 0.04-1.9 sp past it; the next-slot rest rule needs <= 0.2 sp and
  missed by 0.3-0.64 sp in 3; a 1-slot window has no pitch to extend);
- 1: left of the window's start.
Unexplained: 0 of 20 for the gate miss. The CV header reader (`keysig_run_position`, a second look at the SAME raster) also undercounts on
16 of the 20 staves (own count < 3), so it falls silent with the detector (two witnesses off one raster); on 15 of 20 a SIBLING staff of the
same system reads the full 3.

**What the cause teaches.** (1) A gate whose evidence is built from the reader it polices catches exactly the cases where that reader was right
elsewhere on the same staff. (2) The page prints ONE key signature per system, at one x on every staff (page-facts §2), yet it is read per staff
-- the same single-staff blindness 2.177 fixed for the meter with `find_column`. (3) "2 key flats written as rests" was the residue of one
diff of one lane; the population needed a census of the class. (4) 16 of the 20 were once refused (20260930b, `rest_has_a_stem`) by an
accident that a later, unrelated change removed.

**The cleaner fix is upstream of this claim, so I stopped.** Read the key signature as ONE system object: find its columns across all staves
(the 2.177 `find_column` shape) and take the run's extent from the system's agreement (and the dossier's fifths), not from each staff's own
detector boxes. That is a new reader (a different source: other staves), not a window tweak; it would make the claim below catch the 18+4
(they would be NARROWED or refused by Sean's ruling on a column-derived area). The detector's class confusion is the deeper cause; neither
belongs in this lane without Sean.

## 2. What was built (flag OFF, parity-proved)

- GATHER `gather_key_signature_claim`: `Q.CLAIMED_AREA` owner `key_signature` per staff and cell, drawn from the 2.100 window
  (`key_slots.claim_window`) plus a run that opens with cancelling naturals (Sean 2026-10-20; `window_with_cancels`: naturals only BEFORE the first
  sharp/flat, one kind after, needs a clef). `boxes_inside[key]` = `named` (stands in the window, the 2.100 centre rule) + `stand_margin_spaces` +
  measured ink share. Cell 0: READ. A later cell: always NARROWED (see §3).
- ADJUDICATE `claimed_by.consult`: named -> REFUSE `claimed_by:key_signature` (margin = depth inside the run, staff spaces); ink inside the
  area but not standing, or any box of a NARROWED window -> NARROW `claim_narrowed:key_signature` (blue); flags / arpeggiati / arcs: refuse named only.
- ON retires the five gates (notehead, rest, flag, arpeggiato, arc): OFF runs them unchanged. `meter_rows_outside_key_slots` (the meter-glyph
  filter in `movement.py`) is not a gate on a box and stays on `key_slots`.
- The cancelling-natural path is covered by constructed tests only: neither movement changes key (0 windows with naturals on either plate).

## 3. Measures (both plates, OFF vs ON, exported file)

| | Litolff OFF | Litolff ON | Brahms OFF | Brahms ON |
|---|---|---|---|---|
| key claims (cell 0 READ / later cell NARROWED) | - | 207 / 69 | - | 497 / 38 |
| heads refused by the old gate / by `claimed_by:key_signature` | 12 | 12 (only-OFF 0, only-ON 0) | 2 | 2 (0, 0) |
| rests refused by the old gate / by the claim | 23 | 23 (0, 0) | 24 | 24 (0, 0) |
| narrowed by the claim | - | 1 real note (cell 1 of `6/1/3/1/4`, stays written) | - | 1 real rest (`11/1/0/10/6`, now blue) |
| notes in file | 11771 | 11771 (file byte-identical) | 22692 | 22690 (see note) |
| red bars | 508 | 508 | 650 | 650 |
| key flats written as rests | 20 | 20 | 4 | 4 |

Parity is exact for all five gates' refusals on both plates: the claim does the gates' job and nothing more. It fixes none of the 24 flats
(§1). First build error caught by the replay: a later-cell window with a witness staff was READ and refused a real eighth note
(`6/1/3/1/4`); 69 + 38 mid-system "key windows" exist on plates that never change key, so later cells are now always NARROWED -- the two
real marks narrowed above are the cost of keeping them at all (drop them if Sean prefers: they confirm nothing on these plates).
Brahms ON vs OFF also differs by 19 blue dynamics words, 2 notes and 3 glyph verdicts that no key claim touches (text/dynamics readers, beam
discount). Determinism control: a second Brahms OFF replay is byte-identical to the first, so OFF is deterministic and these differences
come from running ON -- UNEXPLAINED (nothing in the claim touches dynamics words; the injected key rows renumber the log's later ids, the
first suspect). Litolff ON is byte-identical to OFF, so it is Brahms-only. A reason is owed before this flag is ever turned ON.

## 4. Controls and checks

- Fast tier: `pytest -m "not slow" tools/omr/tests` 8713 passed, 12 skipped, 2 xfailed. `python3 -m tools.omr.staged.check` 193 (baseline 193).
- Tests `test_staged_key_signature_claim_2_183.py` (25): each control (a real rest/note/flag after the last flat) passes both ways, and mutating
  `stands_in_the_window` to "always" makes 3 fail.
- Blind tiles for Sean: `out/print/2.183-key-signature/` (12, orange box = where to look, means nothing; key `out/print/2.183-key.json`): 9
  drawn (seed 2183) from the 20 Litolff written-rest flats, 3 controls = real eighth rests after the meter. Purpose: Sean confirms the count
  (CLAUDE rule 7) before a key-object lane opens. The claim as built changes none of these.

## 5. Sean's tiles (2026-10-21)

"1-6 key flats 7-8. 8 rest 9. Key flat 10. 8 rest 11-12. Key flat" (`out/print/2.183-key-signature/answers.json`). All 9 cause-population
draws are key flats and all 3 controls are real eighth rests: 12 of 12 as the key. So the census count stands on his eye (20 Litolff + 4
Brahms key flats written as rests, not 2), and the claim as built keeps the controls. The per-system key reader proposed in §1 is NOT built;
it waits for Sean's go-ahead.

---

# 2.187 -- the key signature read ONCE PER SYSTEM

Path: STAGED GATHER (`key_object.py` PURE, `gather.gather_key_object`) + the 2.183 `claimed_by.consult` (unchanged except it copies the row's `key_object` onto the verdict). Flag
`OMR_KEY_PER_SYSTEM`, default OFF, needs `OMR_KEY_SIGNATURE_CLAIM` + `OMR_CLAIMED_REGISTER`. Branch `lane-2.187-key-per-system` (on `lane-2.183-key-signature-claim`).

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED.** Assumed: (1) the printed key signature has ONE count per system, read by the staves' agreement; (2) the
header between a staff's clef and its last accidental holds nothing but key accidentals (Sean 2026-10-12), so a box STANDING in a slot is refused; (3) a staff that reads no
slot of its own may be a transposing staff, so its area is only NARROWED (blue) and no key is ever written to it. Falsified by: a print-confirmed real rest/note standing in a
placed slot, or a transposing staff whose own signature differs from the system's count AND which carries a real mark where the system's count places a slot. NOT confirmed: Sean
has not seen this reader's tiles; two plates only; the dossier check is built but the pipeline admits a dossier only through a confirmed sheet, so ON without a sheet is
"dossier silent". Question for Sean (transposing staves): Beethoven's clarinets print 1 flat, horns none, the rest 3. Is it right that a staff that reads some slots of its own claims the
whole system run (so a mark at a slot it did not print is refused), and one that reads none is only narrowed?

## What was found (measured, not the 2.183 guess)

- The signature is NOT at one x on every staff: each staff's signature is typeset against its own clef, whose width differs (Litolff p2: clef edge 404-414 px, first slot 405-427). An absolute-column
  reader (the 2.177 `find_column` shape) split real columns in pieces and found a run of 1-3 where the print has 3. What the staves agree on is the COUNT and the slot PITCH (~1.1 sp).
- The raster alone does not read these slots (a crushed Litolff flat is a blob fused with its stem, the clef, a barline: connected-component pieces fail the size test on many staves);
  the detector's key/accidental boxes alone do not either (the 2.183 cause). Both are taken as candidate slots per staff (`staff_run`), and the count is the largest k that two staves read in full.
- 12 of the 20 Litolff pages' systems, all 8 per-plate... see measures below.

## The 24 known key flats written as rests (checked page by page: `known_flats_2_187.py`; REAL gather rows -> ADJUDICATE..EXPORT of each page's slice of the 20261020-night record)

| arm | refused as the key's own ink | written blue (narrowed) | still written as rest |
|---|---|---|---|
| base (main) | 0 | 0 | 24 |
| 2.183 only | 0 | 0 | 24 |
| 2.187, dossier admitted (pair or one staff + dossier) | 19 | 2 | 3 |
| 2.187, dossier silent (pair only) | 20 | 2 | 2 |

(`glyph/5/1/1/0/13` stays a rest in both: its staff read 3 slots itself but the flat's box stands 1.2 sp past the placed third; `glyph/7/0/10/0/12` and the two Brahms keys
`15/0/0/0/11`, `21/0/9/0/3` change with the dossier -- see the dossier note: a count the work prints as {0,1,3} made the pair's 2 "disagree" before the dossier-stands-in rule was fixed;
the table above is the pre-fix run, re-run in the final measure.) The 2 narrowed are staves that read NO slot of their own on a system whose other staves read 3 (`5/1/5/0/5`, `9/0/1/0/12`): blue, never refused.

Update after the dossier fix (`find_object`: the dossier bounds the count; a pair reading one more than the work prints is taken one down, a larger gap is a disagreement): Brahms p15
(4 pages' worth of the 24 are on p5/p15/p21/p24; p15 holds the first) now refuses all 4 of its flats' boxes with the dossier admitted (was 2 of 4 abstained). The full 24 are re-measured by `lane_report --from gather` once
2.189's detector cache is on main (a gather per arm is not run before it, coordinator's order).

## The 2.183 Brahms leak (19 blue dynamics words, 2 notes, 3 glyph verdicts): NOT reproduced; cause NOT found

Tested, each a control that could fail, all on the 20261020-night Brahms slices, adjudicate-stage replays of pages (no gather):
- ids: the same replay with the row-id counter started at 677000 (ids cross 999999 mid-run, where `obs:%06d` stops sorting numerically) and again +535 (the 535 key rows): byte-identical export. Ids are not the cause.
- hash order: three PYTHONHASHSEED values, byte-identical. Not set-iteration order.
- the whole movement in two chunks (the 8 sample pages; the other 19 + page 0), OFF vs ON (`OMR_KEY_SIGNATURE_CLAIM`), fresh process each: the only difference is the one rest the claim names (`claim_narrowed:key_signature`, +1 blue, +352 bytes); no dynamics word moves. Same-process OFF-then-ON: identical result.
So on every Brahms page the residue does not appear when the pages are replayed in chunks, with or without a shared process. It needs the whole 27-page record in one log (`replay_2_183.py`), which this lane may not run (measuring.md §0).
The coordinator's rule stands: ON must change nothing but what the claim names; `lane_report`'s no-op control (OFF==ON) is the check, and the 2.187 report below uses it.

## FINAL (2026-10-22): the transposing-staff guard, and the three measures

**Guard (coordinator 2026-10-22).** A staff that read fewer slots than the system's count claims, beyond the slots it read itself, a NARROWED (blue) part only, unless its instrument's written
accidental count is known and is at least N (`claim_for_staff(written_count=)`, READ then). At GATHER the part-to-staff join does not exist yet, so the count is never known today: a B-flat clarinet reading
its 1 flat claims one READ slot and a blue tail, never a refusal. Tests: refused with `written_counts={2: 3}`, narrowed with `{2: 1}` and with none. CONVENTION ASSUMED: a staff's own printed slots are
the only ones that may refuse a box. WHAT WOULD FALSIFY IT: a plate where a staff prints more slots than the detector/raster read AND a print-confirmed flat boxed as a rest stands there (it then stays blue, never lost
-- the cost). NOT CONFIRMED: Sean's answer is pending.

**The 24 known flats, final code** (`known_flats_2_187.py`, real gather rows -> ADJUDICATE..EXPORT of each page): main 0/24 fixed; 2.183 0/24; 2.187 with the dossier admitted: 10 refused (gone from the file), 13 written blue,
1 still a rest; dossier silent: 10 refused, 12 blue, 2 still rest. (Before the guard: 19-20 refused.) Blue is a flagged mark, not a fix: Sean can see and correct it.

**`lane_report --from gather --flag OMR_KEY_SIGNATURE_CLAIM --flag OMR_KEY_PER_SYSTEM`**, frozen sample, detector cache warm after the first arm (wall 2 h 44 m, not minutes: four 8-page gathers).
- Litolff: notes -6, rests -3, blue marks +18 -2, words +1; red bars 0 -> 0 (notes not written 2556 -> 2565). Brahms: blue marks +11, nothing else; red bars 166 -> 166.
- Judged right->wrong: 0 on Litolff (233 tiles) and Brahms (232 tiles); right->narrowed/gone 0; wrong->right 0.
- Control "OFF==record": NOT CHECKED in re-gather mode (reported by the command); the no-op OFF==ON control was not run in this lane (a no-flag run is a third 2.7 h gather pair).
- 11 tiles (`out/lane-report/2.187/tiles/sheet.png`, key `key.json`), seed 2188: the 2 cases that are real fixes on the print are tiles 1 (a bass-clef key flat written as a quarter NOTE, now gone) and 5 (an alto-clef key flat written as an eighth rest, now gone);
  tiles 2, 3, 7, 8, 9, 10, 11 are blue marks on what look like REAL notes standing just after a short signature (the NARROWED tail reaches 1-1.8 spaces past it): a cost, not an error; tiles 4, 6 are controls, unchanged.
  So of the 9 case tiles, 2 are fixes and 7 are blue-on-real: the tail's generous reach (needed for the p5 drift case) is paid for in blue notes. Sean's call: tighten the NARROWED tail to the placed slots' own width (fewer blue notes, more flats left as rests).
- `-6` notes / `-3` rests on Litolff: 2 shown above are key flats; the other lost symbols were not looked at on the print (the report draws 9 tiles from 12 changes).

---

# 2.187b -- the key TAIL judged by what the staff may print (2026-10-22; Sean's tiles and three rulings)

Path: STAGED. GATHER `gather_key_object` MEASURES each tail box's own ink (`key_object.measure_tail_box`: shape, staff step against the lines AT that x, x) and files the
slots' x (`tail_info`); ADJUDICATE `claimed_by.consult` DECIDES (`key_object.judge_tail_box`, given `header.key_tail_context`). No stage was reordered: the claim is still filed at GATHER and
consulted at ADJUDICATE, where every claim has always been consulted; what moved is that the NARROWING of the tail is no longer a reach but a judgement. Flag `OMR_KEY_PER_SYSTEM`, still OFF.

**Cause (rule 3, lesson).** The tail was narrowed for EVERY box in it, so 7 of Sean's 9 changed tiles were real notes. The cause was that it asked "is the box in the reach?" and never "could this staff
print an accidental here?". Sean's question ("does the guessing know transposing instruments?") found the second hole: the written key was never known. The lesson, from the first build of this
fix: a staff's WRITTEN key must not come from the staves' own readings (`expected_fifths`' part-majority tier). On Litolff, 8 of the 13 flats still standing after the first build were on
concert-pitch staves (Fl., Ob., Fag., Bassi, violins) whose part majority was one or two flats SHORT -- the same missed flat misreads the part, and two readings of one missed ink fall together
(CLAUDE §4). The written key is now the system's COUNT (the staves' agreement, a different witness) + the sign of the document's key stretch (flats only vote from the staff's own slots, two with no
sharp: a crushed flat's bowl reads `sharp`, measured 9 of 10) + the staff's transposition READ off its label or its part's, never defaulted (`_transposition`; an unlabelled clarinet is not the B-flat one).

**What a tail box must be to be narrowed (all of Sean's rulings, 2026-10-22).** Slot k of the run holds ONLY the k-th accidental of the fixed order (Bb Eb Ab Db Gb Cb Fb / F# C# G# D# A# E# B#), at
a FIXED staff step for the clef (`key_signature_geometry.slot_positions`, the table the fitter and the resolver read: treble, bass, alto, tenor), measured against the staff locally. So a box in
the tail is NARROWED only if (a) its shape is not a CLEAR contradiction of the run's accidental type (flat for a flat key, sharp for a sharp key, a natural only where the key changes -- the
cancelling naturals come FIRST, at the OLD key's steps, then the new key's accidentals counted from the cancels' end -- any of the three where the type is unknown); (b) its centre stands at slot
k's step within `POS_TOL_STEPS` = 0.5 step (the fitter's `max_residual`; key_slots has only the x tolerance, `SLOT_TOLERANCE_SPACES` 0.5, used for (c)); (c) it stands at slot k's x
(`SLOT_TOL_SPACES` 0.6 + `SLOT_DRIFT_SPACES` 0.2 per placed slot, from the staff's own last read slot or its clef edge); and (d) k is within the staff's WRITTEN count where that is known
(a horn: 0, no tail; a B-flat clarinet in three flats: 1; a staff whose concert key is sharps but whose written key is flats or the other way round takes its OWN type; a transposing staff in
sharps may reach past the system's count). A box that fails any test is LEFT ALONE: neither refused nor blue. The slots a staff READ itself are unchanged (refused).
CONVENTION: the order and the clef steps are Sean's (confirmed). MEASUREMENTS (may only narrow): the 1.25-step flat anchor (whole flats: median 1.23-1.26 steps above the pitch over 824 read flats; a bowl
the detector boxed alone sits on it, so the offset runs 0 -> 1.25 with the ink's height), the x tolerance, the drift.

**Measured, and what did not work (rule 7).**
- The 2.190 shape reader reads the WHOLE glyph or nothing: on the detector's box it called a flat's bowl a `sharp` (a crushed Litolff flat is boxed as a rest over its bowl alone). Read off the accidental-sized
  raster piece that overlaps the box (the `staff_run` size/fill/level tests) it reads 5 of 15 known tail flats (1 right, 1 `natural`, 3 `unclear`; the other 10 have no whole piece), and 53 of 66 real tail notes
  with a piece read `sharp`. So the shape can only REJECT (a clear contradiction), never accept; an unreadable crush is neutral.
- A solid-head test (erosion of the box's ink by a disc of 0.4-0.8 space) was built and DROPPED: at 0.65 space 8 of 10 crushed flat bowls survive it as heads, while 25 of 316 notehead boxes do not (hollow / half heads). It would reject the flats and admit hollow notes: no use. A notehead is excluded by x, by step and by its sharp-reading ink, not by being a head; a note exactly at slot k's x and step is the remaining leak (counted below as notes turned blue).
- No stem-direction feature separates a key flat from a down-stem head in the data (a head with a stem reads `sharp` on both corners; the flat rises on the LEFT, which BL/TR already say). No new measurement added.

**Staves by where the written key came from** (known_flats pages, real gather -> ADJUDICATE of each page's slice of the 20261020-night record; `tail_report_2_187b.py`): see the lane-report section below for the sample pages.

## 2.187b -- clean measure (2026-10-23, quiet box after the overnight; tree = 2.187b merged with origin/main)

Why this replaces the 2026-10-22 numbers: re-gathers run while other lanes gathered hit Surya's 20 s guard in one arm and not the other, so unrelated kinds (words, dynamics, clefs, ties, beams) changed between two arms of the SAME tree (a no-flag control on Brahms: notes +92, rests +62 -80, pitches ~2, red bars 161 -> 166). Those runs are void. The runs below had 0 Surya failures in the key arms; the Litolff no-flag control (`out/lane-report/2.187c-ctl-lit`) printed NOTHING CHANGED.

- `lane_report --flag OMR_KEY_SIGNATURE_CLAIM --flag OMR_KEY_PER_SYSTEM --from gather`, frozen sample. **Litolff:** notes -6, rests -3, blue marks +3 -2, words +1; red bars 0 -> 0 (notes not written 2554 -> 2563). **Brahms:** blue marks -17 and nothing else; red bars 166 -> 166 (the bar-1 mixed-run exclusion turning INFER guesses into marker reads). Judged answers right->wrong 0 on both plates (233 / 232 tiles).
- The 24 known key flats (`known_flats_2_187.py`, real gather rows -> ADJUDICATE of each page): main 0 fixed, 2.183 0, **2.187b 10 refused (gone from the file), 9 written blue, 5 left alone (still a rest)**. Before the tail judge: 10 / 13 / 1.
- Notes in a tail turned blue: 5 of 287 notehead boxes held by a tail (were 35 with the unjudged tail on the same pages).
- Tiles: `out/lane-report/2.187c-key-lit/tiles/sheet.png`, key `key.json` (seed 2194, 9 changes + 3 controls, no two tiles on one ink). Brahms' only change is lost blue marks (`out/lane-report/2.187c-key-bra/`).
