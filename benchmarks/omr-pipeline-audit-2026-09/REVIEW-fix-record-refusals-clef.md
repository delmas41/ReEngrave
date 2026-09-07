# Review — FIX AGENT A, `claude/fix-record-refusals-clef`

**Reviewer: Agent II (author of the findings this build implements).**
Reviewed at `eb8c2204`, 8 commits on `974971e3`. Read-only: no file in the
worktree was edited; its four new test files were run (44 collected, **44
passed**), the full suite was not.

## VERDICT: **APPROVE WITH FIXES** — 3 blocking, 3 minor

The engineering is good and in several places better than what it implements.
But **the site the sweep exists for is the one place it does not record**, and
the comment that justifies the omission is false in the failure direction.

---

## BLOCKING 1 — the clef contest is recorded only on cell 0, and that is the wrong population

`transcribe.py:4713`:

```python
clef_evidence=(first_cell_clef_evidence if cell_idx == 0 else None),
```

justified at `:4669` by: *"Only the staff's first cell reads a clef
(`read_clef=(cell_idx == 0)`), so one dict per staff is the whole population."*

**That sentence is false.** `read_clef` gates the CV locator (`:1770`), the
header detector (`:1820`) and the specialist (`:1856`). It does **not** gate the
detector argmax — lines **1647–1687 contain zero references to `read_clef`**
(`awk 'NR>=1634&&NR<=1690' … | grep -c read_clef` → **0**), and `:1686` sets
`clef_source = "detector"` and overwrites `active_clef` on **every** cell.

That ungated overwrite is the subject of `DECISION_TYPES.md` §3.2 / §R8.1: **11
of 193 scan staves have their clef overturned mid-staff**, each by a single
detection at 0.32–0.82, at least three demonstrably wrong against truth.

Measured over the committed fixtures (`probe_clef_argmax_contests.py`):

| | first cell of staff | **later cell** |
|---|--:|--:|
| cells with ≥1 clef detection, scan | 172 | **25** |
| engraved | 220 | **10** |

**So the sweep records 172 of 197 scan clef-bearing cells (87.3%) and the 25 it
misses are exactly the population the finding is about — including all 11
flips.** A record that covers the cells where the argmax is nearly always right
and omits the ones where it overturns an established clef inverts the point of
the exercise.

**Fix:** pass `clef_evidence` on every cell (keyed by `measure_index`, or
attached to the measure rather than the staff), and correct the comment. If per
cell is judged too costly, the honest minimum is *every cell in which a clef
detection resolved* — 197 scan / 230 engraved, still small.

## BLOCKING 2 — `disagrees` does not answer the question it is credited with

The coordinator asked whether `disagrees` recovers my **25 later-cell
detections: 14 agreeing (worth zero), 11 disagreeing (flipping the staff)**
split. **It does not, for two compounding reasons.**

1. **Different comparison.** `contest["disagrees"]` is `runner_up["clef"] !=
   ranked[0]["clef"]` — *within one cell*. My split is the cell's winner against
   the clef **inherited from earlier cells**. Those are different questions;
   `disagrees` cannot express the second.
2. **Absent exactly where it is needed.** `runner_up` / `margin` / `disagrees`
   are set only `if len(ranked) > 1`. I measured that **each of the 11 flips is
   triggered by the only clef detection in its cell** — so every one would
   produce a `contest` with `n_resolved == 1` and **no `disagrees` key at all**,
   even after blocking 1 is fixed.

**What the record WOULD make corpus-measurable, once blocking 1 lands:** the
split is recoverable by joining `contest["winner"]` against the preceding
measure's `clef` — both already on the record. That is worth stating positively:
**the fix is one wiring change away from making my hand-measured 25/14/11
reproducible by script.** It is not `disagrees` that gets it there.

**Fix:** either record `clef_in_effect_before` on the contest (one assignment,
and it makes the join direct), or state in the docstring that `disagrees` is
intra-cell and the inter-cell question is a join.

## BLOCKING 3 — a THIRD vacuous mutation, in the same family as the two confessed

The two confessions are honest and both redone mutations bite: the `disagrees`
inversion is pinned from both sides (`…records_the_margin_and_the_loser` asserts
`is True`, `…a_duplicate_not_a_contest` asserts `is False`), and the AST test
guards `len(calls) == 2` **before** iterating — the correct defence against the
classic `all([])` pass. That is better than most tests in this repo.

**But the whole clef-evidence wiring is untestable by construction and untested
in fact.** Verified:

- the only `transcribe`-module function any of the four new files calls is
  `T._detections_for_cell(` (`grep -ohE "T\.[A-Za-z_]+\("` over all four → one
  result);
- **no test calls `transcribe()`**, and line 4713 lives inside it;
- **no test asserts on `staff["clef_evidence"]`** — every `clef_evidence` hit in
  `tools/omr/tests/` is either the kwarg or docstring prose.

**Therefore deleting the `clef_evidence=` argument at `:4713` — switching the
entire clef-contest and blocked-readers record off — leaves all 44 tests green.**

⚠️ **And the asymmetry is self-diagnosing:** the key-signature site DID get an
AST wiring test (`test_key_signature_vote_evidence.py:92`) for its staff-dict
write. The clef site, whose wiring is the harder one, did not.

**Fix:** an AST wiring test on `:4713` and on the `staff_dict["clef_evidence"]`
write, in the style already used one file over. Run it red by deleting the
kwarg.

---

## MINOR 1 — the cost decision is right, and incomplete

I agree with the direction, and it does not go far enough. `runner_up_meter`
and `runner_up_votes` are written into the **same returned meter dict** at
`time_signature_locator.py:572-573` as `median_score_margin` / `min_score_margin`
at `:577-578`, and that dict is copied onto every measure. They are page-level
by the same argument. **Move all four, not two.**

⚠️ Worth recording rather than charging to this branch: the meter dict *already*
carries `median_score`, `votes` and `voters` — verified by enumerating the key
sets in a committed fixture. So the build inherited the pattern; it did not
invent it. The `*_final` precedent the coordinator cites is the right one, and
the same reasoning condemns the three pre-existing fields.

## MINOR 2 — the ignore list holds, and contains one dead regex

Independently re-derived: `^/runtime/` matches exactly **5** leaves
(`phase1_s`, `yolo_s`, `total_s`, `direction_text_s`, `contextual_s`) plus
`weight_routing/classification/ms` = **6**. The "exactly six wall clocks" control
is confirmed.

⚠️ `re.compile(r"/_s$")` matches **0 of 14,065 leaves** — the path separator makes
it require a key *named* `_s`. It is inert, not over-broad, so the byte-identity
claim is if anything stronger than stated. But a dead entry in an ignore list
invites someone to read it as coverage. **Delete it or fix it to `_s$`** (which
would then be redundant with `^/runtime/`).

**The seventh leaf is proved, not assumed, and the proof is excellent** — two
runs of one tree, same page, `rejected[5]` holding an 11,708-character
hallucinated essay against the six-character `SECRET`, every other leaf
identical. Exclusion justified; correctly reported rather than fixed; correctly
flagged as *noise, not harmless*.

## MINOR 3 — "six exit labels" is seven

`propose_clef` has five `_note(` sites carrying **seven** labels, because two are
ternaries: `no_clef_anchor` · **`too_few_noteheads` / `no_candidate_clefs`** ·
`no_margin` · `already_in_effect` / `would_worsen_fit` · `proposed`.

The report claims six. The undercount is in the harmless direction — the build
did more than it said — but `no_candidate_clefs` appears **0 times** in the test
file, so the one exit the report forgot is also the one exit nobody pinned.

---

## What I want on the record as good

- **The out-parameter decision.** Refusing to widen a 3-tuple return that three
  existing tests unpack, on the stated ground that *"widening a return to carry
  a record is how a recording change acquires a blast radius"*, is exactly right
  and is the kind of restraint this estate needs.
- **Recording the BLOCKED readers** (`specialist.blocked_by`,
  `detector_header.skipped`) was not in my findings and is the cheapest available
  measurement of what gap-fill-only precedence costs. It directly answers
  `DECISION_TYPES.md` §5.1's *"a ladder cannot express agreement"*.
- **`test_the_winner_matches_the_clef_that_was_actually_used`** and
  `test_the_recorded_exit_agrees_with_the_verdict` — a record that can drift from
  the decision it describes is worse than none, and both are pinned.
- **The empty-tally test.** *"Every staff was read and none of them voted"* and
  *"nothing was read"* both returning `(None, 0.0)` is precisely the
  absent-vs-null confusion I hit in my own round-2 probes; pinning it is right.

## Findings 2 — confirmed as mechanism, NOT re-measured

The coordinator asked me to price the key-signature majority **0.5294** against
the 0.5 gate, and the meter margin **0.0082** (2/4 at 0.5047 over 3/4 at 0.4965).

⚠️ **I did not re-run the pipeline (embargo, and no committed artefact), so I
confirm the MECHANISM and not the numbers.** Both are structurally recoverable
from the new record: `staff["key_signature_evidence"]["system_majority"]` beside
its verdict, and the per-staff `runner_up_score` / `score_margin` plus the
page-level `header_meter_evidence`. Both then become **corpus-measurable by
script** on the next fixture regeneration, which is the point of the sweep and
is achieved.

⚠️ **But nothing is committed to check them against.** The branch adds no
artefact and no probe output; the two headline numbers live only in commit
messages. This project has already been bitten by a refutation whose evidence was
never committed (`TECHNOLOGY_LEDGER.md` §6, the ScoreAug row). **Recommend
committing the two result JSONs, or a one-line extract of each, with the
regeneration command** — a recording sweep whose own findings are not
reproducible undercuts its own thesis.

## Byte-identity

Not independently re-run (embargo). The claim is well-constructed: MusicXML
`diff`-identity on three inputs including 575951 p68 where the locator actually
fires (15 `detector` / 2 `cv_locator`), plus 0 changed / 0 removed through a
script whose ignore list is a measured control. **The structure of the argument
is right**, and blocking 1 does not threaten it — recording less than intended
cannot make output differ.
