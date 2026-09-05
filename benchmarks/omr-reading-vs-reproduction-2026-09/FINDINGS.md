# Reading and reproduction, measured apart

*2026-09-04. Sean asked whether we are testing the pipeline's ability to read a
page or its ability to reproduce one, and whether there is a way to know exactly
what is on a page. There is, for pages we render, and it costs nothing.*

Every accuracy figure this project reports is taken at the far end: our exported
MusicXML against a truth MusicXML. That fuses two questions, which is why nine
"detected, then dropped on the way out" bugs have had to be found by forensics —
in OMR-NED a signal read perfectly and lost in the exporter is indistinguishable
from one never read.

|  | what it asks | tool |
|---|---|---|
| **stage 1 — reading** | did we see the ink, and call it the right kind | `tools/omr/page_truth.py` + `score_reading.py` |
| **stage 2 — translation** | did what we saw reach the file | `tools/omr/score_translation.py` |
| (existing) | does the file say what the truth says | `tools/omr/omr_ned.py` |

---

## 1. Exact page truth, for free

Verovio renders MusicXML directly and, with `svgBoundingBoxes`, emits a `<rect>`
per notation object in the same frame as the glyph it drew, plus every glyph's
SMuFL codepoint. Render a known-correct MusicXML and you have the image and an
exact inventory of its ink from one act. No labeling.

⚠️ **A PAGE TRUTH IS NOT AN ENCODING TRUTH, and the gap is the whole point.**
On the Brahms fixture, against the very file it was rendered from:

| | on the page | in the encoding |
|---|--:|--:|
| dynamics | 19 `dynamicForte` glyphs | 19 `<dynamics>` |
| G clefs | **28** glyphs | **14** `<sign>G</sign>` |
| slurs | **82** arcs | **164** `<slur>` tags |

The clefs differ because a clef is *printed* at every system and *declared*
once; the slurs because MusicXML writes a start and a stop where the engraver
draws one arc. A reader sees 28 clefs and 82 arcs, and that is what a
recognition score must be taken against.

---

## 2. Stage 1 — how much of the page we see

Eleven engraved works, page 1 of each, 3446 printed symbols.

| work | symbols | dets | prec | rec | **F1** |
|---|--:|--:|--:|--:|--:|
| mahler-sym5-mvt1 | 355 | 347 | 0.991 | 0.969 | **0.980** |
| bruckner-sym5-mvt1 | 242 | 243 | 0.951 | 0.955 | 0.953 |
| beethoven-sym5-mvt1 | 307 | 316 | 0.930 | 0.958 | 0.944 |
| dvorak-sym9-mvt4 | 205 | 212 | 0.920 | 0.951 | 0.935 |
| beethoven-sym3-mvt1 | 373 | 347 | 0.965 | 0.898 | 0.931 |
| mozart-sym41-mvt1 | 303 | 314 | 0.904 | 0.937 | 0.921 |
| tchaikovsky-sym6-mvt2 | 231 | 240 | 0.896 | 0.931 | 0.913 |
| brahms-sym4-mvt1 | 314 | 324 | 0.846 | 0.873 | 0.859 |
| brahms-sym1-mvt1 | 675 | 699 | 0.840 | 0.870 | 0.854 |
| mozart-sym40-mvt1 | 181 | 174 | 0.862 | 0.829 | 0.845 |
| tchaikovsky-sym4-mvt2 | 260 | 345 | 0.690 | 0.915 | 0.787 |
| **POOLED** | **3446** | **3561** | **0.884** | **0.913** | **0.898** |

### And the per-family breakdown is the answer to "where is the error"

| family | truth | pred | match | prec | rec | F1 | where the misses went |
|---|--:|--:|--:|--:|--:|--:|---|
| notehead | 856 | 858 | 856 | 0.998 | 1.000 | **0.999** | |
| rest | 929 | 941 | 928 | 0.986 | 0.999 | 0.993 | |
| time_signature_digit | 358 | 358 | 357 | 0.997 | 0.997 | 0.997 | |
| flag | 118 | 120 | 118 | 0.983 | 1.000 | 0.992 | |
| clef | 226 | 230 | 221 | 0.961 | 0.978 | 0.969 | |
| augmentation_dot | 102 | 108 | 101 | 0.935 | 0.990 | 0.962 | |
| key_accidental | 328 | 454 | 328 | 0.722 | 1.000 | 0.839 | |
| beam *(CV)* | 110 | 182 | 110 | 0.604 | 1.000 | 0.753 | |
| **dynamic_letter** | 114 | 216 | 91 | **0.421** | 0.798 | 0.552 | `-` 23 |
| **slur** | 137 | 145 | 73 | 0.503 | 0.533 | 0.518 | `-` 40, beam 24 |
| **accidental** | 226 | 60 | 58 | 0.967 | **0.257** | 0.406 | `-` 168 |
| **tie** | 52 | 71 | 16 | 0.225 | 0.308 | 0.260 | `-` 34, slur 2 |
| barline *(CV)* | 45 | 0 | 0 | — | — | — | `-` 45 |

**Noteheads are read essentially perfectly — 856 of 856, precision 0.998.** So
whatever OMR-NED's 0.1306 is made of on engraved pages, it is not a failure to
see notes. The reading error lives in four places: **inline accidentals**
(recall 0.257 — 168 printed with *nothing* detected there), **ties** (0.260),
**slurs** (0.518), and **dynamic letters**, whose problem is the opposite —
precision 0.421, 216 detections for 114 printed, which is the over-emission the
dynamics work measured from the other end.

⚠️ **`accidental` and `key_accidental` are the same glyph in two roles**, and
the detector splits them differently from the engraver: on Brahms p1 it finds 52
key-class and 41 inline-class where the page prints 51 and 82. Its key
signatures are complete (recall 1.000) and its inline accidentals are not. The
confusion column rules out the easy explanation — the 168 misses have `-`, i.e.
no detection of *any* family within tolerance, so they were not merely
misfiled.

⚠️ **`slur` loses 24 arcs to `beam`**, which is the only real class confusion in
the table, and `barline` is 0 by construction: it is CV-detected and
cell-relative, so it never appears in page coordinates. Both are flagged rather
than counted against the pooled figure.

---

## 3. Stage 2 — what we saw and did not write

Pooled over the same eleven works, on the pipeline's own fixtures.

| family | element | detected | exported | truth | verdict |
|---|---|--:|--:|--:|---|
| **hairpin** | `wedge` | **9** | **0** | 17 | **READ AND DROPPED** |
| **fermata** | `fermata` | 36 | 35 | 36 | **READ AND LOST — one** |
| accidental | `accidental` | 118 | 112 | 115 | 3 short |
| augmentation_dot | `dot` | 158 | 149 | 149 | matches the truth |
| dynamic_letter | `dynamics` | 221 | 169 | 142 | over-emitted |
| articulation | `articulations` | 218 | 182 | 237 | short (unit differs) |
| slur | `slur` | 306 | 398 | 478 | short (unit differs) |
| tie | `tied` | 171 | 159 | 161 | short (unit differs) |
| beam | `beam` | 366 | 822 | 839 | short (unit differs) |
| tuplet | `tuplet` | 51 | 88 | 94 | short (unit differs) |

**The ninth export gap is now priced.** `wedge` has sat open in
`export_coverage.KNOWN_GAPS` as "partial detection, so unlike the eight above
this is not purely an export fix, and closing it cannot be priced from this
inventory alone". It can now: **9 hairpins are read across three works and
every one of them is discarded** — Mahler 5 (4 of 6), Tchaikovsky 6 (3 of 6),
Brahms 4 (2 of 5). Half a reading problem and half an export problem, and the
export half is free.

**And a new one: a fermata read and lost.** Beethoven 5 detects 36 fermatas,
its truth has 36, and 35 reach the file. One mark, found by arithmetic that no
existing check performs — `export_coverage` fires only on the categorical case
(truth has some, we emit zero) and 35-of-36 is invisible to it.

---

## 4. ⚠️ How to read these two together — and how not to

**The stages read different images, on purpose.** Stage 1 needs a page whose ink
is known exactly, which means one we render with Verovio. Stage 2 needs the
pipeline's numbers on the pages the headline benchmark uses, which are LilyPond
renders of the same excerpts, paginated differently. **Their per-family counts
are therefore not comparable to each other** — stage 1's 226 inline accidentals
and stage 2's 115 `<accidental>` elements are different music. Compare each
stage's columns *within* itself.

**Neither says anything about scans.** Renderer truth exists only where we make
the page, and there is no public symbol-level ground truth for real printed
scans to borrow — DeepScoresV2 is digitally rendered, MUSCIMA++ is handwritten.
This separates reading from reproduction on engraved input and leaves scan
robustness exactly where it was.

**The score is not an artefact of the render's scale.** These pages carry ~22
px per staff space at 300 dpi, well under a 600 dpi scan's 40-60, so the whole
figure could have been a resolution result. Re-rendered and re-read at 600 dpi
(45 px per space): Brahms 1 **0.854 → 0.868**, Tchaikovsky 4 **0.787 → 0.789**.
The best and the worst work in the set both move by less than the gap between
any two works, so the ranking and the pooled number stand.

**The reading score is a plateau in its tolerance, not a point.** Matching is on
centres, not IoU — the detector's boxes are learned and the engraver's are
exact, so demanding overlap would measure box style. Pooled F1 over the Brahms
page moves 0.846 → 0.876 across 0.25 → 1.5 staff spaces of tolerance, so the
figure is not an artefact of where the line was drawn.

---

## 5. Two frame errors this found in itself

Both were caught the same way, and it is the tell worth remembering: **the
symbol COUNTS agreed almost exactly while nothing matched positionally.** That
is the signature of a coordinate error and never of a recognition result.

1. **The page margin.** Verovio wraps the page in `<g class="page-margin"
   transform="translate(500, 500)">` and everything below is inside it. Missing
   that put the entire truth 62.5 px off at 300 dpi against a 22.5 px staff
   space — noteheads counted 259 against 259 and matched **zero** at every
   tolerance.
2. **The glyph anchor is not the glyph's centre.** SMuFL puts a glyph's origin
   where the notation needs it — a notehead's on its own middle, a flat's down
   at the staff position it alters. Synthesising a square box around the anchor
   put the key-signature truth 0.59 staff spaces high and scored a correctly
   read signature at **F1 0.078**; calibrating each glyph's box from Verovio's
   own single-glyph rects took it to **0.990**.

A third was avoided by checking rather than assuming: reading glyph extents off
the font outlines in `<defs>` is wrong, because those paths use **relative**
curve commands, and a min/max over their numbers put noteheads 0.66 staff spaces
right of Verovio's own rect for the same glyph. The `note` rects are a free
check on any method here, and they caught it.

The coordinate chain is verified end to end rather than assumed: librsvg maps
CSS px to PDF points at 72/96 and a point rasterises at dpi/72, so image px =
css px × dpi/96 — checked at both 300 and 600 dpi (800×1767 css → 600.00×1325.25
pt → 2500×5522 and 5000×11044 px, all exact).

---

## 6. What to do with it

- **Close the hairpin export half.** 9 read, 0 written, and the reading half
  (9 of 17) is a separate, later problem.
- **Inline accidentals are the largest reading gap** on engraved pages: 168
  printed with nothing detected. That is a detector question, and it is the
  first time it has been separated from the accidentals the exporter derives
  correctly anyway.
- **Ties and slurs are the second.** Not a labelling confusion — the misses have
  nothing there.
- **Re-run after any detector change.** These two numbers move independently,
  which is the entire reason for having both.

```bash
python3 benchmarks/omr-reading-vs-reproduction-2026-09/run.py \
    --fixtures <dir with *.musicxml + *.omr.json + *.omr.musicxml> \
    --work-dir <scratch> --out results.json
```
