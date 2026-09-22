# RESUME HERE — state at the end of 2026-09-21

Picked up from `docs/RESUME-HERE-2026-09-20.md`. Everything below is on
**`claude/part-instrument-check-2026-09`**, pushed and verified with
`git merge-base --is-ancestor`, not by trusting a push.

⚠️ **THAT BRANCH IS `claude/integration-2026-09-18` PLUS TWO THINGS**: the
merged `claude/stem-notehead-gate` (yesterday's in-flight agent, §2) and
today's work. **`main` is stale by four days.**

> ⚠️⚠️ **CORRECTED 2026-09-21 (evening): BOTH CLAIMS IN THAT PARAGRAPH ARE NOW
> STALE, AND THE FIRST WAS WRONG WHEN WRITTEN.** The branch is **NOT**
> `claude/integration-2026-09-18` plus two things — the two had **DIVERGED at
> `b600964e`**, 27 commits against 18, and
> `docs/handoff-2026-09-21-connecting-the-sweep.md` is the session that found
> it. **`main` is no longer stale: everything described here is merged**, plus
> the 17 later commits of this branch that the integration did not take
> (§2b's key-signature work among them). **Work from `main`, not from this
> branch name.** ⚠️ The lever §2b hands on was then measured and **REFUSED** —
> `benchmarks/omr-keysig-marker-fit-2026-09/FINDINGS.md`, and
> `docs/NEXT-2026-09-21-keysig-reading-lever.md` opens with a DO-NOT-RE-RUN
> stamp.

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

## 2b. ⚠️⚠️ RANKED ITEM 2 (the key signature) — THE PREMISE WAS HALF WRONG

*"`key_signature_corroboration` on the staged path — CLAUDE.md says shipped;
the staged path does not import it."* **The import claim is TRUE. The repair
it implies is not.** Findings:
`benchmarks/omr-keysig-staged-reach-2026-09/FINDINGS.md`.

**Wiring the import would produce a pass over an EMPTY DOMAIN**, because on
this path a mid-staff key change cannot exist: `adjudicate_key_signature` is
`Kind.STAFF`, `_gather_keysig_markers` reads **cell 0 and nothing else**, the
run/template readers read the HEADER WINDOW, and the exporter carries one
`fifths` per staff-run. Measured with no pipeline code: **75 and 97 key
verdicts, every one staff-scoped; 105 and 146 marker rows, every one at
`cell:0`; ZERO of either anywhere else.**

⚠️ **THE CONTRAST WITH THE METER SIZES THE REAL JOB.** `Q.METER` has
`segments` + `record.meter_at` + `OMR_METER_SEGMENTS`; the key signature has
**no segments, no `key_at`, one value per run**. It is a missing QUANTITY
SHAPE, not a missing import.

⚠️ **THE REACH OF THE MISSING READER IS 21 AND 2** key-accidental detections
in later cells — and the legacy path is the warning about reading them: of the
15 it DOES read, **7 changed the key and all 7 were wrong**. A mid-staff key
reader must arrive WITH its corroboration.

**WHAT WAS WIREABLE, AND IS WIRED: `Q.KEYSIG_MARKER`** — declared in `wants`
AND `composed_from`, filed 105 and 146 times, read by nothing. ⚠️⚠️ **Both gap
lists excused it with a reason that is FALSE** (*"the markers already feed
`keysig_clef_fit`"* — they do not; that comes from a CV reader on the header
crop and the only detections reaching it are NOTEHEADS). Reading them splits a
reason word that was wrong on **7 of 17 and 9 of 20** staves: `no_evidence`
reported on staves carrying key-accidental ink. It **records, never decides** —
the marker count matches the settled `|fifths|` on only 39% and 51%.

⚠️ `Q.DOSSIER_FACT` is the other never-reached declaration and is **left
alone**: its reason was re-checked and is still true (a dossier is built from
the MusicXML the benchmarks score against).

## 3a. THE FINAL STATE, verified rather than assumed

| | |
|---|---|
| whole `tools` suite | **4,722 passed / 19 skipped / 0 failed** |
| `wiring`, `inventory`, `health`, `reach` `--check` | all **exit 0** |
| the key-signature battery | **14 arms, 14 RED, 0 survivors**, restore verified (4th run) |
| key-signature control arm, BOTH records | **0 decided keys moved**; splits **7** and **9**, the probe's own numbers |
| `check_arm.py --control`, both documents | **the join is UNMOVED**, and the check DID run |
| this lane's battery | **13 arms, 13 RED, 0 survivors**, restore verified |
| the gate lane's battery, re-run and then closed | **21 RED, 0 survivors**, restore verified |
| working tree | clean; branch pushed and verified on origin |

⚠️ **The gate battery's closing number reads IDENTICALLY to the void original
(21 of 21) and means the opposite thing** — the original could not have said
anything else. *A number is not a result until the instrument that produced it
can fail.*

## 4. WHAT IS OPEN, ranked

1. ⚠️ **A mid-staff KEY CHANGE as a quantity shape** — §2b. This is what item
   2 actually turned out to be, and it is a GATHER change plus a `segments`
   shape, following the meter's own precedent. **It must land WITH its
   corroboration**, because the legacy path shows what reading later-cell
   markers costs without one (7 of 15, all wrong). Reach on these pages is
   small (21 and 2) and the ENGRAVED family has none at all, so the case for
   building it is not yet made — **measure a third publisher first.**
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

## 5a. ⚠️⚠️ FIVE INSTRUMENT FAULTS, AND NOT ONE WAS VISIBLE AS A WRONG ANSWER

Every one was found by a mutation battery or by opening a number — never by a
failing test and never by review — and every one produced output that looked
like a measurement:

1. **pytest's elapsed time in the battery's judge** (§3): two batteries, every
   arm red for free. The stem-gate lane's published 21/21 was VOID.
2. **A mutation committed by `git add -A`** while my own battery was mid-arm.
   Working tree right, HEAD wrong; the NEXT battery's dirty-target refusal
   caught it.
3. **Killing a long arm killed one ITERATION, not the shell `for` LOOP.** It
   ran 31 more minutes, overlapped the battery it had just been removed from,
   and raced its own replacement for the same `--tag` output file.
4. ⚠️⚠️ **A unit test overwrote a COMMITTED measurement.** The tests closing
   the instrument survivors drive each instrument's `main()`, which writes
   under `HERE/"out"`. `out/probe-records.json` was silently replaced by the
   one-staff fixture's numbers and **nothing failed** — it still parsed and
   still looked like evidence. Found by a later command reading it and seeing
   `rec.json` named inside.
5. **A vacuous assertion of mine**: `assertIn("MOVED", out)` against an arm
   that prints `MOVED 0` on every run — satisfied by a control that found
   nothing. Exposed only on the battery's third pass.

> **A battery is not done when it goes green once.** Closing a survivor
> CHANGES the suite, so it must be re-run against the closure. Run 3 found two
> more, and one of them was #5. The keysig battery went **8/6 → 14/0 → 12/2 →
> 14/0**.

> **An in-flight mutation is indistinguishable from a deliberate edit.** Mid
> battery, this session was shown `if True:` in a control and told the file
> had "changed on disk". Correct — and it was the battery, which restored it.
> **Do not commit, and do not revert, while one is running.**

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
