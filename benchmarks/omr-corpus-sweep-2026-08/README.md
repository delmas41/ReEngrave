# Corpus sweep — a wide, ground-truth-free baseline

## Why this exists

Every conclusion this project corrected in the last three days was measured on
too little. The `imgsz` flood, the "11-space gaps" band artefact, the A4 staff
ladders, the key-signature "blindness" — four confident numbers, each describing
the instrument rather than the page, each taken on a handful of pages.

The accuracy sets are small **because truth is expensive**: 52 hand-read staves
for clefs, 42 for key signatures, three pages each. That is the right trade for
measuring accuracy and there is no cheap way to grow them.

But a great deal can be measured without truth. This sweep runs the real
pipeline over a sample of every score on this machine and records what came out
— where each clef came from, which key signatures were read and why the rest
were not, every internal-consistency warning, every crash. None of that needs a
right answer to be useful, because the value is in the **diff**: run it, change
something, run it again, and see the blast radius outside the three pages you
were aiming at.

It is the thing that would have caught the La Mer crash months earlier.

## Running it

```bash
python3 benchmarks/omr-corpus-sweep-2026-08/sweep.py --every 6 --max-per-score 40
python3 benchmarks/omr-corpus-sweep-2026-08/sweep.py --summarize
```

Ten scores, 1363 pages available, ~20-30s per orchestral page. It writes one
JSON line per page and flushes immediately, skips pages already recorded, and
records a crashing page as a row with its traceback rather than stopping — so it
survives being interrupted and can be resumed by re-running the same command.

## Reading the result

`sweep.jsonl` is the artefact. Per page: systems, staves, measures, noteheads,
key signatures read, clef sources, clef values, key-signature unread reasons,
warnings raised, seconds, and `ok` / `error` / `traceback`.

**It measures the pipeline's behaviour, not its correctness.** A page where every
staff reads treble scores no worse here than one read perfectly; that is what
the hand-read sets are for. What this catches is the other half: crashes,
abstention rates, warning volume, and any of them moving when they should not.
