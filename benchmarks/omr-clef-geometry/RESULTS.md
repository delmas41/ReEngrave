# Clef reading by geometry — results (2026-08-27)

Follow-up to `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`, which
established that the clef *approach* worked but that no fine-tuned checkpoint
could be deployed, and left alto↔tenor confusion unsolved. This round stops
trying to solve it with a model.

**Headline: alto vs tenor is not a recognition problem, and treating it as one
is why it stayed broken.** They are the same glyph one staff line apart. So is
soprano, mezzo-soprano and baritone. The distinguishing information is the
glyph's *position*, which a class label discards — and DSv2 has only two C-clef
classes, so three of the five are unrepresentable in that label space at any
level of training. Measuring the position instead makes the answer exact.

Two modules, and one starting observation that turned out to matter more than
either.

---

## The starting observation

The user's case: Beethoven's counterpoint studies (Nottebohm, *Beethovens
Studien*, 1873) — species counterpoint and fugue exercises written throughout
in C clefs — came out with no clefs determined.

Reproduced on p.90 (printed p.75). The page has seven detected staves. Across
all of them the production model returns **one** clef detection, and it is
wrong (`clefF`, conf 0.10, on a staff carrying a C clef). Every staff falls back
to the position default, so the page transcribes as treble/bass.

Probing further: at conf **0.03**, over the staff-header crop, with *both* the
production model and the `clef-ft-boxfix` specialist, the number of C clefs
found on this page is **zero**.

| model | conf | C clefs found on p.90 |
|---|---|---|
| production | 0.25 | 0 |
| production | 0.03 | 2 spurious `clefCAlto` at 0.06–0.10, neither on a clef |
| clef-ft-boxfix specialist | 0.25 | 0 |
| clef-ft-boxfix specialist | 0.03 | 0 |

This is a **domain gap, not a threshold**. The glyph is the archaic "ladder"
C clef of 19th-century engraving, which looks nothing like the fonts DSv2 was
rendered from. No confidence setting reaches it, and the specialist — fine-tuned
on modern orchestral scans — is no better. Same conclusion the time-signature
work reached about orchestral meters (`docs/dossier-verification-plan.md`).

---

## Part 1 — `clef_geometry.py`: which line does the clef name?

The detector keeps the job it can do: find a clef and name its family (G / C /
F), which is a real visual distinction. Geometry does the rest — snap the
glyph's named line to the nearest of the five staff lines, look the clef up by
`(family, line)`.

A C clef is symmetric about the line it names, so its named line is the middle
of its box. No calibration constant, and true of an archaic engraving as much
as of a modern font.

`pitch_resolver._CLEF_ANCHORS` and `export._MXL_CLEF_SIGN` are now *derived*
from the same clef table, so all ten clefs are supported end to end without a
second list to drift out of sync. The four pre-existing anchors are unchanged.

**G and F clefs deliberately keep their class label.** They aren't symmetric,
so they'd need a calibrated offset, and the expected value is negative: treble
and bass dominate those families, french/varbaritone/subbass barely occur, and
a wrong guess transposes every pitch on the staff. Enabling them is a config
change (`ClefGeometryConfig(families=...)`), not a code change.

---

## Part 2 — `clef_locator.py`: is there a clef here at all?

Geometry can't help when there is no detection, which on the Nottebohm material
is every staff. So find the clef by shape, the way Phase 4f handles stems and
beams: morphology doesn't care what font a glyph is set in.

Strip the vertical rules (the barline sits ~3px from the clef — too close for
any proximity grouping to separate), strip the horizontal ones (staff lines,
and the substantial residue upstream removal leaves on these thick uneven
lines), cluster the surviving header ink, and take the first glyph-sized
cluster. Accept it only if it is symmetric about its own centre — the C-clef
signature — and then use that same symmetry to read the line, refined to the
axis the ink actually balances about.

Three design decisions did the work:

1. **C clefs only.** The one clef with a shape signature that survives any
   engraving style. G/F yield nothing.
2. **Stop at the first glyph-sized cluster; never scan past one.** This was the
   locator's one dangerous bug. A G clef is too tall to be a C clef, and
   skipping it landed the search on the key signature's first sharp — narrow,
   tall, and beautifully symmetric — which was then read as the staff's clef.
   Fixing this removed *every* false positive on Bach at a stroke, and let the
   crude "clef must start near the staff head" bound be relaxed from 3.0 staff
   spaces to a 6.0 backstop (orchestral clefs sit further in, behind brackets
   and stacked instrument numbers).
3. **It only speaks when nothing else did.** Gated on no clef having been read
   for that staff by either model, so it can add a reading but never overturn
   one, and pages that read correctly today cannot get worse.

---

## Validation

### Controlled ground truth — LilyPond reference staves

`reference-clefs.ly` engraves one staff per clef, so the right answer is known
by construction rather than by eye.

| engraved | read as | symmetry | residual (line spacings) |
|---|---|---|---|
| soprano | **soprano** ✓ | 0.990 | 0.17 |
| mezzosoprano | **mezzosoprano** ✓ | 0.991 | 0.14 |
| alto | **alto** ✓ | 0.9999 | 0.12 |
| tenor | **tenor** ✓ | 0.994 | 0.07 |
| baritone | **baritone** ✓ | 0.990 | 0.02 |
| treble | *(declined)* ✓ | — | — |
| bass | *(declined)* ✓ | — | — |

**5/5 exact, including the alto/tenor pair**, with treble and bass declined
rather than guessed.

### False positives — Bach WTC, 10 pages of piano music

Piano music has no C clefs, so every hit would be a false positive.

| pages | hits |
|---|---|
| WTC I, p.3–12 | **0** |

(Before the "stop at the first glyph-sized cluster" rule: 20 false "tenor"
reads across the same pages, all of them key-signature sharps behind a skipped
treble clef.)

### True positives — real scores

Every located clef below was checked against the rendered page.

| score | located | verdict |
|---|---|---|
| Handel *Messiah* (vocal part), p.2 | 4 × alto | correct — C-clef vocal part |
| Ravel *Boléro*, p.30–31 | 6 × tenor, 4 × alto | correct — trombones, violas |
| Debussy *La Mer*, p.26 | 1 × alto | correct — viola |
| Beethoven 5, p.9 | 1 × alto | correct — viola |
| Nottebohm p.90 / p.95 | 2 × soprano, 2 × tenor, 1 × alto | C clefs where nothing was detected before |

One Beethoven 5 read worth recording: the measured axis landed at y = 478.0
against a staff line at exactly 478 (residual 0.00), naming a tenor clef, on a
glyph a visual estimate had put on the middle line. The measurement was right
and the eyeball wasn't — which is the argument for the whole approach.

### No collateral damage

| run | noteheads | detections |
|---|---|---|
| Nottebohm p.90, before | 68 | 186 |
| Nottebohm p.90, after | **68** | **186** |
| Mahler 5 p.11 | **2506** | 4878 |

Byte-identical detection output on Nottebohm, and Mahler 5 p.11 sits exactly on
the 2506-notehead production baseline from `omr-clef-demo`. The clef work
touches clefs and nothing else — the opposite of the fine-tuned checkpoints,
which bought clefs by collapsing dense-page noteheads to ~5%.

### Export

`soprano` survives the whole chain: `<sign>C</sign><line>1</line>` in MusicXML,
`\clef soprano` in LilyPond, re-parsed by music21 as `SopranoClef`, and the
exported `.ly` compiles.

### Tests

65 new tests (`test_clef_geometry.py`, `test_clef_locator.py`); 513 passing in
`tools/omr/tests/` overall, no regressions. The locator's tests draw their own
cells, so they exercise rule stripping, clustering, the symmetry gate and the
snap against glyphs whose named line is known by construction — including the
G-clef-then-sharp trap that produced the Bach false positives.

---

## What this does NOT fix

**Recall on the Nottebohm book is low** — 5 clefs located across ~57 staves on
the pages sampled. The limiter is upstream of clef reading, and it is worth
recording plainly because it is the next real bottleneck for this material:

- **Text blocks are detected as staves.** Two of p.90's seven "staves" are
  columns of body text that the staff detector latched onto.
- **Many staff-start cells don't contain the clef.** On several staves the
  first cell begins after the clef, so there is nothing for any reader — model
  or CV — to find. Where the cell does contain it, the locator reads it.

Neither is a clef problem. Fixing staff detection and cell extraction on
small-format 19th-century prints is its own piece of work, and it would raise
the yield of everything downstream, not just clefs.

The locator also abstains on Mahler 5 p.11 (dense orchestral, ink-heavy
headers), where the decoupled `--clef-weights` specialist remains the better
route.
