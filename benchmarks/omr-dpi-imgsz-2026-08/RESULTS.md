# DPI and imgsz are coupled, and the best pair depends on the music

## The question

`benchmarks/omr-imgsz-sweep-2026-08` took `imgsz` from 2048 to 512 and moved
every end-to-end metric, correctly identifying it as the cause of note
over-detection. It unified the two `imgsz` defaults that had drifted apart
(CLI 2048, backend 1280 → both 512).

It left the *other* drifted pair alone: the CLI renders pages at **600 DPI**,
the backend at **300**. The obvious reading — "the benchmarks run at one of
them, so make both match" — turns out to be wrong in an instructive way.

## Measured, on the authored end-to-end fixtures

`python3 -m tools.omr.training.end_to_end_eval --dpi D --imgsz N`

| dpi | imgsz | fixture | measures | notes (omr/truth) | recall | precision | duration |
|---:|---:|---|---:|---:|---:|---:|---:|
| **300** | **512** | melody   | 9/6  | 21/24  | 0.625 | 0.714 | 0.667 |
| **300** | **512** | keyboard | 4/4  | 23/27  | 0.852 | **1.000** | **1.000** |
| **300** | **512** | ensemble | 3/4  | 47/45  | **0.956** | **0.915** | **0.930** |
| 600 | 512  | melody   | 12/6 | 30/24  | 0.667 | 0.533 | 0.625 |
| 600 | 512  | keyboard | 4/4  | 31/27  | 0.926 | 0.806 | 0.920 |
| 600 | 512  | ensemble | 4/4  | 57/45  | 0.867 | 0.684 | 0.744 |
| 600 | 1024 | melody   | 12/6 | 16/24  | 0.208 | 0.312 | 0.400 |
| 600 | 1024 | keyboard | 4/4  | 39/27  | 0.704 | 0.487 | 0.684 |
| 600 | 1024 | ensemble | 4/4  | 48/45  | 0.511 | 0.479 | 0.739 |

On these, 300 DPI looks like a clear win — `ensemble` precision 0.684 → 0.915.
**That conclusion does not survive contact with orchestral music.**

## The same comparison on orchestral pages

`python3 -m tools.omr.training.orchestral_eval --dpi D`, excerpts rendered from
the Gradus MXLs (see `benchmarks/omr-orchestral-e2e/`).

| dpi | work | parts | notes (omr/truth) | recall | precision | duration |
|---:|---|---:|---:|---:|---:|---:|
| 300 | beethoven-sym5-mvt1 | 18/18 | 81/81  | 0.531 | 0.531 | 0.674 |
| 300 | brahms-sym1-mvt1    | 21/21 | 495/661| 0.209 | 0.279 | 0.297 |
| 300 | mahler-sym5-mvt1    | 31/38 | 37/24  | **0.042** | 0.027 | **0.000** |
| **600** | beethoven-sym5-mvt1 | 18/18 | 93/81  | **0.642** | 0.559 | **0.731** |
| **600** | brahms-sym1-mvt1    | 21/21 | 496/661| 0.206 | 0.274 | 0.397 |
| **600** | mahler-sym5-mvt1    | 31/38 | 46/24  | **0.208** | 0.109 | 0.200 |

Mahler collapses at 300 DPI — recall 0.208 → 0.042, duration accuracy to zero.
Beethoven loses recall and duration. Brahms is a wash.

## So the two defaults are not simply a bug

The sparse authored fixtures and dense conductor's pages want **opposite**
settings, and each entry point happens to run the one that suits what it was
tuned against. Unifying them in either direction ships a regression on the
other family.

**It is not staff size.** The obvious explanation — orchestral staves are
smaller, so they need more resolution — is measurably false. Staff line spacing
is identical across every fixture at a given DPI (20.8 px at 300, 41 px at 600),
because LilyPond scales the page to fit regardless of `set-global-staff-size`.
What differs is measure **width**: eight bars across an eighteen-staff system
are narrow cells, and cells are rescaled toward a canonical staff span bounded
by `max_cell_width` before being letterboxed into `imgsz²`. Two pages at the
same DPI therefore reach the detector at different effective magnifications.

**imgsz does not scale with DPI.** If the two were a ratio, 600/1024 would
reproduce 300/512. It is far worse than both, matching the imgsz sweep's finding
that false-positive rate tracks *absolute* imgsz.

## Action taken

**None to the defaults.** The CLI stays at 600, the backend at 300, and the
`--dpi` help text now says why, so the next person does not "fix" the
inconsistency without measuring both families.

What did change: `end_to_end_eval` and `orchestral_eval` no longer restate the
pipeline's `dpi`/`imgsz` defaults. They pass `None` and inherit whatever
`transcribe` uses. Restating them is how the benchmark and the pipeline came to
run different configurations twice — the imgsz sweep's published numbers
reproduce here only at `--dpi 300`, which means `imgsz 512` was tuned at 300 DPI
while the CLI ran it at 600.

## The real fix, unbuilt

The variable that matters is not DPI but **pixels per staff space reaching the
detector**, after canonical rescaling and letterboxing. That is computable per
cell before inference. Choosing `imgsz` per cell to put the cell in a measured
sweet spot — rather than fixing one value for a whole corpus — would remove the
trade instead of picking a side.

Prerequisite: a 2-D sweep of dpi × imgsz over **both** fixture families at once.
Every sweep so far has optimised one and silently regressed the other, twice.
