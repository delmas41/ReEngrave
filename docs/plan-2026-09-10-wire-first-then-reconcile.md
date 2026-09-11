# Plan — wire everything first, then measure cleanup, then reconcile

**Sean's calls, 2026-09-10, both of them changes of TARGET rather than next
steps.** Written down before anything is built toward them.

---

## 1. THE TARGET CHANGES: a cleanup count on one real movement

The metric was retired on 2026-09-08 (*"the numbers dont feel like they have
represented much that has been helpful"*) because OMR-NED compares two FILES AT
THE FAR END and can never say which decision went wrong. The staged pipeline
replaced it as the organising goal — but **a pipeline is an architecture, not a
finish line**, and nothing replaced the metric as a way of knowing when to stop.
Grepped for before being asserted: there is no stated success criterion in
`CLAUDE.md`, `PROJECT_STATUS.md`, `PROJECT_BRIEF.md` or `NOTES.md`.

**The new target, in Sean's words: *"how much work would I have to do to clean
it up."*** Take one real scanned orchestral movement end to end, put the output
beside the print, and count what a human would have to fix.

⚠️ It is not a replacement metric and must not be used as one. It is a
RANKING instrument: it sorts the remaining work by what actually costs the
human, rather than by what is cheapest to build next.

---

## 2. WHY THAT FORCES WIRING-FIRST — Sean's question, and the answer

> *"Would it make more sense to wire up all of the decisions first and then go
> back and fix each one? ... we might be wasting time."*

**Yes, and the target above is the decisive argument.** A cleanup count taken
while whole families are absent from the file measures the WIRING, not the
READING: it would be dominated by things that are not there at all, and it
would move every time a family got connected regardless of its quality.

The supporting evidence is this project's own history, and it is not thin:

* **The dominant bug class is discovered BY wiring, not by fixing.** *The value
  existed and nothing read it* has now been found ten or more times. `Q.STEM`
  was gathered and read by nothing while the decision that needed it called its
  own input fragile. `Q.METER`'s segments reached no file. `arc_kind` decided
  199 arcs a page with `grep '<slur'` returning zero.
* **A fix can be BLOCKED by something unwired.** `arc_owner`'s remaining
  quality depends on voices, and voices do not exist on this path at all
  (§4). No amount of effort on arcs finishes that today.
* **A quantity can need a frame that only arrives when something else asks for
  it.** `Q.CELL_BOX` was gathered and discarded until the arc merge needed it;
  page pixels were added to the glyph rows only when a cross-staff question was
  finally asked.
* **Tuning against one document gets overturned by the second.** Measured
  repeatedly here — the spans regression, the meter carry, and on 2026-09-10
  the slur pad constant, whose engraved plateau does not exist on a scan.
  Wiring first accumulates documents' worth of evidence BEFORE anything is
  tuned.

### 2b. ⚠️ THE CONDITION THAT MAKES IT SAFE

**A wiring pass may connect a decision. It may not let one GUESS.**

A crudely wired decision that ABSTAINS is honest and costs nothing — it appears
in the cleanup count as a gap and is fixed later. A crudely wired decision that
guesses puts wrong music in the file and looks confident doing it, and the
cleanup count cannot tell the two apart. `Ruling`'s contract already says this;
a wiring pass is where it is most tempting to break.

So the discipline is: **connect it, let it abstain freely, do not tune.** Every
quality question is deferred to §5.

---

## 3. THE WIRING LIST — derived, not remembered

From `gather_coverage`, `inventory`, `health` and two real records
(Litolff `984073` p1-3, Breitkopf Brahms 1 p0-3), 2026-09-10. ⚠️ **Re-run the
tools rather than quoting this table** — a hand-counted figure in this repo has
rotted at least three times.

### Reach, by detector CLASS

⚠️ **By class, never by the detector's `category`.** All ten `artic*` classes
carry category `ornament`; counting by category reports 300 "ornaments" on a
page holding none. `gather_glyph_families` is routed by class for this reason
and the first draft of this table was wrong in exactly that way.

| family | Litolff p1-3 | Brahms p0-3 | state |
|---|--:|--:|---|
| **fermata** | **63** | 0 | NO QUANTITY |
| articulation | 24 | 196 | ✅ wired 2026-09-10 |
| **wedge** (hairpin) | **0** | **47** | stub, input fed |
| ornament (trill/turn/mordent) | 0 | 7 | NO QUANTITY |
| tremolo | 0 | 0 | detector fires none |
| arpeggiato | 212 | 214 | ⚠️ MISREADS, not a family |
| accidental | 155 | 733 | deliberately not its own quantity |
| direction (words) | — | — | stub, input STARVED |
| voices / voice_index | — | — | NO QUANTITY, derived not detected |
| stem_direction | — | — | NO QUANTITY, derived |
| tied_to_next / _from_prev | — | — | NO QUANTITY, the tie CHAIN |

### What that re-ranks

* **`fermata` is the only unwired family with large reach**, and it is on the
  document already in hand. `_mxl_note` takes `fermata=` already, so the
  emission half is free.
* **`wedge_anchor` has ZERO reach on Litolff.** Measuring it there would have
  produced a clean zero meaning nothing about the rule. Brahms is its only
  fixture.
* **`tremolo` gains nothing from wiring** — the detector produces none, which
  `export_coverage.KNOWN_GAPS` already records as a DETECTION problem.
* **`arpeggiato` is not a wiring item.** 212 and 214 boxes at confidence
  0.35-0.39, median 56x388 px — stems and barlines, already recorded as a
  misread. Wiring it would export ninety arpeggios a page.
* **`voices` is the one with a partial order in front of it.** MusicXML pairs
  `<slur>` WITHIN a `<voice>`, so `arc_owner`'s quality and the two-note rule's
  one-voice half both depend on it. The staged export passes an EMPTY voice map
  today, which is consistent (no voices in the file) and makes that half of the
  rule inert.

### Suggested wiring order

1. **`fermata`** — large reach, renderer free, no dependencies.
2. **`voices` / `stem_direction`** — blocks others; do it before arc quality.
3. **`wedge_anchor`** — needs a renderer AND the arc merge; Brahms only.
4. **`ornament`** — same shape as fermata, much smaller reach.
5. **`tied_to_next` / `_from_prev`** — the tie CHAIN as a quantity, distinct
   from one arc.
6. **`direction`** — two jobs, not one: `Q.DIRECTION_WORD` is the last starved
   input on the record.

Then **stop, and take the first cleanup count.**

---

## 4. ⚠️ WHAT IS *NOT* ON THIS LIST, AND WHY

`A-DUR-5`, unclassified ink as a first-class gathered fact, is Sean's standing
request and is NOT a wiring item in this sense — it needs a RASTER pass in
GATHER, which is new capability rather than a connection. It stays ranked on
its own merits.

`METER_CARRY_FLOOR` / `METER_FROM_BARS_FLOOR` are **untouched by this plan**.
`A-DUR-8` §5.2 asks a human whether better bar sums re-open them; three
sessions have now declined to answer it, deliberately.

---

---

## 5-PRE. THE FIVE STAGES, AND WHAT EACH IS ALLOWED TO DO

⚠️ **Sean, 2026-09-10: *"I thought evaluate had more of that (infer) built into
how it evaluated."*** It nearly does, and the line is sharper than it looks.
Traced through ONE REAL NOTE from the committed Litolff record —
`glyph/1/0/2/4/1`, page 1, staff 2, cell 4 — rather than an invented example.

### GATHER — write down what is on the page. Decide NOTHING.

```
glyph_box               = noteheadHalfInSpace at (136,694) 147x150   conf 0.299
notehead_class          = noteheadHalfInSpace                        conf 0.299
notehead_staff_position = 7.38                        (geometry, NO confidence)
```

Four rows, two readers. ⚠️ The position carries no confidence **because it is a
ruler reading, not a guess** — the distinction GATHER exists to preserve.
Nothing here is a conclusion, not even *"this is a note"*.

### ADJUDICATE — one question, one answer, and the evidence for it

```
duration = {beats: 1.0, written: 1.0, dots: 0, beam_levels: 1}   "head_and_marks"
  detail : head=noteheadHalfInSpace, cv_beams=1, stems_attached=2,
           beams_by_stem=1, flags_attached=0, dots_attached=0, levels_certain=1
  missing: aug_dot, flag, rest, tuplet_ratio
```

**It read a QUARTER where the detector said HALF** — a beam is attached to the
stem and a beamed note cannot be a half note, so the evidence beat the class
name. ⚠️ Note `missing`: what it looked for and did NOT find is recorded, which
is what makes the verdict arguable later.

### EVALUATE — consequences, but ONLY where the answer is FORCED

```
pitch    = F4                     restate_pitch      basis: [position, clef]
duration = {beats: 2.0, reconciled: True}  reconcile_duration  supersedes: vrd:025258
```

Two different characters in one stage. `restate_pitch` is **entailment**:
position 7.38 under the settled clef IS F4. `reconcile_duration` is the one
that looks like judgement — the meter settled, the bar did not sum, so the note
was re-read and **corrected back to 2.0, the half note the detector called at
0.299 in the first place.** ADJUDICATE was wrong and EVALUATE fixed it.

⚠️⚠️ **AND IT IS STILL NOT INFERENCE, BECAUSE OF ONE WORD IN ITS OWN RULE:**

> *"where more than one re-reading lands the bar exactly, NOTHING changes and
> the warning stands."*

Had two lengths both fixed the bar, it would have done nothing. **EVALUATE acts
where the answer is FORCED and goes silent where it is merely LIKELY.** That is
deduction under constraint, not judgement — and it is the property that stops
the repair laundering a guess.

⚠️ **Note also what it CANNOT reach.** That bar sits in a system with eleven
other staves playing the same stretch of time, and **no consequence in EVALUATE
looks sideways at them.** Every one is vertical: `cause -> effect`, from a
settled decision down to what depends on it.

### INFER (proposed) — what is most likely, given everything at once

Same note, one detail changed: suppose TWO re-readings had both fixed the bar.
Today nothing happens, the note stays a quarter, the bar stays wrong, and a
warning nobody reads is filed. **INFER begins exactly there**, and it has what
EVALUATE structurally cannot touch: the other eleven staves' readings of the
same bar, the SUPERSEDED verdict still in the record with its working, the
0.299 the exporter treats as identical to 0.98, and how crowded the bar is
(which says what agreement is worth). It writes its answer **labelled as
inferred, with its basis.**

### EXPORT — write the file, and count what did not reach it

### The table

| stage | the question it answers | acts when |
|---|---|---|
| **GATHER** | what is on the page? | always — it decides nothing |
| **ADJUDICATE** | what does this ONE thing mean, and on what evidence? | it can read it; else abstains |
| **EVALUATE** | what follows NECESSARILY from what we now know? | the answer is **forced** |
| **INFER** | what is most LIKELY, given everything at once? | the answer is **best** |
| **EXPORT** | write it, and count what did not make it | always |

⚠️ **THE TESTABLE FORM OF THE BOUNDARY, and it is assertable:** *no EVALUATE
consequence may contain a tie-break.* One exists today (`reconcile_duration`'s
uniqueness test) and it refuses rather than choosing. If a consequence ever
starts choosing, the stage boundary has moved and nobody will have noticed.

⚠️ **WHY IT IS A SEPARATE STAGE AND NOT A WIDENED `EVALUATE`.** The
"only when forced" rule is LOAD-BEARING — its own docstring calls it what
"stops the repair laundering a guess". Keeping the stages apart is what keeps a
property SAYABLE:

> Everything in the record before EXPORT was **read** or **entailed**.
> Everything after INFER was read, entailed, or **inferred — and labelled**.

**The boundary between the stages is exactly where the guarantee changes**,
which is the right place for one.

⚠️ **NAMING.** `reconcile_duration` is already a consequence INSIDE EVALUATE,
so "RECONCILE" puts one word on both sides of the line it draws. **INFER** is
used below. Sean, 2026-09-10: *"I don't care what it is called."* — so the name
is this document's, and the distinction is the part that matters.

---

## 5. THE FOURTH STAGE — Sean's design, and what already feeds it

> *"a 4th stage or some form of back end on the adjudication stage that starts
> to determine what is more reliable data ... there may be a place for
> 'guessing' — probable outcomes based on all the info — that would never be
> what we want to do at the gather or adjudication stage. There may be places
> where we don't need much info from a particular symbol because we have what
> we need elsewhere ... There will always be certain things that are impossible
> to determine on their own."*

**This reflects the structure closely, and the pipeline has been ACCUMULATING
its inputs while deliberately refusing to spend them.** Working name: **INFER**
(see 5-PRE for why not RECONCILE), after EVALUATE and before EXPORT — it needs settled decisions
AND their consequences before it can weigh anything.

### 5a. What is already saved for it

| already built | and consumed by |
|---|---|
| `Ruling.narrow` — *"it is one of these"*,each candidate carrying its `support` | **nothing.** 174 narrowed durations on one page; the exporter reaches them and REFUSES to argmax, saying so in a comment |
| `Verdict.correlated` — which evidence was ENTANGLED, not merely used | nothing yet |
| the groups layer — `clef_across_systems`, `meter_across_staves`, with `unanimous` / `majority` / `split` | reported, not read |
| `Q.ONSET_COLUMN` — cross-staff simultaneity, 1,483 real instants against 2,409 in a phase-shuffled null | **nothing.** Its own findings name the first consumer and it was never built |
| `Checkable` — whether a decision can be proved against itself with no truth file | declared per decision |

⚠️ **The exporter's refusal to argmax is CORRECT and must stay.** An exporter
that quietly collapses a narrowed verdict overturns, silently and downstream, a
call the reader explicitly declined to make. RECONCILE is the stage that is
ALLOWED to collapse it, because it does so visibly, with a recorded basis, and
after weighing everything the record holds.

### 5b. The efficiency argument is the real prize

Sean's *"we may not need much info from a particular symbol because we have
what we need elsewhere"* is the strongest claim here. A conductor's page is
twenty-odd INDEPENDENT readings of one stretch of time, and today each staff is
read in near-isolation and the redundancy is discarded. If thirteen staves
agree a bar holds three beats, the fourteenth does not need to be READ — it
needs to be checked for DISAGREEMENT.

That reframes *"impossible to determine on its own"* from a defeat into a
ROUTING decision: some symbols only ever need to be CONSISTENT, not read.

### 5c. ⚠️⚠️ TWO HAZARDS, BOTH ALREADY PAID FOR HERE

**1. An uncalibrated probability is WORSE than none.** Measured: calibrated
identity probabilities reached ECE 0.1277 and failed worst at the top of the
range — the top bin promising 0.989 and delivering 0.692. The standard adopted
then, and it governs this stage: *a probability that is not earned launders a
guess into something that reads as evidence.*
✅ **The escape is already named**: that failure was diagnosed as the CORPUS,
and a bar sum is `Checkable.CHECKABLE` — provable against its own meter with no
truth file — so the self-checkable families can be genuinely calibrated from
the score library alone. **Nothing does that yet, and it is the first piece of
RECONCILE worth building.**

**2. Two readers can fall silent TOGETHER.** *The bars are not an independent
umpire over a bad reading*: a page whose meter the reader mangles is a page
whose ink is degraded, and the same degradation stops its bars from summing.
The same shape was found independently in `arc_kind`'s position grammar. So
**the case that most needs an arbiter is the case where the arbiter is
silent**, and a stage that counts two correlated witnesses as two is
double-counting one.
✅ `Verdict.correlated` and `source_kind` exist for exactly this. An arbiter
carrying `source_kind: "page"` is an OMR output of the same raster and fails
together with what it arbitrates; the catalog tier does not.

### 5d. What RECONCILE must NOT do

* It may not run before EVALUATE — it needs consequences settled.
* It may not let its existence loosen GATHER or ADJUDICATE. **The whole design
  rests on the earlier stages still refusing to guess**, so that this stage can
  always tell *"nobody could read this"* from *"this was read and it is
  wrong."* Destroy that distinction upstream and RECONCILE is unbuildable.
* It may not be built before the first cleanup count. **The count is what says
  which abstentions are worth resolving by inference** — building it first
  would be guessing at that in advance, which is the thing this plan exists to
  stop.

---

## 6. THE PLAN OF ATTACK — refined

### The goal, stated so it can be checked

> **One real scanned orchestral movement, end to end. Put the output beside the
> print. Count what a human would have to fix.**

⚠️ It is a RANKING instrument, not a metric to optimise. The moment it becomes
a number to drive down, it will be gamed the way OMR-NED was — that metric
rewards emitting MORE symbols, and a cleanup count rewards emitting FEWER.
**Both failure modes are real and they point opposite ways**, which is why the
count is read as *"what should we fix next"* and never as *"are we winning".*

### Phase 1 — WIRE (no tuning, abstain freely)

In order, because a few block others:

1. ✅ **`fermata`** — **CLOSED 2026-09-10** (`0982864e`). 63 marks → 51
   decided → **37 `<fermata>`**, byte-identical outside them. ⚠️ 26 of 51
   carriers are RESTS, the `nearest_in_bar` fallback fired ZERO times, and the
   13 "absorbed" marks are duplicate DETECTIONS rather than chords.
2. ✅ **`voices` / `stem_direction`** — **CLOSED 2026-09-10** (`eb87d300`).
   Three rules were inert, not missing; the divisi guard now RUNS and one tie
   span is refused. ⚠️ The accounting control RAISED and was right: two
   grouping rules nothing forces to agree wrote 17 notes twice.
3. **`wedge_anchor`** — Brahms only (47 there, **0** on Litolff). ⚠️ **THIS
   LINE WAS WRONG AND IS CORRECTED IN PLACE, checked against the tree:**
   `export._mxl_wedge` IS a reusable renderer, and the arc merge is NOT needed
   — 46 of 47 `Q.WEDGE_BOX` rows are `cv_hairpins` carrying page pixels from a
   reader that searches one staff BAND across the whole page, so its hairpins
   are never cut by a barline. What is open is a STAGE-BOUNDARY question: the
   legacy anchor rule wants the exporter's `measures` shims and three measured
   constants. See `handoff-2026-09-10-three-families-wired.md` §6.
4. ✅ **`ornament`** — **CLOSED 2026-09-10** (`830bfccb`). ⚠️ It closes the
   QUANTITY and closes **no detection gap**: the detector fires ZERO
   `tremolo1`-`5` over 34,115 detections.
5. **`tied_to_next` / `_from_prev`** — the tie CHAIN, distinct from one arc,
   and the last two entries in `NO_VOCABULARY`. ⚠️ The exporter ALREADY sets
   both flags from `_pair_arcs`; what is missing is a quantity NAMING the
   chain, so this is *the record catching up with the exporter* — the opposite
   direction from every other item on this list.
6. **`direction`** — two jobs: `Q.DIRECTION_WORD` is the last starved input.

**Exit condition:** `gather_coverage` reports no family that the detector reads
and the record cannot name, except those with a WRITTEN reason (`arpeggiato` —
212 misread stems; `accidental` — scope, not a mark). ⚠️ **`tremolo` has left
that list of exceptions and is now NAMED** (`Q.ORNAMENT_MARK`) — the detector
still fires none, so naming it changed nothing on any page, which is exactly
the distinction the exit condition has to keep: *the record can express it* is
not *the page supplies it*.

**Progress, 2026-09-10:** `NO_VOCABULARY` **7 → 2**, and **no family in
`FAMILIES` is quantity-less** (asserted derivedly, so the next regression is
loud).

### Phase 2 — COUNT

One movement, one human pass, categories fixed in advance:
**missing** / **wrong** / **spurious** / **would-not-notice**. ⚠️ Fix those
categories BEFORE looking, or the count fits itself to what was found.

### Phase 3 — FIX, ranked by the count

Not by cheapness, which is what ranked the work until now.

### Phase 4 — INFER, for the abstentions the count says are worth it

⚠️ **Not before Phase 2.** The count is what says which abstentions matter;
building first would be guessing at that in advance, which is the thing this
plan exists to stop. ⚠️ **The first piece is calibration from the score
library** — a bar sum is `Checkable.CHECKABLE` and can be proved against its own
meter with no truth file, which is the escape from the ECE 0.1277 failure.

### What is NOT in any phase

* `METER_CARRY_FLOOR` / `METER_FROM_BARS_FLOOR` — `A-DUR-8` §5.2 asks a HUMAN.
  Three sessions have declined to answer. **Do not tune them as a side effect.**
* `A-DUR-5` unclassified ink — Sean's standing request, but it is new
  CAPABILITY (a raster pass in GATHER), not a connection. Ranked separately.
* The scan-side meter READING — blocked on a corpus, not on code.
