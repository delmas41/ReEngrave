# Staff grouping has no phase anchor, and on Mahler it picks the wrong one

## What this explains

Mahler's numbers on this benchmark are far worse than the other two works
(recall 0.136 against Beethoven's 0.691) and none of the fixes this session
moved them at all. This is why.

Truth for the excerpt is 22 notes, all on the "Trompeten in B." staff. The
pipeline reports 36 noteheads spread over staves 10, 14 and 15 — and *none* of
them lie inside the band of the staff they were assigned to:

```
staff 14: band 3262..3428   its noteheads sit at y 3431..3530   (BELOW the band)
staff 15: band 3663..3828   its noteheads sit at y 3507..3582   (ABOVE the band)
```

The notes are real and correctly detected. The **staff bands are shifted**, so
every note lands in the padding of two neighbours and is claimed by both.

## The cause: uniform ladders with no visible staff boundary

Rendering the region and marking the detected staff-line rows shows two trumpet
staves — an "F Trumpet" on bass clef and "Trompeten in B." on treble — set so
tightly that **the gap between the two staves equals the line spacing inside
them**. Lines run 3179, 3220, 3262, 3302, 3344, 3385, 3428, 3469, 3509, 3550 at
a constant ~41 px. There is no gap marking where one staff stops.

The true grouping is `{3179 3220 3262 3302 3344}` and `{3385 3428 3469 3509
3550}`. The grouper produced `{3056 … 3220}` and `{3262 … 3428}` — correct in
*shape*, wrong in **phase**, off by one line, which shifts every band by 41 px
and orphans the last three lines.

`_group_into_staves` slides a 5-peak window and accepts the first one whose
gaps are uniform, then skips 5. On a uniform ladder every phase is equally
uniform, so the phase is decided by wherever the ladder happens to start — an
arbitrary choice, and here the wrong one.

This is not rare on this page. Splitting the 169 detected line-rows into maximal
uniform ladders:

| lines | span | lines mod 5 |
|---:|---|---:|
| 13 | 1537..2031 | 3 |
| 17 | 2040..2699 | 2 |
| 13 | 3056..3550 | 3 |
| 41 | 3663..5312 | 1 |
| 29 | 5842..6996 | 4 |

**Not one of the long ladders is a multiple of five.** 14 of 169 peaks end up
ungrouped. Every one of those ladders spans several staves with no boundary a
gap test can find, and each carries a phase the grouper is guessing at.

And it tracks the benchmark almost exactly:

| work | ambiguous ladders | ungrouped rows | recall |
|---|---:|---:|---:|
| beethoven-sym5-mvt1 | **0** | **0** | **0.691** |
| brahms-sym1-mvt1 | 3 | 5 | 0.605 |
| mahler-sym5-mvt1 | 5 | 14 | 0.136 |

Beethoven's page separates every staff with a real gap, so its phase is never in
doubt — and it is the work this benchmark reads well. That correlation is the
strongest argument that this is the dominant remaining error on dense pages,
rather than anything in recognition.

## Two things I had wrong earlier, corrected

* **"Mahler page 0 genuinely has 31 staves, so staff detection was never
  failing."** The *count* is plausible but the *bands* are misaligned by one
  line in at least one ladder, which is worse than a miscount: it puts real
  notes in the wrong staff's padding.
* **"A staff line at ~3591 was missed."** There is no line there — the longest
  continuous ink run at y=3591 is 40 px, against 4137 px for a real staff line
  at y=3550. That ink is noteheads and a hairpin. Inserting a synthetic line
  there *does* make the grouper produce the right staves, which is what made the
  theory look right; it works by accident, by shifting the phase.

## What a fix needs

A **phase anchor** — some feature that belongs to exactly one staff and can say
where it starts. The obvious candidate is the clef: it is printed once per staff
at a known vertical position within it, and `clef_geometry` already measures
which line a clef is centred on. Anchoring each ladder's phase on the clefs
found along it would replace a guess with a measurement.

Do not fix this by tightening the peak detector or by inventing lines. The lines
are all correctly detected; only their assignment into groups of five is wrong.

Reproduce with:

```bash
python3 benchmarks/omr-orchestral-e2e/probe_staff_ladders.py
```
