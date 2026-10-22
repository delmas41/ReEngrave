# Handoff — 2026-09-08 night: Step 2 closed, Step 4 promoted ahead of Step 3

Written at the close of the local session that picked up
`docs/handoff-2026-09-08-evening-to-local-session.md`. **Everything described
here is committed and on `main`.**

⚠️ Read `docs/handoff-2026-09-08-next-steps.md` for the standing rules and the
definition of Steps 1–5. This file says what closed, what moved, and why the
ORDER changed.

---

## What closed

### Step 1 — already done before this session (ornaments export gap).

### Step 2 — DONE. `benchmarks/omr-staged-shadow-2026-09/STEP2_2026-09-08.md`

Two real runs: `brahms-sym1-mvt1-317803-p2` (2 systems, 14+13) for the
divergence table, `beethoven-sym5-mvt1-984073-p2` (2 systems, 11+11) as the
GROUPS control.

1. **The table was blind to 99.3% of what staged decides** — 12 of 20
   quantities and 18,177 of 18,302 verdicts had no row at all, because
   `divergence()` iterates `legacy.items()`. Now `staged_only` + `coverage`.
2. **4 of 16 "disagreements" were NARROWED verdicts** read as DIFFER. Now
   `NEW_NARROWING`, and only a disagreement when legacy's answer is outside the
   candidate set.
3. **GROUPS: "run a multi-system page" was necessary and NOT sufficient.**
   `_slot_fact` puts the system's staff count in the key (deliberately), so a
   14+13 page corroborates nothing BY CONSTRUCTION. The 11+11 control works:
   `clef_across_systems` 8 unanimous + 1 split, `staff_group` 11 unanimous,
   `checked_nothing` 4 of 6 → 2 of 6, first catch ever.
4. **The catch, adjudicated by Sean against the print:** the Fagotti staff opens
   in BASS, changes to a C clef, returns to bass two bars later. Two findings —
   a `clef_locator` FALSE POSITIVE (it never saw the C clef; it fired `tenor` on
   cell 0, which prints a bass clef, unopposed because the detector read
   nothing), and **a mid-staff clef change neither pipeline can express**
   (`Q.CLEF` is staff-scoped, no arm reads past cell 0).

### ⚠️ THE STAGED PIPELINE CANNOT BE SCORED, AND IT IS STRUCTURAL

Both instruments take MusicXML on both sides. **Staged produces none and has no
exporter** — its result is `record/summary/adjudication/agreement/evaluation/
stubs`, no `pages` key. `git log --all -S` finds no bridge on any branch and
**nothing outside `tools/omr/staged/` and its tests imports the package**.

So "never scored" is a MISSING COMPONENT. ⚠️ Not "nearly done, needs plumbing":
an exporter must reassemble events, voices, measures and parts from
subject-addressed facts, and 6 of 21 decisions are stubs (every arc, dynamic
and direction quantity). **Do not start it as a side quest.**

---

## ⚠️ WHY STEP 4 NOW COMES BEFORE STEP 3

Step 3 was opened and **is blocked by Step 4, measured rather than argued**
(`benchmarks/omr-rests-2026-09/FINDINGS.md`):

    rest rows 4,239   ASSESSABLE 416 (9.8%)   from 2 of 11 rows

On nine of eleven scan-gate rows the PART JOIN fails, so every symbol is
`uncorresponded` with reason `part_unresolved` and nothing compares to
anything. Any rest number from that corpus is a statement about two Dvořák
pages.

That is Step 4's own bucket (`entire staff` / no part correspondence, 51% of
symbols) sitting upstream of Step 3's measurement. **Fixing the join does not
just improve a score — it is what makes Step 3 measurable at all.**

### Step 3 is NOT wasted: the first look already found the mechanism

On what IS assessable, rests are the larger half here too (attribute errors
**rests 174 / notes 123**), and **139 of 173 rest duration errors are one
mechanism**: a whole-measure rest emitted as a literal whole note, 4.0 quarter-
lengths, regardless of meter. Dvořák 9 is in 4/8 (bar = 2.0), so the bar is
twice over-full.

⚠️ **The sizing code is correct and simply not fed.**
`export._measure_rest_beats` computes `num*4.0/den` and returns 2.0 for 4/8;
it is called with `None`, because both call sites resolve
`m_time = measure.get("time_signature") or <staff/part fallback>` and neither
carries a meter. `None` → 4.0 by documented design, which is right for an
UNKNOWN meter and wrong here — the exporter writes `<time>4/8</time>` into the
same part's `<attributes>` and then a 4.0-quarter rest into its 2.0-quarter
bars. **It had the meter and did not consult it.**

⚠️ And the question underneath it is Step 4's again: **why does the staff carry
no `time_signature`** when the page reader found 4/8?

---

## The order for the next session

### FIRST — Step 4: `entire staff` is three problems wearing one name

The handoff's three causes, still filed as one bucket:

1. `_stitch_slots` refusing (3 rows)
2. one-line percussion staves the detector never finds (3 rows)
3. a `works.json` arity convention where one lineup entry covers two printed
   staves (bach)

⚠️ **Any structural fix priced against that bucket is priced against a
mixture. Separate the causes before attempting any of them.** Already measured
and related: `OMR_SLOT_STITCH` and `OMR_CONDENSED_PARTS`, both default-off,
oracle ceiling −4,557 scan edits, and **the condensed COUNT cannot come from
the page** (proved — it is a property of the encoding).

**New evidence from this session** to fold in: the ledger's `part_join` field
reports resolved/unresolved per row directly, so the causes can be separated
without re-deriving them — 9 of 11 committed pairs report `unresolved`.

### THEN — Step 3: rests

Return with a corpus that can see them. The engraved benchmark pairs 1:1 by
construction and can assess all rest rows; the scan gate cannot until Step 4
moves. The measure-rest fix is diagnosed and waiting.

---

## Traps this session paid for (all now written into the code)

* ⚠️ **`symbol_ledger` emits a row per symbol on BOTH sides.** On a `truth`-side
  row `attrs` is the TRUTH and `partner_attrs` is ours. Reading `attrs` as ours
  produces a table that is exactly backwards, and nothing in the column names
  warns you. Documented at the top of `probe_rest_durations.py`.
* ⚠️ **Check the FRAME before comparing coordinates.** `clef_located` is in
  `cell:0`, `staff_extent` is in `page`; comparing them produced a confident
  wrong conclusion about where a clef sat.
* ⚠️ **`Verdict.candidates` holds `Candidate` dataclasses at runtime**, dicts
  only once serialised. A unit test whose fixture used dicts was green on a
  shape the pipeline never produces and died on the first real page.
* ⚠️ **A surviving mutant is not automatically a vacuous test** — check what
  else covers the line first. `parse_in_key` and `_parse_bare_key` are
  redundant for the same label.
* ⚠️ **`OMR_SURYA_KEEP_ALIVE=0` for every unattended run.** The resident server
  is shared; nothing was `pkill`ed.

## Also landed this session (off the critical path)

* `claude/rescue-midstaff-key-lilypond` — mid-staff KEY changes reaching the
  LilyPond exporter, rescued from **uncommitted** working-tree changes in a
  stale worktree; it exists nowhere else in history. ⚠️ NOT merge-ready: its
  `export_coverage.py` hunk documents the hand-written `VISIBLE` list that
  commit `74aa7272` deleted. Same defect class as the mid-staff CLEF finding.
* `tools/omr/key_consensus.py` — concert key by consensus, written key per
  staff by deduction. Pure, reports only, wired into nothing. Parked as **D21**.
  Found four transposing instruments the lexicon calls concert pitch (Alto
  Flute in G, Oboe d'amore in A, Bass Sarrusophone in B♭) — NOT fixed, because
  a lexicon change is global and validates against the 1422-label corpus.
