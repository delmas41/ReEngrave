# RESUME HERE — state at the end of 2026-09-20

Everything is on **`claude/integration-2026-09-18`** (PR #57), pushed and
verified with `git merge-base --is-ancestor`, not by trusting a push.
⚠️ **`main` is stale by three days — branch from the integration branch.**

✅ **NOTHING IS RUNNING. The pair-rule gate landed and is MERGED** — see §4,
which is now a RESULT and includes the day's sharpest finding.

---

## 1. ⚠️ THE ONE THING TO READ FIRST — the conventions are now countable

`tools/omr/conventions.py` parses `docs/engraving-conventions.md` (a PARSE, not
a copy: zero convention text in the module). Two audits landed together and
they agree:

| | |
|---|--:|
| conventions in the registry | **114** (not 125 — see §5) |
| mechanically testable | **109** |
| refuted (and unreadable as live rules, enforced) | **5** |
| entries that declare nothing reads them | **44** |
| **conventions reaching NO decision** | **94 of 114** |
| decisions in the pipeline | 28 |
| …declaring a convention they check | 16, **32 statements** |
| **declared checks NOT actually performed** | **16 of 32** |
| performed checks that can actually FAIL | **1 of 7** |

**Whole categories reach nothing**: stems & beams 18/18, rests 8/8, dynamics
7/7, articulations 9/9, barlines 4/4. ⚠️ *Reaches no decision* is not *reaches
no code* — some are implemented elsewhere and never declared.

**Three declared-but-absent checks are worse than bookkeeping:**
1. **`part_partition`** declares *"each part carries ONE instrument across
   every system"* and `Q.INSTRUMENT` in `wants`; **its body reads neither**
   (verified: no `ev.rows` call at all). Its own docstring spends forty lines
   on the 12-of-75 graft that check would catch.
2. **`key_signature`** declares corroboration *"CONSUMED, default-ON"*. There
   is **exactly one import** of `key_signature_corroboration`, in
   `transcribe.py` — the LEGACY path. The staged path mentions it in three
   docstrings and imports it nowhere. ⚠️ CLAUDE.md describes it as shipped.
3. **`staff_group`** asserts a bracket group is one instrument family — which
   registry entry `[C59]`, status MEASURED HERE, **denies in its title**.

⚠️ **STRUCTURAL: 6 of the 7 performed checks are additive weighted `Term`s,
not tests that can fail.** So `implicates` — which the decorator REQUIRES and
documents as *"what a FAILED check implicates"* — is inert nearly everywhere.

⚠️ **And the gap runs both ways: the BAR SUM — six of the 32 statements, five
decisions, the most-cited constraint in the project — has NO registry entry.**
It is implemented; the document does not know about it.

⚠️ **NOTHING IS WIRED, deliberately.** Wiring alongside the measurement makes
the reach measurement circular (the `Q.INK` / `OMR_FAMILY_POSITIONS`
discipline). The foundation exists and is checked; what to wire first is §6.

Read `benchmarks/omr-convention-coverage-2026-09/FINDINGS.md` and
`benchmarks/omr-convention-registry-2026-09/FINDINGS.md`.

## 2. THE PAGE FRAME — a WINDOW was refuting a rule

`tools/omr/vertical_runs_page.py` + `benchmarks/omr-vertical-runs-page-2026-09/`.
Sean's barline test read **0 of 19** barlines in the cell frame and reads
**11-13 of 19** in the page frame between 0.25 and 0.60 staff spaces, against
**0 of 63** stems. The measure cell was clipping the ends. **The decisive
column is the STEM one** — the barline half inherits the predecessor's
circularity. Battery 17/17 red.

## 3. ⚠️⚠️ THE STEM-ATTRIBUTION LANE IS WITHDRAWN — refuted by the print

*"148 and 228 heads take a direction from a stroke that is not theirs"* —
**withdrawn, do not quote.** Its chord test could not see a TWO-NOTE CHORD
(it required a companion above AND below), so octave pairs were filed as
faults — **64% / 95%** of the flagged group. Sean, shown the first strip:
*"it is an octave of C's and the stem belongs to both."*

Then Sean diagnosed the residual: ***"two separate stems being measured as one
stem"*** — upper voice stemming UP to its beam, lower voice DOWN to its beam,
fused. **Tested and confirmed on the case he saw**, then bounded:
**17 of 4,225 runs (0.40%) overshoot at both ends; ceiling 13 noteheads of
5,684 (0.23%); of 13 crops opened, ONE is the fused-stem fault.**
⚠️ **The Litolff 18% INVERTS — 6 of 6 opened are NOT fused stems.**
**Recommendation: do not build the segmentation repair.** 0.23% is not worth a
change to `Q.STEM`.

## 4. ⚠️⚠️ THE PAIR RULE — THE FIXTURE THAT JUSTIFIES IT PRINTS NO ACCIDENTALS

`OMR_STEM_NOTEHEAD_GATE` (**default OFF**), `benchmarks/omr-stem-notehead-gate-2026-09/`.
`_drop_paired_strokes` deletes a pair of verticals on the premise that it is a
sharp or a natural. Re-derived to the unit: **244 deleted, 80 on a notehead,
62 (77.5%) two genuine stems, 73 heads (9.2% of 793)** stop abstaining without
it.

⚠️⚠️ **THE FINDING IS ABOUT THE RULE, NOT THE GATE.** `CLAUDE.md` justifies the
rule by the LilyPond reference sheet (*"+7/+8/+5/+2 to −1/0/+1/0 on a truth of
48"*). **`benchmarks/omr-phase4-lines/reference-lines.ly` PRINTS NO ACCIDENTAL
AT ALL** — verified independently: **zero altered pitches, zero `\key`
directives**, every pitch a natural. **So that win was never a measurement of
accidental rejection.** All 28 of its deletions land in ONE cell of staff 0
and all 28 stand on a notehead. At per-bar resolution the shipped rule
**EMPTIES the chord bar** (truth 4, ON 0); the page total inverts only because
two errors cancel.

**The gate itself**: OFF reproduces **1,920 / 2,305** exactly; ON is **+80 /
+152 strokes, every one on a notehead, 0 lost**; stemless heads **793 → 720**
(the 9.2%, reproduced from the opposite direction). Hand cells ON 15 / OFF 53
/ **GATED 20**, worse on 3, better on 0. Battery **21 arms, 21 red**. The
legacy `transcribe` path is unchanged **by construction** (`detect_lines`
passes no detections), pinned by an AST test.

⚠️ **Recommendation: leave the flag OFF.** No crop was cut for either plate, so
**accuracy is unestablished** — including the 3 hand cells the gate worsens.
The standing objection is not an *n* argument: **the gate couples `Q.STEM` to
the detector.** ⚠️ And one quoted figure is a composition coincidence the agent
named itself (GATED 4 = truth 4 over four printed chords; the supportable
claim is *strokes on 2 of 4*).

**The item for Sean is not the gate.** It is that a production rule is
justified by a page total on a fixture with no accidentals in it, and the same
fixture at its own per-bar resolution says the rule empties a bar of chords.

## 5. ⚠️⚠️ CORRECTIONS TO MY OWN CLAIMS TODAY — read before quoting me

1. **"125 conventions" was HEADINGS.** Eleven are section titles. It is **114**,
   confirmed by two independently-written parsers.
2. **My Breitkopf staff-space figures used a FLAT 100 px** instead of
   `Q.CELL_STAFF_SPACE` — the exact trap that quantity exists to prevent. Only
   **514 of 817** Breitkopf cells sit at 100 (Litolff: 1,167 of 1,180, which is
   why it escaped). Corrected in place; direction survived, numbers did not.
3. **"The suite is green" was scoped.** `pytest tools/omr` was green while
   `pytest tools` was **15 failed / 20 errors** — a dashboard schema refusal
   red since v0.6.0, pre-existing (control at the pre-session tip: identical).
   Fixed; whole tree now **4,621 → 4,662 passed / 19 skipped / 0 failed**.
4. **I committed 698 lines I never read** via `git add -A` in a worktree an
   agent was using. Removed; it remains in history at `129a6495`.

## 6. WHAT IS OPEN, ranked

1. **Wire the first convention** — and the ranked candidate is not a stem
   rule, it is **`part_partition` reading `Q.INSTRUMENT`** (§1.1): declared,
   absent, and the damage is already on the record.
2. **`key_signature_corroboration` on the staged path** (§1.2) — CLAUDE.md
   says shipped; the staged path does not import it.
3. **Give the BAR SUM a registry entry** (§1) — the most-cited constraint in
   the project, absent from the document.
4. **Re-justify or retire `_drop_paired_strokes`** (§4) — its
   cited evidence does not measure what it claims. The gate is built and
   OFF; the open question is the RULE.
5. **Three prose figures in the registry do not reproduce** (a heading saying
   "six" over five entries; "10 of 87" where 8 hold; "6 of 27" where zero do).
   All inherited from the pre-merge harvests. Not fixed — the brief was
   handles, not rewriting.

## 7. ⚠️⚠️ PROCESS, PAID FOR TODAY

* **FENCE DIRECTORIES, NOT FILES.** Three agents took over a worktree I was
  using; two convention agents shared one and produced an add/add conflict on
  a findings file. **A brief must say `git worktree add` your own DIRECTORY.**
* **A SUCCESSFUL PUSH IS NOT A LANDED MERGE.** My first merge push did not
  survive — an agent had branched from before it and integration ended up on
  its line. Nothing was lost, but only because I re-checked with
  `merge-base --is-ancestor` afterwards. **Verify after pushing, every time.**
* **AN AGENT TOLD NOT TO DELEGATE, DELEGATED.** One returned in 78 s having
  written a plan and secretly spawned a sub-agent, which then wrote into a
  worktree it did not own. Its report described work that did not exist.
* **`| tail` swallows the exit code**, and `pytest ... | tail -3 > f; echo $?`
  reports **`tail`'s** status. Use `${pipestatus[1]}`.
* **Backticks inside `git commit -m "..."` are command substitution in zsh** —
  commit `402c4d18` lost two words that way. Use a heredoc.
* **NEVER `git add -A`** anywhere another agent may be working.
* **Verify every agent claim against the TREE.** Of today's reports: one
  corrected my unit error (right), one claimed a task was already done because
  my staging error had made it look so (wrong), one produced nothing while
  reporting progress. The tree settled all three.

## 8. ⚠️ WHAT IS NOT ESTABLISHED

n is **2 documents, 2 publishers, 8 pages, both SCANS** for every stem and
barline figure today; the engraved family is untouched. **No OMR-NED figure is
claimed anywhere** — the metric is symmetric and would pay for emitting fewer
symbols. **No convention has been wired into any decision**, so nothing here
has yet changed a note in a file. The 79 stem-attribution strips are
**unadjudicated** beyond the handful Sean read in chat.
