# RESUME HERE — state at the end of 2026-09-21

Picked up from `docs/RESUME-HERE-2026-09-20.md`. Everything below is on
**`claude/part-instrument-check-2026-09`**, pushed and verified with
`git merge-base --is-ancestor`, not by trusting a push.

⚠️ **THAT BRANCH IS `claude/integration-2026-09-18` PLUS TWO THINGS**: the
merged `claude/stem-notehead-gate` (yesterday's in-flight agent, §2) and
today's work. **`main` is stale by four days.**

---

## 1. ⚠️ THE FIRST CONVENTION IS WIRED — and it condemns the join each document REFUSED

The 09-20 handoff's ranked item **1**, done. `adjudicate_part_partition`
declared *"each part carries ONE instrument across every system it appears
on"* and **read `Q.INSTRUMENT` on no path at all**. It does now.

| | Litolff Beethoven 5 p1-p4 | Breitkopf Brahms 1 p0-p3 |
|---|--:|--:|
| staves carrying a named instrument | 50 of 75 | 91 of 97 |
| parts named on ≥2 systems — the only ones that CAN disagree | 7 of 12 | 14 of 14 |
| **the SLOT join, which shipped: contested** | **0** | **0** |
| **the ORDINAL join, which each refused: contested** | **3 of 12** | **5 of 14** |

⚠️⚠️ **ALL EIGHT ARE ONE SHAPE: six systems agree, exactly one dissents, and
the dissenter is always the NEXT instrument down** — the signature of a
suppressed INTERIOR staff, and the Phase 2 part-join finding arriving from a
**third** direction after the measure math and the key signatures.

⚠️ **IT RECORDS AND DOES NOT ACT.** Refusing a contested join hands the
document to the fragment fallback (12 parts → 75 fragments) on what may be one
misread label; repairing it needs to know WHICH staff is misfiled, which the
check cannot say. *A wiring pass may CONNECT a decision, it may not let one
GUESS.* Asserted by a test, with the contested count as its positive control.

⚠️ **NOT THE PHASE 2 NUMBER.** That is 12 of 75 staff-systems against hand-read
PRINT truth; this is contested PARTS against our own label readings. Same
fault, different denominators, and **this one is a lower bound.**

Findings: `benchmarks/omr-part-instrument-check-2026-09/FINDINGS.md`.

⚠️ **All three of the audit's headline claims were re-verified against the tree
first and all three hold** — including that `key_signature_corroboration` has
**exactly one non-test import, `transcribe.py`, the LEGACY path**, and that
`staff_group` declares what registry entry `[C59]` denies in its title.

## 2. YESTERDAY'S IN-FLIGHT AGENT LANDED AND IS MERGED

`claude/stem-notehead-gate` — `OMR_STEM_NOTEHEAD_GATE`, **default OFF**,
allow-list, legacy path unreachable BY CONSTRUCTION (verified: the only caller
passing detections is `staged/gather.py`; `transcribe.py:2147` passes none).
Merged clean; whole `tools` suite **4,680 passed / 19 skipped / 0 failed**.

⚠️ **ITS RECOMMENDATION IS SEAN'S TO TAKE AND I HAVE NOT TAKEN IT**: leave the
flag OFF, and read its §5 — a rule running in production is justified by a
page total on a reference sheet that **prints no accidental at all**, and the
same fixture at its own per-bar resolution says that rule **empties a bar of
four chords**. I verified the no-accidental claim directly (`grep` for Dutch
accidental spellings in `reference-lines.ly` returns nothing).

## 3. ⚠️⚠️ TWO MUTATION BATTERIES WERE MEASURING NOTHING — pytest's OWN CLOCK WAS THE JUDGE

`headline()` compared pytest's summary line **verbatim**, and it ends
`" in 0.57s"` — which differs between two runs of an UNMUTATED tree. So every
arm scored RED for free.

```
run A: (0, '13 passed, 5 warnings in 0.57s')
run B: (0, '13 passed, 5 warnings in 0.61s')     IDENTICAL: False
```

⚠️ **`benchmarks/omr-stem-notehead-gate-2026-09/`'s published "21 arms, 21 RED,
0 survivors" is VOID as published** and is re-run here; its FINDINGS §7 carries
the correction with the original beside it. **Only 2 of the repo's 30
batteries carry the shape**, both written 2026-09-20, so it is a regression and
not historic.

⚠️ **Fixing it found FOUR real gaps in my own tests**, three of them the same
shape — *a test named for a hazard it does not reach*: the no-act test built
two EQUAL-count systems, so it took the ordinal branch and never reached the
slot branch the mutation lived in. The fourth is the sharpest: deleting the
arm's POSITIVE control left everything green, because **"nothing moved" is
exactly what a check that never ran looks like** — the hazard the arm exists
to close, reappearing in the suite that guards it. Battery history:
**13/0 (void) → 10/3 → 12/1 → 13/0 on a judge that can fail.**

⚠️ **AND A COMMIT CAPTURED A LIVE MUTATION.** `git add -A` ran while my own
battery was mid-arm and committed `if False:` over the arm's control. The
working tree was right the whole time; HEAD was not, and **the next battery's
dirty-target refusal caught it, not review.** CLAUDE.md says *"never `git add
-A` anywhere another agent may be working"* — the clause to add is that **a
mutation battery is such an agent, and it is one you started yourself.**

## 3a. THE FINAL STATE, verified rather than assumed

| | |
|---|---|
| whole `tools` suite | **4,701 passed / 19 skipped / 0 failed** |
| `wiring --check`, `inventory --check`, `health --check` | all **exit 0** |
| `check_arm.py --control`, both documents | **the join is UNMOVED**, and the check DID run |
| this lane's battery | **13 arms, 13 RED, 0 survivors**, restore verified |
| the gate lane's battery, re-run and then closed | **21 RED, 0 survivors**, restore verified |
| working tree | clean; branch pushed and verified on origin |

⚠️ **The gate battery's closing number reads IDENTICALLY to the void original
(21 of 21) and means the opposite thing** — the original could not have said
anything else. *A number is not a result until the instrument that produced it
can fail.*

## 4. WHAT IS OPEN, ranked

1. **`key_signature_corroboration` on the staged path** — the 09-20 handoff's
   item 2, verified still true today. ⚠️ Note it is **not** a pure wiring job
   like item 1 was: that rule REVERTS a key reading, so performing it is
   acting, and the doctrine needs a decision about that before code.
2. **Give the BAR SUM a registry entry** — the most-cited constraint in the
   project, absent from the document.
3. **`staff_group` vs `[C59]`** — a declared check the registry DENIES. This
   is a contradiction to resolve, not a check to wire.
4. **The gate's default** (§2) and its §5 finding, both Sean's.
5. **Three prose figures in the convention registry still do not reproduce**
   (inherited; untouched today).

## 5. ⚠️ WHAT IS NOT ESTABLISHED

**No print was consulted anywhere today.** Every statement in §1 is agreement
or disagreement between two of our OWN readings, and where they disagree the
check cannot say which is wrong. **The shipped join's 0 is not a clearance** —
this decision's own docstring records a page printing 11 staves in both
systems with DIFFERENT lineups, and *an equal-count check is a constraint
satisfiable by accident*. **Nothing consumes the check's result**, deliberately.
n = **2 documents, 2 publishers, 8 pages, both scans**. **No export, no file,
no OMR-NED figure** — the entire output is a dictionary in a verdict.

⚠️ **The 25 Litolff staves that were never named are outside the check's reach
entirely**, and they are the half of the page most likely to be misjoined:
this edition stops labelling its strings on continuation systems.

## 6. RUNNING IT

```bash
B=benchmarks/omr-part-instrument-check-2026-09
python3 $B/probe_records.py library/_shared-records/*.record.json   # seconds
python3 $B/check_arm.py <record> --control                          # ~1 hour
python3 $B/mutate.py
python3 -m pytest tools/omr/tests/test_part_instrument_check.py
```

⚠️ `check_arm.py` re-adjudicates a whole record and took **~50 min (Litolff)**
and **over an hour (Breitkopf)** per document. `probe_records.py` answers the
same question in under a second by a completely independent route and is the
one to reach for first; the arm is what proves the SHIPPED code says it.
