# Audiveris — Part C: Notation Assembly & Interpretation

**What this is.** A reference on how Audiveris (the most mature open-source OMR
engine, AGPL-3.0) turns *detected symbols* into *music* — the reasoning layer.
Written for the ReEngrave team to borrow ideas from, not code. This slice is the
"categorizing brain": the Symbol Interpretation Graph (SIG), the reduction that
resolves competing hypotheses, and the chord / rhythm / slur / logical-part
assembly that sits on top.

**License boundary (AGPL-3.0).** Everything below documents *algorithms,
architecture, and parameter values* — facts and ideas, which are not
copyrightable — for a clean-room, independent reimplementation. No verbatim
source is reproduced; formulas are given as mathematics and prose. All claims
carry `file:line` citations into the Audiveris `master` tree so you can verify,
but **do not copy Java out of those files into ReEngrave** — reimplement from the
description. Anything I judge to need genuine clean-room care is flagged
`⚠️ CLEAN-ROOM`.

**Evidence tags.** `[DOC]` = official documentation; `[SRC]` = read directly in
Audiveris source; `[INFERENCE]` = my reasoning from the two; `[NOT FOUND]` =
looked, could not confirm.

**Source note.** The docs' internals pages (`/explanation/steps/reduction/`
etc.) are mostly stubs marked "Documentation not yet provided" `[DOC]`; the
conceptual SIG page (`/tutorials/main_concepts/sig/`) is written and useful
`[DOC]`. So most of what follows is `[SRC]`, from these files under
`app/src/main/java/org/audiveris/omr/`:

| area | files |
|---|---|
| Grade framework | `glyph/Grades.java`, `sig/GradeImpacts.java`, `sig/GradeUtil.java` |
| SIG | `sig/SIGraph.java`, `sig/inter/AbstractInter.java`, `sig/inter/Inter.java` |
| Relations | `sig/relation/{Relation,Support,Exclusion,AbstractConnection,HeadStemRelation}.java` |
| Reduction | `sig/SigReducer.java` |
| Chords | `sheet/note/ChordsBuilder.java`, `sig/inter/{HeadChordInter,AbstractChordInter}.java` |
| Rhythm | `sheet/rhythm/{PageRhythm,StackRhythm,MeasureRhythm,SlotsRetriever,Voice,VoiceDistance,MeasureStack}.java` |
| Slurs/curves | `sheet/curve/{SlursBuilder,SlurLinker,CurvesBuilder}.java`, `sig/inter/SlurInter.java` |
| Logical parts | `score/{PartCollation,ScoreReduction,LogicalPart}.java` |

---

## 0. The one-paragraph mental model

Audiveris does **not** commit to a reading symbol-by-symbol. Every candidate
interpretation of some ink — this blob *might* be a quarter head, *might* be an
eighth rest — becomes a **vertex** (`Inter`) in a per-system graph (the `SIG`),
carrying a **grade** ∈ [0,1] (a confidence). Candidates that reinforce each other
(a stem and a head that touch correctly) are joined by **support** edges;
candidates that compete for the same ink, or that are musically incompatible,
are joined by **exclusion** edges. A symbol's *contextual* grade is its own
intrinsic grade boosted by whoever supports it. Then one algorithm —
**reduction** — repeatedly purges weak vertices and, for each remaining
exclusion, deletes the weaker of the two competitors, recomputing grades as it
goes, until what survives is a **consistent, high-confidence, maximal set** of
interpretations. Chords, voices, rhythm, slurs and parts are then *built on that
surviving set*. The contrast with ReEngrave — which commits at each pipeline
stage and patches afterward with consistency checks — is the whole point of this
document, and is drawn out in §8–§10.

---

## 1. THE GRADE FRAMEWORK

Everything downstream is denominated in *grades*, so start here.

### 1.1 What a grade is

A grade is a confidence in `[0, 1]`, clamped there explicitly
(`GradeUtil.clamp`, `sig/GradeUtil.java:58-69`) `[SRC]`. Two grades live on every
interpretation:

- **intrinsic grade** — how good this symbol looks *on its own* (classifier
  output plus geometry), stored on the inter (`AbstractInter`, field `grade`);
- **contextual grade** — the intrinsic grade *after* accounting for supporting
  neighbours (`AbstractInter.ctxGrade`, `sig/inter/AbstractInter.java:142`)
  `[SRC]`.

`getBestGrade()` returns the contextual grade if it has been computed, else the
intrinsic (`AbstractInter.java:508-517`) `[SRC]`.

### 1.2 The intrinsic grade is a weighted geometric mean of "impacts"

An inter's intrinsic grade is not a single classifier number; it is assembled
from several weighted sub-scores called **impacts** (`GradeImpacts` holds three
parallel arrays: names, values, weights — `sig/GradeImpacts.java:30-37,60-66`)
`[SRC]`. The combination rule (`GradeImpacts.computeGrade`,
`sig/GradeImpacts.java:102-120`) `[SRC]` is a **weighted geometric mean, then
scaled**:

```
global = Π_i  impact_i ^ weight_i
grade  = intrinsicRatio · global ^ (1 / Σ_i weight_i)
```

Two facts about this formula matter:

- **Any zero impact is a veto.** If a single impact is 0, `global` collapses to 0
  and the whole grade is 0 (`GradeImpacts.java:112-113`) `[SRC]`. Geometric-mean
  scoring means one failed criterion kills the interpretation, unlike a weighted
  *sum* where a strong criterion can rescue a failed one.
- **`intrinsicRatio` deliberately holds intrinsic grades below 1.** It is `0.8`
  (`glyph/Grades.java:106-108`) `[SRC]`, described as "Reduction ratio applied on
  any intrinsic grade" to "leave room for contextual" — i.e. a symbol can never
  reach full confidence from its own appearance alone; the top 20% of the scale
  is reserved for contextual corroboration. `[SRC]`

### 1.3 The named grade constants

All thresholds live in one class (`glyph/Grades.java`) `[SRC]` — a single tunable
table, which is itself an adoptable idea (§10). Values as of `master`:

| constant | value | role |
|---|---:|---|
| `intrinsicRatio` | 0.80 | ceiling factor on every intrinsic grade |
| `validationMinGrade` | 0.80 | training-time acceptance |
| `goodBarConnectorGrade` | 0.65 | "good" bar connector |
| `minContextualGrade` | 0.50 | **purge threshold** — below this an inter is deleted |
| `goodInterGrade` | 0.40 (= 0.8·0.5) | "good" interpretation |
| `goodRelationGrade` | 0.50 | "good" relation |
| `goodBeamGrade` | 0.35 | "good" beam |
| `ratherGoodHeadGrade` | 0.30 | "rather good" head |
| `symbolMinGrade` | 0.15 | min to be a symbol at all |
| `minInterGrade` | 0.08 (= 0.8·0.1) | floor to keep an inter |
| `keyAlterMinGrade1` | 0.10 | key accidental, phase 1 |
| `timeMinGrade` | 0.10 | time signature |
| `clefMinGrade` | 0.03 | clef (deliberately low) |
| `keySigMinGrade` | 0.01 | key signature |
| `keyAlterMinGrade2` | 0.01 | key accidental, phase 2 |

The spread is informative: **clefs and key sigs are given very low minimum
grades** (0.03, 0.01) because they are structurally load-bearing — Audiveris
would rather keep a weak clef hypothesis alive and let context confirm/deny it
than purge it early. `[INFERENCE]` This is exactly ReEngrave's clef pain point
(the whole `clef_geometry` / `clef_locator` saga), approached from the other end:
Audiveris keeps the hypothesis; ReEngrave commits to a default and patches.

### 1.4 The contextual-grade formula — the crown jewel

This is the single most portable thing in the whole engine. Given an inter's
intrinsic grade `g` and a total support `contribution` from its partners
(`GradeUtil.contextual`, `sig/GradeUtil.java:81-85`) `[SRC]`:

```
contextual(g, contribution) = ( (1 + contribution) · g ) / ( 1 + contribution · g )
```

where each supporting partner contributes
(`GradeUtil.contributionOf`, `:156-160`) `[SRC]`:

```
contributionOf(partner_grade, ratio) = partner_grade · (ratio − 1)
```

and `contribution` is the sum over partners. Properties, all easy to verify:

- `contribution = 0` ⟹ `contextual = g` (no support, no change).
- As `contribution → ∞`, `contextual → 1` (unbounded support saturates at
  certainty).
- It is monotincreasing in both `g` and `contribution`, and stays in `[0,1]`
  whenever `g ∈ [0,1]`. `[INFERENCE]`
- It is a probabilistic "odds-boost": a good partner drags a mediocre symbol up,
  but the better the symbol already is, the less a partner can add. Example:
  `g = 0.3`, one partner of grade 0.8 through a relation with `ratio = 3` gives
  `contribution = 0.8·(3−1) = 1.6`, so `contextual = (2.6·0.3)/(1 + 1.6·0.3) =
  0.78/1.48 ≈ 0.527` — a weak head (0.3) becomes keepable (>0.5) *because a
  strong stem vouches for it*. `[INFERENCE, SRC]`

The formula is ~5 lines and has no Audiveris-specific dependencies. Reproducing
the *mathematics* is fine (it is a fact); do not copy the Java. **This is
adoptable idea #1.**

### 1.5 Where the "ratio" comes from — support relations carry the boost

A support relation's strength is not fixed; it scales with the relation's own
quality grade (`Support.getSourceRatio` / `getTargetRatio`,
`sig/relation/Support.java:152-179`) `[SRC]`:

```
sourceRatio = 1 + sourceCoeff · relationGrade
targetRatio = 1 + targetCoeff · relationGrade
```

The two coefficients are **asymmetric per relation type** and default to 0 in the
base class (`:139-142,163-166`, min support grade 0.1 at `:224`) `[SRC]`;
subclasses set them. Concretely, for a head↔stem support
(`HeadStemRelation.java:234-257,715-721`) `[SRC]`:

- `stemSupportCoeff = 10` (how much a head boosts *the stem*),
- `headSupportCoeff = 4`, further multiplied by a size-`getConsistency()` factor
  (how much a stem boosts *the head*).

So the same physical relation boosts the stem far more than the head — a stem
with a head attached is *much* more likely real than a head with a stem
attached. The asymmetry is a modelled fact about notation, encoded in two
numbers. `[SRC]`

---

## 2. THE SYMBOL INTERPRETATION GRAPH (SIG)

### 2.1 Structure

The SIG is a directed multigraph, one per **system** (`SIGraph extends
Multigraph`, built on the JGraphT library) `[SRC]`:

- **Vertices = `Inter`** (interpretations). One blob of ink can spawn *several*
  inters (a quarter-head hypothesis and an eighth-rest hypothesis for the same
  pixels), and they all coexist as separate vertices. The `inter/` package has
  ~80 concrete inter types (`HeadInter`, `StemInter`, `BeamInter`, `RestInter`,
  `ClefInter`, `KeyAlterInter`, `SlurInter`, `AugmentationDotInter`,
  `TupletInter`, `BarlineInter`, …) `[SRC]`.
- **Edges = `Relation`** (`relation/` package, ~60 types) `[SRC]`.

### 2.2 The three relation kinds `[DOC + SRC]`

The conceptual SIG doc names exactly three flavours `[DOC]`, confirmed by the
class hierarchy `[SRC]`:

1. **Support** (`relation/Support.java`) — mutual reinforcement; *increases*
   contextual grade of both linked inters. Examples: `HeadStemRelation`,
   `BeamStemRelation`, `BeamHeadRelation`, `AlterHeadRelation` (accidental→head),
   `SlurHeadRelation`, `AugmentationRelation`, `ChordStemRelation`,
   `TimeTopBottomRelation`, `ClefKeyRelation` (a clef and a key-signature that are
   pitch-compatible vouch for each other — the doc's worked example) `[DOC, SRC]`.
2. **Exclusion** (`relation/Exclusion.java`) — mutual incompatibility; *at least
   one* of the two must be discarded. Carries an `ExclusionCause`; the two
   observed causes are `OVERLAP` ("physical overlap") and `INCOMPATIBLE`
   (`Exclusion.java:64-69`; used in `SigReducer.java:77-78`) `[SRC]`.
3. **Neutral / informational** — convey structure without support or exclusion,
   e.g. `Containment` (a symbol inside an ensemble) and `NoExclusion` (an
   explicit "these two do NOT exclude even though they overlap", used for mirror
   heads) `[DOC, SRC]`.

Relations also declare cardinality (`isSingleSource` / `isSingleTarget`,
`Relation.java:200-207`) `[SRC]` — e.g. a head may support at most one stem on a
given side — which is what lets reduction know when duplicate links must be
pruned to one.

### 2.3 Contextual grade over the graph, with partner conflicts handled

`SIGraph.computeContextualGrade(inter)` (`sig/SIGraph.java:215-290`) `[SRC]` is
where §1.4 meets the graph:

1. Collect all `Support` edges on `inter` (`getSupports`).
2. For each, read the correct-direction ratio (`getTargetRatio` if `inter` is the
   edge target, else `getSourceRatio`), and keep the partner only if `ratio > 1`
   and the partner has a grade (`:257-270`). Its contribution is
   `partner.grade · (ratio − 1)`.
3. **Crucial subtlety — supporters can themselves be mutually exclusive.** Two of
   `inter`'s supporters might be rival interpretations of the same ink. You cannot
   count both. So `getPartitions(inter, partners)` (`:570-640`) `[SRC]` enumerates
   every *maximal set of pairwise non-excluding* supporters, and the contextual
   grade is the **max over partitions** of `contextual(g, Σ contribution)`
   (`:274-289`). In words: *credit an inter with the best consistent story its
   neighbours can tell about it, never a contradictory one.* `[SRC]`
4. `contextualize()` (`:353-357`) recomputes this for every vertex; it is re-run
   throughout reduction as the graph changes. `[SRC]`

`getPartitions` sorts candidates by reverse grade and, if no exclusions exist
among them, short-circuits to the single trivial partition (`:585-634`) `[SRC]`
— the expensive enumeration only happens when there is real conflict.

### 2.4 How competing hypotheses for the same ink are represented

Two mechanisms `[SRC]`:

- **Explicit exclusion edges** between rival readings (inserted by reduction, §3).
- **`insertExclusion` refuses to exclude two inters that support each other**
  (`SIGraph.java:861-896`): if a `Support` relation already exists between the
  pair, no exclusion is added (`:878-885`). Support beats exclusion. Exclusions
  are always oriented low-id → high-id for determinism (`:865-867`) `[SRC]`.

The upshot: the graph holds the *full lattice of competing readings
simultaneously*, with confidences and with the support/conflict structure among
them, and defers the choice to one global step.

---

## 3. REDUCTION — resolving the graph to one consistent reading

This is the deepest architectural idea and the part with the least documentation
(`/explanation/steps/reduction/` is a stub `[DOC]`), so it is entirely `[SRC]`
from `sig/SigReducer.java` (2435 lines) and the reduce helpers in `SIGraph.java`.
⚠️ **CLEAN-ROOM: treat the *ordering and control flow* below as the design to
reimplement from scratch — it is the crux of the engine — not as text to port.**

### 3.1 Generating conflicts from geometry — `detectOverlaps`

Before anything is resolved, conflicts must be *created*. `detectOverlaps`
(`SigReducer.java:1358-1432`, commented "This method is key!") `[SRC]`:

- Walks inters sorted by abscissa; for each pair whose bounding boxes have
  Intersection-over-Union `≥ minIou = 0.05` (stem↔head uses `minIouStemHead =
  0.02`) (`:1361,1406`; constants `:2379-2385`) `[SRC]`,
- does a precise two-way `overlaps()` shape test, and if they genuinely collide
  **and are not `compatible`** (some class pairs are allowed to overlap: beams,
  slurs-vs-flags/alters/barlines, stems-vs-slurs/wedges — `:132-161`) `[SRC]`
  **and are not mirrors of each other** (`:1394-1397`),
- inserts a mutual `OVERLAP` exclusion (`excludeOverlap` → `insertExclusion`).

So *overlap in the image becomes an exclusion in the graph*: two symbols fighting
over the same pixels are marked as rivals, to be settled by grade. The
abscissa-sort gives an early break once boxes can no longer overlap
(`:1427-1428`) `[SRC]`. **This IoU-overlap-→-keep-the-stronger mechanism is
adoptable idea #2** and maps directly onto ReEngrave's cross-class YOLO
over-detection problem (§9, §10).

### 3.2 Resolving one exclusion — greedy, confidence-first

`SIGraph.reduceExclusions` (`sig/SIGraph.java:1232-1301`) `[SRC]` is the conflict
resolver. Its documented strategy `[SRC]`:

1. Among **all** current exclusion edges, pick the one whose *stronger* endpoint
   (`max(source.getBestGrade, target.getBestGrade)`) is the highest across the
   whole graph (`:1242-1257`).
2. Delete the **weaker** endpoint of that chosen exclusion (`:1259-1282`).
3. Removing a vertex removes the support it was giving, so **recompute the
   contextual grade of every inter that the deleted vertex had supported**
   (`:1291-1294`).
4. Repeat until no exclusions remain (`:1237,1298`).

This is a **greedy, iterative relaxation**, not exhaustive constraint
satisfaction and not global MAP inference. It resolves the *most confident*
conflict first (where the answer is clearest), then lets that decision ripple
through the grades before tackling the next. `[SRC, INFERENCE]` It can be
locally sub-optimal, but it is cheap and stable, and — importantly for the
ReEngrave comparison — it shows that even the mature engine settles for a
**heuristic** resolution of the graph rather than an optimal one.

### 3.3 Purging weak vertices — the grade gate

`SIGraph.deleteWeakInters` (`:384-411`) `[SRC]` deletes every non-frozen inter
whose *contextual* grade `< minContextualGrade (0.50)`. Ledgers are exempt (they
die later when no head references them). "Frozen" inters (human-validated, or
otherwise locked) are never purged. This is the point where §1.4's contextual
boost pays off: a symbol that survives *only because a partner vouched for it*
(intrinsic 0.3, contextual 0.53) is kept; one nobody vouches for is dropped.
`[SRC]`

### 3.4 The reduction loop — a fixpoint over purge + consistency + exclusion

`SigReducer.reduce(adapter)` (`:1882-1942`) `[SRC]` orchestrates it:

```
detectOverlaps(filtered inters)      // §3.1 — create geometric exclusions
adapter.checkFrozens()               // delete anything conflicting with a frozen inter
sig.contextualize()                  // §2.3 — grades up to date
adapter.prolog()
repeat (epoch):
    deleted  += contextualizeAndPurge()      // §3.3 recompute + deleteWeakInters
    deleted  += adapter.checkSlurs()
    while (adapter.checkConsistencies() > 0)  // inner fixpoint: structural rules
        ...
    reduced  += sig.reduceExclusions()        // §3.2 resolve remaining conflicts
    while (adapter.checkLateConsistencies() > 0)
        ...
until (nothing reduced AND nothing deleted)   // outer fixpoint
```

Key points `[SRC]`:

- **Two nested fixpoints.** `checkConsistencies` is itself looped to
  quiescence *inside* each epoch (`:1926-1928`), and the whole epoch repeats
  until an epoch changes nothing (`:1939`). Deletion changes grades, which enables
  more deletion — the loop runs until the graph is stable.
- **`checkConsistencies` is the constraint layer.** Each adapter supplies its own
  (`:2248,2310,2401`) `[SRC]`: it enforces notation rules such as "a stem needs a
  head at an end", "an augmentation dot attaches to one note", "a beam needs
  stems", collapsing duplicate links to one (`reduceAugmentations`,
  `reduceHeadAugmentations` keep only the best/best-placed relation —
  `:1953-1978,2004-2071`) `[SRC]`. Violations trigger deletions or edge removals,
  counted as `modifs` so the loop knows to continue.
- **Two passes with two adapters.** `reduceFoundations()` (`:1988-1991`) runs at
  the **REDUCTION** step over the *founding* inters (heads, stems, beams) with
  `AdapterForFoundations`; `reduceLinks()` (`:2080-2083`) runs the final global
  pass at the **LINKS** step with `AdapterForLinks`. Assembly (chords, rhythm,
  slurs) happens *between and after* these, on the surviving inters. `[SRC]`

### 3.5 What reduction is and isn't

It **is**: a probabilistic, support-and-exclusion-driven, greedy fixpoint that
selects a mutually consistent, above-threshold, near-maximal set of
interpretations, with grades propagating as decisions are made. `[SRC]`

It **isn't**: globally optimal, backtracking, or exhaustive. It never revisits a
deletion. `[SRC, INFERENCE]` That honesty matters for ReEngrave: the win is the
*data structure and the support/exclude modelling*, not a magic solver.

---

## 4. CHORDS — grouping heads on a stem, and voices later

`sheet/note/ChordsBuilder.java` `[SRC]`, doc: "gather, staff by staff, all notes
(heads and rests) into chords" (class doc). Assumes a chord belongs to one staff.

- **Grouping rule: shared stem = one chord.** `connectHead` (`:263-334`) `[SRC]`
  follows each head's `HeadStemRelation` edges; heads on the same stem are added
  as members of one `HeadChordInter` (`:314-330`). Note this is *not* an
  x-proximity heuristic — it is the SIG's head↔stem support edges, already vetted
  by reduction, that define the chord.
- **A head on two stems is duplicated (mirror).** A head with two `HeadStemRelation`
  edges (canonical share: stem-down on the left, stem-up on the right) is logically
  split into two heads, one per chord, linked by `NoExclusion` so the two chords
  don't kill each other (`:274-311,332-333`) `[SRC]`. This is how one printed note
  head participating in two voices is modelled.
- **Whole/stemless heads** have no stem and are gathered separately
  (`detectWholeVerticals`, `:350`) `[SRC]`.
- **Rests** become `RestChordInter` (single-member chords), `buildRestChords`
  (`:167`) `[SRC]`.

Voice assignment is **not** done here — chords are built first, voices are a
rhythm-step concern (§5).

---

## 5. RHYTHMS — slots, voices, meter check, and the search Audiveris gave up on

`sheet/rhythm/` `[SRC]`. Three levels: page → stack (a measure across all staves
of a system) → measure.

### 5.1 Slots: when do two chords start together?

`SlotsRetriever` (`:class doc`) `[SRC]` organises chords into vertical **time
slots** *before* voices/offsets are known. The rules are structural, not just
"same x":

- chords sharing a stem → same slot;
- chords from mirrored heads → same slot;
- chords in the same beam group but on different stems → **cannot** share a slot;
- similar abscissa is only a hint; slightly x-shifted chords can be *adjacent*
  and share a slot. `[SRC]`

Both a **narrow** and a **wide** slot reading are built and merged into
*compound slots* (`MeasureRhythm.process`, `:546-563`) `[SRC]` — a two-tolerance
approach to the ambiguity of "same beat".

### 5.2 Voices: minimum-cost assignment of incoming chords to active voices

`MeasureRhythm.process` (`:534-611`) `[SRC]` walks slots left to right. Starting
chords get voice numbers by vertical order and time-offset 0
(`processStartingChords`, `:623`) `[SRC]`. Then, per slot, `SlotMapper.mapChords`
assigns each incoming chord to a voice by minimising a **`VoiceDistance`** cost
(`sheet/rhythm/VoiceDistance.java:99-156`) `[SRC]`. The cost is a table of integer
penalties:

| situation | penalty |
|---|---:|
| forbidden link (`INCOMPATIBLE`) | 10000 |
| no link (`NO_LINK`) | 60 |
| chords from different staves (separated) | 20 |
| chord new in staff (separated) | 10 |
| opposite stem directions | 6 |
| non-rest chord | 4 |
| chords from different staves (merged) | 2 |

`INCOMPATIBLE = 10000` acts as a hard constraint; the rest are soft preferences.
Voice/time information also **propagates** across slots through three channels —
**tie**, **beam group**, and a manual **`NextInVoice`** relation — so a chord that
is beamed or tied to an already-voiced chord inherits its voice (`MeasureRhythm`
class doc; embraced-rest handling) `[SRC]`. So voice assignment is a small
weighted-assignment problem plus propagation, not a heuristic scan.

### 5.3 Meter check — and the search Audiveris deliberately abandoned

Here is the finding most relevant to ReEngrave's rhythm work. `PageRhythm`'s
class doc (`sheet/rhythm/PageRhythm.java:55-73`) `[SRC]` records that earlier
versions "tried very hard to play with FRATs as adjustment variables to come up
with a 'good' configuration within each stack" — where **FRAT = Flags, Rest
chords, Augmentation dots, Tuplets** (`:57-61,80-82`) — but "this took endless
computations and led to no practical results. So now we simply check the 'time
correctness' of each stack." `[SRC]`

So the flow is now:

- `StackRhythm.process(expectedDuration)` sets the expected measure duration and
  runs `doProcess`; on failure it merely **logs "no correct rhythm"** — it does
  not correct (`:218-229`) `[SRC]`.
- `MeasureRhythm.finalCheck` (`:265-282`) `[SRC]` verifies every chord has a voice
  and a time offset, then calls `measure.checkDuration()`, which sets the measure
  **abnormal** if actual ≠ expected (`MeasureStack` `isAbnormal`/`setAbnormal`,
  `excess` field, `:1517-1524,1896-1936`) `[SRC]`.
- The only remaining "search" is a **bounded 2-pass loop** used *only* when the
  implicit-tuplets option is on (`:542-608`) `[SRC]` — regenerate implicit
  tuplets once and re-run; otherwise a single pass.

**Read this carefully:** Audiveris marks a bad measure *abnormal* for a human to
fix (shown pink in its editor) rather than back-solving it — **but it flags only
after a genuine attempt to build a consistent voice/slot structure.** The flag is
the *residue of an assembly attempt*, not a standalone self-consistency test.
`[SRC, INFERENCE]` This directly validates ReEngrave's decision *not* to build a
general rhythm backtracker (§9).

---

## 6. SLURS / CURVES — fitting curves, then classifying tie vs slur

`sheet/curve/` `[SRC]`. Curves are found from the sheet **skeleton** (thinned
ink), independent of the note grid, then linked to heads.

- **Curve detection & fitting.** `CurvesBuilder` grows arcs along the skeleton and
  fits models; `SlursBuilder` "builds all slur curves from a sheet skeleton"
  (class docs) `[SRC]`, fitting circle/line models (`CircleModel`, `LineModel`)
  and pruning clumps of competing arcs (`ClumpPruner`) `[SRC]`.
- **Linking to heads.** `SlurLinker` (`:class doc`) `[SRC]` finds the best head on
  each side of a slur inside geometric **side areas**: horizontal slurs and
  vertical slurs use different side-area shapes; a candidate head's centre must
  lie on the correct side of the slur's bisector and be consistent with the slur's
  concavity. The chosen link becomes a `SlurHeadRelation` **support** edge
  (`SlurInter` doc: "linked via a `SlurHeadRelation` to a head on its LEFT and/or
  RIGHT side") `[SRC]`.
- **Tie vs slur is decided *after* linking, by pitch identity.** A slur is
  re-labelled a **tie** iff its two linked heads are `areTieCompatible` —
  **same step, same octave, same accidental** (key-implied alteration handled by
  the caller) — and the space between them is clear (`SlurInter.checkStaffTie`
  `:429-450`, `checkCrossTie` `:391-424`, `areTieCompatible` `:1061-1092`) `[SRC]`.
  Ties can also be validated across systems/pages via left/right slur extensions
  (`SlurInter` doc; `checkCrossTie`) `[SRC]`.

The pattern to notice: a slur is *geometry first, semantics second*. Its identity
as tie-vs-slur is not read off the curve; it is **inferred from the pitches of the
notes it connects** — a graph relation (`SlurHeadRelation`) plus a musical test.

---

## 7. PAGE + LOGICAL PARTS — one part = one instrument across the score

`score/` `[SRC]`. Systems are recognised independently, so "the flute" is a
different `Part` object in every system; collation stitches them into one
`LogicalPart`.

- **Match criterion (`PartCollation` class doc, `:40-58`)** `[SRC]`: two systems'
  parts may be identified as the same instrument only if they share the **same
  staff configuration** — same *count of staves*, same *count of lines* in
  corresponding staves, same *small* (cue-size) attribute. Parts may **not** be
  reordered between systems (no partA/partB ↔ partB/partA swap).
- **Pivot + direction (`collate`, `:185-242`)** `[SRC]`: a **2-standard-staff,
  piano-like part** ("biRecord") is used as an alignment **pivot**; parts above it
  are dispatched upward and parts below downward, because extra parts tend to
  appear at the **top** of a system — so when there is no pivot, collation runs
  **bottom-up** (`dispatch` dir ±1, `:256-267`).
- **Names are a *hint*, not the key.** OCR'd part names/abbreviations are used
  when available but the doc flags them "questionable for lack of OCR
  reliability" (`:57-58`) `[SRC]` — i.e. **geometry (staff config) is primary,
  text is secondary.** This is the exact inversion of a risk ReEngrave has already
  learned about (its `contextual.py` part identity leans heavily on margin
  labels; see §9).
- **Score level.** `ScoreReduction.reduce` (`:162-176`) `[SRC]` builds PartRef
  sequences per page and runs `PartCollation` to emit the score's `LogicalPart`
  list. Cross-page slur connection is explicitly listed as **not yet
  implemented** (`ScoreReduction` class doc) `[SRC]`.

---

## 8. THE BIG CONTRAST — one graph vs. a pipeline of commits

| | **Audiveris** | **ReEngrave** |
|---|---|---|
| Core data structure | one **SIG per system**: all competing readings coexist as graded vertices with support/exclusion edges | a **pipeline of dicts**: detections → pitches → durations → voices → export, each stage overwriting the last |
| When a reading is chosen | **deferred** to global reduction | **committed** at each stage (YOLO class, `pitch_resolver` `round()`, `voicing` mode-vote) |
| How conflicts resolve | exclusion edges + greedy grade-first reduction (`SigReducer`) | per-class NMS, precedence rules, then **post-hoc checks** (`_flag_*`) that *abstain* |
| Cross-symbol reinforcement | first-class: a stem raises a head's grade, a clef+keysig vouch for each other (`ClefKeyRelation`) | essentially absent between symbol types; corroboration happens only in narrow votes (`key_signature_vote`, clef reconciliation) |
| Confidence | pervasive, in `[0,1]`, intrinsic **and** contextual, drives every decision | YOLO confidence exists at detection but is **spent at detection**; downstream stages are boolean |
| Bad measure | build voices, then mark **abnormal** (`finalCheck`) | build durations, then **flag** (`_annotate_column_rhythm_warnings`) — but without the assembly attempt |
| Rhythm search | tried global FRAT search, **abandoned it** as impractical | never attempted it; `_reconcile_measure_to_meter` does a narrow ±1 beam-level fix |

The essential difference: **Audiveris keeps every hypothesis alive with a
confidence until one global step picks a consistent set; ReEngrave picks eagerly
and repairs.** ReEngrave's checks (`docs/internal-consistency-checks.md`) and
dossier layer are, in Audiveris terms, a *reduction that runs after the fact with
no competing hypotheses left to choose between* — they can detect that something
disagrees, but the alternative reading has already been thrown away, so they can
only **abstain or flag**, never *re-select*.

---

## 9. WHERE EACH ReEngrave MODULE SITS

Per-topic map with the honest gap. Paths are ReEngrave's `tools/omr/`.

**Chords — `voicing.py`.** `group_chords_in_measure` groups noteheads by
**x-proximity** (tolerance ≈ 0.6 × mean notehead width), *gated* by stem-direction
conflict, then takes chord duration as the **mode** of member durations
(`voicing.py:65-198`). *Gap vs Audiveris:* Audiveris groups by **shared-stem SIG
edges** vetted by reduction (`ChordsBuilder.connectHead`), not by x-distance —
which is why the divisi guard had to be bolted on (`voicing.py:107-148`). A
stem↔head relation, even a cheap CV one, is a stronger grouping key than pixel
distance, and gives the mirror-head split for free.

**Voices — `voicing.py:split_events_into_voices`.** One-or-two voices by
stem-direction only (`:201-238`). *Gap:* Audiveris solves a small min-cost
assignment (`VoiceDistance`) with tie/beam/NextInVoice **propagation**;
ReEngrave has neither cost model nor propagation, so beamed/tied continuations
aren't kept in-voice.

**Rhythm — `rhythm.py` + `transcribe._reconcile_measure_to_meter`.** `rhythm.py`
parses durations from beam-level clustering, flags, dots, and infers/back-fills
time signatures (`rhythm.py:195-560`). `_reconcile_measure_to_meter`
(`transcribe.py:2120-2204`) is a **one-variable constraint solve**: if a
single-voice bar doesn't sum to its meter, try re-reading *one* beam group by
±1 level, accept **only if exactly one** such change hits the meter exactly.
*Assessment:* this is a **narrow, correct instance of exactly what Audiveris's
abandoned FRAT search tried to do globally** — and Audiveris's own experience
(§5.3) says the global version is a dead end. **ReEngrave should not build a
general rhythm backtracker; it should keep and slightly widen this narrow one**
(e.g. allow it to select among a candidate *set* rather than only ±1 a beam).

**Pitch — `pitch_resolver.py`.** `pitch_for_notehead` snaps to the nearest staff
slot via `round()` (`:157-183`) — an eager commit. But
`pitch_candidates_for_notehead` (`:186-250`) already returns **top-N pitches with
weights** for M4's rerank. *This is the closest thing in the codebase to a graded,
competing-hypothesis representation* — it is the natural seed for adoption (§10).

**Consistency checks — `transcribe.py:_flag_*` + `docs/internal-consistency-checks.md`.**
Five additive, abstaining post-passes (measure count, column rhythm-sum, key-sig,
clef register, time-sig agreement). *Relation to Audiveris:* these are a
**post-commit reduction with the alternatives already gone** — they encode the
same invariants the SIG's exclusion/consistency rules do, but can only *surface*
disagreement, not *resolve* it, because there is no graph of live candidates and
no grade to pick a winner. The doc's own principle "majority ≠ correct, so we
don't majority-vote clefs" is precisely the failure mode a grade-weighted vote
(§10) is designed to fix.

**Dossier — `dossier.py`.** External-truth cross-check/seed. Audiveris has no
equivalent (it is fully unsupervised per sheet); this is a ReEngrave strength with
no Audiveris analogue, and it functions as a very high-grade "frozen inter" that
should win any reconciliation.

**Part identity — `contextual.py`.** `apply_contextual_analysis` names staves,
aligns slots across systems, fills defaulted clefs (`:314`, `_fill_defaulted_clefs`
`:127`). *Gap/warning from Audiveris:* `PartCollation` makes **staff configuration
(counts/lines) primary and OCR names secondary**; ReEngrave leans the other way
(margin labels drive the join). Audiveris's ordering is the more robust default
and worth weighting toward.

---

## 10. IS A SIG REALISTIC FOR ReEngrave? — and the adoptable middle path

**A full SIG port is not realistic, and shouldn't be attempted.** Reasons:

1. **It is an architecture, not a feature.** The `sig` package is `SIGraph`
   (1581 lines) + `SigReducer` (2435) + ~80 `Inter` classes + ~60 `Relation`
   classes, each relation hand-tuned with support coefficients. Adopting it means
   rebuilding ReEngrave's entire assembly layer around a graph. `[SRC, INFERENCE]`
2. **It presupposes a different front end.** Audiveris inters come from *glyph
   segmentation* with per-symbol geometry impacts; ReEngrave's front end is a YOLO
   detector emitting boxes + one confidence. Many Audiveris relations (precise
   stem-portion geometry, beam-portion, connection dx/dy grades) have no cheap
   analogue on box detections. `[INFERENCE]`
3. **Even Audiveris's solver is greedy, not optimal** (§3.2) and it *abandoned*
   its most ambitious search (§5.3) — so the payoff of "going full graph" is
   smaller than it looks. `[SRC]`

**But the *ideas* are highly adoptable at specific chokepoints**, because
ReEngrave already has the seeds: graded pitch candidates (`pitch_resolver`),
vote/reconcile layers (`key_signature_vote`, clef reconciliation,
`clef_correction`), and a check layer that already computes agreement. The middle
path is **"confidence + support/exclude between competing readings" applied
locally, not a global graph.**

### Ranked adoptable ideas (highest leverage first)

1. **The contextual-grade formula as a local multi-signal reconciler.** Port the
   ~5-line math `contextual(g, Σ partner·(ratio−1))` (§1.4) as a pure function and
   use it wherever ReEngrave today applies *ad-hoc precedence* among signals that
   bear on one decision: clef = {detector marker, `clef_geometry`, `clef_locator`,
   dossier}; key = {detector accidentals, slot-fit, dossier}; pitch = {y-snap
   candidate, harmonic rerank}. Each signal gets an intrinsic grade and a support
   ratio; combine instead of hard-overriding. This turns "majority ≠ correct"
   (which forced the clef check to abstain) into "confidence-weighted winner." Low
   effort, touches code that already exists (`key_signature_vote.py`,
   `clef_correction.py`). ⚠️ CLEAN-ROOM the *code*; the formula is math, reproduce
   it independently.

2. **Overlap → exclusion → keep-the-stronger, for cross-class YOLO
   over-detection.** Reimplement the essence of `detectOverlaps` +
   `reduceExclusions` (§3.1–3.2) as a small post-detection pass: for two
   detections whose IoU ≥ threshold (Audiveris uses 0.05 general / 0.02 stem-head)
   that are **class-incompatible** (e.g. rest-vs-notehead on the same ink), keep
   the higher-confidence one, drop the other. This is ~30 lines, needs no graph,
   and attacks the documented orchestral failure — the "~100+ dets/cell, mostly
   low-conf rest/notehead FPs" noted in ReEngrave's own labeling guide — with a
   principled rule instead of per-class NMS + conf cutoffs.

3. **Keep competing readings alive one stage longer, so the checks can *select*
   not just *flag*.** `pitch_resolver.pitch_candidates_for_notehead` already emits
   top-N; carry a small `(pitch|duration, weight)` candidate set into rhythm/
   voicing and let `_reconcile_measure_to_meter` (and the theory rerank) **choose
   among candidates** to satisfy the meter, rather than only ±1 a beam level. This
   is the SIG's reduction idea in miniature and generalises the one narrow solver
   ReEngrave already trusts — without a global search Audiveris says doesn't pay.

4. **A tiny explicit support set at the assembly chokepoints, to adjust
   confidence *before* committing.** Model three or four support relations on the
   existing CV signals: notehead↔stem (a head with a stem is more likely real —
   boost; asymmetric like Audiveris's 4 vs 10), notehead↔beam-level, accidental↔
   notehead, clef↔keysig (pitch-compatible → mutual boost). Apply §1.4 to nudge
   detection confidence up/down by structural corroboration, then threshold. Gets
   most of the SIG's cross-symbol reinforcement value with no graph.

5. **One centralized, named grade/threshold table (the `Grades.java` pattern).**
   ReEngrave's thresholds are scattered across modules and env vars; collect them
   into one documented table with an explicit **intrinsic vs contextual** split
   and the "reserve headroom for context" idea (`intrinsicRatio = 0.8`). Cheap;
   makes every subsequent tuning legible.

6. **Adopt the *contract*, not just the checks: attempt assembly, then flag.**
   Audiveris's `finalCheck`/`setAbnormal` flags a measure only after building
   voices/slots (§5.3); ReEngrave flags from a standalone self-consistency test.
   Where feasible, move the confidence-combination (#1–#4) *ahead* of the flag, so
   a flag means "assembly genuinely failed," not "two committed numbers disagree."

7. **Flip part-identity priority toward geometry (`PartCollation` lesson).** Weight
   staff-configuration matching (counts/lines/cue-size) above OCR'd margin labels
   in `contextual.py`, using labels as the tie-breaker — the ordering Audiveris
   chose deliberately for OCR-reliability reasons ReEngrave has already hit.

---

## Appendix — parameter quick-reference (all `[SRC]`)

| parameter | value | file:line |
|---|---:|---|
| `intrinsicRatio` | 0.80 | `glyph/Grades.java:106-108` |
| `minContextualGrade` (purge gate) | 0.50 | `glyph/Grades.java:117-119`, used `sig/SIGraph.java:399` |
| `minInterGrade` / `goodInterGrade` | 0.08 / 0.40 | `glyph/Grades.java:86,89,125-147` |
| `clefMinGrade` / `keySigMinGrade` | 0.03 / 0.01 | `glyph/Grades.java:157-163` |
| contextual grade formula | `(1+c)g / (1+cg)` | `sig/GradeUtil.java:81-85` |
| partner contribution | `partner·(ratio−1)` | `sig/GradeUtil.java:156-160` |
| support ratio | `1 + coeff·grade` | `sig/relation/Support.java:152-179` |
| head/stem support coeffs | 4·consistency / 10 | `sig/relation/HeadStemRelation.java:234-257,715-721` |
| intrinsic grade combine | weighted geo-mean, 0-veto | `sig/GradeImpacts.java:102-120` |
| overlap IoU (general / stem-head) | 0.05 / 0.02 | `sig/SigReducer.java:2379-2385` |
| exclusion resolution | greedy, delete weaker | `sig/SIGraph.java:1232-1301` |
| reduction loop | double fixpoint | `sig/SigReducer.java:1882-1942` |
| voice-distance penalties | INCOMPAT 10000, NO_LINK 60, … | `sheet/rhythm/VoiceDistance.java:99-156` |
| rhythm: FRAT search abandoned | — | `sheet/rhythm/PageRhythm.java:55-73` |
| measure abnormal on mismatch | — | `sheet/rhythm/MeasureRhythm.java:265-282` |
| tie test (same step+octave+accidental) | — | `sig/inter/SlurInter.java:1061-1092` |
| part match = staff config; names secondary | — | `score/PartCollation.java:40-58,185-242` |
