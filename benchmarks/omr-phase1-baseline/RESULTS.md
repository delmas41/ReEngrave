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

---

# Staff-line removal — a no-op on most orchestral scores

**2026-08-28, same session.** `staff_line_removal` preserved a pixel if ink sat
a fixed **4px above and below** it. On any line thicker than about 8px that
test is satisfied by the line itself, so the line preserved itself and nothing
was removed. Measured share of staff-line ink actually cleared:

| page | line thickness (canonical) | before | after |
|---|---|---|---|
| WTC p.5 | 6px (0.06 spaces) | 91.3% | 88.2% |
| Boléro p.31 | 9px (0.09) | 72.5% | **88.5%** |
| Mahler 5 p.11 | 17px (0.23) | **0.9%** | **89.7%** |
| Beethoven 5 p.10 | 25px (0.25) | **0.0%** | **49.8%** |

Every consumer of `image_no_staff` — stem and beam detection, template
matching, the labeling UI's sparse-cell ranking, and the key-signature reader
being built on `claude/key-signature-recognition-57ec0a` — was working on an
image that still had its staff lines. That branch's note that "the header
arrives as one connected mass" is this bug seen from the other end.

## What replaced it

Three changes, each one measured rather than reasoned:

1. **Decide by the vertical run, not a fixed neighbourhood.** At each staff
   line, walk the ink run through every column. A run no taller than the line
   is printed IS the line; a taller one is a notehead, stem, beam or barline
   and is left alone. The line's thickness is measured from the cell, because
   across the corpus it ranges from 0.06 to 0.31 staff spaces — no pixel
   constant can serve both ends of that.

2. **Drop the morphological opening.** It required a candidate pixel to belong
   to a horizontal run of 30% of cell width, which a broken line fails: only
   37.7% of Beethoven 5 p.10's line-row ink survived it, and 73.0% of Mahler's.
   Removing it improved every measure at once — more line ink cleared, a
   smaller largest connected component, and **fewer** stray specks, since a
   partly erased line leaves its own fragments behind (Mahler specks 78 → 1.5,
   WTC 20 → 0.4).

3. **Follow the line where it actually is.** Phase 1 reports one straight y per
   line while the printed line drifts and residual skew tilts it, so across a
   wide cell the ink wanders off its nominal row. Anchoring each column's run
   to the nearest ink within 0.25 staff spaces raised Beethoven 5 p.10 from
   36.9% to 49.8% and Boléro's mean from 75.6% to 85.2%.

A cut cap of 0.45 staff spaces stops anything as thick as a beam from being
erased. Honestly reported: it changes almost nothing measurable (Mahler's beam
count is 239 with or without it, and it does not bind at all on WTC or Boléro).
It is insurance against a case the corpus does not currently contain.

## Downstream, and what is not established

`line_detection` over 25 cells per page, before → after:

| page | stems | beams |
|---|---|---|
| Mahler 5 p.11 | 178 → **145** | 249 → 233 |
| WTC p.5 | 492 → 498 | 566 → 551 |
| Boléro p.31 | 262 → 255 | 308 → 313 |

WTC and Boléro barely move. **Mahler's stem count falls 19%, and this work does
not establish whether that is right.** Before the change, stem detection on that
page was running on an image whose staff lines were entirely intact, so some of
those 178 were plausibly line artefacts — but there is no stem ground truth in
the repo to say so, and the possibility that real stems were lost is not
excluded. Visual inspection of the affected cells shows stems, beams, noteheads,
clef, key signature and text surviving intact; that is evidence, not proof.
Establishing stem/beam ground truth on a dense page is the natural next step,
and it is a prerequisite for trusting Phase 4f the way Phase 1 can now be
trusted.

Beethoven 5 p.10 remains the weakest page at 49.8%. The residue there is not a
threshold failure: on that print the line ink is genuinely fused with the
symbols above and below it, so the runs through it are tall and are preserved
on purpose. Over-erasing them would shred the glyphs.

Tests: 17 new units on synthetic cells (`test_staff_line_removal.py`) covering
each printed thickness from 2 to 30px, a wandering line, a crossing stem, a
notehead on a line, and a beam lying along one.

---

# One-line percussion staves — a staff the grouper could not see

**2026-08-28.** `_group_into_staves` accepts only five-peak windows, so a
percussion part printed as a single rule produced **no `Staff` at all**. The
cost is not the missing percussion part. It is that every staff below it
carried a `staff_index` one lower than its true slot, and slot identity is what
feeds instrument, transposition and expected clef — so one missing rule makes
the lower half of an orchestral system read as the wrong instruments.

La Mer p.25 (`evidence/lamer-p25-margin-21-staves.png`) is the case in the
corpus. Counted off the margin: 21 parts in one system, the twelfth being
**Cymbales** on a single line (`evidence/lamer-p25-cymbales-staff.png`). The
detector reported 20, so both harp staves, four divided violin staves, violas,
celli and basses — nine parts — were each one slot too high.

## What identifies a one-line staff

Not anything about the row itself. A percussion rule is a long inked row
between the page's staves, and so is the single surviving line of a five-line
staff printed too lightly for the peak gates. **On Beethoven 5 at 300 DPI that
second case is the common one**: the first version of this rule fired on 4 of
10 sampled Beethoven pages, a score with no one-line parts at all, and the
firings were a clarinet staff (`evidence/beet5-p8-clarinet-false-positive.png`)
and a first-violin staff (`evidence/mahler-p26-first-violin-false-positive.png`).

Four conditions, each answering a different way of being wrong:

| condition | what it refuses |
|---|---|
| between the page's first and last staff line | page borders, title and footer rules |
| ≥ 4 staff spaces clear of any other staff-line row | two lines of one staff, read as two percussion parts |
| run ≥ half the page's median staff width, overlapping their x-window | hairpins, bracket edges, fragments of text |
| **no line-length run one or two spaces above or below** | the survivor of a lightly printed five-line staff |

The fourth is the one that carries the rule, and it works by asking the *page*
rather than the peak list: whether or not the row pass saw the other four
lines, they are printed, and printed lines are long.

## Measured

47 pages sampled across five scores (every sixth page, 300 DPI):

| | before the neighbour veto | after |
|---|---|---|
| pages firing | 13 | **9** |
| Beethoven 5 (no one-line parts) | 4 of 10 pages | **0** |
| WTC, Boléro | 0 | 0 |

All 14 remaining firings are on La Mer and Mahler 5. Twelve were rendered and
read: Cymb., Trg., Becken, Gr. Tr., Kl. Tr. — every one a labelled percussion
part (`evidence/one-line-staves-confirmed.png`). No false positive survived
inspection.

Corpus effect (`phase1_layout_eval`, 12 pages): **one page moves** — La Mer
p.25, 20 → 21 staves, matching the hand count. The other eleven are unchanged.

## What this does NOT do

A one-line staff is detected, given the page's spacing so that everything
sizing a window in staff spaces still works, and **skipped by barline detection
and cell extraction**. Its content is not read. The cell pipeline canonicalises
by a staff's five-line span, which a single rule does not have; and the barline
vote is a fraction of the staves in a system, so a staff two spaces tall would
answer "barline" for any stem crossing it and move the denominator for every
real staff. Reading percussion is separate work. The slots are the fix.
