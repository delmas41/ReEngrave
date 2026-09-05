# The `wrong flag/beam` gap against Audiveris — attribution and repair (2026-09-04)

The industry comparison (`benchmarks/omr-vs-industry-2026-09/`) put the entire
deficit against Audiveris 5.11 in ONE category: `wrong flag/beam`, 449 edits of
our pooled 2,745 against Audiveris's 48 of 2,569. Every other category nets in
our favor or is roughly tied. This benchmark attributes the 449 and lands the
fixes — all of them in `export.annotate_beams`, none in detection.

**Headline (re-export basis, same fixtures, same scorer): `wrong flag/beam`
449 -> 31, pooled edits 2,745 -> 2,473.** Against Audiveris's 2,569 that flips
the comparison from losing by 176 edits to **winning by ~96**, with our beam
bucket now smaller than Audiveris's 48.

## Method

The recorded run's fixtures and predictions live in the `sad-austin-7e16e7`
worktree (`benchmarks/omr-orchestral-e2e/fixtures/*.omr.{json,musicxml}`);
dumping their musicdiff ops reproduces the recorded totals exactly (449 beam,
2,745 pooled — `ops-baseline/`). Every fix here is EXPORT-ONLY, and the
unmodified exporter re-exports the recorded `.omr.json` byte-identically to the
recorded `.omr.musicxml` (checked on brahms-sym1-mvt1), so the A/B loop is
re-export + re-score with no YOLO rerun (`reexport_and_score.sh`), and the
re-export deltas are exact.

## Attribution of the 449

430 of 449 are `editbeam` — notes the aligner PAIRED whose beam-state lists
disagree. This is not missing notes; it is the exporter writing the wrong
begin/continue/end/flag over correctly read notes.

| work | beam edits | of total | dominant signature |
|---|--:|--:|---|
| brahms-sym1-mvt1 | 154 | 494 | edge note flagged, group closes early |
| mozart-sym41-mvt1 | 127 | 425 | same, inside triplet groups |
| mozart-sym40-mvt1 | 65 | 273 | divisi Viola: interleaved rows fragment runs |
| beethoven-sym5-mvt1 | 34 | 77 | first note flagged (stem-up groups) |
| brahms-sym4-mvt1 | 30 | 419 | mixed |
| tchaikovsky-sym4-mvt2 | 21 | 90 | edge note |
| mahler-sym5-mvt1 | 10 | 52 | edge note |
| others | 8 | — | — |

## The mechanisms, in the order found

### 1. The beam box was tested UNPADDED (~370 edits)

`annotate_beams` assigned a note to a box only when the notehead CENTRE fell
inside the box's x-span. The box bounds beam INK, which runs stem to stem, so
the edge note whose stem sits past its own head centre — the FIRST note of a
stem-up group, the LAST of a stem-down group — fell outside by roughly one
head width. It exported as a flag (`partial`) and the group's begin/end landed
one note early: two `editbeam` charges per group, every group, on every
beam-heavy page. A 2-note group lost BOTH notes (the orphan formed a synthetic
run of one; the survivor was alone under its box; both are "a lone note is
flagged").

This is the same lesson `rhythm._beamed_groups` already paid for (its
docstring names the identical stem-vs-centre geometry); the exporter never got
the pad. **Fix: a padded second pass — one notehead width, median of the
events' own head widths — that runs only where the exact test found nothing.**

Measured alone: beam 449 -> 78, pooled 2,745 -> 2,558.

### 2. First-by-x hands notes to a spurious bar-wide box (Brahms 1)

Contrabass m4 carries a third "beam" box of 685px (a hairpin's ink at the real
beams' own y — real group boxes there are 203-216px) spanning the whole bar.
Boxes were tried in x order, and the spurious box starts leftmost, so all six
notes joined it: one merged 6-note run where the page prints two groups of
three. Real beams at one y level cannot overlap in x, so **a box that
x-contains >= 2 mutually disjoint other boxes is SUSPECT** and is tried only
when no honest box claims the note (`_suspect_beam_boxes`).

### 3. Interleaved and stacked boxes fragment groups (Mozart 40, Mozart 41)

Two boxes often describe ONE group:

- a sixteenth group's primary and secondary strokes (same span, a beam pitch
  apart in y);
- a divisi staff's two rows over the same double stops — Mozart 40's Viola
  prints the lower voice's stems-down beam at x 1088-1304 and the upper's
  stems-up beam at 1137-1352, 354px apart in y: the SAME four notes, offset
  one head width. Under first-by-x the fourth note (exactly covered only by
  the second row) split off into its own group — 6-8 edits per bar, every bar.

The group id IS the box id, so any per-note choice between two boxes over one
group fractures the group. **Fix: boxes overlapping >= 0.6 of the smaller in x
collapse into their union (`_collapse_beam_stacks`), with suspects excluded
from collapsing first** — a bar-wide suspect overlaps every real group at 1.0
of the smaller and would union the whole bar back together (this is exactly
what the v3 arm did by collapsing before computing suspects; Contrabass m4
stayed merged there).

## Refused approaches (measured)

| arm | beam | pooled | why refused |
|---|--:|--:|---|
| baseline | 449 | 2,745 | |
| pad only (`padfix`) | 78 | 2,558 | superseded |
| **narrowest covering box wins** | 273 | 2,753 | Mozart 41 7 -> 145: per-note choice between a group's own strokes fractures the group. The trap the collapse rule exists for. |
| **pad + y-band voice preference (v3)** | 77 | 2,557 | Mozart 40 47 -> 54 instead of falling: chord events flip which head is `noteheads[0]`, so a per-note y preference picks different divisi rows for notes of one run and fractures it. Also collapsed before suspecting, leaving Contrabass m4 merged. |
| **shipped (v4: pad + suspect-then-collapse)** | **31** | **2,473** | |

## Per-work totals (re-export basis, baseline -> shipped)

| work | total edits | beam edits |
|---|--:|--:|
| beethoven-sym3-mvt1 | 215 -> 215 | 0 -> 0 |
| beethoven-sym5-mvt1 | 77 -> 43 | 34 -> 0 |
| brahms-sym1-mvt1 | 494 -> 490 | 154 -> 6 |
| brahms-sym4-mvt1 | 419 -> 401 | 30 -> 10 |
| bruckner-sym5-mvt1 | 187 -> 185 | 2 -> 0 |
| dvorak-sym9-mvt4 | 239 -> 239 | 0 -> 0 |
| mahler-sym5-mvt1 | 52 -> 42 | 10 -> 0 |
| mozart-sym40-mvt1 | 273 -> 218 | 65 -> 10 |
| mozart-sym41-mvt1 | 425 -> 301 | 127 -> 3 |
| tchaikovsky-sym4-mvt2 | 90 -> 69 | 21 -> 0 |
| tchaikovsky-sym6-mvt2 | 274 -> 270 | 6 -> 2 |
| **pooled** | **2,745 -> 2,473** | **449 -> 31** |

## The Brahms 1 net is only -4, and the reason is worth keeping

Its beam edits fell 154 -> 6 while `entire measure insert/delete` rose 7 -> 156.
The rise is a musicdiff ALIGNMENT artifact triggered by near-perfection: the
Timpani's seven bars of repeated C3 eighths now export beam-perfect, but three
of them carry a spurious slur and one a spurious tie — the staff BELOW's arcs,
caught in the cell's padding (verified against the rendered page: the arcs
belong to the next staff's line). Bars differing only by that arc lose their
diagonal pairing to an exact-equal bar elsewhere in the part, and musicdiff
charges whole-bar delete + insert (19 each) instead of the few-edit diff.
Under the baseline every bar had beam errors, no bar paired exactly, and the
aligner stayed diagonal — so the beam fix EXPOSED a cross-staff slur/tie
attribution fault that was already there. That is the next seed: killing those
four arcs is worth ~150 edits on this work alone through de-amplification,
plus its share of the pooled `wrong slur` bucket (123). It is slur-attribution
work (arc-to-staff assignment against the cell padding), not beam work, and is
left open here.

## What remains in the 31

- `delbeam` 16: notes we beam that the truth flags or leaves plain — upstream
  `beam_levels` over-detection (e.g. Mozart 40 Violino II notes carrying a
  level the print does not), not export.
- Brahms 4 Viola m5 (7): fragmented groups on a dense divisi bar where the
  detected boxes genuinely disagree with the print.
- Mozart 41 `delbeam` 3, Tchaikovsky 6 `delbeam` 2: same family.

These are recognition-side and small; the export-side mechanisms are closed
and pinned by five new tests in `tools/omr/tests/test_export.py`
(`TestBeamAnnotation`: edge-note pad, 2-note survival, stack collapse, divisi
collapse, suspect box).

## Standing vs Audiveris 5.11 (same fixtures, same scorer)

| | pooled edits | wrong flag/beam |
|---|--:|--:|
| Audiveris 5.11 | 2,569 | 48 |
| ReEngrave before | 2,745 | 449 |
| **ReEngrave after** | **2,473** | **31** |

The full-pipeline confirmation run (`orchestral_eval --omr-ned --work-dir
fixtures-eval`, this worktree) is recorded in `results-v4.json`; the recorded
headline in CLAUDE.md is untouched per policy (measured off main).
