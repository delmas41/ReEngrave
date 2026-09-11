# Handoff — the target changed, and the order of work with it

⚠️⚠️ **READ [docs/plan-2026-09-10-wire-first-then-reconcile.md](plan-2026-09-10-wire-first-then-reconcile.md)
BEFORE THE THREE 2026-09-10 HANDOFFS.** Those are still correct about what they
measured and their RANKINGS are superseded — they rank under the old order, and
a stale ranking reads as a live work order.

---

## 1. WHAT SEAN DECIDED

**Two changes of TARGET, not next steps.**

1. **The finish line is a cleanup count.** *"How much work would I have to do
   to clean it up."* One real scanned orchestral movement, end to end, counted
   against the print. ⚠️ A RANKING instrument, never a number to drive down.
2. **That forces WIRE-EVERYTHING-FIRST**, which was Sean's own question:
   *"we might be wasting time"* fixing one decision when the data needed to fix
   it comes from another that is not wired yet. **He is right**, and the target
   is the decisive argument — a count taken while families are missing measures
   the WIRING, not the READING.
3. **A fifth stage, INFER**, for probable outcomes weighed across decisions.
   Sean's design; §5 of the plan. **Not before the count.**

---

## 2. WHAT THIS SESSION LANDED

| | |
|---|---|
| `5a4ef68d` | the 361 refused arcs SPLIT — and both repairs it invited REFUSED |
| `bbb8f050` | `articulation_owner` decides and the marks reach the file; stubs **3 → 2** |
| `a292c153` | the plan: wire first, count, then infer |
| `fec6a7b0` | the five stages, traced through one real note, into CLAUDE.md |
| `c877d02a` | the articulation arm and the control that was wrong |

Suite **3586 passed / 11 skipped**. `health --check`, `inventory --check`,
`gather_coverage` green, `unaccounted 0`.

---

## 3. ⚠️ THE TWO RESULTS THAT ARE REFUSALS

**The 361 arcs are bounded and PARKED, not next work.** 170 (47.1%) have no
head anywhere in the arc's bars, 109 (30.2%) have heads the span misses, 82
(22.7%) have exactly one. So *"the remaining three quarters are the DETECTOR's"*
is about half right, and that half is an UPPER bound. **Both obvious repairs
are refused by their own controls**: the `arc_owner` story fires on 95.9% of
failures against a **base rate of 92.2%** among the arcs that DID pair, and
widening `_SLUR_ARC_PAD_NOTEHEADS` is refused because bucket B decays **smoothly
with no plateau** — the gap that constant was read off exists on an engraved
page and not on this scan.

⚠️ **That last one generalises and is the most transferable thing here: a
constant measured on engraved ink may have no plateau on a scan.** The
articulation constant was then checked the same way and **survives** (all 18
attached marks at 0.003-0.435 against a 0.75 cut). Check the others.

---

## 4. ⚠️ THREE PROCESS FAILURES, ALL MINE, ALL CHEAP TO REPEAT

1. **A mutation battery reported TEN SURVIVORS while having deleted both source
   files.** Backup written to one name, restored from another; `sed` emptied
   `ownership.py` and `export.py`; pytest said *"no tests ran"*; the classifier
   grepped for `"failed"`, which an empty run does not match. **The work was
   uncommitted.** Recovered, then committed immediately.
   **The general form, and it is the whole lesson: a battery can pass by
   refusing everything, AND it can pass by accepting everything.** Both print a
   clean summary line. The rewrite restores from `git show HEAD:<path>`,
   refuses a mutation that does not textually apply, asserts the exact expected
   pass count, and reports `BROKEN` rather than `SURVIVED` on an unrecognisable
   run. ⚠️ **It caught `${=T}` on its own first run** — zsh not word-splitting
   a two-path variable — reporting ten `BROKEN` instead of ten false survivors.
2. **`pkill -f diag.py` killed three monitors**, whose shell loops contain the
   literal string `pgrep -f "diag.py"`. CLAUDE.md already records this hazard at
   a much higher cost. **`pkill -f <pattern>` matches WATCHERS of that pattern
   as surely as the thing itself.** I had the PID and did not use it.
3. **A control that fired on its own side effect** — see §5.

---

## 5. THE CONTROL THAT WAS WRONG, AND WHY IT MATTERS MORE THAN THE RESULT

The articulation arm reported *"outside the `<articulations>` blocks, the two
files are DIFFERENT"* while every family count was identical. `_mxl_note`
emits `<notations>` only when non-empty, so a note whose ONLY mark is an
articulation gains a **wrapper** as well as the block, and the line-based strip
removed the block and left the wrapper.

**A control reporting a defect it was not built to see is how a REAL regression
hides behind an expected one.** Replaced with a structural strip; the arm now
NAMES a difference rather than only flagging one.

---

## 6. ⚠️ WHAT `articulation_owner` CORRECTS IN THE PREVIOUS HANDOFF

It called the two fed stubs *"one repair each (write the adjudicator; inputs
are gathered)"*. **The tree said three.** `grep -c articulations
staged/export.py` was **0** and `FAMILIES["articulation"]` carried an **empty
counter tuple**, so the adjudicator alone would have created a fresh
`decided_and_unwritten` — the bucket the arc session had just emptied.

⚠️ **That correction applies to `wedge_anchor` MORE strongly.** `_mxl_note`
already takes `articulations=` / `ornaments=` / `fermata=`, so those renderers
are free — but `_mxl_direction` emits only `<dynamics>` and `<words>`, so a
wedge has **no renderer to reuse** and needs the arc merge as well.

---

## 7. REACH — the table that re-ranks the wiring

By detector CLASS. ⚠️ **Never by `category`**: all ten `artic*` classes carry
category `ornament`, and the first draft of this table counted 300 "ornaments"
on a page holding none.

| family | Litolff p1-3 | Brahms p0-3 | state |
|---|--:|--:|---|
| **fermata** | **63** | 0 | NO QUANTITY — the biggest unwired family |
| articulation | 24 | 196 | ✅ wired |
| **wedge** | **0** | **47** | stub; Brahms is its ONLY fixture |
| ornament | 0 | 7 | NO QUANTITY |
| tremolo | 0 | 0 | detector fires none — wiring gains nothing |
| arpeggiato | 212 | 214 | ⚠️ MISREAD stems/barlines, NOT a family |
| accidental | 155 | 733 | deliberately not its own quantity |

Also on the Brahms record: **656 aug_dot** against Litolff's 20 — which is the
document the dotted REST's unmeasured COST has been waiting for.

---

## 8. OPERATIONAL

* Four symlinks in a worktree: `library`, `tools/omr/training/data/weights`,
  `.venv-surya`, `.venv-omrned`. The staged pipeline needs only the weights.
* **Timings measured THIS session, under CPU contention**: a Litolff 3-page
  gather **~8 min**; a Brahms 4-page gather **~45 min** (413 MB); one
  re-adjudication of the Litolff record **~6 min**; of the Brahms record,
  **> 40 min and it did not finish**. The full suite **~9.5 min**.
* ⚠️ **A `difflib` over two exported files GOES QUADRATIC** — one ran 50
  minutes on ~50k lines and produced nothing. Compare structurally, or diff
  fragments, not lines.
* ⚠️ **The Brahms articulation arm was still running at the end of this
  session** and no result is claimed from it. Its record also predates the
  articulation change (saved verdicts read `not_implemented: 196`); GATHER is
  untouched so re-adjudicating is valid, but it is a pre-change tree's record.

```bash
OMR_SURYA_KEEP_ALIVE=0 python3 -u -m tools.omr.staged <pdf> --pages 1-3 \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
    --out staged.json
python3 benchmarks/omr-staged-arc-split-2026-09/split_arcs.py staged.json [--pad-sweep]
python3 benchmarks/omr-staged-articulations-2026-09/articulation_arm.py staged.json
zsh benchmarks/omr-staged-articulations-2026-09/probe/battery.sh
```
