# Handoff — 2026-09-03, the pre-fill measured against a human

The pre-fill now has a number against human labels, and a breakdown of what
the errors ARE. Read this with the CLAUDE.md subsection "Pre-fill verdicts
from the reference" and the earlier handoff
[`handoff-2026-09-03-prefill-session.md`](handoff-2026-09-03-prefill-session.md).

**Sean's position, and the frame for the next session:** this is not a failed
approach to abandon. What exists today works as a HINT; as recognition
improves it may become labels. A few days spent making it work could save
weeks or months of hand labeling, so the next session should widen the search
rather than close it.

## The measurement

Six Brahms 1 / Breitkopf cells labeled COMPLETELY by hand (every symbol, not
just hollow heads), then scored against what the pre-fill would have written:

```bash
B=benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1
python3 -m tools.omr.training.mxl_verdicts --bench-dir $B \
    --transcription $B/transcription.json --truth $B/reference.mxl \
    --windows $B/windows.json --score --score-classes all --dry-run \
    --cells brahms1-p2-sys0-s3-m4 brahms1-p2-sys0-s9-m0 brahms1-p3-sys0-s5-m5 \
            brahms1-p3-sys0-s9-m1 brahms1-p4-sys0-s0-m3 brahms1-p4-sys0-s10-m5
```

**precision exact 0.84, kind 0.94** — 50 pre-filled boxes, 94 human boxes,
42 exactly right. Recall (0.447) is meaningless here and always will be: the
pre-fill proposes only noteheads, and the human boxed slurs, hairpins, rests
and accidentals too. **Read precision.**

⚠️ **Three caveats, and the first is a flaw in how the sample was chosen.**
The six cells were ranked by how much the pre-fill DECIDED, i.e. the densest
bars — where alignment is most likely to slip. That is a biased sample, not a
random one, and the true batch-wide figure could sit either side of it. n=50
boxes gives roughly a 0.71–0.93 interval at 95%. One edition, one work, one
scan.

## What the 8 errors are — the useful half

Diagnosed box by box (`iou` against the human box, matched as `--score` does):

| cause | n | IoU | fixable? |
|---|--:|---|---|
| **grace notes** read as full-size heads | 2 | 0.80, 0.73 | **NO — see below** |
| **on-line / in-space flips** | 3 | 0.31–0.41 | detection placement |
| **unmatched**, all in one cell | 3 | — | detection placement |

The box is in the RIGHT PLACE for the grace pair (IoU 0.73-0.80, only the
size qualifier differs) and in the WRONG place for the flips (IoU 0.31-0.41,
about half a notehead off, which is what flips the position class). Six of
the eight sit in two of the six cells: **the error is concentrated, not
diffuse.** Excluding the grace ceiling, precision is 44/50 = **0.88**.

## The grace-note ceiling — and two wrong theories on the way

⚠️ **Neither source knows what a grace note is on this data, so the pre-fill
cannot label one.** Established by measurement after two wrong guesses, both
recorded because each looks plausible and each is refuted by one command:

1. *"The pre-fill overwrote a `Small` class the detector supplied."* False —
   `expected_head_class` already preserves the size the detector read.
2. *"The reference can supply it via `<grace/>`, so include grace notes in the
   alignment."* Implemented, measured, **changed nothing**, and reverted. The
   reference holds **0 grace notes in 28,579**: this Gradus encoding does not
   record them at all.

And the detector side: the whole transcription contains **0 `Small`
detections on any page**. So a grace head is read as an ordinary notehead and
the reference has nothing to say about it.

⚠️ **`truth_tokens`' docstring justifies skipping grace notes on the grounds
that "the detector labels them `*Small`". That premise is FALSE on a scan**,
and the consequence is the opposite of the one intended: skipping a grace note
in the reference does not avoid a lucky match, it forces a wrong one, because
the grace DETECTION still exists and pairs with whichever real note follows.
Left as-is because on this reference there are no grace notes to include and
the change was therefore unmeasurable — but it is wrong for the stated reason,
and the first reference encoding that DOES carry `<grace/>` makes it live.

**A page-side route exists and is untried.** Sean's grace boxes measure 41×38
and 44×45 against 51–83 wide and 47–68 tall for the ordinary heads in the same
cell, with an `accidentalNaturalSmall` beside them. A grace head is SMALLER
THAN ITS NEIGHBOURS, which is geometry — the same kind of signal the clef, key
and meter readers already use. A size-ratio rule against the cell's median
notehead is the obvious next probe.

## Where this leaves the approach

**Pre-filled TPs are a queue, not labels — today.** That is a statement about
the current detector and this encoding, not about the idea.

**The most important structural finding: pre-fill precision is DOWNSTREAM of
recognition.** Six of the eight errors are the detection's box placement,
which the pre-fill inherits and cannot improve. So the hollow fine-tune and
the cloud imgsz-2048 re-ship should raise this number **without a line of
pre-fill code changing** — and re-measuring after the re-ship is the cheapest
experiment available.

## Ideas for the next session, roughly by expected value

1. **Confidence-banded admission.** A single global precision throws away
   what the aligner knows. Every cell records `strength`, `strength_exact`
   and per-box exact-vs-near. Admit only boxes from cells above a strength
   bar and leave the rest as hints — that turns 0.84 into a
   precision/coverage CURVE, and a subset at 0.97 covering half the boxes is
   worth more than the whole set at 0.84. **Probably the highest-value idea
   here, and it needs no new labels — the data to plot it already exists.**
2. **Re-measure after the imgsz-2048 re-ship.** Free; tests the "downstream
   of recognition" claim directly.
3. **Per-class precision.** Black noteheads may already clear 0.95 while
   position-sensitive cases drag the mean down. Admit by class.
4. **Grace notes by size ratio** (above) — closes a named ceiling.
5. **A random, larger sample.** The 6-cell sample is biased toward dense
   bars by my own selection. 15–20 randomly chosen cells would give a figure
   worth quoting.
6. **Two-source agreement** — a second reference encoding of the same work,
   or the reference against a second detector pass, admitting only where they
   agree.

⚠️ **Do NOT reopen MXL→bounding-box placement.** Measured at F1 0.064 on 76
hand-mapped cells, x-drift diagnosed as the cause
(`benchmarks/omr-mxl-autolabel/FINDINGS.md`). The whole pre-fill design exists
because the detector places the box and the reference only judges it.

## Mechanics worth carrying over

- **`--score-classes all` REFUSES** without `--cells` or
  `--score-inspected-for PASS`. A single-symbol batch's verdicts hold only
  that pass's boxes, so scoring every class against them charges each
  correctly pre-filled black head as a false positive and reports a number
  that measures which pass the human ran. The guard is the feature.
- **`inspected_passes` is stamped from `batch_config.json`'s `pass_name` on
  the way OUT of a cell.** Swapping the config needs a server restart —
  Sean's completion pass stamped `hollow noteheads` because the server was
  still holding the old config, which is why the scoring run used `--cells`
  instead. `batch_config.completion.json` is committed in the Brahms batch.
- **`benchmarks/*/cells/` is gitignored.** A fresh checkout shows a blank
  canvas; `python3 -m tools.omr.annotate.recut_cells --bench-dir <batch>`
  re-renders from the manifest and refuses any frame that moved. Never
  re-run the cutter on a labeled batch.
- Run every `python3 -m tools.omr...` **from the repo root**.

## The full checklist — where every item stands

Carried from `handoff-2026-09-03-prefill-session.md` so nothing is dropped.

| # | item | state |
|---|---|---|
| 1 | Re-cut the Brahms cell images | **DONE** — `recut_cells` built, tested, run; the canvas shows music |
| 2 | Review the CONFLICT cells | **OPEN** — 5 conflicts on 4 cells, listed below, none looked at yet |
| 3 | Spot-check black heads and rests | **DONE** — the six-cell completion pass, which produced the 0.84 |
| 4 | Decide whether pre-filled TPs are admissible | **ANSWERED: no, not today** — queue, not labels; revisit after the re-ship |
| 5 | Optional tremolo-stroke pass (`tremolo1`–`5`) | **OPEN**, still optional |
| 6 | Gated training run | **DONE** on main — labels PASS; v8 and v9–v12 held out of the catalog |
| 7 | Merge PR #5 | **OPEN** — Sean's call; branch is clean and mergeable |

**Item 2 is the one piece of the original checklist with nothing done on it.**
The four cells, from `prefill/`:

```
brahms1-p2-sys0-s2-m2    2 conflicts
brahms1-p2-sys0-s3-m6    1
brahms1-p2-sys1-s26-m0   1
brahms1-p4-sys1-s15-m7   1
```

Each is a hollow head read where the reference says black — Breitkopf tremolo
abbreviations. The pre-fill deliberately refuses to decide them. Note Sean's
completion pass covered `s3-m4`, not the conflict cell `s3-m6`.

⚠️ **CORRECTED 2026-09-03, same day — all five reviewed, and none is a
tremolo abbreviation** (the encoding carries 168 `<tremolo type="single">`
elsewhere; these bars hold none). Three (both on `s2-m2`, one on `s3-m6`)
are the REFERENCE's tie-splits: one printed dotted-half encoded as tied
eighth+quarter+quarter fragments, so the hollow head is real and Sean's
existing `noteheadHalfOnLine` boxes already cover it. Two (`s26-m0`,
`s15-m7`) are a flat's loop and a natural sign misdetected as hollow heads;
Sean's empty verdicts were already right. Nothing needs clicking. The
actionable residue is a COLLAPSE GAP — a within-measure tie chain should
reconcile by the reading exactly as tremolo/tremolando do. Evidence:
`benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/CONFLICT_REVIEW.md`.

**Also open, smaller:**

- `brahms1-p4-sys1-s27-m3` is the one cell of 56 with no verdict at all.
- On Sean's Mac `batch_config.json` is still the completion palette; the
  original is beside it as `batch_config.hollow.json` and should be restored.
- The six completed cells are stamped `hollow noteheads`, not `completion`
  (the server held the old config). Re-stamping would let
  `--score-inspected-for completion` work without `--cells`.
- Flags were not boxed in the completion pass. Irrelevant to the score;
  matters only if those cells are ever exported as training labels.

## State

- Branch `claude/score-labeling-training-system-iech0i`, PR #5, draft,
  mergeable, no CI configured, no review threads.
- Sean's six completed cells are committed (`a356a58`, rebased to `6f26830`).
- Main is well ahead: hollow fine-tune shipped, Phase 2 batches complete,
  v9–v12 converted and **held out of `catalog-versions.txt`** pending the
  cloud imgsz-2048 re-gate.
