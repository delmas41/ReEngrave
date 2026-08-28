# System grouping by connectivity — 43% → 86%

**Date:** 2026-08-28
**Verdict:** adopted. `tools/omr/system_grouping.py`, wired into
`staff_detector.detect_staves` with the gap heuristic kept as fallback.
**Reproduce:** `python3 benchmarks/omr-system-grouping-2026-08/eval_grouping.py`

---

## Why

Slots (contextual-analysis item #1) are assigned per system, so correct systems
are a prerequisite. `_assign_systems` decided them from the *size* of the gap
between staves, and its own comment names the problem: its MAD rule splits at
"a clearly-bigger-than-normal gap between bracketed sub-systems (e.g. winds vs
brass vs strings)". Those blocks are inside one system.

## The signal

**A system break is a gap that no vertical ink crosses.** Barlines are engraved
through the whole system and the bracket spans it end to end; nothing crosses
between two systems. `measure_extractor._intersystem_connectivity` already
relies on this one level downstream, to tell real barlines from stem columns.

Per adjacent staff pair, count the columns whose ink covers >= 80% of the gap
band. Counts are trimodal:

| bridging | meaning |
|---|---|
| `0` | system break |
| `~4-25` | bracket-GROUP boundary — only the bracket and some barlines cross |
| `~35-95` | inside a bracket group |

The middle tier is a bonus: it recovers the instrument-family grouping as
`Staff.group_index`. Visually verified on Beethoven 9 p70 — two systems, each
grouped **4 woodwinds | 2 horns | 5 strings**. The old detector was finding the
right *groups* and calling them systems.

## Results

14 pages (Beethoven 9 imslp-516488 at 300 dpi; Beethoven 5 p10 at 300 and 600).

| | gap heuristic | connectivity |
|---|--:|--:|
| system count correct | **6/14 (43%)** | **12/14 (86%)** |
| spurious single-staff "systems" | **19** | **0** |
| Beethoven 5 p10 stable across 300/600 dpi | yes | yes |

The two remaining failures (p25, p60) are **merges** — a real break that
something crosses. The gap heuristic's failures are the opposite: it shreds one
system into as many as 12, half of them single staves.

## Ground truth — count BRACKETS, not visual blocks

Ground truth is the number of left brackets, read off a crop of the left margin.

Two earlier attempts at ground truth were both wrong, and both flattered a
different answer:

1. **A ground-truth-free proxy** — "true instrumentation is constant, so a
   correct detector yields a tight staves-per-system distribution." It rewards
   merging every page into one system, and duly reported success.
2. **Counting systems off a whole-page thumbnail.** At that scale the
   brass-to-strings gap looks exactly like a system break, so pages 30-50 —
   single 13-staff systems — were all labelled 2, and the evaluation came back
   43% vs 50%, i.e. "no real gain". Rendering the left margin alone settles it:
   one continuous bracket, one system.

Both mistakes were caught by rendering the page and looking at it properly. The
proxy metric was the more dangerous one because it produced a *confident* number.

## Three traps, each of which cost a measurement

1. **`Staff.x_start` is unusable as a scan window.** It is the longest unbroken
   ink run on the middle staff line, so on a degraded scan it lands anywhere:
   Beethoven 9 p60 staff 3 reports `x_start=885, x_end=1826` against ~275/~2485
   for its neighbours. Intersecting the two staves' extents gave a window that
   missed the bracket and reported a false break. Use the page median.

2. **The window must reach PAST the staff extent.** The bracket is engraved left
   of where the staff lines start and the closing barline right of where they
   end. On Beethoven 5 p10 at 600 dpi the only columns crossing two
   bracket-group gaps sat at x=334-353 and x=2630+, against a median staff
   extent of 355..2629 — clipped to the staff, the system split.

3. **Coverage is resolution-sensitive without gap closing.** A bracket that is
   solid at 300 dpi resolves into a dotted line at 600, and then no column
   clears 80%. Beethoven 5 p10 grouped correctly as 2 systems at 300 dpi and
   wrongly as 4 at 600. Vertical gaps shorter than 0.6 staff spacings are closed
   first, so the tolerance scales with resolution instead of being a pixel
   constant.

Also measured and rejected: **gating a break on gap size** (a guard against a
scan defect splitting a system). On Beethoven 9 p25 the true break between two
12-staff systems has a 68 px gap while intra-system gaps reach 99 px, so the
guard suppressed a real break. Gap size is the assumption this module exists to
reject; the connectivity signal stands alone.

And rejected: **measuring the band through both staves** rather than the gap
alone, on the theory that a barline runs through a staff while a stem does not.
It over-merged badly (3/12 on the then-current labels) because it raises the
count at real breaks too.

## Known limitation feeding item #1

`_group_into_staves` accepts only five-peak evenly-spaced windows, so a
**one-line percussion staff is invisible** — no `Staff` is produced, and every
staff below it carries a `staff_index` one lower than its true slot. Proof and
consequence:
`tools/omr/tests/test_system_grouping.py::test_detect_staves_misses_a_single_line_percussion_staff`.
Not fixed: relaxing the 5-peak rule risks staff detection, which has no
regression baseline.
