# Phase 1 layout — a real regression baseline, and the two bugs it was hiding

**2026-08-28.** Phase 1 (staff detection → barlines → measure cells) had four
failing assertions in `test_pipeline.py` that had been failing long enough to be
described in two separate documents as "pre-existing drift" and worked around.
They were not drift. Two of them were wrong when they were written, and the
pipeline was wrong in a way that one of them was actively concealing.

## What the assertions claimed, and what the pages actually hold

Ground truth here is hand-read, not pipeline output. Sean read the Beethoven
page by eye; WTC was read by an ink probe that scores columns of near-solid ink
across each staff's full five-line span, which shares no threshold with
`measure_extractor` and so cannot agree with it by construction. Both are
recorded in `ground-truth.json`.

| | asserted | actually on the page | detector, before |
|---|---|---|---|
| WTC p.6 bars/system | 3+3+3+3+4 | **3+2+3+3+3** | 3+2+3+3+3 ✓ |
| WTC p.6 cells | 32 | **28** | 28 ✓ |
| Beethoven 5 p.10 staves | 18 | **22** | 18 ✗ |
| Beethoven 5 p.10 bars/system | 5–10 | **14, 15** | 14, 15 ✓ |

Three of the four assertions were simply wrong about the page, and the detector
had been right all along. The fourth was wrong in a much worse way.

## Bug 1 — five staves collapsing into one phantom

Beethoven 5 p.10 is a pocket score: 15.8px line spacing at 600 DPI, with wind
staves printed more lightly than the strings below them. `_candidate_staff_rows`
required each staff-line row to clear a prominence of `0.30 × (page max − min)`
— one number for the whole page, set by its densest music. The wind rows carry
1000–1350 ink against a 1013 floor and a **695** prominence requirement: not
faint in any absolute sense, only faint relative to the strings.

So most wind lines were rejected. The survivors — one line from each of five
different staves — are as evenly spaced as the staves are, and the greedy
grouper accepted them as a staff:

```
[455, 573, 742, 885, 1025]  spacing 142.5   ← five staves, read as one
[1140, 1156, 1172, 1187, 1203]  spacing 15.8
```

Five staves became one. The page reported 18 — which is exactly what the test
asserted, so the bug held a green assertion in place while every note on the
Flute, Oboe, Clarinet, Bassoon and Horn staves was invisible to everything
downstream.

**Fix.** Not a re-tuned threshold — the page's own structure. The strict pass
still runs first, and whatever it finds confidently calibrates two numbers: the
staff spacing, and how much ink a printed line carries *on this page*. A second
comb pass then re-reads the page at that spacing, admitting rows on a much
weaker gate (`0.30 ×` the reference line ink) because a row no longer has to be
judged alone — it only becomes a staff line if four more rows stand behind it at
the page's own pitch. Candidates are scored by fit and resolved greedily.

The comb is a *recovery* pass: where the strict pass already read a staff, its
rows are kept. Letting the comb win on overlap moved two cells on Boléro p.5 for
no reason. Phantoms are rejected before the merge, since a phantom spans the
staves it stands in for and would otherwise block their recovery.

The pool gate was set from a plateau, not a single point. Every value in
**0.20–0.35** gives identical, correct counts on all seven corpus pages; below
0.20 false staves appear (Beethoven 5 p.2 gains a 23rd, La Mer a 21st). 0.30
sits inside the plateau, toward the strict end.

## Bug 2 — music deleted after a false barline

WTC p.6 system 2 has two bars. The detector finds a third barline at x=4476,
where two stems align across the staves — no ink crosses the gap between the
staves there, and the independent probe sees nothing.

That false barline then became the *last* one, so `_measure_x_boundaries` read
the remaining 340px as the blank strip that follows a final barline, and
**discarded it**. The 340px held real notes. The measure count came out right
(2 — the correct answer, reached for the wrong reason), so nothing downstream
could detect the loss.

**Fix.** Absorb the tail into the last measure rather than dropping it. When the
blank-strip assumption holds the cost is a sliver of white on one cell; when it
does not, the music survives. `test_pipeline.py` now asserts the invariant
directly: every system's last cell must reach its staff's right edge.

## Corpus effect

`python3 -m tools.omr.training.phase1_layout_eval` over 12 pages of 8 scores;
`snapshot-before.json` / `snapshot-after.json`.

| page | staves before → after | systems before → after |
|---|---|---|
| beet5-p10 | 18 → **22** (truth 22) | [7, 11] → [1, 10, 11] |
| beet5-p2 | 16 → **22** | [4, 1, 4, 7] → [11, 10, 1] |
| beet5-p8 | 16 → **20** | [1, 1, 1, 2, 11] → **[9, 11]** |
| wtc p5/p8, boléro p5/p31, la mer p25, mahler p11, kirchhoff p10 | unchanged | unchanged |

Every page that already worked is untouched; only the three Beethoven pages
move, all toward the truth. Beethoven 5 p.8 also stops fragmenting into five
systems.

## What this does NOT fix

**Beethoven 5 p.10 still groups as [1, 10, 11] rather than [11, 11].** The
recovered staves are real and correctly read, but the topmost is split into a
system of its own. The cause is measured and is not in staff detection:
`_staff_x_extent` returns the longest **contiguous** ink run on the middle line,
and on these lightly printed staves that is a fragment. Staff 0 reads
x=353..1379 while staff 1 reads x=1715..2633 — no overlap at all, so
`_assign_systems` breaks between them on its `x_overlap_frac <= 0.5` rule.

Measured on staff 0's middle line: it spans 276..2633, the full staff, but in
**28 runs**, 13 of whose gaps exceed one staff space; the largest is 175px = 11
staff spaces.

That matters for whoever fixes it. Branch `claude/clef-recognition-improvement-ab75f6`
is rewriting exactly this function (commit `46ca8c6`) with a **one-staff-space**
bridge. Simulated here against these staves, a one-space bridge does not close
gaps of eleven, and the split remains. Faint 19th-century prints need a far more
generous bridge than dashed modern ones.

Not fixed here deliberately: that branch is actively rewriting the function, and
a second, conflicting rewrite would cost more than it buys. The measurement
above is the input for it. The `test_system_grouping` case is marked
`xfail(strict=True)`, so when that fix lands the test fails as an *unexpected
pass* and asks to be updated rather than sitting green and forgotten.
