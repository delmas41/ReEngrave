# OMR-NED — the first comparable accuracy number this project has had

**2026-08-31.** Every accuracy figure in this repo has been bespoke: F1 over a
25-cell verdict set, pitch recall against an authored fixture, clef accuracy
over 52 hand-read staves. Each answers the question it was built for, and none
can be set beside a published result. OMR-NED (Martinez-Sevilla et al., *Sheet
Music Benchmark*, ISMIR 2025, arXiv:2506.10488) is what OMR papers now report.

    OMR-NED = (insertions + deletions) / (symbols_pred + symbols_truth)

Lower is better. It is computed by `musicdiff` 5.2, which the SMB authors
extended for the paper, reached through `tools/omr/omr_ned.py`.

```bash
python3 -m tools.omr.omr_ned --bootstrap        # once — builds .venv-omrned
python3 -m tools.omr.training.orchestral_eval --omr-ned
python3 -m tools.omr.omr_ned pred.musicxml truth.musicxml   # any single pair
```

## The number

Engraved orchestral benchmark (`benchmarks/omr-orchestral-e2e/`), 8-bar
excerpts, production weights, dossier on:

| work | OMR-NED | edits | truth syms | pred syms | note recall (old metric) |
|---|--:|--:|--:|--:|--:|
| mahler-sym5-mvt1 | **0.0785** | 146 | 958 | 903 | 0.917 |
| beethoven-sym5-mvt1 | **0.1958** | 240 | 655 | 571 | 1.000 |
| brahms-sym1-mvt1 | **0.4664** | 1838 | 2083 | 1858 | 0.717 |
| **pooled** | **0.3164** | 2224 | 3696 | 3332 | — |

> **Superseded 2026-09-01 by the beam fix, the first thing this metric bought.**
> `export.py` never emitted `<beam>` at all, though Phase 4f detects beams and
> `transcribe` writes them into the JSON. Emitting them:
>
> | | before | after |
> |---|--:|--:|
> | pooled | 0.3164 | **0.3045** |
> | edits | 2224 | **2140** |
> | wrong flag/beam | 225 (10.1%) | **141 (6.6%)** |
> | beethoven | 0.1958 | **0.1843** |
> | brahms | 0.4664 | **0.4486** |
>
> Mahler is unchanged — its 8-bar excerpt carries only 24 notes.

Pooled, not averaged — one edit-sum over one symbol-sum, the way the paper
defines it, so the dense score counts for more.

**Do not read this against LEGATO 2's 17.1 and call it a loss.** That number is
on rendered *string quartets*; this is 18–38 staves. Same metric, different
difficulty. What the metric buys is that the comparison is now *possible* and
the categories are standard — not that these rows are league-table entries.

## What it found that note recall could not

Beethoven has **note recall 1.000** and **OMR-NED 0.1958**. Every note it found
was the right pitch; the old metric therefore called the page perfect. The
breakdown says a third of the edit budget is elsewhere:

| pooled category | edits | share |
|---|--:|--:|
| wrong note | 780 | 35.1% |
| entire measure insert/delete | 705 | 31.7% |
| wrong flag/beam | 225 | 10.1% |
| wrong direction | 151 | 6.8% |
| wrong dot | 103 | 4.6% |
| wrong slur | 70 | 3.1% |
| *(14 more)* | 190 | 8.5% |

Three findings, each verified in `musicdiff`'s own textual diff rather than
inferred from the totals:

**1. Flags are being read where beams are printed.** On the Beethoven opening
the pipeline emits `(Note:flagsbeams) A4 eighth, 1 flag` against a truth of
`1 beam=start / continue / stop`, across every staff carrying the motif — 48
edits on this page alone. The notes, pitches and durations are all correct, so
no existing metric sees it, but a flag where a beam belongs is wrong on the page
and wrong in the exported MusicXML.

**2. Directions, dynamics, tempo and text are never emitted at all.** `ff`,
`Allegro con brio` and `Half=108` are present in every truth and absent from
every prediction. That is not a recognition failure to chase — the exporter has
nowhere to put them — but it is 151 + 34 edits of the budget, and it will not
move until something emits them.

**3. `entire measure insert/delete` at 31.7% is real but AMPLIFIED, and this is
the trap in reading this metric.** Measure counts, part counts, and
empty-measure counts all match exactly between truth and prediction, so nothing
is missing. Dumping the op list gives the cause:

```
insbar cost 3 | ['[R]2 fermata']      <- truth
delbar cost 2 | ['[R]2']              <- prediction
```

The measures differ **only by a fermata**. Because the measure's content
signature differs, `musicdiff` charges delete-the-whole-bar plus
insert-the-whole-bar rather than one articulation edit: 25 missed fermatas
became 50 operations costing 128 of Beethoven's 240 edits.

So the honest reading is that the pipeline misses the two famous fermatas of
the Beethoven 5 opening — a genuine miss — and that OMR-NED prices that miss at
roughly five symbols per bar rather than one. **When this bucket is large, open
the op list before believing the severity.** It is the one category here whose
weight does not track musical importance.

## Caveats that belong with any number from this harness

- **It scores recognition AND export together.** `export.to_musicxml` emits one
  `<part>` per (page, system, staff); a Gradus truth has one per instrument.
  Where those disagree the metric charges for it, correctly, but it is not a
  detector number. Read it next to note recall, not instead of it.
- **It is symmetric.** The denominator sums both sides, so swapping prediction
  and truth does not change the score — it silently changes which file is
  parsed strictly. `score_pair` is keyword-only for that reason.
- **The engraved benchmark says nothing about scan robustness** — same caveat
  the orchestral e2e harness already carries.
- **Clefs barely register here**: 9 edits out of 2224 (0.4%). That is not a
  contradiction of the clef work — these pages are engraved and dossier-seeded.
  It does mean the clef thread cannot be justified from *this* benchmark, and
  needs the scanned corpus where it was measured.

## Where the harness lives

| file | role |
|---|---|
| `tools/omr/omr_ned.py` | bridge + CLI; runs on the host's 3.9 |
| `tools/omr/_omrned_worker.py` | runs inside `.venv-omrned` (Python ≥ 3.10) |
| `tools/omr/tests/test_omr_ned.py` | 11 tests; parsing tier needs no venv |
| `tools/omr/training/orchestral_eval.py` | `--omr-ned` scores every pair in one batch |

musicdiff needs Python ≥ 3.10 and music21 ≥ 9.9.1; the host is 3.9 with
music21 8.3.0 and the backend pins its own. Moving the project for a benchmark
would be the tail wagging the dog, so the metric runs out of process in
`.venv-omrned` (gitignored) and talks JSON, the same shape `maestro_bridge.py`
uses to reach node.
