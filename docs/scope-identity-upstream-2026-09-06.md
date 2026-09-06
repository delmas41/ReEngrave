# Scope — identity as an upstream product, with side channels

**Sean, 2026-09-06.** Two ideas, and the second is what makes the first
tractable:

1. **Identity should be upstream.** Which instrument a staff is should be a
   product the pipeline makes early, with clef / key / range / doubling as
   *consumers* of it — "the dossier's evidence without the dossier". (First
   framed 2026-09-05.)
2. **A main flow does not forbid side channels.** Information can also be used
   by secondary processes running outside the primary flow, simultaneously, and
   interactively.

(2) dissolves the objection that killed (1) on its own. Identity needs pitches
(the register check compares a staff's median MIDI to an instrument's range) and
pitches need clefs which need identity. A strict reordering cannot resolve that
circle. A **shared evidence store that several processes read and write, run to
a fixed point**, can — and it is the ordinary answer to this shape of problem.

---

## 1. What is already true — this is NOT a rewrite

Three assets exist that a naive reading of "invert the pipeline" would assume
have to be built.

**The feedback edge already exists.** `clef_correction.apply_proposal` —
*"Restate every pitch on the staff under the proposed clef, in place."* It
re-derives every notehead's pitch from a changed clef, handles the key-signature
restatement, and drops `pitch_candidates` because they were ranked against the
OLD clef. **Identity → clef → pitch is already a wired path.** It is throttled,
not missing.

**Two consumers are already additive-evidence models.** `slots.py` scores
staff↔slot pairs by summing label / group / position terms; `score_layouts.py`
fits layouts the same way. They are the right shape for evidence to flow into.

**Identity already produces a rich block** — `contextual` emits slot maps, per
slot instruments, provenance (`instrument_source`), label evidence and a
reference layout, all serialised into the result JSON.

## 2. What is actually missing

**Reach, not mechanism.** `clef_correction`'s fill tier reaches **34 of 396
staves (8.6%)**, because it fires only where NO clef was read — while the
documented ceiling is clefs read **wrong**. The override tier that would address
that is gated behind `sources.get(slot) == "label"`, which is **unsatisfiable on
scans**: measured over the 20-row scan corpus, **29 of 29** unresolved
non-treble staves have no label printed at all.

**Identity is terminal by construction.** `apply_contextual_analysis` runs at
`transcribe.py:4970`, last, and says so: *"a POST-PASS over the built page
dicts... nothing about detection, rhythm or segmentation changes. It runs last
for that reason."* Only four modules consume identity at all
(`absent_instrument`, `clef_correction`, `contextual`, `transcribe`), and
**nothing re-runs after it**.

**Evidence is destroyed before anyone could use it.** From the probability-gates
taxonomy (`docs/handoff-probability-gates-2026-09-05.md`):

- `grep -c '\bconfidence\b' tools/omr/export.py` returns **1, and it is a
  comment** — the exporter treats a notehead detected at 0.26 and one at 0.98 as
  equally true.
- The five internal-consistency checks compute a graded confidence that
  **nothing reads**. Re-verified today: `key_consistency_warning` and
  `meter_consistency_warning` have **zero consumers** outside their producer. On
  one real scanned document **85 warnings fire and every one is inert**.
- `instruments.Match.coverage` is a float, quantised to high/medium/low, then
  flattened to a flat `SCORE_LABEL_MATCH = 6.0`. Binarised twice on the way into
  a model that is already additive.

## 3. The shape this wants

**Not** "move contextual to the front". Three parts:

**(a) A cheap identity pass BEFORE pitch.** The evidence that needs no pitches —
margin labels, bracket structure, staff counts, score order, roster — runs
early and publishes a per-staff identity hypothesis with its provenance.

**(b) The register-dependent half stays late**, and becomes a *second* pass that
can revise. `apply_proposal` already restates pitches, so a revision is
affordable. Bound the iteration (2 passes, not a loop to convergence) and
require it to be monotone in evidence — a pass may add or overturn on stated
grounds, never oscillate.

**(c) Side channels, per Sean's point.** The consistency checks, the register
inversion check, detection confidence and the label-contradiction signal all
already exist and reach nobody. They do not belong in the main flow; they belong
as *observers writing into the shared store*, which the identity pass reads. The
label-contradiction check recorded today is exactly this shape: free evidence,
already computed, currently discarded.

## 4. ⚠️ The two things most likely to sink it

**Calibration.** The `claude/staff-identity-layer-2026-09-05` branch was asked
for calibrated identity probabilities and measured that **neither calibrates** —
P(name) ECE 0.1277, P(set) 0.1301, n=197 — failing worst exactly where a
consumer would set its bar (top bin promises 0.989, delivers 0.692). Its
pre-registered standard was adopted: **an uncalibrated probability is WORSE than
none, because it launders a guess into something that reads as evidence.** So
this scope must NOT ship confidence-weighted fusion until calibration is
demonstrated on a held-out set. Ordinal tiers with stated provenance are the
honest interim.

⚠️ The diagnosis there was that the failure is the **corpus** (the `derived`
tier that would decide an admission is EMPTY), not the estimator. Building the
corpus is therefore a prerequisite, not a side quest.

**Measurability.** ⚠️ **Neither standing benchmark can see any of this.** Part
names do not reach OMR-NED at all — musicdiff does not score them — so the whole
identity layer is invisible to the headline figure, to the 20-row scan gate and
to `orchestral_eval`. That is why today's faults were found by forensics on one
work rather than by a benchmark going red, and why spans making Brahms four
times worse sat under a green benchmark. **A harness has to come first or this
work cannot be judged.** Sean's 2026-09-05 redirect — score structure against
THE PAGE, not the MXL — is the right substrate, and its check 1 needs no truth
at all.

## 5. Phases, each with its own gate

| # | phase | gate |
|---|---|---|
| 0 | **Harness first.** Per-staff identity scored against held-out labels on label-everything publishers, plus the page-truth structure checks. | Reproduces today's known faults: Beethoven's 7, Brahms's 149. If it cannot SEE them it is not a harness. |
| 1 | **Shared evidence store**, write-only at first: every existing signal (labels, brackets, order, roster, consistency checks, detection confidence) recorded with provenance. No consumer. | Byte-identical output. A pure observation layer must change nothing. |
| 2 | **Early identity pass** on the pitch-free evidence; late pass keeps the register half. | Identity accuracy up on the phase-0 harness; export byte-identical where identity is unchanged. |
| 3 | **Widen the clef reach** — the `sources == "label"` gate replaced by the store's evidence, incl. `clef_register_warning`, which names no instrument and so is available exactly where labels are not. | Measure REACH before accuracy (34/396 today). Then accuracy on both families. |
| 4 | Side-channel observers wired as evidence, one at a time, each priced. | Per-observer A/B; anything unpriced stays off. |

## 6. Cost, honestly

Phases 0-1 are a few sessions and are low-risk. Phase 2 touches the spine of
`transcribe` and is where the schedule risk lives. Phase 3 is where the payoff
is (clef is the documented pipeline ceiling; order-conditioning took clef
0.562 → 1.000 in the identity-layer experiment, so the headroom is real). Phase
4 is open-ended and should be cut to whatever earns its measurement.

**The honest alternative to all of this** is to keep patching the terminal
post-pass, which is what today was. It works — Beethoven's 7 went to 0 — but
each fix is one work deep and invisible to every standing benchmark, which is
precisely how a default that makes a second work four times worse got shipped.

## 7. "Interactive" means the PROCESSES talk — settled 2026-09-06

Sean's clarification, and his reason: **human interaction is the most expensive
part of the process.** So inter-process exchange is not a cheaper substitute for
a human-in-the-loop design — displacing human arbitration is the *point*, and it
is what this project exists to do.

That raises the bar above the write-only store of phase 1. Talking means a
consumer can **push back**: the pitch resolver can say *"under this clef this
staff's register is absurd"*, identity can answer *"then try viola"*, and
`apply_proposal` restates the pitches. That is constraint propagation, not a
blackboard.

**The template already exists.** `contextual._labels_for_page` runs three
readers cheapest-first — PDF text layer (free), Surya OCR (free), Claude Vision
(~1c/system, off by default) — and **only pays when the free ones come back
empty**. That is already one process asking another a question, with a cost
model. Generalising it is the design, not inventing it.

⚠️⚠️ **AND THE FAILURE MODE IS ALREADY MEASURED — this is the thing that will
break it.** Processes that talk can **confirm each other's mistakes**. Identity
tells the clef reader "you are a viola"; the clef reader reports alto; identity
counts that as corroboration. One guess becomes two agreeing signals, and the
loop is invisible because every participant is behaving correctly.

**Three separate places in this codebase already refuse a feedback edge on
exactly these grounds**, which is unusually strong evidence for a hazard that
has not been designed for yet:

- `clef_correction.py:396` — the instrument-clef mechanisms act only on identity
  a reader **actually READ off the page**, *"never score-order deductions —
  measured to close the loop on its own mistake, Beethoven 5 p.15"*.
- `dossier.py:436` — the part→staff join pins on margin LABELS, never on clefs,
  because *"would be circular exactly where it matters"*.
- `score_layouts.py:683` — the same refusal again.

**So the safety rule is PROVENANCE, not topology.** It is not enough that the
control flow has no cycle; the *evidence* must have no cycle. A message may be
consumed only by a process whose own output did not contribute to it. The field
that makes this checkable already exists and is already load-bearing —
`instrument_source` (`label` / `roster` / `score_order` / `score_order_ambiguity`)
— and it was the discriminator that made today's label-contradiction finding
safe: without it, that check reports our own landed fixes as defects.

**Design consequences, concretely:**

1. Every message carries its provenance chain, not just its value.
2. A process refuses a message whose chain contains itself. Read-off-the-page
   evidence may circulate freely; deduced evidence may not return to its own
   deducer.
3. Corroboration counts only across **independent** chains. Two signals sharing
   an ancestor are one signal.
4. Bounded rounds with a stated stopping rule, and every revision recorded with
   what changed it — the project already does this (`rhythm_reconciliation`,
   `weight_routing`, `ambiguous_labels_resolved` are all self-describing).

**And the phase gates need a human-cost axis**, since that is the stated payoff:
alongside identity accuracy, measure **flagged differences a human would have to
adjudicate**. A change that improves accuracy but not review load has not
delivered what it was built for.

## 8. Open, and deliberately not decided here

- Whether the early pass runs per page or per document. A whole-work run has
  more evidence; the web app's default window is `OMR_MAX_PAGES=5`, pages 0-4.
- Whether identity revision may change SEGMENTATION. Everything above holds it
  fixed. Letting it move is a much larger claim.
- ~~What the stopping rule is when two processes disagree and neither yields.~~
  **Settled 2026-09-06 (Sean): escalate to a human, but only as a LAST RESORT.**
  So abstention is permitted and is not free — it is the most expensive outcome
  the system can produce, and the phase gates count it as such (see the
  human-cost axis in §7). A process may abstain; it may not abstain *cheaply*.

## 9. Which arrow carries the information — measured, 2026-09-06

Sean, thinking through the circle: *"if we know a clef or a range of notes we can
narrow down what the instrument could be... once we know the instrument it should
inform verification of the clef and pitches."*

Right in shape, and §7's hazard is narrower than it was stated. **The bad case is
using a DEDUCTION to confirm the OBSERVATION it was deduced from** — deduce
"viola" from an alto clef, then count that clef as corroborating "viola". Identity
informing a *different* observation is legitimate, and the pipeline already does
it: `contextual` sets `clef_source = "slot_continuity"` — a staff that read no
clef takes the clef its own part read on ANOTHER system. Two independent looks at
one fact. Measured 48/52 → 49/52.

⚠️ **But `range -> instrument` is measured to be nearly information-free.** A
family's range is the UNION of its members', percussion spans 0-127, and across
the scan corpus only **5 detected pitches of 9,219** fall outside their family's
union (`benchmarks/omr-structural-parts-2026-09/`). As a way to narrow WHICH
INSTRUMENT, notes-in-range carries almost nothing. It is strong only with a
dossier naming the exact part — and the scan benchmark runs dossier-free by
protocol, which is why the written-range veto has NEVER FIRED ON A SCAN.

✅ **The strong arrow is `range -> CLEF`, and it is computed and discarded.** Not
"which instrument" but "is this clef possible at all": two staves whose registers
are INVERTED (the lower sounding higher) is a clef error whatever the instruments
are. `clef_register_warning` already computes it — Brahms staves 3 vs 4, median
MIDI 53 against 71, a 12-semitone inversion, labelled `advisory`. Verified
2026-09-06: **zero references in `clef_correction.py` and no consumer anywhere in
`tools/omr`, `backend` or the frontend.**

Two properties make it the best lever available:

1. **It needs no instrument name** — so it is available exactly where label
   evidence is structurally absent (29 of 29 unresolved non-treble staves on the
   scan corpus print no label at all).
2. **It is a comparison BETWEEN two staves**, so it cannot confirm itself — it
   satisfies §7's provenance rule by construction rather than by a gate.

So the corrected reading of Sean's loop: not `notes -> instrument`, but
`notes -> "that clef cannot be right" -> identity -> verify the pitches`.
