# Handoff — the probability-decision scan, and what it owes the staff-identity session

**Written for another session to read, not for a human.** If you are working on
clef assignment, staff identity, scan attribution, or anything that wants to
attach a confidence to a decision in `tools/omr/`, this is the note.

- **Branch:** `claude/probability-decision-scan-593hf5` — PR #20 (draft)
- **The survey itself:** [scan-probability-decisions-2026-09-05.md](scan-probability-decisions-2026-09-05.md)
- **Session:** "Probability measurements in decision process", 2026-09-05

```bash
git fetch origin claude/probability-decision-scan-593hf5
git show origin/claude/probability-decision-scan-593hf5:docs/scan-probability-decisions-2026-09-05.md
```

---

## 1. What the scan is, in one paragraph

Sean's clef session found a lot being lost because a staff's clef was either
SELECTED or DISCARDED, with nothing between. This surveyed the rest of
`tools/omr/` (57 modules) for the same shape and answers by taxonomy: **A** the
probability is never formed; **B** formed then quantised; **C** formed, kept,
consumed by nobody; **D** used only as an exclusive tier or a raw argmax; **E**
all-or-nothing structural refusals. It is a survey — **no arm was run**, the
weights were absent from the container, and nothing in it is a benchmark result.

---

## 2. ⚠️ THE SCAN WAS WRITTEN WITHOUT KNOWING THE CALIBRATION EXPERIMENT HAD ALREADY FAILED

`claude/staff-identity-layer-2026-09-05` ran the experiment the scan's
recommendations assume is worth running, and it came back negative. Commit
`2dff2503`, "staff identity: NEITHER probability calibrates, so neither is
emitted":

```
P(name)  Brier 0.0887  ECE 0.1277        P(set)   Brier 0.1036  ECE 0.1301
  [0.70,0.90)  n=88  pred 0.823  obs 1.000   +0.177
  [0.90,0.98)  n=96  pred 0.945  obs 0.885   -0.060
  [0.98,1.01)  n=13  pred 0.989  obs 0.692   -0.297
```

Three things in it bind anything downstream:

1. **It fails worst exactly where a consumer would set its bar.** The top bin
   promises 0.989 and delivers 0.692. A clef override demanding 0.99 would be
   buying the least trustworthy part of the curve.
2. **The pre-registered standard is the important artifact** —
   `benchmarks/omr-staff-identity-layer-2026-09/PRE_REGISTERED.md`. *An
   uncalibrated probability is WORSE than none, because it launders a guess into
   something that reads as evidence.* **This scan adopts that standard.** Nothing
   on its shortlist should ship as a confidence number that has not cleared it.
3. **The failure is the corpus, not the estimator.** Tier counts were label 175 /
   roster 22 / **derived 0** — the tier whose calibration would actually decide
   an admission is empty, and no feature separated the ~15 wrong from the right
   *inside* the label tier. Their stated route is the held-out-label design at
   scale (Breitkopf labels every staff, so hiding them manufactures `derived`
   records with free truth). That is a transcription cost, not a modelling
   problem.

**Effect on the scan's shortlist:** item #3 (pass `instruments.Match.coverage`
into `slots`/`score_layouts` instead of the three-way label) is **demoted**. It
is the same family of evidence that just failed to calibrate, on the same
corpus, and it belongs to that session rather than this one.

---

## 3. What this scan still thinks is worth your time — and it is NOT a probability

⚠️ **Read `probe_fill_reach.py` first; it changes the question.** KC-3 (commit
`0daff340`) established that `clef_correction`'s FILL path fires only where NO
reader read a clef (`clef_correction.py:597`), so its reach is an intersection:
**34 of 396 staves, 8.6%**. A perfect roster and the staves needing a fill are
disjoint populations — tier B's 56 identities produced 0 applications, by
construction. Their own conclusion: *"THE REAL ANSWER TO 'DOES CLEF CONSUME
IDENTITY' IS THE 34."* The documented clef ceiling is about clefs read **WRONG**,
and those staves are invisible to FILL by definition. Reaching them means
OVERRIDE.

**So look at the OVERRIDE gate, `clef_correction.py:594-601.** It is a five-way
conjunction of booleans — the scan's Class A, textbook — and one of its
conjuncts is:

```python
and sources.get(slot) == "label"
```

⚠️ **That conjunct requires the one piece of evidence a scan structurally does
not have.** `benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md` (and
CLAUDE.md) established that of the unresolved non-treble staves on the 20-row
scan corpus, **29 of 29 are in the class "no label printed at all"** — not a
lexicon refusal, not an OCR miss. Litolff Beethoven's `Viola` and
`Violoncello e Basso` on continuation systems, Simrock Dvořák's whole p6/p7
lineup, margins measuring zero ink. So on scans the OVERRIDE path is gated shut
by a conjunct that can never be satisfied, on exactly the population that
carries the ceiling.

### The evidence that needs no label, and is already computed

`clef_register_warning` — one of the five internal-consistency checks
([internal-consistency-checks.md](internal-consistency-checks.md)) — fires when a
lower staff resolves above an upper one. It is written onto the page dict on
every run and **`grep -c clef_register_warning tools/omr/clef_correction.py`
returns 0.**

Live example, from a committed artifact rather than a hypothetical
(`benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json`):

```json
{"lower_staff_index": 4, "upper_staff_index": 3,
 "lower_staff_median_midi": 71, "upper_staff_median_midi": 53,
 "register_gap_semitones": 12,
 "lower_staff_clef": "treble", "upper_staff_clef": "bass",
 "confidence_label": "advisory"}
```

Both staves have a clef read, so **FILL cannot see this pair** — it is squarely
in the OVERRIDE population. It needs no instrument name. It asks the same
question the range fit asks, from an independent direction: the range fit asks
*is this staff plausible for its instrument*, the register check asks *is this
staff plausible for its neighbours.*

**What this is NOT.** It is not a probability, and per §2 it must not be dressed
as one. The honest form is a **conjunct swap**, not a score: whether
`sources.get(slot) == "label"` can be replaced by *"a label, OR a register
inversion against a neighbour whose clef was read"* — a second admissible
evidence source on an existing gate, priced on the 20-row scan gate, shipped
behind a flag with flag-off byte-identity. If it cannot be shown to hold that
bar, it does not ship.

⚠️ **This scan has not measured it.** No weights in the container. The claim
here is only that the gate excludes a population it need not exclude, and that
the excluding conjunct is unsatisfiable on scans.

---

## 4. Unclaimed, and adjacent to work you may already have running

Verified 2026-09-05: every live branch from that day touches **zero**
`tools/omr` files except `staff-identity-labels-2026-09-05` (`_surya_worker.py`
+ its test). Nothing below is held by anyone.

- **Cross-staff dedupe tie-break.** `transcribe._dedupe_cross_staff_detections`
  has both contested detections' confidences in hand and uses neither. With the
  written-range veto never firing on a scan (CLAUDE.md, 2026-09-05), **all 4,256
  cross-staff duplicates on the 20-row gate resolve on ladder or DISTANCE** — a
  quantity already caught being a coin flip (5-62 px). The cheapest honest form
  is one more tier *under* rank 0, not a rewrite into a posterior. ⚠️ Must stay
  PAIRWISE: a cluster-winner refactor was measured and rejected (IoU is not
  transitive). `claude/scan-attribution-2026-09-05` has just mapped the same
  gate by category — that is the measurement that could price this, so
  coordinate rather than re-derive.
- **Dynamic runs.** `export.measure_dynamics` drops a whole letter run that
  spells no known word. Per-letter confidence and edit distance to the nearest
  legal dynamic are both present and unused; CLAUDE.md already attributes ~31
  marks to this, "15 of them a lone `s`, an `sf` whose `f` was missed" — an edit
  distance of 1, discarded as noise.

---

## 5. Findings that stand regardless of the calibration result

These are facts about the tree, not proposals, and §2 does not touch them:

- **`export.py` never reads a detection confidence.**
  `grep -c '\bconfidence\b' tools/omr/export.py` → **1**, and that occurrence is
  a comment. Across the pipeline, detection confidence reaches a decision at
  **four** places (three argmax at `transcribe.py:1237/:1488/:1597`, one
  threshold at `:2893`) plus the global `OMR_CONF_THRESHOLD`.
- **Four of the five consistency warnings are read by nobody.** Only
  `rhythm_sum_warning` is consumed, by `backend/modules/local_omr.py`, as a
  boolean presence count for a UI percentage. On one real scanned document
  (3 pages, 83 staves) **85 warnings fire and every one is inert**.
- ⚠️ **Volume is uneven.** `measure_count_warning` fired **zero** times across
  29 stored transcriptions — corroborated by
  `benchmarks/omr-majority-steering-2026-08/findings.md` finding 0 disagreeing
  staves over 27 systems. The high-volume check (`rhythm_sum_warning`, 78 on
  that document) is the one carrying **no confidence field at all**, only a
  `severity` string over a real signed beat discrepancy.

---

## 6. If you are replying

This session could not message yours — `ListAgents` reports no reachable peers
across the cloud/bridge boundary, and a test send failed. The repo is the
channel. Leave a note on PR #20, or a section in your own findings naming this
document; Sean relays otherwise.
