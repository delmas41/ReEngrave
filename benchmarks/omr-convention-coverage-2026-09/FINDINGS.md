# Are the declared constraints actually checked? — the audit, 2026-09-20

**No code outside `benchmarks/omr-convention-coverage-2026-09/`.** No
adjudicator was touched, nothing was wired, and none of the gaps below was
repaired. `git diff <base>..HEAD -- tools/ docs/` is **empty**, asserted
rather than remembered. Sean, on the 28 decisions' `checked_by` statements:
*"We need to make sure that all of those are actually included in our
decision-making in some form of the stages."*

```bash
python3 -m benchmarks.omr-convention-coverage-2026-09.probe.declared_vs_read --check
python3 -m benchmarks.omr-convention-coverage-2026-09.probe.coverage --check
python3 benchmarks/omr-convention-coverage-2026-09/probe/mutate.py
```

---

## ask-first block

**CONVENTION ASSUMED.** That a `checked_by` sentence is a claim worth auditing
at all — i.e. that where the pipeline names a constraint it ought to be able
to apply it, or to say why not.

**WHAT WOULD FALSIFY IT.** §1: the field's own definition. `checked_by` is
documented as *"the SPECIFIC constraints, named"* under a `Checkable` enum
asking *"can this fact's own correctness be tested with NO ground truth?"* —
**it declares CHECKABILITY, not implementation**, and the decorator only
requires that a `CHECKABLE`/`MIXED` decision NAME a constraint and NAME the
group a failure would implicate. On that reading a statement nobody runs is a
correctly-filed map entry, not a defect. This audit reports what runs and
what does not, and does not assert that every NOT PERFORMED is a bug.

**NOT CONFIRMED WITH SEAN.** Whether he reads `checked_by` as a promise or as
a map. The answer changes what §4 is: a defect list, or a work list.

---

## 1. REACH, and three of the brief's counts are wrong

Re-derived from the tree, never from the brief.

| | brief | **derived** | how |
|---|--:|--:|---|
| decisions registered | 28 | **28** ✅ | `len(adjudicate.REGISTRY)` after importing `adjudicators` |
| decisions declaring `checked_by` | 16 | **16** ✅ | same |
| `checked_by` statements | 32 | **32** ✅ | `sum(len(d.checked_by) …)` |
| registry conventions | **125** | **114** ❌ | `###` headings inside the 11 category sections |
| …with a prediction and a falsifier | 114 | **114** ✅ | `- **Predicts (mechanically):**` = `- **Would be falsified by:**` = 114 |

**There are not 125 conventions and there never were.** The registry's own
Counts table says 114, its per-category table says 114, and a derived parse
reproduces that table **category for category** — which is the control, since
a parse that merely reached 114 by a different route would not. `125` appears
nowhere in the document. Every entry has both a mechanical prediction and a
falsifier, so *114 with a prediction* is the whole registry, not a subset.

⚠️ **`adjudicate.REGISTRY` IS EMPTY ON A BARE IMPORT** — the decisions
register by decorator. The probe imports `tools.omr.staged.adjudicators`
explicitly and **refuses (exit 2) on an empty registry** rather than
reporting a clean tree over nothing.

---

## 2. The mechanical substrate, and it caught its own author

`probe/declared_vs_read.py` answers one decidable question — *which `Q.*`
names appear in this decision's call closure* — and nothing else. It is the
BOUND on the audit, not the audit: a quantity absent from the closure
**cannot** be tested by that decision; a quantity present may be read for
something else entirely.

⚠️⚠️ **ITS FIRST RUN WAS VACUOUS AND ITS OWN POSITIVE CONTROL IS WHAT SAID
SO.** It reported that **no** declared `wants` entry is ever unreached —
because `inspect.getsource` returns the **decorator**, and `wants` lives in
the decorator, so every declared input appeared to be read by the body. That
is the identical fault CLAUDE.md already records for the tree's own inert-
`wants` check (*"it reported zero, because `inspect.getsource` includes the
decorator and `wants` lives there"*). **The fifth instance, and the first one
caught by a control instead of by accident.** `--check` refuses at zero
rather than printing a clean tree.

With decorators stripped it reproduces **CLAUDE.md's recorded instance from
the tree with no hand-listing** — `adjudicate_clef` declares
`notehead_staff_position` and never reads it — and finds **twelve more**:

**13 inert `wants` entries across 9 of 28 decisions**, full list in
`out/declared-vs-read.txt`. The ones that matter to §4 are
`part_partition → instrument`, `instrument → staff_group, staff_ordinal`,
`key_signature → keysig_marker, dossier_fact` and
`system_membership → gap_bridging`.

---

## 3. ⚠️⚠️ 16 OF THE 32 DECLARED CHECKS ARE NOT PERFORMED

Reached by reading all 16 declaring function bodies **and their helpers** —
not inferred from the declaration. Per-statement evidence in
`out/verdicts.json`.

| verdict | n | means |
|---|--:|---|
| **NOT PERFORMED** | **16** | nothing in the staged pipeline runs it |
| PERFORMED | 7 | the declaring decision runs it and the outcome can change the verdict |
| PERFORMED, RECORDED ONLY | 3 | computed and written to the record, deliberately not acted on |
| PERFORMED ELSEWHERE | 3 | live in another stage; the location is named |
| PARTIAL | 3 | runs on one branch and not on the population the statement names |

⚠️ **THE BRIEF ASKED FOR THREE WORDS AND THREE WAS NOT ENOUGH.** Forcing
PERFORMED / NOT PERFORMED / CANNOT TELL would have produced confident wrong
answers in **both** directions: `arc_kind`'s tie-vs-slur grammar is computed
every time and written to `detail["grammar"]` under a **priced** refusal to
act on it (`OMR_ARC_RECLASS`, +130 scan edits) — calling that "not performed"
would invite someone to build what already exists; and `duration`'s bar sum
runs in EVALUATE (`consequences.reconcile_duration`) — calling that
"performed" would credit the adjudicator with a check one stage away. The two
extra words are mine and both are defined in `out/verdicts.json`.

⚠️ **There is no CANNOT TELL.** Every one of the 32 resolved on reading. That
is a fact about these functions — they are short, and they declare their
exits — not a claim that the method always terminates.

### The three that are more than a coverage gap

**(a) `part_partition` CB14 — the check that would catch the graft its own
docstring documents as shipped.** It declares *"each part carries ONE
instrument across every system it appears on"*, declares `Q.INSTRUMENT` in
`wants`, and **never reads it** (probe: reached = `slot_index`,
`system_staff_count`). Its docstring spends forty lines on the 12-of-75
staff-systems joined to the wrong instrument — *"a Timpani part carrying the
Viola's key signature"*. That is precisely what a per-part instrument
consistency test detects. **The named check and the documented failure are
the same thing, and the check is not wired.** Structurally the same shape as
`adjudicate_clef`/CB15, and sharper, because the damage is on the record.

**(b) `key_signature` CB21 asserts a consumption that does not happen where
it lives.** The declaration reads *"a key CHANGE is printed on every staff at
the same bar (key_signature_corroboration — **CONSUMED, default-ON**)"*.
`grep` says `tools/omr/key_signature_corroboration.py` is imported by
**exactly one file — `tools/omr/transcribe.py`, the LEGACY path**. Nothing
under `tools/omr/staged/` imports it; the only staged references are comments
and this declaration. The parenthetical is **true of the pipeline it names
and false of the pipeline the declaration sits in** — the mirror of
*fixed-then-kept-open-in-prose*: a claim of consumption, in the wrong
pipeline, read by the next person as coverage.

**(c) `staff_group` CB07 asserts what a MEASURED registry entry denies.** It
declares *"staves of one bracket group are one instrument FAMILY"*. Registry
entry **`[C59]`**, status MEASURED HERE, is titled *"A bracket BLOCK is an
engraving unit, not an instrument family"* — and `adjudicate_group_symbol`'s
own docstring gives the case: Brahms 1 p.1 reads blocks `[2,2,2,2,2,7,1,3]`,
five PAIRS that are `2 Flöten`, `2 Oboen`. The check is not performed, and had
it been performed as stated it would have been wrong. **A registry with IDs
would have caught this by joining; today nothing does.**

### The seven that ARE performed, and what they look like

`instrument`/CB08 (the roster veto, a real refusal), `clef`/CB16, CB17, CB18,
`glyph_owner`/CB23 (`_range_veto`), `tuplet_ratio`/CB28, `meter`/CB31.

⚠️ **SIX OF THE SEVEN ARE IMPLEMENTED AS ADDITIVE EVIDENCE, NOT AS A TEST
THAT CAN FAIL.** `clef`'s three are weighted `Term`s — its own comment says
*"ADDITIVE, NOT A FILTER"* — so the constraint raises a candidate's score and
can never report a violation. **Only `tuplet_ratio`/CB28 is a refusal**
(`if len(heads) != 3: abstain("wrong_member_count")`), with `instrument`'s
veto and `meter`'s confinement removing an answer rather than failing.

⚠️⚠️ **THE CONSEQUENCE IS THAT `implicates` IS INERT ACROSS THE BOARD.** The
decorator **requires** `implicates` whenever `checked_by` is given, and
documents it as *"what a FAILED check implicates — the GROUP, not the
culprit"*, with the rule that a violated constraint *"must raise EVERY
member's suspicion"*. If almost nothing can fail, almost nothing can
implicate. The one place the tree honours it is
`consequences.reconcile_duration`, whose docstring says so. **This is a
structural observation, not a count, and it is the most generalisable thing
in this audit.**

---

## 4. ⚠️⚠️ 94 OF THE 114 CONVENTIONS REACH NO DECISION

`out/coverage.txt` has the full list; `out/join.json` is the pairing.

| | n |
|---|--:|
| conventions **claimed** by at least one `checked_by` statement | **20** |
| conventions reaching **no decision at all** | **94** |
| `checked_by` statements matching **no registry convention** | **13** |

⚠️⚠️ **"REACHES NO DECISION" IS NOT "REACHES NO CODE", AND CONFLATING THEM
WOULD BE THE WORST ERROR AVAILABLE HERE.** The question asked was about
ADJUDICATE-stage `checked_by` declarations. Many uncovered conventions are
implemented, and implemented well, **somewhere else** — `[C1+L3]`'s clipped-
fragment drop is in `transcribe.py`, `[C4]`'s ledger ladder is
`Q.GLYPH_LADDER` in GATHER, `[C16+L27]`'s whole-rest-means-the-bar is
`consequences.size_measure_rest` in EVALUATE. **The finding is that they are
not DECLARED by any decision**, so nothing joins the convention to the
decision that depends on it.

**A cheap second axis, and its error rate stated.** Splitting the 94 by
whether the registry's own `- **Code:**` field names a file: **54 name code,
40 name none**. ⚠️ That proxy is a fact about the **document**, not the tree,
and it over-counts: spot-checking five of the 40 found **two with code the
registry simply does not cite** — `[C65]` *A BRACE means ONE PLAYER* is
`BRACE_FAMILIES` in `structure.py:21`, consumed at `:199`; `[C74+L72]` *the
printing TRADITION* is `tools/omr/score_language.py` behind
`OMR_SCORE_LANGUAGE`. **n = 5, so no rate is claimed** — the split is a
pointer to where to look, never a count of unimplemented conventions.

**Where the gap concentrates.** Whole categories are untouched by any
declaration: **Stems & beams 18 of 18**, **Rests & bar filling 8 of 8**,
**Dynamics & hairpins 7 of 7**, **Articulations & ornaments 9 of 9**,
**Barlines & repeats 4 of 4**. Every claimed convention sits in structure,
identity, clef/key, meter or arcs — **the families that have adjudicators
with `checked_by` at all**, which is the result agreeing with itself and not
an independent finding.

---

## 5. ⚠️⚠️ THE BAR SUM — THE MOST-DECLARED CONSTRAINT IN THE PIPELINE — HAS NO REGISTRY ENTRY

**Six of the 32 statements are the bar sum** (CB06, CB22, CB26, CB27, CB29,
CB30), across five different decisions, and it is the constraint this project
cites more than any other. **The registry holds no entry for it.** No `###`
heading in any of the eleven categories states that a bar's durations sum to
its meter; the phrase appears twice in the whole document, both times *inside
another entry*, as a thing other conventions lean on (`[C28]`, `[C29]`,
`[C33]` "all lean on bar sums as a second witness").

That is a hole in the **registry**, not in the pipeline — the bar sum is very
much implemented (`consequences.reconcile_duration`, `probe/bar_fill.py`).
It is worth saying because it inverts the expected direction of this audit:
the sharpest coverage gap found is a convention the CODE knows and the
DOCUMENT does not.

**The other 13-minus-6 statements matching no entry are two clean families
and one real gap**, and the registry is right about the first two:
* **catalog facts** (CB03, CB08, CB13 — the work roster): `source_kind:
  "catalog"`, deliberately *not* read off the plate. A registry of engraving
  conventions correctly holds nothing for them.
* **instrument facts** (CB10, CB15, CB23 — the written range): a property of
  the instrument, not of the ink.
* **CB20, and this one IS a gap**: *"across the staves of a system the DELTA
  is shared, never the value — transposing parts print different signatures
  for one key"* is an engraving convention, it is the reason the key-signature
  corroboration guard must use the weaker witness, and **no entry states it**.
  `[C81+L39]` (timpani/horns/trumpets print no key signature) is adjacent and
  is not it.

---

## 6. The join is MY READING, and here is how much to trust it

There are no convention IDs on the declaration side — a sibling agent is
creating them, and this audit neither waited for nor depended on that work.
So the pairing in `out/join.json` was made by reading both sides, and carries
a confidence per row: **20 high, 5 medium, 4 low, 13 no-entry**.

**Where I would expect a second reader to disagree.** CB01 and CB05
(*"every staff of a system prints the same number of bars"*) are mapped to
`[C56+L74]` at **low** confidence, because no entry states the bar-count
equality itself — `[C56]` is the barline convention it follows *from*. CB28's
member-count claim is mapped to `[C54]` at **low** for the same reason. CB09
and CB12 (label contradiction) are **medium**: `[C71]` is about two
abbreviations for one section, not about a label disagreeing with an
assignment. **If those four were re-read as no-entry, the uncovered count
rises from 94 to 96** and the no-entry statement count from 13 to 17.

`probe/coverage.py` does only the arithmetic **over** that reading, and
derives the denominator from the registry so the two halves stay separable.
Its `--check` refuses unless the parse reproduces the registry's own
per-category Counts table, unless the join claims something, and unless the
join and the verdicts cover exactly the statements **the tree declares** —
so the reading cannot silently drift away from the code it is about.

---

## 7. The mutation battery, and why its first run was 9-of-11 wrong

**Final: 10 arms, 10 red, 0 survivors, positive control green, restore
md5-verified.** Byte snapshot before the first arm, in-flight sentinel,
refuses a dirty tree — and it **refused its own first invocation**, because
its own untracked file made the tree dirty, which is the checkpoint recipe
arriving as the battery's first act.

⚠️⚠️ **ITS FIRST RUN REPORTED 9 OF 11 NOT RED AND EVERY SURVIVOR WAS THE
BATTERY'S OWN FAULT — one design error, repeated nine times.** The arms
DELETED GUARDS (`if X:` → `if False:`). **A guard-deletion arm is an
EQUIVALENT MUTANT on a healthy tree**: a guard only fires when its condition
is true, every condition on a healthy tree is false, so removing it changes
nothing and the arm **can never go red**. Nine arms reported as coverage gaps
and not one was. Rewritten so every arm **breaks the subject** and then
watches the guard fire.

That is this repo's own recorded lesson — *a battery of REFUSAL tests can
pass by refusing everything, so it needs a POSITIVE control in the same
class* — **arriving from the other direction: a battery of guard-deletions
passes by never making anything fail.** Worth adding to the family, because
the two are not the same mistake and the same person made both.

---

## 8. WHAT IS NOT ESTABLISHED

* **That any NOT PERFORMED is a DEFECT.** `checked_by` is documented as
  declaring CHECKABILITY, not implementation (§ask-first). Sixteen statements
  name constraints nothing runs; whether that is a map or a promise is Sean's
  call and is not settled here.
* **Nothing was run on a page.** No gather, no export, no metric, no crop, no
  record. Every figure is a property of the tree and of one committed
  markdown document.
* **The join is a reading** (§6) and four low-confidence rows would move the
  headline by 2.
* **The closure is a BOUND, not a use.** A quantity present in a decision's
  closure may be read for something other than the declared check; the probe
  cannot tell. The *absence* direction is sound; the presence direction is
  not, and every PERFORMED verdict in §3 rests on my reading rather than on
  the probe.
* **I did not audit the other twelve decisions.** 12 of 28 declare no
  `checked_by` at all. Whether they *should* — whether a decision with no
  named constraint is correctly `UNCHECKABLE` or merely undeclared — is a
  different question and was not asked.
* **The 54-names-code / 40-names-none split is a document property** with a
  spot-checked error of 2 in 5. No rate is claimed.
* **No convention was checked against a page or a print**, so this says
  nothing about whether any of the 114 is TRUE on the plates in the library.
* **Nothing was repaired**, deliberately. CLAUDE.md records a brief that
  exempted four refusals from scrutiny and calls it *"the audited pattern
  committed inside the audit"*; fixing while auditing is the same move.
