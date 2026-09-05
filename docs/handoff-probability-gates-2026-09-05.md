# Handoff: gates → calibrated probabilities

**From** the staff-identity-layer session (2026-09-05), for the session
surveying the pipeline for gates that could become probability evaluations.
Direct messaging between our two sessions does not resolve in either
direction, so this file is the channel. **Write your findings to a path and
name it here** (append at the bottom) — or to
`benchmarks/omr-probability-gates-2026-09/FINDINGS.md` and I will read it.

Everything below is measured on this repo, not proposed. Sources are named so
you can re-derive rather than trust.

---

## 1. The standard Sean settled, so we do not grow two vocabularies

**Two quantities, kept separate, never blended, never derived from one another
by a fixed factor:**

| | means | consumers |
|---|---|---|
| **P(name)** | this specific answer is correct | must COMMIT: naming, an override, carrying a fact forward |
| **P(set)** | the truth is somewhere in this narrowed set | only RULE OUT: vetoes, priors, arbitration tie-breaks |

The gap between them is the whole value. Measured on the identity layer: where
it answers **wrong**, the truth is still in its candidate set **0.200** of the
time; where it **abstains**, **0.902**. One blended number destroys that
distinction. Each calibrates against its own event — P(name) against "was this
name right", P(set) against "was the truth in the set".

**The consequence that generalises: an abstention is not a dead end.** Under
this split, staves the namer refuses are five-way shortlists holding the answer
nine times in ten. On the identity layer the namer reaches 0.773 of staves and
the set-shaped consumers reach **1.000** — zero staves carry nothing at all.
Expect the same shape wherever a gate currently emits a binary refusal: the
refused population is usually still informative.

## 2. The bar. A probability is not a confidence score

⚠️ **A confidence score that does not separate is worse than nothing**, because
it launders a guess into something that reads as evidence. This repo's
cautionary case is `LayoutFit.agreement`: it sits at **1.000 for 70% of the
WRONG answers** against 89% of the right ones. `contextual.py:833` already
discards it, at no cost.

So the deliverable is the number **plus its validation**:

- a **reliability curve** (predicted vs observed frequency, binned) and a
  scalar — Brier and/or ECE, state which;
- **calibrated on data not used to develop the rule.** Same-data calibration
  reports fit, not calibration;
- **per publisher as well as pooled.** Publisher-shaped rules are this
  project's recurring trap — document roster transfer scored Simrock 45/45 and
  Litolff 2/50, same rule;
- ⚠️ **size the corpus from the BINS, not from what is available.** Detecting a
  0.08 miscalibration at a 0.95 bin centre needs n ≥ 29 in that bin. A curve
  drawn on fewer records than the bin design called for is the exact failure
  this exercise exists to avoid;
- ⚠️ **if it does not calibrate, emit nothing and report that.** We did this on
  2026-09-05: P(name) ECE 0.128, P(set) 0.130, top bin promising 0.989 and
  delivering 0.692 — nothing shipped.

**Prefer frequencies to models.** An empirical tier rate IS a probability
estimate and stays auditable back to "cases like this were right N of M times".

⚠️ **Once a probability exists, consumers threshold on it and the constant
becomes a decision rule nobody revisits** — which is the thing you would be
trying to fix. State each consumer's bar **with its cost-when-wrong, at the
call site**.

## 3. Which gates to go after — and which to leave alone

⚠️ **This repo's best constants sit on a measured EMPTY GAP, not a threshold.**
A probability adds nothing where the populations do not overlap: it reports
0.99 forever and invites tuning. **Leave these alone**, and check for the same
shape before touching anything else:

- notehead height — interior 0.61–1.12 staff spaces, clipped edge fragments
  0.29–0.56, nothing between;
- stem length — decays smoothly to 8 spaces and stops, then an 11× cliff to a
  second population (barlines, brackets);
- augmentation-dot offset — bimodal at 0.00 and +0.50, nothing from +0.57 to
  +3.75;
- cut-common centre-column fill — 1.00 for all 24 cut cases, ≤0.48 for
  everything else;
- direction-text lexicon gate — **load-bearing, do not loosen** (recorded in
  CLAUDE.md).

**The candidates are the priced TRADES — gates chosen knowing they cost
something:**

| gate | where | why it is a candidate |
|---|---|---|
| **`OMR_CONF_THRESHOLD` = 0.25** | one global number for **208 classes** | strongest in the pipeline: the shipped weights bake per-class floors into the head BIASES because there was nowhere else to put them |
| `dot_single_clear_is_enough` | `clef_locator` | explicitly recorded as a trade: −8 false positives for −20 declined C clefs |
| `_dedupe_cross_staff_detections` | `transcribe` | ladder → range → distance, each tier binary; the distance tie-break is near a coin flip (5–62 px in the hairpin case) |
| `_stitch_slots` refusal | `export` | hard refusal on disagreeing staff counts drops you into per-system fragments — a much worse fallback |
| dossier slot-level checks | `dossier` | run only when staff count == part count, else abstain whole |
| `mxl_verdicts` labels/queue | training | already tier-shaped; Phase C found every policy lands 0.815–0.859 — the signature of a decision wanting a number, not a band |
| agreement floors 0.70 | time-sig vote, key-sig vote | |
| alignment strength ≥ 0.5 | pre-fill | |

## 4. ⚠️ The result that inverts the obvious hypothesis — check REACH first

Measured 2026-09-05 on the clef consumer, pricing identity tiers by edits:

| tier | identity precision | edits moved |
|---|--:|--:|
| roster | **1.000** | **0** |
| derived | 0.550 | −13 (from **2** applications, one a regression) |

**The perfect tier moved nothing and the worst tier moved everything.** Not a
paradox: the consumer applies only where no clef was read (34 of 396 staves),
and the perfect tier's identities were all on pages where every clef was
already read. **A perfect answer and the population that could use it were
disjoint.**

> **Value on a consumer path is a function of REACH first and precision
> second.** Before measuring any gate's accuracy, measure how many cases it
> can actually act on.

The same diagnostic killed the headline motivation: the documented clef ceiling
is clefs read **WRONG**, and those staves *have* a clef, so the ungated path
cannot see them by definition.

## 5. A gate is sometimes right, and one earned its keep the same day

`clef_correction` requires a literal `"label"` source before overriding a clef
that was actually read. Its own comment (`:477`) names why — *"the p2 violas
are named Violin by the prior"*. Our held-out arm reproduced exactly that,
Viola→Violin ×3. And on the **ungated** neighbouring path, the derived tier
*named* a staff rather than abstaining and produced a regression — the gate's
predicted hazard appearing next door to it.

**A probability does not remove such a gate; it lets each consumer set a bar by
what a wrong answer costs.** Where that cost is a whole staff of wrong pitches,
expect the honest answer to be a high bar admitting few cases — and report the
**admissible population beside the threshold**, because a well-calibrated 0.99
that admits four cases is the §4 result in a different costume.

---

## Reply here

Append your path, or drop findings at
`benchmarks/omr-probability-gates-2026-09/FINDINGS.md`.

Things I would find most useful back: which gates you find sitting on **overlapping**
populations (the real candidates), and any gate whose refused population turns
out to be large — that is where the P(set) half pays.
