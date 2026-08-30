# Majority-steered re-segmentation — measured 2026-08-29

**Verdict: the feature ships INERT on every page in this repository, and the
probe written to measure it found a crash instead.** Both halves of that
sentence are the result; neither is the one that was expected.

```bash
python3 benchmarks/omr-majority-steering-2026-08/probe_majority_steering.py
```

## What was built

`resegment_fused_measures` splits a measure cell back into real bars when the
cell is a >2x-median-width outlier and a genuine internal barline can be found
inside it. Cells that are fused but *not* wide enough to be flagged are left
alone — deliberately, since without a target count there is no way to tell a
wide bar from a fused pair.

`claude/omr-dossier-verification-layer-eaf6d0` (July, unmerged) added a target:
`expected_bars_by_system`, which relaxes the width gate for a system the
conservative pass left SHORT, while still requiring barline ink and never
splitting past the count. That logic is what was cherry-picked here.

**Its data source was not.** The branch fed the parameter from a hand-typed
dossier's `page_layout(p).measures_per_system`. On `main` a dossier is
*generated from MusicXML*, and MusicXML page and system breaks describe the
engraver's own edition — the right bar counts for the wrong page. Feeding that
in would be worse than feeding nothing.

The count now comes from the page itself (`majority_bars_by_system`): every
staff in a system is printed against the same barlines, so when one staff reads
fewer bars than the rest, the majority is the count. This is the same reasoning
`transcribe._flag_measure_count_inconsistency` already uses to FLAG the
disagreement after detection; computing it off the cells lets Phase 1 ACT on it
instead, and it needs nothing but cell counts, so it runs before a single symbol
has been detected. It abstains without a strict majority, and on single-staff
systems.

## What it does on real pages: nothing

Twelve real scan pages, ten of which carry staves:

| | |
|---|---:|
| systems examined | 27 |
| systems where a staff disagrees with the majority | **0** |
| systems steering changed | **0** |
| bars added | **0** |

Every staff of every system on Bach WTC, Beethoven 5, Boléro, La Mer, Mahler 5
and Kirchhoff agrees with its neighbours about how many bars the system has. The
conservative pass has already done the work; there is no shortfall left to steer.

This is the same finding the July measure-count check reached from the other
direction — *no in-repo PDF triggers it naturally* — and it is a fact about the
corpus, not about the feature. The pages here are single-column, cleanly barred
scans. A fused measure that the conservative gate misses needs a cell between
1.5x and 2x the median width, on a staff whose siblings read one bar more, and
this corpus contains no such case.

**So this ships unexercised.** It is guarded — no barline ink means no split
whatever the count says, and it never overshoots — and it is byte-identical to
the previous behaviour on all 27 systems. But nothing here demonstrates that it
helps, and this file should not be read as if it did. The honest status is: the
mechanism is in place and tested at unit level, waiting on a page that needs it.

Note also that the orchestral end-to-end benchmark cannot exercise it either,
and for a structural reason: its pages are rendered by LilyPond from MusicXML,
so their bar counts are correct by construction (8/8, 7/7, 8/8). Confirming
inertness there is worth something; confirming usefulness is impossible.

## The one hazard, and why it is covered

Steering from the page's own majority runs BEFORE detection, so it cannot use
the note-content test that separates a fused pair of real bars from a condensed
multi-measure rest — the dominant orchestral false positive, and the reason
`_flag_measure_count_inconsistency` down-weights that case to `low`. A resting
staff genuinely reads fewer bars than its neighbours and is not wrong.

What protects it is that a multi-measure rest carries no internal barline, and
steering never splits without barline ink. Pinned end to end in
`TestMajoritySteeringIsSafeOnRestingStaves`.

## What the probe actually found: La Mer p.25 could not be transcribed at all

Writing the probe surfaced a **pre-existing crash on `main`**, unrelated to
steering — it fires in the conservative path.

`detect_barlines` and `extract_measures` both exclude one-line percussion
staves, because a staff two spaces tall votes "barline" for every stem that
crosses it. `resegment_fused_measures` was never given the same guard. There the
omission is not noise but a hard error: `_detect_barlines_in_window` sizes its
morphological kernel from the staff span, and La Mer p.25's Cymbales staff has a
span of **0**, so OpenCV is asked for a 1x0 kernel and raises.

```
cv2.error: (-215:Assertion failed) anchor.inside(Rect(0, 0, ksize.width, ksize.height))
```

La Mer p.25 is **the page the one-line-staff support was validated on**. Its
regression test covers staff detection, which is where the work was done, and
stops short of transcription — so a page that had been specifically fixed in
August could not be read end to end. With the guard: 20 staves, 60 measures,
2097 detections.

Two lessons worth keeping:

1. **A new staff kind has to be walked through every consumer, not just the ones
   it was written for.** Two of three call sites got the filter; the third was
   the one that crashes rather than degrades.
2. **A probe written to measure feature A is a cheap way to find bug B.** This
   one ran Phase 1 over twelve pages with no detection, took seconds, and the
   feature it was built for turned out to be the less valuable half of the work.

### The audit that lesson 1 asks for

Rather than leave it as a moral, every consumer of `Staff` was checked against a
real one-line staff (La Mer p.25 staff 11: `line_ys=[1841]`, span 0), and the
blast radius was measured over 22 pages of La Mer and Mahler 5 — the two
benchmark scores that have one-line parts.

| | |
|---|---:|
| pages swept | 22 |
| pages carrying a one-line staff | **13** |
| of those, crashing on `main` before the fix | **3** |
| crashes after the fix | **0** |

La Mer p.25 and p.30, and Mahler 5 p.5. The crash needs a one-line staff **and**
a cell wide enough to trigger the barline scan, which is why it is 3 of 13 rather
than all 13 — and why it went unnoticed. One-line staves are much commoner than
the original write-up implies ("14 times over 47 pages"): they are on **13 of 22
consecutive pages** of these two scores.

The other consumers are safe, and for different reasons worth recording:

- `detect_barlines`, `extract_measures` — filter on `len(line_ys) >= 5` already.
- `_cell_scale` — guards `staff_span_px <= 0` and returns early, so the
  canonicalization path was never at risk.
- `header_windows_for_page` / `header_cells_for_page` — **do** build a window and
  a cell for a one-line staff. That is harmless rather than correct: the cell
  carries `staff_line_ys_canonical=[52]`, one entry, so `clef_geometry`'s
  `len(...) != 5` guard abstains, and no fabricated five-line geometry reaches
  any reader. Verified across all 13 pages: **zero** header cells faking five
  lines. It costs one wasted detector call per one-line staff and produces no
  wrong answer, so it is left alone.
- `slots.py`, `contextual.py`, `staff_labels*` — include one-line staves
  deliberately. That is the entire point of the August work: the staff must exist
  so the staves below it keep their slot.

So the shape of the rule is: **anything that MEASURES a one-line staff must skip
it; anything that COUNTS it must not.**
