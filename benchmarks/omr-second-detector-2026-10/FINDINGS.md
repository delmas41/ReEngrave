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

### 4. Sean's idea: "90% ink inside = black, anything less = hollow" -- measured on truth, NOT wired
Scripts `interior_variants.py` (+ `.json`), `interior_pipeline.py`, `interior_crops.py`; page raster 600 dpi, centre window = the 2.88 interior (30% shrink). Variants: (a) the current window on the box given (Sean's truth box for a hollow head, Brahms black truth box, a production black box on Litolff); (b) the window on a standard head box re-centred by `gather.recentre_notehead`'s search (staff-line runs >= 2.5 sp erased first, no size gate); (c) (b) with the local line rows left out (2.73 `ink_off_line`). Brahms = every hand-truth head on pdf 0 (378 black, 33 hollow). Litolff = the 95 clean TEST cells: 50 truth hollow boxes; "black" = the 90 PRODUCTION black-class boxes in those cells that no truth hollow box matches (a SOFT label: Sean boxed only hollow heads on Litolff, so an unlabelled hollow head or a non-head sits in this set; see the crops).
| page | variant | black n: min/p5/med/p95/max | hollow n: min/p5/med/p95/max | at "< 0.90 = hollow": black flip / hollow stay black | best cut (errors, gap) |
|---|---|---|---|---|---|
| Brahms | (a) current | 378: 1.0/1.0/1.0/1.0/1.0 | 33: 0.16/0.19/0.25/0.80/0.90 | 0/378 / 1/33 | 0.95 (0, 0.10) |
| Brahms | (b) re-centred | 378: 0.53/1.0/1.0/1.0/1.0 | 33: 0.19/0.25/0.41/0.80/0.95 | 1/378 / 1/33 | 0.96 (1, 0.014) |
| Brahms | (c) + line rows out | 378: 0.24/1.0/1.0/1.0/1.0 | 33: 0.19/0.25/0.41/0.77/0.95 | 1/378 / 1/33 | 0.867 (2, 0.167) |
| Litolff | (a) current | 90: 0.72/1.0/1.0/1.0/1.0 | 50: 0.10/0.20/0.60/0.99/1.00 | 2/90 / 11/50 | 0.988 (6, 0.024) |
| Litolff | (b) re-centred | 90: 0.23/0.71/1.0/1.0/1.0 | 50: 0.23/0.31/0.47/0.81/0.84 | 9/90 / 0/50 | 0.848 (7, 0.018) |
| Litolff | (c) + line rows out | 89: 0.12/0.71/1.0/1.0/1.0 | 50: 0.23/0.29/0.45/0.67/0.82 | 10/89 / 0/50 | 0.688 (6, 0.018) |
(`unread`: (c) could not read 1 Litolff black box, the line rows took too many of its rows. Canonical-to-page conversion checked against 59 production glyph boxes: median 0.1 px, max 0.3 px.)
Reading:
* **No variant separates cleanly on both pages, so none is added to the 2.114 block.** On Brahms (a) is clean at a 0.95 cut (all 378 black heads read exactly 1.00; the highest hollow 0.90; gap 0.10) and at "< 0.90" one hollow head (reading exactly 0.90) stays black. On Litolff the best cut still makes 6-7 errors out of 140 in every variant, with a gap of 0.02. (b) and (c) fix Litolff's HOLLOW side (0 of 50 stay black at 0.90, against 11 of 50 for (a): the head-centred window plus the line rows out is what the manager and Sean asked for) but their flips on the black side rise to 9 and 10 of 90.
* **Those Litolff "black" flips are mostly not black heads** (`out/print/2.114-round2/interior-litolff-black-closest.png`, the four lowest under (c)): a staff/barline junction (0.12), and three small heads with a visible white slit that Sean did not label (0.38, 0.38, 0.50). So part of the Litolff "error" is the soft label, not the rule; the clean hollow side (`interior-litolff-hollow-closest.png`, the four highest, 0.67-0.82) shows hollow heads whose white is a small slit under a thick rim, the same look as those four, which is why no cut at 0.9 can tell "thick-rimmed hollow with a slit" from "black with a nick" by the interior fraction alone. Brahms closest black (`interior-brahms-black-closest.png`): one box on a barline/beam junction (0.24 under (c)), three genuine black heads on or near staff lines (0.95-0.97).
* **As the pipeline actually sees it** (`interior_pipeline.py`, `Q.NOTEHEAD_INK` on the detector's own box, OFF record, the 95 clean cells): the 4 truth-hollow heads under a production BLACK box read raw centre 0.69 / 0.72 / 0.97-1.00 (3 of 4 are >= 0.90, tile 13 among them: the box sits on the rim); 4 of 90 other black boxes read < 0.90 (min 0.73). A 0.90 cut would flip 1 of the 4 real hollow heads and 4 black boxes (possibly real hollow ones), i.e. it does not help where the disagreement is, which is the box placement (item 2), not the cut.
* Controls: the measure sees black (Brahms 378 heads at 1.00) and hollow (median 0.25) apart where the box is on the head, and every variant reads tile 13's hand-centred head inside the hollow band only when line rows are out AND the box is centred (0.56-0.64), so it can fail and does on the production box. Not tuned: no cut here was fitted; the table reports a 0.90 cut as asked and the best cut as a description.
* What would change the conclusion: Sean labelling the Litolff black side (the 90 boxes, or a sample), and a re-centre that works on 0.7-0.9-size boxes (the 2.39b gate), then re-run `interior_variants.py`. Per CLAUDE.md §4 any cut from these two plates would only NARROW on another publisher.

### 5. Round-2 A/B (tree `f785e3a9`, `--through adjudicate --no-surya --no-ocr`, flag OFF vs ON, records `runs/2.114/ab/`, round-1 records kept in `ab-round1/`)
Both pages gathered back to back after the overnight lock cleared (`score_second_output_r2.txt`, `identical_check_output_r2.txt`, `judged_output_r2.txt`).
* Litolff 984073 idx 1, clean 95: gather view recall OFF 37/50 = 74.0% -> ON 42/50 = 84.0%, precision 86.7% -> 84.6%; guess view 74.0% -> 43/50 = 86.0% (precision 84.9%). Same as round 1 by construction: the new rule only changes which written outcome a second-only head gets. Item 3 above: 2 of the +5 (tiles 1, 14) are duplicates of heads production already reads, so the honest clean-95 gather gain is +3 (80.0%).
* Brahms 317803 pdf 0: hollow found 33/33 both arms, filled heads called hollow 0, boxes 64 -> 65, extra 26 -> 26.
* Controls: every glyph that is not a second-only box is IDENTICAL OFF vs ON (beams, ledgers, ties, every non-second class): Litolff 751 = 751 (+7 second-only), Brahms 1776 = 1776 (+1). `judged score` OFF vs ON: right / wrong unchanged on every item of both docs (only the 2.114 tiles' own narrowed / abstained columns move). `python3 -m tools.omr.staged.check`: open 192, unchanged.
* How the rule settled the touched heads now (ON): Litolff second-only NARROWED 3 (all truth hollow: tiles 3, 15, 17), abstained `second_only_no_independent_evidence` 1 (the tie fragment, tile 5: not a note), refused by ink 1 (tile 4), owned-by-another-staff 2 (tiles 1, 14: duplicates); production-black/second-hollow: NARROWED 1, black stands 2, older rule 1. Brahms: owned-by-another-staff 1 (tile 8), black stands 1, older rule 2. READ hollow by the new rule: 0. A second-only head never reaches the output without a stem or a dot.
* Blind tiles for round 2: `out/print/2.114-round2/` (13 tiles, 2 controls; the new ON record touched no head round 1 had not already asked, so the rest are the 11 threshold tiles). Hidden manifest marks them and records interior readings (a, b, c). Eight Litolff "black" production boxes (the lowest-reading under (c), the staff/barline junction skipped; two near the "B." text at the left margin are probably not heads and will answer "not a note") and the three highest-reading truth hollow heads.

## Sean's round-2 tiles (2026-10-14) and the cleaned 90% measurement
Scripts: `cleaned_interior.py` (+ `cleaned_interior.json`, `cleaned_interior_output.txt`), reading `interior_variants.json` (round-2 raster readings, NOT re-gathered) and the Litolff idx 1 OFF record `runs/2.114/ab/rec-lit-off.json`. STAGED only (the interior reader and the ADJUDICATE readers); LEGACY is not involved.

### Sean's answers, scored against the hidden manifest
Verbatim: "1. Part of a bracket 2.2 3.f dyn 4.bracket 5. Key flat 6.2 7.4 8. Time signature number 4 9. Whole rest 10.2 11. Fermata 12.2 13. Dot 2" -> `out/print/2.114-round2/answers.json` (his word kept in `sean`; 2 / dot 2 = hollow, 4 = black, everything else = not_a_note).
* Controls: tile 7 (Brahms, truth black) -> black, tile 13 (Brahms, truth hollow, dotted half) -> hollow. Both right.
* The 8 "THRESHOLD black-labelled" Litolff production boxes: 0 real black heads, 1 hollow (tile 2, `glyph/1/0/9/3/2`), 7 not a note (bracket x2 = tiles 1 and 4, f dynamic = 3, key flat = 5, time-signature 4 = 8, whole rest = 9, fermata = 11). Exactly the expected split.
* The 3 truth-hollow threshold tiles (6, 10, 12): all three hollow. Right.
So the Litolff "black" side of the 2.114 soft label was wrong for 8 of its 90 boxes, and the print says 7 of those are not noteheads at all and one is a hollow half.

### The 90% measurement on the cleaned black set (Litolff 984073 idx 1, 95 clean cells; Brahms untouched, hand truth)
"Sean" = drop his 7 not-a-note boxes, move tile 2's box to hollow (black 90 -> 82, hollow 50 -> 51). "Sean + record" = also drop every remaining black box the record itself reads as a non-note mark (script docstring: R1 `notehead_is_not_a_notehead` decided True except the real-head reasons duplicate / stacked / nearer-staff; R2 whole-rest verdict; R3 >= 50% inside a detector box of a rest / fermata / dynamic / key / accidental / clef / time-signature / brace class; R4 centre within 1 sp of the staff's left/right extent). That removes 6 more (73-76 black left, by variant): `0/15/1` (whole rest), `3/0/8` (quarter-rest box), `6/6/1` (too narrow), `11/2/3`, `11/2/4`, `11/2/5` (clipped fragments). Not picked by eye; the record misses Sean's tile 5 (key flat: no key/accidental box and no refusal on it) and calls tile 8 only through a mis-detected quarter-rest box.
Counts are errors as (black read < cut, hollow read >= cut); "best" is cut (errors, gap).
| set | variant | black n: min/p5/med/p95/max | hollow n: min/p5/med/p95/max | cut 0.85 | cut 0.90 | cut 0.95 | best cut (errors, gap) |
|---|---|---|---|---|---|---|---|
| original | (a) current | 90: .72/1/1/1/1 | 50: .10/.20/.60/.99/1 | 2+17 | 2+11 | 3+7 | .988 (6, .024) |
| original | (b) re-centred | 90: .23/.71/1/1/1 | 50: .23/.31/.47/.81/.84 | 7+0 | 9+0 | 11+0 | .848 (7, .018) |
| original | (c) + line rows out | 89: .12/.71/1/1/1 | 50: .23/.29/.45/.67/.82 | 7+0 | 10+0 | 11+0 | .688 (6, .018) |
| Sean | (a) | 82: .72/1/1/1/1 | 51: .10/.20/.62/1/1 | 2+18 | 2+12 | 2+8 | .988 (6, .024) |
| Sean | (b) | 82: .23/1/1/1/1 | 51: .23/.31/.46/.81/.84 | 2+0 | 2+0 | 3+0 | .884 (2, .089) |
| Sean | (c) | 81: .12/1/1/1/1 | 51: .23/.29/.45/.66/.82 | 1+0 | 2+0 | 3+0 | .848 (1, .054) |
| Sean + record | (a) | 76: .72/1/1/1/1 | 51: .10/.20/.62/1/1 | 2+18 | 2+12 | 2+8 | .988 (6, .024) |
| Sean + record | (b) | 76: .78/1/1/1/1 | 51: .23/.31/.46/.81/.84 | 1+0 | 1+0 | 2+0 | .884 (1, .089) |
| Sean + record | (c) | 75: .88/1/1/1/1 | 51: .23/.29/.45/.66/.82 | 0+0 | 1+0 | 2+0 | .848 (0, .054) |
| Brahms (unchanged) | (a) | 378: 1/1/1/1/1 | 33: .16/.19/.25/.80/.90 | 0+1 | 0+1 | 0+0 | .95 (0, .10) |
| Brahms | (b) | 378: .53/1/1/1/1 | 33: .19/.25/.41/.80/.95 | 1+1 | 1+1 | 1+1 | .96 (1, .014) |
| Brahms | (c) | 378: .24/1/1/1/1 | 33: .19/.25/.41/.77/.95 | 1+1 | 1+1 | 1+1 | .867 (2, .167) |
(The "original" rows reproduce the Round 2 table of section 4 exactly, which is the control for this re-computation.)
Reading:
* Cleaning the black side changes the Litolff picture, because its errors were the soft label. With the head-centred window the black side now sits at 1.00 (p5) and the hollow side tops out at 0.84 (b) / 0.82 (c): a 0.85 cut is clean on Litolff variant (c) with the record's own verdicts too (0 errors, gap 0.054; best cut .848 sits inside it), and 1 error (a black box reading 0.88 under c, 0.78 under b) at the asked 0.90 cut. A 0.90 cut makes 2 errors on Sean-only (b) and (c).
* (a), the window on the detector's box, does NOT improve: its errors are on the hollow side (12 of 51 truth-hollow heads read >= 0.90 because the box sits on the rim), unaffected by cleaning. The Litolff gain belongs to re-centring, not to the 90% idea itself.
* The remaining Litolff black-side errors at 0.90, by key: `6/6/1` (0.23 b / 0.12 c, the staff/barline junction of section 4; the record already calls it `too_narrow`, so it leaves in Sean + record) and `9/2/1` (0.78 b / 0.88 c; the record calls it `stacked_head_duplicate`, a real head, kept). `9/2/1` is the one error left and is a question for the print, not asked of Sean yet.
* Both pages together are still not a single rule: on Brahms (a) is clean at 0.95 and (b)/(c) carry the same one barline-junction black box and the one 0.90 / 0.95 hollow they had; on Litolff (c) at 0.85 is clean. A cut that is clean on both would be 0.95 on Brahms (a) and 0.85 on Litolff (c), two windows. Per CLAUDE.md §4 two plates only NARROW; nothing is wired.
* Caveat, who says it's right: Sean saw only the 8 threshold boxes. The other 82 "black" boxes are still production's own class, so a clean row means "agrees with production's black on the boxes Sean was not asked about", not "verified black". The record-cleaned rows rest on the record's own readers, which are not a witness independent of the detector's boxes (R3 reuses the detector).

### How many non-note black boxes reach the output as notes (Litolff idx 1 OFF record, STAGED export)
All 99 production `noteheadBlack*` boxes of the page, the same four flags plus Sean's 7, and each one's fate from `export.build` (the `fates` the exporter keeps): 15 sit on such a mark (Sean's 7 + 8 flagged by the record; one of the 8, tile 2, is a real hollow head Sean confirmed and the record refuses as a clipped fragment).
* Written as a note: 0 of 15.
* Refused by an ADJUDICATE not-a-note verdict (`not_a_notehead:*`): 10 (too_narrow 3, clipped_fragment 7; Sean's tiles 1, 3, 4, 11 are in it; tile 2, a real head, is in it too).
* Refused by the whole-rest verdict (`ink_is_a_whole_rest`): 2 (tile 9 and `0/15/1`).
* Not refused by any not-a-note reader, dropped only because no pitch could be read (`no_pitch`): 3 -- Sean's tile 5 (key flat), tile 8 (time-signature 4), and `3/0/8` (a quarter-rest box). Their drop is incidental to the missing pitch, not a decision that the mark is not a note: with a ladder or a position they would be written.
Numbers only; no fix proposed here.
