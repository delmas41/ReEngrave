# The convention registry gets a machine-readable handle

2026-09-20. `tools/omr/conventions.py`, its tests, a 24-arm mutation battery
and one audit probe. **No adjudicator is touched, nothing is wired into any
decision, and no convention's CONTENT is edited.**

---

## ASK-FIRST

**CONVENTION ASSUMED.** That an entry's own source tag — `[C34 + L46]` — is a
stable handle: that the two harvest files' numbering (`C1`–`C87`, `L1`–`L79`)
is historical and will not be renumbered, and that it is therefore a better
identifier than a position or a title.

**WHAT WOULD FALSIFY IT.** Someone renumbering `docs/conventions/from-this-repo.md`
or `from-the-literature.md`, or a future entry being added to the merged
registry with no source tag at all — the second is the likelier, and it
lands as a parse finding (`SOURCE ENTRY VANISHED` / no entry at all) rather
than as a silent renumber, because the tag line is the discriminator that
makes a heading an entry.

**NOT CONFIRMED WITH SEAN.** The ID scheme itself; that `Testability` is a
useful axis at all given it comes out degenerate (below); whether the three
prose figures in §5 should be corrected in the document or left with this
note beside them. **No convention was reclassified, reworded or removed.**

---

## 1. REACH — and it is not a partial parse

```
     114  entries_parsed
     114  entries_with_all_fields
     166  source_tokens_resolved
     114  statuses_resolved
       5  refuted_found
     109  testable_found
      20  anchors_referenced
      16  claims_parsed
     166  conservation_rows
      11  contents_rows
       5  failed_table_rows
```

**All 114 entries parse and all 114 carry all ten required fields** — `Says`,
`Predicts (mechanically)`, `Numbers`, `Literature`, `Measured here`, `Status`,
`Rigid or publisher-dependent`, `Would be falsified by`, `Known exceptions`,
`Code`. Field coverage is 114/114 on every one of the ten; there is no
partially-structured entry in the document.

⚠️ **The positive control is checked BEFORE any finding is reported**, and
`--check` exits **2** when any reach number is zero. A parser that matches
nothing reports a clean registry — which is exactly what `gather_coverage`'s
anti-drift guard did when it compared names for equality, matched none, and
left a closed finding open in four documents.

---

## 2. THE ID IS DERIVED, NOT ASSIGNED

Each entry already prints its own source tag on the line under its heading.
The **first token** of that tag is the id: `C1`, `L3`, `C77`. It is not
positional, so reordering the document cannot renumber anything, and it is not
the title, so rewording a heading cannot either.

It is unique **by measurement, not by assumption**: 114 entries carry 166
source tokens, covering `C1`–`C87` and `L1`–`L79`, **each exactly once, with no
gap and no surplus**. That is what makes *"an ID that vanished"* a derived
finding instead of a pinned list — a missing number in either range is
reported by name, and so is a token claimed by two entries.

Lookup: `by_id("C34")`, `by_source("L46")` (the entry that ABSORBED that
source entry), `by_slug(...)` (the document anchor).

---

## 3. WHAT THE GRADES ARE, AND THE ONE THAT CAME OUT DEGENERATE

| grade | n |
|---|--:|
| **Status** MEASURED HERE | 67 |
| **Status** LITERATURE ONLY | 27 |
| **Status** ASSERTED | 13 |
| **Status** REFUTED HERE | 5 |
| **Status** ENCODING | 2 |
| **Refutation** none | 100 |
| **Refutation** internal caveat | 9 |
| **Refutation** whole entry | 5 |
| **Testability** testable against ink | 109 |
| **Testability** refuted | 5 |

⚠️⚠️ **`Testability` IS DEGENERATE AND THAT IS THE HONEST RESULT, NOT A
DESIGN.** The brief asked for three buckets — mechanically testable, *usable
only when writing music*, refuted. Reading all 114 `Predicts (mechanically)`
rows, **not one is engraving-side only**: every entry states a prediction a
reader can check against ink, and every entry carries a concrete falsifier.
So the axis collapses to `114 − 5 refuted = 109`, and the *writing-only*
bucket is **EMPTY**. No classifier was invented to populate it. A keyword
grader over those rows would have produced a bucket that looks informative
and is a property of the grader.

⚠️ **`Testability` and `Status` are orthogonal and conflating them is the
never-promote violation.** `TESTABLE_AGAINST_INK` says *a test can be
written*; it does **not** say the claim has been checked on a plate. Only
`Status` says that, and 40 of the 109 testable entries are LITERATURE ONLY or
ASSERTED.

---

## 4. A REFUTED ENTRY CANNOT BE READ AS A LIVE RULE — enforced, not described

Three mechanisms, each with a mutation arm:

1. **`rule_text()` RAISES `RefutedConvention`** on all five entries refuted
   outright. `.says` still returns their text, because evidence is never
   thrown out with the behaviour — but the accessor a consumer reaches for
   refuses.
2. **`measured_figure()` RAISES `NotMeasuredHere`** on a LITERATURE ONLY or
   ASSERTED entry. *Never promote LITERATURE ONLY to MEASURED HERE* is
   enforced at the API surface.
3. **A refutation must be stated in BOTH places.** An entry in *Conventions
   that FAILED here* whose `Status` row does not say REFUTED — or the
   reverse — is a `REFUTATION HALF-STATED` finding. Either half alone is a
   live rule wearing a refutation.

⚠️ **The nine entries with a refutation INSIDE them are a THIRD state, not a
rounding of the other two.** They are live (`is_live` is True, `rule_text()`
answers) and they carry a named trap: `C3` ledger pitch, `C10` the
middle-line stem rule, `C19` rest aspect, `C31` the cut-C template, `C36` the
slur pad, `C42` Sean's S6, `C64` the column residual, `C78` hairpin isolation,
`C86` bracket-groups alone. Collapsing them into `NONE` loses the trap;
collapsing them into `WHOLE_ENTRY` deletes nine working rules.

⚠️ **A check that did not exist and now does:** the FAILED table names each
refuted entry **twice** — once as a link, once as a source tag. Point the link
elsewhere and a reader following it lands on a live rule believing it refuted.
`REFUTATION ROW MISADDRESSED` reports that. On the current document all five
links and tags agree.

---

## 5. ⚠️⚠️ WHAT IS MALFORMED IN THE REGISTRY — three prose figures, no arithmetic errors

`probe/prose_claims.py` locates **13** numeric claims the document makes about
itself in prose and checks each against the entries. **Ten reproduce
exactly**, including the entire Conservation arithmetic (114 / 166 / 87 / 79 /
46 / 52 / 41 / 27) and both word-spelled figures (*Five* refuted, *nine*
internal caveats). **Three do not, and none of them is an arithmetic error.**

### 5.1 "The **six** repo entries that absorbed more than one" names FIVE

Conservation states:

> **The six repo entries that absorbed more than one literature entry:**
> `C17` (+L24, L25) · `C21` (+L33, L34) · `C22` (+L36, L37) · `C51` (+L58,
> L61) · `C77` (+L45, L76, L79 — three) · and no others. `46 + 6 = 52` ✅.

**It names five entries.** The `6` is the count of **excess absorptions**
(1+1+1+1+2), which is the right number for `46 + 6 = 52` — the arithmetic is
correct and the **heading mislabels what the 6 counts**. A reader auditing the
merge by counting entries finds five and concludes one was lost.

### 5.2 "**10** of the 87 repo-side entries" lead publisher-dependent — **8** do

The prose marks it *"(the repo file's own count)"*, and
`docs/conventions/from-this-repo.md:49` does state `PUBLISHER-DEPENDENT 10`.
So it is a **SOURCE-file figure carried across the merge and never recomputed
on the merged rows**, where eight lead that way: `C3`, `C14`, `C26`, `C59`,
`C60`, `C70`, `C74`, `C75`.

### 5.3 "**6** of the 27 literature-only ones" — **zero** do

The six it names — `L6`, `L7`, `L8`, `L14`, `L15`, `L71` — all lead
**"Variable"**, which is a different vocabulary word from
`PUBLISHER-DEPENDENT`. Under the document's own stated test (*"by the entry's
leading word"*) the literature-only count is **0**, not 6.

⚠️ **These two are the ONLY numbers in the header that are not properties of
this document, and both are exactly the ones the prose flags as inherited.**
The registry's own warning — *"THE LEADING WORD UNDERCOUNTS, IN BOTH
DIRECTIONS"* — already covers the semantic risk. This finding is narrower and
sharper: the **figures themselves** do not describe the merged registry.

⚠️ **Not fixed here.** The brief is handles, not rewriting, and a count in a
merged document is the merger's call. `prose_claims.py --check` exits 1 until
they are reconciled.

---

## 6. WHAT THE CHECK CATCHES

`python3 -m tools.omr.conventions --check` compares the document **against
itself**. Neither side is a hand list: the entries are parsed, and so is every
claim they are checked against.

| finding | what it means |
|---|---|
| `MISSING FIELD` | an entry lost one of the ten required rows |
| `STATUS UNREADABLE` | a Status row matching none of the five status words |
| `NO SOURCE TAG` | an entry with no `[C../L..]` tag |
| `DUPLICATE SLUG` | two entries producing one anchor |
| `SOURCE CLAIMED TWICE` | one source entry carried by two registry entries |
| `SOURCE ENTRY VANISHED` | a number inside `C1..C87` / `L1..L79` carried by nothing |
| `CONSERVATION ROW MISSING` / `UNPLACED` | the ledger and the entries disagree |
| `COUNT DISAGREES` | any figure in the Counts tables or the Contents list |
| `REFUTATION HALF-STATED` | the FAILED table and a Status row disagree |
| `REFUTATION ROW MISADDRESSED` | the FAILED table's link and its tag name different entries |
| `DANGLING CITATION` | a `[C..]` cited in prose that no entry carries |
| `BROKEN ANCHOR` | an internal link with no heading behind it |

**Exit codes: 0 clean · 1 findings · 2 the parse is DEAD.**

⚠️ **An unreadable Status row is a FINDING, never a default.** The first draft
fell back to `ASSERTED`, which is this tree's governing rule broken inside its
own guard — *a fallback must never convert "cannot tell" into a definite
answer*. `Status.UNREADABLE` exists for that and is never gradeable.

---

## 7. THE MUTATION BATTERY FOUND A FAULT IN ITSELF FIRST

**Final: 24 arms, 24 red, restore verified by hash, positive controls
(`rule_text_refuses_EVERYTHING`, `problems_reports_NOTHING_ever`) in the same
class as the refusal arms.** The first run had **two survivors and neither was
a test gap**.

### ⚠️⚠️ Survivor 1 — the battery ran the WRONG MUTATION and called it a gap

CPython invalidates a `__pycache__` entry on the source's **mtime and SIZE**.
Two arms of this battery replace a 78-character line with a 21-character one,
and a 74-character line with a 17-character one — **both deltas are exactly
57**. The two mutated files are therefore the **same size**, and written inside
one mtime tick the second arm imported the **first arm's bytecode**. It ran the
wrong mutation, the target test passed, and the arm was reported as a
**SURVIVOR** — a gap in the suite that does not exist.

Found because the arm went **RED when run by hand** and survived inside the
battery. The governing form:

> **A mutation battery must not trust the import system to notice that it
> edited a file.**

Repaired by purging `tools/**/__pycache__` and running every arm with
`PYTHONDONTWRITEBYTECODE=1`. This is the sibling of the recorded hazard that
*an interrupted battery leaves the tree neither as it found it nor as git has
it* — same family, a different layer, and it fails in the direction that
manufactures work: it invents test gaps rather than hiding them.

### ⚠️ Survivor 2 — an equivalent mutant, answered by DELETING code

A `DUPLICATE ID` check could never go red: an entry's id **is** its first
source token, so two entries can only share an id by sharing a source token,
which `SOURCE CLAIMED TWICE` already reports. *A branch that cannot be reached
cannot be wrong, and cannot be right either.* It was deleted, the test that
accepted either finding was tightened onto the reachable half, and a
`DUPLICATE SLUG` arm and test were added in its place — slugs are derived from
**titles**, so that one is independently reachable and is red.

---

## 8. THE REGISTRY'S OWN POINT 6, NOW A NUMBER

> *"`Code` says whether anything reads it. A large number of entries here end
> in **no consumer found**."*

Derived: **44 of 114 entries declare that nothing reads them**, and **8 of
those 44 are MEASURED HERE** — measured on this project's own plates and
consumed by nothing. 69 entries name a code path at all; **11 entries name a
path AND declare no consumer** (the ledger-grid rows, which are labelling-UI
only). Those are two different facts and are reported apart: collapsing
`code_paths` into a single `has_consumer` boolean loses the second.

⚠️ **Reported, not acted on.** Which of the 44 is worth a consumer is the
question the next step asks; this one only makes the list addressable.

---

## 9. WHAT IS NOT ESTABLISHED

- **Nothing is wired into any decision, and no adjudicator was touched.** A
  producer and its first consumer landing together makes the reach measurement
  circular — the discipline `Q.INK` and `OMR_FAMILY_POSITIONS` both shipped
  under. The 32 `checked_by=(...)` prose statements in the staged decisions are
  **still unlinked to this registry**; joining them is the next step and is a
  separate, measured job (a sibling session audits the decision side).
- **No page was read, no score gathered, no MusicXML exported, no metric run.**
  Every figure here is a property of a markdown file and of the tree.
- **The `Testability` axis is degenerate** (§3) and may not be worth keeping.
  It is reported as measured rather than dressed up.
- **`is_publisher_dependent` is a filter, never an answer.** It reads the
  LEADING word, and the registry's own warning is that the leading word
  undercounts in both directions — 8 entries lead with it, **20** mention a
  publisher or edition somewhere in that row.
- **The three prose figures in §5 are NOT corrected.** `prose_claims.py
  --check` exits 1 until someone decides.
- **The ID scheme rests on the two harvest files not being renumbered** (§ASK
  -FIRST). Nothing enforces that from here.
- **No claim is made that any convention is TRUE.** This module parses what the
  registry says and grades how the registry says it. A convention is a
  hypothesis and a cheap test, never a licence.

---

## Reproduce

```bash
python3 -m tools.omr.conventions                     # reach, grades, findings
python3 -m tools.omr.conventions --check             # 0 / 1 / 2
python3 -m tools.omr.conventions --id C34            # one entry, in full
python3 -m tools.omr.conventions --json
python3 benchmarks/omr-convention-registry-2026-09/probe/prose_claims.py --check
python3 benchmarks/omr-convention-registry-2026-09/mutate.py
python3 -m pytest tools/omr/tests/test_conventions.py -q
```
