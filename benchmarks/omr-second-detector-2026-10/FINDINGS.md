# ROADMAP 2.114 -- a second detector at GATHER for hollow heads only

2026-10-13, branch `lane-2.114-second-detector`, not merged. STAGED path only (GATHER + ADJUDICATE, `--through adjudicate --no-surya --no-ocr`).
Flag `OMR_SECOND_HOLLOW_DETECTOR`, default OFF. Weights `omr-weights/candidates/scale2110-OLD896-raw-2026-10-13.pt` (2.110 OLD arm), hollow classes only.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* **CONFIRMED by Sean (2026-10-13):** a hollow head is decided by "a certain amount of white on the inside", not a clear middle (staff lines run through hollow heads). This is the 2.88 raw-raster reading, reused (`_raw_reads_firmly_hollow`, `_hollow_readings`, `_hollow_margin`).
* **ASSUMED:** production's boxes are right about every class; the second model is a witness for regular half/whole heads only (`second_hollow.HOLLOW_CLASSES`: Half/Whole x OnLine/InSpace + `noteheadWhole`; cue `...Small`, double whole, every black and every non-head class are dropped).
* **FALSIFIED IF:** a filled head the second detector calls hollow survives the ink test as hollow (none in the two pages below), or any non-hollow class from the second model reaches the record (`identical_check.py`: every non-second glyph identical OFF vs ON).
* **NOT CONFIRMED:** the 2.88 cut-offs (centre 0.2-0.75, ring - centre >= 0.15, two rasters, head-shaped box) on any publisher but Litolff. Hence the choice below.
* **CHOICE, and why:** the ONLY DECIDED outcome is where production boxed a head, the second calls it hollow, the interior is firm, one bare stem, nothing on it (`second_hollow_confirmed`, READ). A head production never saw stays NARROWED however firm (the cut-offs are Litolff-tuned; the box has one witness); ink reading filled refuses it. This run: `second_hollow_confirmed` fired on 0 real heads (the one disagreement the new rule settled was NARROWED, see table), so the DECIDED branch is untested on a real page and covered by unit tests only.

## Numbers (every one from `score_second.py`, `score_truth.py`, `identical_check.py`; records `runs/2.114/ab/` gitignored, regenerate with `run_ab.sh off|on`)
Both arms gathered back-to-back on the same clean committed tree `f35c8033`, same production weights (`hollow-graft-shift09`), ON = `OMR_SECOND_HOLLOW_DETECTOR=1` (recorded in the record's provenance `env_overrides`).
Command: `python3 benchmarks/omr-second-detector-2026-10/score_second.py off=A/rec-lit-off.json:A/rec-bra-off.json on=A/rec-lit-on.json:A/rec-bra-on.json --out score.json` (`score_second_output.txt`).

**Leak guard first** (`leak_check.py`, 2.112's `check_leak`, mix = v1-v4 + v13-v22 from both roots, 1,182 cells): Litolff idx 1: 9 of the 104 TEST cells are training cells (2 exact-pixel pairs, 18 key pairs over the 2 roots, 18 near >= 0.90; the same 9 as 2.112 found: `s0-st2-m3, s0-st3-m6/7/8/11/14, s0-st7-m1, s0-st8-m8, s0-st9-m15`). Brahms pdf 0: 0 exact / 0 key / 0 near of 112 cells. So Litolff is scored on the 95 CLEAN cells (50 truth heads) with all 104 (59 heads) as the second column; the second detector saw those 9 cells in training, production did too.

Views (same function on both arms; OFF's own landed 2.70/2.88/2.23 readings count in OFF): `gather` = box class (2.110's view), `read` = + a black head whose duration verdict is DECIDED half/whole, `guess` = + NARROWED with a hollow candidate.

| Litolff 984073 idx 1 | OFF | ON |
|---|--:|--:|
| clean 95: hollow recall, gather view | 37/50 = 74.0% | 42/50 = 84.0% |
| clean 95: precision, gather view | 39/45 = 86.7% | 44/52 = 84.6% |
| clean 95: recall / precision, guess view | 37/50 = 74.0% / 86.7% | 43/50 = 86.0% / 84.9% |
| all 104: recall, gather / read / guess | 72.9% / 74.6% / 74.6% | 81.4% / 83.1% / 84.7% |
| all 104: precision, gather / read / guess | 88.9% / 89.1% / 89.1% | 86.9% / 87.1% / 87.3% |

| Brahms 317803 pdf 0 (hand truth) | OFF | ON |
|---|--:|--:|
| hollow heads found (of 33), all three views | 33 | 33 |
| hollow boxes / extra boxes (on timeSig digit 15, tremolo 3, other 8) | 64 / 26 | 65 / 26 |
| FILLED truth heads called hollow, all three views | 0 | 0 |
| beam / ledgerLine / tie / slur recall (`score_truth`, gather and ADJ views) | 0.80 / 0.71 / 0.57 / 0.92 | **identical** (0.80 / 0.71 / 0.57 / 0.92; ADJ tie 0.44 both) |
| hollow-heads precision in the GATHER view | 0.55 | 0.54 |
Controls that can fail (all pass): truth vs itself 59/59, shifted 3 head widths 0/59, a view calling every black glyph hollow drops Litolff precision 0.89 -> 0.37; `score_truth` controls 1-4 PASS (beams deleted 0.80 -> 0.0, shifted max recall 0.077, beams x3 precision 0.23 -> 0.08). `identical_check.py`: every glyph that is not a second-only box is identical OFF vs ON on both pages (751 = 751; 1,776 = 1,776); ON adds 7 glyphs on Litolff, 1 on Brahms. Beam/ledger/tie are untouched by construction (no second-model box of those classes is kept) and the measurement agrees.

**Disagreements and how they were settled (ON records, the whole page; counts of heads the second detector touched: 111, of which 96 agree with a production hollow head)**
| page | relation | settled as | n | vs Sean's truth |
|---|---|---|--:|---|
| Litolff | production black, second hollow | NARROWED black/hollow (new rule) | 1 | truth hollow 1 |
| Litolff | production black, second hollow | black stands (ink filled / marks) | 2 | truth hollow 1, not a truth hollow head 1 |
| Litolff | production black, second hollow | already narrowed by an older rule (`beam_discounted_uncertain`) | 1 | truth hollow 1 |
| Litolff | production saw nothing | NARROWED (second-only head) | 4 | truth hollow 3, not a truth hollow head 1 |
| Litolff | production saw nothing | refused: ink reads filled | 1 | not a truth hollow head 1 |
| Litolff | production saw nothing | owned by another staff (older decision) | 2 | truth hollow 2 |
| Brahms | production black, second hollow | black stands | 1 | no truth box |
| Brahms | production black, second hollow | older rule narrowed (`beam_discounted_uncertain`) | 2 | truth BLACK 1, no truth box 1 |
| Brahms | production saw nothing | owned by another staff | 1 | truth hollow 1 |
READ hollow via the new rule: 0. Filled heads wrongly turned hollow (Brahms hand truth): 0 in any view; the one Brahms truth-black head the older `beam_discounted_uncertain` rule narrows is pre-existing (OFF too). The +5 clean heads in the gather view are all second-only boxes (3 NARROWED, 2 whose duration is abstained `owned_by_another_staff`, the box still hollow-classed); the guess view adds 1 more from a production-black head narrowed with a hollow candidate. None is READ. One truth hollow head the second detector reached stays black (ink-filled/marks branch): a miss, not an error.

## Reading, and what these numbers do not show
* The mechanism does what it was built for on Litolff (+10 points clean recall, -2 points precision) and moves nothing on Brahms (33/33 either way, 0 filled heads turned hollow, beams/ledgers/ties identical). It is one page per publisher: 5 recovered heads, 1 Brahms extra box. The size of the Litolff gain is NOT established beyond this page, and the second model trained on 9 of those cells (clean figure excludes them).
* The Brahms side has almost nothing to say: 4 disagreements on a page where the OLD arm's extra boxes (2.110: 35 vs production's 26, 22 on time-signature digits) are mostly refused by the "production saw another class" rule (`over_other`) or already hollow.
* The DECIDED branch (`second_hollow_confirmed`) fired on no real head; only the blind tiles can say whether the NARROWED outcomes were right.
* Older rules already settle part of the disagreement (`beam_discounted_uncertain` decides first); the new block sits after the flag/hook branches and before the 2.23 narrowing.

## Tests / checks
24 RED-first tests (fast tier: 7,794 passed, 0 failed) `tools/omr/tests/test_staged_second_hollow_2_114.py` (RED on the unrepaired tree with only the helper module and the new `Q`/`READERS` present: 15 failed, 9 passed; green here): flag OFF bit-identical (also: OFF never builds the detector), non-hollow classes dropped, one head boxed twice, a staff line through the middle reads hollow, filled stays black with margin recorded, ambiguous NARROWED with both candidates, DECIDED verdict on other evidence not overturned, a detector that throws is a refusal, second-only heads never DECIDED.
`python3 -m tools.omr.staged.check`: TOTAL 192 = main (no_producer fixed by letting the flag, not a parameter, build the detector; wiring/capture/reach entries registered). `judged score` on the OFF and ON records of both pages: identical, TOTAL right/wrong columns unchanged (`judged_output.txt`). Blind tiles: `out/print/2.114-second-detector/` (17 tiles incl. 2 controls; LEGEND.md; answers go in `answers.json` later).

## Sean's blind tiles (2026-10-14)
Answers in `out/print/2.114-second-detector/answers.json` (his verbatim word per tile beside the mapped answer; he answered with durations: 2 / dot 2 = hollow, 4 / dot 4 / 8 = black, trem slash / whole rest / part of a tie = not a note). Scored against `manifest.json` hidden fields; the second detector claimed hollow on every non-control tile.
* **Controls: 2 of 2 right.** Tile 7 (truth black) -> Sean 4 = black; tile 10 (truth hollow) -> Sean dot 2 = hollow.
* **Second detector's hollow claim, 15 non-control tiles: 9 right, 6 wrong.** Right: 1, 3, 6, 8, 12, 13, 14, 15, 17. Wrong: 2, 9 (tremolo slashes, not notes), 4 (whole rest), 5 (part of a tie), 11 (black), 16 (black).
* **What the written output did, per settlement (right = the outcome matches Sean, no invented or lost note):**
| settlement | tiles | right | wrong / note |
|---|---|--:|---|
| NARROWED (second-only head), new rule | 3, 5, 15, 17 | 3 of 4 | **5 wrong**: a tie fragment narrowed as a hollow head = a blue invented note |
| NARROWED black/hollow (new rule) | 6 | 1 of 1 | real half, both candidates carried |
| refused: ink reads filled | 4 | 1 of 1 | whole rest correctly refused |
| black stands (ink filled / marks) | 9, 13, 16 | 1 of 3 | **13 wrong**: a real half kept black; **9 wrong**: a tremolo slash kept as a black head (both detectors boxed it); 16 right (black) |
| abstained `owned_by_another_staff` (older decision) | 1, 8, 14 | no claim written | all three are real halves the second detector had right; none reached the output |
| `beam_discounted_uncertain` (older rule decided first, not the new block) | 2, 11, 12 | 2 of 3 | **2 wrong**: a tremolo slash narrowed as a head; 11 (black) and 12 (hollow) keep both candidates |
* Net: the new rule's own outcomes (NARROWED second-only, NARROWED black/hollow, refused, black stands) were right on 6 of 9 tiles; the three wrong ones are 5, 9 and 13. Tiles 2 and 9 are a detector-level fault shared with production (a tremolo slash boxed as a head), not caused by the second detector's class choice. Nothing was READ hollow by the new rule (see above).
* Small n (one Litolff and one Brahms page, 15 tiles): this shows which failure kinds exist (tie fragment as second-only head, real half left black by the ink rule), not rates.

## Round 2 (2026-10-14), STAGED only. Sean's tile verdicts drive three items
Records read: the round-1 ON/OFF records (`runs/2.114/ab/`, gitignored). Crops: `out/print/2.114-round2/`. Scripts: `owner_crops.py`, `tile13_interior.py`, `offline_probe.py`.

### 1. Tile 5 (Litolff glyph/1/0/3/13/2, part of a tie): a second-only head needs a witness that is not the second box
Rule (`rhythm._second_only_evidence`, in the 2.114 second-only block of `adjudicate_duration`): a head ONLY the second detector boxed may be NARROWED (a GUESSED head) only if one of three witnesses from another source says a note is there: a stem the stem reader attached (`stem_box`), the CV ruler's vertical run beside the head, up or down (`stem_reach`, `Q.HEAD_STEM_REACH`; `both` = barline, not a witness), or an augmentation dot (`aug_dot`). None -> ABSTAIN `second_only_no_independent_evidence`, candidates (`would_narrow`) and signed margin recorded, nothing written. To make `stem_reach` exist for such a head, `gather_head_stem_reach` also reads a second-only head (it used to read only contested heads); flag OFF has no such head, so OFF is unchanged. Ledger rungs are NOT a witness here: `Q.GLYPH_LADDER` exists only for contested heads.
`measure_head_stem` on the page raster for every second-only head (round-1 ON records, hand-run `reach.py`): tile 5 `none` (down 0.48, up -0.01 sp) REFUSED; tile 4 (whole rest) `none`, already refused by ink; tile 3 `up` (2.59 sp; the stem reader also attached one) carried by `stem_box` + `stem_reach`; tile 15 `down` 3.04 sp, `stem_reach` only (the stem reader found none: `no_stem`); tile 17 `up` 3.30 sp, `stem_box` + `stem_reach`; tiles 1 / 8 / 14 are owned-by-another-staff (item 3). Tile 5 is the only one confirmed-not-a-note that the rule newly refuses; the three Sean confirmed hollow second-only heads that reach the output all keep their narrowing. A whole-class second-only head has no stem, so it now needs a dot or is refused (no confirmed case either way; tile 4 was a whole REST).

### 2. Tile 13 (Litolff glyph/1/0/9/11/1, a real half read BLACK): the BOX, not the cut-off
Raw readings (centre / ring): production and second boxes (they agree, IoU 0.91) 1.00 / 0.69 on all three rasters (raw, net, off-line). Confirmed hollow heads read raw centre 0.21-0.86, off-line 0.31-0.75 (tiles 3, 6, 10, 12, 15, 17); confirmed black heads read raw 0.78-1.00, off-line 0.88-1.00 (tiles 7, 11, 16) (`offline_probe.py`). Tile 13's 1.00 is the black heads' value, so no cut-off change could admit it without admitting 7 and 11.
Two causes stack: (a) THE BOX. Both detectors boxed 18 x 14 px = 0.83 x 0.81 of a standard head (1.4 x 1.1 sp), sitting on the head's upper rim 0.3 sp above its centre; `gather_notehead_recentre` declined it as "already head-sized" (its gate `RECENTRE_BOX_SIZE_GATE` is 0.7), and 2.73's `head_cut_by_line` found no second enclosed hole (the head's upper slit is open to the right). So the centre window lands on solid rim (centre 1.00). (b) THE SCAN: the top staff line runs through the middle and the head's white is two small slits. A standard box centred on the head's own ink (by eye, `tile13_interior.png`) reads raw centre 0.78 / ring 0.70 (just over 0.75), but with the line's rows left out (2.73's `ink_off_line`, which already exists) centre 0.56-0.64 / ring 0.59-0.64 over five centre positions within 2 px: inside the hollow band, far from the black 0.88-1.00. So the line-row exclusion the manager asked for is already built and works once the box is on the head; what is missing is the re-centre.
Changed in this round: nothing for item 2. The cause is `gather_notehead_recentre` (ROADMAP 2.39b, production, flag OFF reads it too); raising its gate above 0.83 changes OFF output and needs its own measurement (a head-sized-box population, not this one head). Proposed, not done: a roadmap item "re-centre boxes 0.7-0.9 of a standard head" tested on Sean's tiles 13 and 7/11/16. Not done inside 2.114 because a second re-centre of our own would be a guess (rule 6).

### 3. Tiles 1, 8, 14 (real halves, `owned_by_another_staff`): a duplicate was refused, not a note lost
All three: the second detector's box is cut from the cell of the staff ABOVE (tile 1 and 14: staff 9, Brahms tile 8: staff 6), at that cell's bottom (top) edge, so the box is clipped (tile 1: 32 x 11 px of a 23 px head; tile 14: 22 x 9). The head's own staff is the neighbour (tile 1, 14: staff 10, head 1.6 sp above its top line, 5.6-5.7 sp from staff 9; tile 8: staff 5, on ledger lines below it, 4.9 sp vs 5.8 sp). PRODUCTION already boxed the same head in that staff's own cell (`mark_group` of size 2: glyph/1/0/10/14/3, glyph/1/0/10/7/1, glyph/0/0/5/5/6) and reads it: half (2.0), half (2.0) and dotted half (3.0), `head_and_marks`, DECIDED. `adjudicate_duration` sees the owner (`glyph_owner`: ladder for tile 1 [one ledger rung found, staff 10], `stem_toward_staff` for tile 14 [stem down, tip 4.4 sp], `ledger_owner_density` for tile 8 [0.72 vs 0.18]) is the other staff, which holds the twin, and abstains the clipped copy. On the print (`owner-tile{1,8,14}.png`) the head sits directly on the neighbour staff with its stem into it, so the owner is right; the ownership reader and the box frame are not at fault (page boxes of the two copies overlap exactly: tile 1 x 2335.9-2368.2 vs 2343.7-2367.6, same top y 2883.7). Sean's "belong to the main staff in the cell" fits: it is the staff the head sits on; a question for him is whether he meant the cell's own staff, but the record and the crops agree on the neighbour.
CONSEQUENCE FOR THE GAIN: these three are NOT a gain of the second detector. Each is a clipped duplicate of a head production already read as a half in its owner's cell, so the dedupe is correct behaviour and nothing was lost. Recount of the round-1 gain without them: Litolff clean 95 (gather view) OFF 37/50 = 74.0%, ON 42/50 -> 40/50 = 80.0% (the two clean-set owned-by-another-staff duplicates, tiles 1 and 14, removed from the +5), guess view 37 -> 43 becomes 37 -> 41 = 82.0%; Brahms found 33/33 either way, so its owned duplicate (tile 8) adds nothing. The mechanism's real second-only gain is the heads that are boxed in their own staff's cell and NARROWED (tiles 3, 15, 17) plus the black-to-hollow narrowing (tile 6, 12).
