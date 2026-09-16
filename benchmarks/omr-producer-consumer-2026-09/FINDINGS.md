# Does the information reach its consumer? — a derived check, and the second missing producer

2026-09-15. No flag. Branch `claude/info-reaches-its-consumer`.

```bash
python3 -m tools.omr.staged.wiring                 # the four tables
python3 -m tools.omr.staged.wiring --check         # non-zero on anything unaccounted
python3 -m tools.omr.staged.wiring --run rec.json  # corroborate FRAME from a record
python3 benchmarks/omr-producer-consumer-2026-09/roster_reach.py
python3 benchmarks/omr-producer-consumer-2026-09/mutate.py
```

Committed beside this file: `wiring.txt` (the tool's own output on the tree
that shipped), `roster-reach.txt`, `mutate.txt`.

---

## 1. Why an instrument, and why now

*The value existed and nothing read it* has been found in this repo **ten or
more times, every one of them by accident**. `Q.STEM` gathered and read by
nothing — 916 rows, inside the decision whose own docstring calls the beam
level its fragile input — **found three separate times**. `pipeline.run_staged`
taking `pdf_path`, rasterising with it and dropping it, so
`gather_margin_labels` filed `not_implemented: "no pdf_path supplied"` on **75
of 75 staves, on every staged run this repo has ever made**. `Q.METER`'s
`segments` reaching no file while `record.meter_at`, whose own docstring says
it *is* how a bar's meter is read, was called by nothing but its own tests.
`adjudicate_dynamic` deciding and filing a verdict per cell while
`grep '<dynamics' export.py` returned **0**.

The 2026-09-11 handoff, after the second missing producer in two days, wrote
the conclusion this session implements: ***"Worth a derived check rather than a
third discovery."***

`tools/omr/staged/wiring.py` asks three of the six questions the brief listed.
Which three, and why the others are not here, is §7.

⚠⚠ **AND ONE OF THEM WAS BUILT TWICE.** *A parameter threaded with no
supplier* is **`tools/omr/no_producer.py`**, which a sibling session landed on
main the same day — derived from the AST over the whole of `tools/`, finding
`pdf_path` and `roster` with no hint. This session built its own before
merging main, and it was a DUPLICATE: **CLAUDE.md states the rule and this
session did not follow it** — *`git log --all --oneline -S "<the thing>" --
tools/omr/` before building anything*, written there after the hairpin export
was built twice. ~200 lines were written and deleted. The question is theirs;
what survives here is the roster REPAIR, which **closes one of their tool's
own open findings** — their entry said *"REMOVE THIS ENTRY the day a producer
lands"*, and their stale-entry test is what made it leave.

---

## 2. What the check found

Numbers are the tool's, on the tree that shipped (`wiring.txt`).

| question | examined | healthy | **findings** |
|---|--:|--:|--:|
| **FRAME** — a declared input read where it is never filed | 81 declared reads | 31 EXACT + 50 scoped | **0 broken, 6 LATENT**, 1 repaired |
| **DETAIL** — a key written on a row and named nowhere else | 113 keys | 91 read | **22 written and unread** |
| **ROUNDTRIP** — a field dropped by its own `to_json` | 9 classes, 56 fields emitted | — | **1, and it is READ** |

Plus **11 gather sites whose subject Kind cannot be derived statically**, over
**3 named shapes** — reported rather than dropped, each on `KNOWN_GAPS` with
the reason it cannot be derived.

### 2a. PRODUCER — moved out, and the repair stayed

The question is `tools/omr/no_producer.py`'s (above). Its finding stands
exactly as that tool states it: `roster` was threaded `run_staged` ->
`run_staged_on` -> `gather` -> `gather_external`, **forwarded at every link
and supplied by nobody**, so `Q.ROSTER_ENTRY` was dead on every staged run
this repo has made. §3 is the repair; `dossier` is the same shape and stays
open, deliberately (§6).

### 2b. FRAME: zero broken, six traps armed for the next person

**Nothing in the tree today reads a declared input at a Kind where nothing
files it.** The four instances CLAUDE.md records were each repaired.

What the check adds is the tier that did not exist: **LATENT** — a `wants`
entry that is INERT *and* whose quantity is filed only at a Kind
`Scope.EXACT` cannot reach. Those are not bugs today; they are **traps armed
for whoever closes the inert declaration**, and they are visible before the
consumer is written.

| decision | declares | scope | filed at | closing it needs |
|---|---|---|---|---|
| `adjudicate_clef` | `Q.NOTEHEAD_STAFF_POSITION` | staff | glyph | `subject=` |
| `adjudicate_key_signature` | `Q.DOSSIER_FACT` | staff | document | `SELF_AND_ANCESTORS` |
| `adjudicate_meter` | `Q.DOSSIER_FACT` | system | document | `SELF_AND_ANCESTORS` |
| `adjudicate_part_partition` | `Q.INSTRUMENT` | document | staff | `subject=` |
| `adjudicate_part_partition` | `Q.STAFF_ORDINAL` | document | staff | `subject=` |
| `adjudicate_system_membership` | `Q.GAP_BRIDGING` | system | page | `SELF_AND_ANCESTORS` |
| ~~`adjudicate_instrument`~~ | ~~`Q.ROSTER_ENTRY`~~ | ~~staff~~ | ~~document~~ | **closed, §3** |

⚠️ **`adjudicate_part_partition declares Q.INSTRUMENT` IS RANKED WORK, NOT A
PERMANENT GAP.** The Phase 2 part-join finding is that *a short system must
pair by INSTRUMENT NAME*; the identity is on the STAVES and that decision runs
at DOCUMENT. So the repair the handoff ranks next needs `subject=` per staff,
and a bare `ev.rows(Q.INSTRUMENT)` would return nothing — silently.

⚠️⚠️ **COLLAPSING "READ WITH ITS OWN REACH" INTO "NOT READ" MADE THE FIRST
DRAFT REPORT 28 FALSE TRAPS.** A SYSTEM-scoped decision reading `Q.EVENT`,
filed at CELL, looks broken and is not: it reads DOWNWARD through an explicit
`subject=` or `scope=`, which is correct and common (46 such reads). A read
carrying either kwarg has its reach decided by an expression the tool cannot
evaluate, so it is **excluded from the verdict rather than guessed at**.

### 2c. DETAIL: 22 keys written on a row and named nowhere else

The finest grain of the same fault — the one `Q.METER_GLYPH`'s `letter` flag
lived in for months. Every one is inventoried in `wiring.KNOWN_GAPS` with what
it would take; three are worth naming here.

- **`Q.MARGIN_LABEL.reader_confidence`** — the reader's own confidence in the
  label, and **the decision that names the staff does not look at it**.
  `adjudicate_instrument` takes `labels[-1].value`, the LAST row rather than
  the best-read one. The slot-index work records `Obol.` reading at `low`
  confidence on a real page, and this project's history records `Tr. Alt.`
  resolving to a SINGER at HIGH confidence — so the field is neither useless
  nor sufficient. ⚠️ **Not repaired**, and the reason is this repo's own rule:
  detection confidence reaching a decision is Class D of the probability
  taxonomy, and an uncalibrated number consumed as evidence measured ECE
  0.1277, *worse than none*.
- **`Q.DIRECTION_WORD.page_n_read` / `page_n_candidates` /
  `page_n_rejected_by_lexicon` / `page_state` / `split_is_page_level` /
  `page_conflicts`** — CLAUDE.md already names the job: *"the ranked next step
  is to move the two OCR rungs into the record as INDEPENDENT readings — today
  `read_directions` returns only winners, so a refused candidate cannot be
  split into `the decoder was silent` and `the lexicon refused`."* **These six
  counters ARE that split, written and consumed by nothing.**
- **`Q.KEYSIG_RUN_POSITION.clefs_tried`** — the comment at the write site says
  in terms that it separates *a run that fits NO slot table* from *a header
  with no run at all*. Nothing reads the field that makes the separation.

⚠️ `*.mirror` (3 keys) is the one class arguably right to be unread: it marks
a row reproducing a LEGACY path, for a human auditing the two against each
other. Provenance for a reader, not evidence for a decision.

### 2d. ROUNDTRIP: one field, and a saved record cannot carry it

Added after a sibling agent surfaced the instance independently. **The check
reproduces it from the tree with no hand-listing**, which is the proof the
question is live:

> `Verdict.single_pass_revision` is declared at `record.py:835`, **READ by the
> fixpoint guard at `:1026`**, and **absent from `Verdict.to_json`**.

So the field cannot survive a round trip: a replayed record comes back
`False`, and the guard's one sanctioned exemption — the
durations -> meter -> durations loop `reconcile_duration` is explicitly
allowed — is silently not there. **No saved record can be replayed through
that guard as written.** This is the `works.json` `lines` fault one layer in,
where the producer and the projection sit in one class so the comparison is
exact.

⚠️⚠️ **THE FIRST CUT COMPARED KEY NAMES AND REPORTED A RENAME AS A DROP.**
`Witness` emits `self.row_id` under the key `"row"` — the field survives the
round trip perfectly, and a name comparison calls it dropped. **A check that
cannot tell a RENAME from a DROP has one false positive per renamed key and
trains the next reader to skim the list.** The question compares the field's
VALUE (`self.<field>` appearing anywhere in `to_json`), not its key.

⚠️ **REPORTED WITH ITS PRICE AND DELIBERATELY NOT REPAIRED**, on the finding
agent's own reasoning: adding a key to `Verdict.to_json` changes EVERY record
this repo writes, so every byte-identity control over a record — and this
project runs several, including `regather_control.py`, which exits non-zero on
a mismatched pair — would report a difference that is not the change under
test. That is the *perturbs upstream by existing* hazard. **Pricing it is
Sean's call.** A test pins the current behaviour against `Verdict.to_json`'s
own output, so a later session cannot quietly repair it and leave the
reasoning behind.

---

## 3. The repair: the roster reaches the decision

Three legs, because the fault was three faults wearing one name.

**(1) THE PRODUCER.** `staged/__main__.py` gains `--work-id` and
`--no-roster`, and resolves through `work_roster.roster_for_pdf(pdf)` — which
honours `OMR_WORK_ID` and **abstains (returns `None`) for any PDF the store
does not hold**. On by default, because the default is a no-op everywhere it
has no business acting.

**(2) THE FRAME.** `Q.ROSTER_ENTRY` is filed on the **DOCUMENT** — it is a
fact about the WORK — and `adjudicate_instrument` runs at **STAFF**. The
obvious `ev.rows(Q.ROSTER_ENTRY)` would have returned nothing forever, with
the declaration present, the quantity gathered and the `wants` entry
satisfied. It reads `scope=Scope.SELF_AND_ANCESTORS`. **The check flagged this
as LATENT before the line existed**, which is the tier earning its keep on its
first day.

**(3) THE CONSUMER.** `work_roster.decide` is **imported, not restated** — the
measured rule, 28 firings over 1,422 real margin labels, every one
hand-adjudicated correct, with four outcomes whose risks differ and an ORDER
between them that was measured (recovery before disambiguation; the other
order reads `mbone Basso` as a Contrabass, confidently and wrongly).

⚠️ **THE REASON WORD WAS ALREADY RESERVED.** `roster` has been a declared
reason of `adjudicate_instrument` since the day it was written, and nothing
could ever return it. *A vocabulary word with no branch* — the same fault one
layer up from a parameter with no producer, and the third documentation shape
this repo has recorded after *fixed-then-kept-open-in-prose* and *a rule
described in a docstring and never built*.

⚠️ **SEAN'S RULING IS WHAT PUT IT IN ADJUDICATE** (handoff §7): *"ADJUDICATE
takes the roster; INFER does not need it."* The structural argument is
CLAUDE.md's own — *if you want a second witness that does not fall silent
exactly when it is needed, it must not come off the same raster.* A roster is
`source_kind: "catalog"`, read off the work's IMSLP page, and **does not go
silent when the scan is bad**.

⚠️ **`source_kind` IS RE-CHECKED AT THE POINT OF USE, and that is not
belt-and-braces.** `work_roster()` enforces the tier when it BUILDS a roster
from the catalog; **nothing enforced it on a row that arrived some other
way**, and the `editions` tier is `source_kind: "page"` — an OMR output of the
same raster.

⚠️ **A VETO NAMES WHAT IT LOOKED AT, AND `Ruling.abstain` CANNOT.**
`Ruling.abstain` takes no `used`, so an abstention it builds names **nothing**
— and an abstention CAUSED by a roster row that cannot name that row is a
refusal with no provenance. The veto constructs its `Ruling` directly (still
an abstention by `abstained`'s own definition) so the roster row lands in
`Verdict.basis`, where the circularity filter and every later reader need it.

### 3a. REACH — measured

See `roster-reach.txt`. Every figure is the probe's.

⚠️⚠️ **THE PROBE DRIVES THE STAGED DECISION, NOT `work_roster.decide`.** The
RULE was measured a week ago. What was never measured, because it could not
happen, is the rule ARRIVING. A probe calling `decide()` directly would
re-measure the rule and say nothing about either fault.

**THE DECISIVE CASE, and it closes a defect a sibling session recorded and
explicitly left open.** Litolff Beethoven 5 is the document the whole Phase 2
cleanup count is taken on; `work_id_for_pdf` resolves its PDF to
`beethoven--symphony-5`, whose catalog roster is 10 instruments at
`parse_rate 1.0`, `source_kind: catalog`, `complete=True`. Driving the staged
decision on the label the page prints at slot 11:

| | verdict | reason | roster outcome |
|---|---|---|---|
| WITHOUT a roster | **`Bass voice`** | `label` | `unchanged` |
| WITH the roster | **`Contrabass`** | `roster` | `disambiguated` |

That is exactly the row `benchmarks/omr-slot-index-2026-09/FINDINGS.md`
records as *"a separate defect, found in passing and NOT fixed: the reference
reads slot 11 as **`Bass voice`** (the page prints `Basso.`) — a singer on an
orchestral score, the trap this file documents at length."* The rule to fix it
already existed and had already been measured; **what was missing was three
wires.**

⚠️ **REACH IS SMALL AND THE CEILING IS THE CATALOG, NOT THE RULE.** The
catalog holds 223 works, all `source_kind: catalog` — but a roster only
reaches a document the store's editions map can join to one. `roster_for_pdf`
ABSTAINS otherwise, which is every generated fixture and every upload, so the
layer is a **no-op on the eleven-work engraved benchmark** unless a harness
sets `OMR_WORK_ID`.

**THE TWO ARMS, in full** (`roster-reach.txt`):

| arm | labels | works with a roster | verdicts compared | **moved** |
|---|--:|--:|--:|--:|
| cleanup-count pages (Litolff Beethoven 5 p.1-4) | 50 | 1 of 1 | 50 | **1** |
| the lexicon corpus | 1236 | 6 of 6 | 1236 | **20** |

On the lexicon corpus the outcomes are `unchanged` 1216, `recovered` 17,
`disambiguated` 3 — the 17 are Ravel's `Violoncelles` truncations (which the
lexicon abstains on) recovering to **Cello**, the 3 are `Basso.` to
Contrabass on Beethoven 5.

⚠️ **THAT 20 OF 1236 REPRODUCES THE LEGACY LAYER'S OWN RECORDED FIGURE.**
CLAUDE.md states `OMR_ROSTER_LABELS` as *"20 of 1422 real margin labels change
(1.4%)"*; the staged wiring, over the subset whose work the catalog holds,
moves 20 of 1236. **The rule was already measured; what this session added is
that it ARRIVES.**

⚠️ **150 labels are EXCLUDED, NOT SKIPPED**, and the probe says which: five
sources whose work the catalog does not hold or whose id could not be derived
(`mahler5-local-scan` 135, `handel-messiah` 32, `bach-wtc1` 4,
`dvorak9-simrock-scan` 15). **A denominator that quietly shrinks is how a
reach figure flatters itself.**

⚠️ **IT IS SLOW FOR A DOCUMENTED REASON**: `instruments.lookup` costs ~0.6 s
on a string that matches NOTHING (it walks ~400 aliases twice, compiling a
regex per alias), and Ravel's dump is 427 LaTeX-mangled Surya strings that
match nothing — x2 arms, x2 decisions that each call it. ~55 min of CPU.

---

## 4. Things the instruments did to themselves

⚠️⚠️ **THE TOOL'S OWN GAP LIST SILENCED THE TOOL, AND THE QUESTION WENT TO
ZERO.** The DETAIL question decides a key is read if any file under `tools/`
names it. Writing each of the eighteen unread keys into `KNOWN_GAPS` **with
its reason** put every one of those names into a file under `tools/` — and the
question that had just reported eighteen findings reported **NONE**. *The
inventory written to account for the findings closed the check that produced
them.* The vacuous-assertion family arriving inside the tool built to catch
it, one turn after its own docstring quotes `health.py` reporting *"EMPTY
CELLS: none"* by accident. A gap list naming a key is not a consumer of it,
for the same reason a test naming one is not — **both trees are now excluded,
and the count went 18 -> 22 when they were**, because four keys had been
counted as read on the strength of a test mentioning them.

⚠️ **THE REACH PROBE'S WORK-ID MAPPING WAS HAND-TYPED AND EVERY ENTRY WAS
WRONG.** I wrote out `beethoven--symphony-5-op67` — the library's *directory*
name — where the catalog keys on **genre + number**, `beethoven--symphony-5`.
The arm reported *"works the CATALOG holds a roster for: 0"* on the very
document the repair was built for. ⚠️ **It reported that rather than reporting
zero MOVES**, which is the reach-first rule paying for itself — a dead
instrument that announces it is dead. But it is still a hand list inside a
probe for a tool whose entire thesis is *derive, never hand-list*, and it took
a `work_id_for_pdf` call to notice. The ids are derived now; what survives by
hand is only the IMSLP number, which is in the source string.

⚠️ **THE STALE-GAP TEST FIRED ON THE REPAIR, AS DESIGNED.**
`inventory.KNOWN_GAPS` carried `"instrument declares 'roster_entry'"` and
`test_a_CLOSED_gap_must_LEAVE_the_list` went red the moment the declaration
stopped being inert. *A closed gap must LEAVE, or the list stops describing
the pipeline and starts describing its history* — enforced rather than
remembered, and it worked without anybody remembering to look.

⚠️ **A CROSS-REFERENCE IN A GAP LIST MUST NAME ITS REFERENT.** "as the row
above" is a POSITIONAL reference into a dict and stops being true the first
time an entry is inserted — the same shape as the anchored markdown insertion
that orphaned a sentence in CLAUDE.md and cost two sessions a false `git
blame` diagnosis. The test now requires a backticked name.

⚠️ **AND THE FIRST REACH RUN BURNED 28 MINUTES OF CPU ON A 427-STAFF
"SYSTEM".** Ravel's dump is 427 labels over many pages; putting them all in
one `Q.SYSTEM_STAFF_COUNT` makes `adjudicate_part_partition` and
`adjudicate_slot_index` do work no printed page ever asks for. Chunking at 24
is both faster and more faithful — and changes no verdict, because
`Q.INSTRUMENT` depends on the staff's own label and the DOCUMENT's roster,
neither of which crosses a chunk. ⚠️ The process was at **99.9% CPU**, not
wedged: this repo's own rule that *a frozen CPU clock is the picture that
reads as a hang* has a converse, and a busy one can still be doing the wrong
work.

---

## 5. What was repaired

| | |
|---|---|
| `roster` given a producer | `--work-id` / `--no-roster` on the staged CLI, default on |
| the roster read at the right scope | `Scope.SELF_AND_ANCESTORS`, flagged LATENT before the line existed |
| the roster actually consumed | `work_roster.decide` imported; `roster` reason now reachable |
| the veto names its evidence | `Ruling` constructed directly so `used` survives |
| `source_kind` enforced at the point of use | `identity._work_roster` refuses a non-`catalog` row |
| the record is parseable | `Q.ROSTER_ENTRY` carries a dict, not a dataclass `repr()` |
| `inventory.KNOWN_GAPS` | the now-closed `instrument declares 'roster_entry'` removed |

---

## 6. What was found and deliberately NOT repaired

- **`Verdict.single_pass_revision`** — §2d. Reported with its price, on the
  finding agent's reasoning. **Sean's call.**
- **`dossier` has no producer and stays that way.** A dossier is generated
  from the same MusicXML the benchmarks score against, so the scan gate is
  dossier-free **by protocol** — a `--dossier` flag would put a truth file
  inside a measurement path. Two LATENT frame traps hang off it
  (`adjudicate_meter`, `adjudicate_key_signature`), both inventoried so
  whoever wires a dossier for a non-measurement purpose does not step in them.
- **The 22 unread detail keys.** Each is its own job with its own reach, and a
  detail key is only worth wiring against a decision that wants it — choosing
  which is a separate judgement from finding them.
- **The 6 remaining LATENT frame traps.** Closing an inert declaration is
  `inventory --check`'s question and a behaviour change, not a wire.
- **11 unresolvable gather sites.** `Subject.from_key(k)` puts the Kind in the
  key at runtime; `sub` and `g` are unpacked from collections. Deriving them
  would mean tracing which collection the key came from, and **a wrong answer
  there is worse than none** — it would file a quantity at a Kind nothing
  files it at and manufacture a FRAME finding against working code. `--run`
  resolves every one from a record's own subject keys.

---

## 7. Which of the six questions this does NOT reach

| # | question | where it stands |
|---|---|---|
| 1 | a parameter threaded with no producer | **asked here** (PRODUCER) |
| 2 | a quantity declared and never gathered, or gathered and never read | **already owned** by `gather_coverage`; not duplicated |
| 3 | a `wants` entry the body never reads | **already owned** by `inventory._never_read`; LATENT builds ON it |
| 4 | a declared input read at a SCOPE that cannot reach it | **asked here** (FRAME), and asked by nothing else |
| 5 | a verdict DECIDED that reaches no file | ⚠️ **NOT REACHED** |
| 6 | a field dropped by a projection | **partly** — ROUNDTRIP at class grain, DETAIL at row-field grain; NOT at cross-module projection grain |

⚠️ **(5) IS NOT REACHED AND THE REASON IS STRUCTURAL, NOT LAZINESS.**
`export.status_census` already answers it **at run time**, as a PARTITION with
an `unaccounted` bucket a test requires to be empty — and CLAUDE.md is
explicit that the census is what to use because `decided_but_unwritten` is a
FILTER and *a filter cannot say where a family WENT*. A static twin would have
to model which renderer writes which element, which is the exporter's control
flow, and it would be a second answer that can disagree with the census — two
records of one thing that nothing forces to agree. **(5) has an instrument and
it is not this one.**

⚠️ **(6) IS ONLY PARTLY REACHED, EVEN WITH ROUNDTRIP.** ROUNDTRIP compares a
class's declared fields against its OWN `to_json`, which is exact because
producer and projection sit together. The `works.json` `lines` case is
different: a field computed on the way in and dropped by **four separate
projections** in four different modules, each of which NAMED it. **A general
projection checker needs to compare a producer's output keys against a
consumer's input keys across a serialisation boundary, and nothing here does
that.** Ranked, not built.

---

## 8. Controls

- **Positive controls, asserted rather than printed.** Each question reports
  how many cases it found HEALTHY, and `--check` exits **2** — before it looks
  at a single finding — if any is zero. A question that can only ever answer
  "nothing wrong" is not a question, and this repo has shipped exactly that
  three times (`health.py`'s "EMPTY CELLS: none", the flag-direction guard
  descending through `environ.get`, `gather_coverage`'s anti-drift guard
  comparing `events` to `Q.EVENT`).
- **`--check` is green on this tree**: 41 problems, **0 unaccounted, 0 stale**.
- **Mutation battery**: `mutate.py`, **18 arms, all RED, 0 survived, positive control GREEN** (22 before the four producer arms left with their question).
  ⚠⚠ **Its first run reported ONE genuine survivor and it was the better
  camouflage fault**: `test_an_unresolvable_subject_is_NAMED_never_defaulted`
  is NAMED for the hazard and reached only the `Call` branch — defaulting an
  unbound local Name to `'staff'` left it GREEN. *The name is what a reviewer
  trusts and the only part they cannot check by reading.* Closed, and the arm
  is red. ⚠ The run also mis-counted: the positive control was listed beside
  the survivors as *"2 survived"* when there was one — the kind of miscount
  that gets a genuine gap waved through. It is now reported apart.. Anchors are checked
  for **exactly one** occurrence and an ambiguous anchor is an ERROR, never a
  silent pass — the fault that made the fermata battery mutate a different
  function and the part-join battery pick the wrong of two `pdf_path`
  forwards. It also **refuses to run on a dirty tree**, because a battery that
  `git checkout`s a dirty file destroys work and cannot tell its own mutation
  from yours.
- **Full suite**: SUITE_PLACEHOLDER. `no_producer --check`,
  `inventory --check`, `gather_coverage`, `health --check` and
  `wiring --check` all exit 0.

---

## 9. What is NOT established

- **Accuracy.** Nothing here was checked against a print. A `vetoed` row is a
  claim that the lexicon was wrong, adjudicated by the rule's own recorded
  reasoning; **the one thing that would settle it is the crop.**
- **That the roster helps the file.** No MusicXML was exported and no metric
  was run. `<part-name>` is not scored by musicdiff, which is why the roster
  layer has never had a pooled figure and does not get one here.
- **Anything about a staged run.** The reach arms read COMMITTED label dumps;
  no page was re-gathered, and **the staged path has NOT been run end to end
  with a roster on this branch.**
- **That the FRAME question is complete.** It judges only reads whose reach is
  fixed by the decision's own declaration — 30 of 76. The other 46 carry a
  `subject=` or `scope=` this tool cannot evaluate, and a frame fault inside
  one of those is invisible to it.
- **That ROUNDTRIP covers serialisation.** It asks about `to_json` only. A
  class with no `to_json`, or a field dropped by a DIFFERENT module's
  projection, is out of its reach.
