# Boxing is a DECISION — and layering it is what makes the width test a real witness

**2026-09-18.** Sean, on being told that a width read off the detector's own box
can catch the detector contradicting itself but can never corroborate its class:

> *"Is boxing something a decision? We are sending something forward that
> already has a declaration. 'It should fit in this box…' Something about this
> makes me feel like there should be more options at the GATHER stage and the
> ADJUDICATE stage should determine the boundaries, because that is partly how
> it is determined. Maybe we have 2 or 3 layers of boxing?"*

**This document argues he is right, that tonight's evidence is entirely
box-as-decision failures, and that the layering he proposes SOLVES the
corroboration problem `benchmarks/omr-notehead-width-2026-09` concluded was
unsolvable.** Read with
[docs/stage-charter-2026-09-18-what-each-stage-does.md](stage-charter-2026-09-18-what-each-stage-does.md)
and [docs/diagnosis-2026-09-18-who-actually-decided-it.md](diagnosis-2026-09-18-who-actually-decided-it.md).

⚠️ **Nothing here is built or measured. It is a proposal with a cost section.**

---

## 1. YES — AND THE BOX AND THE CLASS ARE ONE CLAIM, NOT TWO

A YOLO box is trained to bound a **class**. The box for
`noteheadBlackInSpace` is *the extent the model believes a black notehead
occupies*. So the box does not describe the ink — **it describes the model's
hypothesis about the ink**, and the name and the boundary are the same
assertion made twice.

That is exactly why the width lane found what it found: *"a width read off the
detector's own box is that detector's signal however it is filed, so it can
catch the detector CONTRADICTING ITSELF but can never corroborate the class."*
**Sean's question is the diagnosis of that result rather than a reaction to
it.**

And `gather.py:373` files it with `log.observe` — as a **FACT about the page**
— which is the category error. It is a fact about the DETECTOR.

## 2. ⚠️⚠️ EVERY CONTAMINATION FAILURE MEASURED IN THE LAST TWO DAYS IS A BOUNDARY FAILURE FIRST

Not a naming failure. In each case **the extent was decided wrongly, and then a
name was assigned to that wrong extent**:

| what the print shows | what the boxing did |
|---|---|
| a stem joined to its own notehead | ONE box over BOTH → measured "too WIDE" → **the stem is discarded because it was found attached to its own note** (217 heads Litolff, 345 Breitkopf) |
| a barline | a notehead-class box over a long thin run — **459 of 476** in Breitkopf's largest bucket |
| a printed time-signature **8** | boxes carved out its **two round counters** separately and called each a notehead — 8 of the 22 misses |
| the printed word **cresc** | a box carved out the letter **e** |
| a rehearsal mark **B** | a box over the letter, both bowls legible |
| a whole rest | a box of notehead WIDTH and half its height |

⚠️ **The time-signature counters are the decisive case**, because they show the
boundary can be wrong in the *other* direction: the box is not too big, it is
**a sub-part carved out of a larger glyph**. No width test, no height test and
no class rule can see that, because at the scale of the box everything is
consistent. **Only the extent of the surrounding INK disagrees.**

## 3. ⚠️ A BOX STRUCTURALLY CANNOT REPRESENT A MERGE OR A SPLIT — AND BOTH ARE THE NORM HERE

This repo has already measured that the plates do not hand us one mark per
thing: *"Litolff MERGES and Breitkopf SHATTERS, and neither plate gives one row
per mark"*; the median Litolff cell's largest component holds **46%** of its
ink; Breitkopf is **56% specks**. A single box has nowhere to say *"this extent
contains two marks"* or *"this mark continues outside this extent."*

⚠️⚠️ **AND `Q.INK` ALREADY DOES THE RIGHT THING, ONCE**: it carries
`ink_n_components` and `ink_share_of_cell` **as a merge WARNING rather than
repairing the merge**, on the explicit ground that deciding where one mark ends
is not GATHER's business. **That is Sean's principle already implemented, in
exactly one place, and read by nothing.**

## 4. THE LAYERING — three, and they are already half-built

| layer | what it is | decides? | status today |
|---|---|---|---|
| **1. INK EXTENT** | the connected component: *this ink is physically joined to this ink*, in both frames, with merge/split warnings | **no** — a measurement | **`Q.INK`, built, default-ON, READ BY NOTHING** |
| **2. CANDIDATE EXTENTS** | *IF this is an X, its extent is this* — the detector's box, a template match, the stroke reader's column band, a projection | **no** — hypotheses, several per piece of ink, none privileged | **exists but MIS-FILED as fact** (`Q.GLYPH_BOX` via `log.observe`); the stroke reader's bands exist behind a flag |
| **3. ADJUDICATED EXTENT** | the boundary chosen *as part of* deciding what it is, with the losing candidates recorded | **yes** | **does not exist** |

⚠️ **Layer 3 is Sean's sharpest point and it is right: deciding the boundary IS
how the name is decided.** A stem is a stem *because* there is a hairline run of
roughly 3½ staff spaces at the side of a notehead — the run's extent is not a
separate fact to be looked up afterwards, **it is the evidence for the name.**
The repo already relies on this without naming it: the stroke reader works by
finding an extent, and `A-DUR-8` attaches a note to its beam **by its STEM**,
i.e. by an extent rather than by a centre.

## 5. ⚠️⚠️ WHY THIS SOLVES THE PROBLEM THE WIDTH LANE CALLED UNSOLVABLE

That lane's conclusion was that the only independent witness would have to
measure the INK, *"which is `Q.INK`, default-ON and read by nothing."* The
layering says what to DO with it:

**Layer 1 against layer 2 is a genuine two-witness comparison** — one is the
raster, the other is the model — and their DISAGREEMENT is the signal:

* ink extent **>>** proposed extent → a **MERGE**: the stem fused to its head.
  *This is the width cap's entire population, reframed as a disagreement rather
  than as a disqualifying measurement.*
* proposed extent is a long thin run, class says notehead → a **BARLINE**. The
  459.
* ink extent **⊃** proposed extent, and the surrounding component is a digit →
  a **SUB-PART CARVED OUT**. The eight time-signature counters — the case no
  box-internal test can reach.
* many ink components inside one proposed extent → a **SHATTERED** mark
  (Breitkopf's 56% specks).

**None of these requires a new threshold.** They are all *"the two layers
disagree, and here is how"*, which is a recorded fact a later stage can weigh —
questioning without overturning.

## 6. ⚠️ FOUR HONEST COSTS AND ONE REFINEMENT

1. **ROUTING IS BY CLASS TODAY** (`export._claims`, `gather_glyph_families`).
   If layer 2 is a hypothesis rather than a fact, nothing can be routed by it
   alone, and **every family's dispatch changes.** This is the large cost and it
   should be costed before it is started.
2. **RECORD SIZE.** `Q.INK` alone is **0.6 MB/page** (Litolff) and **3.1
   MB/page** (Breitkopf) against records already in the hundreds of MB.
   Carrying several candidate extents per piece of ink multiplies it. Sean's
   instruction to hold everything is explicitly scoped to **discovery**.
3. **FRAMES WILL BITE IMMEDIATELY.** Comparing layers means comparing
   coordinates, and this repo's most repeated defect is a frame error — two
   staves' canonical frames coincide by construction, a page box is a fact about
   one page, a measure box is corners where a detection box is width/height.
   `Q.INK` already carries both frames, which is the mitigation.
4. **IT IS A GATHER CHANGE**, so `readjudicate` and `reexport_arm` are
   structurally blind to it and pricing needs **two full re-gathers**.

⚠️⚠️ **THE REFINEMENT: "ADJUDICATE determines the boundaries" hits a limit,
because boundaries are JOINT.** ADJUDICATE's charter is *"what does this ONE
thing mean"* — but if this ink belongs to the stem it cannot also belong to the
notehead, so neighbouring extents are **mutually exclusive** and cannot be
settled one at a time. That is a partition problem. **The repo has the pattern
already**: `adjudicate_glyph_owner` resolves a cross-staff CONTEST, and the
dedupe work's lesson was that *a contest must be RESOLVED, not RELOCATED* —
688 verdicts had been relocating a copy and doubling one piece of ink into two
notes. **So boundary arbitration between neighbours should follow the CONTEST
pattern, not the per-thing pattern** — and where a contest cannot be resolved,
the honest outcome is a recorded ambiguity, not a split.

## 7. THE CHEAPEST FIRST STEP, and it changes no value

**Report the layer-1 vs layer-2 disagreement as a number, acting on nothing.**
It needs no new threshold, no routing change and no re-gather beyond one, and it
would immediately say — per publisher — how much of the detector's output is a
merge, a barline, a carved sub-part or a shattered mark. **That single table is
the thing no instrument in this repo can currently produce**, and it is what
would tell us whether layer 3 is worth building.

## 8. ⚠️ WHAT THIS DOES NOT CLAIM

* **Nothing here is measured.** Section 5's four disagreement shapes are
  predictions from the print evidence of
  `benchmarks/omr-stem-crop-pass-2026-09` and
  `benchmarks/omr-notehead-width-2026-09`, not results.
* It does **not** claim boxes are the wrong representation everywhere — they
  are demonstrably fine for noteheads on clean engraving (**856 of 856**). The
  claim is narrower: **a box cannot carry a merge, a split, or a sub-part, and
  on these plates those are the common cases.**
* It does **not** argue the stages are the main source of bad readings. Much of
  the loss is upstream of all of them.
* The three-layer split is a PROPOSAL. Two of the three layers exist in some
  form; the argument that they should be explicitly separated, and that layer 2
  should stop being filed as a fact, is new and untested.

---

## 9. ⚠️⚠️ ADDENDUM — LENGTH IS A POSITIVE IDENTIFIER FOR EVERYTHING EXCEPT A STEM, AND THAT INVERTS HOW `detect_stems` WORKS

Sean, 2026-09-18, after being shown that a barline (4.00 spaces) sits at the
median of the stem distribution (3.93) and an accidental (~2.5) does not:

> *"Because stems change in length that should not be a factor in determining
> what it is. Accidentals have 2 consistent sizes (normal and small — for grace
> notes). Bar lines are the length of a staff or they extend to other systems.
> **Length is helpful in all of them except stems.**"*

**He is right, and it is a sharper statement than the symmetric one it
replaces.** Length is not a weak discriminator between stems and accidentals —
it is a **strong POSITIVE identifier for every vertical mark whose length is
ENUMERABLE, and no identifier at all for the one whose length is CONTINUOUS.**

| vertical mark | its length | enumerable? |
|---|---|---|
| **accidental** | **two sizes** — normal, and `*Small` for grace notes | **YES** |
| **barline** | the staff's height, or a known multi-staff span | **YES** (from the staff geometry) |
| **clef** stroke | fixed sizes, and confined to the header window | **YES** |
| **STEM** | **2.14 → 6.78 staff spaces, median 3.93** (measured, n = 1,920) | **NO** |

⚠️ **The two accidental sizes are ALREADY IN THE CLASS SPACE, not a proposal**:
`accidentalFlat` / `accidentalNatural` / `accidentalSharp` alongside
`accidentalFlatSmall` / `accidentalNaturalSmall` / `accidentalSharpSmall` — and
Sean hand-labelled BOTH `accidentalNatural` and `accidentalNaturalSmall` on
Brahms p2. The vocabulary already asserts his claim.

### ⚠⚠ THE INDICTMENT THIS CARRIES: `detect_stems`' FILTERS ARE ALL DIMENSION BOUNDS ON A VARIABLE-LENGTH OBJECT

⚠⚠ **CORRECTED 2026-09-18 EVENING — THIS SECTION SAID "SIX FILTERS" AND ONLY
FOUR CAN FIRE.** `benchmarks/omr-vertical-runs-2026-09` measured it over **12,944
real candidates**: the **ASPECT** test (`h/w < 3.0`) can never fire, because past
the height and width bounds `h/w ≥ 2.0/0.6 = 3.33` **always** and the ratio is
scale-invariant; and the **AREA** floor cannot either, because a component
surviving a 1.6-space opening carries ≥ 32 px against a floor of 10. **Both read
ZERO.** ⚠ It does not weaken the argument — the four that DO fire are still all
dimension bounds — but *"six filters"* is wrong wherever this repo says it,
including the stage charter and the forward plan. ⚠ And it is **not** an argument
for deleting them: `filter_sweep_arm.py` relaxes `max_width_lines` to 1.5, at
which both become live.

Every one of them tries to describe a stem by its size — `max_width` 0.6,
`min_height` 2.0, `max_height` 8.0, a 3:1 aspect, an area floor, an edge margin.
**By this argument none of them can work, and the repo's own history is the
evidence:**

* the **width cap** discards **217 (Litolff) / 345 (Breitkopf)** heads, and the
  crop pass adjudicated its discards **33 of 33 REAL** — it is throwing away
  stems *because they are still attached to their own notehead*;
* `max_height = 8.0` exists only because a cap at 6.0 *"silently un-stemmed
  exactly the notes furthest from their beam"*;
* `min_height = 2.0` is what puts ~12.6% of real stems into accidental
  territory.

**Three constants, three recorded failures, all of the same kind: an attempt to
bound something the engraver varies on purpose.**

### THE INVERSION IT IMPLIES

**Identify the enumerable marks POSITIVELY by length. Identify the STEM by
ATTACHMENT — a notehead at one of its ends, offset half a notehead width from
that head's centre — and never by dimension.**

That is the synthesis of Sean's two observations in this conversation: *a stem
is connected to a notehead* (which is its positive evidence) and *length is
helpful for everything except stems* (which is what its evidence is NOT). Each
kind of vertical mark then gets the evidence that actually identifies it, rather
than one size window applied to all of them.

⚠️ **THE GUARD, because the obvious version of this is unsafe.** If a stem were
merely *"what is left once the others are identified"*, then every failure to
recognise a barline or an accidental becomes a stem. **So attachment must be
POSITIVE evidence and not a residue** — a run is a stem because a notehead sits
at its end, not because nothing else claimed it. A thin-shape sanity floor stays
(it must still be line-shaped); a length WINDOW does not.

⚠️ **AND IT EXPLAINS THE ACCIDENTAL SURPRISE** of
`benchmarks/omr-ink-first-2026-09`: the veto fired on **24 accidentals, clefs and
rests of 33** because **the pipeline has no category for "a vertical line that is
not a stem."** They were not being mistaken for stems by a bad rule — there was
nowhere else for them to go.

⚠️ **The tight-spacing case Sean raised strengthens it rather than weakening
it**: when an engraver squeezes accidentals into a sixteenth-note run, what
compresses is the HORIZONTAL spacing — the gap to the note and to its
neighbours. **The height does not compress, because an accidental's height is
set by the staff.** So in exactly the crowded case where position and proximity
become unreliable, **length is the property that stays put.**

⚠️ **NOT MEASURED**: the accidental sizes are quoted from the glyph vocabulary
and SMuFL, not measured on these plates; the ~12.6% stem/accidental overlap is
Litolff only; and no arm has tested attachment-without-a-length-window, which is
what this addendum proposes.
