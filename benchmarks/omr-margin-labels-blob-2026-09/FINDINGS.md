# A whole system's margin arriving as one label — closed

**2026-09-04/05.** The last open item from `benchmarks/omr-lexicon-2026-09/`:
"a whole margin can arrive as ONE label, and it resolves to whichever
instrument the index reaches first" — Beethoven 5's 17-staff margin resolving
to **Piccolo**, Mahler 5's 19-staff margin to **Trombone**. Flagged there as a
reader/assignment fault, not a lexicon one, needing its own look.

## What it actually was

Both blobs are Surya reads (`beethoven5-575951-textlayer` names the edition,
not the reader that produced this record — that page's text layer is thin
enough here that Surya was consulted). Re-reading the exact pages with the
raw per-block output surfaced (`_surya_worker.py`'s `raw_lines`, not exposed
to the host before this) shows Surya returning **exactly one OCR block for the
whole crop**:

```
mahler5-BAD p163 sys0 — 19 staves, span=1506px
  raw_lines (1): 'Flötten \n 3 \n 8 \n 4 ... Bässe \n 1 \n 2 \n 3 \n 4 \n 5 \n 6 \n 7'
  assigned: {'10': '<the whole thing>'}

beethoven5-BAD p58 sys0 — 17 staves, span=1506px
  raw_lines (1): 'Fl. \n pic. \n ... Tr. \n Bas.'
  assigned: {'8': '<the whole thing>'}
```

Surya's layout step failed to segment the crop at all — every instrument name
on the page, one OCR block. `_assign` was never wrong about WHICH staff the
block's centroid landed nearest; the input it was handed was already garbage,
and it had no way to know that. Forcing a block onto the nearest tick when
there is only one block turns "the OCR did not segment" into "this staff plays
the piccolo" — a confident wrong instrument rather than an honest abstention.

⚠️ **Not a single-staff-system / infinite-tolerance edge case.** Both systems
have many staves (17, 19) and the existing `tolerance` math (`_TOLERANCE =
0.5` of the inter-tick spacing) is finite and working correctly here — it
faithfully picked the nearest tick to the one block it was given. The defect
is upstream: nothing previously recorded a block's own SIZE, only its
centroid, so a block spanning the whole crop looked identical to a normal
label as far as `_assign` could tell.

## The fix

`_lines_with_boxes` already read each block's polygon for its y-centroid;
it now also keeps `max(ys) - min(ys)` — the block's own height — and threads
it through `_lines` to `_assign`. A block taller than
`_RUNAWAY_HEIGHT_FRACTION` (0.5) of the SYSTEM's own tick span is dropped
before the nearest-tick test, rather than being forced onto whichever staff
it lands nearest.

Scale-invariant on purpose: the ratio is to the crop's OWN tick span, not an
absolute pixel count, so it travels across DPI and system size without a
second constant to tune per corpus.

## The two populations the threshold sits between

Measured directly against the real pages, plus a known-good comparison where
Surya DID segment correctly (`reproduce_blob.py`, the exact script this
file's numbers came from — re-run it and the table below is what prints):

| case | span | block | height | **frac** |
|---|--:|---|--:|--:|
| Mahler 5 p.163 (BAD) | 1506px | the whole crop | 1568px | **1.041** |
| Beethoven 5 / 575951 p.58 (BAD) | 1506px | the whole crop | 1567px | **1.040** |
| Boléro p.1 sys.1, 19 staves (GOOD) | 1513px | `2 TAMBOURS 3 TIMBALES…` | 70.6px | 0.047 |
| ″ | 1513px | `HAUTBOIS 2 Hautbois…` | 67.4px | 0.045 |
| ″ | 1513px | `3 SAXOPHONES Sopranino…` | 64.3px | 0.042 |
| ″ | 1513px | `CLARINETTES Petite Cl…` | 64.3px | 0.042 |
| ″ | 1513px | `TROMPETTES 3 Tromp…` | 59.6px | 0.039 |
| ″ | 1513px | `BASSONS 2 Bassons…` | 53.3px | 0.035 |
| ″ | 1513px | `FLÜTES 2 Grandes Flütes…` | 42.3px | 0.028 |
| ″ | 1513px | 9 more blocks | 22–25px | 0.015–0.017 |

**A ~22× gap, with `0.5` sitting in the middle of it.** The bad blocks are
*slightly over* 1.0 because `margin_strip`'s own padding (`2 * spacing` above
and below the outermost staff) adds a little height beyond the raw tick
span — a block that swallows the crop swallows the padding too. All 17
distinct blocks Surya correctly split on Boléro's page — the SAME kind of
dense, many-staff system a runaway block would target — sit at 1.5–4.7% of
the span, and 16 of the 19 staves receive a correct instrument (the other 3
are strings the page genuinely leaves unlabelled below the first system).
`0.5` is not a tuned edge; anywhere from roughly 0.1 to 0.9 would separate
these two populations identically on this evidence.

⚠️ **Fixing this exposed a second, narrower failure the first synthetic test
attempt didn't catch.** A test asserting only that no returned label exceeds
some LENGTH passes whether or not the gate fires, because the real defect
concatenates many instrument names into one long STRING specifically because
the runaway block spans many staves' worth of *text* as well as height — a
single huge GLYPH (one character) is tall without being long. The shipped
test (`test_a_block_that_swallows_the_whole_crop_is_rejected_not_assigned`,
`tools/omr/tests/test_staff_labels_surya.py`) asserts on the STAFF ASSIGNMENT
directly (`"X" not in labels.values()`), and was run red (gate disabled,
`{0: 'Ob.', 2: 'X'}`) before green (gate on, `{0: 'Ob.'}`) to confirm it
actually exercises the mechanism rather than passing vacuously either way.

## Validation

- Full suite: **2059 passed, 0 failed** (was 2058 before this fix — +1 new
  test), including every existing `staff_labels_surya` test unchanged.
- Both known-bad systems: **`labels: {}`** — correctly rejected outright,
  where before they resolved to a confident wrong instrument.
- The known-good Boléro system: **byte-identical**, all 7 labels intact — the
  gate only reads block height, so a block that was never near the threshold
  is untouched.
- `raw_lines` now carries `{"text", "height"}` per block instead of bare
  strings — a purely additive change (nothing on the host consumed the old
  shape), kept because a mapping bug, an OCR miss, and a rejected runaway
  block now look different in the diagnostic output where before the first
  two were indistinguishable and the third didn't exist as a concept.

## What this does NOT fix

Surya's own layout step still fails to segment a dense multi-staff margin on
these two pages — that is a property of the model, not something this repo
controls. The fix stops the failure from producing a confident wrong
instrument; it does not recover the labels those two systems should have had.
Both systems now behave as **unlabelled**, which is the honest fallback the
rest of the pipeline (dossier joins, slot naming) already handles — see
"Unlabelled staves must return null" in `staff_labels_vision.py`'s design
notes, the same standard the Vision reader already holds itself to.

## Reproducing

```bash
python3 benchmarks/omr-margin-labels-blob-2026-09/reproduce_blob.py
python3 -m pytest tools/omr/tests/test_staff_labels_surya.py -k swallows -v
```
