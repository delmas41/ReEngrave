# The scan domain, measured (2026-09-01)

Five pages of real scans, five publishers' worth of print between them, run at
the pipeline's own defaults with **no dossier**, scored against each movement's
reference MusicXML trimmed to the measures the page actually holds.

**Pooled OMR-NED 0.7960** — 9050 edits over 6151 truth + 5218 predicted symbols.

For scale, this repository's engraved orchestral benchmark is **0.1364**. That
comparison is the point of the whole exercise and it is not a like-for-like one;
see *Engraved against scanned* below for what separates the two numbers besides
the paper.

```bash
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --list
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py            # all five rows
python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --score-only
```

## The table

| row | edition | window | staves | measures | OMR-NED | edits | truth | pred |
|---|---|---|---|---|--:|--:|--:|--:|
| Beethoven 5 | Litolff-family, IMSLP 984073, 2897×3813 ccitt | 1–16 | 12/12 | **16/16** | **0.7119** | 1305 | 1064 | 769 |
| Beethoven 5 | *same plates*, IMSLP 575951, 5409×7207 jbig2 + text layer | 1–16 | 12/12 | **16/16** | 0.7479 | 1454 | 1064 | 880 |
| Dvořák 9 | Simrock 1894, IMSLP 405834, 5088×6976 jbig2 | 1–8 | 15/15 | 9/8 | **0.5873** | 955 | 792 | 834 |
| Brahms 1 | Breitkopf *Sämtliche Werke*, IMSLP 317803, ~5276×6940 ccitt | 1–7 | 14/14 | 8/7 | 0.9351 | 3689 | 2083 | 1862 |
| Mahler 5 | Edition Peters 3087b, local scan, 4385×5857 jbig2 | 0–8 | 17/17 | **9/9** | 0.8149 | 1647 | 1148 | 873 |

Pooled edit distribution:

| category | edits | share |
|---|--:|--:|
| entire measure insert/delete | 3538 | 39.1% |
| entire staff insert/delete | 2676 | 29.6% |
| wrong note | 2062 | 22.8% |
| wrong direction | 195 | 2.2% |
| wrong keysig | 175 | 1.9% |
| wrong note head | 118 | 1.3% |

**Layout is not the problem, and that is the most encouraging line in the
table.** Staff counts are exact on all five pages — 12, 12, 15, 14, 17 — on five
different publishers' scans, including Mahler's page where four one-line
percussion staves sit between the tuba and the strings. Measure counts are exact
on three of five, and the two misses are both one measure and both the same
class of bug (§1).

## Note recall, which disagrees with OMR-NED and is right to

Multiset pitch comparison per printed staff, carried over from
`eval_first_run.py`. Mahler has no hand-read staff map yet, so it reports
OMR-NED only.

| row | exact R | step R | +duration R | exact P |
|---|--:|--:|--:|--:|
| Beethoven 984073 | 0.599 | 0.701 | 0.388 | 0.657 |
| Beethoven 575951 | **0.728** | **0.796** | **0.463** | 0.525 |
| Dvořák 9 | **0.844** | 0.854 | 0.625 | 0.600 |
| Brahms 1 | 0.743 | 0.830 | 0.576 | 0.644 |

Two things fall out. **Duration is the weakest row everywhere**, 0.39–0.63
against 0.70–0.85 for position — the invisible-half-notehead diagnosis
(`omr-first-run-2026-08/DURATIONS.md`) is alive in every one of these pages and
is not a Beethoven peculiarity. And **the row with the best note recall (Dvořák,
0.844) is not the row with the best OMR-NED**, which is the next section.

---

## The same plates, twice: 984073 against 575951

The two Beethoven scans are the same engraving. Normalising each page's 17
Flauti barlines to its own system width, they agree to a maximum of **0.0014** —
0.14% of the system (VERIFICATION.md). So the window, the notes and the layout
are held constant and only the scan varies: 2897×3813 ccitt with no text layer
against 5409×7207 jbig2 with one.

A third arm renders the high-res file at **321 dpi**, chosen so its raster
matches the low-res one pixel for pixel (600 × 2897/5409). It is not part of the
protocol; it exists to test a mechanism.

| arm | raster | noteheads | exact R | exact P | edits | pred syms | OMR-NED |
|---|---|--:|--:|--:|--:|--:|--:|
| 984073 @600 | 2897×3813 | 134 | 0.599 | 0.657 | 1305 | 769 | **0.7119** |
| 575951 @321 | 2894×3857 | 165 | 0.612 | 0.545 | 1406 | 736 | 0.7811 |
| 575951 @600 | 5409×7209 | 204 | **0.728** | 0.525 | 1454 | 880 | 0.7479 |

**Resolution explains the recall difference, and the experiment is what shows
it.** Downscaling the high-res scan to the low-res scan's pixel size drops its
exact recall from 0.728 to 0.612 — essentially the low-res scan's 0.599. The
advantage is a genuine resolution effect and it is reproduced by construction,
not inferred.

⚠️ **OMR-NED ranks these three in an order that has little to do with reading
them.** It puts the low-res scan first and the matched-resolution arm last,
while note recall puts the high-res scan far ahead of the other two. The
matched-resolution arm makes **fewer** edits than the full-resolution one — 1406
against 1454 — and scores **worse**, 0.7811 against 0.7479, because it emits 736
predicted symbols against 880 and the denominator moved further than the
numerator.

This is the symmetry trap CLAUDE.md warns about, seen from the other side: there
it was a ratio *falling* while `omr_ed` rose (dilution); here it is a ratio
*rising* while `omr_ed` falls. **On the scan domain the two metrics disagree
about which reading is better, and both are right about different things** — the
pipeline reads more of the high-res page and invents more on it. Report them
together on this corpus; a single scalar will mislead.

⚠️ It is also **not a pure resolution A/B** even at 600 dpi: 575951 carries a
text layer, which turns on the free `staff_labels` rung and feeds part naming and
contextual clef filling. Its key-signature reading is worse (6/12 correct against
9/12), which is not something resolution would predict.

---

## Engraved against scanned, on identical music

Two rows are the same works as the engraved orchestral benchmark, so the domain
gap can be read directly rather than inferred from a pooled figure.

| work | engraved | scanned | ratio |
|---|--:|--:|--:|
| Beethoven 5 mvt1 | 0.1649 (205 edits, mm.1–8) | **0.7119** (1305, mm.1–16) | 4.3× |
| Brahms 1 mvt1 | 0.1709 (675 edits, mm.1–8) | **0.9351** (3689, mm.1–7) | 5.5× |
| Mahler 5 mvt1 | 0.0455 (86 edits, mm.1–8) | **0.8149** (1647, mm.0–8) | 17.9× |

Engraved figures from `benchmarks/omr-ned-2026-08/current-accuracy.json` at
commit `68be549`.

⚠️ **Three things differ besides the paper, and the third is large.**

1. The excerpts are not the same measures (the engraved benchmark shrinks its
   window until LilyPond gives one page). OMR-NED is a ratio, so this is a
   second-order effect, but it is not zero.
2. The engraved input is rendered from the very file it is scored against, so
   its part structure matches the truth by construction. Every scanned row
   except Dvořák condenses — 18 reference parts onto 12 printed staves, 21 onto
   14, 38 onto 17 — and that alone is 29.6% of the pooled edits (§2).
3. **The engraved baseline runs WITH a dossier and these rows run without one.**
   `orchestral_eval` defaults to `use_dossier=True`; this benchmark refuses it,
   because `data/dossiers/` is generated from the same MusicXML used here as
   truth. So the ratios above are *domain + part model + external truth*, not
   domain alone.

**Mahler is the sharpest reading of the domain gap** — 0.0455 engraved against
0.8149 scanned, on music the pipeline transcribes almost perfectly when it is
printed cleanly. Nothing about the recognition changed; the page did.

---

## Ranked scan-side failures

Measuring, not fixing. Each item has the evidence that found it; pipeline code
was not touched.

### 1. System furniture is read as a measure — 2 of 5 rows

The single most mechanical bug here, and it appears at both ends of a system.

**Dvořák, left edge.** Measure 0 spans x 876–932, **56 px wide** — 2.2 staff
spaces, narrower than a notehead and stem — on a page whose real measures are
299–731 px. Its only detection is a **`brace` at confidence 0.33**. The system's
initial rule and the string group's curly brace are read as two barlines, and
all 15 staves emit 9 measures where the page prints 8.

**Brahms, right edge.** Measure 7 spans x 5388–5501, **113 px**, and contains
exactly one detection: **`timeSig9`**. That is the cautionary 9/8 printed after
the final barline; the system-end rule and the courtesy meter's own rule bound a
measure that holds nothing but a digit.

Both were cases this benchmark's own ground-truth probe had to handle
explicitly, and its constants are recorded there (`probe_page_measures.py`,
`BRACKET_MERGE_SPACES`).

⚠️ **Width alone is not a sufficient test, and I checked before claiming it
was.** Measured over the five pages, genuine measures run **4.2 to 28.7 staff
spaces** — the 4.2 is a compressed rest bar on Beethoven 5 p.1 — against 2.2 and
3.5 for the two spurious cells. That is a 0.7-space gap on a five-page corpus,
which is a threshold to tune, not a cliff to sit on.

**Content is the sound discriminator.** Both spurious cells contain exactly
**one** detection and it is structural furniture — a `brace` at conf 0.33, a
lone `timeSig9` — never a notehead or a rest. A genuine measure on even a fully
tacet staff contains its whole-bar rest. "A cell whose only content is a brace
is not a measure" needs no threshold at all.

### 2. A leading furniture-measure poisons the whole part's exported clef

The compounding half of §1, and worth more than the extra measure itself.

On Dvořák the **per-measure** clefs are read correctly from measure 1 onward —
Fagotti `['treble','bass','bass','bass']`, Viola `['treble','alto','alto',…]`,
Violoncello and Contrabasso `['treble','bass','bass',…]`. But
`export.to_musicxml` takes each part's `<clef>` from its **first** measure, and
the first measure is the 56-px brace cell, so **all fifteen parts export as G2**:
bassoon, both trombones, timpani, viola, cello and contrabass included.

The pitches are right — exact recall on this row is 0.844, the best in the table
— so the exported file is musically correct and notationally mislabelled on nine
of fifteen staves. Brahms, whose spurious measure is at the *end*, exports all
fourteen clefs correctly including an alto and a tenor. That asymmetry is the
proof of the mechanism.

Evidence: `fixtures/dvorak-*.omr.json` staff `measures[i].clef` against
`<clef>` in `fixtures/dvorak-*.omr.musicxml`.

### 3. The condensation floor — 29.6% of all edits, and it is not a bug

`entire staff insert/delete` is 2676 pooled edits. On Beethoven it is a single
op type, `inspart`, **513 cost over 6 ops**: six whole reference parts with no
counterpart, because the print condenses 18 parts onto 12 staves. That one
structural fact is 39% of that row's edits before a single note is read.

**Dvořák is the control that proves it.** It is the only work in the library
whose printed staff count equals its reference part count, and its category
breakdown has no `entire staff insert/delete` in the top six at all — while
`wrong note` rises to **55%** of its edits. Remove the part-model penalty and
the metric starts measuring the reading. That is exactly why the row was chosen,
and it is the reason Dvořák's 0.5873 is the most informative number in the table.

Not a defect to fix in the pipeline — printed scores condense; that is what a
printed score is. But it means **a pooled scan figure is dominated by how much
each edition condenses**, and per-row reading is mandatory.

### 4. Clefs on Dvořák's Simrock print (see §2 for the export half)

Nine of Dvořák's fifteen staves print a non-treble clef (bass on Fagotti,
Trombone basso, Tympani, Violoncello, Contrabasso; C-clefs on Tromboni and
Viola). The per-measure reader gets them; the summarising `staff.clef` field and
the export do not. Brahms by contrast reads **14/14 including alto and tenor**,
so this is edition-specific, not a general clef failure.

### 5. The margin-label crop clips the first characters of a label

Nine rejected labels across three rows, and they share a shape:

| read | printed |
|---|---|
| `ken in C u. G` | **Pau**ken in C u.G |
| `larinetten in B` | 2 K**larinetten in B** |
| `competen in C` | 2 Trom**peten in C** |
| `contrafagott` | **K**ontrafagott |
| `Carinetti in B.` | C**l**arinetti in B. |
| `Compani in C.G.` | **Tim**pani in C.G. |
| `Yiolino II.` | **V**iolino II. |
| `Base Trommel` / `line Trommel` | **Grosse** Trommel / K**leine Trommel** |

Most are missing a *prefix*, which is a crop-window symptom rather than an OCR
one — the label crop starts too far right. The lexicon then rejects the lot, and
each rejection costs a staff its identity. Two further notes: `Yiolino II.` and
`Carinetti in B.` are single-character errors that a fuzzy match would recover,
and Surya renders stacked numerals as **LaTeX** (`in C \frac{1}{2}`,
`in Es \frac{3}{4}`), which no lexicon written for printed strings will match.

### 6. `Basso` resolves to "Bass voice" — and the mechanism that should stop it never ran

Beethoven 5's bottom staff exports as **"Bass voice"**, a singer, on the most
famous orchestral page in the repertoire.

This is *not* a lexicon gap. `instruments.py` already lists `basso` in
`AMBIGUOUS_ALIASES` as `("Bass voice", "Contrabass")`, with a comment saying
position settles it — *"the label sits directly below the cellos, where no voice
belongs"* — and naming Mozart 41 and Mahler 5 as the cases it was built for.
Beethoven 5 p.1 is that exact shape, and the run reports
**`ambiguous_labels_resolved: 0`**. The resolver did not fire.

Evidence: `fixtures/beethoven-sym5-mvt1-984073-p1.omr.json`, `contextual`
block (`labelled_staves: 10`, `label_tiers: {surya: 12}`,
`instruments_from_score_order: 2`, `ambiguous_labels_resolved: 0`).

### 7. Key signatures on scans: 9/12 and 6/12 on the same printed page

Against the hand-read truth `[-3,-3,-1,-3,0,0,0,-3,-3,-3,-3,-3]`, the low-res
Beethoven scan reads **9/12** and the high-res one **6/12** — the same twelve
printed signatures, two scans of one plate. `wrong keysig` is 175 pooled edits,
small in the totals but it is what puts 17 points between `step` recall and
`exact` recall on these pages.

### 8. The reference library's Mahler pickup carries 20 invisible notes

Not a pipeline bug — a **truth** bug, and it would have been charged to the
pipeline. `mahler--symphony-5--mvt1--gradus.mxl` measure 0 has a hidden quarter
(`style.hideObjectOnPrint`) in a second voice on every staff but the solo
trumpet, beside the visible rest the page prints. The trimmer drops them.

⚠️ **The engraved benchmark has been silently stepping over this**:
`orchestral_eval` excerpts from measure 1 by default, so it never renders m0.
Anyone extending it to include a pickup will meet these twenty notes.

---

## What is in this directory

| file | committed | what |
|---|:--:|---|
| `works.json` | yes | the per-row windows, provenance and hand-read staff maps |
| `SCOPING.md` | yes | how the six candidates were chosen from 27 paired works |
| `VERIFICATION.md` | yes | how each window was proved, and what one of them cost |
| `RESULTS.md` | yes | this file |
| `results.json` | yes | the table behind it |
| `results-resolution-arm.json` | yes | the 321-dpi side arm |
| `scan_eval.py` | yes | the runner |
| `trim_reference.py` | yes | venv-side trimmer (music21 10.5) |
| `verify_window.py` | yes | the content cross-check |
| `probe_page_measures.py` | yes | the ink cross-check |
| `fixtures/` | **no** | trimmed truth, transcriptions, exports — regenerable |

## Caveats worth carrying

- **Six rows were scoped; five ran.** Bach Brandenburg 3 is recorded and dropped
  with its reason (a tutti page with no tacet staff for the probe to count on,
  and a second system that needs counting by hand). It is the only work whose
  reference numbers the pickup 1, so the print runs one *behind* the file — the
  reason to finish it later.
- **The pooled 0.7960 is dominated by condensation**, which varies per edition.
  Track the rows; the pooled number is a headline, not a diagnostic.
- **Mahler has no hand-read staff map**, so it contributes to OMR-NED but not to
  the note-recall table. Its 17 five-line staves plus four one-line percussion
  staves make that map more work than the others.
- **This benchmark writes nothing into
  `benchmarks/omr-ned-2026-08/current-accuracy.json` or CLAUDE.md's
  `accuracy:begin name=headline` block.** Those are defined as the engraved
  orchestral figure. If the scan figure ever needs a present-tense home it should
  get its own record and its own marker in `accuracy_record._BLOCKS`, following
  that design rather than fighting it.
