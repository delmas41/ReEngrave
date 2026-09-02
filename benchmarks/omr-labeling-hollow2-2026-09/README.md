# Hollow noteheads, round 2 — five editions, five presses

[`omr-labeling-hollow-2026-08`](../omr-labeling-hollow-2026-08/README.md)
labelled **one** edition. The failure it exists to fix is appearance-specific —
a half notehead's counter closing on a particular scan of a particular press —
so a model taught on one print learns one appearance. This round varies the
press, the decade and the scan.

| batch | edition | raster | cells | measured yield |
|---|---|---|--:|--:|
| [`peters-mahler5`](../omr-labeling-hollow2-2026-09-peters-mahler5/) | Mahler 5 *Adagietto*, Edition Peters 3087b | 4385x5857 jbig2 @600 | 56 | **9/12 cells, ≈56 boxes** |
| [`eulenburg-scheherazade`](../omr-labeling-hollow2-2026-09-eulenburg-scheherazade/) | Scheherazade, Eulenburg miniature, plate 2957 | 2938x4293 jbig2 @600 | 56 | 5/12, ≈56 |
| [`litolff-hires`](../omr-labeling-hollow2-2026-09-litolff-hires/) | Beethoven 5 finale, Litolff 1870, plate 2769 | 5409x7207 jbig2 @599 | 56 | 5/12, ≈42 |
| [`breitkopf-brahms1`](../omr-labeling-hollow2-2026-09-breitkopf-brahms1/) | Brahms 1, Breitkopf & Hartel *Samtliche Werke* | ~5280x6945 ccitt @534 | 56 | 3/12, ≈23 |
| [`simrock-dvorak9`](../omr-labeling-hollow2-2026-09-simrock-dvorak9/) | Dvorak 9, Simrock 1894, plate 10139 | 5088x6976 jbig2 @601 | 56 | 3/12, ≈19 |

**280 cells, ≈196 hollow noteheads expected.** Yield is a twelve-cell read of
each batch by eye, scaled — not a transferred rate.

The Litolff is deliberately the same plates the first round labelled, scanned
four times larger: *how the same ink is photographed* is its own axis of
appearance and the cheapest one to vary. Its music is new (the finale, not
movement I).

Every batch is **draw-from-scratch**: `detections/` holds an empty stub per
cell. The first round's [AUDIT.md](../omr-labeling-hollow-2026-08/AUDIT.md)
measured why — 116 of 117 model pre-labels were false on that print.

## Two things this round learned the hard way

**1. Meter shortfall does not transfer as a selector.** The first round ranked
bars by how far their content fell short of their meter, worth 4x uniform
sampling *there*. Here it fails twice over: it ranks bars the pipeline got
wrong *for any reason* (three pages of Beethoven's beamed-quaver Allegro gave
51 ranked cells and **not one** hollow head in twelve read at random), and on
most of these editions the meter is never read at all, so there is nothing to
rank — 1–7 short bars per page against Beethoven's 43–49. The Mahler
*Trauermarsch* is the structural case: it is in **cut common**, and
`time_signature_locator` deliberately never searches for `timeSigCutCommon`,
so that movement cannot be ranked this way at all.

**2. A page-level look is not enough either.** Brahms's 6/8 wind lines read as
sustained at page scale and are *dotted quarters* — solid. Only the cells
settle it.

## The selector that did work

A hollow notehead is an ink ring around a white lens. `hollow_score.py` counts
the enclosed white regions of notehead-counter size and shape in a cell's
staff-line-removed crop.

⚠️ **A cell RANKER, not a detector.**
`../omr-first-run-2026-08/DURATIONS.md` closed the detector route: proposing
boxes this way gave 662 candidates for 68 real half notes. *Does this cell
contain one* is a much weaker question, and it validates against the first
round's own hand labels:

```
score >= 1   selects 22, 20 correct   precision 91%   (uniform 52%)
score >= 2   selects 14, 14 correct   precision 100%
top-20       18 positives                        90%
```

**A band, not a top-N.** The count inflates on a lighter print without meaning
more half notes — Dvorak's top cells score 9–47 and are runs of beamed
semiquavers whose "counters" are the gaps between beams and the loops of
*cresc.* Cells come from the band **2–6**, sampled randomly inside it.

```bash
python3 benchmarks/omr-labeling-hollow2-2026-09/validate_hollow_score.py
```

⚠️ needs `benchmarks/omr-labeling-hollow-2026-08/cells/`, which is gitignored
and lives in the MAIN checkout — pass `--cells-root` from a worktree.

## Reproducing a batch

```bash
# 1. cut every measure cell on the chosen pages (page is 1-based on the CLI)
PYTHONPATH=. python3 benchmarks/omr-labeling-hollow2-2026-09/cut_candidate_cells.py \
    --out-dir benchmarks/omr-labeling-hollow2-2026-09-<tag> \
    --plan "<tag>=/abs/score.pdf:175:999,<tag>=/abs/score.pdf:176:999"

# 2. keep the 56 best by hollow score, delete the rest, write HOLLOW_HINTS.txt
python3 benchmarks/omr-labeling-hollow2-2026-09/rank_and_trim.py \
    benchmarks/omr-labeling-hollow2-2026-09-<tag> 56

# 3. empty detections stub per cell, then label
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow2-2026-09-<tag>
```

`cut_candidate_cells.py` wraps `select_cells_orchestral` with two changes, both
documented in its docstring: the padding globals are left at the **pipeline's**
values (so a cell is framed as the detector sees it at inference, the argument
`select_short_bar_cells` makes), and even-spaced sampling is replaced by a
seeded random one — the stride aliased onto measure 0, putting 23 of 54
Scheherazade cells on the clef-and-key crop at the head of a system.

## Pages avoided on purpose

No cell comes from a page that `benchmarks/omr-scan-e2e-2026-09` scores
(Beethoven 575951 p0, Dvorak p4, Brahms p0, Mahler p1). Labelling those would
train on the benchmark.
