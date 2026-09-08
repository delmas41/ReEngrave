# Assumptions in the staged pipeline

## ⚠️ STATE OF THE BUILD — read this first, and trust it over memory

**If your recollection disagrees with this file, a code tag, or a test, THE
FILE IS RIGHT.** Do not re-derive a settled question from a summary; open the
file. The 129 coherence tests are the real guard — a contradiction of a pinned
decision fails a test instead of passing quietly.

**Wired (15 of 21 decisions).** Unchanged; the gather side beneath them
moved. `system_membership`, `system_staff_count`, `staff_ordinal`,
`measure_partition`, `staff_group`, `group_symbol`, `instrument`,
`slot_index`, `part_partition`, `clef`, `key_signature`, `glyph_owner`,
`tuplet_ratio`, `duration`, `meter`.

**Stubs (6), in priority order:** `arc_owner` → `arc_kind` →
`articulation_owner` → `wedge_anchor` → `dynamic` → `direction`.

**Consequences: 5 wired** (`restate_pitch`, `reconcile_duration`,
`move_glyph`, `respell_accidental`, `name_part`), **1 stubbed** —
`join_parts`, deliberately last, because it is the consequence of the decision
a pre-registered gate already falsified.

**GATHER is now complete except the arcs**: geometry, detections, notehead
positions, ownership evidence, rhythm marks, **the classical-CV stem/beam
rung**, both clef crops, the per-candidate key fit, the meter, margin labels.
Direction text remains a declared stub behind its hard edge.

**Working on right now:** nothing in flight.

**Next, in order — but ⚠️ SEE THE OPEN QUESTION BELOW FIRST:** (1) candidate
sets; (2) redundant groups as first-class; (3) the implication tests over
them; (4) the arc family.

**⚠️ JUDGMENTS FORMED AND NOT YET BUILT** — the only things a memory loss can
destroy, so they are written down rather than remembered:

1. **`tally()` sums everything, and that is wrong for composition.** Agreement
   among witnesses SUMS; a fact composed from inputs is as reliable as its
   WEAKEST input, so it should take a MINIMUM over `composed_from`. Recorded in
   ideal-reader §5.4; not implemented.
2. **`label_contradiction` is the cheapest available win in the whole
   project** — 158 firings over two whole works, hand-adjudicated 0.873 the
   EXPORT is wrong, needs no truth file, and nothing acts on it. It is not
   wired into the staged pipeline at all.
3. **A clef decided by a lone `keysig_slot_fit` clears the floor**
   (`W_KEYSIG_FIT` 1.5 > `MARGIN_FLOOR` 1.0). Deliberate but untested against
   real pages; if it proves too strong, lower the weight, not the floor —
   A-CLEF-6 says the floor carries two jobs.
4. **The redundant groups are still not represented as groups** (ideal-reader
   §4.1) — the largest principle-driven gap, and the one experience did not
   suggest.
5. **`Verdict.detail` AND `Verdict.used` were added on 2026-09-07** because
   `Ruling` filled both and the harness dropped both. ⚠️ The sweep is now a
   standing test (`record_coverage.py`), it is proven to bite by a mutation
   test, and it reports CLEAN — so this specific family is closed for the
   record layer and does not need looking for again by hand.
6. ✅ **CLOSED — the CV stem/beam rung is wired.** `Q.BEAM_STROKE` now has two
   readers and `adjudicate_duration` arbitrates them: a YOLO box is kept only
   where **no CV stroke overlaps its x-range**. ⚠️ Three beam states stay
   distinct on the record — `read`, `none_over_this_note`,
   `reader_declined` — so a duration right *because the beams were read* is
   never confused with one right *because the note was unbeamed*.
7. **`slot_index` makes no document-wide claim on purpose.** It uses the
   system's own ordinal, because `slots.build_reference` picking a lineup from
   one system once named 149 Brahms staves an instrument the work has not got
   — a BAD ANCESTOR that no provenance tag catches. Do not wire the
   document-wide reference without the `OMR_SPAN_REFERENCE_FIT=off` replay.

---

**Nothing in `tools/omr/staged/` has been measured.** Not one accuracy arm has
been run against it. Every ordering, constant and precedence rule below is an
**assumed best practice**, written down so the testing phase can attack it.

That is the point of the list. Sean's instruction for this phase was to build
the whole thing on assumed best practice and record the assumptions rather than
stop to measure; **this file is the record, and it is the input to the testing
phase.**

## ⚠️ EVIDENCE FOR THE ARCHITECTURE, FOUND BY BUILDING IT

**Not a changelog. A bug fixed in a diff disappears; these are arguments, and
they are the answer to "why build before measuring".**

### 1. `duration` sat before `tuplet_ratio`, and duration READS the tuplet

`adjudicate_duration` consumes the tuplet verdict to scale its beats. In the
first `ORDER` list it ran **first** — so the ratio would have arrived too late
and **every triplet would have exported at its written value**: the exact fault
the ratio exists to fix, reintroduced by ordering alone, **in a pipeline built
specifically to get ordering right.**

That is Sean's claim demonstrated on the architecture's own body:

> *"We have the information but not in the right order so it kills or discards
> or miscalculates."*

⚠️ **It was found by WIRING, not by reasoning** — I wrote the ORDER list by
hand, read it twice, and it was wrong both times. And **no measurement would
have shown it**, which is the part that matters: both orders run clean, produce
a full result, and raise nothing. The wrong one is merely *wrong*. A metric
sees a triplet exported at 1.0 instead of 0.667 as a few edits somewhere in a
bar, indistinguishable from a hundred other causes.

**Pinned by `test_the_tuplet_decides_BEFORE_the_duration`.**

### 2. `used` vs `considered` — the gap nothing could previously express

`considered` is what the **harness handed in**; `used` is what the **decision
weighed**. A decision handed ten rows may weigh three.

⚠️ **The gap between them is where a decision quietly ignores evidence it
declared** — which is the shape of every dropped-signal fault this project has
paid for, and until the split there was nowhere to even write it down. It was
itself found by the coverage sweep after `Ruling.detail` turned out to be a
family rather than an instance.

### 3. Two readers, two images, one silent fallback

`line_detection` **prefers** `cell.image_no_staff` and **silently falls back**
to `cell.image` when it is missing. `extract_measures` leaves it `None`. So a
pipeline that forgets `remove_staff_lines` does not fail — **it degrades the CV
rung quietly**, and a whole-rung failure looks like a thin page.

⚠️ And the two images must stay apart: erasing for the detector costs **7–13
pooled reading points**, takes noteheads to **0.774** on Mozart 41, and
**manufactures** beam confusion (YOLO beams 46 → 105, precision 0.783 → 0.343,
firing on staff-line residue). **Erase for the CV consumer, bound the search
for everyone else, never erase for the detector.**

## ⚠️ PRINCIPLE vs CONTINGENCY

Every entry carries a tag, re-derived against
[`docs/ideal-reader-2026-09-07.md`](../../../docs/ideal-reader-2026-09-07.md),
which asks what correctly reading a page requires **from the music rather than
from our components**.

* **PRINCIPLE** — true of reading music, and of any correct reader. Keep it.
* **CONTINGENCY** — true only of the parts we happen to have. Say what would
  make it go away.
* **MIXED** — a principled shape carrying a contingent constant or list.

⚠️ **A principle that arrived through a scar is still a principle.** Several
below are ours by injury and survive on their merits.

⚠️ **The tags are the point of the audit, not decoration.** A list that does not
separate the two cements the second kind into the architecture. **25 entries:
12 PRINCIPLE, 8 CONTINGENCY, 5 MIXED** — and one contingency (A-EVAL-2) is
currently doing a principle's job.

## ⚠️ CHECKABLE vs UNCHECKABLE — where self-correction is possible at all

Every decision in `adjudicate.ORDER` carries `checkable=` / `checked_by=` /
`implicates=` / `composed_from=` **in its decorator**, enforced by
`test_staged_discipline.py`. The reasoning is
[ideal-reader Part 5](../../../docs/ideal-reader-2026-09-07.md); the summary a
builder needs:

* **0 of 21 decisions are purely CHECKABLE. 14 are MIXED, 7 UNCHECKABLE.**
  Checkability is a property of a fact's **consequences**, never of its reading.
* ⚠️ **A failed check is certain about the GROUP and silent about the MEMBER.**
  Nine eighths in a 4/4 bar proves an error and does not say which of the meter,
  a duration, a spurious note, a missing one, or a **mis-owned glyph** is wrong.
  `implicates=` is that membership. **Never condemn the cheapest member.**
* **Weight by kind:** agreement **sums**; composition takes the **minimum** over
  `composed_from` (a chain is as strong as its weakest link); a violated
  constraint is a **negative on every member**; a satisfied one is a **weak**
  positive, because wrong readings pass too. ⚠️ `tally` currently sums
  everything — right for agreement, wrong for composition.
* ⚠️ **Why it matters:** the library pairs a PDF with a reference for **27 of
  235 editions**, and Sean's input is IMSLP scans. **The checkable class is what
  the system can police on the actual work; the uncheckable class will always
  need a reference or a human** — so human attention belongs on the second.

## How to read a row

| field | meaning |
|---|---|
| **id** | cite it when you test or change it |
| **assumption** | what we decided with no measurement |
| **why** | the reasoning, and any existing measurement that merely *informs* it |
| **how to falsify** | the cheapest experiment that would overturn it |
| **blast radius** | what else moves if it is wrong |

⚠️ **A number quoted in a "why" is evidence about the OLD pipeline.** None of
them was re-measured against this one, and several are about a mechanism that
merely resembles ours. Do not promote a "why" to a result.

---

## A-ORDER — what runs when

### A-ORDER-1 · The adjudication order

**MIXED** — the RULE (order binds only on verdict-consumption) is principle; the 21-item LIST is ours.
*`adjudicate.ORDER`*

**Assumption.** Decisions run structure → identity → header facts → ownership →
rhythm → text.

**Why.** Adjudication reads a **frozen** log, so ordering is free for
measurements; it binds only where one decision consumes another's *verdict*.
This order is the assumed dependency order.

**How to falsify.** Permute it. Any pair whose swap changes a verdict has a real
dependency the list does not express — that is a finding, and the fix is to
declare the dependency, not to re-sort by hand.

**Blast radius.** A decision that runs too early sees `State.ABSENT` for a
verdict that would have existed and abstains. It fails **quiet and safe** — the
verdict records `missing`, so the symptom is visible rather than a wrong answer.

### A-ORDER-2 · ⚠️ Identity BEFORE ownership and BEFORE the clef

**PRINCIPLE** — Sean's chain: identity NARROWS the clef, range and transposition.

**Assumption.** The instrument is adjudicated before glyph ownership and before
the clef.

**Why.** This is the inversion the whole split exists for. Today the instrument
arrives **647 lines after the note**, so ownership's strongest tier (the
instrument's written range) is structurally unavailable when ownership runs, and
on a scan it is doubly so — `_staff_written_ranges` returns `{}` with no dossier
and the scan gate is dossier-free by protocol, so **all 4,256 duplicates resolve
on ladder or distance**.

**How to falsify.** Compare ownership verdicts with the identity tier available
and withheld. If the range tier changes nothing, the inversion buys nothing and
the cost of computing identity first is unpaid.

**Blast radius.** Large. It is the ordering claim the architecture rests on.

⚠️ **And identity is a declared STUB**, so today this assumption is *untested by
construction* — the tier it unlocks is not yet computed by anything.

### A-GATHER-1 · Only three gathering edges are forced

**MIXED** — geometry-before-everything is principle; the other two edges are facts about OUR readers.

**Assumption.** Within GATHER only three orderings are real: page geometry
before every reader; detection before direction text; detection before notehead
positions.

**Why.** Verified in the tree during the design: a cell is *defined* by
`staff.line_ys` (`measure_extractor.py:1441-1442` enforces it itself);
`direction_text._blank_detections` (`:301`) erases every detected glyph from the
mask before looking for words; a position is measured from a detection's
y-centre.

**How to falsify.** `verify_order.py`-style static assertion. ⚠️ **The premise
handed to the design said TWO edges and verification found THREE** — do not
inherit this count either. Nine further input edges are listed in the design
document §7.1(3) and none is re-asserted here.

### A-DUR-1 · ⚠️ Duration is a VERDICT, not a measurement

**PRINCIPLE** — a duration is COMPOSED from marks; the marks are measurements, the value is not.

**Assumption.** `Q.DURATION` is adjudicated from `Q.BEAM_STROKE`, `Q.FLAG`,
`Q.AUG_DOT`, `Q.NOTEHEAD_CLASS` and `Q.STEM`; the meter then consumes the
duration *verdict*.

**Why.** Forced by a build-time finding, not chosen. `rhythm.measure_length_beats`
(`:382-390`) sums `ev["duration_beats"]`, `_page_column_lengths` (`:453`) calls
it per measure, and `infer_page_time_signature` (`:467`) votes those lengths —
and `duration_beats` is *written* at `transcribe.py:2335`. The meter vote's
input is the rhythm pass's **output field**. That is a third hard edge, and it
is only survivable because the meter is a decision, so the edge becomes an
adjudication-order constraint.

**How to falsify.** It is not an assumption about the world; it is a reading of
the code. Falsify by showing the vote can be computed from measurements alone.

**Blast radius.** If wrong in the other direction — if duration really is a
measurement — the meter loop is tighter than modelled and `reconcile_duration`'s
bound matters more.

---

## A-GROUP — the grouping decisions

### A-GROUP-1 · An all-zero bracket reading ABSTAINS

**CONTINGENCY** — an artefact of one function writing the same 0 from four branches.

**Assumption.** When every staff of a system reads `group_index == 0`, we record
an **abstention**, not a reading of "one family".

**Why.** `_assign_groups` writes `0` from four different branches — three
refusals (`:596` too small, `:611` no column evidence, `:672` no system) and one
real assignment (`:620`) — plus a fifth path that never calls it at all. On the
old record a refusal and a reading are **byte-identical**, so an all-zero page
genuinely cannot be told apart. Abstaining is the honest reading of an
ambiguous record.

**How to falsify.** Emit the branch from inside `_assign_groups` (the real fix)
and count how many all-zero systems were readings rather than refusals. If most
were readings, this assumption is costing real evidence.

**Blast radius.** `Q.STAFF_GROUP` abstains more than it needs to, so
`Q.GROUP_SYMBOL` falls back to the incumbent rule more often. **Fails toward
today's behaviour**, which is why it is the safe choice while the mirror stands.

### A-GROUP-2 · ⚠️ A brace means ONE PLAYER, so its evidence is the INSTRUMENT

**PRINCIPLE** — a brace states WHO PLAYS, not how many staves.

**Assumption.** `Q.GROUP_SYMBOL` is `brace` when the group's instrument family
is keyboard or harp, `bracket` otherwise, and **abstains with no identity**.

**Why.** All three incumbent sites decide it by **staff count** —
`export.py:681` and `:3523` on `len(staves) == 2`, `:3446` on
`len(slots) == 2`. A bracket block of two staves is *not* a grand staff: Brahms
1 p.1 reads blocks `[2,2,2,2,2,7,1,3]`, five **pairs** that are `2 Flöten`,
`2 Oboen` and so on, and consuming "block of 2" as a brace declares five wind
pairs to be pianos.

**How to falsify.** Count pages whose 2-staff group is a real keyboard against
those whose 2-staff group is a wind pair. Also: find a braced instrument outside
`BRACE_FAMILIES` (organ with pedal is 3 staves; celesta; accordion).

**Blast radius.** With identity stubbed this **always abstains**, so today it is
a pure no-op and the incumbent rule stands everywhere.

### A-GROUP-3 · Grouping is ADDITIVE, never overruling

**CONTINGENCY** — 'additive' presupposes an incumbent; a migration mode, not a permanent one.

**Assumption.** `Q.STAFF_GROUP` and `Q.GROUP_SYMBOL` may only add a fact where
none stood.

**Why.** Informed by a replay over 67 stored transcriptions: consuming the
grouping fact additively changed 20 exports, added 108 bracket groups, kept
braces at 2 → 2 with none lost, and made **zero** content differences outside
the group lines. Letting it overrule would have produced the five-pianos result
above.

**How to falsify.** Run the competitive arm and hand-adjudicate every overturn.

### A-GROUP-4 · ⚠️ The measurement is SILENT on the population the incumbent fires on

**CONTINGENCY** — our reader refuses systems under 3 staves; notation does not.

**Not an assumption — a limit, recorded here so nobody reads a null as a pass.**

`_assign_groups` refuses systems of fewer than 3 staves, so **on a real
two-staff page `Q.BRACKET_BLOCK` cannot speak at all.** The two failure modes
people cite — a two-staff orchestral extract read as a piano, and a real piano
on a crowded page — are different problems, and this evidence can only ever
address the second. A test showing "no change on piano pages" is measuring the
silence, not the fix.

---

## A-CLEF — the clef adjudicator

### A-CLEF-1 · Confidence is a TIER, never a multiplier

**MIXED** — 'an uncalibrated number is worse than none' is epistemic principle; the three bands are ours.
*`CONF_HIGH = 0.60`, `CONF_LOW = 0.30`*

**Assumption.** Detector confidence enters as one of three bands.

**Why.** An uncalibrated probability is worse than none — measured here at
ECE 0.1277, with a top bin promising 0.989 and delivering 0.692. Three bands
because three is what the evidence plausibly supports; a fourth would be
invention. The cut points are **round numbers, not measured gaps**, which is
weaker than this project's usual standard (its good constants sit on measured
plateaus with an empty interval in the middle).

**How to falsify.** Sweep both cut points. If the verdict is flat across a wide
range, they are plateaus and fine; if it moves sharply, they are tuned and the
sweep has found the real boundary.

**Blast radius.** Only the clef.

### A-CLEF-2 · The relative weights

**CONTINGENCY** — ours entirely -- and weighting may be the wrong SHAPE, see ideal-reader Part 4.3.
*`W_DETECTOR_HIGH 3.0`, `W_DETECTOR_MID 1.5`, `W_DETECTOR_LOW 0.4`,
`W_LOCATOR 2.0`, `W_SPECIALIST 1.0`, `W_CARRY 1.5`, `W_INSTRUMENT 1.0`,
`W_DOSSIER 4.0`*

**Assumption.** These express the ordering *external truth > confident detector >
CV locator > carry > instrument prior > weak detector*.

**Why.** The **ordering** is the claim; the numbers are only a way to write it
down. It reflects what the existing chain does implicitly — the detector wins
today at any confidence, the locator is a gap-filler, the dossier overrides.

**How to falsify.** Any permutation that changes a verdict identifies a pair the
ordering actually decides. Test the **order**, not the magnitudes.

**Blast radius.** Only the clef.

### A-CLEF-3 · ⚠️ A floor exists at all

**PRINCIPLE** — a reader must be able to say 'I do not know'.
*`MARGIN_FLOOR = 1.0`*

**Assumption.** A contest closer than 1.0 abstains.

**Why.** **The floor's existence is the change, not its value.** Today there is
no floor anywhere in the clef chain — the measure-cell argmax wins at any
confidence, including 0.11. The reachable improvement is "a staff whose readers
disagree says so".

**How to falsify.** Sweep it. ⚠️ **Read the abstention count, not the score** —
every abstention costs OMR-NED, because musicdiff charges an absent element.

**Blast radius.** Every abstained clef produces **no pitches at all** under
`restate_pitch` (A-EVAL-2). This is the single largest behavioural difference
between the two paths.

### A-CLEF-4 · ✅ CLOSED — `clefC` now names nothing

**PRINCIPLE** — alto/tenor/soprano/mezzo/baritone ARE the same glyph on different lines.

**Was:** a `clefC` detection was read as alto, marked in the code as a
placeholder.

⚠️ **AND IT WAS WORSE THAN "A PLACEHOLDER".** A detector clef at high
confidence weighs 3.0 and the locator's **measured** name weighs 2.0 — so the
placeholder would have **outvoted the only reader that can answer the
question**, and any measurement taken then would have priced the placeholder
rather than the mechanism.

**Now:** `_clef_of("clefC")` returns `None`. A `clefC` contributes **family
support** to whichever C clef the locator named and names none itself; with no
locator reading the clef **abstains** rather than guessing alto.
`Q.CLEF_LOCATED` is wired on **both crops** with `locate_clef(trace=...)`, so a
refusal carries the reader's own branch name.

⚠️ **THIS ENTRY WAS STALE FOR A DAY.** It described `clefC → alto` as live
after the code had closed it — my edit silently matched nothing and I did not
check. *Fixed-then-kept-open-in-prose*, the documentation dual of
detected-then-dropped, in a file three days old. **A tagging pass that only
adds tags would not have caught it; re-deriving each entry against a standard
did.**

### A-CLEF-5 · A `clefC` is worth 1.5 as family support

**MIXED** — 'a glyph naming a family constrains without deciding' is principle; 1.5 is ours.
*`W_C_FAMILY = 1.5`*

**Assumption.** Enough to break a tie between two located C clefs, not enough
to carry one on its own.

**How to falsify.** Sweep it against pages where the locator names two
different C clefs on one staff from the two crops.

### A-CLEF-6 · ⚠️ `MARGIN_FLOOR` carries TWO jobs

**CONTINGENCY** — an artefact of computing margin against a runner-up of 0.

**Found by writing a test, not designed in.** With a single candidate the
runner-up is `0`, so the floor is *also* an absolute floor on a lone reading —
a solitary clef at confidence 0.05 with nothing corroborating it does not take
a staff.

**Why it stays.** It is the right behaviour and matches A-EVAL-2's philosophy.

**How to falsify.** ⚠️ **A sweep moves BOTH behaviours at once** — separation
between two candidates, and sufficiency of one. Report them apart, or the sweep
will attribute one's effect to the other.

---

## A-OWN — ownership

### A-OWN-1 · Tier order, and confidence declared but unweighted

**PRINCIPLE** — a veto on the IMPOSSIBLE and a preference among the possible are not on one scale.
*`W_LADDER_COMPLETE 4.0`, `W_RANGE_IMPOSSIBLE -6.0`, `W_DISTANCE 0.5`*

**Assumption.** Ladder completeness, then the written-range veto, then distance.
`Q.GLYPH_CONF` is **declared in `wants` and must not be weighted.**

**Why.** The order mirrors the existing tiers. The confidence exclusion is
measured on the old pipeline: over 4,521 contested pairs, P(winner conf > loser
conf) = **0.545** against a 0.500 null, and a `|Δconf| > 0` tie-break would
**overturn distance on 45.5% of contests**. It is declared rather than omitted so
a future hand has to decline it deliberately instead of never seeing it.

**How to falsify.** The confidence half is already measured; re-deriving it under
the staged path is the check that it still holds.

**Blast radius.** Stubbed today, so none.

### A-OWN-2 · The range veto reads POSITION + CLEF, not a resolved pitch

**PRINCIPLE** — never consume an interpretation where the mark is available.

**Assumption.** Ownership's range tier consumes `Q.NOTEHEAD_STAFF_POSITION` plus
the `Q.CLEF` verdict.

**Why.** Today it reads `det["pitch"]` (`transcribe.py:3153-3154`), an
interpretation. That is not a cycle *today* — nothing feeds ownership back into
the clef — but it becomes one the moment a clef adjudicator reads ownership.
Declaring both makes the basis record it, so the harness can **see** the loop if
anyone ever closes it.

**How to falsify.** Compare verdicts computed from position+clef against
resolved pitch. They should agree exactly where the clef agrees.

---

## A-EVAL — the third stage

### A-EVAL-1 · The downhill order

**MIXED** — composition HAS a direction (principle); the list is ours.
*`evaluate.DOWNHILL`*

**Assumption.** Consequences flow structure → identity → parts → clef → key →
ownership → pitch → accidental → meter → duration.

**Why.** Assumed. It is checked at **import** — a rule whose effect sits at or
above its cause raises `UphillRule` — so the list is enforced even though it is
unmeasured.

**How to falsify.** Any consequence that genuinely needs to run the other way.
⚠️ **If you find one, do NOT build a fixpoint. Record the tension and
escalate.**

### A-EVAL-2 · ⚠️ An abstained clef produces NO pitches

**CONTINGENCY** — ⚠️ **SUPERSEDED 2026-09-07 BY SEAN'S OWN PROCEDURE.** He neither leaves it blank nor guesses: he narrows from context, TESTS the candidates by what they imply, and falls back to *"the primary simple choice"* only when the test cannot discriminate. So `emit nothing` is not the alternative to `guess silently` — see [ideal-reader Part 4.2](../../../docs/ideal-reader-2026-09-07.md). The three-outcome replacement (decided-by-test / decided-by-convention / abstained) is the one to build.

**Assumption.** `restate_pitch` emits nothing for a staff whose clef abstained.

**Why.** The alternative is the existing behaviour — a positional default,
measured right about half the time (`already_in_effect` 46.7%/53.4%) and
**indistinguishable on the record from a reading**. Producing nothing is worse
for a naive metric and better for a reader who needs to know what we do not know.

**How to falsify.** Count staves that lose every pitch. ⚠️ **This will make
OMR-NED worse and that is expected.** The precedent is `OMR_SLOT_STITCH`:
structurally correct, doubles its named bucket 715 → 1,632, shipped default-off
with the reason recorded. Read `new_abstention` before reading any score.

**Blast radius.** The largest single behavioural difference between the paths.

### A-EVAL-3 · Consequences are events; no `*_final` value is written

**PRINCIPLE** — a record that must be re-maintained by every writer WILL go stale; three did.

**Assumption.** Nothing in EVALUATE writes a value-shaped summary field.

**Why.** A value must be re-maintained by every later writer and the existing
ones were not — `clef_final` 9 of 20 stale, `key_signature_final` 19 of 26,
`time_signature_final` with **no keeper at all**. Two keepers were bolted on
after two fields went stale; that is a shape failing, not three oversights.

**How to falsify.** Find a consumer that genuinely needs the current value and
cannot query for it. (`Log.verdict` is that query.)

---

## A-BUILD — decisions forced by the build itself

### A-BUILD-1 · ⚠️ GATHER is a TRANSLATING layer, not an out-parameter

**CONTINGENCY** — we are not touching the old path.

**Assumption.** GATHER calls the existing readers unchanged and translates what
they *return* into rows, instead of adding a `log` out-parameter to each.

**Why.** The design specified out-parameters, on the tree's own convention that
widening a *return* to carry a record is how a recording change acquires a blast
radius (`transcribe.py:1744-1746`, `:1492-1495`). That is still the right end
state — but the instruction for this phase is **alongside, with the existing
pipeline untouched**, and out-parameters touch a dozen files the old path also
runs through.

**⚠️ THE COST IS REAL.** A translating layer can only record what a reader
*returns*, so a refusal reason living in a local variable can only be
**MIRRORED** — re-derived from the same inputs. Every mirrored row carries
`mirror=True` in its detail so nothing downstream can mistake our re-derivation
for the reader's own word.

**How to falsify.** For each mirror, emit the reason from inside the reader and
compare. Any disagreement is a mirror that was wrong.

**Blast radius.** `Q.BRACKET_BLOCK` and `Q.GAP_BRIDGING` are the mirrors today.
This is the one place the build knowingly owes the design something.

### A-BUILD-2 · `Subject.staff` is SYSTEM-LOCAL

**PRINCIPLE** — a staff's identity within its system is what every join needs.

**Assumption.** Staves are addressed by index **within their system**; the
page-wide index is kept in `detail["page_staff_index"]`.

**Why.** `Staff.staff_index` and `MeasureCell.staff_index` are both "0-based
within the **page**" — system 1's staves continue system 0's count — while every
join in this project must be by position within the system (`draft_windows` says
so, and joining by the page-wide number puts a staff on another instrument's
part). One number, two meanings; the staged pipeline normalises once, at the
boundary.

**How to falsify.** Any page where the mapping is not a bijection.

**Blast radius.** Every subject key. Getting it wrong misfiles every row.

### A-BUILD-6 · An external fact's descendants carry it; a page reading's do not

**PRINCIPLE** — two witnesses derived from one source are ONE witness.

**Assumption.** `Observation.basis` is empty for anything read off this
raster, and non-empty for anything derived from an external document.

**Why.** Forced by the dossier double-count (finding 5 below). The first
invariant — "empty by definition" — made two descendants of one dossier look
like two independent witnesses.

**How to falsify.** Find an external source whose descendants reach one
decision by paths that should NOT be collapsed. (I could not construct one:
if two facts really do come from one document, agreement between them is not
corroboration.)

**Blast radius.** Anything with a `tier`. Today: dossier and roster.

### A-BUILD-4 · The margin-label cascade runs with the FREE rung only

**CONTINGENCY** — a build-phase safety choice.

**Assumption.** `gather_margin_labels` calls `contextual._labels_for_page`
with `surya_fallback=False` and `ocr_fallback=False` by default, so only the
PDF text layer speaks.

**Why.** Conservative for a build phase in which nothing is measured: the
free rung costs nothing and cannot spawn a model. ⚠️ **The A/B must turn both
on to be comparable** — the old path defaults them to `True`, so a shadow run
with them off is comparing a thinner reader against a fuller one and every
`differ` row on a text-layer-less page is an artefact of the flag, not of the
architecture.

⚠️ **And an operational warning for whoever turns them on.** Surya's
keep-alive server is ONE PER MACHINE and `--serve` detaches to ppid 1, so a
stray worker cannot be told from the daemon by parent pid. **Never
`pkill -f llama-server`** — it has already destroyed a sibling agent's
multi-hour transcription. Use `--stop`, or `OMR_SURYA_KEEP_ALIVE=0` for an
unattended run, on the principle that an unattended run should not depend on
shared state it is not allowed to repair.

**How to falsify.** Run both arms on a page with no text layer and count the
labels each rung supplies.

### A-BUILD-5 · ⚠️ An empty stage is an ERROR, not an empty result

**PRINCIPLE** — a stage that produced nothing because nothing loaded is indistinguishable from one with nothing to do.

**Assumption.** `adjudicate.run` and `evaluate.run` raise when their registry
is empty rather than reporting a clean, empty pass.

**Why.** Found during this build, by exactly the route it guards against: a
test imported the adjudicators but not the consequences, EVALUATE reported
`fired: []` / `skipped: []`, **and the empty run read as a pass.** That is the
same shape as `OMR_CONTEST_DUMP` and `locate_clef(trace=)` — complete
recorders that recorded nothing because they were off, with nothing about the
output saying so.

**Blast radius.** None; it converts a silent null into a startup failure.

### A-BUILD-3 · `detector=None` is a supported mode

**PRINCIPLE** — a missing reader is an abstention, not a failure.

**Assumption.** With no weights, every cell abstains `READER_UNAVAILABLE` and
the pipeline runs end to end.

**Why.** It is what lets the whole staged path be exercised in a unit test with
no PDF, no weights and no venv — and it is the honest behaviour on a machine
with no weights file, which today **fails the run**.

**Blast radius.** None: it only makes a failure into an abstention.

---

## ⚠️ Things this build found that are NOT assumptions

Recorded here because they are the opposite — facts discovered while building,
which the tester should not spend time re-deriving.

1. **The host is Python 3.9.6**, so `slots=True` and runtime PEP-604 unions are
   unavailable. No module in `tools/omr` uses either.
2. **The meter vote consumes a written field, not a conclusion** — a third hard
   gathering edge (A-DUR-1).
3. **Pages are NOT independent.** `_ClefContinuity` (`transcribe.py:740`,
   instantiated `:4587`) and `carried_meter` (`:5389-5403`) make page *N+1*'s
   inputs page *N*'s outputs. The claim that every page is assembled
   independently is false, and **nothing here may be parallelised across pages
   without replicating that carry.**
4. **The provenance tag that guards all three circularity refusals is itself
   read through a defaulting `.get()`** — `contextual.py:1298` and `:1451` use
   `instrument_source.get(slot, "label")`, and `"label"` is the one tier the
   refusals admit. Whether the default is reachable is **UNMEASURED**; the shape
   is the hazard.
5. ⚠️⚠️ **THE DOSSIER HAZARD DOES NOT DISSOLVE. IT CHANGES SHAPE — and the
   second shape is worse.** Both halves belong together, and this entry is
   written as one item precisely because **a hazard recorded as "dissolved"
   is exactly the kind of claim that gets quoted later without the second
   half.**

   **The half that really does dissolve — SELF-REFERENCE.** The standing
   warning is that a clef adjudicator must exclude `clef_evidence["dossier"]`
   on a seeded run or it reads back its own seed. That hazard exists because
   the dossier *overwrites a reading* and the reading is then re-read. In the
   staged design the dossier is a row among rows, it overwrites nothing, and
   there is no seed to read back. That half is genuinely gone.

   **The half it becomes — DOUBLE-COUNTING.** If a dossier supplies BOTH the
   clef seed AND the instrument, a clef decision that weighs the dossier row
   *and* the instrument is counting **one source twice**. That is not
   self-reference; it is the other rule — *two signals sharing an ancestor are
   ONE signal, not corroboration* — and it is **more insidious, because it
   looks like two independent pieces of evidence agreeing.**

   ⚠️ **AND IT WAS NOT CAUGHT AS FIRST BUILT.** The design said
   `Observation.basis` is empty *"by definition"*, so a dossier's two
   descendants shared no ancestor and the correlation check saw two
   independent witnesses. **That was a modelling error, and the invariant is
   now narrower and true:**

   > A row read off **this raster** has no ancestors.
   > A row derived from an **external document** carries that document's row.

   `Log.observe(..., derived_from=(...))` is how a descendant carries it, and
   a dangling reference is **refused** rather than silently producing an empty
   closure. `gather_external` therefore runs FIRST in the page loop, because
   nothing can name a row that does not exist yet.

   Pinned by `TestTheDossierDoubleCount` (5 tests, in the same family as the
   three refusal-reproduction tests), including a **control** — a detector
   reading the same clef is *not* correlated with the dossier, because the
   rule must collapse a shared ancestor and not everything that agrees.
   Mutation-tested: dropping `derived_from` fails exactly the three positive
   tests and leaves the control green.

   ⚠️ **A third form is still open and is NOT addressed here:** if a dossier
   seeds the part↔staff **join**, and that join feeds identity, and identity
   feeds the clef, the chain is genuine. That one the filter *does* catch,
   because the join is a verdict with a basis — but it has no test, because
   no join is wired yet.

---

## What would make this list shorter

Every stub in `adjudicate.stubs()` is an assumption-generator: a decision that
does not run cannot have its precedence tested. **13 of 21 decisions and 5 of 6
consequences are declared stubs today.** The fastest way to make this list
smaller is to wire identity — it is the input to four other decisions and the
one whose absence makes A-ORDER-2, A-GROUP-2 and A-OWN-1 untestable by
construction.
