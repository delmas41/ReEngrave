# The target architecture, and how to get there one decision at a time

**Commissioned by Sean, 2026-09-07:**

> *"The real work right now is the big picture pipeline with stages and how we
> determine what something is."*

> *"There may be a single order of gathering the info, but then all the info
> needs to flow in any direction once it is gathered. The human brain does this
> naturally — it gathers all the info and uses what it needs to make a
> particular decision."*

**This document is the TARGET and the MIGRATION.** The diagnosis is finished and
lives in three documents on `main` — `docs/architecture-decision-map.md`
(what every decision sees and who reads it),
`docs/pipeline-gather-then-adjudicate-2026-09-07.md` (which orderings are real),
`docs/scope-part-correspondence-2026-09-07.md` (scope and witnesses) — and
⚠️ **`benchmarks/omr-partition-truth-2026-09/FINDINGS.md`, the pre-registered
gate that falsified the third document's one recommendation** and, in the first
draft, this document's step 1. **They are input here and are not re-derived.**
There is no new census below.

⚠️ **No pipeline code was changed.** One read-only probe over stored artefacts:
`benchmarks/omr-target-architecture-2026-09/probe_clef_double_read.py`.

⚠️ **Every line number below was verified against this tree at `6ec22487`**,
not inherited — the map is stamped `e1107b5b` and several of its anchors have
drifted by hundreds of lines. Where a quoted anchor differs from a standing
document's, the difference is noted.

⚠️ **The target needs no new model, no new corpus, and no rewrite.** It is not a
blackboard, a scheduler, or a rules engine — the page/staff/measure dicts are
already the shared record. Every step below is flag-guarded, byte-identical with
the flag off, and independently revertible. **Nothing here is all-at-once.**

---

# Part 1 · The target

## In one sentence

> **Every reader keeps its MEASUREMENT on the record. Every decision is moved to
> a phase where the whole record is available, declares which measurements it
> wants, and records what it saw — including when it abstained.**

Not "re-order the pipeline". The pipeline's acquisition order is nearly right.
What is wrong is that **interpretation happens at the moment of measurement and
destroys it**, so a decision that later needs the measurement finds only
somebody's conclusion.

`pitch_resolver.py:180-181` is the whole thesis in two lines: a notehead's
fractional staff position is computed, rounded, and the fraction is gone. The
position is a *measurement* — geometry against this staff's own lines. The pitch
is an *interpretation* — it required a clef. We keep the interpretation and
throw away the measurement, and then every later decision that would like to
reconsider the clef has nothing clef-free to reconsider it with.

## The two phases

**Phase G — GATHER.** Produces *measurements*. A measurement is a quantity read
off the raster that does not require any other reading to be true. Its shape:

```
what was measured · the value · the reader · the crop/frame it was read in · its score
```

It is never a name. `pos_float = 5.47`, not `E4`. `symmetry = 0.886, clef=alto,
crop=header`, not `this staff is alto`. `"Tr. Alt."`, not `Trombone`. Ink
overlap with two staff bands plus the ladder rungs between, not *this staff owns
the glyph*.

**Phase A — ADJUDICATE.** Produces *named facts*. A decision is a pure function
of the gathered record plus earlier-adjudicated facts. It reads no raster. It
returns a value **and** a record: what it considered, what won, by how much, and
if it declined, why.

## The payoff, and it is arithmetic

`docs/pipeline-gather-then-adjudicate-2026-09-07.md` §1.1 names **five** hard
edges. Under the split, **three of the five are hard only for interpretation**:

| edge | hard for GATHERING? |
|---|---|
| page geometry (staves → systems → barlines → cells) → every reader | ✅ **yes** — nothing has coordinates before it |
| detections → direction text (it subtracts every detection from the ink) | ✅ **yes** — the crop cannot be made first |
| clef → key signature | ❌ the accidental RUN's positions are measurable with no clef; only choosing the slot table needs one |
| clef → pitch | ❌ the notehead's staff POSITION is measurable with no clef |
| duration → meter vote | ❌ beam strokes, dots and notehead classes are measurable with no meter |

**Gathering has two hard edges. The other three are adjudication-order
constraints, and those are free** — adjudication reads a frozen record, so the
order in which decisions run inside Phase A costs nothing and can differ per
fact. That is Sean's *"all the info needs to flow in any direction once it is
gathered"*, made safe rather than merely permitted (Part 5).

## How a decision declares what it wants — no framework required

A decision is a function whose signature names the gathered keys it reads, and
which returns `(value, record)`. The declaration IS the signature; the audit IS
the record. `key_signature_corroboration` already has exactly this shape.

## This is a generalisation, not an invention

Four places already hold gathered facts in the target's shape, and the fourth
proves the pattern:

| substrate | what it holds | adjudicator |
|---|---|---|
| `pitch_candidates` | every alternate pitch + weight, **100% of noteheads** | none in production |
| `clef_evidence["contest"]` | candidates, winner, runner-up, margin, clef before/after | none |
| `contested_notehead_pairs` | both confidences and the deciding tier, per contest | none |
| **key-signature vote evidence** | per-staff tally, majority share, source | ✅ **`key_signature_corroboration`, default-ON 2026-09-07** |

⚠️ **And the correction that this document exists to make.** The obvious reading
of that table — *"the other three need consumers"* — is what the last four
documents concluded, and it is why each collapsed into a point fix. It happened
again this week, in full: the gather-then-adjudicate document's single
recommendation was *"give `clef_evidence["contest"]` its consumer"*; the reach
gate was measured (`benchmarks/omr-clef-contest-reach-2026-09/`), it **cleared**
— 22 overturns / 396 staves, 14 label-gated, 3 documents — and the finding was
*"the consumer already exists, is disabled, and its coverage table is two rows
long."* **The work reduced to flipping a flag and adding table rows.**

That is not bad luck. **One bespoke consumer for one orphan record is a point
fix by construction**: it creates one coupling and leaves the next orphan
costing exactly as much. The target is not three consumers. It is one *shape* —
measurement kept, decision moved, record written, abstention visible — adopted
one decision at a time, so that the N+1th decision reuses the Nth's plumbing.

**The migration test in Part 4 is precisely this: after a step lands, is the
next step cheaper?** A step that fails that test is a point fix however good its
number is.

## The first step, so it is on this page

**Move brace grouping out of the exporter.** `export.py:3523` and `:681` both
decide it with `len(staves) == 2`, while `group_index` — the page's own
statement of family grouping, read off the raster by `staff_detector` with no
lexicon and no template — sits on the staff dict with **no reader in
`export.py`**. It is a MEASUREMENT, which is what a migration toward *"keep the
measurement, move the decision"* should move first. And because bracket blocks
are **precise but under-recalled** (22/22 precise, 22/39 recalled), the
absent-fact case is common rather than hypothetical — so the discipline the step
exists to install gets exercised on the first try.

**Then the cheapness test:** part boundaries, `export._stitch_slots`
(`:3218`) deciding what a `<part>` IS from staff ordinal alone while
`slot_index` sits on the same dict. Same era, same file, same transport — but
`slot_index` is an ADJUDICATED fact, so it must arrive with its provenance and
the consumer must gate on it. **If step 2 is not nearly free, step 1 was a point
fix and this document is wrong.**

⚠️ **Steps 1 and 2 were the other way round in the first draft of this document,
and the swap is a correction, not a preference** — see Part 4, which has the
falsifier that forced it and why the target's own principle predicts the new
order.

---

# Part 2 · Score the measurement, not the interpretation

Sean's mechanism:

> *"If it gathers notes and clefs and the clefs are 40% correct but the notes
> are 90% correct, we could use the correct notes to help find the correct
> clef."*

⚠️ **The correction that makes it non-circular is already established and must
be carried:** a *pitch* is derived from the clef, so "the notes are 90% right"
is not independent of the clef. **A notehead's STAFF POSITION is.** Score
positions, never pitches.

## What is genuinely interpretation-free here

Each is a quantity whose only ancestor is the raster and the page geometry.

| measurement | where it is computed | kept today? |
|---|---|---|
| notehead **staff position** (`pos_float`) | `pitch_resolver.py:180` | ❌ rounded away at `:181` |
| detector glyph class + confidence | `_detections_for_cell` | ✅ on the dict; ❌ never reaches `export.py` |
| beam stroke count, stem length | `line_detection` | partly |
| **accidental-run positions** in the header window | `key_signature_locator` | ❌ `.boxes` reaches nobody |
| clef-locator **symmetry** and located line | `clef_locator` | ✅ since the refusal-recording work |
| margin-label **string**, before lexicon lookup | the three readers | ✅ |
| barline column ink, staff-line geometry | `measure_extractor`, `staff_detector` | ✅ |
| glyph-to-staff band distance + ladder rungs | `_dedupe_cross_staff_detections` | partly (`contested_notehead_pairs`) |

## What LOOKS independent and is not — the list to check against

| pair | why it is one signal, not two |
|---|---|
| pitch ↔ clef | the pitch was computed **from** the clef |
| key signature ↔ clef | the slot table is **chosen by** the clef, so an agreeing key is not corroboration |
| duration ↔ meter | the meter is voted **out of** the durations (`_reconcile_measure_to_meter` is bounded ±1 for exactly this reason) |
| instrument name ↔ score-order prior | a `score_order_ambiguity` name is the prior's own output |
| **the header pre-pass clef ↔ the measure-pass clef** | ⚠️ **MEASURED BELOW: the same call on the same object.** Not two readings at all where it matters |

## The reformulation Sean's mechanism actually licenses

> For each candidate clef, a staff's noteheads give a distribution of staff
> positions — clef-free. An instrument's written range is a distribution of
> staff positions *once a clef is assumed*. So score the CLEF by which
> hypothesis puts this staff's own positions inside the range of the
> instrument its labels / roster / layout propose.

This is close to what `clef_correction` already does, with **one input changed**:
`clef_correction` reasons from *resolved pitches* (`clef_diatonic_shift`
restates them) — the interpretation — which is why it is entangled with the
provenance refusals and why its FILL tier reaches 34 of 396 staves. Reasoning
from positions is the same algorithm on a clef-free input, and it can be scored
against several candidate instruments at once without committing to one.

⚠️ **Not a claim that it works.** The register→clef arrow is **measured weak in
one form**: `clef_register_warning` compares ADJACENT staves, reach 7/193,
precision **0 of 11** — and an orchestral score is ordered by family, not by
register, so that form was always going to fail. Comparing a staff against
**its own** positions under different clef hypotheses is one of the two variants
`docs/architecture-decision-map.md` §9.4 leaves explicitly open, and under
standing rule A00 a worse score in one form does not condemn the mechanism.
**Its reach must be measured before its accuracy** — that is Part 4's third
step, deliberately third.

⚠️ **Do not re-propose the refuted edges**: deduced identity → clef
(`clef_correction.py:566` — the map's `:396` has drifted), clef → the part↔staff
pin (`dossier.py:434`, `score_layouts.py:682`), detection confidence as the ownership tie-break
(P = 0.545 against a 0.500 null, would overturn 45.5% of contests).

---

# Part 3 · Internal agreement as the runtime signal

There is no truth at runtime, so reliability must come from **agreement between
things computed independently**. Two questions, in this order: does the signal
have REACH, and is it really independent.

## Reach first — and most of the existing checks are silent

| check | fires (scan 193 staves / engraved 224) | usable as a signal? |
|---|--:|---|
| `rhythm_sum_warning` | 111 / 12 | ✅ volume — and it is the one check with **no confidence field at all** |
| `time_signature_disagreement` | 17 / 1 | ~ moderate |
| `clef_register_warning` | 7 / 4 | ❌ fires, and is **wrong** (precision 0/11) |
| `key_signature_warning` | 0 / 3 | ❌ |
| `measure_count_warning` | **0 / 0** | ❌ **a check that never fires cannot order anything** |

**One high-volume check and one moderate one is not a reliability model.** So
the honest position is: new agreement measures have to exist, and the first
question about any of them is reach.

## The obvious unbuilt one, measured — and it is a correction

`docs/architecture-decision-map.md` §3.2(b) records that the header clef is read
twice and the readings never compared, calls the comparison **free**, and marks
it UNMEASURED. Measured now, over the 20-row scan gate (396 staves, 20 pages,
5 documents), from the artefacts the clef-contest reach arm already produced:

```
A · do the two DETECTOR rungs fall silent on the same staves?
    both spoke                          304
    both silent                          92
    DIVERGENT (one silent, one not)       0
```

**The two readings are not independent.** Statically: the pre-pass rung is
`_clef_from_dets(_header_detections(detector, start_cells[0], …))` and the
measure rung is the argmax inside `_detections_for_cell(detector,
staff_cells[0], …)`. `start_cells` and `staff_cells` are both
`systems[sys_idx][staff_idx]` — **the same list object** — the four detector
parameters are the same, the clef subset is untouched between them
(`_drop_clipped_notehead_fragments` filters noteheads only), and both take a
strict-greater argmax over the same list in the same order. The only permitted
divergence is the octave suffix, which the pre-pass does not apply. The
396/396 coincidence is the empirical confirmation, and incidentally evidence
that the detector is deterministic within a run.

**So the "free agreement signal" would return agreement on 304 of 396 staves for
a reason that carries no information.** Comparing them as the map proposed would
have produced a healthy-looking 77% agreement rate that means nothing.

⚠️ **But there IS a substrate, and it is not the one that was named.** On the 92
staves where the detector was silent, the CV locator genuinely runs **twice on
two different crops** — the header window in the pre-pass, the measure cell in
the measure pass — and there:

```
B · header crop vs measure cell, over the 92
    same verdict                         78   (of which BOTH FOUND NOTHING: 72)
    both located a clef                   6
    DIFFERENT verdict                    14
      header=alto  measure=None          12
      header=tenor measure=None           1
      header=None  measure=alto           1
    final clef CONTRADICTS the located one  5 of 14
```

**13 of the 14 divergences run one way: the header crop read a C clef the
measure cell could not**, at symmetry 0.78–0.97, with the measure cell refusing
for `occupied` / `too_big` / `no_clusters` — too much other ink. On **5 of the
14** the staff's final clef contradicts the located one (`alto → treble`,
`alto → bass`, `tenor → bass`), which is exactly the documented ceiling: C clefs
read as treble or bass.

⚠️ **And this reframes the fix away from "compare the two clefs".**
`_header_cell_beats_measure_cell` is a boolean gate choosing ONE crop for the
locator to read — and on **14 of 14** divergent staves it chose the measure
cell, the crop the reader could not read, while the other crop had already been
read and thrown away in the same run. That is a Class-A gate over two
measurements the pipeline already has. It is a *crop-choice* defect, not a
reader-independence one.

⚠️ **This is REACH ONLY. No page was hand-read.** 5 contradicted staves is an
upper bound on defects, not a defect count — precisely as the clef-contest reach
gate found 14 reachable overturns of which roughly half were ordinary
engraving. Bach supplies 6 of the 14 and Beethoven's two Litolff scans are one
plate, so n is nearer 4 documents than 20 rows.

## The rule for using agreement

⚠️ **An uncalibrated probability is worse than none** — measured here
(P(name) ECE 0.1277, top bin promising 0.989 and delivering 0.692). So an
agreement signal may **order**, never **weight**:

- order which reading a decision tries first;
- break a tie among candidates that are otherwise equal;
- order which staves a human is shown;
- and the one that is not ordering but is still not weighting — **make a
  decision ABSTAIN and say so**, rather than proceeding silently on contested
  evidence.

**Nothing here becomes a multiplier on a score.**

## The new agreement measures that would have to exist

Each is a comparison of two things with **different ancestors**, and each needs
its reach measured before its accuracy:

1. **the same reader on two crops** — the clef case above, and the same shape is
   available for the key signature (header window vs measure cell) and the meter;
2. **the same fact at two scopes** — a staff's reading against its own reading
   on other systems. This is `clef_continuity`'s mechanism, and it is the one
   carry that survives (the other three are dead), so the machinery exists;
3. **two readers of the same crop** — the detector and the CV locator both look
   at a clef, and today the locator is silenced by PRESENCE, not by score
   (`transcribe.py:1953`, `if read_clef and locate_c_clefs and clef_source is
   None`): a detector clef at 0.11 permanently mutes it.

---

# Part 4 · The migration

## The test

> **After this step lands, is the NEXT step cheaper?**

A step that only produces a number fails it. So does a step that gives one
orphan record one bespoke consumer. The three steps below each install a piece
of reusable machinery, and step 2 exists specifically to *demonstrate* that
step 1 made it cheaper.

## ⚠️ What is deliberately NOT first — and it contradicts the standing shortlist

`docs/architecture-decision-map.md` §9.5 ranks **"record the refusals"** first:
free, byte-identical, and the prerequisite for deciding everything else. **It
should not be the first step now, and the evidence is this week's.** Recording
is gathering. The refusal-recording work *did* land for the clef, it *did* make
the contest visible — and the hunt for its consumer collapsed into a flag,
because there was nowhere for a new consumer to plug in. **Gathering more
without an adjudication surface produces more orphans**, and there are already
three. Record the refusals *as each decision migrates*, not ahead of all of
them.

## ⚠️ The correction: what the first draft got wrong, and what it proves

The first draft made **part boundaries** step 1, citing `slot_index` as *"set on
193 of 193 staves, measured"* and the claim that on Brahms 1 p.2 *"the slot join
expresses exactly the tacet case the page prints."*

**That claim was falsified by a pre-registered gate the same afternoon, in this
document's own base tree** —
[`benchmarks/omr-partition-truth-2026-09/FINDINGS.md`](../benchmarks/omr-partition-truth-2026-09/FINDINGS.md),
at `482c6104`, an ancestor of `6ec22487`. I did not read it, and the draft was
wrong for it.

| | |
|---|---|
| where ordinal **succeeds** | slot and ordinal both match hand truth **exactly**, 3 distinct documents, 100% per-staff — using the real exporter functions, not a restatement. The prior n=3 agreement claim is *strengthened* |
| where ordinal **refuses** — the only population the change newly touches | `_stitch_slots_by_slot` succeeds and is **wrong on 3 of 27 staves (0.889)**: it fails to continue *"4 Hörner in Es"* across the tacet break and grafts the genuinely-tacet *"2 Trompeten in C"* slot onto the horn's continuation |

⚠️ **`193/193` is COVERAGE, not correctness.** The draft cited it as if it were
evidence the fact is right. The probe it came from counts `len(slots)` and never
which staff landed in which slot, so a 14-slot output that is wrong in three
places and one that is exactly right are indistinguishable to it. **A completeness
figure is not an accuracy figure**, and I used one as the other.

### ⚠️ And the root cause is this document's own Part 5 rule

All four contested staves carry `instrument_source: "score_order"` — **no margin
label was read** — and contextual is already wrong there, calling both
horn-family staves *Trumpet*. `slots.assign_slots` inherits that into
`slot_index`, and the exporter would then have consumed a **deduced** identity as
though it were a read one.

That is the exact edge the codebase refuses in three other places
(`clef_correction.py:566`, `dossier.py:434`, `score_layouts.py:682`). **So the
gate did not falsify the architecture — it exhibited it.** The failure is a
provenance-chain violation, which Part 5 names, and it is worst precisely where
the change would newly matter: a suppressed staff is where the score-order DP has
the fewest anchors, so *the refusing population is largely the population with no
label*.

### The principle that fixes the ordering, and it is not "pick the less-wrong fact"

> **Move MEASUREMENTS before INTERPRETATIONS.** `group_index` is read off the
> raster. `slot_index` is a conclusion whose ancestors include deduced identity.
> A migration whose thesis is *"keep the measurement, move the decision"* should
> prove its transport on a measurement.

The swap is derived from the target, not chosen for convenience — which is the
test any re-ordering here should have to pass.

## Step 1 — move a MEASUREMENT to the site that re-derives it

**Brace / PianoStaff grouping.** `export.py:3523` (MusicXML) and `:681`
(LilyPond) both decide it with `len(staves) == 2`. `group_index` — the bracket
block `staff_detector` assigned, *"the PAGE's own statement of family grouping,
and the only one that needs no lexicon and no template"* — is on the staff dict
and **no reader in `export.py`** touches it. It was emitted specifically because
it had never reached the dict, with a comment saying nothing reads it yet.

**Why this one is first.** It is a gathered fact: its only ancestors are the
raster and the page geometry, so it closes no loop, needs no provenance gate,
and cannot launder a deduced identity. No new measurement, no probability, no
refused edge, no held decision. And it lands in the **export era** — the era with
nine recorded instances of *computed correctly, then re-derived downstream* — so
the plumbing has customers waiting.

**What it installs, and this is the point:** the discipline for a decided fact
travelling from the site that made it to a consumer that used to re-derive it,
**including what happens when it is absent**. That part is load-bearing here
rather than hypothetical: bracket blocks are **precise and under-recalled —
22/22 precise, 22/39 recalled** — so the absent case is roughly *half* the
population. They may ANCHOR a grouping where present and must ABSTAIN where
absent, never assign, falling back to `len(staves) == 2`.

⚠️ **The absent case is exactly what nothing has ever caught.** The three dead
carry dicts (`transcribe.py:4851/4873/4885` read, `:5232-5234` written, same loop
nest, one visit per key) survived because **a dead lookup with a good default is
indistinguishable from a live one that agrees.** A moved fact must arrive, or the
consumer must record that it did not.

**Before any code**: over every stored transcription, count staves where
`group_index` is present and disagrees with `len(staves) == 2`, and how many
systems carry no block at all. That is a read of committed JSON. ⚠️ **Its reach
is UNMEASURED** — if `group_index` never disagrees on any stored page, the step
is byte-identical and installs the transport at zero accuracy cost, which is a
fine outcome for a step whose product is machinery, but it must be *stated* as
that rather than discovered later.

## Step 2 — the cheapness test, and the falsified step done correctly

**Part boundaries.** `export._stitch_slots` (`:3218`) decides what a `<part>` IS
from **staff ordinal and nothing else**, while `slot_index` sits on the same
dict; the stronger join exists (`_stitch_slots_by_slot`, `:3338`) and is
reachable only as a fallback behind `OMR_SLOT_STITCH`, default off.

The fault is still real, and stated the same way: **the exporter trusts
contextual's identity for what to CALL a part (`export.py:3466`, `:3657`) and
refuses it for what a part IS (`:3218`).**

**What changes after the falsifier: the fact must arrive with its provenance,
and the consumer must gate on it.**

| the situation | what the consumer does |
|---|---|
| ordinal **succeeds** | no-op — measured identical to truth and to each other, 3 documents |
| ordinal **refuses** and the slot's identity was **read** (`instrument_source == "label"`) | use the slot join |
| ordinal **refuses** and the identity was **deduced** (`score_order`) | **abstain** — record it and fall back to ordinal |

On Brahms 1 p.2 all four contested staves are `score_order`, so **the measured
3-of-27 error never ships**: that row abstains and behaves exactly as it does
today. ⚠️ Which means the **reach of this step is UNMEASURED and may be zero** —
how many refusing rows carry label-read slots is not known, and Brahms p.2 has
none. **That is its pre-registered gate**, on the same terms the clef-contest
reach gate was run: measure the population before claiming the accuracy.

**Why it is the cheapness test.** Same era, same file, same transport as step 1,
a different fact. The one thing it adds is provenance gating — and that is one
existing field (`instrument_source`) consumed the way four other consumers
already consume it, not a new mechanism. **If step 2 is not nearly free, step 1
was a point fix and the target is wrong.** That is the experiment, and the swap
did not weaken it: step 1 now installs *transport + absent-fact abstention* and
step 2 adds *provenance*, so the increment is still one small dimension.

⚠️ And before it: replay both partitions over every stored transcription under
`OMR_SPAN_REFERENCE_FIT=off`, the arm known to poison the reference. If the slot
partition shatters there, the reference must be hardened first.

## Step 3 — keep the first new measurement, and adjudicate the clef on it

Only now is a new gathered fact worth adding, because there is somewhere for it
to go and a way for its consumer to abstain.

1. **Keep `pos_float`** at `pitch_resolver.py:180` instead of rounding it away at `:181`.
   Byte-identical to the output; it is an added field.
2. **Adjudicate the clef from staff-position distributions** (Part 2's
   reformulation) rather than from resolved pitches — reach measured first, on
   the population `clef_correction`'s FILL tier cannot see by construction:
   staves whose clef was read **wrong**, not staves with no clef.
3. Fold in the crop-choice finding of Part 3: the divergent-crop staves are
   already-computed evidence that a staff's clef is contested.

**Why third.** It needs a new measurement (steps 1 and 2 need none), it aims at
accuracy rather than at machinery, and it is the first step where the
circularity rule actually binds (Part 5).

## Order, restated

| # | decision | the fact being moved | new evidence? | why here |
|--:|---|---|---|---|
| 1 | brace grouping: `group_index` over `len(staves)==2` | **measurement** — page geometry | none | no provenance question can arise; installs transport + absent-fact abstention, and the absent case is ~half the population |
| 2 | part boundaries: `slot_index` over ordinal, **provenance-gated** | **interpretation** — ancestors include deduced identity | none | **the cheapness test**; adds exactly one existing field (`instrument_source`) |
| 3 | clef from staff POSITIONS, not resolved pitches | new measurement (`pos_float`) | yes | first new measurement; aimed at the documented ceiling |

⚠️ **Steps 1 and 2 changed places after
`benchmarks/omr-partition-truth-2026-09/FINDINGS.md`.** The reason is stated
above and is a principle, not a preference: move measurements before
interpretations.

## What is irreversible, and what needs everything at once

**Nothing, and nothing.** Every step is a flag with byte-identical flag-off —
the project's standing acceptance test, already asserted for arcs, reclass,
condensed parts and slot stitch. There is no step that requires the others to
have landed. **The target is fully incremental, and that is the strongest
argument for it**: it can be abandoned after any step with the pipeline in a
working state and the previous steps still paying.

---

# Part 5 · What stops it going circular

## The rule, in one sentence

> **A decision may consume a fact only if that fact's provenance chain does not
> contain the decision's own output; and two facts sharing an ancestor count
> once, not twice.**

This is `docs/scope-identity-upstream-2026-09-06.md` §7's rule, unchanged. What
the gather/adjudicate split adds is why it is cheap to obey: **a gathered fact
has no ancestor but the raster**, so among measurements "flow in any direction"
is unconditionally safe. The rule only ever binds between *adjudicated* facts —
which is a much smaller set, and the one the three standing refusals already
police.

## Are provenance tags a prerequisite?

**For step 1: no — genuinely independent.** `group_index` is produced by
`staff_detector` from page geometry; its only ancestors are the raster and the
staff lines. It closes no loop and there is nothing to tag.

**For step 2: yes — but the tag already exists, so it is a new USE, not a new
field.** ⚠️ This is the answer the first draft got wrong, and the partition-truth
gate is why. `slot_index`'s ancestors include the identity `contextual` assigned,
which on the refusing rows is `score_order` — deduced, not read. Consuming it
unconditionally is the same edge `clef_correction.py:566`, `dossier.py:434` and
`score_layouts.py:682` each refuse. The tag that binds it is `instrument_source`
(1 writer, 4 readers, already load-bearing), and step 2's gate is one more reader
of it. ⚠️ There is a *second*, separate hazard on step 2 that no tag fixes: a
**bad ancestor** — `slots.align` inherits `build_reference`'s single-system pick,
which once named 149 Brahms staves an instrument the work has not got. Its guard
is the `OMR_SPAN_REFERENCE_FIT=off` replay.

**For step 3: yes — prerequisite.** Positions → clef → pitch, and the pitch must
never re-enter. Today the resolved pitch carries **no provenance tag at all**,
and `pos_float` would need one saying it is clef-free. The existing tags are
`instrument_source` (1 writer, 4 readers), `clef_source` (2 writers, 4 readers)
and `time_signature["source"]` (the best-enforced, via
`rhythm._READING_SOURCES`); `key_signature_source` is partial — one positive
value, the rest defaulted. Ownership and pitch carry none, and today that is
moot because neither has a cross-decision consumer. **Step 3 is what stops it
being moot, which is the same sentence as "step 3 is where the tag becomes a
prerequisite."**

⚠️ One filter is not optional and is already named: a clef adjudicator must
exclude `clef_evidence["dossier"]` on a dossier-seeded run, or it reads back its
own seed as corroboration. The scan gate is dossier-free; this bites the
engraved arm.

⚠️ And the regime constraint: all three of the pipeline's existing propagations
are **single-pass**, no `while`, no fixpoint. Every step above stays in that
regime — it changes what a decision READS (evidence frozen at gather time), not
the direction in which it writes. **If a future version re-derives the clef
contest from restated pitches, the edge becomes uphill and a convergence
argument is required. This project has twice declined to build one.**

---

# What is UNMEASURED here

- **Whether acting on any of it improves OMR-NED.** Nothing below Part 3's reach
  figures is an accuracy claim.
- **Whether the 5 contradicted clef staves are wrong.** Reach is an upper bound;
  converting it to a defect count needs a human against the print — the same
  standing that the clef-contest reach gate ended on.
- **Step 1's reach** — how often `group_index` is present AND disagrees with
  `len(staves) == 2` on a stored page. It may be zero, in which case the step is
  byte-identical and buys only machinery. Read-only to settle.
- **Step 2's reach** — how many rows where the ordinal join REFUSES carry
  slots whose identity was **read** rather than deduced. Brahms 1 p.2, the only
  refusing row with hand truth, has **none**, so the reach may be zero. This is
  step 2's pre-registered gate.
- **The refusing population's failure rate in general.** `n = 1` distinct
  document; 1-of-1 failing is not a rate. It is enough to block shipping on the
  stated justification, and no more than that.
- **Step 3's reach** — how many staves have a clef read *wrong* that a
  position-distribution adjudicator could see. Unmeasured, and it is the gate.
- **The net effect of the three dead carry dicts.** Reach is every staff; damage
  is unknown because three separate mechanisms compensate for part of it.
- **Every figure quoted from another benchmark** — the check firing counts, the
  fill-tier funnel, P = 0.545, 193/193 `slot_index`, 22/39 bracket recall, the
  ECE figures. Cited with source; **not re-run here.**

# Reproducing the one measurement

```bash
python3 benchmarks/omr-target-architecture-2026-09/probe_clef_double_read.py \
    --fixtures <dir of *.omr.json carrying clef_evidence> --glob '*.clefcontest.omr.json'
```

Read-only. Exit `0` measured · `1` the static argument was falsified (the two
detector rungs are not the same call) · `2` missing or empty input. **All three
refusal paths were proved by running**: a missing directory, a directory with no
matching files, and a directory of real transcriptions that carry no
`clef_evidence` (the committed scan-gate fixtures) each exit 2.

⚠️ **`clef_evidence` is a build product and no committed artefact holds it.** The
figures above come from the `--tag=clefcontest` arm of
`benchmarks/omr-clef-contest-reach-2026-09/`, which cost ~2600 s. Re-running the
probe needs those files or a fresh arm; the probe refuses rather than reporting
a zero.
