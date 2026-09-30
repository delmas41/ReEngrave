# The graft tool was backwards, and production carries the bug

**Date:** 2026-09-29. **Branch:** `claude/weights-ab-2.34`, not merged.
ROADMAP 2.34.

## 1. The bug in `merge_class_head.py`

A YOLOv8 detect head has three parts per FPN scale: `model.22.cv2.*`
(shared box regression), `model.22.dfl` (shared, fixed), `model.22.cv3.*.2`
(the per-class 1x1 classification conv -- one weight row + one bias per
class). The whole point of a graft (round 5, `docs/handoff-2026-09-04-
round5-class-collapse.md`) is to take a narrow specialist's improvement to
a FEW classes without carrying the rest of what its own fine-tune did.

The plain `--ft`/`--base` path (no `--import-rows`) did the graft
BACKWARDS. It started from the FINE-TUNE's *entire* state dict and copied
the *non-kept* classes' `cv3` rows back from `--base` -- leaving every
other tensor (backbone, neck, `cv2` box regression, DFL, and every OTHER
class's own `cv3` row) as the fine-tune's, unrestored. `--import-rows` and
`transplant_class_rows.py` were already anchored on `--base` correctly and
did not share the bug -- only the path `compose_specialists.sh` and every
round-5/6 ship command actually called.

**Fixed:** the graft now starts from `--base`, unconditionally, and writes
only the *kept* classes' `cv3` rows onto it, from `--ft`. Everything else
is base's, bit-exact, because it is simply never written -- the same shape
`transplant_class_rows.py` already used, and the direction Sean's own
round-5 note ("Graft onto PRODUCTION, not onto the pre-hollow base") was
reaching for without naming the mechanism.

**Test** (`benchmarks/omr-labeling-survey-2026-09/test_merge_class_head.py`,
4 cases, synthetic nc=6 state dicts, no real weights): kept classes' rows
= the fine-tune's; every non-kept row = base's; the box-regression and
backbone stand-in tensors NEVER move; `--bias-shift` shifts the grafted
row, not base's. Run RED against the pre-fix code (`git stash`d the fix,
re-ran): `test_box_regression_and_backbone_never_move` fails exactly as
predicted (box-regression tensor reads the fine-tune's tag, not base's);
GREEN with the fix restored.

## 2. Does the shipped production graft carry the bug? YES.

Read-only tensor diff, `hollow-graft-shift09-2026-09-04.pt` (commit
`0e9f005b`) vs. its recorded donors (`GRAFT-TRAINING-SET-AUDIT.md`):
`--base omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt`, `--ft
omr-weights/round5-sweep/distill25/epoch0.pt`, `--keep` the 7 notehead
classes (14 indices, duplicated names).

| | bit-identical to BASE | bit-identical to FT (`distill25/epoch0`) |
|---|--:|--:|
| of 595 tensors | 187 | 589 |
| `model.22.cv2.*` (box regression, all 3 scales) | 0 | all |
| `model.0`/`model.1`/`model.9` (backbone) | 0 | all |
| `model.22.cv3.*.2` (classification, the graft's own target) | mixed (6 tensors match neither -- the intended per-class split) | |

**Production's entire backbone, neck, box-regression head and DFL are
`distill25/epoch0`'s, not `hollow-ft-2026-09-03`'s.** The 187 "matches
base" tensors are almost entirely BatchNorm buffers that happen to
coincide numerically, not genuine restoration. `distill25` was NOT trained
with a frozen backbone (its own conv weights diverge from base too), so
this is not merely a classification-row question: every symbol's box
COORDINATES in production today are read through `distill25`'s features,
not through the 09-03 base's. This was flagged conceptually in DECISIONS
2026-09-29 ("does production carry the fine-tune's box head") and is
confirmed here directly, read-only, no retraining.

**What this does NOT mean:** production is not necessarily worse for it --
round 5's own three-axis gate measured this exact checkpoint beating
production on every axis before it shipped. It means the checkpoint that
shipped is a different, more invasive object than "production plus seven
grafted rows," and every downstream composability check in this benchmark
line (round 6, the rest-specialist experiment's `D-composite` finding)
that assumed otherwise was measuring something narrower than it thought.
Re-shipping with the fixed tool (base = today's actual production, keep =
the same 7 classes, donor = the same `distill25/epoch0`) would produce a
DIFFERENT checkpoint than what is live today; that is a re-ship decision,
not made here.

## 3. `--through` -- GATHER + ADJUDICATE only (ROADMAP 2.34, added mid-lane)

Sean, mid-lane: *"if we try grafting weights can we do that in the first 2
stages of production ... where it just handles gathering ink and boxing and
identifying before it goes to all of the other stages?"* The staged CLI
had no stop-after option. Added `--through {gather,adjudicate,evaluate,
infer}` to `tools.omr.staged` (default `infer` -- every stage, exactly as
before this option existed) and the matching `through=` parameter on
`pipeline.decide`/`run_staged`/`run_staged_on`. `--through adjudicate`
runs GATHER + ADJUDICATE, writes the record (its `stopped_after` key names
where it stopped; `--musicxml`/`--lilypond`/`--pdf` are refused together
with anything but `infer`, since EXPORT reads what EVALUATE/INFER derive).
14 new tests, `tools/omr/tests/test_staged_through.py`: the default is
byte-identical to before (control), each stop point carries exactly the
keys it should and no EVALUATE-consequence rows (e.g. no `pitch` verdict)
leaked into a record stopped after ADJUDICATE, and `decide()` itself
refuses a `through="gather"` request (that stop is the caller's job,
before `decide()` is ever invoked).

## 4. The A/B harness (`run_ab.sh` + `diff_records.py`)

Sean's method (DECISIONS 2026-09-29): graft into a COPY of production,
run the SAME pipeline over the SAME pages with only the weights differing,
compare at GATHER+ADJUDICATE. `run_ab.sh <pdf> <pages> <label>=<weights>
<label>=<weights> [pdf_basename]` runs `python3 -m tools.omr.staged
--through adjudicate` twice and hands both records to `diff_records.py`,
which reports, for one family (default `rest`): GATHER box counts by
class; every ADJUDICATE quantity filed on a rest glyph (verdicts by
outcome/value/reason, abstentions by reason) -- this covers `duration`
(the rest's own value), `glyph_owner` (ownership), and `rest_is_not_a_rest`
(refusals) without hand-picking which quantities matter; and, where
Sean's rest-queue verdicts (`benchmarks/omr-queue-rests-2026-09/verdicts/`)
cover a gathered cell, how many of each record's surviving rests are
Sean's TP vs. FP vs. unsure, matched by (page, system, staff, measure)
CELL ADDRESS + class count.

KNOWN LIMITATION, flagged not hidden: the cross-reference matches by cell
address + class count, not by sub-pixel IoU of the two canonical-frame
boxes. `Q.REST`'s own detail carries `x0/y0/x1/y1` in the SAME per-cell
canonical frame the labeling UI cuts cells in, so a geometric match is
possible in principle -- not done here because that frame is proven NOT
constant across cells (`Q.CELL_STAFF_SPACE`: 100px nominal, 19-50px on
two-thirds of an engraved fixture's cells under a width-vs-height scaling
fallback) and confirming gather's runtime frame agrees with the labeling
corpus's own recut on that fallback was out of scope. The count-based
match is exact wherever a cell holds 0 or 1 of a class (the common case)
and ambiguous only where it holds 2+ of the same class.

**Unit-tested** (`test_diff_records.py`, 5 cases, synthetic CLI-shaped
records, no real weights or gather): `load()` correctly unwraps the CLI's
`{"record": {...}, ...}` shape (the loader's first version read the WRONG
level and silently saw 0 boxes everywhere -- caught before the real run
below and regression-tested here); a real difference is not hidden; the
surviving-rests filter correctly excludes a decided duplicate; the
cross-reference correctly joins `cells.json` + a verdict file by cell
address.

### Setup

    ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-surya .venv-surya
    ln -sfn /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned .venv-omrned
    ln -sfn /Users/seanjohnson/Desktop/ReEngrave/library library
    ln -sfn /Users/seanjohnson/Desktop/ReEngrave/omr-weights omr-weights
    mkdir -p tools/omr/training/data
    ln -sfn /Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/weights tools/omr/training/data/weights

### The candidate built

    python3 benchmarks/omr-labeling-survey-2026-09/merge_class_head.py \
      --ft /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a0b689cec50b2fdc6/runs/detect/runs/rest-exp-E/weights/epoch0.pt \
      --base omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
      --keep restWhole restHalf restQuarter rest8th rest16th restHBar \
      --labels-root data/user-labeled \
      --out omr-weights/candidates/rest-exp-E-epoch0-graft-2026-09-29.pt

Arm E (oversampled) per `REST_SPECIALIST_EXPERIMENT.md` section 3's own
readout -- best F1 of any raw checkpoint (0.786), the one positive signal
the experiment found. Verified read-only against production: 592 of 595
tensors bit-identical to base; only the 3 kept-class `cv3.*.2.weight`
tensors differ (their bias happened to already equal production's for
this donor -- checked directly, not assumed).

### One-page proof (Brahms 1/i, Breitkopf `317803`, pdf page 1 -- the
acceptance-set page, and the one with the most rest-queue coverage: 12
verdict cells)

**Control, C = P** (production vs. a copy of the same file):

    ./run_ab.sh library/editions/brahms/.../...imslp317803.pdf 1 \
        production=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
        production_copy=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
        brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf

**Result: ZERO differences at stage 2** -- 350 rest boxes gathered on both
arms, byte-identical per-class counts, byte-identical ADJUDICATE census
(`duration`, `glyph_owner`, `rest_is_not_a_rest`), and identical cross-
reference against Sean's verdicts (10 cell/class rows, 21 surviving, 17
Sean TP on both). `out/production-vs-production_copy/TABLE.md`.

**Candidate, C = P + arm E's rest rows (fixed tool):**

Same command, second arm = the graft above. **Result: one reclassification** --
1 box moves from `restQuarter` (beats=1.0) to `rest8th` (beats=0.5); the
`rest_is_not_a_rest` duplicate-box refusal count shifts by the matching +-1
(a `restQuarter`'s duplicate-box companion is re-evaluated once its
sibling's class changes). `glyph_owner` and every other quantity: zero
difference. The cross-reference against Sean's 10 verified cells shows no
change (21 surviving / 17 TP on both) -- the one changed glyph is outside
those 10 cells, so this proof run cannot say whether the reclassification
is a gain; a full-page or whole-work run with a wider verdict set would.
`out/production-vs-candidate/TABLE.md`.

**Reading:** the harness is doing exactly what Sean asked -- a graft this
small (12 kept rows out of 208x3 scales) produces a correspondingly small,
localized, fully-accounted-for effect at GATHER+ADJUDICATE, with the box-
regression/backbone confirmed untouched (per sections 1-2's fix) and no
silent disruption elsewhere in the record.

### Running the full A/B (unattended, per Sean's "machine time is fine,
context is not")

    nohup benchmarks/omr-weights-ab-2026-09/run_ab.sh \
        <full-work-pdf> <page-range> \
        production=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
        candidate=omr-weights/candidates/<your-graft>.pt \
        <pdf-basename-if-cross-referencing-the-rests-queue> \
        > benchmarks/omr-weights-ab-2026-09/out/run.log 2>&1 &

Each arm is ~93 s/page (margin-label rung off via `--no-surya --no-ocr`,
already passed by the script) times the page count, twice (once per arm).
Read `out/<a>-vs-<b>/TABLE.md` when it finishes; `summary.json` beside it
is the same data as JSON for a script. Extend to another family by adding
its GATHER quantity to `diff_records.FAMILY_GATHER_QUANTITY` and (if it
has one) its "is not a real X" quantity to `surviving_rests`'s pattern --
not built for families beyond `rest` here, since Sean's brief named rests
first and this was proven on one page, not priced across families.

## 5. Sean's question, answered: does "fine-tuning deletes classes" survive rule 7? (2026-09-29, evening)

Round 5's claim was measured with the class-inventory screen
(`HOW-THE-TESTS-JUDGE.md` §2): a before/after COUNT on 30 held-out cells,
with no truth. Re-checked here with the raw data still on disk and the
print as the umpire. Nothing trained; ~2 minutes of detector time.

**1. Where production differs from the raw fine-tune — tensor diff,
read-only.** `hollow-graft-shift09-2026-09-04.pt` vs
`round5-sweep/distill25/epoch0.pt`: **6 of 595 tensors differ, and they
are exactly `model.22.cv3.{0,1,2}.2.{weight,bias}`** — the per-class output
rows. Within them, 201 of 208 rows equal `hollow-ft-2026-09-03`'s and the 7
notehead rows are the fine-tune's with the 0.9 bias shift. Every feature
(backbone, neck, box regression) is the fine-tune's.

**2. What the two read — `probe_class_inventory.py`, 30 held-out cells,
reproduced today.**

| class | production | raw fine-tune | 09-03 base | pre-hollow |
|---|--:|--:|--:|--:|
| beam | 127 | **0** | 126 | 127 |
| tie | 19 | **0** | 19 | 24 |
| accidentalSharp | 15 | **0** | 15 | 15 |
| augmentationDot | 13 | **0** | 12 | 12 |
| rest8th | 12 | **0** | 12 | 12 |
| clefG | 11 | **0** | 12 | 10 |
| ledgerLine | 11 | 11 | 31 | 57 |
| noteheadBlack (both) | 266 | 266 | 267 | 269 |

**3. Who says it's right: the print.** `out/print/weights-question-2026-09-29/wtc_beams_prod_vs_raw.png`
— same cell, production's beam/tie/sharp/dot boxes on the left, the raw
fine-tune on the right. The beams, ties and dots are on the page; the raw
fine-tune draws none of them. **Class deletion is real, and it is confined
to the last layer**: two checkpoints with identical features, differing
only in those 6 tensors, read 127 beams vs 0. The fine-tune's features
still carry beams — its class rows were taught "absent".

**4. So the two 09-29 findings reconcile, they do not conflict.** The
fine-tune improved the EYES (option A: hollow heads 31 vs 17 of 68 on
Beethoven 5 p1) and wiped the VOCABULARY of every class the corpus never
boxed. Production = fine-tuned eyes + the base's vocabulary restored for
201 classes. That is the recipe that works.

**5. "The tool was backwards" was backwards about the design.**
`ROUND5_METHOD_2026-09-04.md` §3 designs exactly what the 09-04 tool did:
*"take the fine-tune and put the base's rows back for every class the
corpus does not teach"* (its table: "keep 7 notehead classes, restore
201"). Round 5's measurements measured the object that shipped. What was
wrong was a LATER summary — CLAUDE.md §9 said "graft the fine-tuned rows
onto the production checkpoint" — and the 09-29 "fix" made the tool match
the summary. Option A then showed the summary's direction is the worse
one. ⚠️ Consequence: the fixed tool no longer builds production's shape in
one command. Equivalent: `--base <fine-tune> --ft <old production> --keep
<every class the corpus does NOT teach>` — but `--bias-shift` then lands on
the restored rows, not the taught ones, so a shifted build needs a second
pass. Not built; no re-ship is pending.

**6. One real loss, and it does not reach the product.** `ledgerLine` did
NOT come back when its row was restored (11 prod = 11 raw vs 31 base / 57
pre-hollow): for this class the fine-tune's FEATURES moved, not just its
row. The 30 cells are engraved WTC plates
(`wtc_ledger_prod_vs_prehollow.png`: pre-hollow boxes the ledger lines,
production mostly does not) — but engraved pages route to the pre-hollow
weights (`imgsz2048-ft-30ep.pt` is byte-identical to the PRE-HOLLOW file),
so production never reads them. On SCANS (110 Breitkopf cells,
`breitkopf_ledger_prod_vs_prehollow.png`) the counts are 240 vs 268 and
the most-different cells show the pre-hollow's extras are mostly STAFF
LINES boxed as ledgers (which `family_precision` already refuses). No
scan-side loss seen. The screen missed the engraved loss because its
threshold is "< 25% of baseline" and 11/31 is 35% — a class losing
two-thirds of its reading passes the screen.

**What this does not answer:** whether the fine-tune's eyes are better on
anything but hollow heads. Option A (stages 1–2, same pipeline, only the
weights differ) is the instrument for that, and it passes rule 7 where its
truth is the reference encoding or Sean's verdicts.

**Sean's verdict on the crops (2026-09-29, same evening):** *"the first one
had actual ledger lines that it was highlighting, the second one [were]
beams of eighth and 16th notes."* — i.e. `wtc_ledger_prod_vs_prehollow.png`:
the pre-hollow's boxes are real ledger lines (production's misses are real
misses); `wtc_beams_prod_vs_raw.png`: production's boxes are real 8th/16th
beams (the raw fine-tune's zero is a real deletion). Both §5 claims now
rest on Sean, not on a count. The Breitkopf ledger crop (scan side) was not
shown to him; its "mostly staff lines" reading is still the manager's.

**Scan side, Sean on `breitkopf_ledger_prod_vs_prehollow.png`:** *"the first
2 are in the staff, the second 2 are actual ledger lines in blue."* So the
older weights both over-fire (staff lines) AND find some real ledgers
production misses — "no scan loss" above was too strong. Split over all
110 cells (`split_ledger.py`, geometry only: a ledger lies OUTSIDE the five
lines by definition; an unmatched box centred inside the staff ± 0.3 space
is a staff line; matched = IoU ≥ 0.3):

| | both find | only older weights | only production |
|---|--:|--:|--:|
| outside the staff (candidate real ledger) | 173 | 37 | **54** |
| inside the staff (a staff line — false) | | **58** | 16 |

On scans production misses ~37 candidate ledgers the older weights find,
and finds ~54 they miss, with a quarter of their staff-line false boxes.
"Candidate" because outside-the-staff is necessary, not sufficient (a
beam or hairpin end could sit there) — the 37 and 54 are not adjudicated.
Net: no case for routing scans back to the older weights on ledger lines;
both miss some, which is why 2.6d reads ledger rungs from the ink too.

