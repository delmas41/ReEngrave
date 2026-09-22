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

## 4. Files

```
tools/omr/staged/infer.py             Gate, FAMILY_BLOCK_ENV, enabled_rules,
                                      stage_should_run, per-rule skip + report
tools/omr/staged/inferences.py        the slot rule opts into its own gate
tools/omr/staged/pipeline.py          stage_should_run() at the call site
tools/omr/staged/adjudicators/clef.py the supplied clef, GAPS ONLY
benchmarks/omr-unnamed-block-slot-2026-09/flip_arm.py
benchmarks/omr-infer-default-2026-09/mutate.py
```
