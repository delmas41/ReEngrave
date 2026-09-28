# The question and its likelihood

*Calibrated candidates, the unclassified ink, and a multiple-choice review.*

**2026-09-28. PLANNING ONLY. No code until the manager dispatches it**
(DECISIONS 2026-09-28). Written by a planning session from a conversation
with Sean. Every claim about the tree names a file or a `FINDINGS.md` and was
checked against `origin/main` at `ab1bb486`. Roadmap: **Phase 6**.

This document is the reasoning behind Phase 6, as the 09-22 plan is for
Phases 0–5. It restates no measurement it can point to. Read it by section;
§5 is the work, §8 is what Sean still has to answer.

---

## 0. What Sean asked for, in his words

> *"At some point I imagine we will get to a point where we are able to
> determine what most everything is on a page but there will always be a few
> things that just need a human to decide. My hope at that stage is that the
> UI shows the human the measure in question and then gives a multiple choice
> answer of what the ink could be. To do this our staged pipeline would need
> to have a probability assigned to every symbol/ink blob and that number
> would determine how likely it is that it is a rest or a quarter note, etc."*

> *"I think the probabilities idea got ruled out too early because at the
> time the structure/system could easily lead to over confidence and cyclical
> feedback. With the new staged pipeline I can see how the probabilities
> portions could be very helpful both as we start to categorize what
> initially is hard to box in the gather stage and to help us improve the
> system in the long term based on measuring the systemic probabilities
> compared to the human answers."*

> *"I think the narrow process helps make a decision when we [already] know
> something about the ink, just not enough to make a decision. This could be
> a way to tackle the unidentified but visible ink — the initially unboxable.
> And I can see how this probability score along with the basic 3 way rule
> decision — combined could be even stronger. Also we found that where
> certain information relies on other symbols being determined but are
> afraid of it being a feedback loop it is helpful to know which info is more
> likely true."*

> *"I don't want to start any actual coding until the current session that
> is doing the Coding reaches a break so that I can have one main manager
> agent coordinating all of this."*

**Four goals follow from those words:**

1. **The question.** A human is shown one bar and a short list of what the
   ink could be, and picks one, or "none of these".
2. **Calibration.** The pipeline's likelihoods are measured against the
   human's answers and get better from them.
3. **The unclassified ink.** Ink the detector did not box is narrowed from
   what we DO know about it (shape, position, the detector's weaker guesses),
   instead of staying unread.
4. **Ordering without a loop.** Where two decisions depend on each other,
   the more certain one informs the less certain, never the reverse.

---

## 1. What the tree already has, and what it does not

**Already built (the structure for goal 1 exists):**

| what | where |
|---|---|
| `Outcome.NARROWED`: "it is one of these, and I cannot choose", with `Candidate`s ordered best first | `staged/record.py` (`Outcome`, `Candidate`, `Verdict.candidates`) |
| Decisions that narrow today: duration on ambiguous beams (`beams_ambiguous`), a rest whose slot contradicts its class (`rest_slot_contradicts_class`), `slot_index`, direction text, clef | `adjudicators/rhythm.py`, `identity.py`, `text.py`, `clef.py` |
| EXPORT refuses to argmax a narrowing and counts it (`duration_narrowed`) | `staged/export.py`, `status_census` |
| INFER may collapse a NARROWED verdict to one of its own candidates, labelled, and never overturns a DECIDED one | `staged/infer.py`, CLAUDE.md §4a |
| The review viewer: one staff, one bar at a time; human answers filed as evidence; re-run through `pipeline.decide` | `staged/review/`, ROADMAP 3.4 |
| **A first set of human answers about detector boxes**: Sean's three passes (confirm / relabel / nothing / owned elsewhere on named glyphs) | `benchmarks/omr-stage-review-2026-09/out/sean-*/sean.sidecar.json` |
| `Q.INK`: every connected piece of ink, unfiltered, with its shape and which detector classes overlap it | `gather.gather_ink`; `benchmarks/omr-ink-gather-2026-09/FINDINGS.md` |
| Sean's methodology: the ink is the subject, and a box may carry several candidate labels (detector top-k, CV locators) | DECISIONS 2026-09-23 (*shape from the class, role from the geometry*) |
| The ink-first route sized (not built): what the detector call must return, what the record must hold, what it costs | `benchmarks/omr-shape-role-2026-09/FINDINGS.md` Part 2 §(c) |

**Not built:**

- **The detector's per-class scores.** `YoloDetector.detect` keeps the
  argmax class and that class's score only. Per-class scores are the raw
  sigmoid outputs before NMS: independent per class, so they do not sum to 1
  and are not a distribution. The route to them is sized in the shape-role
  FINDINGS §(c).
- **The detector's weaker guesses.** `gather.gather_detections` runs at
  `conf_threshold=0.25` and discards everything below it. Ink the detector
  "saw" at 0.08 leaves no row.
- **A likelihood.** `Candidate.support` is an order in the deciding
  function's own units, deliberately not a probability (its docstring). No
  calibration table exists, and no log records which candidates a human was
  SHOWN.
- **A way to pick a candidate.** `agree` / `disagree` on a verdict is filed
  and reaches no stage by design (`review/SIDECAR.md`).
- **A reader of `Q.INK`.** Nothing in ADJUDICATE reads it. ROADMAP 2.4c
  (zero-coverage mark-sized ink → a marked bar, never a note) is `todo`.

**How big the unclassified ink is** (pointers, not restated):

- About half of each plate's ink components are covered by no detector box
  (shape-role FINDINGS §(c), both scan documents).
- By count that population is mostly specks, and by area mostly merged
  blobs. On the one page with hand truth, a small real share is marks the
  detector missed (`omr-ink-first-2026-09/FINDINGS.md` §3).
- So goal 3 is three problems, not one: **noise**, **merges**, and **missed
  marks**.

---

## 2. Why probability was parked, and what has changed

**The park.** Plan 2026-09-22 §7 lists "a probability calibration" among the
research items that stay parked "until a count says they are worth it".
`Candidate`'s docstring forbids reading `support` as a probability. Both
rest on one measurement: calibrated **instrument-name** probabilities scored
ECE 0.1277 on n = 197, failing worst in the top bin
(`docs/architecture-decision-map.md`, "a calibrated probability anywhere").
**The diagnosis recorded beside it was "the corpus, not the estimator"**:
there was no human-answered set to calibrate against.

**What has changed since then:**

1. **There is a corpus now.** The review viewer turns every human answer
   into a row against a named subject (ROADMAP 3.4). Three passes already
   exist.
2. **The record has the guards whose absence made a probability
   dangerous:**
   - every verdict names its `basis`;
   - `Evidence.correlated_groups` counts one reader on one crop as ONE
     signal;
   - the fixpoint guard refuses a revision reachable from its own cause, and
     `single_pass_revision` bounds the one sanctioned loop;
   - INFER's harness writes only where the record has no answer, only a
     reader's own candidate, and supersedes visibly;
   - EXPORT refuses to argmax.

**What has not changed:**

- An uncalibrated number is still worse than none.
- Two readers off one raster still fall silent together (CLAUDE.md §10).

The rules in §3 exist for those two facts.

---

## 3. The rules a likelihood must obey (PROPOSED; Sean confirms in §8 Q1)

- **R1. Calibrated or absent.** A likelihood exists only for a (reader,
  family) that has a calibration table against human answers. Elsewhere it
  is `None`: declined, never defaulted. `Candidate.support` keeps its
  meaning, an ORDER.
- **R2. It lives inside NARROWED.** A likelihood never turns NARROWED into
  DECIDED by itself. Only two things may choose: INFER (labelled, above a
  bar Sean sets per family, default OFF), or a human answer.
- **R3. It is filed in INFER.** It is a labelled row naming the table it
  came from. It is never computed inside an ADJUDICATE decision (a decision
  reads the log, not a table) and never at EXPORT.
- **R4. Independent witnesses only.** Rows in one `correlated_groups` group
  are one witness. Likelihoods are never multiplied across a shared raster.
- **R5. "None of these" and "something else" are always answers.** A choice
  is never forced from a list that may not hold the truth (rule 8).
- **R6. Silence is not an answer.** A box the human saw and did not touch is
  UNANSWERED, never "confirmed". The log records what was SHOWN apart from
  what was ANSWERED.
- **R7. A table has a control that can fail.** The answers that fit a table
  never score it (a held-out split). Shuffled answers must make it worse
  (rule 7). Its bins and its minimum n are fixed before anyone looks.

---

## 4. Where each piece lives in the stages

| stage | its part in the question and the likelihood |
|---|---|
| **GATHER** | Files the detector's opinions: top-k classes with their raw scores per box, and sub-threshold boxes as a separate quantity nothing existing reads (6.3). `Q.INK` stays the unfiltered population. |
| **ADJUDICATE** | Each decision NARROWS where its evidence does not separate the candidates. A new `ink_kind` decision narrows unboxed ink from its shape and the detector's weak opinions (6.4). A human choice is read like `human_owner` is today (6.1). |
| **EVALUATE** | Strikes out candidates that cannot be right: the bar must add up (`reconcile_duration`), key and clef constraints. A narrowing that EVALUATE shrinks to one is DECIDED by consequence and needs no likelihood. |
| **INFER** | Files the calibrated likelihood (R3). Resolves dependent decisions most-certain-first (6.7). Collapses above a calibrated bar only where Sean has set one (6.8). |
| **EXPORT** | Unchanged in kind. It still refuses to argmax. Unclassified non-noise ink marks its bar as unread (2.4c). |
| **REVIEW** | Whatever is still NARROWED, plus unclassified ink, becomes a question: the bar, the ink marked, the candidates in order (with likelihoods once calibrated), "none of these", "something else". The answer is a human row, and the re-run can settle its neighbours. |

---

## 5. The work: ROADMAP Phase 6

Every item waits for the manager. None starts before the current coding
session reaches a break (DECISIONS 2026-09-28).

### 6.0 — The decision
Probability reopened as planned work. **Done**: DECISIONS 2026-09-28. The
rules in §3 are proposed until Sean answers §8 Q1.

### 6.1 — The question: a human picks a candidate
- **What.** The viewer shows every NARROWED verdict on the staff it is
  viewing as a multiple-choice panel:
  - the bar cropped and the subject marked (a corner bracket on the exact
    head, CLAUDE.md §6b);
  - the candidates in support order;
  - "none of these" and "something else".
- **The new verb.** A new sidecar verb `choose` records `{verdict,
  candidate | "none" | "other"}`. Lane A files it as a human Observation on
  the verdict's subject (one new quantity, e.g. `Q.HUMAN_CHOICE`).
- **First consumer.** `adjudicate_duration`, the largest narrowed
  population (`duration_narrowed` in `status_census`). It DECIDES with
  reason `human_choice` only on a candidate it had itself admitted. "none"
  and "other" leave it NARROWED and are reported.
- **Gate.** Reach first: how many NARROWED verdicts the viewed staff shows,
  printed before anything else. Then a pick must move that note from
  `duration_narrowed` to written in the re-export.
- **Controls.** An empty sidecar reproduces the record N/N. A pick naming a
  value OUTSIDE the candidate list is REFUSED: this is the positive control
  that the refusal can fire. RED first.
- **Re-gathers.** None.

### 6.2 — The answer log (the calibration corpus)
- **What.** Every question SHOWN is logged:
  - subject, decider, reason;
  - the candidates in the order shown, with their support;
  - the glyph's `Q.GLYPH_CONF` where it has one;
  - the answer, or `unanswered` (R6);
  - reader, and the record's provenance (commit, `dirty`).
- **Box answers too.** The same applies to box answers the viewer already
  takes (confirm / relabel / nothing). Each is a labelled judgement on a
  detector class and its score.
- **Mechanism.** An optional sidecar field `shown` (additive, per
  `SIDECAR.md`'s rule for optional fields), plus an extractor that builds
  the corpus from committed sidecars and the record they name.
- **Gate.** The extractor reproduces Sean's three existing passes. Their
  confirms, relabels and "nothing"s appear as answers. The boxes he did not
  touch appear as `unanswered`, not as confirmations.
- **Control.** A sidecar with its `shown` field stripped must be REFUSED as
  a corpus source, not silently read as "nothing was shown".
- **Re-gathers.** None. Lands with 6.1: one lane, one sidecar contract.

### 6.3 — The detector's opinions, recorded (GATHER)
- **What.** A new detector method returns, per box, the top-k classes with
  their raw scores, and the boxes between a floor (e.g. 0.05) and the
  production threshold. It uses route (1) of shape-role FINDINGS §(c): slice
  the raw prediction tensor before NMS.
- **Additive.** `YoloDetector.detect` is UNCHANGED, so legacy output is
  byte-identical. `gather_detections` files the new data as NEW quantities
  that no existing decision reads, so every current verdict is unchanged by
  construction.
- **Depends on 2.12g.** 2.12g collapses the role-twin channels at the same
  detector call. Do it first, or do both in one lane, so the top-k is taken
  over the collapsed channels (FINDINGS §(c): "(c) is DOWNSTREAM of (e)").
- **Gate.** Reach: how many unboxed `Q.INK` components gain at least one
  sub-threshold opinion, and how many boxes carry a runner-up within a stated
  margin, per page. Then the record size per page. Printed before any
  consumer exists.
- **Control.** The base record and the arm record have identical verdicts
  and an identical MusicXML. This can fail: a consumer reading the new
  quantity by accident would move it.
- **Re-gathers.** Two full re-gathers (base and arm on one tree, CLAUDE.md
  §6b). The ultralytics version (8.4.x) is probed before the method is
  written.

### 6.4 — What is this ink? (ADJUDICATE, the first reader of `Q.INK`)
- **Builds on 2.4c**, which lands first as the decided half: zero-coverage
  mark-sized ink at a corroborated column becomes a marked bar, never a
  note.
- **What.** A decision `ink_kind` on components covered by no box. It
  answers from:
  - **Shape:** size in spaces, fill, which line or space it sits on, what it
    touches.
  - **The detector's weak opinions** (6.3).
  - **Later, cross-system recurrence:** Sean, 2026-09-09: *"the same
    unrecognizable blob on every system at bar 51"*.
- **Its three outcomes:**
  - It DECIDES only where a convention Sean has stated forces it (a speck
    below a size he names; residue on a staff line's y).
  - It NARROWS among `{notehead-like, vertical stroke, merged marks, part
    of a mark, a named family…}`.
  - It ABSTAINS otherwise.
- **Output.** The unread-bar mark at EXPORT, and a question in the viewer.
  **Never a note** (rule 8).
- **Needs.** Per-component ink on the count pages (`--ink-rows`). The
  summary ink form drops the geometry this reads (shape-role FINDINGS §7).
- **Gate.** Reach per page. Then print crops of each outcome for Sean,
  `VERDICT_none_yet: null`, before any default.

### 6.5 — Calibration tables
- **6.5a (first, read-only).** A first reliability table for the
  detector's own score `Q.GLYPH_CONF` from Sean's three passes. How often is
  a box of score s confirmed, relabelled or refused, per family? It needs
  the three records on the Mac and no pipeline change. The small n is
  stated, not hidden.
- **6.5.** From 6.2's corpus, per (decider or detector family):
  - top-1 reliability;
  - **top-k coverage** (how often the right answer is on the list shown:
    the number that makes a multiple-choice panel worth showing);
  - ECE over bins fixed in advance.
- **Mechanism.** The table is an artefact with provenance: the answers used,
  n, and the tree. INFER reads it and files the likelihood as a labelled row
  (R3). A family below its minimum n has no likelihood (R1).
- **Controls.** A held-out split, and shuffled answers that must worsen the
  table (R7).
- **Location.** `benchmarks/omr-likelihood-2026-09/`, a benchmark directory
  this item authorises (rule 9).

### 6.6 — The question queue
- **What.** Walk the questions a bar at a time across staves, not one staff
  at a time. The order:
  - **By consequence first:** what an answer releases, e.g. the one
    narrowed duration in a bar 2.8 holds out, whose answer would let the bar
    add up.
  - **By calibrated uncertainty once 6.5 exists.**
- **The screen.** This is the screen Sean described: the measure, the ink
  marked, the choices.
- **Gate.** On one count page, answered questions per page against
  fix-actions per page from the cleanup count. The claim to test is that a
  question is cheaper than a fix.

### 6.7 — Most-certain-first resolution (INFER)
- **What.** Where two decisions depend on each other, the calibrated
  more-certain side informs the less-certain one, never the reverse. The
  pairs: meter ↔ bar durations, key ↔ in-bar accidental, clef ↔ pitch,
  ownership ↔ pitch.
- **Why it cannot loop.** A step reads only facts more certain than itself,
  which is acyclic by construction. The fixpoint guard stays.
- **What it replaces.** Today the direction is fixed in code (durations vote
  the meter, the meter re-reads the durations, once). With calibrated
  likelihoods it is chosen per case.
- **Default and checks.** Default OFF. Print-checked on crops before any
  flip (rule 5). Requires 6.5.

### 6.8 — Auto-accept above a calibrated bar
- **What.** INFER may collapse a NARROWED verdict to its top candidate only
  where that family's held-out top-1 reliability, at that likelihood, meets
  a bar Sean sets per family. Labelled, superseding visibly.
- **Default and gate.** Default OFF, gated on the count.
- **Scope.** This is the "auto-accept rules from recorded verdicts" of
  ROADMAP 3.4 and Phase 5, made measurable.

---

## 6. Order, and what can start first

```
6.0 ─┬─ 6.1 + 6.2 (one lane) ─┬─ 6.5 ─┬─ 6.7
     │                        │       └─ 6.8
     │                        └─ 6.6 (consequence order now; likelihood order after 6.5)
     ├─ 6.5a (read-only, on the Mac, no pipeline change)
     └─ 2.12g ─ 6.3 ─ 6.4   (2.4c lands before 6.4)
```

**The first dispatch needs no GATHER change and no weights:** 6.1 + 6.2 as
one lane, and 6.5a as a read-only measurement on the Mac. 6.3 waits for
2.12g, and both wait for the in-flight GATHER lanes (3.4g-3 Part B, 2.14) to
land, since all of them change what a gather produces.

**How Phase 6 is judged (rule 4).** Against the cleanup count, like
everything else: does the cleanup of a page get cheaper? That means fewer
fix-actions, and questions that take less time than the fixes they replace.
Top-k coverage, ECE, questions answered and ink narrowed are CONTROLS, never
headlines.

---

## 7. Lane fences for the manager (by function name)

| item | touches | collides with |
|---|---|---|
| 6.1 + 6.2 | `review/server.py` (the sidecar kind table, the panel API); `review/human_evidence.py` (`check_sidecar`, `ingest`, one new action branch); `review/static/app.js`; `adjudicators/rhythm.py::adjudicate_duration` (reads the choice); `record.Q` (one quantity); `review/SIDECAR.md` (the `choose` verb, the `shown` field) | **3.4f** (`human_evidence.ingest` and `adjudicators/clef.py`): fence on the `ingest` branch. Any 2.12 rest item in `rhythm.py`: fence on `adjudicate_duration`. |
| 6.3 | `yolo_detector.py` (a NEW method; `detect` untouched); `staged/gather.py::gather_detections`; `record.Q` | **2.12g** (the same detector call: do it first or together); **2.14** and **3.4g-3 Part B** (`gather.py`) |
| 6.4 | a new adjudicator module; `adjudicate.REGISTRY` / `ORDER`; `export.py`'s `status_census` (`_census`) | **2.4c** (lands first); any lane adding a census family |
| 6.5 / 6.5a | a new `benchmarks/omr-likelihood-2026-09/`; one INFER rule in `inferences.py` | any lane editing `inferences.py` (2.3's duration rules) |
| 6.7 / 6.8 | `staged/infer.py`, `staged/inferences.py` | the same |

---

## 8. Questions for Sean (rule 3: before any code)

- **Q1.** Do the seven rules in §3 stand as written? The ones that most
  constrain the design are R2 (a likelihood never decides by itself), R5
  (always "none of these") and R6 (silence is not an answer).
- **Q2.** How many choices should the panel show: the whole candidate list,
  or the top three plus "none of these" and "something else"?
- **Q3.** Which family first: duration (the largest narrowed population),
  the whole-vs-half rest, or the unboxed ink?
- **Q4.** What ink is noise? Is there a size below which a speck is never a
  mark? Is ink lying on a staff line's y, thinner than a line, always staff
  residue? (These are the conventions `ink_kind` would DECIDE on. Anything
  not stated here, it can only narrow.)
- **Q5.** How many answers per family before a calibration table counts?
  Set it before anyone looks.
- **Q6.** Auto-accept (6.8): ever? If so, how reliable must a family be, on
  answers it was not fitted to, before INFER may choose for you?
- **Q7.** Does the manager run 6.1 + 6.2 as the first Phase 6 lane when the
  current session breaks, or after the in-flight Phase 2 merges?

---

## 9. What this plan does not do

- **No code, no flag, no benchmark directory yet.** 6.5 authorises one when
  it is dispatched.
- **It does not invert the record's subject tree** (the ink as the subject
  and boxes as rows on it: shape-role FINDINGS §(c), a multi-week lane). 6.3
  and 6.4 get most of its benefit without the inversion. Revisit it after
  6.3 re-measures how many ink components carry more than one opinion.
- **No joint probabilistic model of the whole page.** 6.7's
  most-certain-first order is the bounded form.
- **No detector training.** The opinions come from the existing
  checkpoints.
