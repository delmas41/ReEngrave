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
