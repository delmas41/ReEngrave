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

### Ground truth from the target book itself — Nottebohm p.31 (PDF 46)

Sean read the clefs off exercises Nr. 20–22 by eye: three systems of four
staves carrying the full vocal clef set, in the archaic square engraving. This
is ground truth on exactly the material the detector cannot touch, and it is
checked in (`nottebohm-p46-ground-truth.json`) with a scorer
(`tools/omr/training/clef_ground_truth_eval.py`).

| | first measured | after the Phase-1 fixes |
|---|---|---|
| clefs READ | 6 staves | **9 staves** |
| precision on those | 6/6 | **7/7** |
| overall (read + inherited + defaulted) | 6/12 | **9/12** |
| supplied by the CV locator | 4/4 | 7/7 |

The two numbers must not be averaged into one, because they measure different
subsystems. **Reading is right every time it happens.** Coverage is the problem.

Two cautions on reading this table. The intermediate figure of 12/12, reached
partway through the Phase-1 work, was measured when barline detection had
collapsed and every staff was a single cell — an easier and unrepresentative
input, not a real high-water mark. And the final 9/12 is scored against
*correct* measure segmentation, where the first cell is a real measure rather
than a whole system.

The locator separated **soprano from alto from tenor** on the square lattice
glyph — three clefs one staff line apart — repeatedly across the page.

### Why the misses were misses

Attributing every miss by hand, at the point where 6 of 12 were read:

| miss | cause | whose problem |
|---|---|---|
| Nr. 22 ×3 | the clef is **not in the cell** — it begins past it | Phase 1 (`_staff_x_extent`) |
| Nr. 20 tenor, Nr. 22 bass | staff lines **mis-grouped** | Phase 1 (`staff_detector`) |
| Nr. 21 alto | clef fused into an oversized cluster | the locator |

Five of six were Phase-1 layout failures — which is what prompted fixing them
(next section), and what took the page from 6/12 to 9/12.

### One negative result, recorded so it isn't retried

The fragmented-clef misses look like the horizontal-rule stripper eating the
archaic clef's bars (those bars are ~1–1.5 staff spaces wide and the threshold
is 1.5). Sweeping that threshold from 0.7 to 6.0 staff spaces makes it **worse
in both directions** (4 located → 1–3), because keeping more horizontal ink
re-fuses the glyph with staff-line remnants. 1.5 is already the optimum.

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

## Phase 1: what the clef work forced open

Chasing the misses above led into the layout stage, and the fixes there
mattered more than the clef work itself. Full rationale in the commits; the
measured effect:

| page | systems | barlines | cells |
|---|---|---|---|
| Nottebohm p46 | 5 → **3** (correct) | 5 → **24** | 16 → **88** |
| Nottebohm p90 | 4 | 9 → **21** | 18 → **39** |
| Beethoven 5 p8 | 5 | 74 → 86 | 273 → 293 |
| La Mer p25 | 9 → 3 | 14 → 12 | 65 → 78 |
| Mahler 5 p11 | 3 | 23 → 27 | 221 (unchanged) |
| WTC ×3, Boléro ×2, Handel | unchanged | unchanged | unchanged |

p46 has 3 systems × 4 staves × ~7 measures, so 88 cells is about right where 16
was not. Three causes, each a rule quietly depending on something else:

1. **`_staff_x_extent` took the longest strictly-contiguous ink run.** Scanned
   staff lines are dashed, so it returned a fragment. Offset measured at 1.2
   staff spaces on Bach and **up to 46** on Nottebohm — past the clef entirely.
2. **The system's opening barline survived as a measure boundary**, because its
   margin was a fixed 10px where engravers set that rule a *fraction of a staff
   space* in (1.5 spaces = 20px on Boléro). It manufactured a sliver measure
   that swallowed the clef.
3. **The system's left edge was `min(x_start)`** across its staves. Staves are
   engraved flush, so that edge is a consensus: on Boléro p.31 one staff of
   seventeen read 4.3 spaces wide of its neighbours and cost that system its
   clefs. Now the median.

Fixing those broke barline detection, which had been depending on the damage:

4. **System grouping was being done by x-overlap**, accidentally. Staves whose
   broken extents disagreed were split apart; once every staff spanned the page
   they merged into one system and the barline vote threshold became
   unreachable. The vertical-gap rules could not take over because both are
   computed over ALL gaps, so on a page that is mostly system breaks the breaks
   drag the thresholds above themselves (p.90: gaps 65, 65, 65, 341, 394, 830 —
   a median of 203 sits above the 341 and 394 breaks). Added a threshold
   against the low quartile, which estimates within-system spacing whatever
   share of the page is breaks.
5. **Open-score barlines do not cross the gaps between staves.** Each voice's
   barlines stop at its own staff, so every real barline scored connectivity
   0.00 and the orchestral-tuned filter discarded all of them. Measured:
   Nottebohm p.31 is 4/4 votes and 0.00 connectivity on every barline; Mahler 5
   p.11 has real barlines at 0.4–1.0 and it is the *stem alignments* that score
   0.00. The filter now asks each system which kind it is.

## Whole-book run

254 pages, of which 156 were transcribed before the run was stopped as no
longer informative. Over those pages:

| | |
|---|---|
| "staves" reported | 1522 |
| — real music (carrying noteheads) | 1366 |
| — body text read as staves | 147 |
| pages containing music | 124 of 156 |
| noteheads / measures | 53,476 / 6,012 |
| **clefs read** | **268 of 1366 staves (20%)** |
| — by the CV locator | **204** (83 alto, 64 tenor, 57 soprano), on 85 pages |
| — by the detector | 64 |

On this book the shape locator does **three times the work of the model**, and
all 204 of its reads are C clefs the detector cannot see at any confidence.
That is the entire soprano/alto/tenor layer of the book, which previously
defaulted to treble.

The honest headline is the other 80%: **1098 staves still have no clef read**
and carry an inherited clef or a positional default. Clef *reading* is
essentially always right when it happens; clef *coverage* is not solved, and
what limits it is still upstream — the clef outside the cell, or fused into
neighbouring ink.

## What this still does NOT fix

Clef coverage on this book is 20%. Where a cell contains its clef, the locator
reads it and reads it correctly; what remains is upstream. Two limits, both
measured, neither addressed:

### 1. Body text is detected as staves

`staff_detector._ink_profile` counts ink *pixels* per row and requires a row to
clear `MIN_LINE_LENGTH_FRAC` (35% of page width). A row of justified body text
easily clears that on total ink while containing no long run at all, and five
consecutive text baselines have regular enough spacing to pass the 5-line
grouping test. So a paragraph becomes a "staff", with a clef and measures of
its own. Two of Nottebohm p.90's seven staves are text columns; two of p.92's
twelve are.

The natural fix — score rows by longest contiguous run instead of total ink —
was measured and is **wrong**. Across 274 detected staves on eight scores, the
minimum per-line run fraction separates badly: genuine, full-width staves in
Boléro, WTC, La Mer and Handel score as low as 0.018, because heavy notation
ink interrupts the line. Rejecting on line continuity would discard real staves.

What *does* separate cleanly is **staff span versus the page's median span**:

| | span | page median span | x-extent (of page width) |
|---|---|---|---|
| Nottebohm p.92 text "staves" | 215, 216 | 62 | 0.021, 0.015 |
| every genuine staff measured | within ~10% of median | — | 0.147 … 0.908 |

Text baselines sit ~3.5× further apart than staff lines, and the x-extent of the
resulting "staff" is a couple of percent of the page (the longest ink run on a
text row is one word). Either signal rejects the text blocks without touching a
single genuine staff in the corpus.

**Not implemented here.** It is a Phase-1 change, and Phase 1 currently has no
trustworthy regression baseline — `test_pipeline.py`'s staff- and measure-count
assertions already fail in this tree from earlier drift (identically on `main`,
verified). Changing staff detection without a working Phase-1 baseline is how
this project has been bitten before. The measurements above are the input to
doing it properly.

### 2. Some staff-start cells still begin after the clef

The gross form of this is fixed (see the Phase-1 section above) and it is what
took p.31 from 6/12 to 9/12. It has not gone away entirely: on pages laid out
as several short exercise fragments side by side, `_staff_x_extent` can still
land past the clef, and the cell then opens mid-measure with nothing for any
reader to find. This is the largest single contributor to the 80% of staves
with no clef read.

### 3. Dense orchestral headers

The locator abstains on Mahler 5 p.11 — ink-heavy headers, no glyph-sized
cluster it will commit to. The decoupled `--clef-weights` specialist remains the
better route there, and the two compose: the specialist runs first, the locator
only where it stayed silent.
