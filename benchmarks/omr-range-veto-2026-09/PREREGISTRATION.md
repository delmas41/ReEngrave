# Range veto from roster identity — pre-registration

**Written and committed BEFORE any arm was scored.** Merge base `53fd9366`
("OMR_ROSTER defaults ON"). Findings land beside this file.

## The question

`transcribe._dedupe_cross_staff_detections` arbitrates a glyph detected in two
staves' padded cells with three tiers: **ledger ladder**, then the **instrument's
written range**, then **distance**. Tier 2 reads `_staff_written_ranges(page,
dossier)`, which returns `{}` outright when `dossier is None` — and the scan gate
runs dossier-free by protocol. So on scans tier 2 has never fired.

`OMR_ROSTER` (shipped `53fd9366`, default-ON) supplies per-staff instrument
identity read from the page with no dossier. **Can it feed the starved tier, and
what is that worth in edits?**

## ⚠️ The prior negative that does NOT cover this

`benchmarks/omr-structural-parts-2026-09/` measured a **family**-level range
substitute and found it vacuous: a family's range is the UNION of its members', so
percussion spans 0–127 and only 5 detected pitches of 9,219 fell outside their
family union.

**That does not carry over.** Per-INSTRUMENT ranges in `instruments.py` are far
tighter than per-family unions — all 38 instruments carry a `written_range`, and
they run e.g. Timpani (36, 60), Piccolo (74, 108), Violin (55, 100), Bassoon
(34, 72). A union over "brass" or "percussion" destroys exactly the discrimination
this tier needs. The old negative is about a coarser object; it neither predicts
nor forbids this result.

But its **lesson** is adopted in full: **measure REACH before quality.**

## Ordering problem, stated up front

`_dedupe_cross_staff_detections` runs per page (`transcribe.py` ~line 4484), while
`apply_contextual_analysis` — the producer of roster identity — runs after every
page is built (~line 4760). **Identity does not exist where the veto lives.** Any
mechanism must either hoist acquisition or defer arbitration. This is a cost of
the fix, and it is only worth paying if reach is non-trivial.

## Step 1 — reach probe (no pricing)

`OMR_CONTEST_DUMP=1` records every contested pair onto the page dict: both staves,
both pitches, the category, and the tier that actually decided it. It is
**verdict-neutral** — it only appends to a list, so a run with it on removes
exactly the same detections as a run with it off. That makes the same run serve as
my control arm.

Reach is then, over the 20-row scan gate, the count of contests that are

1. **noteheads** (the range tier only ever speaks on `category == "notehead"`), AND
2. carry a **resolvable pitch on both sides**, AND
3. have a **roster identity** on at least one contesting staff, AND
4. where that identity's `written_range` **separates the two readings** — one
   outside its part's range and the other inside its own, which is the existing
   "veto on the IMPOSSIBLE" condition, not a preference.

Broken out **by row** and **by identity provenance** (`label` / `roster` /
`score_order`).

## Step 2 — pre-registered decision rule

| reach (pairs the veto would speak on, 20 rows) | what happens |
|---|--:|
| **0** | Report a **reach negative** and stop. Build nothing. |
| **1–24** | Report as thin. Build only if concentrated in ≥3 rows; otherwise stop. |
| **≥25** | Build the mechanism, price it. |

⚠️ **A reach negative is a respectable result and will be reported as one.** Three
identity consumers priced today have already landed there.

## Step 3 — pricing, if reached

- **Noise floor on the 20-row gate is ≥ ±6 edits.** The byte-determinism claimed
  in this gate's older findings held on the 5-row era and does **not** hold at 20
  rows. Anything under ±6 edits is not evidence.
- **`0.8444` is NOT a baseline for this tree** — 28 files of `tools/omr` separate
  its stamping commit from main. I run **my own control arm on my merge base**
  (the `.contest` run above) and difference against that only.
- Enables the flag: pooled edits improve by **more than 6** on the 20-row gate,
  with **no row regressing by more than 6**, and the engraved 11-work pool
  unmoved or explicitly reported.
- Leaves it off: anything smaller, or any row losing real notes.

## Design constraints held

- **A veto on the IMPOSSIBLE, never on the unlikely.** Widening it into a
  preference is out of scope. The Beethoven bassoon case keeps `A♭1` over a `C4`
  precisely because distance beat evidence there.
- **Written pitch, not concert** — `written_range` follows the project's written
  convention; a concert comparison would false-veto every transposing staff.
- **Provenance is measured, not assumed.** `score_order` identity is ~1 staff in
  10 wrong and a wrong identity here DELETES A REAL NOTE. Both a
  `label`+`roster`-only arm and an all-provenance arm are reported if the
  mechanism is built.
- Ships behind a flag, **default-off**. A default flip is Sean's call with a
  number attached.

## Already observed, and it sharpens constraint 3

On the smoke row `beethoven-sym5-mvt1-984073-p1`, identity named 12/12 staves —
and named the **Contrabass staff "Bass voice"** (a singer). Ranges: Bass voice
(40, 64) against Contrabass (28, 67). A veto trusting that identity would rule
every real contrabass note below MIDI 40 impossible and delete it. This is the
false-veto mechanism the provenance arm exists to measure.
