# The written-range veto, supplied from a page-read roster

**Measured 2026-09-05/06. Verdict: the reach is REAL, the mechanism works
exactly as designed, and it does not pay. `OMR_ROSTER_RANGE_VETO` ships
default-off.**

Branch `claude/range-veto-2026-09-05`: `06064db6` pre-registration → `2bac86a7`
mechanism → `f52f0b69` price. Merged dormant.

*(Written up by the coordinating session from the agent's report and
`f52f0b69`'s commit message — the agent's harness refused it a `.md` file. The
numbers below are its measurements, not a restatement of anything else.)*

---

## What this was

`transcribe._dedupe_cross_staff_detections` arbitrates a notehead detected in
two staves' padded cells, in three tiers: **ledger ladder**, then the
**instrument's written range**, then **distance** as a tie-break.

⚠️ **Tier 2 had never fired on a scan.** `_staff_written_ranges(page, dossier)`
returns `{}` when `dossier is None`, and the scan gate runs dossier-free by
protocol — a dossier is generated from the same MusicXML the gate scores
against. So every contested glyph on the gate resolved by ladder or by raw
distance.

`OMR_ROSTER` shipped default-ON on 2026-09-05 and supplies exactly what that
tier was starved of: **per-staff instrument identity, read from the page, with
no dossier.** This measured whether that unblocks it.

## Reach — measured before quality, and it is real

| funnel, 20-row scan gate | n |
|---|--:|
| contested pairs, all categories | 4,521 |
| … noteheads — the only category this tier speaks on | 816 |
| … identity present on both staves | 768 |
| … where the two written ranges **separate** the readings | **474** |
| … **and the veto disagrees with what distance already did** | **52** |

⚠️ **The number that matters is 52, not 474.** The other 422 merely confirm the
answer distance had already reached. 36 survive the conservative `label`-only
arm; they spread over 11 of 20 rows.

⚠️ **The circulating "4,256 contested duplicates" counts every category.**
Noteheads are 816 of 4,521 — quote the right denominator.

⚠️ **The family-union negative does NOT cover this, and that distinction should
be propagated.** `benchmarks/omr-structural-parts-2026-09/` measured a
*family*-level range substitute as vacuous: a family's range is the union of its
members', so percussion spans 0–127 and only **5 pitches of 9,219** fell
outside. Per-instrument ranges are tight — Timpani 36–60, Piccolo 74–108 — and
find **474**. Two different rules; the old null is not evidence about this one.

**So this is the first identity consumer that did NOT die on reach.** Clef FILL
(34 of 396 staves, disjoint from where identity applies), the clef override
(measured zero), and `_stitch_slots` (12 rows refuse the ordinal join, but 9 are
single-system pages and the slot join is already available on the other 3) each
failed because their population was empty or already served. This one had a
population and still lost.

## Price — control and both arms on the same merge base

| arm | OMR-NED | edits | Δ | swaps |
|---|--:|--:|--:|--:|
| control (flag off) | 0.8441 | 74,962 | — | 0 |
| `label` identity only | 0.8443 | 74,970 | **+8** | 36 |
| `all` identity sources | 0.8446 | 74,986 | **+24** | 52 |

Both arms are the wrong sign against the gate's **≥ ±6 edit** noise floor. Only
5 of 20 rows move at all.

⚠️ **`0.8444` was deliberately not used as the baseline** — 28 files of
`tools/omr` separate its stamping commit from `main`, so the control is a fresh
run on this run's own merge base (`53fd9366`).

**Provenance caution was measured, not assumed, and it was right:** admitting
`score_order`-derived identity is **three times worse** (+24 against +8) and its
`wrong note` gain is a quarter the size (−8 against −32). A `score_order` name
is a hypothesis about where a staff *sits*, and a wrong identity here **deletes
a real note**. Corroborating case: the identity layer names Beethoven's
*Contrabass* staff "Bass voice" (40–64 against 28–67), which would rule real
contrabass notes impossible.

⚠️ **The decisive number is the READING, not the metric.** `wrong note` −32
against `entire measure insert/delete` +51 is the documented amplification, so
note recall was checked directly: **exact matched notes 3,153 → 3,155, +2 from
36 swaps.** The veto is right about as often as it is wrong. A metric-only read
of this arm would have been ambiguous; the reading is not.

## Why it fails, and it is an existing refusal's reason

**The veto adjudicates between two SCAN-RESOLVED PITCHES, and a scan's resolved
pitch is the dominant error term** — `wrong note` is 29.6% of this pool.
`OMR_ARC_RECLASS` was refused for scans on exactly this ground.

> **A rule whose input is a scan's resolved pitch cannot be better than that
> pitch is.**

That is worth carrying as a pattern rather than as one result. It also says when
this re-prices: the plumbing is merged and default-off, so **if scan pitch
resolution improves, this arm re-runs for free.**

## Two variants, one shipped and one refuted

- **"Apply only where the ladder already abstained"** is what shipped
  (`rank == 0` only). 5 of the 52 are ladder-decided and deliberately untouched
  — the ladder is the stronger tier and keeps precedence.
- **Requiring both clefs to have been READ** (not positionally defaulted) was
  refuted for the cost of a join: it removes 2 of the 52 and **0 of the label
  arm's 36**. A no-op.
- **A semitone tolerance was NOT tested**, deliberately: it converts a veto on
  the *impossible* into a preference on the *unlikely*, which is a different
  tier with a different failure mode.

⚠️ **That clef join was WRONG the first time and said "0 of 52"** — a doubled
`.` in a derived key emptied it, and **an empty intersection reads exactly like
a dramatic finding**. `compare_arms.py` now raises on an empty join. The
original assertion checked input *length* but not *overlap*; length alone does
not prove two sets were ever compared.

## Controls

- The instrumented control is **byte-identical to a plain default run** on the
  two rows that move most, and the veto arm differs on both — so the control is
  the shipped default and the comparison is not vacuous.
- The engraved 11-work pool is unmoved **by construction**: the flag is off, and
  with a dossier present tier 2 already fires in-loop at rank 1, so those pairs
  are never parked for this path.
- Full `tools/omr` suite green: 2,291 passed.
- The `_optional_pass_failure` anti-drift counter caught a third pass as
  designed; it was raised 2 → 3 **with its semantics kept, not exempted**.
