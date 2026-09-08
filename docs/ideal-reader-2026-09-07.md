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
the coordinator and treated here as primary source. Four of his statements do
real work below and are quoted where they are used: the **chain** (*system →
instrument → clef → key → time signature → note*), the **accidental scope
rule**, the observation that a key change is shared across transposing staves
*"because the relationship between the two changes together"*, and — the
largest — **what he does when a mark is unreadable**, which supplied property
(d) and answered a live build fork.

⚠️ **Two of the four corrected me rather than confirming me.** The key-change
remark overturned a row of my own redundancy table (the invariant is the delta,
not the value), and the unreadable-mark answer overturned both my Part 1
conclusion (*"only agreement is checkable"*) and the two-way fork I had put to
him. **The parts of this document that came from asking are the parts that
changed.**

---

# PART 1 — THE IDEAL

## In one paragraph

A score **composes** (a sounding pitch is a function of five marks with no
redundancy — remove one and the answer is unrecoverable), **repeats** (an
enumerable set of facts printed several times: the meter on every staff, the
clef at every system head, a tie's pitch at both ends), **constrains** (an
earlier fact deletes candidates for a later one — a flute cannot be in bass
clef), and **is testable by consequence** (a candidate can be run forward
through a composition and its output checked against what is independently
known — do these implied pitches fit this instrument's range; do these
durations sum to this meter). Composition is where errors hide, repetition is
where they show, constraint is why the chain has an order, and consequence is
how a reader settles what is unreadable. **So a correct reader keeps every mark
apart from what it composes into, carries each fact's scope, holds a candidate
SET and a disagreement as values, knows which witnesses are independent, and can
say "I do not know" — after testing, and distinguishably from a convention.** A
reading is correct when every composition evaluates to what the page means and
every redundant group agrees; **the second is checkable directly and the first
by implication, and those two self-checks are the whole of what a reader with no
ground truth has.**

⚠️ The rest of Part 1 is the derivation. A reader who stops here has the ideal.

## What a printed score is, considered as a thing to be read

A score is an encoding designed for a performer who must read it **at speed, at
a distance, while playing**. **Four** consequences follow, and they are
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

⚠️ **Sean corrected my first draft of one row.** A key signature is **not**
redundant in VALUE across staves — a clarinet in A and a flute print different
ones. What is shared is the **change**: *"transposing instruments help define
the key, because the relationship between the two changes together."* A reader
looking for a shared *value* sees disagreement on every orchestral page.

⚠️ The lesson is bigger than the key signature: **for each redundant group the
invariant must be STATED, and it is not always the value.**

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

### (d) A composition can be RUN FORWARD ON A CANDIDATE and its output tested

⚠️ **This is the operation that turns (a) from a liability into a test, and it
is the one I missed.** It comes from Sean, answering what a reader does when a
mark is unreadable:

> *"If a clef is unreadable then I would look to what instrument it is and
> usually there are only a few options and almost always a primary simple
> choice — then I would look to see if the clef were what I think it is would
> the pitches it implies make sense? If it looks like a time signature changes
> then the math of the notes in the measure would verify."*

A composition has no redundancy among its **inputs** — that is (a) — but its
**output is not free**. A pitch must lie in the instrument's range; a bar's
durations must sum to its meter; a tie's two ends must be the same pitch. So an
unknown input is recovered by **generate and test**: enumerate candidates, run
the composition forward on each, keep those whose output satisfies what is
already known.

> **The evidence is not new. It is the evidence already gathered, evaluated
> THROUGH the candidate.**

It costs nothing to acquire and it discriminates **precisely where repetition
cannot** — on the compositional chain, which is where (a) says errors hide.

⚠️ **Note the symmetry with (c), and that termination survives.** Constraint by
**antecedent** deletes candidates *before* the fact is read (a flute cannot be
in bass clef). Constraint by **consequence** deletes them *after*, by what they
would imply. **Both only ever delete**, so the narrowing is monotone in both
directions and Part 3's argument is untouched.

## What follows, for any correct reader

Six requirements, each falling out of (a)–(d) above rather than from our parts.

0. **Represent a candidate SET, not only a chosen value** — (c) and (d) both
   work by deletion, and a narrowed set is the *input* to the implication test.
   Sean narrows to a few options **in order to** test them.
1. **Keep each mark separately from what it composes into** — one mark feeds
   several compositions, and (d) re-runs them on candidates.
2. **Carry a fact's SCOPE.** Sean states two in one sentence: *"a key signature
   … applies to all of the notes after until there is another accidental, which
   will affect all the same notes in that bar only."* Part-scoped and
   until-revoked; bar-scoped and pitch-scoped. **A reader that cannot represent
   scope can apply neither rule.**
3. **Hold "two witnesses to one fact disagree" as a VALUE** — (b)'s whole
   product.
4. **Distinguish not-printed from printed-and-unread from read-as-zero** — a
   *silent* witness is not a *dissenting* one, and a reader that confuses them
   cannot count a majority.
5. **Know which witnesses are independent** — two derived from one source are
   one witness; counting twice manufactures confidence.
6. **Be able to say "I do not know"** — and, per (d), to say it only *after*
   testing, and to distinguish it from a declared convention.

## What "correct" means — and what is checkable at runtime

> A reading is correct when **every composition evaluates to what the page
> means** and **every redundant group agrees**.

The second is checkable directly. ⚠️ **And the first is checkable INDIRECTLY,
by (d)** — not against the page's meaning, which we do not have, but against
what the composition's output must satisfy. **That is the correction Sean's
answer forces on my first draft**, which said only the second was checkable and
concluded that enumerating redundant groups was the highest-value thing a reader
could do.

It is not the only one. **A reader with no ground truth has two self-checks, and
they cover different ground:**

| | checks | reaches |
|---|---|---|
| **agreement** (b) | witnesses to one fact disagreeing | facts that are *printed more than once* |
| **implication** (d) | a candidate's consequences violating what is known | the *compositional chain*, where nothing is printed twice |

Neither subsumes the other, and (d) is the one aimed at where errors hide.

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

Part 1c and 1d give a second, stronger argument that needs no case split.
**Constraint is MONOTONE IN BOTH DIRECTIONS** — narrowing by antecedent deletes
clef candidates *before* the clef is read, testing by consequence deletes them
*after* by what they would imply, and neither ever *adds* one back. A monotone
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

### 4.2 ⚠️ A-EVAL-2 — ANSWERED, and the answer is neither option I offered

I asked Sean whether he leaves an unreadable clef blank or pencils a guess.
**He does neither**, and his procedure has three steps where I offered two:

> narrow from context → **test the candidates by what they imply** → if still
> undecided, take *"the primary simple choice"*

So the fork was a false one. `abstain → emit nothing` is not the alternative to
`guess silently`; **the alternative is to decide by implication, and to fall
back to a declared convention only when the test cannot discriminate.**

**What it becomes:**

| situation | outcome |
|---|---|
| the implication test discriminates | `DECIDED`, with the test in the basis |
| candidates survive the test equally | `DECIDED` on the conventional default, `reason="convention"` |
| no candidates, or no test available | `ABSTAINED` — genuinely nothing to say |

The middle row is the one that did not exist before, and it is Sean's *"almost
always a primary simple choice"*. ⚠️ **It is not a silent guess**: `reason` and
`basis` distinguish a convention from a reading on the record, which is the
whole point of the verdict shape. **Requirement 5 — "be able to say I do not
know" — is preserved and its population shrinks.**

⚠️ **How much it shrinks is UNMEASURED and I am not measuring it.** The
implication test needs *something* known about the output, and §4.7 shows the
clef has two such tests with different reach.

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

⚠️ **And (d) is what makes it pay.** A narrowed set is not just a more honest
abstention — **it is the input to the implication test.** Sean narrows to a few
options *in order to* test them; a set with no test is a shrug, and a test with
no set has nothing to run over. The two features are one feature.

### 4.5 A-GROUP-3 — "additive" is a migration mode

Correct while an incumbent exists; it should not calcify into the architecture.
Nothing to change now; it needs an expiry, not an edit.

### 4.6 ⚠️ The two implication tests already exist. Neither needs rebuilding.

Reasoning from what is already recorded — **no measurement taken.**

⚠️⚠️ **THE TRAP, AND IT HAS ALREADY BEEN MEASURED AND REFUTED IN ONE FORM.**
`clef_register_warning` asks whether a staff's median pitch is inverted
relative to its **neighbour** — reach 7 of 193 scan staves, precision **0 of
11**, because an orchestral score is ordered by **family, not by register**, so
every firing was a family boundary (bassoon above horn). **That form is dead.**
What Sean describes differs on four counts and none of them is cosmetic:

| | the refuted check | the implication test |
|---|---|---|
| scope | two staves compared | **one staff, self-contained** |
| reference | the neighbour's reading | **this instrument's own written range** |
| subject | a settled reading, audited | **a candidate, being tested** |
| assumption | that staves are ordered by register — **false** | none about ordering at all |

**Anyone proposing this must be able to state those four differences.** It is
also *not* either of the two variants `docs/architecture-decision-map.md` §9.4
leaves open (one bracket group; a staff against its own reading on other
systems) — it is a third, and it is the mechanism `clef_correction.propose_clef`
already implements.

**`clef_correction.propose_clef` — RIGHT MECHANISM, WRONG GATE.** It proposes a
clef from the instrument's written range: exactly Sean's *"would the pitches it
implies make sense?"*, self-contained on one staff. Its problem is not
correctness, it is **reach**: it fires only where **no clef was read**, so it
sees 34 of 396 staves (8.6%) and produced 5 proposals on 193 scan staves,
applying **0**. ⚠️ **The documented ceiling is clefs read WRONG — a population
the fill tier cannot see BY CONSTRUCTION.**

The staged pipeline removes the gate structurally rather than widening it: the
clef adjudicator holds a candidate **set**, so the test runs over *every*
candidate on *every* staff that has an instrument, and "fill where empty"
stops being a tier at all. ⚠️ **Its reach is then bounded by IDENTITY**, and on
scans that is the binding constraint — 29 of 29 unresolved non-treble staves
print no label at all.

⚠️ **So the clef needs a SECOND implication test that needs no identity, and one
is already in the tree.** The accidental run's **positions** are measured
clef-free; the **slot table** is chosen by the clef. So running
`fit_key_signature` over each candidate clef and comparing the fits is a test of
the *clef*, needing no instrument. **The evidence that it discriminates is the
documented bug**: fitting three flats against a *guessed* clef returned **two
sharps** — a different accidental type fitting a different prefix. A fit that
changes that much with the clef is a sensor for it. **A bug becomes an
instrument when you run it deliberately over all candidates instead of
accidentally over one.** ⚠️ It is vacuous where no accidentals were found, and
a 0-accidental key fits every clef — so the two tests cover different staves,
which is the point of having both.

**`rhythm_sum_warning` — RIGHT MECHANISM, RIGHT REACH, NO CONSUMER.** *"The math
of the notes in the measure would verify"* is already computed, and it fires
**111 times on 193 scan staves**. Its only consumer is a boolean presence count
feeding a UI percentage. ⚠️ **The arithmetic Sean describes is already being
done and thrown away** — and it is the one high-volume check with **no
confidence field at all**.

⚠️ **One caution specific to this half.** Meter-vs-durations is the redundant
group with a **derived** member (Part 3), so it is the one place a test could
become a loop. As a **test** it is free. As a **repair** it needs the bound that
already exists — ±1 beam level, exact landing, unique answer, single voice.
**Test freely; repair only under the bound.**

**Verdict: neither is the wrong shape.** One is absence-gated and one is
consumer-less. In the staged pipeline both are ordinary implication terms in a
decision that declares them — which is what `wants` is for.

### 4.7 A-GATHER-1 — label the two contingent edges

Two of the three "hard gathering edges" are facts about our readers, not about
notation. They are currently written as if all three were laws. A one-line
correction in the docstring, so nobody later treats them as immovable.

---

# PART 5 — WHICH FACTS CAN BE CHECKED WITHOUT TRUTH

> Sean: *"There will be certain facts that can be determined by themselves:
> this measure is 4/4 and it has 9 eighth notes is a provable mistake. Other
> things like is this a C or a C# will not be internally provable. That needs
> to be connected to what weighs in the process."*

Every decision in `adjudicate.ORDER` now carries `checkable=`, `checked_by=`,
`implicates=` and `composed_from=` **in the decorator**, enforced by
`test_staged_discipline.py`. This part says what the categorisation is, what
testing it changed, and what it implies for weight.

## 5.1 The distinction, and three things the binary hides

**CHECKABLE** — an independent constraint must hold, so a violation is
detectable with no ground truth. **UNCHECKABLE** — the fact is *determined* but
not *verified*; read the marks right and the answer is forced, and nothing
independently confirms it. ⚠️ **The uncertainty is in the reading, not in the
logic** — which is why "wrong" and "unverifiable" are different words.

Testing it against the 21 decisions surfaced three refinements, each of which
changes a weight:

1. ⚠️ **A check has RESOLUTION.** It catches errors larger than its own
   granularity and is blind below. The written-range test catches a whole
   **clef** error — two or more diatonic steps — and cannot see **C vs C#**, one
   semitone. *That is why Sean's example is the example*: C# is not mysterious,
   it is simply below the resolution of every constraint available.
2. ⚠️ **A check has COVERAGE.** A tie's two ends must be the same pitch — so
   C vs C# **is** checkable *at a tie* and nowhere else. "Uncheckable" nearly
   always means *"uncheckable in general, checkable in special positions"*, and
   the special positions are worth naming because they are free.
3. ⚠️ **A check inherits its inputs' reliability.** A sound check over
   unreliable inputs is an unreliable check — and this is measured, not
   supposed. The tie/slur grammar veto is exactly the constraint in (2), and it
   scored **neutral on engravings and +130 edits on SCANS**, because its input
   is the resolved pitch and `wrong note` is 26% of that pool. **The check was
   never wrong; its evidence was.**

## 5.2 ⚠️ The result: nothing is purely CHECKABLE

| | count | decisions |
|---|--:|---|
| **CHECKABLE** | **0** | — |
| **MIXED** | 14 | system membership, system staff count, measure partition, staff group, instrument, slot index, part partition, clef, key signature, glyph owner, arc kind, duration, tuplet ratio, meter |
| **UNCHECKABLE** | 7 | staff ordinal, group symbol, arc owner, articulation owner, wedge anchor, dynamic, direction |

**Every fact that can be checked at all is checkable only through what it
composes INTO, never by re-reading it.** That is property (d) arriving as a
result rather than an assertion, and it is why the empty first row matters:
**checkability is a property of a fact's CONSEQUENCES, not of its reading.**

## 5.3 ⚠️ A failed check is certain about the GROUP and silent about the MEMBER

Nine eighths in a 4/4 bar proves an error. It does not say **which**: the meter,
a duration, a spurious note, a missing one, or a mis-owned glyph from the staff
above. So a violated constraint must **raise every member's suspicion** and must
never **condemn the cheapest member to change**. `implicates=` is that
membership, declared, and a test asserts the fact under test is always in its
own group — *a check that implicates only other facts has quietly decided it is
innocent.*

✅ **The tree already honours this in the one place it is implemented.**
`_reconcile_measure_to_meter` repairs a failed bar sum only when the corrected
bar lands **exactly** on the meter and the answer is **unique** — i.e. it
declines precisely when more than one member could explain the failure. That is
the rule, implemented, before it was stated.

⚠️ **And the membership is wider than it looks.** `rhythm_sum_warning`'s group
contains **glyph ownership**: a notehead wrongly awarded from the staff above
breaks the receiving bar's sum. So the highest-volume unconsumed check in the
tree is also a check on the 4,521-contest arbitration that today resolves 94.1%
of cases by distance.

## 5.4 What it implies for weight — four rules, differentiated by kind

| evidence | how it combines | why |
|---|---|---|
| **agreement** among independent witnesses (b) | **SUM**, correlated groups counted once | more witnesses is more evidence |
| **composition** from inputs (a) | ⚠️ **MINIMUM over the inputs**, not the sum | if any input of a composition is wrong the output is wrong — a chain is as strong as its weakest link. `composed_from=` is what a consumer needs to compute it |
| a **violated** constraint (d) | a **negative** term on **every** member of `implicates` | §5.3 |
| a **satisfied** constraint (d) | a **weak positive** on all members | ⚠️ **asymmetric on purpose**: many wrong readings also pass. A bar summing to 4/4 could hold two compensating errors. **Failing is strong disconfirmation; passing is weak confirmation.** |

⚠️ **The second row is the correction to a naive terms model** and the staged
pipeline does not implement it yet: `tally` sums everything. Summing is right
for agreement and wrong for composition.

## 5.5 ⚠️ Why this matters beyond the design

The score library holds **235 editions** and pairs a PDF with a reference
encoding for **27 works**. Sean's stated primary input is scanned orchestral
scores from IMSLP, and **almost none of them will ever have a reference
encoding.**

> **So the CHECKABLE class is the part the system can police on the actual
> work, and the UNCHECKABLE class is the part that will always need either a
> reference or a human.**

Two consequences worth acting on:

* Every error in the 7 UNCHECKABLE decisions — *and* every error finer than a
  check's resolution (§5.1.1), which includes **C vs C#** — is invisible to the
  system on a page with no reference. **That is not a gap to close; it is the
  permanent shape of the problem**, and it is what the review UI exists for.
* ⚠️ **It follows that human attention should be spent on the uncheckable
  class**, because the checkable class can be found without them. A review
  queue ordered by *"what can I not check?"* is worth more than one ordered by
  confidence — and it needs no model to build, only `checkable=`.

## 5.6 The checks that already exist and are not consumed

⚠️ **The cheapest work on this entire list.** Ranked by what is recorded; **no
measurement taken here.**

| check | volume | precision | consumed? |
|---|---|---|---|
| ⚠️ **`label_contradiction`** — a staff whose OWN margin label was read on THIS page, exported under a different name | **158 firings** over two whole works (110 of 973 and 48 of 1713 labelled staff records) | ⚠️ **hand-adjudicated 0.873 the EXPORT is wrong**, 0.127 the label is, 0 both right | ❌ **computed on every contextual pass, acted on by nothing** |
| `rhythm_sum_warning` | **111 of 193** scan staves | unmeasured | ❌ a boolean presence count feeding a UI percentage; ⚠️ the one high-volume check with **no confidence field at all** |
| `time_signature_disagreement` | 17 of 193 scan | unmeasured | ❌ |
| `propose_clef` | 34 of 396 staves (8.6%) | 5 proposals on 193 scan staves, **0 applied** | ⚠️ right mechanism, **absence-gated** — fires only where NO clef was read, while the ceiling is clefs read WRONG |
| `key_signature_warning` | 0 scan / 3 engraved | — | ❌ near-silent |
| `measure_count_warning` | **0 / 0** | — | ⚠️ a check that never fires cannot order anything. Corroborated by a separate probe finding 0 disagreeing staves over 27 systems, so it may be *true* rather than broken — but it has no discriminating power on this corpus |
| `clef_register_warning` | 7 of 193 | **0 of 11** | ⚠️ **refuted in its adjacent-staff form** — see Part 4.6 |
| ✅ `key_signature_corroboration` | 7 flips | — | ✅ **CONSUMED, default-ON since 2026-09-07 — the model to copy** |

⚠️ **`label_contradiction` is the headline and it is not close.** It has the
highest volume, the only *measured* precision on the list, and — decisively for
§5.5 — **it needs no truth file, no dossier and no roster**: it asks the
document to agree with itself. It is also invisible to every standing
measurement, because musicdiff does not score `<part-name>`.

---

# WHAT IS UNMEASURED HERE

Everything. This is reasoning about notation and about the code in this tree.
No arm was run, no page was read, and no claim here is an accuracy claim. The
one *empirical* statement — that `ASSUMPTIONS.md`'s A-CLEF-4 entry was stale —
was checked by reading the file.
