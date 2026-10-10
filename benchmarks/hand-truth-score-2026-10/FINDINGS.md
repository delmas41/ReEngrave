# hand-truth scorer, first version (ROADMAP 1.7, plan Phase D: D1 + D2)

**Path:** STAGED, GATHER + ADJUDICATE only. **Date:** 2026-10-10. **Code:** `tools/omr/hand_truth/score.py`
(the scorer + CLI), `score_controls.py` (D2), `score_crops.py` (diagnostic crops),
`tools/omr/tests/test_hand_truth_score.py` (49 tests, synthetic, fast tier). **Output:**
`brahms317803-p0-first-score.{txt,json}` here; crops in `out/print/1.7-d1-score/`.

```
python3 -m tools.omr.hand_truth.score --page <page.json> --record <record.json> --derive \
    [--pdf <score.pdf> --crops-dir DIR --crop-cells s0-st3-m0 --crop-ink "x,y;x,y"] [--out report.json]
python3 -m tools.omr.hand_truth.score --controls --derive --page <page.json>      # D2, no record needed
```

## 1. What was run

* **Truth:** Sean's `data/hand-truth/pages/imslp317803/0.json` (Brahms 1, Breitkopf 317803, PDF index 0), read from
  `/Users/seanjohnson/Desktop/ReEngrave-handtruth` (branch `claude/hand-labeled-truth-1.7`, `4619a27b`), never written. sha256
  `fc54ec49…bf41c8`, byte-identical to the copy on `origin/main`. State `labeling`: 1,342 boxes (377 drawn, 895 prefill-confirmed,
  70 prefill-fixed); 202 cells; 112 measure cells, of which **89 are inspected `all-ink`**. Those 89 are the scored cells.
* **Record:** `python3 -m tools.omr.acceptance_quick --doc brahms1-breitkopf` (PDF pages 0-1, `--through adjudicate`) on `origin/main`
  `6762622c`, clean tree, weights = production scan weights (`deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, by routing),
  dpi 600. Read through `record_io.load_record`.
* **Held out:** this page is held out and production never trained on any of its cells (`INVENTORY.held_out_cells_trained_by_production`
  has no entry for `imslp317803:0`), so the **trained side is empty (0 cells)** and the not-trained side is everything.

## 2. The first numbers

(Full text in `brahms317803-p0-first-score.txt`; per-notehead rows in the `.json`.)

**Frame control: OK.** All 112 measure cells the two sides both cut have identical rectangles (max difference 0.0 px; same
`preprocessing.render_page`, so the same binarise + deskew). Matched DRAWN boxes (Sean's own strokes) are centred on the record's boxes:
median dx -0.27 px, dy +0.26 px (p10..p90 about +-5 px, 0.17 staff space of 32 px). Lines-on-ink (`readout.frame_control`'s measure):
record +214.1, truth +213.3.

Per family (recall / precision; G = every detector box, A = after ADJUDICATE; "drawn" = recall on the boxes Sean DREW, i.e. what the
prefill detector had not supplied):

| family | truth | read | G recall | G prec | A recall | A prec | drawn m/n |
|---|--:|--:|--:|--:|--:|--:|--:|
| notehead | 339 | 390 | 1.000 | 0.869 | 0.985 | 0.954 | 6/6 |
| stem (CV in the product; detector class rare) | 227 | 16 | 0.057 | 0.812 | 0.057 | 0.812 | 0/212 |
| ledger line | 223 | 184 | 0.704 | 0.853 | 0.704 | 0.975 | 4/70 |
| augmentation dot | 109 | 110 | 0.991 | 0.982 | 0.982 | 0.991 | 0/1 |
| tie | 70 | 157 | 0.586 | 0.261 | 0.614 | 0.672 | 2/10 |
| slur | 63 | 131 | 0.921 | 0.443 | 0.889 | 0.727 | 6/7 |
| beam | 41 | 144 | 0.805 | 0.229 | 0.805 | 0.264 | 0/8 |
| time-signature digit | 36 | 46 | 0.889 | 0.696 | 0.889 | 0.696 | 0/3 |
| accidental | 35 | 54 | 1.000 | 0.648 | 1.000 | 0.660 | 7/7 |
| flag | 31 | 35 | 0.935 | 0.829 | 0.935 | 0.853 | 1/2 |
| rest | 16 | 20 | 1.000 | 0.800 | 1.000 | 0.941 | - |
| key accidental | 11 | 12 | 1.000 | 0.917 | 1.000 | 0.917 | - |
| dynamic letter | 9 | 34 | 0.889 | 0.235 | 0.889 | 0.286 | 1/1 |
| clef | 8 | 11 | 1.000 | 0.727 | 1.000 | 0.727 | 1/1 |
| barline, brace, text, tremolo | 30, 8, 4, 11 | 0 | 0 | n/a | 0 | n/a | 0/29, 0/8, 0/4, 0/6 |

Classes the truth has and the detector never produced on this page: `barlineSingle` 27, `barlineDouble` 3, `brace` 8, `text` 4,
`tremolo1` 11. Classes the detector produced and the truth never has: `staff` 50 (staff lines are confirmed per staff, not boxed; the family
is NOT SCORED), `dynamicP` 6, `arpeggiato` 2, `dynamicM` 2, `articTenutoBelow`, `dynamicZ`, `flag16thDown` 1 each.

**Noteheads** (339 in scored cells; 334 matched at ADJUDICATE, 5 lost by ADJUDICATE, 0 missed at GATHER):
owner right 332, wrong 0, abstained 0, no truth 2; staff position right 329, wrong 2, abstained 1, no truth 2. **These are against a
DERIVED reference, not Sean's labels** (section 3).

**Per staff (system header)**, against the first cell where it is fully labeled (8 of 14 staves): clef 8 of 8 right; key 7 of 8 right (the
one "wrong" is a truth label error, section 5); meter 7 right + 1 no truth (a digit is not boxed). Cautionary 9/8 after the last barline (11
of 14 staves scored): 10 right, 1 no truth. (The record reads 6/8 at bar 0 and a corroborated cautionary 9/8 at the last cell.)

## 3. How to read them, and how not to

1. **`prefill-confirmed` recall is ~1.0 in every family and means nothing.** 895 of the 1,342 boxes ARE the production detector's own boxes
   that Sean confirmed, and this record was made by the same weights. The honest recall of the detector is the "drawn" column, and it is
   small-n for most families. Notehead "recall 1.000" is 323 confirmed + 6 drawn + 10 fixed, all found. The real notehead loss is at
   ADJUDICATE (0.985).
2. **Sean has not written `owner_staff` or `staff_position` on any box (0 of 1,342), and no tool writes them.** The scorer therefore reports
   owner and position against a DERIVED reference from his box and the cutter's staff lines (`--derive`): in-staff heads from the lines
   (244), far heads from his own ledger-line boxes (88), and 2 far heads stay unlabeled (no ledger box of his leads to a staff). It is
   labelled `derived` on every line. It is the same staff detector the record used, so agreement is weaker evidence than it looks; and 208
   of the 334 heads carry no `glyph_owner` verdict at all (uncontested: they stay on the staff they were cut from), so most "owner right"
   is "nobody contested it and the nearest staff is its staff". The contested heads (126) are the informative ones; all 126 agree.
3. **Precision is a lower bound.** Of the unmatched record boxes in scored cells, some sit over marks Sean has not boxed. The repo's own
   ink control (B2) over the 89 cells lists 533 components under half covered by truth boxes. Sampled (`ink-uncovered-*.png`), most are
   staff-line slivers on this thick-lined plate and unboxed barlines (only 30 barline boxes), not missed notes; so it WARNS, it does not count.
4. **Tie versus slur is where arcs go wrong.** 21 of Sean's 70 ties are `prefill-fixed`: the detector said slur and he made it a tie, so at GATHER
   they match 0 (the record box is a slur). ADJUDICATE's `arc_kind` recovers 11 of the 21 (the ADJUDICATE view files an arc under the kind
   it decided). Arcs are also boxed per cell: 9 of the 23 fixed ties and 19 of the 40 confirmed ties touch a cell edge, and where a tie is
   a fragment of a longer arc the IoU is under 0.3 (`4-tie-tie-other_family` crop).

## 4. D2: the controls, each seen failing

Built from the truth itself through the real `Log`, round-tripped through JSON and read back through `readout.run_from_result` and the
scorer's own adapter. All pass on the clean scorer (on the synthetic page and on Sean's real page). Each was then run RED:

| control | what it must show | bug seeded in | result |
|---|---|---|---|
| self_score | truth vs itself: every family recall = precision = 1, nothing wrong | owner comparison always False; matcher matches nothing | RED, RED |
| owner_shift | owner accuracy 1.0 -> 0.0 when the truth is moved one staff; matches and positions unchanged | owner comparison always True | RED |
| position_shift | position accuracy 1.0 -> 0.0 when every head reads one step off; owner unchanged | position comparison always True | RED |
| header_wrong | wrong clef/key/meter/cautionary score all-wrong | header judges always "right" | RED |
| frame | OK unshifted; FAILED for boxes off by 0.35 space (x, y), cells off by 6 px, wrong dpi | frame check that never trips | RED |
| drop_and_add | dropping 10% of heads lowers recall and leaves precision 1; adding spurious lowers precision and leaves recall 1 | every rate = 1.0 | RED |
| no_overlap_no_match | boxes moved where no truth head stands match nothing | matcher that pairs by order | RED |
| refusal | a family no cell was inspected for is REFUSED, not zero | scope that inspects everything | RED |

Two of these exist because a control failed on first contact: the by-order matcher stayed GREEN under `self_score` (a record in truth
order IS paired by order), which is why `no_overlap_no_match` was added; and that control's first version, a fixed 8-space shift,
FAILED on the real page (it dropped heads onto their neighbours) while passing on the synthetic one, so the shift is now searched and
verified independently of the matcher. `TestEachControlCanFail` re-runs every seeded bug in the fast tier.

## 5. What the first score shows

**The five commonest kinds of miss** (ADJUDICATE view, one example cell each; crops `1-` to `5-` in `out/print/1.7-d1-score/`; green is the
truth box, red the record's boxes, blue the staff lines the cutter measured):

1. **212 stems**, all drawn by Sean: the detector hardly ever produces the `stem` class (the product reads stems with CV, which this scorer
   does not score yet), `s0-st0-m6`.
2. **58 ledger lines** the detector did not box (all drawn by Sean; 8 more sit under a box of another family), `s0-st0-m5`.
3. **27 barlines**: not a detector class (CV), `s0-st0-m5`.
4. **14 ties** where the record has a box of another kind on the same ink: the detector's slur (Sean made 21 of his ties from detector slurs),
   or a longer arc over a truth fragment, `s0-st5-m0`.
5. **8 beams** never boxed, `s0-st1-m5`.

Next in the list: 8 braces and 6 tremolos (not detector classes), 6 ties refused by ADJUDICATE as staff line, 5 slurs, 5 noteheads.
Excluding the classes the detector never produces, the order is ledger lines, ties, beams, ties lost at ADJUDICATE, slurs, noteheads.

**For the reader (Phase 2 material; none of it is fixed here):**

* ADJUDICATE refuses 6 of Sean's confirmed ties as "not an arc -- ink is a staff line"; 4 more are dropped to another staff (range veto /
  distance). 10 ties lost in all (`tie` kind in the `.txt`; see the first tie crop).
* 5 of 339 noteheads are lost at ADJUDICATE, every one a "not a notehead" refusal: 2 "stacked head duplicate" (`6-notehead-…` crop: the
  lower head of a stacked dyad), 1 "head cut piece", 1 "too narrow", 1 "clipped fragment".
* The detector's beams: 144 boxes against 41 true ones (precision 0.23-0.26), none removed by ADJUDICATE; 8 true beams never boxed.
* Ledger lines: of the 70 Sean drew, the detector found 4, 58 have no detector box and 8 sit under a box of another family
  (`2-ledger_line-…` crop: one rung of a stacked pair is missed).
* Dynamic letters: 34 boxes against 9 (precision 0.29 after ADJUDICATE).
* Stems, barlines, braces, text and tremolos are not detector classes (CV or nothing): the scorer lists them but cannot score the CV readers
  yet (next step).

**For Sean (truth labels the scorer tripped over; he decides every one):**

* `s0-st3-m0`: the third key-signature flat is boxed as `accidentalFlat`, so the header reads 2 flats; the record's 3 is right.
* `s0-st5-m7`: the "8" of the cautionary 9/8 is boxed as `noteheadWholeInSpace` (box `q713`); it is counted as a notehead.
* `s0-st4-m0`: the "8" of 6/8 has no truth box at all.
* Two far heads (`q133`, `q136`, `s0-st0-m6`) have no ledger-line box toward any staff.

## 6. What the brief said and the tree contradicted

* "Each box has `owner_staff`, `staff_position`": the fields exist in the schema; no box carries a value and no tool writes one. Hence
  `--derive`, and the "Sean's" numbers are n/a.
* Brief: 89 of 112 measure cells fully labeled: correct. Margin, top and bottom cells (90) are all unlabeled and unscored.
* The `wiring` check matched this module's `.owner` attribute as a read of the detail key `own` and went from exit 1 (192) to exit 2
  (broken) with a stale `KNOWN_GAPS` entry; both modules declare `DERIVED_CHECK = True`, the sanctioned marker for a measuring
  instrument. `check` stays at 192.

## 7. Next steps (each a decision, not done here)

1. Sean writes owner/position for the 92 far heads (or accepts the ledger-derived reference); then the owner and position columns become his.
2. Add the CV readers as a second SOURCE (`Q.STEM`, `Q.BEAM_STROKE`, barlines) so 212 of 227 stems stop reading as misses. **`Q.STEM` done, section 8**; beams and barlines are still open.
3. Arc truth that spans cells (merge fragments, or match by containment).
4. The `acceptance_quick` third view needs the Brahms COUNT page (PDF index 1) labeled first; this page is the first page, not the count page.
5. Instrument names; the Litolff page (the 0.25 degree deskew note is untested here: both sides use the same `render_page`, and the cell-frame control
   will say so on that plate).

---

## 8. Stems: how reliably are we finding them? (ROADMAP 1.7; Sean 2026-10-10, *"How reliably are we finding stems?"*)

**Path:** STAGED, GATHER + ADJUDICATE only. **Measurement only: no reader, filter or constant was changed.** **Code:**
`tools/omr/hand_truth/score_stems.py` (new), the hook and two CLI flags in `score.py`, six controls in `score_controls.py`,
`tools/omr/tests/test_hand_truth_stems.py` (58 tests, synthetic, fast tier). **Output:** `brahms317803-p0-stems-score.{txt,json}`
here; eight phone-sized images, their maker and every fact on them in `out/print/1.7-stems/` (`stem_01.png` .. `stem_08.png`,
`table.txt`, `make_images.py`).

```
python3 -m tools.omr.hand_truth.score --page data/hand-truth/pages/imslp317803/0.json --record <record.json> --derive \
    [--stem-runs <record gathered with OMR_VERTICAL_RUNS> --stem-ink --pdf <score.pdf>] --out report.json
python3 -m tools.omr.hand_truth.score --controls --derive --page data/hand-truth/pages/imslp317803/0.json
```

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED (CLAUDE.md rule 3; nobody could be asked before the build; Sean's own stem
boxes are the reference, so these are conventions about HOW to compare to them):

* ASSUMED: a CV stem is "Sean's stem" when its centre column is within 0.25 local staff spaces of his box's and they share half of the
  shorter one's length. FALSIFIED by the shift control (8.7): moving every CV stem one head width must collapse recall.
* ASSUMED: a head HAS a stem of Sean's when a stem box of his lies within 0.30 spaces of the head's box. A head with none is
  `no_truth`, never a false positive (about 18 printed stems lack a box, the 2.81 lane).
* ASSUMED, from Sean's own boxes: a stem's truth direction is where it extends beyond its head, checked against the engraving's
  side rule (up -> right, down -> left, CLAUDE.md section 10); a head where they disagree is `ambiguous` and not judged (17 of 321).
* NOT CONFIRMED WITH SEAN: that his stem boxes are the stems' ink (212 of the 227 are his own strokes; the 13 `prefill-confirmed`
  and 2 `prefill-fixed` are detector boxes he kept).

### 8.1 What was run

* **Truth:** `data/hand-truth/pages/imslp317803/0.json` (sha256 `debf248f...`, byte-identical to the copy in `ReEngrave-handtruth`), 1,346
  boxes, 89 fully labeled measure cells (the scored cells), **227 stem boxes** (212 drawn, 13 confirmed, 2 fixed). Read, never written.
  Sean has corrected 4 labels since section 1, so the notehead rows differ from the first score by one (338 truth heads, 333 matched).
* **Record:** `python3 -m tools.omr.acceptance_quick --doc brahms1-breitkopf --out-root out/l17s-quick` on `cc2ef5a3` (origin/main
  `ae2ec2ed` plus one docs commit), **clean tree (`dirty: false`)**, PDF pages 0-1 through ADJUDICATE, production scan weights by
  routing, dpi 600. Scored on page 0. `OMR_SURYA_KEEP_ALIVE=0`.
* **Why each stem was lost** needs the runs the stem opening produced and then refused, which the record does not hold by default. A
  second gather of page 0 with the research producer on (`OMR_RESEARCH=OMR_VERTICAL_RUNS OMR_VERTICAL_RUNS=1 python3 -m
  tools.omr.staged <pdf> --pages 0 --no-surya --no-ocr --through gather`, no detector) adds one `Q.VERTICAL_RUN` row per run with the
  first filter that refused it. **Control that could fail:** its `Q.STEM` rows must be the scored record's: 358 = 358 rows on 95 cells,
  0 cells differ (`--stem-runs` refuses a record whose stems differ).
* **Frame.** `Q.STEM` is `[x, y, w, h]` in the cell's CANONICAL frame, with no page fields. The scorer reads each cell's canonical-per-page
  factor back from the detector boxes (they carry both) and cross-checks it against `Q.CELL_STAFF_SPACE` over `Q.STAFF_SPACING`: 112 of
  112 cells measured both ways, worst relative disagreement 0.19%, 0 distrusted, 0 stems declined for want of a frame.

### 8.2 Where the product reads a stem (from the tree)

| quantity | stage | what it is | read by |
|---|---|---|---|
| `Q.STEM` | GATHER (`gather.py`, reader `cv_lines`, `line_detection.detect_stems`) | CV stem `[x, y, w, h]`, canonical cell px; the survivors of six filters and the pair rule | `Q.HEAD_STEM`, `Q.STEM_DIRECTION`, `rhythm._stems_on` (the duration), `notehead_precision._stem_rows_on`, the tip-ink / slash / beam-join readers |
| `Q.HEAD_STEM` (2.78) | ADJUDICATE (`stem_value.adjudicate_head_stem`) | which `Q.STEM` row a head box stands on; **box overlap, no tolerance** | `adjudicate_stem_value`, EVALUATE `share_stem_value` |
| `Q.STEM_DIRECTION` | ADJUDICATE (`rhythm.adjudicate_stem_direction`) | up / down by stem projection, else by a beam mate | the duration, articulations, the voice split |
| `Q.HEAD_STEM_REACH` (2.58d) | GATHER | a second raster read of the vertical run beside a CONTESTED head, page px | `glyph_owner` only |

The duration reads the SAME `Q.STEM` rows (each decision re-derives the overlap privately), so a stem not found is a stem missing from the
duration too: of the 106 stemmed heads without their right stem, 61 stand at `decided` and 44 at `narrowed` duration (against 174 decided and
41 narrowed for the 215 with it). The scorer does not judge those durations (the truth carries none); it files the standing.

### 8.3 THE ANSWER (Brahms 317803 pdf 0, 89 scored cells; numbers as the scorer prints them)

| | of | number |
|---|--:|--:|
| Sean's stems **found** by the CV reader | 227 | **173 = 0.762** (172 cover >= 0.8 of the stem) |
| ...by the detector's `stem` class (the number the scorer used to print) | 227 | 13 = 0.057 |
| ...by either source | 227 | 175 = 0.771 (2 only the detector boxed) |
| CV stems that are **not** Sean's ("invented") | 243 read in scored cells | **68 = 0.280** (precision 0.720) |
| Heads of Sean's that have a stem box of his | 338 | 321 (17 have none: unjudged) |
| ...that get their **right stem** attached by ADJUDICATE | 321 | **215 = 0.670** |
| ...`Q.HEAD_STEM` DECIDED, and right when decided | 321 / 220 | 220 decided, **215 right = 0.977**, 5 wrong |
| ...ABSTAINED `no_stem` | 321 | 101 (97 stem not found, 4 stem found) |
| ...direction right, of those judged | 250 | **247 = 0.988** (55 abstained `no_stem`, 16 read with no judged truth) |

Per staff (`system.staff`; found/truth, valid/read; instrument names are not in the truth):

```
0.0  6/21 0.286   6/9    0.1  7/21 0.333   7/11    0.2  9/21 0.429   9/14    0.3  10/15 0.667  10/21
0.4 12/12 1.000  12/17   0.5  7/7  1.000  7/13    0.6  4/7  0.571   4/12    0.7   2/2  1.000   2/6
0.8 12/12 1.000  12/15   0.9 35/36 0.972  35/37    0.10 32/33 0.970  34/47   0.11 34/37 0.919  37/41
(and 3 truth stems filed to no staff band, found 3/3)
```

**The loss is concentrated, not spread:** 46 of the 54 missed stems are on the four top staves (0.0-0.3: 15, 14, 12, 5); the other 8 are
3, 3, 1, 1 on 0.6, 0.11, 0.9, 0.10. Staves 0.4-0.11 read 0.92-1.0 except 0.6 (4 of 7). This is one page of one score; 8.8 says what that
does and does not license.

### 8.4 The misses, by cause (54 of 227 Sean's stems), with the code path and constant for each

Every one of the 54 has the stem's ink on the page and **no CV stem of any size in its column** (0 fragments). Where each went, from the
runs the stem opening produced (`Q.VERTICAL_RUN`, the first filter that refused each):

| cause | stems | what the record says | code path and constant |
|---|--:|---|---|
| the run is **too WIDE** (the stem fused with the heads beside it) | **45** | one run 0.93-1.22 spaces wide (median 1.06) x 3.75-6.6 tall, its centre 0.36-0.57 spaces off the stem, refused `RUN_TOO_WIDE` | `line_detection.detect_stems`, `max_width_lines = 0.6` (60 canonical px at space 100) |
| the stem's own thin run is **PAIRED** off | **6** | a clean 0.16-0.25-wide run, 3.2-7.0 tall, dropped as one of a pair | `line_detection._drop_paired_strokes`, `accidental_pair_gap_lines = 0.9`, `accidental_pair_overlap = 0.6` |
| both | 3 | the thin run PAIRED, and a second run too wide (0.68 x 2.1, 0.71 x 2.3, 0.99 x 4.7) | both of the above |
| any other filter (too short, too tall, cell edge, area, aspect), or no ink | **0** | | |

Facts about the 54, against the 173 found (a fact common among the found is not what loses a stem):

* **The stem is on the page.** The ink in Sean's stem column is unbroken for >= 0.9 of his box's length on 53 of 54 (median 1.0; the
  other 0.67); the shortest unbroken run on any of them is 2.85 spaces against the 1.6 the opening needs. None is lost for want of ink.
* **Thirds.** **48 of 54** stand on two heads a THIRD apart (the closest two heads 2 steps, so the boxes touch; 83 stems have such a pair,
  35 of them found). 0 of 13 stems whose closest two heads are a fourth or wider are missed, 0 of 8 with heads on both sides of the stem,
  1 of 5 with a second (the 3-head chord `b4092`), 5 of 126 with one head (4 PAIRED, 1 too wide). By count of heads on the stem: 2+ heads
  49 missed / 52 found; one head 5 missed / 121 found (0.960). **95 of the 106 stemmed heads without their right stem stand on a missed
  third.** This is 2.77b's "two stacked heads fuse into one component against the width cap", counted.
* **PAIRED.** The partner is a 2.23-2.40 space stroke 0.42-0.64 spaces from the stem, **never one of Sean's stems (9 of 9)**: it lies on
  one of his accidental boxes in 7 and on a notehead box in 2 (`stem_04.png`, `stem_05.png`). The pair rule was written for exactly an
  accidental's two strokes (`_drop_paired_strokes` docstring); here it takes the real stem down with them. `OMR_STEM_NOTEHEAD_GATE` (default OFF, a
  `line_detection` flag that 2.4a re-decides) narrows this very rule; its own findings are `benchmarks/omr-stem-notehead-gate-2026-09/`.
* **Short stem:** 0 of the 6 stems under 2.5 spaces is missed; the shortest miss is 2.85. **Long:** 17 missed of 71 at >= 4.5.
* **Through staff lines:** crossing none 0 missed / 10; crossing 1-4 lines 52 / 193; crossing all five 2 / 24. No separation: a stem that
  runs through the lines is found about as often as one that does not.
* **Touching a beam box** 17 missed / 103, **a slur or tie box** 23 / 89: these are chord stems (confounded with the thirds).
* **Stem found but not attached:** 4 heads (8.5). **The head itself missed:** 0 stemmed heads missed at GATHER; 4 are refused at
  ADJUDICATE as not a notehead (2 of them still attach their right stem).
* Not seen on this page: a stem lost to a gap in its ink, to the 8-space tall cap, to the cell edge, to the area floor, to the aspect
  filter. (The `Q.HEAD_STEM_REACH` docstring's "thin where it crosses the next staff's lines" is a contested-head case this page's 54 do
  not contain.)

### 8.5 Per head

Of Sean's 321 stemmed heads: 215 right stem; 97 no stem attached because none was found; **5 attached to a stroke that is not a stem**;
4 stem found but not attached. The 102 heads on missed stems are the 97 and the 5.

* **Wrong stem (5 heads, 3 CV strokes):** 4 heads on two missed thirds (stem refused too wide), 1 on a one-head stem refused PAIRED. Each
  stroke is 3-4 px wide and 2.2-2.4 spaces tall, stands against the head's right edge, and lies on one of Sean's FLAG boxes: on the
  print it is the RISING CURVE of an eighth's flag (all three zoomed and looked at; `stem_06.png` shows one). Filed `one_stem` on the
  head(s) it touches; their direction still reads right (5 of 5).
* **Found but not attached (4):** the found stem stands 0.00, 0.02, 0.02 and 0.10 spaces (0-3 px) from the head box;
  `adjudicate_head_stem` takes only boxes that overlap, so it files `no_stem` (`stem_07.png`). `rhythm._boxes_overlap` states "heads take
  exactly one stem and where none overlaps the nearest is 94 px away": on this page 4 heads stand under 3 px.
* **Direction** is right on every one of the 199 heads that got their right stem and were judged, and on 48 heads that did not (43 of them
  with the stem not found: the beam-mate tier); the 3 wrong all stand on heads without their right stem.
* `Q.HEAD_STEM_REACH` (contested heads only): 122 of the 321 have a row; of the 78 with up or down against a judged truth direction,
  69 agree.

### 8.6 What the 68 "invented" stems are

None of the 68 has a stem of Sean's at its column: **65 lie on another mark** (time-signature digit 16, clef 13, flag 13, key accidental 11,
accidental 10, rest 2), 3 touch a head of his that has no stem box. They are strokes 2.0-3.7 spaces tall and 0.03-0.5 wide, inside symbols
(`stem_08.png`: the bass clef, the flats and the "6/8"). Three of them are named as a stem by a head (the 5 heads of 8.5). 115 more `Q.STEM`
rows lie in the 23 measure cells nobody has fully labeled yet and are not scored. This is not a count of what would hurt a cleanup.

### 8.7 The controls, each seen RED

Built from the truth through the real `Log`, with a CV stem reader's rows in a canonical frame x2.5 that is not the page frame. All pass on
the clean scorer on the synthetic page and on Sean's page. Each was then run RED on **both** (`TestEachStemControlCanFail`, and the same
bugs seeded against the real page):

| control | must show | bug seeded in | result |
|---|---|---|---|
| `stems_self` | CV recall = precision = 1 through the canonical frame; every stemmed head on its own stem, direction right; detector class untouched | no canonical conversion; a matcher that links nothing; an attach judge that never says right; a direction judge that never says right | RED x4 |
| **`stems_shift`** | every CV stem moved **one head width (1.3 spaces = 41.6 px)**: recall and precision <= 0.05, no head keeps its stem, detector-class recall unchanged (so the collapse is the CV source's) | a matcher that ignores the column; a tolerance of 6 spaces | **RED x2** (recall 1.0 shifted, 321 heads still right) |
| `stems_drop_and_add` | drop 20%: recall down, precision 1; add 20% nobody drew: precision down, recall 1 | rates that are always 1 | RED |
| `stems_attach_swap` | every head names the NEXT stem: stem recall stays 1, heads with their right stem <= 5%, and they read as ANOTHER stem | an attach judge that always says right | RED |
| `stems_direction_flip` | directions reversed: accuracy <= 0.05, attachment unchanged | a direction judge that always says right | RED |
| `stems_reader_not_run` | no `Q.STEM` row and no abstention: REFUSED; an abstention in every cell: scored, recall 0.0 | a reader that never ran counted as ran | RED |

Three of these exist because something failed on first contact: (1) the shift control's first version cleared the shifted stems at 0.5 spaces
and **could not be built on the real page** (beamed stems stand 1.57 spaces apart, so a head width lands 0.27 off a neighbour and clears
the 0.25 tolerance by 0.02 only); it now uses its own restated 0.30-space window and accepts a shift on which <= 2% of stems land (1.3 spaces:
2 of 227). (2) The synthetic page's stem stood at the head's centre-right while running down, which the side rule calls ambiguous, so the
direction control judged nothing until the stem moved to the head's left edge. (3) The cause finder's first version matched a run by the
distance of its CENTRE and read **45 of 54 misses as "no run at all"**: a stem fused with the head beside it is a run whose centre is half a
space from the stem. `test_the_centre_distance_version_misses_it` holds the RED.

The tolerance itself is read off the data: of Sean's 227 stems, 173 have a CV stem within 0.15 spaces and the next nearest is 0.40; from the
CV side 175 within 0.15, then 0.40; two neighbouring truth stems are never closer than 1.57. The widest empty interval is 0.15-0.40 in both
directions and 0.25 is its middle.

### 8.8 Limits, and where the brief and the tree disagreed

* **One page, 89 of its 112 measure cells, one plate.** The stem number here is largely a statement about the top four staves of this passage
  (46 of the 54 misses; thirds in the upper parts). Whether 0.76 is the plate's rate or this passage's needs a second labeled page (the
  Litolff page, a different and MERGING plate, is next in 1.7) before anyone quotes it as the reader's rate.
* The truth is Sean's boxes: 17 heads have no stem box (the brief says ~18; none is a whole note) and are unjudged, so a real stem on one of
  them is not credited and a wrong one is not charged. 4 further stemmed heads are not read as heads at ADJUDICATE and are still counted.
* The direction truth is DERIVED from his boxes (8, convention), not a label of his.
* The brief's "about 18 heads lack a stem box" and "212 of the 227 stems are drawn by Sean" both reproduce (17; 212). The 2.77b "127 px
  component against a 60 px cap" is the **width** cap (`max_width_lines = 0.6`), not a height cap; here the fused runs are 93-122 px at space 100.
* The brief asked for stems "touching a beam or slur" and a "stem along staff lines" as candidate causes: both are reported as facts above.
  Among the 126 ONE-HEAD stems, where the thirds cannot confound them, those touching a beam box are missed 1 of 65 and those not 4 of 61;
  touching a slur or tie box 3 of 44, not 2 of 82. The numbers are too small to rank and none loses a stem by itself (every one of the
  54 is a refused run, 8.4).
* `score_stems.py` and `score_controls.py` carry `DERIVED_CHECK = True` like their siblings, so `wiring` needs nothing new. On the final
  head (`77b908fb`): fast tier **7,082 passed**, 12 skipped, 2 xfailed, 825 deselected; `python3 -m tools.omr.staged.check` **N = 192**,
  unchanged (before and after).

### 8.9 Pointers (the roadmap items that already own these populations; nothing is decided here)

* The 45 + 3 fused runs and the 2.77b open item (`OMR_STEM_STROKE` reads them, moves 81 of 1,286 Litolff verdicts) are one population.
* The 6 + 3 PAIRED stems and `OMR_STEM_NOTEHEAD_GATE` (default OFF) are one population: 2.4a.
* The 4 found-but-not-attached heads (`adjudicate_head_stem`'s no-tolerance overlap) and the 5 heads filed on a flag's rising curve
  are 2.78's (a stem that is refused leaves the next vertical stroke against the head to be its stem).
* The scorer now prints these numbers at GATHER + ADJUDICATE for any record, so the next re-gather reads them with one command.
