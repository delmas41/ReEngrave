# ROADMAP 2.174 -- a decided quarter under a beam we do see (STAGED GATHER+ADJUDICATE; flag `OMR_STROKE_AT_STEM_TIP_NARROWS`, default OFF)

Records: 20261018-night (main bd5b8f7cc). Branch `lane-2.174-quarters-under-seen-beams`. Probes: `probe/`. Slices cut with 2.165's `pages_2_165.py`.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
1. **A beam joins every stem it spans AT THE STEM'S END** (Gould; omr-beam-confirm-2026-10 s9.2; Sean 2026-10-16 "the stem tip decides beamed or not"). A stroke the filters KEPT at a head's own stem end is a witness the head may be beamed; the plain quarter written over it is "cannot tell" written as an answer (rule 8). Falsified by an unbeamed quarter this narrows whose stem end only touches a neighbour's beam (the blind tiles).
2. **An eighth is decided only on a beam or flag READ on that stem** (CLAUDE s4). This lane NARROWS (value / one beam level, equal support), never decides an eighth.
3. The zone (0.6 space across the stem, 0.6 along it) is 2.81's tip reach with the across distance widened from 0.3, because the CV reader erases stems before tracing (measured ~0.45 space, Brahms p10 `glyph/10/0/9/2/0`). A cut-off, NOT CONFIRMED on a third publisher, so it only narrows.

## 1. Brief from the tree
2.38 join reader, 2.146 tip decides (ON), 2.153 parked OFF, 2.165 ON, 2.170 ON. `adjudicate_duration` already narrows `beams_ambiguous` when `possible > certain`; these quarters have `possible == 0`: `_beam_levels` matches the head's CENTRE column or a join witness, and the join reader said "stroke_does_not_reach_stem_horizontally".

## 2. Population and random sample
Population = first `adjudicate_duration` verdict DECIDED `head_and_marks`, written 1.0, no dots, head not open, a CV or detector `beam_stroke` in the cell (`census_2_174.py`): Litolff 651 (own stem found 533, not found 118); Brahms 2,042 (found 967, not found 1,075).

Random sample, 40 per plate, seed 2174 (`sample_2_174.py`, `crops_2_174.py`; my own look at crops, not evidence):

| crop shows | Litolff /40 | Brahms /40 |
|---|--:|--:|
| not a note (barline sliver, stem box, dot, rest, clef edge) | 6 | 21 |
| real unbeamed quarter / chord head | 24 | 12 |
| flagged eighth (a missed FLAG, not a beam) | 0 | 2 |
| **really beamed** | **6** | **2 clear (+1 probable)** |
| unclear | 4 | 2 |

**Random-sample rate: beamed under a decided quarter = Litolff 15% (to 25% with the unclear), Brahms 5-8% (13% of its real notes).** Judged tiles are a different population, cut at doubtful places: Sean's 2.165 tiles hold 9 of 10 bar-disputed decided quarters as eighths, and the judged `head_and_marks` quarters in the census are only 5 (Litolff) and 7 (Brahms), with the "2 right / 8 wrong" figure of 2.165 not reproducible on first-verdict features. The random sample says most decided quarters with a beam row in the cell are NOT beamed (Brahms: more than half are not notes at all).

### Why the beam was not tied (the 9 beamed notes)
| cause | n | cases |
|---|--:|---|
| kept stroke starts just past the group-edge stem; join reader "does not reach the stem horizontally"; nothing dropped, level 0 | 2 | Brahms 10/0/9/2/0, 24/1/9/7/6 |
| the CV stroke dropped as a LEDGER LINE | 2 | Litolff 15/1/5/4/2, 7/0/8/8/2 |
| stem side read opposite to where the beam stands (stroke on the "far side") | 2 | Litolff 6/0/6/11/13, 6/1/3/9/4 |
| no beam stroke of either reader at the group | 1 | Litolff 16/1/1/2/2 |
| no own stem found, only stroke refused `too_thin` | 1 | Litolff 16/1/8/2/3 |
| far side + `too_thin` | 1 | Brahms 23/1/3/3/24 |

No cause is a majority; the five causes are 2/2/2/1/1/1 of 9. Census-wide the class "strokes in the cell, NOTHING dropped, level 0" is Litolff 31 / Brahms 123 notes; it has the cleanest engraving rule, so it is the one fixed. The rest are named, not fixed (ledger-line drop; stem side; strokes never gathered).

### Inside the staff or outside (manager, from Sean: "easier to see the beam outside of the staff than inside")
Nearest beam stroke centre inside the staff (top line - 0.5 space .. bottom line + 0.5 space) or outside (`inout_2_174.py`). MISS = decided quarter with a stroke in the cell; HIT = decided beamed eighth/sixteenth with a joined beam.

| | outside miss/hit | inside miss/hit | miss rate outside | inside |
|---|--:|--:|--:|--:|
| Litolff | 412 / 1,755 | 121 / 1,557 | 19% | 7% |
| Brahms | 743 / 1,693 | 224 / 2,311 | 30% | 9% |

The rate does NOT show inside-the-staff beams missed more (the outside miss pool is inflated by slivers and quarters beside another group's beam). Of the 9 beamed samples 6 stand inside the staff and 3 outside; 3 of the inside ones were dropped or mis-sided where the beam crosses lines (ledger-line drop, far-side reading). Staff lines confuse the SIDE and LEDGER tests, not the join and level readers as a whole.

## 3. The fix
STAGED ADJUDICATE `rhythm.adjudicate_duration`, immediately before the final `head_and_marks` returns (beam/head_and_marks part only; 2.173's whole-class branch untouched). Flag `OMR_STROKE_AT_STEM_TIP_NARROWS` (OFF). Where nothing earlier spoke, no beam/flag counted, head not open, own stem with a decided side, and a stroke in `kept` (after side, tip, ink, ledger, neighbour, arc tests) lies in the 2.81 zone at the stem END (`_refused_stroke_at_tip(..., across_spaces=0.6)`): NARROWED between the plain value and one beam level (`beams_ambiguous`, detail `stroke_at_stem_tip`). Tests `test_staged_stroke_at_stem_tip_narrows_2_174.py` (5, with flag-off, far-across and far-along controls); `docs/flags-2026-09.md` rows added.

## 4. Measured on the EXPORTED FILE (whole-plate replay, ADJUDICATE..INFER..EXPORT; `replay_2_174.py`, `compare_2_174.py`, `score_2_174.py`; OFF = main with 2.165 ON)
| | Litolff OFF -> ON | Brahms OFF -> ON |
|---|---|---|
| notes in file (`notes_reaching_file`) | 6,686 -> 6,688 | 12,176 -> 12,181 |
| bars held out | 618 -> 617 | 890 -> 887 |
| blue (GUESSED) notes | 1,567 -> 1,575 | 1,889 -> 1,899 |
| first verdicts decided quarter -> narrowed | 3 | 5 |
| standing verdicts moved | 3 (one quarter -> narrowed; one eighth -> narrowed; one quarter -> eighth by a chord mate sharing the stem) | 5 (3 quarters, 2 dotted quarters -> narrowed) |
| quarters turned into eighths by this flag | 0 decided | 0 decided |
| judged right/wrong/narrowed | 159/29/6 -> same | 129/22/5 -> same |
| judged tiles that move | none | none |

**The fix is correct in kind and tiny in size**: the zone catches 8 notes on two plates, against 154 "kept, uncounted" census notes and about 100 beamed-under-quarter notes estimated from the random sample on Litolff alone. Most of those stand under causes this fence does not touch.

## 5. Blind tiles
`out/print/2.174-review/` (8 tiles: 6 unjudged notes the flag narrowed, 3 per plate, plus 1 plain decided quarter per plate as controls), one blue box, nothing else drawn, question "what is the written value of the note in the blue box?". Key `out/2.174/tiles-key.json`; `probe/tiles_2_174.py`, ONE run made tiles and key and checked every blue box equal to its key row. Two of the 5 Brahms narrowed notes are already judged (excluded).

## 6. Tests
Own file 5 passed. Fast tier `pytest -m "not slow" tools/omr/tests -q`: 8,541 passed, 12 skipped, 2 xfailed, 0 failed.
