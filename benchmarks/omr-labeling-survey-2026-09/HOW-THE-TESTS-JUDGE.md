# How the labeling/training tests judge a checkpoint — plain words

Five instruments have driven every labeling and training decision since
round 4. Each one has an opinion about what "correct" means and how close a
detection has to land to count as a match. Two of the five treat a MODEL's
own output as the truth. This page says which, and where that can quietly
disagree with what Sean actually boxed.

## 1. The unboxed-residue probe (`probe_spec_residual.py` / `_matched.py`)

**Correct answer:** the human label file for a cell — but the ORIGINAL probe
never checks a detection against a SPECIFIC human box. It sums teacher
detections and sums human boxes, separately, over the whole corpus, and
subtracts the two totals. **A cell where the teacher over-fires is never
offset by a cell where it under-fires** — that is the bug the audit found
(41% → 38% for rests just from fixing this). The `_matched` version instead
does a real per-instance match: nearest human box (any of the 208 classes,
not just the family), by center distance under 0.6 average box diagonals.
**Where it can differ from Sean:** the match radius is a number this project
chose, not one Sean confirmed — a genuine miss whose nearest human box
happens to sit at 0.65 diagonals away reads as "matched" (a false negative
for the miss count) or vice versa. And **the teacher's own false positives
count as "unboxed"** unless separately screened — `restWhole`/`restHBar` on
staff-line and slur ink is the teacher hallucinating a box, not the labeler
missing one, and nothing in the matching removes that without the eyeball
step the audit did by hand.

## 2. The specialist screen ("rests 12→0" — round 5/6's class-inventory check)

**Correct answer:** none — this is a **before/after count**, not a
match against truth. `probe_class_inventory.py` runs a checkpoint over 30
fixed held-out cells and counts detections per class; a class the
BASELINE checkpoint read 12+ times and the candidate reads 0 times is
"collapsed." **This never asks whether the 12 were right** — a checkpoint
that hallucinates 12 wrong boxes of a class scores as healthy on this test.
**Where it differs from Sean:** the 30 cells are dense orchestral cells
chosen for notehead density, not for holding the symbol under test — round
6 itself caught this for slurs ("production reads 0 slurs on the 30
held-out cells", so a suppressed slur class is invisible there). **This
test is BLIND on any class the 30 cells don't contain**, silently.

## 3. The forgetting axis (`wtc_forgetting_eval.py`)

**Correct answer:** reconstructed from `benchmarks/omr-phase3.4/verdicts-yolo-realft-ported`
— Sean's own TP/FP verdicts, but **on an EARLIER model's detections**
(`yolo-realft`, the checkpoint phase 3.4 ran before the hollow campaign).
A box counts as ground truth only if (a) that earlier model drew it AND Sean
marked it TP, or (b) it is an explicit `fn_noteheads` entry — a NOTEHEAD the
earlier model missed, logged as a point with a synthesized box (median TP
notehead size). **This is exactly the caveat the task asked to flag:
anything the yolo-realft model never boxed, for a class OTHER than
notehead, is simply absent from this truth file** — there is no
`fn_rests`, `fn_ties`, `fn_beams`. A tie the earlier model never drew and
nobody separately logged as missing does not exist for this test, in either
direction: a candidate checkpoint that finds it gets no credit, and one that
never finds it is never charged. **Matching:** category + IoU≥0.5 for boxed
GT, or center-distance under 0.6×size for point GT (the `--match center`
mode, "fair to box-size drift", is the one every recorded number uses).
**Where it differs from Sean:** it is Sean's own judgment, filtered through
what a specific, older model chose to show him — a real, symbol-level
adjudication, but not a complete one, and complete only for noteheads.

## 4. The hollow axis (`hollow_eval.py` vs Beethoven 5 p.1)

**Correct answer:** the work's reference MusicXML (Gradus edition), via
`eval_first_run.py` — a real external truth, not a model's output. Clefs and
key signatures are hand-read off the actual scan where the edition and the
page disagree (documented cases: Breitkopf prints no key signature for
Trombe/Timpani where the reference file carries three flats). **Matching:**
pitches are compared as MULTISETS per printed staff (not sequences), scored
twice — `exact` (letter+accidental+octave) and `step` (letter+octave only,
accidental discarded) — because a `step` recall far above `exact` recall
means the pipeline found the right notehead and read the wrong accidental,
which on this specific page is what an unread key signature produces.
**Where it differs from Sean:** the measure window (bars 1–16) was
independently counted by a bar-detector, not read by Sean bar-by-bar; a
condensed staff carrying two reference parts is scored by the pipeline's own
part order, which the file's own docstring calls "genuinely ambiguous."

## 5. The three-axis gate (`gate_all.py`)

Not a sixth truth — it runs axis 3 (forgetting, §3) and axis 1/2 (hollow
payoff + scan end-to-end, §4) on the same checkpoint list and prints one
table. **Its blind spot is the union of both inputs':** a checkpoint that
collapses a class the 30-cell screen doesn't contain, or forgets a symbol
`yolo-realft` never drew, passes clean. Round 5's own history is the
warning here — a checkpoint (`shift 1.5`) that read the BEST pooled OMR-NED
number in the table was, by every other measure, the worst checkpoint in it,
because OMR-NED (used inside axis 2, `eval_first_run`'s pooled score is a
separate, non-OMR-NED number, but the same shape of trap applies) rewards
predicting fewer symbols. **Read the element counts against truth, never
the ratio alone.**

## Bottom line for this experiment

Tests 1 and 2 above are the ones this round's arms are screened with first
(cheap, no GPU needed for scoring). **Both have a truth problem**: test 1's
per-instance match has a tunable radius and no FP screen unless paired with
the eyeball step; test 2 has no truth at all, only a before/after count, and
is blind on cells that don't hold the symbol — which is exactly why this
experiment's own eval (`eval_rest_arm.py`) insists on held-out cells that
DO contain rests, scored against two explicit truth sets (Sean's own boxes,
and a separately-flagged "corrected" set), rather than reusing either
existing instrument unmodified.
