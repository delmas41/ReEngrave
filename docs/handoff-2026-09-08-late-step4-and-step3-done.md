# Handoff — 2026-09-08 late: Step 4 separated, Step 3's mechanism found and fixed

Written at the close of the session that picked up
`docs/handoff-2026-09-08-night-step4-then-step3.md`. Branch
`claude/reengraved-step-4-step-3-105645`, two commits, pushed. **NOT merged.**

⚠️ Read the two FINDINGS files before trusting anything restated here:
- `benchmarks/omr-part-join-2026-09/FINDINGS.md` (Step 4)
- `benchmarks/omr-rests-2026-09/FINDINGS.md` **§7 onward** (Step 3; §1–§5 are
  the superseded first look, kept because the corrections are the finding)

---

## STEP 4 — DONE. The bucket is four causes, and only one is the reader's

| | rows | symbol rows | share | whose fault |
|---|--:|--:|--:|---|
| **A** `_stitch_slots` refuses | 3 | 6,937 | **46.3%** | **the reader** |
| **B** lineup names one-line percussion staves | 3 | 4,815 | 32.1% | the ledger's arity gate |
| **C** one lineup entry, several printed staves (bach cembalo) | 1 | 2,469 | 16.5% | the ledger's arity gate |
| **D** no lineup at all (mahler p2) | 1 | 771 | 5.1% | a missing hand-verified fact |

Classifier is DERIVED from `works.json` + our part count, and the causes sum to
the pooled `part_unresolved` mass **exactly** (14,992 vs 14,992) with 0 rows
`unexplained`. **The handoff named three causes; there are four** — D was
silently inside it.

**What each needs next:**

* **A** — `OMR_SLOT_STITCH`, already built, measured, never worse. **Its `n`
  objection is unchanged** (3 rows = 2 distinct pages of one structural shape),
  and flipping a default is Sean's call. What is new is that those 3 rows own
  46.3% of the unassessable mass: a different argument for the same change, not
  a new score.
* **B, C** — an arity gate comparing like with like. **The durable fix is a
  FIELD in `works.json`**, not code: `one_line: true` on a percussion-rule
  entry, `printed_staves: 2` on bach's cembalo. WHICH entries are one-line is
  not structural today — only the COUNT is derivable
  (`len(staves) - page.n_staves`) — so `price_unlocks.py` hand-reads the
  indices from each row's own prose note and ASSERTS the count. **That is a
  hand-verified-data change and wants Sean, not an agent guessing.** Ceiling on
  the two committed rows: mahler p3 **+1,059**, bach p1 **+1,846** assessable
  rows, from 0.
* **D** — mahler p2 needs a `staves` map. Nothing on disk can supply it.

## STEP 3 — mechanism found, fixed, and the metric cannot see it

**A whole-rest glyph is not four quarters of silence.** 558 of 618 wrong rest
durations (90.3%) are a bar holding exactly one rest. Fixed via
`export._is_lone_measure_rest`. ⚠️ **Restricted to the WHOLE-rest glyph** — the
first cut accepted any lone rest and inflated single detected QUARTER rests
into full bars, costing 34 engraved edits.

⚠️ **The previous session's diagnosis was wrong**: `_measure_rest_beats` is not
fed `None`, it is **never called** — the bar has a detected rest, so the
empty-measure branch is not taken. **Read the branch, not the resolution.**

⚠️⚠️ **OMR-NED IS IDENTICAL ON BOTH FAMILIES** — engraved 0.12138/2532 in all
23 categories, scan gate 34,963 edits on all 11 rows — while the ledger records
`rest.type` 933 → 10 and `rest.duration_ql` 328 → 4 on the engraved eleven with
**every non-rest family identical to the row**. Positive control: six works'
rest `<duration>` values moved; Beethoven 3 is in 3/4 and its whole rests went
4.0 → 3.0. **Use the ledger for anything about durations.**

## ⚠️ THE INSTRUMENT WAS LOSING 1,771 TRUTH SYMBOLS

`coverage_check()` was computed on every row, written into
`out/ledger-summary.json`, and **read by nothing** — `balanced=False` on 9 of
20 rows for as long as it existed, which its own docstring calls an instrument
defect that voids every figure. Class C, inside the instrument built to make
the metric legible. And its rest rule was **98.5% wrong**: 1,050 of 1,066
absorbed rests are the all-parts-rest case an engraver prints.

Fixed (new outcome `absorbed_by_condensation`; `run_ledger` READS the control).
Controlled A/B on the committed 20-row summary: unbalanced 9 → 0, `rest.type`
471 → **963**, `rest.duration_ql` 471 → **942**, **every non-rest figure
identical to the unit**. `out/ledger-summary.json` and `out/ledger-rows.csv`
were regenerated under the fixed instrument and are committed.

---

## ⚠️⚠️ THE "NEXT STEP" THIS FILE FIRST NAMED WAS A FIXTURE ARTEFACT

This section originally said the residual rest mass is a meter-READING gap —
*"only 86 of 159 exported parts carry a `<time>` at all"*. **Checked before
acting on it, and it is not.** Per row rather than pooled: every
movement-OPENING page reads its meter on **100%** of staves (12/12, 12/12,
14/14, 15/15) and every CONTINUATION page reads almost none (0/22, 2/22, 1/13,
2/15). Correct — a meter is printed at a movement's start and nowhere else, and
`transcribe` has carried it forward as `source="carried_from_previous_page"`
since 2026-08-31. **The gate transcribes ONE PAGE PER ROW, so the carry has no
previous page.**

Pages 1-2 of the same PDF in ONE call (65.5 s): page 2 goes **0 → 20 of 22**
staves with a meter, exported parts **12 → 34 of 34**, and **218 of 255 lone
whole rests come out at the printed 2/4 bar length** where the one-page fixture
sized every one at 4.0. **So the §Step-3 fix is worth MORE in production**
(`OMR_MAX_PAGES=5`, one call) than the benchmark can show.

⚠️ **CARRY THIS, it is bigger than the number: the scan gate's one-page cut
silently disables every PAGE-SPANNING mechanism, which then reads as a pipeline
gap.** Ask whether a mechanism spans pages before pricing it on that corpus.

**What genuinely remains** is 4 staves of 34 reading 4/4 or 1/4 on a 2/4
movement, all `source: None` — a staff keeping a disagreement with its own
system's majority. That is a VOTE/override question
(`rhythm.drop_uncorroborated_meter_changes`, the half-the-staves page vote),
not a reading one, and costs 37 wrongly-sized measure rests on two pages. It
also answers the old handoff's closing question (*"why does the staff carry no
`time_signature`?"*): on Dvořák p5 it DOES; elsewhere it is the one-page cut.

So the ranked next work is: **(1)** the `works.json` arity field for causes B
and C above — cheapest, needs Sean's confirmation of nine hand-read indices,
unlocks 4 of the 8 rows; **(2)** re-measure the rest residual with 11 rows
joined instead of 7, which would be the first corpus-wide rest figure; **(3)**
the 4-staff meter-vote question.

Then, in the original order: **Step 5** (six staged stubs) — still deliberately
last, and the staged pipeline **still has no exporter**, which is a missing
component, not plumbing. Do not start one as a side quest.

## Suite

**3,057 passed in 8m50s**, `tools/omr/tests/` with `test_direction_text.py`
excluded (its Surya-venv test is environment-dependent in a worktree and is a
documented pre-existing condition, not a breakage). `export_coverage --all`
exits 0. The music21 cross-parser and the ledger's identity self-check are
clean on all 22 re-exported files.

## Traps this session paid for

* ⚠️ **`part_index` on a TRUTH-side ledger row is the TRUTH part index**, not
  ours — a condensed staff makes those different numbers. Mapping it onto our
  part list said a Beethoven bar holding no rest held one, and turned 90% into
  55%. **The same frame class as `clef_located` (cell) vs `staff_extent`
  (page); it recurs, and it always looks plausible.**
* ⚠️ **The ledger CLI takes no `part_join`.** `python3 -m tools.omr.symbol_ledger
  PRED TRUTH` joins positionally only where the part counts already agree, so
  against a 38-part Mahler reference it never does — which is where §1's
  "9.8% assessable" came from. Use `run_ledger.py`, or build the join yourself.
* ⚠️ **`benchmarks/omr-hairpins-2026-09/score_export_arm.py` is the right tool
  for an export A/B** on the engraved benchmark: it re-exports the eleven
  STORED transcriptions, so the detector never re-runs and a difference cannot
  be detector noise. Minutes, not half an hour.
* ⚠️ Four symlinks in a worktree, and a fifth thing: `.venv-omrned`,
  `.venv-surya`, `tools/omr/training/data/weights`, plus
  `OMRNED_PYTHON` for `orchestral_eval`.
* ⚠️ `timeout` does not exist on this macOS; `| tail` buffers a whole pytest
  run so you cannot watch progress.

