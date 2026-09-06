# Pre-registered — roster wiring, per consumer

Written **before** `probe_roster_identity.py` or `price_roster_consumers.py` was
run for the first time, and committed in the same commit as their first results
so no bar can move after a number is known.

The reach numbers below are NOT pre-registered — they were measured first, on
purpose, because `probe_fill_reach.py` established that a consumer's reach has
to be known before its quality is worth measuring. They are quoted here so the
bars can be read against them.

## Reach, measured first (`probe_consumer_reach.py`, 396 staves / 20 rows)

| consumer | population it can act on | share |
|---|--:|--:|
| IDENTITY (unnamed + derived by the layout prior) | **151** | 0.381 |
| PART NAMING (staves exporting a coordinate stub) | 31 | 0.078 |
| CLEF FILL (no clef read at all) | 34 | 0.086 |
| STITCH (`_stitch_slots` refuses, ≥2 systems) | **3 rows** | — |

⚠️ **STITCH IS ALREADY SATURATED AND IS NOT A ROSTER CONSUMER.** Twelve of the
twenty rows refuse the ordinal join, but nine of those are SINGLE-SYSTEM pages
where stitching is a no-op by construction. Of the three multi-system rows where
the question genuinely arises, `_stitch_slots_by_slot` is **already available on
3 of 3** — every staff already carries a slot. So a roster cannot widen that
consumer's reach at all; what blocks `OMR_SLOT_STITCH` is the musicdiff charging
asymmetry already measured in `benchmarks/omr-staff-structure-2026-09`, not
identity. It is dropped from this task's pricing and reported as a reach
negative.

## KC-1 — does the roster ACQUIRE, through the real ladder, in production code?

`probe_roster_identity.py` reports acquisition per document: which page and
system it came off, how many positions it named, and how many of those are
correct against `works.json` `staves[]`.

- **Bar: acquisition precision ≥ 0.95** over named positions, reproducing the
  0.962 coverage / 1.000 precision that `probe_real_acquisition.py` measured
  outside the pipeline. This is a REPRODUCTION bar for the same signal in
  production plumbing, never an improvement bar.
- **If precision < 0.90**: the production path is not reading what the probe
  read — the wiring is wrong, not the idea. Report, fix or stop; ship nothing.

## KC-2 — does the roster move IDENTITY, and in which direction?

Two arms over the same freshly detected staves and the same cached label reads,
scored on the 198 truth-bearing staff records:

    OFF   `OMR_ROSTER=0` — today's answer (`SHIPPED`)
    ON    `OMR_ROSTER=1` — roster names a slot the run's own pages did not

- **Enable-if: coverage rises AND precision does not fall.** Specifically
  `named` must increase and pooled precision must be within 0.01 of OFF or
  better. A roster's whole claim is that it names staves nobody printed a name
  for on this page; buying that with a precision drop is refused.
- **If pooled precision falls by more than 0.01**: refuse, and report which
  documents did it. The expected mechanism, from `probe_real_acquisition.py`, is
  a vocabulary hole — an instrument every one of whose staves went unread drops
  out of the roster entirely and its staves come out as their neighbour.
- **If coverage does not rise**: report the negative and ship disabled. That is
  a real possible outcome here — 92.2% of gate staves already carry a name, and
  the 151-staff reach is mostly names the layout prior DEDUCED rather than
  missing names, so the roster has to be allowed to CORRECT as well as fill for
  the number to move.

⚠️ The roster never overrides a name read on a page of this run (`setdefault`).
So on the OFF-vs-ON comparison the only staves that can change are those whose
name today is `score_order`-derived or absent.

## KC-3 — what does it cost in EDITS?

Priced on the 20-row scan gate, export-only A/B over the same stored
transcriptions where possible, otherwise a full re-transcription of both arms on
the same merge base.

- ⚠️ **CONTROL ON MY OWN MERGE BASE.** `0.8444` is not a baseline for this tree
  and `results-reconciliation.json` is stale with respect to main by
  `a4918874`. The BASELINE arm is run by this tree and asserted against itself;
  no absolute figure from this harness is quoted as the gate's.
- **The scan gate's noise floor is ±6 edits.** A delta inside ±6 is NOT a
  result. Any claim of improvement needs |delta| > 6 and an attribution to named
  rows.
- **Enable-if for part naming: |delta| ≤ 6 (i.e. no measurable harm).** Part
  names are not scored by musicdiff — rewriting every `<part-name>` measures 0
  edits — so the case for enabling part naming is correctness, and the edit
  measurement's job is only to prove it costs nothing. **A non-zero delta here
  would mean the roster changed something other than a name and must be
  explained before anything ships.**
- **Enable-if for the clef consumer: delta < −6.** Tier B already priced at
  exactly 0 edits on a disjoint population, so the prior expectation is 0 and
  the pre-registered response to 0 is: **ship disabled, report the negative.**

## Standing rules carried in from the prior workstream

- A consumer that moves zero edits ships **disabled** and is reported as a
  negative.
- Only **label-sourced** identity is carried across pages. Derived identity is
  recomputed per page and never travels (0.550 carried vs 1.000 observed).
- Provenance is per-FACT (`label` / `roster` / `score_order`), because the carry
  cannot be implemented safely without it.
- No `--record`, no touching `current-accuracy.json` or the canonical benchmark
  results.
- **Every default is Sean's call.** Both flags added here (`OMR_ROSTER`,
  `OMR_ROSTER_CLEF`) ship OFF regardless of what the numbers say; the numbers
  are a proposal.
