# The rule was flipped on, and the sheet was demoted to a fallback

2026-09-21 evening. Sean, in one sentence: *"Flip on the previous work and
redo our work tonight to be an option to turn on when we can't get the info
we need."* Two changes, and they pull in opposite directions on purpose —
one turns a measured reader ON, the other stops an unmeasured one
overriding a reader that already spoke.

No new constant. No threshold. No re-derivation of anything already measured.

---

## 1. The flip — and why it could not be one word

`collapse_slot_index_to_family_block` is Sean's own rule: a block of unnamed
staves at the foot of a system, placed against the reference's trailing
same-family run. It was built on 2026-09-17, scored **25 of 25 correct
against the PRINT with ZERO grafts**, measured at `staff_not_identified`
**783 → 141**, and then left switched off.

⚠️⚠️ **IT WAS NOT SWITCHED OFF ON ITS OWN MERITS. It shared `OMR_INFER` with
two DURATION rules whose own findings record that not one of their inferences
has ever been checked against a page.** So raising the flag that ships a
print-verified rule also shipped two unverified ones, and lowering it to keep
those off also kept the verified one off. **One switch, two evidential
weights, and the stronger one lost.** That is not a tuning decision anybody
took; it is a consequence of the registry having one dial.

**Each rule now carries its own gate.**

| rule | flag | default | evidence |
|---|---|---|---|
| `collapse_slot_index_to_family_block` | `OMR_SLOT_FAMILY_BLOCK` | **ON** | 25/25 against the print, 0 grafts |
| `collapse_duration_by_column` | `OMR_INFER` | off | no note checked against a page |
| `collapse_duration_to_barline` | `OMR_INFER` | off | no note checked against a page |

⚠️ **The two predicates are written out separately and a shared helper was
REFUSED.** `test_flag_default_direction.py` finds flags by walking the AST for
`os.environ.get(NAME, default)` compared to a literal word set; a generic
`_flag_on(env, default_on=...)` helper passes the name as a PARAMETER and
would hide **both** flags from that scan. This file already records that guard
being blind to the two meter flags for exactly that kind of reason. Verified
rather than assumed — the scan returns:

```
tools/omr/staged/infer.py:153  OMR_SLOT_FAMILY_BLOCK  default '1'  NotIn {'','0','false','no','off'}  -> default-ON
```

⚠️ **The directions are OPPOSITE and both are correct.** `OMR_INFER` is an
allow-list because its default is OFF (a typo must not switch two unverified
rules on); `OMR_SLOT_FAMILY_BLOCK` is a deny-list because its default is ON
(a typo, or an empty value, must not silently restore a 642-event gap).

⚠️ **`Gate` is ONE object carrying the flag name and its predicate**, so the
report can name the flag that held a rule back without a second table mapping
predicates to names. A two-entry hand list is still a hand list.

### What the flip does, measured

`flip_arm.py`, on `library/_shared-records/beethoven5-p1-p4-ink-identity.record.json`
(provenance `e38dbc25`, **clean tree**), base-vs-arm on ONE tree:

| | base (`OMR_SLOT_FAMILY_BLOCK=0`) | **shipped default** |
|---|--:|--:|
| `slot_index` decided | 55 | **70** |
| `slot_index` narrowed | 20 | **5** |
| inferences made | 0 | **15** |
| **verdicts outside `slot_index` that moved** | — | **0** |

Every one of the 15 carries `decider: infer:collapse_slot_index_to_family_block`.
The 5 left narrowed are the condensed member the rule declines by design.

⚠️ **This reproduces the rule's own published funnel from a different
direction** — its FINDINGS record *20 narrowed → 15 collapsed*, measured on a
different record, on a different tree, by a different arm. It is a
reproduction, not a new result, and must not be quoted as one.

⚠️⚠️ **THE CONTROL THAT MATTERS IS THE ZERO.** With only this rule enabled
the stage can write exactly one quantity — asserted directly off the registry
(`{r.target for r in enabled_rules()} == {"slot_index"}`) and confirmed on a
real record: **0 verdicts outside `slot_index` moved.** A fourth stage that
starts running by default and quietly touches a duration is the entire reason
the two flags were separated rather than merged.

### ⚠️ The first arm was DEAD, and the reason is worth keeping

Run against `library/_shared-records/beethoven5-p1-p4.record.json` the arm
reported **0 narrowed — nothing for the rule to speak into** — and refused to
classify anything. That record carries **0 `margin_label` observations and
`instrument` abstaining `no_evidence` on 75 of 75 staves**: it predates the
`pdf_path` repair, so no staff was ever named and the family-block branch has
no reference run to fill. The `-ink-identity` record carries **50 labels and
`instrument` decided on 50 / abstained on 25**, which is the split the rule's
own findings describe.

**A shared record is a snapshot of the reader that made it**, and the two
Litolff records differ by more than a date.

### ⚠️⚠️ `block_arm.py`'s control FAILS on today's tree and was NOT weakened

That arm's control is *the committed record's own slot verdicts, reproduced*.
On today's tree it reports **12 of 75** and exits 2. It is right to: CLAUDE.md
recorded this morning that *"the shared records can no longer license a
rebuild ... any future A/B must be base-vs-arm on ONE tree"*, and
`adjudicate_slot_index` gained its short-system pairing rule after that record
was gathered.

Widening that control until it passed would be *a control that computes the
wrong thing*, applied deliberately. `flip_arm.py` is a separate instrument
asking the smaller question, and says so in its own docstring.

---

## 2. The supplied clef speaks GAPS ONLY

Tonight's session fact sheet can supply a clef per staff. Before this change
`adjudicate_clef` admitted it as a term weighing **`W_DOSSIER` = 4.0** — above
**`W_DETECTOR_HIGH` = 3.0**.

⚠️⚠️ **SO A SUPPLIED CLEF DID NOT CORROBORATE A READ ONE, IT REPLACED IT** —
silently, on every staff, including where the reading was right and the sheet
held a typo. That is the opposite of what Sean asked for, and it is also the
opposite of his standing rule that evidence must CONTRIBUTE and never gate.

On, the `dossier` tier is admitted **only where the page said nothing** —
where `_detector_terms` and `_locator_terms` are both empty. The precedent is
`adjudicate_key_signature`, whose template reader answers gaps only for the
identical reason and whose own measurement refused letting the fuller reading
win; inherited rather than re-litigated.

⚠️ **IT IS A REFUSAL TO SPEAK, NOT A WEIGHT CHANGE, and the distinction is
load-bearing.** Lowering `W_DOSSIER` below the detector would still let a
supplied clef out-vote a *pair* of weak read terms, and would weaken it on the
honest case — a staff nothing was read on — for no reason. The two questions
are *may it speak here* and *how loud*; only the first was in doubt. The
weight ordering is pinned by a test so the rule cannot later be deleted as
redundant on the mistaken ground that the weights already handle it.

⚠️ **The CARRY tier is untouched.** `clef_continuity`'s mechanism is the one
carry in this pipeline that survives, it was measured, and it is not what was
asked to change. A rule that took it along with the seed would be a second,
unpriced change riding on the first — asserted by its own test.

⚠️ **The refusal is RECORDED**, not silent:
`detail["supplied_clefs_withheld_because_the_page_spoke"]`, written only when
something was actually withheld. A supplied clef that disagreed with a page
that spoke is the one signal a gaps-only rule would otherwise throw away — and
an always-present zero would put the key on every staff in the document, which
is the *a null key is still a key* hazard from the other side.

### ⚠️ The red proof, stated exactly

Against the previous `_carry_terms`, **three of the seven new tests go red**:
the two overturn tests and the recorded-refusal one. The first draft of that
test class's docstring claimed all seven did. **That was false**, and it is
the precise shape this repository warns about — *a test named for a hazard it
does not reach*, written into the summary rather than the body. Corrected in
place. The other four are deliberately not red and each is load-bearing: one
is the POSITIVE CONTROL (without it the three red ones would pass for a rule
that threw every seed away), two guard what must NOT change, and one pins the
weight ordering that makes the rule necessary at all.

---

## 3. What this does NOT establish

- **No print was consulted tonight.** The flip's correctness rests entirely on
  the 2026-09-17 crop pass (25 of 25); nothing new was adjudicated against a
  page. The clef change is a REFUSAL, so it has no accuracy to measure — but
  it has not been shown that the staves it now declines to speak on were being
  helped or harmed before, because **no supplied clef has ever been scored
  against a print.**
- **No export, no file, no OMR-NED.** `flip_arm.py` stops at the verdicts. The
  rule's own findings measure the file effect (+642 events, 562 pitched notes)
  and that was NOT re-run here.
- **n = 1 document, 1 publisher, 4 pages**, a scan, and the same Litolff plate
  every lane in this thread uses. **Breitkopf has NO population for this rule
  at all** — 0 abstentions, because that plate labels nearly every staff — so
  the second publisher can neither corroborate nor refute it.
- **A GATHER change is invisible to `flip_arm.py`**, which rebuilds from a
  saved record.
- ⚠️ **The two changes interact and the interaction is UNMEASURED.** The
  family-block rule and the supplied clef both assign instruments to lines. If
  a sheet is supplied AND the rule is on, they need checking against each
  other rather than being trusted separately. Nothing here does that, because
  no record in the tree carries a `clef_seed` row.

---

## 4. The battery — and the two survivors it found

**20 arms, 20 RED, 0 survived**, restore hash-verified for **every** subject
(`out/battery-2026-09-21.txt`). Arms span three files and **each arm names its
own subject**: the sibling battery in `omr-factsheet-2026-09` dispatches its
second subject by substring-matching the arm's NAME, which is a hand list
wearing a conditional — rename an arm and it silently mutates the wrong file.

⚠️ **Its FIRST run was 18 RED / 2 survived, and the two are different animals:**

1. **An EQUIVALENT MUTANT of my own writing.** Giving `Switch.env` / `.fn`
   defaults cannot fire, because every `Switch` in the tree is constructed
   with both arguments POSITIONALLY. It survived correctly. *An arm that can
   never go red trains the next reader to skim the list*, so it is **named in
   the file and replaced** by one that mutates the value actually used
   (`INFER_SWITCH = Switch("OMR_NOT_A_FLAG", …)`).
2. **A REAL GAP.** Swapping `W_DOSSIER` for `W_CARRY` on the supplied term
   survived every test, because in the gap case the seed is usually the ONLY
   candidate and any positive weight wins. Not harmless: on a staff the page
   said nothing about, an `instrument` term (1.0) or a key-signature slot fit
   (1.5) can still be in the contest. Closed by asserting the recorded SCORE.

---

## 5. ⚠️⚠️ THE INSTRUMENT FINDING: A ONE-WORD IDENTIFIER CAN FALSELY CLOSE A GAP

The field was first called `gate`. `wiring --check` then went from **64
problems / 0 stale** to **63 / 1 stale**, reporting the unrelated detail key
`Q.DIRECTION_WORD.gate` as **CLOSED** — because the DETAIL question matches
detail keys by BARE NAME anywhere in `tools/`, and a new identifier spelled
the same way reads as a consumer.

**A falsely-closed gap is live damage**: `KNOWN_GAPS` stops describing the
tree, and the entry would have been deleted by the stale-entry test. Fixed by
renaming the field to `switch` — confirmed by re-measuring back to **64 / 0**,
not by reasoning — and **not** by deleting the gap entry.

⚠️ **The weakness is the checker's and is recorded rather than repaired here**:
any new lowercase identifier in `tools/` can close an unrelated detail-key gap.
That is another lane's instrument.

⚠️ **A control-probe in the middle of this destroyed every uncommitted file in
the worktree** (`git checkout-index -a -f` overwrites ALL tracked files, not
the two that were stashed). Recovered by replaying the session transcript;
three things needed hand repair, and **two of them were deliberate red-proof
MUTATIONS whose `cp`-based restores were not replayable** — so the replay
faithfully re-applied the mutation and dropped the undo. *A recovery that
replays writes will replay your mutations too.*

---

## 6. Files

```
tools/omr/staged/infer.py             Gate, FAMILY_BLOCK_ENV, enabled_rules,
                                      stage_should_run, per-rule skip + report
tools/omr/staged/inferences.py        the slot rule opts into its own gate
tools/omr/staged/pipeline.py          stage_should_run() at the call site
tools/omr/staged/adjudicators/clef.py the supplied clef, GAPS ONLY
benchmarks/omr-unnamed-block-slot-2026-09/flip_arm.py
benchmarks/omr-infer-default-2026-09/mutate.py
```

---

## 7. 2026-09-23 — `OMR_INFER` itself flipped to default ON (roadmap 2.3)

**The decision, stated exactly.** Sean, 2026-09-23, roadmap item 2.3: the two
duration rules (`collapse_duration_by_column`, `collapse_duration_to_barline`)
move from `OMR_INFER` default OFF to default ON.

⚠️⚠️ **THIS CLOSES A QUESTION `benchmarks/omr-infer-duration-print-2026-09/
FINDINGS.md` LEFT EXPLICITLY OPEN, AND THAT IS RECORDED HERE RATHER THAN
SMOOTHED OVER.** That file's own closing line (§9, "What this still does not
settle") reads: *"Both rules remain default OFF and this does not change
that... 2.3's default decision is still open."* This section is the decision
that closes it, taken by Sean on the evidence that file accumulated same-day:
three subjects checked against the print (§7, §8), all three found WRONG
under the reads that omitted `Q.GLYPH_OWNER`, the omission fixed and
re-measured (§9: 16 inferences → 13, three dropped, zero surviving values
changed), and confirmed that EXPORT never shared the same blind spot (§9b).
No fourth subject has been checked since. The remaining thirteen inferences
that fix measured are still unverified against a print one at a time — the
decision to ship is Sean's, not a claim that this pass discharged that
burden.

### The flip

`infer_enabled()` (`tools/omr/staged/infer.py`) changes from an allow-list on
a default of `"0"` to a deny-list on a default of `"1"` — the same direction
flip `OMR_SLOT_FAMILY_BLOCK` took on 2026-09-21, now true of both flags in
this file. `test_flag_default_direction.py`'s AST scan confirms the new
predicate is a deny-list for a default-ON flag (source, not asserted here).
`test_infer_stage.py::TestTheFlag` is rewritten the same way `_all_off`'s
docstring in `test_infer_bypass.py` already anticipated for a future flip:
`test_on_by_default`, `test_a_typo_does_not_switch_it_off`, and — the
positive control, without which the deny-list predicate could be replaced by
`lambda: True` and every test in the class would still pass —
`test_the_off_words_work`, asserting `OMR_INFER=0` (among other off-words)
actually reads OFF.

### Gate, same tree as the flip

`pytest -m "not slow"`: **2,823 passed, 3 skipped, 0 failed** — identical to
the print-check pass in `omr-infer-duration-print-2026-09/FINDINGS.md` §9,
confirming the flip touched no other behaviour.
`python3 -m tools.omr.staged.check`: **255 open, status ok** — unchanged
from the baseline recorded throughout this month's sessions (exit 1, not 2:
findings open but nothing broken).

### Measured, base (`OMR_INFER=0`) vs arm (`OMR_INFER=1`), each on ONE tree

Both documents replayed from their committed whole-movement shared records
via `benchmarks/omr-infer-stage-2026-09/reinfer.py`'s `rebuild()` (id-exact
replay of every observation, abstention and verdict), INFER re-run over two
INDEPENDENT rebuilds per document so the two arms cannot contaminate each
other, each arm exported with `tools.omr.staged.export.to_musicxml`. The
control (replay reproduces the saved record before any arm runs) is reported
first and is not a courtesy — a rebuild that does not reproduce the record
would make every number below a measurement of the harness, not the flag.

**Litolff** (`beethoven5-litolff-mvt1-whole-20260923.record.json`, 16 pages,
commit `dbc9962b`, dirty tree):

- control: **101,361 of 101,361 verdicts reproduced, 0 differ**

| | OFF | ON |
|---|--:|--:|
| `collapse_duration_by_column` | 0 | **20** |
| `collapse_duration_to_barline` | 0 | **49** |
| total inferences | 0 | **69** |
| `<note>` elements written | 12,375 | **12,424** (+49) |
| `duration_narrowed` refusals | 1,376 | **1,321** (−55) |
| `notes_not_written_total` | 4,170 | **4,115** (−55) |
| `status_census` balanced / unaccounted | true / [] | true / [] |
| wall time — rebuild / INFER / export | 10.6s / **1.4s** / 1.3s | 11.3s / **10.6s** / 1.4s |

**Brahms/Breitkopf** (`brahms1-breitkopf-mvt1-whole-20260923.record.json`, 27
pages, commit `47fbff1e`, dirty tree):

- control: **238,473 of 238,473 verdicts reproduced, 0 differ**

| | OFF | ON |
|---|--:|--:|
| `collapse_duration_by_column` | 0 | **174** |
| `collapse_duration_to_barline` | 0 | **113** |
| total inferences | 0 | **287** |
| `<note>` elements written | 22,922 | **23,145** (+223) |
| `duration_narrowed` refusals | 3,583 | **3,339** (−244) |
| `notes_not_written_total` | 11,207 | **10,976** (−231) |
| `status_census` balanced / unaccounted | true / [] | true / [] |
| wall time — rebuild / INFER / export | 28.4s / **3.4s** / 3.4s | 28.5s / **20.8s** / 3.6s |

⚠️ **The OFF arm made zero inferences on both documents and the ON arm's own
INFER wall time is 6–7× the OFF arm's** (Litolff 1.4s → 10.6s; Brahms 3.4s →
20.8s), scaling with document size in both arms — the tell this project's own
convention asks for (§6b, CLAUDE.md): a cached no-op reports as identical
numbers AND identical wall time, and neither happened here.

⚠️⚠️ **THE FUNNEL INVERTS BETWEEN THE TWO PLATES, REPRODUCING THE STANDING
CAVEAT ABOUT THIS PAIR OF DOCUMENTS RATHER THAN A NEW RESULT.** On Litolff
`collapse_duration_to_barline` supplies 71% of the inferences (49 of 69); on
Breitkopf `collapse_duration_by_column` supplies 61% (174 of 287). CLAUDE.md
already records *"Litolff MERGES and Breitkopf SHATTERS"* as a property of
the two plates' ink, not of either rule — this is that property showing up
again, one level up the pipeline, in which of two structurally identical
rules a document's own bar layout hands more work to. Neither rule dominates
universally; a document with columns that corroborate cleanly favours
`by_column`, a document whose narrowed notes more often run uncontested to
the barline favours `to_barline`. **Not evidence either rule is wrong on
either document** — both populations remain print-checked at n = 3, all on
Litolff, none on Breitkopf.

### What this pass does NOT establish (unchanged from §9's own list, widened)

- **No new print check.** Zero additional subjects were read against a page
  in this pass; the print evidence behind the flip is entirely the three
  subjects `omr-infer-duration-print-2026-09/FINDINGS.md` already recorded.
  **Breitkopf has zero subjects checked against its own print** — the 287
  inferences above are unverified in the direction that matters, on the
  document whose funnel differs most from the one that was checked.
- **musicdiff / OMR-NED was not run.** This measures the record and the file
  the record produces, not agreement with an outside encoding. CLAUDE.md's
  standing warning about OMR-NED (§6b) — it is symmetric and rewards fewer
  symbols, and pitch errors are structurally invisible to it under
  `AllObjects` — applies with full force to any future attempt to quote it
  as evidence for or against this flip.
- **A GATHER or ADJUDICATE change is invisible to this instrument.**
  `reinfer.rebuild()` replays a FIXED gather and a FIXED adjudication;
  answering "did GATHER change what INFER sees" needs two full re-gathers,
  which this session did not run (CLAUDE.md: do not run a gather).
- **n = 2 documents, 2 publishers, both already in the acceptance set.** No
  third plate, no third publisher, corroborates or refutes the funnel
  inversion above.

### Files

```
tools/omr/staged/infer.py                              INFER_ENV predicate flipped
tools/omr/staged/inferences.py                          comment at the slot rule's own gate
tools/omr/tests/test_infer_stage.py                     TestTheFlag rewritten deny-list
tools/omr/tests/test_infer_bypass.py                    _all_off docstring
tools/omr/tests/test_infer_barline_rule.py              _run docstring
docs/flags-2026-09.md                                   both OMR_INFER rows
benchmarks/omr-infer-stage-2026-09/reinfer.py            reused unmodified
```
