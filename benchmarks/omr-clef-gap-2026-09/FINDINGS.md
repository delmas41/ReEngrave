# The unread clef on a part the record has already placed — roadmap 2.10

**Roadmap:** 2.10. **Date:** 2026-09-23. **Path:** STAGED. **Branch:**
`claude/clef-gap-2.10`, off `1c9cf26c`.

**Sean, 2026-09-23** (`docs/DECISIONS.md`): *"yes — viola staff with
unreadable clef reads as alto and it should check other systems if the alto
clef can be found"*.

The rule this built, in his order and only into the gap:

1. the staff's own `Q.CLEF` verdict — if it ABSTAINED, and only then;
2. the clef DECIDED on the same part on OTHER SYSTEMS of the document, by
   MAJORITY of those reads; **a split abstains**;
3. failing that, the instrument's conventional header clef from
   `tools/omr/instruments.py`.

A READ clef is never overruled. Every inferred clef is labelled, named by
staff in the export census, and its derived pitches name it in their `basis`.

---

## 1. The one-sentence result

**On the Litolff whole movement all 9 unread clefs are filled, every one of
them by tier (2) and none by the convention, 0 DECIDED clefs move, `no_pitch`
refusals fall 807 → 552 and events written rise 10,415 → 10,646 — and on page
3 the Viola staff the funnel traced goes from 0 of 48 heads written to 37 of
48, which is exactly the number that benchmark estimated a clef would unlock.
Brahms and the engraved fixture hold ZERO abstained clefs, so the rule is
provably inert on both, and the instrument-convention tier has reach ZERO on
all three documents.**

---

## 2. Where the numbers came from

| what | command (from the worktree root) |
|---|---|
| base vs arm, per document | `python3 benchmarks/omr-clef-gap-2026-09/probe/replay.py <record> --id <id> --out-json benchmarks/omr-clef-gap-2026-09/out/<id>.json --write-arm <scratch>/arm` |
| the per-staff gate, BOTH arms | `python3 benchmarks/omr-notehead-funnel-2026-09/probe/funnel.py --record <scratch>/arm/beethoven5-litolff-{base,arm}.record.json --page 3 --system 0 --staff 9 --ref-part Viola --ref-first 49 --ref-last 64 --musicxml <scratch>/arm/beethoven5-litolff-{base,arm}.musicxml --out-json benchmarks/omr-clef-gap-2026-09/out/funnel-{base,arm}-litolff-p3-s0-st9.json` |
| the tables from those | `python3 benchmarks/omr-notehead-funnel-2026-09/probe/tables.py --funnel <that json>` |
| what is LEFT in `no_pitch` | `python3 benchmarks/omr-clef-gap-2026-09/probe/remaining_no_pitch.py --record <scratch>/arm/beethoven5-litolff-arm.record.json` |
| the header crops | `python3 benchmarks/omr-clef-gap-2026-09/probe/crop_clef.py --arm <scratch>/arm/beethoven5-litolff-arm.record.json --pdf library/editions/beethoven/symphony-5-op67/…imslp984073.pdf --label litolff --dpi 600` |
| the unit battery | `python3 -m pytest tools/omr/tests/test_infer_clef_gap.py -q` → **37 passed** |
| the fast tier | `python3 -m pytest tools/omr/tests -m "not slow" -q` |
| the derived checks | `python3 -m tools.omr.staged.check` → **254 open** (baseline 255) |

`replay.py` **imports** `benchmarks/omr-infer-stage-2026-09/reinfer.py`'s
`rebuild` and `control` rather than taking a copy. The per-staff gate is
`omr-notehead-funnel-2026-09`'s own probe, run UNCHANGED over both arms'
records — this directory owns no second copy of a refusal rule.

**The controls, all of them, including the one that reads FALSE.**

| control | result | why it matters |
|---|---|---|
| the rebuild reproduces the record (Litolff) | **101,361 of 101,361 verdicts, 156,525 of 156,525 observations, 0 differ, +0 extra** | a rebuild that is not the record makes every number below a measurement of the harness |
| the base arm is deterministic | **true on all three** (run twice, byte-identical MusicXML) | a base that is not stable makes every delta noise |
| the base arm's file equals the RECORD's own file | **false on both scans — and that is correct** | ⚠️ the base arm re-runs the whole INFER stage with only `OMR_CLEF_GAP` off, and both records predate `OMR_INFER`'s default flip (2026-09-23), so the base already carries the two duration rules' inferences (69 Litolff, 287 Brahms). **The BASE ARM is the baseline, never the record** (CLAUDE.md §6b, *base vs arm on ONE tree*). A table cut from the record's own export would put the duration rules' effect in this rule's column. |
| `funnel.py`'s own accounting control | PASSED on both arms | it sums its per-subject log back to the exporter's own refusal totals |
| the crop frame control | **8 of 9 passed, 1 REFUSED** | §6 |
| the new test battery run RED first | every symbol it reaches for is absent at `1c9cf26c` | `git grep -n -e CLEF_GAP_SWITCH -e clef_gap_enabled -e inferred_in_basis -e 'def run_over' -e reads_beyond_cause -e clef_gap_census -e 'def fill_clef_gap' -e _move_glyph_also_reads 1c9cf26c -- tools/` returns nothing |

---

## 3. Per document

| | Litolff (Beethoven 5, whole mvt, 16 pp) | Breitkopf (Brahms 1, whole mvt, 27 pp) | engraved (Beethoven 5 bars 1–24) |
|---|---|---|---|
| clef verdicts | 331 | 691 | 54 |
| DECIDED / NARROWED / **ABSTAINED** | 307 / 15 / **9** | 689 / 2 / **0** | 54 / 0 / **0** |
| abstention reasons | all 9 `no_candidates` | — | — |
| inferred by **(2) other systems** | **9** | **0** | **0** |
| inferred by **(3) instrument convention** | **0** | **0** | **0** |
| still abstained after | **0** | 0 | 0 |
| **DECIDED clefs changed** | **0** | **0** | **0** |
| `no_pitch` refusals before → after | **807 → 552** (−255) | 61 → 61 | 0 → 0 |
| `duration_narrowed` before → after | 1,321 → 1,345 (+24) | 3,339 → 3,339 | unchanged |
| every other refusal bucket | unchanged | unchanged | unchanged |
| events written (the log's own count) | **10,415 → 10,646** (+231) | 21,680 → 21,680 | unchanged |
| `<note>` elements in the file | **12,424 → 12,585** (+161) | 23,145 → 23,145 | 676 → 676 |
| `status_census` `unaccounted` | `[]` both arms | `[]` both arms | `[]` both arms |
| export `balanced` | **True** both arms | **True** both arms | **True** both arms |
| the bounded second EVALUATE pass fired | **376** (`restate_pitch` 287, `move_glyph` 89) | **0** | 0 |
| new verdicts in the arm | **454** = 9 clef + 376 pitch + 69 duration | 287, all duration | 0 |
| every new verdict labelled or a named consequence | **true** | true | — |

⚠️ **The duration verdicts (69 Litolff, 287 Brahms) are in BOTH arms** and are
the two INFER duration rules, not this one. They appear in the "new verdicts"
row because the arm re-runs the whole stage; the base/arm DELTA is 9 clefs and
376 pitches on Litolff and **exactly nothing** on the other two.

⚠️ **+231 events written against +161 `<note>` elements, and they are not the
same question.** `events_written` counts what the exporter placed; a bar that
used to hold one measure rest and now holds four notes gains four elements and
loses one, and a chord is several `<note>` elements for one event. The BALANCE
control (`events_in_log 14,530 = written + not written`) holds in both arms,
which is the figure to read.

⚠️ **`duration_narrowed` rises by 24, and that is the refusal ORDER, not a
regression.** `_place_notes` tests `no_pitch` BEFORE `duration_*`, so a head
on a clefless staff was charged to `no_pitch` and hid everything downstream of
it — the funnel states this explicitly. 24 of the 255 heads that stopped
failing the pitch test now fail the duration test instead. Net heads written
is +231, not +255.

⚠️ **Brahms and the engraved fixture are a REACH ZERO, not a clean result.**
Neither document holds a single abstained clef, so the rule had nothing to
speak about. *A change that moves nothing because it is INERT and one that
moves nothing because the page holds NOTHING TO MOVE are the same number* —
the population row above is what separates them, and `replay.py` prints a
warning on a zero-abstention document for exactly that reason.

### The nine, named

| staff | clef | tier | slot / part | other systems read | independent witness groups | pitches derived |
|---|---|---|---|---|---|---|
| `staff/2/1/9` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 76 |
| `staff/3/0/9` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 47 |
| `staff/5/0/7` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 26 |
| `staff/5/1/5` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 26 |
| `staff/7/0/9` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 73 |
| `staff/7/1/9` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 33 |
| `staff/14/0/11` | bass | other systems | 11 (unnamed) | `{bass: 8}` | 8 | 9 |
| `staff/15/0/9` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 50 |
| `staff/16/1/9` | alto | other systems | 9 Viola | `{alto: 14, treble: 1, bass: 1}` | 14 | 36 |

Written by `export.coverage`'s new `inferred_clefs` key, one line per staff —
**named, never counted**, because Sean adjudicates these one header at a time
and `status_census` partitions FAMILIES and structurally cannot see a single
staff (the funnel's own caveat 5).

⚠️ **The slot-9 tally is not unanimous** — 14 alto against one treble and one
bass. Sean's rule is a MAJORITY, so it fills; the full tally rides on the
verdict and is printed on every crop, so a reader sees the dissent without
being told about it.

⚠️ **7 of the 9 stand on a slot that is itself an INFERENCE**
(`part_from_an_inference: true`) — `collapse_slot_index_to_family_block`
placed the Viola. Those clefs are an inference resting on an inference, which
is legible from `basis` and is stated in the verdict's own detail. The rule
ORDER inside INFER is what makes it possible at all, and
`test_infer_clef_gap.TestItRunsAfterTheSlotRule` pins it: registered before
the slot rule, this one finds no decided slot, proposes nothing, and reports a
clean, FALSE zero.

---

## 4. The gate

**Roadmap 2.10's gate: `staff/3/0/9` writes ≥ 37 of 48. It writes 37.**

Both columns are `omr-notehead-funnel-2026-09/probe/funnel.py` run on this
lane's own BASE and ARM records, so nothing but `OMR_CLEF_GAP` differs.

| Litolff pdf page 3, system 0 | base (`OMR_CLEF_GAP=0`) | arm (`=1`) |
|---|---|---|
| `staff/3/0/9` clef | **ABSTAINED (`no_candidates`)** | **alto** (inferred) |
| notehead boxes on the staff | 48 | 48 |
| `R:no_pitch` | **40** | **0** |
| `R:duration_narrowed` | 0 | 3 |
| `R:owned_by_another_staff` | 3 | 3 |
| `R:clipped_fragment` / `too_narrow` / `ink_is_a_whole_rest` | 3 / 1 / 1 | 3 / 1 / 1 |
| **WRITTEN** | **0** | **37** |
| balance | 48 = 0 + 48 ✅ | 48 = 37 + 11 ✅ |
| `no_pitch` on the whole PAGE | 40 | **0** |
| every other staff on the page | — | **identical, row for row** |

The 37 is not a coincidence: the funnel's estimate was *48 − 5 refused before
the pitch test − 3 whose duration is NARROWED − 3 owned by Violino II = 37*,
stated there as an upper bound on what a clef unlocks. It is the exact figure,
which means the clef was the whole of the blockage on that staff and nothing
else moved.

⚠️ **37 heads WRITTEN is not 37 heads RIGHT.** The reference holds 31 sounding
heads over those bars and we now write 37. Per-head correspondence was not
established here any more than it was in the funnel. What this table says is
that the heads reach the file; whether each pitch is correct is the next
question and needs Sean or a hand-labelled pass. The crop in §6 settles the
CLEF, which is the one decision this lane made.

---

## 5. What is LEFT in `no_pitch`, and it is one thing

`no_pitch` does not go to zero on the document — 552 survive. Reading the
halving as *"the clef was most of it"* would be the inference CLAUDE.md warns
against, so the survivors were partitioned (`probe/remaining_no_pitch.py`):

| cause | n |
|---|---|
| **the staff's clef is NARROWED** | **596** |
| owned by another staff (a different refusal) | 5 |
| the clef is ABSTAINED — i.e. the rule did not reach it | **0** |
| the clef is DECIDED and no `notehead_staff_position` row exists | 0 |
| the clef is DECIDED and is not in `_CLEF_ANCHORS` | 0 |
| the clef is DECIDED and a position row exists — unexplained | 0 |
| no clef verdict at all | 0 |

⚠️ The 601 here is a SUPERSET of the exporter's 552: this counts noteheads
with no standing pitch, and `_place_notes` takes some of them out under an
EARLIER test (`not_a_notehead`, `ink_is_a_whole_rest`). Both numbers are
printed side by side rather than one being presented as the other.

**So after 2.10 the entire residual `no_pitch` population is the NARROWED
clef**, which this rule declines by design (§8). That is a population, not a
hunch, and it is the obvious next item — but it is a DIFFERENT claim: a
narrowing means `adjudicate_clef` READ the staff and could not separate two
candidates under its own margin floor, and collapsing that from another system
is a decision about the clef reader's floor rather than a gap-filling one. Not
proposed here.

---

## 6. The crops — 8 cut, 1 REFUSED

`benchmarks/omr-clef-gap-2026-09/out/print/` (`crop-manifest-litolff.json`,
every `VERDICT_none_yet: null`). Cut from the PDF at the gather's own **600
DPI** (read from the record's `provenance.settings.args.dpi`), zoom 4, with:

* the staff's own five `Q.STAFF_LINES` traced in **GREEN**, so the crop says
  which staff it is about — Sean's own correction of 2026-09-23;
* a **RED** bracket on the header window, where a clef would be printed;
* a blue ruler, one tick per staff space;
* a caption naming the staff, the inferred clef, the tier, the slot, the full
  other-systems tally and the independent-witness count.

| file | staff | inferred | frame contrast |
|---|---|---|---|
| `litolff-p2-s1-st9-alto-clef_from_other_systems.png` | `staff/2/1/9` | alto | 13.77 |
| `litolff-p3-s0-st9-alto-clef_from_other_systems.png` | `staff/3/0/9` | alto | 152.51 |
| `litolff-p5-s0-st7-alto-clef_from_other_systems.png` | `staff/5/0/7` | alto | 208.43 |
| `litolff-p5-s1-st5-alto-clef_from_other_systems.png` | `staff/5/1/5` | alto | 212.31 |
| `litolff-p7-s0-st9-alto-clef_from_other_systems.png` | `staff/7/0/9` | alto | 204.11 |
| `litolff-p7-s1-st9-alto-clef_from_other_systems.png` | `staff/7/1/9` | alto | 161.91 |
| `litolff-p14-s0-st11-bass-clef_from_other_systems.png` | `staff/14/0/11` | bass | 234.19 |
| `litolff-p16-s1-st9-alto-clef_from_other_systems.png` | `staff/16/1/9` | alto | 148.72 |
| — **REFUSED** | `staff/15/0/9` | alto | **7.14**, under the 8.0 margin |

⚠️⚠️ **THE REFUSAL IS THE CONTROL WORKING, AND IT IS NOT PAPERED OVER.** The
frame control (imported from `omr-infer-duration-print-2026-09`, not copied)
asks whether the staff's recorded line positions are materially darker than a
half-space off them on the page this script rendered. On page 15 they are not,
by a small margin. Something about that staff's filed geometry and that render
disagree, and until that is understood **nothing drawn on that page is
evidence** — so no crop was produced rather than one with a caveat. It is the
ninth inference and it has no picture. ⚠️ `staff/2/1/9` passes at **13.77**,
which clears the margin but is an order of magnitude below the other seven;
read that crop knowing so.

⚠️ **Brahms cut ZERO crops because it has zero inferred clefs.** That is the
page, not the probe: `crop_clef.py` prints a warning on an empty run for
exactly the reason `reach.py` exists.

⚠️ **Nobody has adjudicated any of these yet.** Every `VERDICT_none_yet` is
`null`. The rule ships default-ON on the strength of the mechanism, the
controls and the funnel's own prediction — not on a print check, and
`docs/flags-2026-09.md` gives the flag `research` for that reason, not
`promote`.

---

## 7. The ordering problem, and what was rejected

INFER runs **after** EVALUATE (`infer.run` takes EVALUATE's report as a
positional argument, so the ordering is structural), and a notehead's PITCH is
an EVALUATE consequence of the clef. **An inferred clef that nothing
re-evaluates repairs nothing** — the staff keeps its 48 heads and its 48
refusals, and the rule is inert in exactly the way that reads as a clean zero.

**What was built: `evaluate.run_over(log, causes)`** — a SECOND pass over the
same rules, in the same DOWNHILL order, out of the same loop body (`_pass`), in
which a rule fires at a subject **only where its own cause verdict, or a
verdict it DECLARES it also reads, is one of the verdicts INFER just wrote**.
Because INFER writes only where the record had no answer, every rule that fires
in the second pass is one the first pass SKIPPED. On Litolff it fires 376
times: `restate_pitch` 287 and `move_glyph` 89. There is no `while`.

Three details the bound rests on:

* **`move_glyph` declares `reads_beyond_cause`.** Its CAUSE is the ownership
  and its clef comes from the WINNING staff, so a pass keyed on the cause alone
  would silently skip a glyph a contest awarded to the repaired staff — 89 of
  them on Litolff. That is a half-repair that reads as a whole one, and it is
  the `_cause_for` failure (*"reported `cause_absent` and did nothing,
  silently, and identically to a page with no meter"*) one stage over.
* **`restate_pitch` gained one guard: it never overturns a pitch that already
  stands.** ⚠️ FOUND BY THE ARM, NOT BY A HUNCH — the first Litolff run died on
  `glyph/2/1/9/6/2` with `AlreadyAdjudicated`. A glyph cut in the
  abstained-clef staff's cells but awarded to a neighbour had been re-pitched
  by `move_glyph` on the WINNER's clef in the first pass; `restate_pitch` walks
  the staff's position rows and a contest DROPS the loser rather than removing
  its row, so the second pass offered it again — on the clef of the staff it
  had left. The guard is a **provable no-op on the first pass**:
  `restate_pitch` is the first writer of `Q.PITCH` in DOWNHILL order, and the
  Litolff record's only two deciders of that quantity are `restate_pitch`
  (10,618) and `move_glyph` (2,686), which runs after. A positive control
  asserts the first pass still writes every pitch it used to.
* **One loop body for both passes**, so the asserted rule ORDER (`move_glyph`
  after `respell_accidental`) cannot be right in one and wrong in the other.

**Rejected, and why** — recorded on `run_over` itself, because the next person
will reach for one of them:

| alternative | why not |
|---|---|
| move the clef guess into ADJUDICATE | `restate_pitch` would see it in the first pass and none of this would be needed — and the guarantee INFER exists to keep (*everything before EXPORT was READ or ENTAILED*) is gone, with a guess indistinguishable from a reading in the record the cleanup count is adjudicated against. Refused by the roadmap item itself. |
| let EXPORT derive the pitch | the exporter already refuses to argmax a narrowing for the same reason; an interpretation in the writer is one no stage can see and no `basis` records. |
| call `evaluate.run` a second time | it fires every rule at every subject, so `size_measure_rest`, `reconcile_duration`, `name_part` and `join_parts` all re-fire over the whole document and append a second copy of what they already concluded. Not a bounded pass — a doubled record. |

**How the label propagates.** It is a QUERY, not a second flag:
`infer.inferred_in_basis(log, verdict)` walks the provenance closure and
returns the inferred verdicts a row rests on. A pitch restated from an inferred
clef is not itself an inference — `restate_pitch` is a consequence and the
pitch FOLLOWS — but its `basis` names the clef, and the query answers *was a
guess in this chain* from the record alone. Stamping a second `inferred` flag
onto every consequence would make two things that must agree, which is the
`clef_final` failure (9 of 20 stale) in miniature. Both cases are asserted: a
pitch from an inferred clef returns that clef's id, a pitch from a READ clef
returns `()`.

**Where it is wired.** `pipeline.py`, immediately after `infer.run`, over
`infer.inferred_verdicts(log)`. Its report rides INSIDE the `inference` key
rather than as a second top-level one, so `test_infer_bypass`'s property —
*turning the stage on adds exactly ONE top-level key* — survives, and
`OMR_INFER=0 OMR_SLOT_FAMILY_BLOCK=0 OMR_CLEF_GAP=0` still produces a record
byte-identical to one from a tree without the stage.

---

## 8. What the rule DECLINES, and why each decline is deliberate

| state | what happens | why |
|---|---|---|
| clef **DECIDED** | untouched, census says `declined_prior_is_decided` | rule 3 of the stage. Replacing a READING with a guess makes a cleanup count unable to tell a reading fault from an inference fault. Tested adversarially: every other system says alto, this one READ treble, it keeps treble. |
| clef **NARROWED** | untouched, `declined_prior_is_narrowed` | ⚠️ `infer.INFERABLE` admits a narrowing and this rule still declines it. A narrowed clef means `adjudicate_clef` read the staff and could not separate two candidates under its own `MARGIN_FLOOR`; Sean's rule is about a clef that could not be read AT ALL. 15 such on Litolff, so it is a live exclusion — and §5 shows it is now the whole residual population. |
| `Q.SLOT_INDEX` not DECIDED | declines, `declined_part_not_decided` | no part means no other systems to ask and no instrument to name. |
| tier (2) tie for top | abstains, `split` | Sean: *a split abstains*. Not the alphabetical winner, not the nearest system, and **not a fall-through to tier (3)** — that would answer a contested question with weaker evidence than the evidence that failed to settle it. |
| the instrument name is not in `instruments.py` | declines, `declined_no_instrument_name` | |

⚠️ **The identity the rule requires is the SLOT, not `Q.INSTRUMENT`.** Sean's
sentence says *"a part whose instrument is decided"*, and on Litolff
`Q.INSTRUMENT` ABSTAINS on all 9 staves whose clef abstained — the Viola prints
no margin label on those systems, which is the same fault twice over. What IS
decided there is `Q.SLOT_INDEX`, the document-wide part the staff sits on,
whose detail carries the reference's own name for that slot. So the rule gates
on the slot and reads the NAME off whichever verdict carries one.

---

## 9. What was NOT established

1. **Nothing has been checked against the print.** Eight crops exist and Sean
   has read none of them. The rule is default-ON on the mechanism, the controls
   and the funnel's own arithmetic. Every `VERDICT_none_yet` is `null`.
2. **Tier (3) has reach ZERO on all three acceptance documents and is exercised
   only by tests.** Every Litolff gap was answered by tier (2) before the
   convention was consulted; Brahms and the engraved fixture hold no gap at
   all. The convention is registered as `[C88]` in
   `docs/engraving-conventions.md` with status **ASSERTED** and that zero
   written into its *Measured here* field — a convention nothing has measured
   must not read as one something has.
3. **The witness independence is COMPUTED and is not a gate.**
   `independent_groups` returns 14 groups for the slot-9 alto reads, so on this
   document they are 14 signals and not one carried down the page. But
   `adjudicate_clef` has a CARRY term, so on another document they could be
   one, and this rule would still fill — Sean's rule is a majority of reads,
   and an independence floor he did not ask for would have refused the very
   Viola the item exists to repair. The partition and the tally both ride on
   the verdict so the question stays answerable from the record.
4. **The two scan records are from DIRTY trees** (`dbc9962b`, `47fbff1e`, both
   `dirty: true`). Per CLAUDE.md §4b they are not baselines. Every number here
   describes THESE records; a re-gather could move all of them — and a GATHER
   change would be invisible to this instrument by construction, as
   `reinfer.py` says of itself.
5. **No whole-document accuracy figure was taken.** OMR-NED is the engraved
   control only, and the engraved fixture is inert here, so there is nothing
   for it to say. The scan measures in CLAUDE.md §6a are the machine proxies
   above plus Sean's count — this lane moves the proxies and cannot speak to
   the count.
6. **A clef CHANGE is the failure mode neither tier can see.** A bassoon going
   to tenor or a cello to treble is exactly the case where the other systems
   say the wrong thing with a large majority AND the instrument's convention
   agrees with them. Nothing the record holds refutes it, which is why the
   answer is BEST rather than FORCED and why the abstention stays underneath.

---

## 10. What is committed here

```
FINDINGS.md
probe/replay.py              base vs arm on one saved record: INFER + run_over + EXPORT
probe/crop_clef.py           one header crop per inferred clef, frame control imported
probe/remaining_no_pitch.py  the partition in §5
out/litolff.json             every figure in §3, per staff and per system
out/brahms.json
out/engraved.json
out/funnel-base-litolff-p3-s0-st9.json   the §4 gate, BOTH arms, from the funnel's own probe
out/funnel-arm-litolff-p3-s0-st9.json
out/remaining-no-pitch-litolff.json
out/print/*.png + crop-manifest-litolff.json
```

The two whole-movement records (314 MB, 478 MB), the arm records and the
MusicXML stay out of the tree; all of them are regenerated by the commands in
§2.

---

## 11. The code, in one list

| file | what changed |
|---|---|
| `tools/omr/staged/infer.py` | `OMR_CLEF_GAP` + `CLEF_GAP_SWITCH` (deny-list, default ON); `Inference.FILL_CLEF_GAP`; `inferred_in_basis()`. ⚠️ **No harness change was needed**: `INFERABLE` has always held `ABSTAINED`. This is the first rule to use it, and `_admit`'s value bound (rule 4) applies only to a NARROWED prior — so on this path the bound comes from the rule's own evidence instead, which is why it may propose only a clef READ elsewhere in this document or a `default_clef` from the table. *Never overturns a DECIDED one* is unchanged and is tested adversarially. |
| `tools/omr/staged/inferences.py` | `fill_clef_gap`, registered LAST so it runs after the slot rule; `clef_gap_census` holds the whole body so the probe and the rule cannot disagree about the population, the tally or the tier. |
| `tools/omr/staged/evaluate.py` | `_pass` (one loop body, both passes); `run_over`; `Rule.reads_beyond_cause`. |
| `tools/omr/staged/consequences.py` | `move_glyph` declares `_move_glyph_also_reads` (the winner's clef); `restate_pitch` gains the already-stands guard and its `bound` says so. |
| `tools/omr/staged/pipeline.py` | the bounded second pass, after INFER, reported inside the `inference` key. |
| `tools/omr/staged/export.py` | `_inferred_clefs(rec)` and the `inferred_clefs` key in the coverage report — census-side only; no bar, event or refusal code touched. |
| `tools/omr/instruments.py` | `instrument_named(name)`, beside the table it reads. |
| `tools/omr/score_language.py` | its own `instrument_named` — a second linear scan over the same table — now delegates. |
| `tools/omr/conventions.py` | unchanged: the registry PARSES the markdown. The new entry is `[C88]` in `docs/engraving-conventions.md`, and `[C25 + L38]`'s **Code** row now names its first staged consumer for the clef half. |
| `docs/flags-2026-09.md` | `OMR_CLEF_GAP`, both tables. |
| `tools/omr/tests/test_infer_clef_gap.py` | **new, 37 tests.** |
| `tools/omr/tests/test_infer_stage.py` | the flag separation now DERIVED from the registry (a fourth rule fails it loudly rather than sliding past an assertion that enumerated two); `_WithRule` loads the rules before saving them — entering it while `RULES` was empty saved `[]` and restored `[]`, and `_ensure_rules` will not reload an already-imported module, so the stage stayed ruleless for the rest of the process; one SOURCE-TEXT assertion rewritten behaviourally, since `staged.check` counts those and the refactor broke it on correct code (`source_text_tests` 48 → 47). |
