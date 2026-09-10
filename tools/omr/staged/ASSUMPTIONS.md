# Assumptions in the staged pipeline

## ⚠️ START HERE — you are a fresh agent and this file outranks your memory

**If your recollection disagrees with this file, a code tag, or a test, THE
FILE IS RIGHT.** Do not re-derive a settled question from a summary; open the
file. **197 coherence tests** across 12 `tools/omr/tests/test_staged_*.py`
files are the real guard — a contradiction of a pinned decision fails a test
rather than passing quietly.

**What this is.** `tools/omr/staged/` is an alternative OMR pipeline built
ALONGSIDE `tools/omr/transcribe.py`, selected by `OMR_ADJUDICATE`
(`0` default / `shadow` / `1`). Four stages: **GATHER** (readers emit
measurements as rows), **ADJUDICATE** (decisions declare their evidence and
return a value *and* a record), **GROUPS** (redundant groups — N witnesses to
one fact, and whether they agree), **EVALUATE** (consequences, downhill only,
one pass, no fixpoint). Design: `docs/architecture-design-2026-09-07.md`. The
standard its assumptions are audited against:
`docs/ideal-reader-2026-09-07.md`.

⚠️ **NOTHING HERE HAS BEEN MEASURED. Not one accuracy arm has been run.** No
`scan_eval`, no `orchestral_eval`, no OMR-NED. Every ordering, constant and
precedence rule is an assumption recorded below, and the point of writing them
down is that they are what the testing phase attacks.

⚠️ **The existing pipeline is untouched.** `git diff --diff-filter=M
origin/main...HEAD` modifies no file outside `tools/omr/staged/`,
`tools/omr/tests/test_staged_*` and `docs/`.

---

## STATE OF THE BUILD — accurate at the head of `claude/redundant-groups-2026-09-07`

**Nothing is half-finished. Redundant groups landed clean and the session
ended at a green commit.**

**⚠️ REDUNDANT GROUPS ARE IN (`groups.py`), and they are the fourth stage.**
`GATHER → ADJUDICATE → GROUPS → EVALUATE`, surfaced as `result["agreement"]`
and printed by the CLI. **6 redundancies declared, 3 refused with their
reasons, 44 tests, 15 mutations run RED.** ⚠️ **It has NO CONSUMER, on
purpose**: seeing that witnesses disagree is this stage; deciding what to do
about it is D4. That is stated in the module's own docstring so it cannot
become the ninth complete recorder that recorded nothing.

**Decisions: 15 wired of 21** (`adjudicate.ORDER`) — `system_membership`,
`system_staff_count`, `staff_ordinal`, `measure_partition`, `staff_group`,
`group_symbol`, `instrument`, `slot_index`, `part_partition`, `clef`,
`key_signature`, `glyph_owner`, `tuplet_ratio`, `duration`, `meter`.

**Stubs: 6** — `arc_owner`, `arc_kind`, `articulation_owner`, `wedge_anchor`,
`dynamic`, `direction`. Each is a *declared* stub (`stub=True`), abstains with
`ABSTAIN.NOT_IMPLEMENTED`, and its docstring says what it needs. ⚠️ A stub is
fine; a MISSING decision is not, because a missing one is indistinguishable
from one that always abstains.

**Consequences: 5 wired of 6** — `restate_pitch`, `reconcile_duration`,
`move_glyph`, `respell_accidental`, `name_part`. **Stub: `join_parts`**,
deliberately last (D9).

**GATHER is complete except direction text and the arcs**: page geometry,
detections, notehead positions (clef-free, fraction kept), cross-staff
ownership evidence, rhythm marks, the classical-CV stem/beam rung, both clef
crops with the locator's own refusal branch, the per-candidate key-signature
fit, the meter, margin labels via the cascade. `Q.DIRECTION_WORD` is a declared
stub behind its hard edge (D13).

**Run it:**

```bash
python3 -m tools.omr.staged score.pdf --pages 0-2 --weights <file>.pt
python3 -m tools.omr.staged score.pdf --pages 0        # no weights: it still runs
python3 -m pytest tools/omr/tests/test_staged_*.py -q  # 197, seconds, no venv
```

---

## NEXT, IN ORDER — and the order IS the thesis

1. ✅ **DONE — redundant groups** (`groups.py`, was D2). See A-GROUPS-* below.
2. **Implication tests over them** (D4). A composition can be run FORWARD on a
   candidate and its output checked: do these implied pitches fit this
   instrument's range; do these durations sum to this meter. It reaches the
   compositional chain, where *nothing is printed twice* and agreement cannot
   help. It is next because it now has both of its inputs — candidate sets and
   groups — and because it is **the named consumer of the group report**, which
   today has none.
   ⚠️ **AGREEMENT AND IMPLICATION ARE DIFFERENT MACHINES AND THE SPLIT IS
   CLEAN.** `measure_count_warning` is an AGREEMENT check — several staves
   witnessing one bar count — and is now a declared redundancy.
   `rhythm_sum_warning` is an IMPLICATION check — one bar's durations composed
   forward and compared to its meter — and is **not** a group, because a bar
   sum has exactly one witness. Do not look for the bar sum in `groups.py`; it
   belongs to D4, and `Group.implicates` is the field it will reuse.
3. **`join_parts`** (D9), once the partition abstention is priced.
4. **The arcs** — `arc_owner`, then `arc_kind`. Last because they are
   self-contained and nothing else waits on them.

⚠️ **Why groups came before "finish the stubs":** the stubs are *breadth*;
groups and implication tests are *depth on what is already wired*. A sixth
stub adds another decision with no self-check; the groups give the fifteen
already wired a way to be wrong out loud. **And for Sean's actual input —
IMSLP scans, where 27 of 235 held editions have a reference encoding —
internal agreement is the only self-check that will ever exist on the real
work.**

## ⚠️ WHAT A FRESH AGENT MUST NOT DO

**Each of these is a refusal that was paid for. An unrecorded refusal gets
re-tried, and this project has paid for that repeatedly.**

| ✗ do not | because — with the number |
|---|---|
| **Put a probability or calibrated weight on `Candidate.support`** | An uncalibrated probability is **worse than none** — it launders a guess into something that reads as evidence. Measured: **ECE 0.1277**, top bin promising **0.989** and delivering **0.692**, failing worst exactly where a consumer sets its bar. Relative support, **ordered**, is enough. A test asserts the supports do not sum to 1. |
| **Erase staff lines before the detector** | Costs **7–13 pooled reading points**, takes noteheads to **0.774** on Mozart 41, and MANUFACTURES beam confusion: YOLO beams **46 → 105**, precision **0.783 → 0.343**, firing on staff-line residue. The rule is **erase for the CV consumer, bound the search for everyone else, never erase for the detector.** |
| **Union YOLO and CV beams, or replace CV with YOLO outright** | A YOLO box bounds the **stack**, not a stroke, so a union adds a centre in the GAP between two strokes and three sixteenths read as three eighths — union cost pooled **0.1917** against **0.1861**. ⚠️ REPLACE scores **five edits better** and is REFUSED: it throws real beams away and takes notes that lose every beam from **4 to 7**. Keep a YOLO beam only where no CV stroke overlaps its x-range. |
| **Retrofit every decision to emit candidate sets** | Only beams and the clef are natively set-shaped. **A decision that genuinely has one answer must not be dressed as a set to look uniform.** |
| **Use detection confidence to break an ownership tie** | P(winner conf > loser conf) = **0.545** against a 0.500 null, and a `|Δconf| > 0` tie-break would **overturn distance on 45.5%** of 4,521 contests. It is in `wants` so it must be declined *deliberately*, never merely unseen. |
| **Resurrect `clef_register_warning`'s adjacent-staff form** | Reach **7 of 193** scan staves, precision **0 of 11** — every firing a family boundary, because an orchestral score is ordered by **family, not register**. The self-contained per-staff form (`propose_clef`) is a different thing and is fine. |
| **Count ledger rungs instead of testing completeness** | Two broken ladders are **not** evidence either way: a found rung can belong to the other staff's note exactly as a gap can. On the Beethoven bassoon pair the ghost's one rung WAS the real C4's own ledger, and counting beat the real note. |
| **Delete the loser of a contest** | `move_glyph` **supersedes**. Arc attribution measured `drop` at **2,388 vs 2,371** — better arm-for-arm — and refused it, because it got there by emitting **20 fewer slurs, 12 of them real**. Keeping the loser addressable is what lets a later identity correction reach it. |
| **Widen `_reconcile_measure_to_meter`'s bound** | It repairs only when the answer is **UNIQUE** — i.e. it declines exactly when more than one member could explain the failure. That is "certain about the GROUP, silent about the MEMBER" implemented. **Never condemn the cheapest member to change.** |
| **Let a key signature be fitted against a guessed clef** | Three flats fitted against a guessed clef came back as **TWO SHARPS**. GATHER asks the reader once per *candidate* clef; the adjudicator reads the answer for the clef that won, and abstains if none did. |
| **Declare a redundant group over a quantity that merely LOOKS printed twice** | Three are refused at the head of `groups.py` with their reasons. The sharpest: a KEY SIGNATURE across the staves of one system, where transposing instruments genuinely carry different written keys at the same bar — a B-flat clarinet in a 3-flat movement is `fifths: -1`. `key_signature_corroboration` says it outright: *"the other staves read something else" is not evidence of anything.* What IS redundant across a system is a key change's POSITION, not its value. |
| **Read a group's `dissenting` as "the member that is wrong"** | It is the plurality's complement and nothing more. `suspects` — EVERY witness, majority included — is the implicated set, and a SPLIT names no dissenter at all. `_reconcile_measure_to_meter` is the tree's one correct implementation of this: it repairs ONLY when the answer is UNIQUE, i.e. declines exactly when more than one member could explain the failure. |
| **Reuse `adjudicate._one_signal` for a group's witnesses** | It matches on `(reader, frame, quantity)` and is SUBJECT-BLIND. That reads correctly inside a decision, whose evidence is almost always about one subject — and a redundant group is the opposite case by construction, so it would collapse a whole system's twelve-staff meter vote into ONE witness. `groups.one_signal` adds `subject` to the key; the divergence is pinned by a test so unifying them is a decision, not an accident. |
| **Build the systematic version of a fix mid-stream** | Scope rule: **FIX NOW only if it corrupts the thing being built; PARK everything else — and the systematic version of a fix is a PARK even when the instance is a fix-now.** A borderline case is a PARK, not a judgment call. |

---

## ⚠️ DEFERRED — parked, with the evidence kept

**The rule (Sean, 2026-09-07):**

> **FIX NOW** only if it corrupts the thing being built — a defect in this
> pipeline's own substrate propagates into every decision wired after it.
> **PARK** everything else. ⚠️ **The systematic version of a fix is a PARK
> even when the instance is a fix-now**: correct the instance, park the
> checker. ⚠️ **A borderline case is a PARK, not a judgment call** — parking
> is reversible in one message and a detour is not.

**The test is not "is this real".** Everything below is real; that is what
makes it tempting. **The test is: does the BUILD get worse if I wait?**

⚠️ **A parked item keeps its evidence.** The cheap half of a find is the
observation and the expensive half is the fix — a park that loses what was
seen is a deletion with extra steps.

| # | what | why parked | what it would take |
|--:|---|---|---|
| D3 | **`tally()` should take a MINIMUM over `composed_from`** | ideal-reader §5.4. Wrong *weighting*, not a wrong *record* — no verdict is corrupted, so waiting costs nothing | agreement SUMS; composition is as strong as its weakest link. `composed_from` is already declared on all 21 |
| D4 | **The implication tests as consumed terms** — `propose_clef`'s range test per candidate; `rhythm_sum_warning` given a consumer | needs D1 and D2 to be worth doing properly | ideal-reader §4.6 |
| D5 | **GATHER out-parameters instead of the translating layer** | A-BUILD-1. The end state, but it touches a dozen files the OLD path runs through — the opposite of "alongside" | a `log` kwarg per reader; deletes the `mirror=True` rows |
| D6 | **`Q.BRACKET_BLOCK` / `Q.GAP_BRIDGING` are MIRRORS**, re-derived rather than the reader's own word | the mirror is honest and marked; converting it is D5 | `_assign_groups` emitting its own branch |
| D7 | **`Mode.ADDITIVE` needs an expiry** | A-GROUP-3: correct while an incumbent exists, should not calcify | a decision, not an edit |
| D8 | **The six remaining stubs** — `arc_owner`, `arc_kind`, `articulation_owner`, `wedge_anchor`, `dynamic`, `direction` | ordinary remaining work, not a deferral of a fix | each is a declared stub and says what it needs |
| D9 | **`join_parts` consequence** | blocked: it is the consequence of the decision a pre-registered gate falsified, and `adjudicate_part_partition` correctly abstains there | pricing that abstention first |
| D10 | **Document-wide slot reference** | blocked: `build_reference` picking a lineup from one system once named 149 Brahms staves an instrument the work has not got | the `OMR_SPAN_REFERENCE_FIT=off` replay |
| D11 | **`W_KEYSIG_FIT` (1.5) exceeds `MARGIN_FLOOR` (1.0)**, so a lone key-signature fit decides a clef | a weight, not a defect; changing it without evidence is guessing twice | a sweep, once measuring is allowed. ⚠️ Lower the WEIGHT, not the floor — A-CLEF-6 says the floor carries two jobs |
| D12 | **Asking the locator per candidate clef costs 4 calls per staff** | correctness first, and the shape is right (ask every candidate, including ones that never proposed themselves) | measurement, then caching if it bites |
| D13 | **Direction text gather** | a declared stub behind its hard edge (it subtracts every detection from the ink) | wiring `direction_text.find_candidates` after detection |
| D14 | **`BEAM_EDGE_TOLERANCE_WIDTHS = 1.0`** — how far past a stroke's end a notehead may sit and still *maybe* be under it | a constant with no measurement behind it; it decides how often a duration NARROWS rather than decides | a sweep once measuring is allowed. ⚠️ Too small and the set never forms; too large and every note narrows |
| D15 | **A NARROWED verdict has no exporter** | nothing exports yet, so it costs nothing today — but MusicXML has no way to say *"one of these two"* | a decision about what a narrowed fact serialises as. ⚠️ **Do not resolve it by silently taking `candidates[0]`** — that is the collapse this whole feature removed, moved one stage later |
| D16 | ⚠️ **`adjudicate._one_signal` is SUBJECT-BLIND, so `Verdict.correlated` is wrong on any decision that reads across subjects** — `adjudicate_meter` reads `Q.METER_TEMPLATE` with `SELF_AND_DESCENDANTS`, so every meter verdict records all twelve staves as ONE signal | **INERT TODAY, and only just.** The two decisions that pass `correlated=` into `tally` (`clef`, `glyph_owner`) both read a single subject, so no weight is currently wrong. What is wrong is the RECORD. Parked because the fix touches `adjudicate` and every verdict's `correlated` field — the systematic version of a fix, which is a PARK by the rule even when the instance is real | add `subject` to the Observation key, as `groups.one_signal` already does, and re-run the suite. ⚠️ **The moment any decision reading across subjects starts consuming `correlated`, this becomes a live defect** — flag it to whoever wires one |
| D17 | **Cross-READER groups** — the detector's `Q.METER_GLYPH` and the template reader's `Q.METER_TEMPLATE` are two witnesses to one meter and are not joined | a group needs one `reading` function, and those two value shapes are a SMuFL name (`timeSig4`) and a pair `(4, 4)`. Mapping one onto the other is a DECISION, not a group — and the two readers are documented as COMPLEMENTARY (`timeSigCommon`/`timeSigCutCommon` are the two the detector reads well and the template library has no digits for) | a declared normalisation per reader pair. ⚠️ Cross-reader agreement is plausibly the most valuable kind, so this is a park worth reopening early |
| D18 | **The key CHANGE group** — a mid-staff key change is corroborated by another staff of the same system changing at the SAME BAR | blocked on a row: nothing emits a mid-staff key change as a measurement, so the group would have nothing to assess. The value-across-systems group that IS declared cannot substitute — it compares values, and a genuine change shows up there as a disagreement | a `Q.KEY_SIGNATURE` row at cell scope, then a redundancy whose `reading` is the CHANGE POSITION and not the value. `key_signature_corroboration` has the witness argument already worked out, including why it is the WEAKER and therefore usable claim |
| D19 | **A group's `silent` members are placed best-effort** — a subject that produced no row is keyed through `_PhantomRow`, which carries only its subject, and a `fact_key` needing more raises and files it as unplaceable | correct by construction (it never guesses a subject into a group it may not belong to) but it means a silent staff with no `slot_index` verdict is invisible to the part-scoped groups | either emit a slot verdict for every staff, or key the silent set from the subject tree rather than from the fact function |
| D20 | **GATHER reads key signatures with `key_signature_locator` ALONE — the weaker of the two readers this repo has, by a margin measured on the very page the first shadow run used.** `gather.py:982` imports `locate_key_signature`; `key_signature_template` is referenced nowhere under `tools/omr/staged/`, while `transcribe.py:272` imports it and `transcribe.py:1521` records *"the locator reads 2 of 12 staves given the correct clef and this reads 11"* on Beethoven 5 p.1 | it is a READER swap with a MEASURED precedence rule attached, so doing it without the precedence would ship a regression the old path already priced. Not a defect in anything written here — every verdict the locator produced is correctly recorded and correctly reasoned | port the template reader as a SECOND witness with its own `reader=`, and express *gaps only* as a declared precedence in `adjudicate_key_signature`, not as an `if read is None` chain. ⚠️ **It may not simply win**: it is the one source here that can OVER-count, and letting the fuller reading take it gains 1 staff on Beethoven 5 p.2 and 2 on the Pastoral and costs a WRONG reading on WTC I p.17. Evidence and the run that found it: `benchmarks/omr-staged-shadow-2026-09/FINDINGS.md` |
| D21 | **The key-signature-across-a-system group is refused for a reason that only covers TRANSPOSING staves** (`groups.py:97`), and the rest of the system is left unwitnessed. Sean, 2026-09-08: only transposing instruments may disagree with the concert-pitch ones; and given the key by consensus plus a known transposition the WRITTEN signature is DEDUCIBLE, so a transposing staff becomes predicted-and-checkable rather than merely excluded | not a defect — a declared refusal being narrower than it looked, plus new capability on top. Parked because it needs a group, a `Q` for the deduced key, and a precedence, and because the measurement is 149 scores | ⚠️ **Three constraints, all measured, all cheap to get wrong.** (a) The witness set is `chromatic % 12 == 0`, NEVER `== 0` — Contrabass is −12, an OCTAVE transposition that does not change the key, and the naive form drops the bass. (b) A third category exists beside transposing/not: **natural brass and timpani print NO signature by convention** — on Beethoven 5 p1 the concert-pitch set splits 8 to 2, so MAJORITY survives and UNANIMITY does not. (c) Genuine counter-examples exist and are nameable: bitonality (Holst's Mercury, measured) and scordatura (Mahler 4 mvt 2, not in corpus). ⚠️ **EVIDENCE, NOT REPAIR** — on the Viola a consensus fix would have produced the right answer for the wrong reason and hidden D20, whose box sits outside the system's accidental band. `fifths_offset` already exists and predicts 10 of 12 on that page. Full reading: `benchmarks/omr-string-key-agreement-2026-09/FINDINGS.md` |

⚠️ **D1 (candidate sets) and D2 (redundant groups) were CLOSED and have LEFT
this table**, per the rule `export_coverage` already applies: an entry that is
closed must leave, or the list stops describing the code and starts describing
its history. D1's argument is build finding 4 below; D2's is `A-WIT` and
`groups.py`'s own docstring.

⚠️ **RETRO-APPLIED, INCLUDING TO MYSELF.** Under this rule two things I did
mid-stream were parks, not fix-nows:

* **`record_coverage.py`** — the coordinator commissioned it and has named it
  drift. Fixing `Verdict.detail` and `.used` was fix-now (they corrupt the
  substrate: every verdict wired afterwards would inherit the loss). **Building
  the checker and its mutation test was the systematic version and should have
  been D-something.** It is built, passing, and kept — and it is the last thing
  of its kind built mid-stream.
* **`subjects_from`** — added while wiring ownership because a verdict per
  detection would bury 4,521 contests under tens of thousands of no-ops. ⚠️
  **Borderline, therefore a PARK under the rule**, and I did it inline. The
  build was noisy without it, not wrong. Recorded here as an honest miss.

**Applied correctly as FIX-NOW, with the criterion:** the `ORDER` inversion
(every later duration inherits an unscaled triplet), `Verdict.detail`/`.used`
(every later verdict inherits the loss), and `remove_staff_lines` missing from
`prepare_pages` (**every** duration built on a silently-degraded beam rung).
All three corrupt the substrate; none could wait.

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

### 4. ⚠️ We reproduced `pitch_resolver.py:181` ON PURPOSE, one layer up

`_beam_levels` counts the strokes covering a notehead's column and returns an
**integer**. Where a stroke's x-range ends near the note the honest reading is
*"two, possibly three"* — and that alternative is destroyed at the moment of
counting, exactly as `pos_float` is computed at `pitch_resolver.py:180` and
rounded away at `:181`.

⚠️ **This is the most damning of the four findings, because we did it while
trying not to.** The thesis of the whole architecture is *keep the
measurement, move the decision*; the new code kept the measurement (strokes
with x-ranges are rows) and then collapsed the **interpretation** to a single
value at the first opportunity, which reintroduces the same loss one level
higher. The duration composed from it inherits a precision the reading never
had.

**Fixed by candidate sets** — `Outcome.NARROWED`. Recorded here rather than
only in a diff, because the lesson is that *keeping the measurement is not
sufficient*: a decision that collapses early throws away just as much, and it
is harder to see because the row underneath still looks intact.

### 5. A silent fallback turns a whole-rung failure into a thin page

`line_detection` **prefers** `cell.image_no_staff` and falls back to
`cell.image` without complaint. So a missing erased variant does not fail — it
degrades the entire CV rung quietly, and the page presents as sparse.

⚠️ **The incumbent already learned this from the other direction.**
`_optional_pass_failure` exists because an optional pass that *abstains* and
one that *fails like a defect* were indistinguishable, and a renamed parameter
went dark for hours behind an honest-looking "unavailable". Same lesson,
arrived at independently in new code: **not-raising is not the same as
not-telling-anyone.**

### 6. A consequence whose CAUSE was coarser than its EFFECT was silently dead

`reconcile_duration` acts on a **cell**; the meter is decided at **system**
scope. The exact-subject lookup found nothing, so the rule reported
`cause_absent` and did nothing — **identically to a page that prints no
meter.** Every consequence with a coarser cause was dead the same way.

⚠️ **Found by a test refusing to fire, not by reading.** And it is the
abstention/defect distinction again, a third time: *nothing raised, nothing
logged, and the output was indistinguishable from a legitimate silence.*

### 7. ⚠️ The no-fixpoint guard forbade the one revision the design permits

`Log.record` refused any verdict that superseded something appearing in its own
`basis`. **But a revision READS WHAT IT REVISES** —
`reconcile_duration` takes the old duration's written value and re-reads its
beam level — so the guard refused *every revision there can be*, and the
pipeline's single bounded loop could never fire.

The real fixpoint is deriving the new value **through something that itself
depends on the old one**: if the meter were voted out of these very durations,
then meter → duration → meter is a cycle and no bound saves it. The check now
excludes the superseded verdict from its own closure test.

⚠️ **The lesson is about safety rails, not about this rule.** A guard tight
enough to be provably safe was tight enough to be useless, and it looked
correct for four days because nothing exercised it. **A rail nothing has driven
into is an untested rail** — and the test that pinned it was pinning the wrong
rule, so it passed too.

### 8. ⚠️ "One signal" is not a global predicate — it INVERTS between a decision and a group

`adjudicate._one_signal` calls two Observations one signal when
`(reader, frame, quantity)` match. Inside a decision that is right: a
decision's evidence is almost always about ONE subject, so the triple reads as
*the same reader on the same crop*, and it is what stops the two clef crops
being counted twice.

**A redundant group is the opposite case by construction.** Its witnesses are
twelve different staves, read by one reader, on one KIND of crop — so the
triple matches for all twelve and the identical predicate would collapse an
entire system's meter vote to ONE witness, reporting `SINGLE` on the
strongest agreement the page can offer.

⚠️ **Same code, same rows, opposite correct answers.** What changed is not the
evidence but the QUESTION: correlation is relative to what the rows are being
compared *for*. `groups.one_signal` adds `subject` to the key and the
divergence is pinned by a test, so unifying them later is a decision rather
than an accident — and D16 records that the adjudicate side is wrong on its
own terms too, inertly, in `Verdict.correlated`.

### 9. ⚠️ A WALL OF AGREEMENT IS THE SAME NULL AS A WALL OF ZEROS

The first smoke run of the group stage produced a healthy-looking table: six
facts for `clef_across_systems`, six `SINGLE`; six for
`instrument_across_systems`, six `NONE`. Nothing in it said *"four of these
five redundancies corroborated precisely nothing"* — and `SINGLE` and
`UNANIMOUS` both read, at a glance, as *no problems found*.

This project already knows that **a zero is a suspect, not a result** — seven
plus probes have printed clean tables of zeros at exit 0. The new form is
worse, because the number is not zero: `n_facts: 6` looks like coverage.
**The quantity that matters is not how many groups agreed but how many had TWO
INDEPENDENT SIGNALS to agree with**, and until `Group.uninformative` and the
report's `checked_nothing` list existed, that number was computable and
uncomputed.

⚠️ Generalised, and worth carrying past this module: **a check reports three
things — it passed, it failed, and it could not run — and a check that could
not run must never be counted in the first bucket.** The five internal
consistency checks fail this test today from the other direction (85 warnings,
all inert); this one would have failed it from the agreement side.

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

### A-DUR-2 · ⚠️ A carried meter is WEIGHED by the bars, not gated

**PRINCIPLE** — self-checking arithmetic outranks inherited information.
*`rhythm._corroborate`, `W_METER_CARRIED`, `W_METER_BAR_FITS`, `METER_CARRY_FLOOR`, `METER_CARRY_MIN_BARS`, `OMR_METER_CARRY` (default `0`)*

**Assumption.** A system that read no usable meter may take the last meter
that was READ, as a CANDIDATE; every bar of that system then adds `+1.0` if it
fits and `-1.0` if it does not, against a floor of `2.0` and a minimum of two
assessable bars. Only a `voted` verdict is a source, so a carry never chains
onto a carry and `pages_since_read` is the true distance back to ink.

**Why.** A meter is a fact of the MOVEMENT, printed at its start and nowhere
else, so a page-at-a-time pipeline has none from a movement's second page on.
Sean, 2026-09-09: *"If the measure is what we think it is - does the math of
the notes make sense. If not then the meter should decrease in probability."*
So the bars do not veto, they move its standing — and the movement-boundary
problem dissolves, because a new movement's bars simply contradict the old
movement's meter. Measured on Beethoven 5 / Litolff `984073`: page 2's two
systems carry at +7.0 and +8.0; **all three systems of the *Andante* (page 17,
truth 3/8) refuse the carried 2/4**, at -3.0, -1.0 and too-few-bars — with no
movement detector anywhere.

⚠️ **THE ORDERING IS STRUCTURAL, NOT TUNED.** Two net contradicting bars
outweigh ANY carry and no carry outweighs the bars. Asserted on the constants
themselves, so a sweep that breaks the ordering fails even if every
behavioural test still passes.

⚠️ **NOT A PROBABILITY.** `adjudicate` bans them on measurement — calibrated
identity probabilities reached ECE 0.1277 and failed worst at the top of the
range. Signed terms are the same shape without the claim. ⚠️ But that
objection was diagnosed as the CORPUS, and a bar sum is CHECKABLE against
itself with no truth file, so this family could be genuinely calibrated later.

⚠️ **A LONE WHOLE REST IS NEVER READ HERE** — it stands for the bar whatever
the meter and its 4.0 is our own default, so it would read that default back
as evidence (left in, 13 of 17 agreeing bars vote 4.0 on the Andante); and it
is what `size_measure_rest` supersedes, so touching it makes the record report
a genuine fixpoint.

✅ **THE OPEN QUESTION IS ANSWERED, 2026-09-09** — *"a movement boundary on a
page that READS WELL is unmeasured"*. It was the wrong name for the case: this
decision never asks whether a movement started, only whether the carried meter
FITS. On p.63 of the same document (mid-Finale, carried `2/4` from p.1,
printed `3/4`) the carry is refused at **−6.0** (1 agree / 8 disagree) and
**−7.0** (0/8), and the same bars name **3.0 at +5.0** — so the refusal there
IS discriminating, unlike the *Andante*'s. ⚠️ A movement-START page remains
unmeasured and **this document has none that reads well** (p.17 / p.32 / p.44
all fail, for opposite reasons: sparse opening vs dense tutti). See
`A-DUR-7` and `benchmarks/omr-staged-meter-from-bars-2026-09/FINDINGS.md` §4b.

**How to falsify.** Find a document where the bars corroborate a meter that is
wrong, or contradict one that is right. The weights are the place to look:
they are symmetric and DECLARED UNMEASURED, because the two pages available
separate under every ratio tried.

**Blast radius.** Bounded by the flag, and self-limiting even with it on: a
carry the bars refuse simply abstains, which is the status quo. Still `0` on
**n** — one document — not because the hazard is unhandled. See
`benchmarks/omr-staged-meter-carry-2026-09/FINDINGS.md`.

### A-DUR-4 · ⚠️ A meter governs a RANGE OF BARS, and the glyph opens a change

**PRINCIPLE** — Sean, 2026-09-09: *"I don't want the dichotomy of it's a system or a group of notes surrounding it. It is both."*
*`record.meter_at`, `rhythm._meter_changes`, `W_CHANGE_GLYPH_PAIR`, `METER_CHANGE_FLOOR`*

**Assumption.** A `Q.METER` verdict's value carries `segments` — one entry per
stretch of bars, each with the `from_cell` it starts at. A change is proposed
only where a time-signature GLYPH stands at that bar; the bar math then
confirms it, refuses it, or chooses between staves that read it differently.

**Why.** Measured on Beethoven 5 / Litolff p.62, which prints a mid-system
change to 3/4. The page prints bar 147, so the reference's change at bar 155 is
CELL 8 — and the detector's `timeSig3`+`timeSig4` land on cell 8 **exactly**,
while the bar-math anomaly sits at cell 6, two bars early and wrong. **The
glyph is the precise signal; the arithmetic is the noisy corroborator.**

⚠️ **ONE FACT, NOT TWO.** Adding a separate "there is a change at bar N" fact
beside an unchanged system meter was refused on this project's own history: two
records of one thing that nothing forces to agree is what let an accuracy
figure go stale in three of four places.

⚠️ **A CHANGE-ONLY VERDICT IS A REAL ANSWER.** p.62 reads a usable meter on 2
staves of 17, far under the coverage floor, so the system abstains — and a
system-scoped meter would have had nowhere to put the 3/4 its print states
plainly. As segments it says the true thing: *unknown until bar 8, 3/4 from
there*. `meter_at` returns None for a bar no segment covers.

⚠️⚠️ **A CHANGE TO A LETTER METER WAS INVISIBLE, AND 23 OF 23 STAVES DETECTED
IT.** `_meter_from_digits` required two stacked digits and skipped
`timeSigCommon` — *"timeSigCommon and friends: no pair"* — so the caller
counted it as a `loose` glyph, built no `readings` entry and skipped the bar.
Found on the engraved fixture (`A-DUR-8`), where LilyPond spells 4/4 as `C`:
`meter_glyph` = 23 rows, all `timeSigCommon`, all at the right cell, and the
system abstained `no_evidence`. **Perfect detection dropped by the rule.**
Fixed by `rhythm._meter_from_letter` — **a sibling session's, landed first**;
a second session reached the identical finding from the same bar and its
duplicate implementation was deleted in favour of theirs, which additionally
abstains where one staff reads BOTH letters. Digits still win where both are
present, and the letter reaches `raw` because — unlike a BORROWED spelling —
the glyph was matched here.

⚠️ **A PROPOSED METER MUST BE ONE THE REPERTOIRE PRINTS.** Without the gate,
p.61 produced a confident change to **1/1** at support 5.0 out of `timeSig1`
detections. The list is `time_signature_locator.DEFAULT_METERS`, imported.

**How to falsify.** A printed change the glyph does not mark, or a glyph-marked
bar that is not a change. ⚠️ **The second half is barely tested**: the bar-math
corroborator contributed `0 fit / 0 not` even on the case that works, because
the whole-rest exclusion removes exactly the post-change bars (a change is
typically followed by most instruments resting).

**Blast radius.** n = 1 change, 1 document. Controls are clean (pages 0-2 and
p.17 report one segment and no change), but one true positive is one.

### A-DUR-7 · ⚠️ The bars name a LENGTH; only ink names the ENGRAVING

**PRINCIPLE** — a decision may propose only what its evidence can distinguish.
*`rhythm._bars_opinion`, `_form_for_length`, `_meter_from_bars`, `METER_FROM_BARS_FLOOR`, `_METER_LENGTHS`, `OMR_METER_FROM_BARS` (default `0`)*

**Assumption.** A system that read no meter and could not carry one may take
the bar length its own bars agree on, scored in the carry's currency (`+1.0`
per bar that fits, `-1.0` per bar that does not, floor `4.0`). The printed
FORM is borrowed from the nearest preceding system whose meter was `voted` AND
whose length already matches; where none exists the decision abstains
`bars_name_a_length_without_a_form`, recording the length, the support and
every spelling that length could be.

**Why.** A bar sum is a length in quarter-notes and a meter is a length AND an
engraving: 2.0 is `2/4` and `4/8`, 3.0 is `3/4`, `6/8` and `12/16`. The
arithmetic cannot separate them because it is the same arithmetic. Sean:
*"If there is no established meter then it must derive the most likely meter
based off of the order of determination above"* — so the half that can be
derived is derived and the half that cannot is refused, not guessed. ⚠️ The
guess is not free: `raw` reaches `staged.export` as `symbol="common"`, a
positive claim that a `C` is PRINTED on a system that printed nothing we could
read. The letter is therefore **never** borrowed even when the numbers are.

⚠️ **IT CANNOT CROSS A MOVEMENT BOUNDARY, and that is what makes it a
different mechanism from the carry rather than a second copy.** Every term
comes from bars inside one system, so the *Andante* cannot be handed movement
1's `2/4` by this route however many pages of it precede — its four assessable
bars read four different lengths and it scores **-2.0**. Only the SPELLING
reaches back, and only where the length already matches.

⚠️ **"FOR 6 MEASURES" IS NOT A RUN.** Measured over 24 systems, the longest
CONSECUTIVE run of assessable bars is 5 where the meter is read, 3 where it is
wanted and 1 on the dense finale pages — because an unassessable bar breaks a
run without contradicting anything, which is a fact about legibility, not
meter. So the length of the evidence is expressed by the terms ACCUMULATING,
not by a run-length constant.

⚠️ **ONE CONSTANT, AND A SECOND WAS DELETED FOR BEING INERT.**
`METER_FROM_BARS_MIN_ASSESSABLE = 4` was written on `METER_CARRY_MIN_BARS`'s
two-questions reasoning and **a mutation arm proved it could not fire** — a
bar is worth 1.0, so the floor of 4.0 already implies four assessable bars.
Deleted rather than left as decoration: a gate that cannot fire reads as a
protection that is not there.

⚠️⚠️ **A REFUSAL MAY NOT BLOCK A LATER RUNG, AND THE `or`-CHAIN LET IT.**
`_carry_meter` returns a `Ruling` when it decides AND when the bars outweigh
it, both truthy, so `a() or b() or c()` stopped at a refusal — the bar reader
unreachable behind the refusal it had itself caused, at exactly the case both
mechanisms exist for. `_meter_fallbacks` orders the rungs by what each KNOWS
(corroborated carry → this system's own bars → a printed change → the most
informative refusal, **not the last one tried**). ⚠️ Half the gap predates
this entry: `_change_only` sat behind the same `or`, so a refused carry also
suppressed a meter change printed on that system.

⚠️⚠️ **"A MOVEMENT BOUNDARY ON A PAGE THAT READS WELL" WAS THE WRONG NAME FOR
THE OPEN CASE.** The mechanism never asks whether a movement started, only
whether the carried meter FITS. Measured on p.63 (mid-Finale, carried `2/4`,
printed `3/4`): the carry is refused at **−6.0** (1 agree / 8 disagree) and
the same bars name **3.0 at +5.0** — a wrong meter refused and a right length
named on one well-read page, which is the discrimination the *Andante* could
not give. ⚠️ A movement-START page specifically is still unmeasured **and
this document has none that reads well**: all three were located (p.17, p.32,
p.44) and all three fail, for OPPOSITE reasons — an opening is either sparse
(most instruments resting) or a dense tutti. The remaining route is engraved.

**How to falsify.** A page whose bars coherently agree on a length that is not
its meter — most likely one where a systematic duration misread is shared by
every staff, which is the correlated-evidence hazard `A-DUR-6` names. The
per-bar cross-staff majority is the only thing standing against it, and it is
weaker than it looks: bars on one staff share that staff's beam and clef
regime, so they are not fully independent witnesses.

**Blast radius.** Bounded by the flag, and self-limiting with it on: it is
reached only where the reading AND the carry have both already failed, so it
can overturn nothing. ⚠️ **On the one document available it never reaches its
DECIDED branch on a page the carry does not already serve** — the two systems
it newly speaks for (p.63) name 3.0 with no `voted` 3.0 anywhere to spell it,
so they take the abstaining branch. See
`benchmarks/omr-staged-meter-from-bars-2026-09/FINDINGS.md`.

### A-DUR-8 · ⚠️⚠️ BAR SUMS WERE WRONG ON PERFECT INK — ✅ CLOSED on one engraved document

**MEASUREMENT, not a design decision.**
*`benchmarks/omr-staged-meter-engraved-2026-09/`, `render_meter_change.py`, `hide_change_signature.py`*

**What was measured.** `beethoven-sym5-mvt4` bars 203-218 rendered through
LilyPond — 23 parts, every part playing in every bar, ink perfect by
construction — changes to 4/4 at bar 209. **Assessable bars only** (the ones
that reached the quorum and are therefore the mechanism's own answers):

| system | truth | assessable | read |
|---|---|--:|---|
| bars 203-205 | 3/4 | 3 of 3 | **3.0, 3.0, 3.0** ✅ |
| bars 206-214 | 3/4 → 4/4 at cell 3 | 4 of 9 | 3.0 ✅, **4.0 at 20/23** ✅, **3.5 (18/23)** ✗, **6.0 (20/23)** ✗ |
| bars 215-218 | 4/4 | 1 of 4 | **4.5 (12/23)** ✗ |

**Three of five assessable bars on the two dense systems are wrong**, and not
by ties or near misses: 18 of 23 staves agree on 3.5 against a truth of 4.0.

**Why it matters.** The whole bar-sum family — the carry's second witness
(`A-DUR-2`), `OMR_METER_FROM_BARS` (`A-DUR-7`) and Sean's per-bar model
(`A-DUR-6`, items 3, 4 and 5) — assumes a page's own arithmetic is readable
where the page is legible. **It is not, and the scan was never the reason.**
The cross-staff majority that is supposed to make a bar trustworthy passes
them. ⚠️ **This is the half that is additional to the sibling session's
measurement**: they measured that ASSESSABILITY falls with density (100% of
bars at 1.5 events per bar, 33% at 4.5) — how many bars speak; this is whether
the ones that do are RIGHT.

⚠️ **The errors run LONG** (3.5, 4.5, 5.0, 6.0 vs 4.0) on a page with no
missing ink — a diagnosis to open, not a conclusion.

⚠️⚠️ **THE DIAGNOSIS IS DONE (2026-09-09) AND IT IS TWO FAULTS, ONE OF THEM
FIXED. BOTH ARE THE SAME FAMILY: A MARK IS GATHERED AND THE DECISION READS IT
IN THE WRONG PLACE.** See
[`benchmarks/omr-staged-duration-beams-2026-09/FINDINGS.md`](../../../benchmarks/omr-staged-duration-beams-2026-09/FINDINGS.md).

* ✅ **FIXED — a note is joined to its beam by its STEM.** A beam stroke runs
  from the first stem it joins to the last, and a stem stands at the SIDE of
  its notehead, so the OUTER note of every beamed group has its centre roughly
  half a notehead width past the stroke's end — measured, the overshoot
  clusters at **0.35-0.47 notehead widths**. `_beam_levels` tested that centre,
  so 114 narrowed durations read `none_over_this_note` while a stem of the head
  demonstrably met the beam; `BEAM_EDGE_TOLERANCE_WIDTHS` then caught them as
  POSSIBLE and `_bar_lengths_for` collapsed the range to its LONGEST candidate.
  ⚠️ **`Q.STEM` was declared in `wants` and `composed_from`, carried a
  `KNOWN_GAPS` entry, and was read by nothing** — 916 rows on a three-page
  record. `_stem_joined` reads it as an ADDITIVE tier beside the centre test.
  Assessable bars **12 → 14, correct 7 → 10**, `narrowed` **147 → 29**, no bar
  right-to-wrong. ⚠️ The candidate-policy question DISSOLVES: under the stem
  tier `top` and `lowest` agree on every bar, which is the claim that the
  ambiguity was an artefact of the association.
* ✅ **FIXED — a MARK must be ATTACHED to its notehead.** `Q.FLAG` and
  `Q.AUG_DOT` are gathered on the MARK's own glyph subject and were read on the
  NOTEHEAD's, so **134 flag rows and 157 dot rows reached ZERO durations** — 0
  durations carrying a dot, `beam_evidence == "flag"` 0 times. It accounted for
  both directions of the residual, confirmed against the encoding the page was
  rendered from: m211 read `quarter + 8th-rest` × 4 = **6.0** where the truth
  holds **100 eighths**, and m207/m208 read a plain half at **2.0** where 8
  parts play a **dotted half**. Now 112 flags attached (109 deciding) and 157
  dots, and **the fixture reads 16 assessable bars, all 16 correct**.
  ⚠️ A flag hangs on a STEM, which on this path beats the legacy x-centre rule
  (`_flag_for_notehead`'s own docstring says it cannot use the stem because a
  0-stem detector has none — stale here). ⚠️ A second bug sat in the same two
  lines: `levels = len(flags)` counts GLYPHS, and one `flag16thUp` is one glyph
  and TWO levels. ⚠️⚠️ And the dot window needed a unit that was not on the
  record — `Q.CELL_STAFF_SPACE`, gathered where `_cell_grid` already computes
  it, because **it is not a constant**: the nominal is
  `CANONICAL_STAFF_SPAN_PX / 4 = 100`, but `_upscale_to_canonical` scales a
  too-wide cell by WIDTH, and on this fixture **184 of 368 cells read 100 and
  the other 184 read 38.5-56**. `DOT_ABOVE_NOTE_MAX_SPACES` /
  `DOT_BELOW_NOTE_MAX_SPACES` had sat in the staged module, with a paragraph of
  measured justification, **used by nothing in it**.

⚠️ **AND IT HAS A MEASURED COST ALREADY.** `A-DUR-2` records that only the
BENEFIT of the carry was measured. On the engraved fixture at bar 155 a
**correct** carry is refused — 4 bars agree, 4 disagree, +1.0 against a floor
of 2.0. That is the cost side, and it is a direct consequence of this entry.

**What it does NOT overturn.** Where the bars are read right, both mechanisms
behave: the carry brings the new 3/4 forward at +5.0 (4/0) and the bar reader
independently derives the same 3/4 at +4.0, borrowing the spelling from the
system that read it.

**How to falsify.** Render any other change (bar 364 is 2/2, one command) and
find the sums correct. **Do not tune `METER_CARRY_FLOOR` or
`METER_FROM_BARS_FLOOR` against this** — that is fitting a constant to a
broken input.

**Blast radius.** Staged path only (`tools/omr/rhythm.py` untouched, so no
engraved or scan figure moves).

✅ **THE SCAN ARM IS DONE** — Litolff Beethoven 5 mvt1, pdf pages 1-4, windows
hand-verified, 2/4 throughout, ONE gather adjudicated four times so no detector
jitter (`readjudicate.py`, whose `--control` reproduces the pipeline's own 2993
duration verdicts exactly before any arm is read). **The two halves come
apart**: the STEM tier is the whole gain (per-staff readings right 401 → 430 of
733), and the MARKS half does **nothing at all** there (401 → 401) — not
because the rule fails but because the detector fires **49 flag boxes and 35
dots over 2347 noteheads**, against 134 and 157 over 1118 on an engraving. A
DETECTION limit, the same shape already recorded for hairpins.

⚠️⚠️ **IT IS NOT FREE, AND ONLY THE PER-STAFF VIEW SHOWS IT.** At bar level
**0 bars go right → wrong** and 11 become assessable, all right — but that is
the cross-staff quorum working, not the rule being harmless. Underneath, **54
readings go wrong → right and 26 go RIGHT → wrong**: a 2:1 trade. On the
engraving every move was one way, so this is exactly what a perfect-ink fixture
cannot price.

⚠️ **THE FALSE-ATTACHMENT PROBE NEEDS NO TRUTH FILE**: a note under a beam
carries no flag, so a notehead with both is a contradiction. **Engraved 3 of
112 flagged notes (2.7%); scan 7 of 37 (18.9%)** — seven times the rate on a
seventh of the population, so the worry is real and bounded. **No gate was
added**: switching the flag half off by print quality would be a rule fitted to
one scan of one publisher, and the measured cost of leaving it on is one net
reading in 733.

⚠️⚠️ **AND A SECOND PUBLISHER'S SCAN NOW EXISTS AND CORRECTS THE ABOVE.**
Brahms 1 mvt1 / **Breitkopf & Härtel**, pdf pages 0-3 (14/27/28/28 staves),
truth read off the encoding (`6/8`, one bar of `9/8` at m8, `6/8`) and its
placement corroborated by our segmentation matching the window EXACTLY on pages
1-3 (15, 15, 21). Control **4365 of 4365**.

**It HOLDS and is far larger**: per-staff readings right **42 → 108 of 493**,
and with the rule OFF **not one of the eight assessable bars is right** — four
of them reading exactly **4.0 in a 6/8 movement**, the signature of a beam
missed. With it on, six of eight are 3.0.

⚠️ **It corrects the claim above: "the marks half does nothing on a scan" was
about THAT DOCUMENT.** Litolff `984073` is catalogued *"low-res bitonal"* and
fires 49 flag boxes and 35 dots; Breitkopf fires **371 and 656**, and there the
marks half alone is worth **+13** where on Litolff it was worth **0**. Read
every "on a scan" above as "on that scan".

⚠️ **The two halves are SUPER-ADDITIVE — +15 and +13 separately, +66 together**
— and the mechanism is the bar: a bar is right only when EVERY note in it is,
so a bar holding one beam-missed and one flag-missed note stays wrong until
both are repaired.

⚠️ **The costs are larger too**: 27 readings go RIGHT → wrong against 93 the
other way (3.4:1), and the contradiction rate is **27.5%** against Litolff's
18.9% and the engraving's 2.7% — three points, ordered engraved < Litolff <
Breitkopf, i.e. **the worse the ink, the more the flag half picks up**. ⚠️ And
the page is read badly whatever we do: 108 of 493 is **22%** against Litolff's
59%, so this is a large RELATIVE gain on a document that is still mostly wrong.
⚠️ The `9/8` bar the fixture was chosen for is **unassessable** — its 23 staves
read 23 different lengths — so the quorum correctly declines the one bar the
document was picked for.

⚠️⚠️ **AND THE BAR-LEVEL FIGURES OF THAT ARM WERE WRONG WHEN FIRST PUBLISHED
(44/43 → 49/48), FOR A REASON WORTH MORE THAN THE NUMBERS.** The probes keyed a
bar on `(page, cell)`, and **a cell index RESTARTS at 0 on each system of a
page** — so system 0's third bar and system 1's third bar were merged into one
pseudo-bar and then scored. Four pages of a UNIFORM-meter document could not
expose it; the first fixture whose truth is not uniform did, immediately. The
corrected figures are **71/67 → 78/74**, the direction is unchanged, and the
merged version had ALSO been hiding losses — it reported one bar dropping out
of the quorum where there are four. ⚠️ Per-staff readings were keyed on the full
event subject all along and did not move, which is why the headline survived.

✅ **THE SECOND PUBLISHER IS MEASURED (above)**, and this thread already
has a case where a result held on a second document and broke on a second
publisher's scan. ⚠️ **The scan bar sums were already nearly right where they
were assessable at all** (67 of 71 → 74 of 78); what moved is how MANY bars can
speak. Re-pricing `METER_CARRY_FLOOR` or `METER_FROM_BARS_FLOOR` still needs
that second publisher first.

### A-DUR-6 · ⚠️⚠️ THE TARGET MODEL — a meter is decided PER BAR, from layered evidence

**SEAN'S DESIGN, 2026-09-09, recorded verbatim so it is not lost or paraphrased away.**

> *"It's almost as if each bar needs to do its own math but submit first to
> contextual elements. Example: 1. Does the bar have a meter glyph? 2. Are
> there meter glyphs on different systems on this same bar. 3. What is the sum
> of durations for this bar. 4. What is the sum of this same bar on all the
> other systems? 5. The bars on either side for 4 bars have the same equivalent
> of the sum? ... I think eventually we can add beat subdivision matches the
> time signature? And are there any undefined blobs of ink?"*

> *"If there is an established meter and no sign of change then it starts the
> same meter. If there is no established meter then it must derive the most
> likely meter based off of the order of determination above."*

**The governing rule.** Persistence by default; a change must be argued for.
Where nothing is established, the meter is DERIVED from the ranked evidence
rather than defaulted.

**The evidence, in Sean's order** — status against what exists today:

| # | evidence | today |
|--:|---|---|
| 1 | a meter glyph at this bar | ✅ `Q.METER_GLYPH`, now gathered at EVERY cell |
| 2 | meter glyphs at the same bar on other staves | ✅ voted in `_meter_changes` |
| 3 | this bar's own duration sum | ✅ `_bar_lengths_for` |
| 4 | the same bar's sum on every other staff | ✅ the per-bar modal vote |
| 5 | the surrounding bars' sums | ⚠️ PARTIAL — forward of a candidate (`_bar_run`), and now the whole system's own bars as a proposer of the LENGTH (`A-DUR-7`) |
| 6 | beat subdivision agrees with the meter | ❌ not built; beams are gathered, grouping is not read — ⚠️ and a note is now joined to its beam by its STEM (`A-DUR-8`), which is the association such a rule would need |
| 7 | undefined blobs of ink | ❌ not built — see A-DUR-5 |

**Three things to carry into building it, each paid for by a measurement here:**

⚠️ **THE RUN MUST BE DIRECTIONAL.** Bars AFTER a candidate change point are
evidence for the NEW meter and bars BEFORE it are evidence for the OLD one, so
a symmetric ±4 window blurs exactly the boundary it is meant to find. Run
LENGTH is legitimate evidence ("the longer the more likely"); a symmetric
window around a suspected change is not.

⚠️ **A RUN MAY PROPOSE — BUILT 2026-09-09, AND IT IS NOT A RUN.** See
`A-DUR-7`. The discriminator turned out to be the ACCUMULATED agreement rather
than consecutiveness (a run breaks on an unassessable bar, which measures the
page's legibility and not its meter), and the thing a bar sum can propose is
only a LENGTH — `2/4` and `4/8` are one arithmetic. The *Andante* refuses
itself at −2.0 with no special case.

⚠️ **EVIDENCE STILL HAS TO BE INDEPENDENT.** Ten bars whose durations all trace
to one misread beam level are ONE signal. `correlated_groups` exists for this
and the clef work is the warning: every clef detection on a staff is one group,
so no amount of detector evidence breaks a clef tie.

**Worth adding to the list:** a **double barline** at the candidate bar. A
meter change is nearly always printed after one and it is a genuinely
independent reader. ⚠️⚠️ **BUT IT IS NOT CHEAP, AND THIS ENTRY SAID IT WAS.**
Checked 2026-09-09: `Q.BARLINE_COLUMN` is a per-staff **count of cells cut**
(`gather.gather_measures` observes `last + 1`), not barline positions and not
barline types — and the repo has **no barline-type classification at all**
(NOTES.md item 5, which is why `<repeat>` is dropped on export). So this needs
new CV *and* a new gathered quantity. Correct the estimate before budgeting
for it. Also a tempo word at that
bar ("Tempo I.", "Allegro") — the engraver's own section marker, blocked only
on `direction` being a stub.

### A-DUR-5 · ⚠️⚠️ UNBUILT AND WANTED — unclassified ink as a first-class fact

**SEAN'S REQUEST, 2026-09-09, recorded so it is not lost.**

> *"I really don't want to lose the 'here is a blob of ink but we don't know
> what it is' gather data point. It can be used in every decision point if
> needed to help rule things out or determine patterns like — this is the same
> unrecognizable blob on every system at bar 51... or we know what this blob is
> in 3 of the 10 systems and they all line up and are there for the same
> thing."*

**The idea.** GATHER records ink it cannot name, as a quantity, with position.
Then any decision may ask: *is there something here?* — and, more powerfully,
**do the unnamed things LINE UP across staves and systems?** A blob at the same
bar on every staff is a printed event whatever it is; a blob at one bar on one
staff is noise. Where a few staves DO classify it and the rest only see a blob,
the classified minority names what the majority corroborates.

⚠️ **THIS IS NOT REACHABLE FROM THE DETECTION RECORD, AND THE MEASUREMENT SAYS
SO.** At p.62 cell 8 the meter is printed on every staff, we classify it on
**2 of 17**, and the other 15 carry **no unclassified detection at that
column** — the ink was not detected at all, rather than detected and unnamed.
So the tier needs a **RASTER pass in GATHER**, not a re-weighting of what is
already recorded.

**The precedent exists.** `direction_text._blank_detections` subtracts every
detection from the page's ink so that *"find the text"* becomes *"find the
ink"*. The same subtraction, kept as rows rather than consumed for OCR, is the
whole mechanism.

**Why it is worth doing.** It is the only proposal on the table that helps the
case where a reader classifies nothing — which is every hard page measured
here: p.17's meter change, p.62's other 15 staves, and the scan corpus's
hairpins (1 detected against 198 encoded).

### A-DUR-3 · ⚠️ The pipeline's ONE sanctioned loop, declared per rule

**CONTINGENCY** — allowed by Sean, 2026-09-09, after the guard escalated it.
*`evaluate.rule(single_pass=True)`, `Verdict.single_pass_revision`, `record.UphillConsequence`*

**Assumption.** `reconcile_duration` may revise a duration even though the
meter that triggers it now DEPENDS on that duration, because the loop is
single-pass.

**Why.** Corroboration makes the meter read the bars, and the repair rewrites
those same bars from the meter — which `UphillConsequence` refuses by default,
correctly, since it cannot see that a loop terminates. This one does: unrolled
it is `duration_v1 -> meter -> duration_v2`, a straight line run once, which is
the rule `transcribe` has always stated as *"vote once, repair once"*. What
makes it safe is the BOUND, not the flag — at most one note, an exact landing,
a unique answer, so it cannot iterate even in principle.

⚠️ **DECLARED PER RULE, NOT GLOBALLY**, so the exemption cannot spread by
accident, and the guard's error message now names it so the next person meets
a choice rather than a wall.

**How to falsify.** Show a rule declaring `single_pass` whose bound permits a
second application, or a run where a value oscillates.

**Blast radius.** One rule. Any other rule wanting the exemption must declare
it and state a bound that makes iteration impossible.

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

## A-WIT — redundant groups (the witnesses)

⚠️ **`A-WIT`, not `A-GROUP`.** `A-GROUP` above is the bracket/staff-grouping
decisions and is a different thing entirely. These are about *several
witnesses to one fact*.

### A-WIT-1 · ⚠️ A disagreement implicates the GROUP, never a member

**PRINCIPLE** — Sean's own statement of it, and the property the whole module is shaped around.
*`Group.suspects`, `Group.dissenting`*

**Assumption.** A group that disagrees raises the suspicion of **every**
witness, the majority included. `suspects` is all of them; a SPLIT names no
dissenter at all; there is no `culprit`, `correct_value` or `repair` field, and
a test asserts structurally that none is ever added.

**Why.** Nine eighths in a 4/4 bar proves an error without naming which symbol
— it could be the meter, a duration, a spurious note, a missing one, or a
mis-owned glyph. `_reconcile_measure_to_meter` is the tree's one correct
implementation: it repairs only when the answer is **UNIQUE**, i.e. declines
exactly when more than one member could explain the failure.

**How to falsify.** Not falsifiable by measurement — it is a statement about
what the evidence supports. What IS measurable is the cost: hand-adjudicate a
sample of MAJORITY groups and count how often the dissenter really is the
error. ⚠️ **Even a high rate would not license convicting it**, because the
cases where it is wrong are the ones the metric cannot see. It would license a
RANKING for a human queue, which is a different product.

**Blast radius.** Everything downstream of a disagreement. Get it wrong and a
failed bar sum confidently rewrites whatever is cheapest to alter.

### A-WIT-2 · The vote unit is the SIGNAL CLASS, not the row

**PRINCIPLE** — two signals sharing an ancestor are ONE signal, not corroboration.
*`groups.one_signal`, `Group.n_signals`, `Group.uninformative`*

**Assumption.** Witnesses are partitioned into signal classes; a class votes
once, and only if its own rows agree. Fewer than two classes is `SINGLE`,
never `UNANIMOUS`.

**Why.** Measured, on the old pipeline: the header clef pre-pass and the
measure-pass argmax LOOK like two readings and are the same call on the same
list object — divergent on **0 of 396 staves** — and counting them as
agreement would have produced a healthy-looking **77% agreement rate carrying
no information**. `Verdict.basis` makes the ancestor closure a set operation,
so the rule is enforced rather than remembered.

**How to falsify.** Count the groups whose `n_signals` is below their witness
count on a real page. If the number is ~0, the collapse is buying nothing here
and the cost of computing it is unpaid. ⚠️ **A zero there is a suspect**: it
is also what a broken closure walk produces.

**Blast radius.** Every agreement figure. Over-collapse hides real
corroboration; under-collapse manufactures it.

### A-WIT-3 · ⚠️ The redundant thing is an ASPECT, and `reading` names it

**PRINCIPLE** — arrived at by injury, in `key_signature_corroboration`, and it survives on its merits.
*`Redundancy.reading`, `Redundancy.aspect` (required prose)*

**Assumption.** Each redundancy declares which aspect of a fact is printed more
than once, and compares only that.

**Why.** A meter is corroborated by other staves reading the same METER,
because a meter is one fact shared by the system. A key signature is not:
transposing instruments genuinely carry different written keys at the same bar,
so *"the other staves read something else" is not evidence of anything*. What
transplants is the POSITION of a change, not its value. A wrong `reading`
therefore manufactures disagreement out of correct engraving.

**How to falsify.** For each declared redundancy, find printed music where the
declared aspect legitimately differs. That is not a bug report — it is either a
`legitimate_difference` to declare or a redundancy to refuse.

**Blast radius.** Confined to the redundancy that gets it wrong.

### A-WIT-4 · A part is joined across systems by ORDINAL, and only within one lineup

**CONTINGENCY** — an artefact of `slot_index` being a per-system ordinal today.
*`groups._slot_fact`*

**Assumption.** Two staves witness one part only when their systems print the
**same number of staves**; the staff count is in the fact key.

**Why.** `adjudicate_slot_index` returns the staff's ordinal within its own
system and says so. A printed score suppresses tacet staves, so joining slot 4
of an 11-staff system to slot 4 of an 8-staff system grafts a horn's
continuation onto a trumpet's part — the population `export._stitch_slots`
refuses outright, and where the partition gate measured **3 of 27 staves
misgrouped**.

⚠️ **THE COST IS REAL AND IS THE OPPOSITE OF SAFE-LOOKING.** On a document
whose systems suppress staves, every part-scoped group (`clef`, `instrument`,
`key_signature`) degrades to `SINGLE` across the board and corroborates
nothing — and a wall of `SINGLE` reads as "no problems found". That is what
`checked_nothing` in the report exists to say out loud.

**How to falsify.** Count part-scoped groups with ≥2 witnesses on a real
orchestral scan. If it is near zero, the join is too strict to be useful and
the answer is a document-wide reference lineup (D10), not a looser key.

**Blast radius.** Four of the six declared redundancies — `clef`,
`instrument`, `key_signature` and `staff_group` are all part-scoped.

### A-WIT-5 · Groups run AFTER adjudication and BEFORE evaluation

**MIXED** — "verdict witnesses need verdicts" is forced; the choice of before-EVALUATE is ours.

**Assumption.** `GATHER → ADJUDICATE → GROUPS → EVALUATE`.

**Why.** Verdict-sourced redundancies need the decisions to have run. Placing
it before EVALUATE means the report describes what was **adjudicated** rather
than what a consequence later restated, which is the cleaner claim — and
consequences supersede verdicts, so the other order would report a mixture.

**How to falsify.** Run it in both positions and diff the report. Any group
that changes is a fact a consequence revised, which is worth knowing either
way.

**Blast radius.** None today: nothing consumes the report.

### A-WIT-6 · ⚠️ The report has NO CONSUMER, deliberately

**CONTINGENCY** — a phase boundary, not a design position.

**Assumption.** `result["agreement"]` is produced, surfaced and acted on by
nothing.

**Why.** Seeing that witnesses disagree is one job; deciding what to do about a
disagreement is another, and doing them together is how a failed check ends up
convicting the cheapest member. The named consumer is D4.

⚠️ **This is exactly the Class-C shape this project keeps paying for** — the
five internal-consistency checks fire **85 warnings on one real document and
every one is inert**. The difference is that this one says so in its own
docstring, names its consumer, and is printed by the CLI rather than left in a
JSON nobody opens. **If D4 does not land, this entry becomes the accusation
rather than the excuse.**

**How to falsify.** It is a plan, not a claim. It fails by not being executed.

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
does not run cannot have its precedence tested. **6 of 21 decisions and 1 of 6
consequences are declared stubs today** (the count was stale at 13/5 for two
days — the ledger dual of a stale figure, in the file that says the tree
outranks the ledger). The fastest way to make this list
smaller is to wire identity — it is the input to four other decisions and the
one whose absence makes A-ORDER-2, A-GROUP-2 and A-OWN-1 untestable by
construction.
