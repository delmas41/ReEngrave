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
2. Add the CV readers as a second SOURCE (`Q.STEM`, `Q.BEAM_STROKE`, barlines) so 212 of 227 stems stop reading as misses.
3. Arc truth that spans cells (merge fragments, or match by containment).
4. The `acceptance_quick` third view needs the Brahms COUNT page (PDF index 1) labeled first; this page is the first page, not the count page.
5. Instrument names; the Litolff page (the 0.25 degree deskew note is untested here: both sides use the same `render_page`, and the cell-frame control
   will say so on that plate).
