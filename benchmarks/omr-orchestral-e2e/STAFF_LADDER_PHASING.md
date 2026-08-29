# Staff "phase" ambiguity was a fixture artifact — corrected

**This document previously argued that `_group_into_staves` has no phase anchor
and picks the wrong one on Mahler. That diagnosis was wrong, and the commit
carrying it (`f28f096`) overstated a pipeline bug that is really a bug in this
benchmark.** The evidence and the correction are both below, because the way it
went wrong is worth keeping.

## What was observed

On the Mahler excerpt, all 22 truth notes were correctly detected but landed
inside *no* staff's band:

```
staff 14: band 3262..3428   its noteheads at y 3431..3530   (below the band)
staff 15: band 3663..3828   its noteheads at y 3507..3582   (above the band)
```

The page presented long uniform ladders of evenly spaced lines — runs of 13, 17,
41 and 29 — with no gap anywhere marking where one staff stopped and the next
began. `_group_into_staves` slides a 5-peak window and takes the first uniform
fit, so on such a ladder its phase is arbitrary. That much is true.

## Why the conclusion was wrong

The ladders were not a property of orchestral engraving. They were a property of
**this benchmark rendering a 38-part score onto A4**. LilyPond, out of room, set
the staves about one staff-space apart — so the bottom line of one staff and the
top line of the next are indistinguishable from two lines within a staff. Real
engraving never does this; it uses a bigger sheet.

Re-rendering the identical excerpt on larger paper:

| paper | staves found | ambiguous ladders | inter-staff gap |
|---|---:|---:|---|
| a4 | 31 / 38 | 5 | **1.0 spaces** |
| **a3** | **38 / 38** | **0** | 1.8 spaces |
| a2 | 38 / 38 | 0 | 4.3 spaces |

On A3 the pipeline finds every staff and there is no ambiguity left to resolve.
No phase anchor was needed; the input was malformed.

`excerpt()` in `orchestral_eval.py` now scales the sheet with the part count —
a4 up to 20 parts, a3 to 40, a2 beyond.

## Effect on the benchmark

| work | parts | recall | precision | duration |
|---|---|---|---|---|
| beethoven-sym5-mvt1 | 18/18 → 18/18 | 0.691 | 0.700 | 0.857 |
| brahms-sym1-mvt1 | 21/21 → 21/21 | 0.605 → **0.691** | 0.510 → **0.660** | 0.485 → 0.487 |
| mahler-sym5-mvt1 | 31/38 → **38/38** | 0.136 → **0.250** | 0.083 → **0.207** | 0.000 → **0.167** |

Beethoven is untouched — 18 parts still render to A4. Mahler's part count now
matches its dossier, so the slot-level checks that had been abstaining all along
finally run, and immediately flag two clef mismatches.

## What to take from it

* **A benchmark can manufacture failure modes that do not exist.** Every number
  measured on the A4 Mahler page was real, reproducible, and about nothing.
* The tell was there to be read earlier: barline groups spanning a single staff
  came out 170 px tall with **3 px** between consecutive groups. Staves three
  pixels apart should have prompted "is this page even legible?" rather than a
  hunt for a grouping bug.
* `probe_staff_ladders.py` is kept. It is still the right instrument — it
  measures whether a page's staves are separable at all, which is a genuine
  precondition, and it is what showed the fixture was at fault once pointed at
  the same excerpt on different paper.

## What is still open

`_group_into_staves` genuinely has no phase anchor. On a real page whose staves
are properly separated that never matters, and no such page has been observed to
trip it. It stays a latent weakness, not a live bug, and should not be
"fixed" without a real page that fails.
