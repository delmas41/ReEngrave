# Probability gates in the OMR pipeline — where a decision collapses to a boolean

**Consolidated note, 2026-09-05.** Everything the probability-decision-scan
session produced now lives in this one file; it previously sat in two
(`scan-probability-decisions-2026-09-05.md` and
`handoff-2026-09-05-probability-decision-scan.md`), both now removed.

⚠️ **If you have your own notes for this path, they belong ABOVE this line** —
this document is written to be appended to, and everything below was added by
the scan session.

---

**The question.** The clef session found that a lot was being lost because a
staff's clef was either *selected* or *discarded*, with nothing in between and
no way to combine the several things the page already knew. Sean asked whether
that shape occurs elsewhere: where else does a decision collapse to a boolean,
what would a probability be worth there, what is the blast radius, and where
could an existing probability be combined with evidence gathered somewhere else?

This is the sibling of
[docs/discussion-detector-right-output-wrong-2026-09-04.md](discussion-detector-right-output-wrong-2026-09-04.md).
That one asks *"the pipeline knew the answer and wrote a different one — where
else?"*. This one asks **"the pipeline had a degree of belief and threw it away
— where else?"** Same method: a taxonomy, because "decided without a
probability" is not one failure mode, and each class needs a different repair.

**Nothing here is a code change.** It is a survey with a ranked shortlist and
per-item blast radius, so the next session can pick an item and price it rather
than rediscover the landscape.

---

## Method, and what it can and cannot see

- Read every hard threshold and abstention gate in `tools/omr/` (31,346 lines,
  57 modules): all module-level numeric constants, every `abstain` mention, and
  the decision bodies of the arbitration functions.
- Grepped the consumer side for each probability the pipeline *computes*, to
  find the ones nothing reads.
- Probed **29 stored transcription JSONs** in `benchmarks/` for the graded
  signals the internal-consistency layer writes, to get a real firing rate
  rather than an assumed one.

⚠️ **The OMR weights are not in this container** (`omr-weights/` is gitignored
and absent), so nothing here was re-measured end to end. Every count below is
either read off committed artifacts or cited from a benchmark that already
measured it. **No claim here is a benchmark result**; the shortlist says which
harness would have to price each item, and — following this repo's hard-won
rule — whether that harness can *see* it at all.

---

## ⚠️ Read this before the shortlist: the calibration experiment already failed

**Added 2026-09-05, after cross-session review.** This survey was written
without knowing that `claude/staff-identity-layer-2026-09-05` had already run
the experiment its recommendations assume is worth running. It came back
negative, and the result binds everything below. Full reconciliation and the
handoff to that session:
the "For the session picking this up" section below.

Commit `2dff2503`, "staff identity: NEITHER probability calibrates, so neither
is emitted" — 197 records, held out by engraving:

```
P(name)  Brier 0.0887  ECE 0.1277        P(set)  Brier 0.1036  ECE 0.1301
  [0.98,1.01)  n=13  pred 0.989  obs 0.692   -0.297
```

It fails worst exactly where a consumer would set its bar. Their pre-registered
standard — `benchmarks/omr-staff-identity-layer-2026-09/PRE_REGISTERED.md` —
is that **an uncalibrated probability is WORSE than none, because it launders a
guess into something that reads as evidence**, and on that standard they emitted
nothing. **This document adopts that standard.** Nothing on the shortlist below
should ship as a confidence number that has not cleared it.

Their diagnosis is that the failure is the CORPUS, not the estimator: tier
counts were label 175 / roster 22 / **derived 0**, so the tier whose calibration
would actually decide an admission is empty.

Two consequences, both applied to the table below:

- **Item #3 is demoted.** Passing `coverage` into the slot aligner is the same
  family of evidence that just failed to calibrate, on the same corpus. It
  belongs to that session.
- **Item #1 is re-framed, and is not a probability.** Their KC-3 result
  (`0daff340`, `probe_fill_reach.py`) shows `clef_correction`'s FILL path reaches
  only **34 of 396 staves (8.6%)** because it fires only where no clef was read,
  while the documented clef ceiling is about clefs read WRONG — invisible to
  FILL by definition. The reachable question is the OVERRIDE gate at
  `clef_correction.py:594-601`, a five-way boolean conjunction whose
  `sources.get(slot) == "label"` conjunct is unsatisfiable on scans (29 of 29
  unresolved non-treble staves have no label printed). `clef_register_warning`
  needs no label and fires on that population. The honest form is a **conjunct
  swap on an existing gate**, not a score.

---

## The taxonomy: five ways a degree of belief is lost

### Class A — the probability is never formed

A boolean veto with no score behind it. The decision is a cliff, and a case one
pixel to the wrong side of it is discarded with no record that it was close.

The repo already knows this hurts, and has priced it once in exactly the terms
Sean is asking about. From CLAUDE.md on the C-clef locator's dot veto:

> **FALSE POSITIVES 13 → 5.** Unlike everything else here this is a TRADE, taken
> deliberately — 8 false positives removed for 20 declined C clefs.

That sentence *is* a probability threshold being set by hand, on a score that
does not exist. With a calibrated score the same knob would be a threshold on a
number, and the 20 declined clefs would be recoverable by whatever downstream
evidence disagreed. Today a declined clef leaves no trace for anything to
reconsider.

Members: the `clef_locator` veto cascade (`dot_single_clear_is_enough`,
`min_symmetry_mezzosoprano`, the proportions veto — each an early `return None`);
`export.measure_dynamics` discarding a whole letter run that spells no known
word; `_reconcile_measure_to_meter`'s uniqueness requirement; the
`_drop_clipped_notehead_fragments` height gate.

### Class B — formed, then quantised before it is used

A genuinely continuous quantity is computed, bucketed into a label, and the
label is what travels. The resolution is lost at the boundary, not at the source.

The clean example is instrument identity. `instruments.Match` carries
`coverage: float` (the fraction of the label's letters the matching alias
covers) and `ocr_folded: bool`. `Match.confidence` reduces both to
`"high" | "medium" | "low"`. Then `slots.py`:

```python
MIN_LABEL_CONFIDENCE = ("high", "medium")   # "low" is treated as absent
...
score += SCORE_LABEL_MATCH if label == slot.instrument else SCORE_LABEL_CONFLICT
```

**`slots.py` and `score_layouts.py` are already additive-evidence models** —
exactly the architecture the clef work wants — and the label evidence entering
them is binarised twice on the way in: `low` is dropped entirely, and `high` and
`medium` then score an identical `6.0`. A label matching at coverage 0.61 and
one matching at 1.00 are indistinguishable to the aligner, and a 0.59 is not
there at all.

Members: the above; the five internal-consistency checks' `confidence_label`;
`rhythm_sum_warning`'s `severity` string over a real beat discrepancy;
`clef_correction.ClefProposal.confidence_label` (it does keep `fit` and
`margin` alongside, which is better than most).

### Class C — formed, kept, and consumed by nobody

The probability survives into the output and nothing ever reads it. This is the
largest class by volume and it has the two biggest single findings in the scan.

**C1. `export.py` never reads a detection confidence — not once.**

```
$ grep -c '\bconfidence\b' tools/omr/export.py
1                      # ...and that one occurrence is inside a comment
```

Every symbol the detector emits carries a confidence. The exporter treats a
notehead detected at 0.26 and one detected at 0.98 as equally true. Across the
whole pipeline, detection confidence is consulted as a **decision input at four
places**: three `argmax` picks (clef and label reads at `transcribe.py:1237`,
`:1488`, `:1597`) and one threshold (`_drop_unladdered_noteheads`,
`transcribe.py:2893`) — plus the single global `OMR_CONF_THRESHOLD` gate at
detection time. It reaches no export decision, no arbitration tie-break, and no
consistency check.

**C2. The internal-consistency layer's confidence is read by nobody.**

Five checks compute a graded confidence on every page
([docs/internal-consistency-checks.md](internal-consistency-checks.md)). Grepping
every consumer outside `transcribe.py` and the tests:

| warning | consumed by |
|---|---|
| `measure_count_warning` | *nothing* |
| `key_signature_warning` | *nothing* |
| `clef_register_warning` | *nothing* |
| `time_signature_disagreement` | *nothing* |
| `rhythm_sum_warning` | `backend/modules/local_omr.py` — as a **boolean presence count** for a UI quality percentage |

**Measured, on one real scanned document** (Breitkopf Brahms 1, 3 pages, 83
staves, `benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json`):
**85 warnings fire** — 78 `rhythm_sum`, 4 `time_signature_disagreement`, 2
`clef_register`, 1 `key_signature`. Every one carries either a confidence float
or a signed magnitude. Every one is inert.

⚠️ **Volume is uneven and the honest reading matters.** Across all 29 stored
transcriptions, `measure_count_warning` fired **zero** times — corroborated
independently by `benchmarks/omr-majority-steering-2026-08/findings.md`, which
found 0 disagreeing staves across 27 systems. The graded checks are low-volume;
`rhythm_sum_warning` is the high-volume one (74 `high` / 4 `low` severity on
that document, beat-error quartiles 0.5 / 1.0 / 2.0 / 4.0, max 15.0) **and it
is the one with no confidence field at all.**

### Class D — formed and used, but only as an exclusive tier or a raw argmax

Evidence exists in several kinds, and the first kind that speaks decides; the
rest are never consulted, and a near-tie is indistinguishable from a landslide.

`transcribe._dedupe_cross_staff_detections` is the worked example, and it is
already halfway to the fix — it computes a `rank` per verdict (2 = ledger
ladder, 1 = written range / hairpin-has-notes, 0 = distance) and applies strong
verdicts first, which was itself a measured improvement. But the ranks are
**exclusive**: once the ladder speaks, range and distance are never asked, and
within a rank every verdict is equal. Rank 0 is a large population decided by a
quantity the repo has already caught being a coin flip:

> measured, the three misattributed detections were only 5-62 px nearer staff
> 18's top than staff 17's bottom, against 25 px the other way for the one
> correctly kept, close enough that distance is nearly a coin flip.

And the loser is deleted outright, so nothing downstream can revisit a 5-px call.

⚠️ **This class contains the scan pipeline's single biggest unarbitrated
population.** CLAUDE.md records that the written-range veto has never fired on a
scan — `_staff_written_ranges` returns `{}` with no dossier, and the scan gate
runs dossier-free by protocol — so across the 20-row scan gate **all 4,256
cross-staff duplicates are resolved by ladder or by distance alone.**

Members: the above; `key_signature_vote`'s "the reading with the most
accidentals wins" (a count-argmax, sound because under-counting is the only
failure mode, but blind to how well each reading fit its slot table); the three
`best_conf` argmax picks in `transcribe.py`.

### Class E — all-or-nothing structural refusals

A join abstains for a whole page or a whole part rather than reporting per-unit
confidence. Correct as far as it goes — each was adopted because guessing was
measured worse — but the refusal is total and carries no gradient, so nothing
partial survives and no downstream evidence can rescue the easy 80%.

Members: `export._stitch_slots` (returns `None` for the entire result the moment
two systems disagree on staff count); `dossier`'s slot-level checks (abstain
unless staff count equals part count exactly); `mxl_verdicts`' per-cell
alignment-strength floor of 0.5; `time_signature_locator`'s
`min_staff_fraction` page abstain.

---

## Shortlist, ranked, with blast radius

"Blast radius" in this repo's terms is three questions: how many decisions it
touches, **which harness can price it**, and — the one this repo has been bitten
by repeatedly — **whether that harness can see it at all.**

| # | Change | Class | Reach | Priced by | Can the gate see it? |
|---|---|---|---|--:|---|
| 1 | Feed `clef_register_warning` into `clef_correction` | C+D | 2 staves / scan page | scan gate, clef eval | **Partly** — `eval_pipeline_clefs` (52 staves) sees it directly; OMR-NED may not move |
| 2 | Detection confidence as rank-0 tie-break in `_dedupe_cross_staff_detections` | C+D | ~4,256 pairs over the 20-row gate | 20-row scan gate | **Yes** — this is the scan gate's own population |
| ~~3~~ | ~~Pass `coverage` into `slots` / `score_layouts`~~ — **DEMOTED**, see above | B | — | — | Same family that failed to calibrate; hand to the staff-identity session |
| 4 | Nearest-legal-word for dynamic runs in `measure_dynamics` | A | ≤31 marks on the scan gate | 20-row scan gate | **Yes** — already attributed there |
| 5 | Give `rhythm_sum_warning` a confidence from its own beat magnitude | B+C | 78 per scan document | unit tests only, at first | **No** — inert until something consumes it |
| 6 | Score the `clef_locator` vetoes instead of vetoing | A | 5 remaining FPs / 20 declined clefs | clef corpora (both — never one) | **Yes**, and only these |
| 7 | Per-part confidence from `_stitch_slots` instead of a whole-result `None` | E | 3 of 20 scan rows | 20-row scan gate | **Yes**, but tangled with `OMR_SLOT_STITCH`'s known bucket trap |

**Recommended first: #2, then #1 as a conjunct swap.** ⚠️ This originally read
"#1 and #2", with #1 described as "nearly free". After the reconciliation above,
#1 is not free and not a probability — it is a proposal to admit a second
evidence source on the OVERRIDE gate, and it belongs to the staff-identity
session's territory, so it goes to them as a note rather than being built here.
#2 is where the volume is and is held by nobody.

⚠️ **#5 and #7 come with warnings from the existing record.** #5 changes nothing
observable until a consumer exists — shipping it alone is inventory, not a fix,
and this repo has already been burned by a documented fix that was not in the
tree. #7 sits on top of `OMR_SLOT_STITCH`, which is dormant *because* recovering
continuous parts moved edits into a bucket musicdiff charges more heavily; any
work there inherits that trap and must read
`benchmarks/omr-staff-structure-2026-09/FINDINGS.md` first.

---

## The three real "combine it with something else" opportunities

These are the ones where the second piece of evidence genuinely exists today,
is independent of the first, and is available at the same point in the pipeline.

### 1. Clef: three independent signals, none combined

`clef_correction` decides on **range fit alone**, behind two hard cutoffs
(`MIN_FIT = 0.75`, `MIN_FIT_MARGIN = 0.25`) that `return None`. Two other
signals about the same question are computed on the same page and never
consulted — `grep -c clef_register_warning tools/omr/clef_correction.py` → **0**:

- **Register inversion.** `clef_register_warning` fires when a lower staff
  resolves above an upper one. On the Brahms scan it fires precisely on the
  pair staff 3 / staff 4, reporting median MIDI 53 against 71 — a
  12-semitone inversion, labelled `"advisory"`, read by nobody. That is the
  *same defect* the range fit is hunting, from an independent direction: the
  range fit asks "is this staff plausible for its instrument", the register
  check asks "is this staff plausible for its neighbours" — and the neighbour
  version needs **no instrument label**, which matters enormously, because
  `benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md` established that
  29 of 29 unresolved non-treble staves on the scan corpus have **no label
  printed at all**. The register check is the evidence that survives exactly
  where the label evidence is structurally unavailable.
- **The key signature's own fit.** The slot table a key signature is fitted
  against is *chosen by the clef*, so a clef hypothesis is falsifiable against
  ink already read: CLAUDE.md records that "a wrong clef produces wrong
  signatures rather than abstentions (measured: bass staves defaulted to treble
  read 3 flats as 2 sharps)". A candidate clef that makes the key signature fit
  its slots *better* has independent corroboration, and today re-fitting is
  never attempted.

### 2. Cross-staff arbitration: a fourth tier, already on the object

`_dedupe_cross_staff_detections` has `di["confidence"]` and `dj["confidence"]`
in hand at the moment it decides, and uses neither. The cheapest honest version
is not a rewrite into a posterior — it is **one more tier under rank 0**: where
distance separates two candidates by less than the margin the repo has already
measured as noise (5–62 px), prefer the higher-confidence detection. Given the
range veto never fires on scans, rank 0 is where nearly the whole scan
population lands.

### 3. Dynamics: per-letter confidence plus a lexicon distance

`measure_dynamics` builds a run of letters and drops it whole unless the run is
in `_DYNAMIC_WORDS`. Both ingredients for a graded decision are present and
unused: each letter's detection confidence, and the edit distance from the run
to the nearest legal dynamic. CLAUDE.md already attributes the loss and even
names the mechanism — "15 of them a lone `s`, an `sf` whose `f` was missed" —
which is an edit distance of 1 from a legal word, discarded as if it were noise.

---

## Checked, and deliberately not on the list

Recording the negatives, so the next pass does not re-walk them:

- **The five consistency checks' abstain-on-near-even-split rule** is correct
  and should stay. With no external anchor a 2-2 disagreement genuinely cannot
  say which side is wrong. The finding is that the confidence it *does* compute
  is unused — not that it should assert more.
- **`key_signature_vote`'s "most accidentals wins"** rests on a real asymmetry
  (the geometry layer can lose an accidental but cannot invent one) and its
  `can_carry` restriction was added after a measured page regression. Sound as
  it stands; only its blindness to per-reading fit quality is a gap.
- **`hairpin_detection.CV_CONFIDENCE = 0.99`** looks like a fake probability and
  is not one — it is a deliberate sentinel, documented as such and tagged
  `detector: "cv"` so a downstream filter cannot silently drop a CV reading.
  Leave it.
- **The `_dedupe_cross_staff_detections` pairwise structure** — a
  cluster-winner rewrite was measured and rejected (IoU is not transitive). Any
  probability work here must stay pairwise.
- **`OMR_CONF_THRESHOLD` as a single global gate** is a real Class-A cliff, but
  the per-class fix already shipped by a different route: the production weights
  bake per-class confidence floors into the head biases
  (`merge_class_head.py --bias-shift`). Re-opening it as a threshold question
  would duplicate that.

---

## Checklist

- [x] Scan every threshold / abstention gate in `tools/omr/`
- [x] Grep the consumer side for each computed probability
- [x] Probe 29 stored transcriptions for real firing rates
- [x] Confirm no prior probability-fusion work exists (`git log --all -S`)
- [x] Taxonomy, shortlist, blast radius per item
- [ ] **#1** — `clef_register_warning` → `clef_correction` *(hand to the clef session)*
- [ ] **#2** — detection confidence as rank-0 tie-break
- [ ] **#3** — `coverage` into `slots` / `score_layouts`
- [ ] **#4** — nearest-legal-word for dynamic runs
- [ ] #5–#7 — deferred, see the warnings above

---

# For the session picking this up

## 1. What is worth your time — and it is NOT a probability

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

## 2. Unclaimed, and adjacent to work you may already have running

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

## 3. If you are replying

This session could not message yours — `ListAgents` reports no reachable peers
across the cloud/bridge boundary, and a test send failed. The repo is the
channel. Leave a note on PR #20, or a section in your own findings naming this
document; Sean relays otherwise.
