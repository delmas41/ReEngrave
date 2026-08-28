# ReEngrave OMR — where we are, 2026-08-28

A cross-session reconciliation. Five sessions worked the OMR pipeline today; three
were still running when this was written, so treat the "unmerged" section as a
snapshot rather than a settled state.

`PROJECT_STATUS.md` is the project's standing "where we are" file and is **stale**
(last updated 2026-06-10 — it predates July's dossier/consistency work and all of
August's clef, key-signature and contextual work). This document covers today only.

---

## 1. The sessions

| Session | Branch | State |
|---|---|---|
| Clef recognition improvement | `claude/clef-recognition-improvement-ab75f6` | **running**; work is on main |
| Key signature recognition | `claude/key-signature-recognition-57ec0a` | stopped; work is on main |
| Recognition improvement next steps | `claude/recognition-improvement-next-2f1709` | **running**; 4 commits unmerged |
| OMR key-signature locator tuning | `claude/omr-key-signature-tuning-3144e5` | **running**; at main, nothing committed yet |
| Contextual analysis | `claude/reengraver-contextual-analysis-29cdd5` | 8 commits unmerged |

## 2. What landed on main today (main = `efd59f7`)

Clef and key signature stopped being classification problems and became **geometry**:

- **`clef_geometry.py`** — read *which staff line the clef names*, not which glyph class
  it is. Alto/tenor/soprano/mezzo/baritone are the same glyph on different lines, so no
  classifier or ensemble can separate them; measuring position does.
- **`clef_locator.py`** — a classical-CV C-clef locator for scores where no model sees a
  clef at all. Rejects an F clef by its two dots rather than by proportions, and will
  not nominate a notehead stack.
- **`staff_header.py` + `header_ink.py`** — a *measured* header window, fixing the
  documented `Staff.x_start` failure (the longest-unbroken-ink-run heuristic lands past
  the clef on degraded prints).
- **`key_signature_geometry.py` / `key_signature_locator.py` / `key_signature_vote.py`**
  — positional key-signature reading plus a cross-page vote.
- **`clef_source`** on each staff dict — names which reader supplied the clef
  (`detector` / `specialist` / `cv_locator`), **absent meaning defaulted**. This is the
  single most useful field for judging a page's pitches.
- **Body-text staves are filtered out** before system assignment, closing the
  "paragraphs detected as staves" item.
- **Phase-1 test expectations corrected against the pages themselves** (`e6a4110`,
  `9509990`). This retires the "Phase 1 has no regression baseline" objection that had
  been blocking Phase-1 changes for months — it is no longer a valid reason to defer one.

Suite on main + the contextual branch: **795 passed, 0 failed.**

## 3. What is unmerged

**`claude/recognition-improvement-next-2f1709`** (4 commits, active) — staff recovery
via a "comb" pass that finds lightly printed staves the ink gate missed, plus
spacing-outlier rejection; a fix for staff-line removal being a no-op on most
orchestral scores; stem/beam ground truth and the stem bug it found; beams redefined as
horizontal ink that stems run into.

*Trial-merges into the contextual branch with **zero conflicts**.* It is complementary,
but see the caveat in §5.

**`claude/reengraver-contextual-analysis-29cdd5`** (8 commits, this one) — system
grouping by vertical connectivity (43% → 86%); instrument labels from the PDF text
layer; stable slot identity by monotone alignment (92% label purity); clef proposal from
the instrument's written range. Plus the disproven clef-from-key-fit benchmark.

**`clef-phase0-eval`** (15 commits) — the time-signature labeling batch and the clef
fine-tune Phase-0 conclusion (**do NOT deploy `clef-ft` weights** — they fix all-treble
but collapse dense-page noteheads 2506 → 114). Carries **hand-drawn label verdicts**,
which are irreplaceable; the branch's last commit exists specifically to preserve them.

## 4. Reconciliation findings

**No work is at risk of being lost.** Specifically checked:

- The clef session's worktree is sitting in an **interrupted merge** (`UU
  clef_locator.py`, 18 uncommitted paths). Both merge parents are already ancestors of
  main, the conflict markers are gone, and main's `clef_locator.py` is a **superset** —
  it has the `staff_band_spaces` band filter *and* the refactor onto the shared
  `header_ink` rule-strippers, where the worktree copy has only the former. It is an
  abandoned duplicate of a merge that was completed properly via
  `reconcile/clef-into-main`. Nothing unique. Resetting it is that session's call, not
  ours — it is still running.
- Four older worktrees (`blissful-payne`, `silly-bose`, `distracted-bartik`,
  `adoring-kare-52c6`) hold uncommitted frontend/backend edits, but **zero files
  modified today**. They are leftovers from earlier sessions, not today's work.
- `NOTES.md` on main correctly marks the SmartScore ensemble item **partly overtaken**:
  the clef half is solved by geometry; the time-signature half and cross-page state
  resets remain open.

## 5. The one thing that genuinely interacts

`recognition-improvement-next` **recovers staves that the ink gates missed.** The
contextual branch's numbers — 86% system grouping, 92% slot label purity — were measured
on a staff set that was missing those staves. The two compose cleanly in the text, but
**the contextual measurements should be re-run after that branch merges**, because more
complete staff detection changes both the systems and the reference layout they are
built from. Expect them to move; most likely upward.

Related and still open: `_group_into_staves` accepts only five-peak windows, so
**one-line percussion staves are invisible** and every staff below one shifts by a slot.
Proven in `tools/omr/tests/test_system_grouping.py`. The old reason for not fixing it
("Phase 1 has no regression baseline") no longer applies — see §2.

## 6. Suggested merge order

1. `recognition-improvement-next` — it is upstream of everything (better staff detection).
2. Re-run the contextual benchmarks, then merge the contextual branch.
3. `clef-phase0-eval` separately, for the labels; the fine-tuned weights stay unused.

## 7. Where the pipeline actually stands

Reading a score now runs: staves (with body-text filtering) → systems by connectivity →
part identity per staff → instrument, from the text layer where there is one → clef by
geometry, then by instrument range where geometry was silent → key signature by position
and cross-page vote → pitches → the five internal-consistency checks.

The honest gaps: instrument identity needs a text layer (~28% of the corpus), time
signatures remain unreliable, one-line percussion staves are invisible, and the
key-signature *detector* is weak enough that Beethoven 5 p15 reads `0 sharps / 0 flats`
across all 18 staves of a C-minor movement.
