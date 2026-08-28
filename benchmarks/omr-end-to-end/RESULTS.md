# End-to-end accuracy — the first measurement of whether the notes come back right

**2026-08-28.** Every quality figure in this repository is either symbol-level
on hand-labeled cells — the headline **F1 98.8%** — or *coverage* rather than
accuracy. [`benchmarks/omr-real-world`](../omr-real-world/) reports **"100% pitch
coverage and 100% rhythm coverage"** on all five PDFs, which means every
detected notehead was assigned a pitch and a duration. It does not mean the
pitch is correct, and a page can score 100% there while reading entirely the
wrong music. The other headline number, "compiles with zero errors", measures
compilability.

So nothing measured the thing the project exists to do: turn a PDF into the
right notes. This does.

## How the truth is obtained

By authoring it. `tools/omr/training/e2e_fixtures.py` builds scores in music21,
writes the MusicXML (the truth), and renders them through `musicxml2ly` and
LilyPond to PDF (the input). The pipeline is then asked to recover what went in.
Exact, free, and reproducible on any machine with LilyPond.

    python3 -m tools.omr.training.end_to_end_eval

Three layouts, matching the material the corpus contains:

| fixture | shape | stands in for |
|---|---|---|
| `melody` | one staff | the simplest case |
| `keyboard` | two staves, braced | WTC, Handel reduction |
| `ensemble` | four staves, mixed densities, one alto clef | Boléro, Mahler, Beethoven 5 |

`ensemble` exists because a single staff is not merely an easier case, it is a
**different** one: barline detection votes across staves, so a lone staff has
nothing to corroborate with. A benchmark built only from melodies would report a
failure no real orchestral page has.

The fixtures sit in the pipeline's normal operating range — 20.8px staff spacing
at 300 DPI, against 12.5-13.5 for the orchestral corpus and ~18.5 for WTC at the
same DPI. That was checked rather than assumed: an earlier throwaway spike used
a single tiny staff on an otherwise empty page and produced numbers that said
more about the fixture than the pipeline.

## Baseline

Taken at **600 DPI**, the pipeline's own default, on the merged tree (main's
clef / key-signature / staff work plus this branch's Phase-1 and Phase-4f work).

| fixture | parts | measures | notes (omr/truth) | pitch recall | pitch precision | duration |
|---|---|---|---|---|---|---|
| melody | 1/1 | **12/6** | 61/24 | 0.375 | 0.148 | 0.889 |
| keyboard | 2/2 | 4/4 | 45/27 | 0.407 | 0.244 | 0.364 |
| ensemble | 4/4 | 4/4 | 103/45 | 0.400 | 0.175 | 0.167 |

Pitch recall is the share of true notes recovered; precision the share of
reported notes that are real. Notes are aligned **per part** by longest common
subsequence over pitch names — generous, in that it ignores where a note sits in
the bar and asks only whether the sequence of pitches is right.

### Two things that moved between runs, neither of them recognition

The first baseline was taken at **300 DPI**, which was simply a mistake — that
is not the pipeline's default, and DPI moves the numbers a long way and not in
one direction: melody's duration rate 0.29 → 0.89, keyboard's precision
0.14 → 0.33 but its recall 0.59 → 0.41. A benchmark run at a non-default
setting measures a configuration nobody uses.

`ensemble` also **changed shape**. It used to come back as one part; on the
merged tree it is 4 parts and 16 measures, because main's system-grouping work
fixed the open-score barline problem that had collapsed it. That is a real
improvement in structure — and it makes the note score STRICTER, because the
alignment pairs part against part only when the two agree on how many parts
exist, and falls back to one concatenated sequence when they do not. So
`ensemble`'s earlier 0.711 recall and this run's 0.400 are not measuring the
same thing. The comparison to trust from here is between runs where the
structure columns match.

## What this does NOT establish

These are clean synthetic renders. They say what the pipeline does with ideal
input, and ideal input is not what it was tuned on — so these numbers are a
**floor on the diagnosis, not a verdict on real scans**. There is still no
note-level ground truth on a real score, and getting it would need either
hand-transcription or a score whose MusicXML is already known.

The alignment is also generous by construction (see above), and the `measures`
column counts the musical bar count per part rather than summing across parts,
because summing is not comparable when the two scores disagree about how many
parts exist.

## Using it

    python3 -m tools.omr.training.end_to_end_eval --out after.json --compare baseline.json

`--compare` prints only what moved, so a change to any stage of the pipeline can
be checked against the notes it actually produces rather than against the
symbols it detects.
