# Handoff, 2026-09-21 evening — the fact sheet, and a correction Sean made that changed the session

⚠️ **READ FIRST, BEFORE BUILDING ANYTHING:**
[docs/ask-first-conventions.md](ask-first-conventions.md) — say out loud how a
HUMAN reads the thing off the page, and what ENGRAVING CONVENTION governs it,
before the first line of code.

On `main`. Tree clean; **48 factsheet tests, battery 24 arms / 24 RED / 0
survivors**, all nine derived checks exit 0.

⚠️ **Read §5 before anything else: Sean ruled on the one open decision the same
evening, it is implemented, and opening it found two further gaps that made the
original one harmless.**

Predecessor: [docs/handoff-2026-09-21-connecting-the-sweep.md](handoff-2026-09-21-connecting-the-sweep.md)
(`effabd20`) — the four-lane integration. **Nothing in it is superseded.**

---

## 1. THE CORRECTION THAT STARTED THE SESSION, AND IT IS THE MOST REUSABLE THING HERE

Asked where the project stood, I said staff identity was the largest loss on
Litolff and framed it as an unsolved READING problem, quoting **41% of
noteheads reaching the file**.

**Sean: *"I thought we were good with staff identity if we used the dossier?"***

He was right and the framing was wrong, in two separate ways:

1. ⚠️⚠️ **41% IS NOT A READING SCORE.** The dominant loss is
   `staff_not_identified` (783 notes), which is `OMR_HOLD_OUT_UNIDENTIFIED`
   **working exactly as designed** — his own call, *"hold out — I want truth"*.
   Those notes were gathered, decided, pitched and arbitrated; they are absent
   because nobody could NAME THE STAFF, and the shortfall is *counted* rather
   than dressed as an orchestra. Quoting it as *how well the page was read* is
   reading the hold-out as a failure.
2. ⚠️⚠️ **THE DOSSIER IS NOT BLOCKED — IT IS UNPLUMBED, FOR A REASON ABOUT
   MEASUREMENT THAT GOT APPLIED TO PRODUCTION.** `gather_external(dossier=…)`,
   `gather_clef_seed` and `Q.DOSSIER_FACT` all exist. What is missing is a CLI
   rung, and `staged/__main__.py:231` says why: *"a dossier is generated from
   the same MusicXML the benchmarks score against … a `--dossier` flag would
   put a truth file inside a measurement path."* **Correct about the gate,
   silent about reading a score** — *A PREMISE ENCODED IN A REFUSAL OUTLIVES
   ITS REASON*, with the scope never having been stated.

⚠️ **AND THE DOSSIER WOULD NOT HAVE SETTLED IT ANYWAY**, which is the half
neither of us had in hand: `dossier.slot_facts_for_system` requires
`len(parts) == n_staves` and ABSTAINS otherwise (`dossier.py:581`). Beethoven 5
encodes **18 parts** and prints **12 staves**, so on every condensed
conductor's page the per-staff tier is silent by design. *Which encoded part
sits on which printed staff* is a property of the **ENGRAVING**, absent from
the MusicXML entirely.

**That is the gap the fact sheet is aimed at, and it is the one a musician
closes in five minutes.**

---

## 2. WHAT LANDED

`tools/omr/factsheet.py` (945 lines), 32 tests, a 17-arm battery.
**Nothing consumes a sheet and no pipeline behaviour changes** — no reader,
adjudicator or exporter is touched. Findings:
[benchmarks/omr-factsheet-2026-09/FINDINGS.md](../benchmarks/omr-factsheet-2026-09/FINDINGS.md).

```bash
python3 -m tools.omr.factsheet draft score.pdf --record rec.json -o sheet.json
python3 -m tools.omr.factsheet show  sheet.json
python3 -m tools.omr.factsheet check sheet.json --record rec.json --write
```

⚠️⚠️ **THE RULE THAT MAKES IT AN INSTRUMENT RATHER THAN A CRUTCH — and it is
the whole reason Sean asked for auto-population rather than a blank form:
every field a human corrects is a recorded DISAGREEMENT with a reader.**
`merge` writes the reader's own answer back as `reader_said`, recovered from
the record on each re-draft, so the human never has to preserve anything.
`report()` is a scorecard of the readers on exactly the facts that gate the
pipeline, collected for free, on whatever document is in front of you.
⚠️ **A DISAGREEMENT COUNT, NOT AN ERROR COUNT.** The first run filed the
CATALOG as wrong because a hand-typed publisher dropped an umlaut.

**PROVENANCE IS THE SHAPE OF THE LEAF.** `"Flute"` is a hand fact,
`{"value": …, "source": …}` a machine one, `null` nobody's answer — so
confirming is *replacing the dict with the bare value*, and you cannot
accidentally mark something confirmed.

| | Litolff Beethoven 5 p1-4 | Breitkopf Brahms 1 p0-3 |
|---|--:|--:|
| facts | 54 | 56 |
| **machine supplied** | **29** | **44** |
| still unknown | 25 | 12 |

One hand pass on the worst document in the corpus — **12 names, 1 bar number,
6 suppression lists** — takes `still unknown` **25 → 0**.

⚠️ **ONE BAR NUMBER PLACES EVERY SYSTEM AFTER IT** and reproduces this repo's
independently hand-verified figures to the bar (p4/s0 at **82**, p4/s1 at
**97**). It **BREAKS** the chain where the reader decided no bar count rather
than carrying a number across a gap it cannot measure.

---

## 3. WHAT IT FOUND IN TWO SECONDS THAT NOBODY HAD WRITTEN DOWN

On Brahms the drafted lineup is **13 of 14 correct**, and the fourteenth is a
live reader fault: the horn staff reads **`'in C 1 2'`** on p0/s0, **`'(C)'`**
and **`'(Es)'`** on p1/s0, and **`'Hr.'` / `'Hr. (Es)'`** on p1/s1 — the
instrument noun truncated away on some systems and not others. That is exactly
`OMR_ROSTER_LABELS`' population (measured at 1.4% of labels, default OFF),
firing on the document every other lane measures on. It is also why the systems
"disagree about the order": **the disagreement is the READER's, not the
edition's.**

---

## 4. WHAT IS NOT ESTABLISHED

- ⚠️⚠️ **NOTHING CONSUMES A SHEET**, deliberately — the `Q.INK` discipline: a
  producer and its first consumer landing together makes the reach measurement
  circular.
- ⚠️⚠️ **NO PRINT WAS CONSULTED BY THIS WORK.** The Brahms lineup is checked
  against the reader's own output; the Litolff fill uses Sean's previously
  committed hand reading. Whether a drafted name is RIGHT is exactly what the
  sheet exists to have a human answer.
- **The six suppression asks are irreducible** from these inputs: knowing a
  system prints 11 of 12 staves does not say WHICH is missing.
- `lineup.full` **assumes the widest system prints the whole lineup.** If every
  system on the pages in hand suppresses something, the real lineup is longer
  and nothing here can tell. Flagged as a check.
- n = **2 documents, 2 publishers, 8 pages, both scans**; the ENGRAVED family
  is untouched. Both shared records PREDATE fixes, so the Litolff draft
  measures a reader that **never ran** (`margin_label` reports
  `not_implemented` on 75 of 75 staves), not one that failed — the sheet says
  so rather than collapsing the two.
- No OMR-NED, because the sheet emits no music.

---

## 5. ⚠️ DECIDED — *"let the dossier only reach the pipeline through a confirmed sheet"*

**Sean ruled the same evening, and it is implemented.** `--sheet` on the staged
CLI is the only rung; **there is still no `--dossier` and there will not be
one**, asserted by a test. The gate is `factsheet.dossier_for`, and it is one
line because the shape rule already did the work: confirming a fact IS
replacing the machine's dict with the bare value, so `source_of == "hand"` is
exactly *a person looked at this*. **The measurement path is now structurally
unable to consume a dossier rather than trusted not to.**

✅ `no_producer --check` goes **`FINDINGS — 1` → `0`** — the tool that found the
missing producer reports it closed.

⚠️⚠️ **OPENING IT FOUND THE PATH HAD THREE GAPS, AND THE SECOND MADE THE FIRST
HARMLESS.** `gather_clef_seed` reads `dossier["clef_by_staff"]` and **not one
of the 97 committed dossiers has that key** — it has always been handed `{}`
and abstained on every staff, because the key is the OUTPUT of the
part-to-staff join while the file holds only the input. **A bare `--dossier`
would have changed nothing and nobody would have known**, since that abstention
reads exactly like a dossier that names no clef. The third: the existing join
returns a LIST where the seed wants a DICT, and is never called from staged.

⚠️⚠️ **AND A GRAFT WAS NEARLY SHIPPED.** The seed looked up
`clefs.get(staff_index)` with one dict for EVERY system; a printed score
suppresses tacet staves, so index 6 is the Timpani on a full system and Violino
I on one that drops it. Both halves are per-system now, with a seam test.
Two independent facts must also reconcile — `len(full) − len(suppressed)`
against the reader's own staff count — and it fired immediately on a
suppression list this session had **invented for a demo**.

⚠️⚠️ **THE SEED IS REDUNDANT WHERE IT CAN BE CHECKED.** Litolff p1/s0: 12 of 12
staves seeded, every clef correct — and **all 12 agree with what the pipeline
already decided.** Six of 75 staff-systems carry no decided clef and whether a
seed fills them is **unmeasured**, because it needs per-system suppression a
human must confirm. **No claim is made that any of this improves anything.**

## 6. WHAT IS NOW OPEN

1. ⚠️ **No sheet has ever driven a real run.** The gate, the join and the seeds
   are measured over committed records and hand data; nothing has been gathered
   with `--sheet`. That needs weights and ~30 min, and it is the first thing to
   do.
2. **Only the dossier→clef path is wired.** The sheet's own facts — the
   lineup, the suppressions, `first_ref_measure` — still reach nothing.
   `adjudicate_instrument` abstains `no_evidence` on 75 of 75 Litolff staves
   while a confirmed lineup sits in a file naming every one of them. That is
   the next consumer, and it is a behavioural change needing its own arm.
3. ⚠️ **An admitted dossier still reaches NEITHER meter nor key signature.**
   `Q.DOSSIER_FACT` is declared in both their `wants` and read by neither.
   Whether it SHOULD is a separate question — the dossier is `source_kind:
   encoding`, so a meter taken from it is not independent of the truth a
   benchmark scores against, even behind the sheet gate.
4. The eight decisions in [docs/symbol-dossiers/INDEX.md](symbol-dossiers/INDEX.md)
   §6. Nothing has been flipped; no default changed, no flag added.

## 6b. RANKED NEXT WORK

1. **One real run with `--sheet`**, to turn every figure here from derived into
   observed.
2. **The truncated margin label.** The sheet found a second independent
   instance on the primary Breitkopf document; `OMR_ROSTER_LABELS` is built,
   measured and default OFF, and now has a fresh population to price against.
3. **Join a chord to its stroke** — carried unchanged, reached from three
   directions: `_stems_on` is too NARROW, not too wide.
4. **The ENGRAVED family for beams** — 430 of 449 legacy edits were `editbeam`,
   and the new `<beam>` emission has never been run there.
5. **A GATHER reader for the in-bar accidental** — 256 and 733 printed glyphs
   reach no quantity at all.

## 7. THE MANAGER'S OWN FAILURES THIS SESSION

- **I gave Sean a wrong framing of where the project stood**, quoting 41% as a
  reading score when it is a hold-out count, and calling staff identity
  unsolved when the dossier tier exists and is merely unplumbed. **He corrected
  it in one sentence.** Same shape as the 09-20 stem lane: *three messages from
  a musician looking at the thing beat four probes and a battery.*
- ⚠️⚠️ **THREE BUGS IN THE NEW MODULE, ALL FOUND BY FILLING A REAL SHEET RATHER
  THAN BY READING IT**, and the tests that existed at the time caught none:
  (a) `source_of` answered `"hand"` for CONTAINERS, so `merge` bailed at the
  top level and merged nothing — **every re-draft silently returned the old
  sheet and the scorecard read a clean ZERO**; (b) a hand-typed
  `suppressed: ["Timpani"]` was **DISCARDED**, because a list-VALUED fact is
  indistinguishable from a list OF facts — the precise failure the module
  exists to prevent, committed by the module itself; (c) suppression was
  derived from a name the lexicon had **REFUSED**, wherever the same raw string
  happened to appear twice. Only (c) was caught by a mutation arm.
- **I ran a mutation battery and edited `tools/` while a full suite was
  running** — both hazards this file documents, in one go. That run was
  discarded and the suite re-run clean; the reported 4,748 is from the clean run.
- A documented figure went stale between measuring and writing (Brahms open
  checks 3 → 8). Caught by re-measuring against the shipped code before
  committing, which is the only reason it is right.
- ⚠️⚠️ **I NEARLY SHIPPED THE 12-OF-75 GRAFT.** `gather_clef_seed` looks up one
  index-keyed dict for every system, and I wired a seed into it without asking
  what index 6 means on a system that suppresses the Timpani. **No test would
  have caught it** — every fixture had one system. What caught it was comparing
  the seed against the pipeline's own clef verdicts and then asking what
  happens on a SHORT system. *Checking beat testing.*
- ⚠️ **I INVENTED DATA FOR A DEMO AND PRESENTED IT AS A RESULT.** The earlier
  acceptance run used `suppressed: ['Oboi','Trombe','Timpani']` for Litolff
  p3/s1 — 12 − 3 = 9 against a reader that counts **8 staves**. It was never
  hand-read; I typed it to make the demo fill. The reconciliation guard now
  refuses exactly that, and it found my own fabrication the first time it ran.
  **The figure "still unknown 25 → 0" rests partly on it and should be read as
  a shape, not a measurement.**


---

## 8. ⚠️⚠️ THE SECOND CORRECTION — AND IT TURNED THE SESSION AROUND

Sean, later the same evening, having read §2:

> *"I thought we had figured out the instrument to line issue. Using the
> natural order of instruments, the list of instrumentation from the score or
> a dossier and the addition of any clefs that could be read as well as family
> brackets — would all add up to clarity of the instrumentation. Did we lose
> that at some point?"*

**He was right, and I had presented the fact sheet as the answer to a problem
that was already solved.** Verified against the tree rather than from memory:

| his signal | declared by `adjudicate_instrument` | actually READ |
|---|---|---|
| margin label | yes | **yes** |
| roster / instrumentation list | yes | yes, but too late to place a staff |
| family bracket | yes | **no** |
| natural order of instruments | yes | **no** |
| clef | yes | **no** |

`adjudicate_instrument` is `labels = ev.rows(Q.MARGIN_LABEL)` and, if empty,
`Ruling.abstain("no_evidence")` — **one channel deep**, with `score_order` in
its own declared `reasons` and no branch that can return it. And his
order-plus-family rule **had** been built, on 2026-09-17, scored **25 of 25
against the print** — and left switched off.

> **You didn't lose it. Most of it was never connected to the reader that
> actually runs — and your own rule was built, measured, and left switched
> off.**

Then, in one sentence:

> *"Flip on the previous work and redo our work tonight to be an option to
> turn on when we can't get the info we need."*

Two changes pulling in opposite directions. Both are in. Findings:
[benchmarks/omr-infer-default-2026-09/FINDINGS.md](../benchmarks/omr-infer-default-2026-09/FINDINGS.md).

### 8a. The flip — and why it could not be one word

`collapse_slot_index_to_family_block` shared `OMR_INFER` with two DURATION
rules **neither of which has had a single note checked against a page**. So
raising the flag to ship a print-verified rule also shipped two unverified
ones, and lowering it to keep those off also kept the verified one off.
**One switch, two evidential weights, and the stronger one lost** — not a
decision anybody took, a consequence of the registry having one dial.

Each rule now carries its own `Gate` (flag name + predicate as ONE object, so
a report can name the flag that held a rule back without a second table):

| rule | flag | default |
|---|---|---|
| `collapse_slot_index_to_family_block` | `OMR_SLOT_FAMILY_BLOCK` | **ON** |
| `collapse_duration_by_column` | `OMR_INFER` | off |
| `collapse_duration_to_barline` | `OMR_INFER` | off |

⚠️ **The two predicates are written out separately and a shared helper was
REFUSED** — `test_flag_default_direction.py` finds flags by AST, and a helper
taking the name as a PARAMETER would hide both. Confirmed present in the scan
(`OMR_SLOT_FAMILY_BLOCK  default '1'  NotIn {...}  -> default-ON`) rather than
assumed; that guard has been blind to two flags before.

**Measured**, base-vs-arm on ONE tree: `slot_index` decided **55 → 70**,
narrowed **20 → 5**, **15 inferred**, and **0 verdicts outside `slot_index`
moved**. It reproduces the rule's own published funnel from a different
record, tree and instrument.

### 8b. The sheet demoted to a fallback

`adjudicate_clef` admitted a supplied clef at **`W_DOSSIER` = 4.0 against
`W_DETECTOR_HIGH` = 3.0**, so tonight's sheet did not corroborate a read clef
— **it replaced it**, silently, including where the reading was right and the
sheet held a typo. Now **GAPS ONLY**, the `adjudicate_key_signature`
precedent, with the refusal recorded on the verdict.

⚠️ **A refusal to speak, not a weight change.** Lowering `W_DOSSIER` would
still let a sheet out-vote a PAIR of weak read terms, and would weaken it on
the honest case. The ordering is pinned by a test so the rule cannot later be
deleted as redundant.

### 8c. ⚠️ THREE THINGS WORTH CARRYING

1. **A shared record is a snapshot of the reader that made it.** The first
   measuring arm reported **0 reach** — `beethoven5-p1-p4.record.json` holds
   **0 margin labels and `instrument` abstaining on 75 of 75**, because it
   predates the `pdf_path` repair. The `-ink-identity` record holds 50 labels.
   **The two Litolff records differ by more than a date.**
2. **`block_arm.py`'s control fails on today's tree (12 of 75) and was NOT
   weakened.** CLAUDE.md recorded that morning that the shared records can no
   longer license a rebuild; widening that control until it passed would be
   *a control that computes the wrong thing*, on purpose. A separate arm asks
   the smaller question and says so in its own docstring.
3. **I claimed seven new tests went red against the old code and three did.**
   Caught by running the red proof instead of asserting it — the docstring is
   corrected in place and now names which four are controls and why.

### 8d. WHAT IS NOT ESTABLISHED

- **No print was consulted on the evening's work at all.** The flip's
  correctness rests entirely on the 2026-09-17 crop pass.
- **No supplied clef has ever been scored against a print**, so 8b says the
  seed no longer overrides a reader and nothing about whether the staves it
  now declines were being helped or harmed.
- **No export, no file, no OMR-NED** — the arm stops at the verdicts.
- **Breitkopf has NO population for the flipped rule** (0 abstentions — that
  plate labels nearly every staff), so a second publisher can neither
  corroborate nor refute it.
- ⚠️⚠️ **THE TWO CHANGES INTERACT AND THE INTERACTION IS UNMEASURED.** Both
  assign instruments to lines. No record in the tree carries a `clef_seed`
  row, so nothing has ever run them together.

### 8e. RANKED NEXT WORK, AFTER THIS

1. **Give `adjudicate_instrument` a second channel.** It is the actual answer
   to Sean's question and nothing above touches it: today a staff with no
   margin label exits identification after ONE reader, and `score_order` is a
   declared reason with no branch. This is *A PREMISE ENCODED IN A REFUSAL
   OUTLIVES ITS REASON* with a name already in the vocabulary.
2. **One real run with a sheet**, so the two evening changes are measured
   together rather than separately.
3. **A crop pass on the 15 inferred placements**, which would make the flip's
   correctness a fact about today's tree rather than an inheritance.
