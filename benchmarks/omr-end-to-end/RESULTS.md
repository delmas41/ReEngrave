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

| fixture | parts | measures | notes (omr/truth) | pitch recall | pitch precision | duration |
|---|---|---|---|---|---|---|
| melody | 1/1 | **9/6** | 32/24 | **0.292** | **0.219** | 0.286 |
| keyboard | 2/2 | 4/4 | **111/27** | 0.593 | **0.144** | 0.438 |
| ensemble | **1/4** | 4/4 | 47/45 | 0.711 | 0.681 | 0.906 |

Pitch recall is the share of the true notes recovered; precision is the share of
reported notes that are real. Notes are aligned per part by longest common
subsequence over pitch names — deliberately generous, since it ignores where a
note sits in the bar and asks only whether the sequence of pitches is right. A
measure-aware alignment would score lower.

## What it exposes

**Single-staff scores over-segment.** `melody` reads 9 measures where there are
6, and the overlay shows why: with one staff there is no cross-staff vote, so
note stems are read as barlines. Mis-segmentation then cascades — the first cell
collects 18 noteheads where the bar holds four. This is the worst fixture on
every metric, and it is the *simplest* music on the page.

**Noteheads are over-reported.** `keyboard` returns 111 notes for 27, a
precision of 0.14 on a clean render. Whatever the mechanism, it is not a subtle
accuracy loss.

**Four staves came back as one part.** `ensemble` is read as a single part
because each staff ended up with one measure — every internal barline was
missed — which triggers the "fragmented row" merge in `export.to_musicxml`. In
open score the barlines do not cross between staves, which is the same shape the
clef branch found on Nottebohm.

Interestingly `ensemble` is the *best* fixture on note accuracy (0.71 recall,
0.91 duration) despite being the most complex. More staves means more corroborat-
ing evidence, which is the opposite of the intuition that dense scores are harder.

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
