# The ink-first test on Brahms p2 — the veto's cost is ZERO, and it does not fire on barlines

**2026-09-18.** Sean's rule (*a stem has a notehead at one of its ends; a
barline has none*), measured on the one page where hand truth, ink rows and
detector boxes all exist. **Read-only** apart from a comment.

⚠️ **PROVENANCE.** The measuring session was refused a findings file — the
**fourth** time today — so its synthesis is in commit `b0e02f61`'s message and
its artefacts are `out/ink-first.txt` and `out/mutate.txt`. This is that record
transposed at integration; **[mgr]** marks what the managing session re-derived.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN
**ASSUMED**: Sean's own — a stem has a notehead at one of its ends, a barline
has none. **FALSIFIER**: a vertical run with no head at either end that the
print shows *is* a stem — measured as the veto's COST, with a positive control.
⚠️ **NOT CONFIRMED WITH SEAN**: whether an **accidental's** vertical stroke
belongs in this rule's population, **which is where its firings actually land**
(§4).

## 1. The blocking artefact now exists
`out/brahms1-breitkopf-p2.gather.json` — **7.9 MB, committed**, 6,055 `Q.INK`
rows over 202 cells. `omr-ink-extent-2026-09` named exactly this as the one
thing blocking the test. **A cloud session with no weights and no `library/`
can now run it.** Validated against the full 150 MB staged record: identical
output but **one row** (`roster_entry`, a difference in the session's own call).

## 2. The frame join controlled CLEAN — the run did not have to stop
The hazard was that the hand boxes and the gathered cells might be in different
canonical frames. They are not: staff spacing agrees on **19 of 19 cells (17
exactly)**, and **97 of 99 hand noteheads land on a detector notehead
(0.980)**. 264 hand boxes, matching the corpus's own count. ⚠️ Grid-top
disagrees on 9 of 19 and **that is expected** — `OMR_CELL_LINE_TRACE` slides the
stored rows onto the ink, never the crop. Staves per system read **14/13**,
which is CLAUDE.md's own figure for this page from a different direction.

## 3. The ink-first partition — 776 rows in the 19 hand cells

| bucket | n | share | share of AREA |
|---|--:|--:|--:|
| real mark, detector agrees | 184 | 23.7% | 19.1% |
| **detector invention** (symbol class, no hand box) | 140 | 18.0% | 13.2% |
| **structural ink** (stem / beam / staff) | 100 | 12.9% | 21.8% |
| **missed mark** (hand truth only) | 48 | 6.2% | 11.4% |
| unexplained (neither) | 304 | 39.2% | 34.4% |

⚠️⚠️ **THE STRUCTURAL BUCKET IS MANDATORY, NOT A REFINEMENT.** The hand corpus
carries **no stem/beam/staff class by policy**, so un-split the figures read
219 / 240 / 13 — **structural ink counts as "detector invention" AND as "missed
music" at once.** Any future use of this partition must keep it.

⚠️⚠️ **AND THE UNEXPLAINED BUCKET IS NOT MISSED MUSIC: 72.4% of it is SPECKS
carrying 0.3% of its area, while 43 pieces carry 84.9%** — the largest a
**22.8 × 12.0 staff-space blob holding 53% of its cell.** So by COUNT it is
noise and by AREA it is whole-bar merges. **This reproduces the ink-extent
headline (42.5% of pieces / 36% of area) in shape and shows that NEITHER number
is evidence of missed music** — which is the correction that figure needed.

## 4. ⚠️⚠️ SEAN'S RULE: THE COST IS ZERO, AND IT DOES NOT FIRE ON BARLINES

**The veto (EVALUATE half — *no head at either end ⇒ not a stem*):**

| | |
|---|--:|
| reach, vertical runs over all ink | **68** |
| would fire on | **33** |
| **COST** (detector says no head, HAND TRUTH says there is one) | **0 of 68** |
| positive control `--drop-det-heads` | cost **0 → 1** |

⚠️ **The zero is the page's, not the instrument's** — the control moves it, so
the probe can detect a cost when one exists. ⚠️ **It is zero BECAUSE notehead
recall is 0.980 here**, and the crop pass's *"a third are not noteheads"* is a
**PRECISION** fault — which pushes this rule toward **not firing**, never toward
deleting stems. **Those two facts are compatible and were not obviously so.**

⚠️⚠️ **BUT WHAT IT FIRES ON IS NOT BARLINES — 24 of 33 coincide with a
`keyFlat` (9), `accidentalNatural` (7), `restQuarter` (2), `accidentalFlat` (2),
`clefG` (2), `accidentalSharp` (1) or `clefF` (1)**, every one of which contains
a tall vertical stroke; 9 coincide with nothing the hand pass drew.
**[mgr] re-derived from `out/ink-first.txt`.** The entire thread — the census's
`too TALL` bucket, the crop pass's 12-of-12, this brief — framed the rule
against **barlines**. On this page its real population is **accidentals and
clefs.** That does not refute it (those are correctly *not stems*), but it means
its value is not where anyone said, and **Sean has not been asked whether an
accidental's stroke belongs in its domain.**

**The positive half** (*a head at an end ⇒ a stem*) is **INFER-shaped and NOT
proposed**: all **14 of 14** runs the hand pass calls symbol-less have a head at
an end. ⚠️ **Legitimacy checked**: it reads only its own cell's noteheads —
`size_measure_rest`'s precedent — with **no cross-staff reading**, so it is a
legal EVALUATE consequence on that count.

⚠️ **`too TALL`: reach 3, and 3 of 3 agree with the print.** But the hand column
is **vacuous** there (not those cells), and **only 1 of 3 is barline-shaped in
the ink** — the other two are **24 and 16 staff spaces wide**, merged into
whole-bar blobs.

## 5. Engraved control: NOT RUN
Skipped on the brief's own permission — a render plus a second ~16-minute gather
against a usage limit. **So there is no verdict on whether the instrument works
on clean ink.**

## 6. Two corrections to committed figures
1. ⚠️⚠️ **`CLAUDE.md`'s `OMR_INK` row had two numbers on the WRONG
   PUBLISHERS**: it read *"5.6 components per cell against 30"* with Breitkopf
   first, while its source says *"Litolff yields 5.6 and Breitkopf 30"* and its
   own next clause says *"Litolff MERGES and Breitkopf SHATTERS"*. **[mgr]
   verified against `omr-ink-gather-2026-09/FINDINGS.md:146` and corrected in
   place.** Re-measured here: Breitkopf median **26.0**, mean **30.0**.
2. ⚠️ **The session committed a revert it did not write** — a stale staged
   `record.py` change rode in from the worktree's previous branch through a bare
   `git commit`, and `git status` was clean afterwards so nothing announced it.
   It had reverted the *box-convention warning* that its own control B exists
   for. Repaired in `120ab9e8`. ⚠️ **[mgr] Its final report nevertheless claimed
   `git diff -- tools/` was EMPTY, which the tree contradicts (15 insertions)** —
   the claim and the disclosure are both in the same report. Merged clean; the
   restored text is the managing session's own, minus two emoji variation
   selectors.

## 7. Battery
**9 arms, 9 RED, 0 survivors**, restore md5-verified. All four of the first
run's problems were the battery's own, including its `headline()` not reaching
the partition rows it mutated.

## 8. ⚠️ NOT ESTABLISHED
n = **1 page, 1 publisher, 19 of 202 cells**. ⚠️ **The hand corpus cannot say
whether a run IS a stem** (no stem class), so **whether the veto wrongly refuses
a real stem is unmeasured** and needs print adjudication of the 33 firings.
⚠️ **The veto's marginal value over `detect_stems`' six shipped filters is
unmeasured** — only survivors reach the record. No print consulted by this
session; no engraved page; no OMR-NED; publishers reported apart. **The
breakthrough's core claim stands neither confirmed nor refuted** — what changed
is that its two headline ink-first figures are **not** evidence of missed music.
