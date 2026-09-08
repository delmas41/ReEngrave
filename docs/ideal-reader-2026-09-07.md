# What correctly reading a page requires

**Commissioned by Sean, 2026-09-07:**

> *"My initial instinct is that this list is shaped too much by our experience
> and needs to be addressed philosophically. What is the ideal scenario should
> shape this first."*
>
> *"Our ideal should benefit from what we have learned, not be made up entirely
> in isolation. I also don't want a false dichotomy between consistent reading
> and a pipeline of better decisions."*

⚠️ **Nothing here is measured.** This is reasoning about notation, written to
give `tools/omr/staged/ASSUMPTIONS.md` a standard it was not written against.
Part 2 tags every assumption **PRINCIPLE** or **CONTINGENCY**; the tags are
mirrored into that file so the two cannot drift.

⚠️ **Nothing here says the staged pipeline is wrong.** Part 4 lists what a
contingency is currently shaping that it should not, and does not rebuild it.

⚠️ **Part 1 is derived from Sean's own account of reading a score**, relayed by
the coordinator and treated here as primary source. Three of his statements do
real work below and are quoted where they are used: the **chain** (*system →
instrument → clef → key → time signature → note*), the **accidental scope
rule**, and the observation that a key change is shared across transposing
staves *"because the relationship between the two changes together"*. The third
corrected a row of my own table.

---

# PART 1 — THE IDEAL

## What a printed score is, considered as a thing to be read

A score is an encoding designed for a performer who must read it **at speed, at
a distance, while playing**. **Three** consequences follow, and they are
different in kind. ⚠️ **Confusing the first two is the single most expensive
mistake a reader can make; missing the third is why a reader works harder than
it needs to.**

### (a) Notation COMPOSES — and composition is not redundancy

Most of what a reader wants is stated nowhere. It is the value of a function
over several marks:

> sounding pitch = *f*( notehead position, clef, key signature, accidentals
> earlier in this bar, the instrument's transposition )

Five marks, one answer, and **no redundancy whatever** — remove any one and the
answer is unrecoverable, not merely less certain. The key signature does not
*corroborate* the accidentals; it is a compression device and the accidental is
its override. **A reader that treats a compositional chain as agreeing witnesses
manufactures disagreements that do not exist**, and a reader that resolves such
a "disagreement" corrupts the chain.

### (b) Notation REPEATS — and repetition is where the free evidence is

A smaller, **enumerable** set of facts is printed more than once, because a
performer's eye cannot hold them:

| the fact | its witnesses |
|---|---|
| the meter | printed on **every staff** of the system |
| the clef, the key signature | reprinted at the head of **every system** — *within one part* |
| a key **change** | ⚠️ shared across the staves of a system as a **DELTA, not a value** — see below |
| where a bar ends | one barline crossing **every staff** of the system at one x |
| a tied note's pitch | stated at **both ends** of the tie |
| who is playing | the margin **name**, the **clef**, the **register** of the notes, the **transposition**, and the work's **roster** |
| how many staves a system has | the **bracket**, the **systemic barline**, the staff count itself |
| how time divides a bar | the meter, the **sum of durations**, the **beaming** |

These are genuine redundancy: **one fact, several witnesses, each readable
without the others.**

⚠️ **One row of that table is subtler than the rest, and Sean's account
corrected my first draft of it.** A key signature is **not** redundant in VALUE
across the staves of a system — a clarinet in A and a flute print different
signatures for the same music. What is shared is the **change**:

> *"Transposing instruments help define the key, because the relationship
> between the two changes together."*

So the invariant across staves is **the delta**, and a reader that looks for a
shared *value* will see disagreement everywhere on any orchestral page. He gives
the same shape for spotting a change at all: *"a new group of accidentals that
always adds sharps or flats in the same order"* — **the order is the invariant,
not the count.**

⚠️ The general lesson is bigger than the key signature: **for each redundant
group, the invariant must be stated, and it is not always the value.**

> ⚠️ **Composition is where errors HIDE. Repetition is where they SHOW.**

### (c) Notation CONSTRAINS — and this is what makes the chain an order

An earlier fact does not merely *corroborate* a later one; it **removes
candidates** for it. Sean's example is exact:

> *"If we know that the first line is a flute then we know it is not a
> transposing instrument. Then clef should be either treble or treble with an
> 8va marking."*

That is not a weight and not a witness. A flute **cannot** be in bass clef, and
knowing the instrument deletes most of the clef's candidate set before any clef
is read. The same holds down the whole chain he describes —

> *system → instrument → clef → key → time signature → note*

— and it is why that is the right ORDER rather than merely a possible one:
**each step is chosen to narrow the next by the most.** The note is last because
everything narrows it.

⚠️ **Constraint is not redundancy and must not be scored like it.** A witness
that agrees raises support; a constraint that is violated makes a reading
**impossible**, and the two are not on a scale together. This is the general
form of the rule ownership already applies — *a veto on the impossible, never on
the unlikely.*

⚠️ **And constraint is MONOTONE**: each step only removes candidates, never adds
them. That matters in Part 3.

## What follows, for any correct reader

0. **Represent a candidate SET, not just a chosen value.** Constraint (c) works
   by deletion, so a reader that only ever holds one answer has nowhere to put
   *"it is one of these three"* — and that is the state most of the chain is in
   most of the time.
1. **Keep each mark separately from what it composes into.** One mark
   participates in several compositions and any of them may later be revised.
   Sean states the composition rule for accidentals exactly: *"If there is a key
   signature then that should apply to all of the notes after until there is
   another accidental, which will affect all the same notes in that bar only."*
   ⚠️ Note the two different SCOPES in one sentence — the signature is
   part-scoped and until-revoked, the accidental is bar-scoped and pitch-scoped.
   **A reader that cannot represent a fact's scope cannot apply either rule.**
2. **Hold "two readings of one fact, and they disagree" as a VALUE.** In a
   redundant group this is the only correctness signal available without
   external truth.
3. **Distinguish not-printed from printed-and-unread from read-as-zero.** In a
   redundant group a *silent* witness is not a *dissenting* one, and a reader
   that cannot tell them apart cannot count a majority.
4. **Know which witnesses are independent.** Two witnesses derived from one
   source are one witness; counting them twice manufactures confidence out of
   nothing.
5. **Be able to say "I do not know."** Without it, a group with no majority
   forces a guess, and the record can no longer distinguish that guess from a
   reading.

## What "correct" means — and what is checkable at runtime

> A reading is correct when **every composition evaluates to what the page
> means** and **every redundant group agrees**.

**Only the second is checkable without the answer.** So the redundant groups of
(b) are the *entire* self-check available to a reader with no ground truth, and
**enumerating them is the highest-value thing such a reader can do.** Everything
else is a guess about a guess.

---

# PART 2 — EVERY ASSUMPTION, RE-DERIVED

**PRINCIPLE** — true of reading music, and of any correct reader.
**CONTINGENCY** — true only of the parts we happen to have.

⚠️ **A principle that arrived through a scar is still a principle.** Several
below are ours by injury and survive on their merits; the *why* column says so.

| # | tag | why it holds — or what would have to change |
|---|---|---|
| **A-ORDER-1** order of adjudication | **CONTINGENCY** (the list) over **PRINCIPLE** (the rule) | That order binds *only* where one decision consumes another's verdict is a consequence of composition (Part 1a). The specific 21-item list is ours. |
| **A-ORDER-2** identity before ownership and clef | **PRINCIPLE** | Sean's chain, and Part 1c's reason for it: identity **narrows** the clef, the range and the transposition. *"If we know that the first line is a flute … clef should be either treble or treble with an 8va marking."* |
| **A-GATHER-1** three forced gathering edges | **1 PRINCIPLE, 2 CONTINGENCY** | *Geometry before everything* is principle: a coordinate needs a frame. *Detection before direction text* and *before positions* are facts about **our** readers — a reader that segmented text and notation jointly would have neither. ⚠️ Currently written as if all three were laws of notation. |
| **A-DUR-1** duration is a verdict, not a measurement | **PRINCIPLE** | A duration is *composed* from notehead class, beams, flags and dots. The marks are measurements; the value is not. |
| **A-GROUP-1** an all-zero bracket reading abstains | **CONTINGENCY** | Purely an artefact of one function writing the same `0` from four branches. Gone the moment the reader emits its branch. |
| **A-GROUP-2** a brace means one player, so its evidence is the instrument | **PRINCIPLE** | A brace is a statement about *who plays*, not about *how many staves*. True of any engraving. |
| **A-GROUP-3** grouping is additive, never overruling | **CONTINGENCY** | "Additive" presupposes an incumbent to not-overrule. In the ideal there is no incumbent, only witnesses weighed together. A migration mode, not a permanent one. |
| **A-GROUP-4** the measurement is silent on 2-staff pages | **CONTINGENCY** | Our reader refuses systems under 3 staves. Nothing about notation makes a 2-staff system unreadable. |
| **A-CLEF-1** confidence is a tier, never a multiplier | **PRINCIPLE**, ours by injury | *An uncalibrated number is worse than none* is an epistemic truth, not a local one — a number that reads as evidence and is not corrupts every decision downstream. ⚠️ The **three-band bucketing** and the cut points are CONTINGENCY. |
| **A-CLEF-2** the relative weights | **CONTINGENCY** | Ours entirely. ⚠️ And Part 4.3: weighting at all is arguably the wrong shape. |
| **A-CLEF-3** a decision may abstain | **PRINCIPLE** | Part 1, requirement 5. |
| **A-CLEF-4** `clefC` names nothing | **PRINCIPLE** | Alto, tenor, soprano, mezzo and baritone **are the same glyph on different lines**. A class name cannot name one; only geometry can. This is a fact about notation, not about our detector. ⚠️ *Recorded here as CLOSED — see the honesty note below.* |
| **A-CLEF-5** a `clefC` is worth 1.5 as family support | **CONTINGENCY** (the number) over **PRINCIPLE** (the shape) | *A glyph that names a family constrains without deciding* is principle. 1.5 is ours. |
| **A-CLEF-6** the floor carries two jobs | **CONTINGENCY** | An artefact of computing margin against a runner-up of 0. A reader that scored absolute support separately would not have it. |
| **A-OWN-1** ladder → range → distance; confidence unweighted | **PRINCIPLE** | *A veto on the impossible outranks a preference among the possible* is principle — and Part 1c says why: a constraint and a witness are not on one scale. The measured 0.545 is contingent **evidence for** it, not the reason. |
| **A-OWN-2** the range veto reads position + clef, not a resolved pitch | **PRINCIPLE** | Part 1, requirement 1: never consume an interpretation where the mark is available, or the chain becomes unrevisable. |
| **A-EVAL-1** the downhill order | **PRINCIPLE** (direction) over **CONTINGENCY** (list) | Composition has a direction; that is what makes it composition. |
| **A-EVAL-2** an abstained clef produces no pitches | ⚠️ **CONTINGENCY presented as principle** | The principle is *never present a guess as a reading*. **Emitting nothing is one way to obey it; emitting a marked provisional reading is another, and is better for a human reviewer.** We chose silence because MusicXML has no way to say "uncertain". That is a fact about our OUTPUT FORMAT. See Part 4.2. |
| **A-EVAL-3** consequences are events, not values | **PRINCIPLE**, ours by injury | A record that must be re-maintained by every later writer *will* go stale; three fields did. An event describes a moment and cannot be made wrong later. |
| **A-BUILD-1** GATHER translates rather than emits | **CONTINGENCY** | We are not touching the old path. Gone when readers emit their own rows. |
| **A-BUILD-2** `Subject.staff` is system-local | **PRINCIPLE** | A staff's identity within its system is what every join needs; a page-wide running index is an implementation detail that means something different. |
| **A-BUILD-3** `detector=None` is a mode | **PRINCIPLE** | A missing reader is an abstention, not a failure — Part 1, requirement 3. |
| **A-BUILD-4** the label cascade runs free-rung-only | **CONTINGENCY** | A build-phase safety choice. |
| **A-BUILD-5** an empty stage is an error | **PRINCIPLE**, ours by injury | A stage that produced nothing because nothing was loaded is indistinguishable from one that had nothing to do. Requirement 3 again, at the level of the machine. |
| **A-BUILD-6** an external fact's descendants carry it | **PRINCIPLE** | Part 1, requirement 4, stated exactly. |

**Tally: 25 entries — 12 PRINCIPLE, 8 CONTINGENCY, 5 MIXED** (a principled
shape carrying a contingent constant or list). ⚠️ **One, A-EVAL-2, is a
contingency currently doing a principle's job**, which is the finding this
exercise was for.

⚠️ **An honesty note, because it is the same failure this project has a name
for.** `ASSUMPTIONS.md`'s A-CLEF-4 entry still described `clefC → alto` as live
**after the code had closed it** — my edit silently matched nothing and I did not
check. *Fixed-then-kept-open-in-prose*, the documentation dual of
detected-then-dropped, in a file three days old. Repaired in the tagging pass.

---

# PART 3 — CONSISTENCY vs A PIPELINE OF BETTER DECISIONS

## The framing is false, and the reason is precise

The coordinator's guess — *consistency is a property to **measure and expose**,
not a fixpoint to **solve*** — is **substantially right, and can be made exact**
by splitting redundant groups according to what their members are.

**A group whose members are all MEASUREMENTS.** The meter on twelve staves. The
clef at the head of three systems. A barline's x across a system. The roster
against the lineup. **Measurements do not change**, so reconciling them is one
decision over a frozen set — which is precisely the gather-then-adjudicate
split. **No iteration arises, and none is conceivable**: there is nothing for a
second pass to see that the first did not.

**A group with a DERIVED member.** The bar's duration *sum* against the printed
meter. The beaming against the meter. Here resolving the group can change a
member, which changes the group. ⚠️ **This is the only place iteration could
arise at all** — and the project already has the answer, arrived at by injury:
**bound the repair.** `_reconcile_measure_to_meter` may re-read a beam level by
±1 only, the bar must land *exactly*, the answer must be *unique*, single-voice
measures only, and it never adds, deletes or re-pitches a note. **A bound
replaces a fixpoint**, and it is strictly better than one: it is inspectable,
it terminates by construction, and it cannot launder a guess.

## ⚠️ And constraint settles it independently

Part 1c gives a second, stronger argument that needs no case split.
**Constraint is MONOTONE** — identity deletes clef candidates, the clef deletes
pitch candidates, and nothing in the chain ever *adds* one back. A monotone
narrowing **terminates by construction**: the candidate set is finite and every
step shrinks it or leaves it alone.

So Sean's *"all the info needs to flow in any direction once it is gathered"* is
safe for a reason more basic than ordering discipline: **flowing information
into a narrowing chain can only remove possibilities, and removal cannot cycle.**
Iteration would only be needed if some step could *widen* a candidate set — and
in a correct reading nothing does. A reading that has to widen is a reading that
was wrong earlier, which is a repair, not a fixpoint.

## So why is it not a dichotomy

**Because consistency-seeking PRODUCES exactly the evidence a better-informed
pipeline CONSUMES.** They are one activity seen from two ends:

> *"the meter is 2/4 on eleven staves and 4/4 on the twelfth"* is not a problem
> to be iterated away. It is a **fact**, it is **cheap**, it is available
> **before any decision is made**, and the twelfth staff's other readings should
> be weighed knowing it.

A pipeline that carries disagreement as a first-class value gets *strictly more*
information than one that reconciles it early, because reconciliation is lossy:
once you have written "the meter is 2/4" you can no longer tell a unanimous page
from a page with one dissenter. **Consistency is what feeds the pipeline, not
what competes with it.**

## ⚠️ Where I disagree with the coordinator's phrasing

**"Measure and expose" is not enough, and this project has the scar.** An
exposed signal with no consumer is what `pitch_candidates`,
`clef_evidence["contest"]` and `contested_notehead_pairs` already are — three
complete records, correctly maintained, read by nobody. **A disagreement must be
CONSUMABLE**: a row a later decision names in its `wants`, so the harness can
record that it was there and that the decision saw it.

> **Measure it, expose it, and give it a consumer — or it becomes the fourth
> orphan.**

## What iteration would actually cost, if anyone wanted it

Two things the project does not have and has twice declined to build: a
**convergence argument** (does it terminate, and does the fixed point mean
anything?), and a **rule for when two bounded repairs disagree**. Both declines
were right. If it were ever needed, it would be bounded to a *single* group
containing a derived member, one pass, with the derived member's re-derivation
bounded exactly as the meter/duration repair already is — i.e. it would look
like what we have, not like a solver.

---

# PART 4 — WHAT CHANGES IN THE BUILD

**Listed, not rebuilt.**

### 4.1 ⚠️ The redundant groups are not represented at all — the biggest gap

Part 1 says they are the entire runtime self-check, and the staged build
gathers **none of them as groups**. It emits `Q.METER_GLYPH` per staff and
`Q.CLEF_GLYPH` per staff, and nothing anywhere says *"these N rows are witnesses
to ONE fact; here is whether they agree."*

**What it would look like:** a redundant group is declared by (quantity, scope)
— the meter's scope is the SYSTEM, the clef's is the PART across systems, the
barline's is the SYSTEM — and the harness derives, for free, `n_witnesses`,
`n_silent`, `majority`, `dissenters`. That derived agreement becomes a row a
decision can declare in `wants` (per Part 3). **This is the one addition Part 1
demands that experience did not suggest**, and it is close to free: every
witness is already a row.

### 4.2 A-EVAL-2 — silence is our output format, not a principle

An abstained clef currently produces **no pitches**. The principle is *never
present a guess as a reading*; silence is one way to obey it and a **marked
provisional reading** is another, and better for the human reviewer this project
exists to serve.

**What it would look like:** the consequence still runs, and every pitch it
derives from an abstained clef is stamped `provisional`, with the abstention in
its basis. Cheap to switch, as the coordinator asked — it is one branch in
`restate_pitch`.

### 4.3 A-CLEF-2 — weighting destroys the group structure

`adjudicate_clef` sums weighted terms, which **throws away how many independent
witnesses agreed**. Part 1 says that count *is* the signal. A weight of 3.0 from
one reader and 1.5+1.5 from two are indistinguishable in the sum, and they are
not the same evidence at all.

**What it would look like:** partition the readers into agreement groups first,
record the partition on the verdict, and let the decision see *"three witnesses,
two agree"* rather than *"score 4.5"*. The signed-term machinery stays for
ordering within that.

### 4.4 ⚠️ There is no way to say "it is one of these three"

Part 1, requirement 0. A `Ruling` carries a value or abstains, and a `Verdict`
records `DECIDED` or `ABSTAINED`. **Neither can express a narrowed candidate
SET** — which, by Part 1c, is the state most of the chain is in most of the
time. Knowing the staff is a flute should *delete bass, alto and tenor* and
leave `{treble, treble-8va}` for the next reader, and today that knowledge can
only arrive as a term nudging a score.

**What it would look like:** a third outcome, `NARROWED`, carrying the surviving
candidates. It is not a probability — it is a set, and set intersection is how
constraints compose. ⚠️ It also gives abstention a floor: a decision that
narrowed 5 candidates to 2 and then could not choose has said something useful,
and today it is indistinguishable from one that knew nothing.

### 4.5 A-GROUP-3 — "additive" is a migration mode

Correct while an incumbent exists; it should not calcify into the architecture.
Nothing to change now; it needs an expiry, not an edit.

### 4.6 A-GATHER-1 — label the two contingent edges

Two of the three "hard gathering edges" are facts about our readers, not about
notation. They are currently written as if all three were laws. A one-line
correction in the docstring, so nobody later treats them as immovable.

---

# WHAT IS UNMEASURED HERE

Everything. This is reasoning about notation and about the code in this tree.
No arm was run, no page was read, and no claim here is an accuracy claim. The
one *empirical* statement — that `ASSUMPTIONS.md`'s A-CLEF-4 entry was stale —
was checked by reading the file.
