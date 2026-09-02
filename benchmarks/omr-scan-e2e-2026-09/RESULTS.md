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

The top two are 69% of the corpus and most of that is the **condensation
convention** — 18 reference parts against 12 printed staves, 21 against 14, 38
against 21. §3 measures how much: **23.4%** of the pooled edits, not the 29.6%
the `entire staff insert/delete` bucket alone suggests, with the rest of that
bucket turning out to be reading failure it was hiding.

**Layout is not the problem, and that is the most encouraging line in the
table.** Staff counts are exact on all five pages — 12, 12, 15, 14, 17 — on five
different publishers' scans, including Mahler's page where five one-line
percussion staves sit between the tuba and the strings (five, not four: §9).
Measure counts are exact on three of five, and the two misses are both one
measure and both the same class of bug (§1).

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

## Row 1 is a controlled reproduction of the first run — what is and is not comparable

`benchmarks/omr-first-run-2026-08` reported **0.8706** on Beethoven 5 p.1. Row 1
uses the *same* edition (IMSLP 984073), the *same* page (PDF index 1), the
*same* window (mm. 1–16) and the *same* protocol (CLI defaults, no dossier), so
it is a like-for-like before/after on the pipeline.

**Comparable:** the edition, the page, the measure window, the protocol, the
metric, and the truth. Three separate checks say the truth is the same object:
the trimmer's output and the first run's committed
`truth/beet5-mm1-16.musicxml` both parse to 18 parts, 16 measures and 147 note
objects; scoring the first run's committed *prediction* against each gives
**identical** results — 0.8667, 1664 edits, 1064 truth symbols, same category
breakdown to the edit; and this reference carries no invisible notes, so the
trimmer's one editorial rule does not touch it.

**Not comparable:** the number 0.8706 itself. Re-scoring the first run's own
committed prediction against its own committed truth today gives **0.8667** —
1664 edits over 1064 truth symbols, against the recorded 1723 over 1123. Edits
and truth symbols are both down by exactly **59**, so the change is entirely on
the truth side of a file that has not changed. It is not the trimmer (proved
above); the remaining candidate is the musicdiff / music21 stack in
`.venv-omrned`, which was not pinned when 0.8706 was recorded. **0.8667 is the
baseline this row should be read against**, not 0.8706.

So, on identical inputs:

| | first run (2026-08-31) | row 1 (today) |
|---|--:|--:|
| OMR-NED | 0.8667 | **0.7119** |
| edits | 1664 | 1305 |
| measures found | 13 / 16 | **16 / 16** |
| `wrong note head` | 208 | **14** |
| `wrong note` | 288 | 154 |
| `wrong timesig` | 26 | **0** |
| `entire staff insert/delete` | 513 | 513 |

The meter and barline work of 2026-08-31 and everything since is visible in
every row of that table except the last, which is the condensation floor and
does not move because nothing about the page or the part model changed.

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

Ranked by how clearly the mechanism is established, not by edit count — several
items carry no edit count at all. **The 2026-09-02 condensation measurement (§3)
does not reorder them.** It resizes §3 (29.6% → 23.4%, and from "a floor" to "a
floor with reading failure hiding inside it") and adds §9, which was found while
counting the printed staves that §3 needed. §2 has since been fixed; the note
under it says by what.

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

✅ **Fixed on main after this was measured**, by `6d11a34` and
[FIX_ROUND_2026-09-02.md](FIX_ROUND_2026-09-02.md), which narrows the mechanism
one step (seven parts open G2 and *recover* at m2 in MusicXML; on LilyPond all
fifteen really are treble). Re-scoring the re-exported prediction on
2026-09-02 the Dvořák parts read `G2 G2 G2 F4 G2 G2 G2 C3 F4 F4 G2 G2 C3 F4 F4`
— bassoon, both trombones, timpani, viola, cello and bass now correct. Its raw
score moved **955 → 956 edits** (`wrong clef` 8 → 12, `wrong note` 525 → 517):
the notation is right and the metric is a point worse, which is what a fix that
adds symbols to a symmetric measure looks like. The table at the top of this
file predates it.

### 3. The condensation floor — measured: the convention explains 23.4% of pooled edits, not 29.6%

`entire staff insert/delete` is 2676 pooled edits, 29.6% of the corpus: whole
reference parts with no counterpart, because the print condenses. On Beethoven
it is a single op type, `inspart`, **513 cost over 6 ops** — 18 reference parts
onto 12 printed staves, 39% of that row's edits before a note is read.

**That bucket is an upper bound on what the convention costs, and it overstates
it by nearly a third.** `condensation_arm.py` builds a second ground truth per
row with `music21.Score.partsToVoices`, stacking the reference's parts as
voices on the number of staves the page prints, and re-scores the *same*
predictions against it. Nothing is re-transcribed; no YOLO runs.

**The allocation comes from the page.** On four rows it is `works.json`'s
hand-read `staves` map — which printed staff carries which reference parts, read
off the scan — used as the `voiceAllocation` directly rather than restated, so
the join stays stated once. Mahler had no such map and one was derived for it
from the plate's own margin labels and staff geometry (`condensation
.staves_as_printed`, §9): 15 of its 22 printed staves match a reference part
name verbatim, the **only** staff carrying notes in mm.0–8 is pinned by what the
page prints rather than assumed — the reference's one sounding part is index 17
and the page prints that fanfare on the upper trumpet staff, marked `I.` — and
the seven parts with no printed staff here are doublings and divisi that are
silent across the whole window, so where they land moves no note. That last
claim is priced, not asserted, at the end of this section.

| row | parts → staves | raw NED | raw edits | condensed NED | condensed edits | convention explains |
|---|---|--:|--:|--:|--:|--:|
| Beethoven 984073 | 18 → 12 | 0.7119 | 1305 | 0.6180 | 1100 | 205 (**15.7%**) |
| Beethoven 575951 | 18 → 12 | 0.7479 | 1454 | 0.6330 | 1197 | 257 (**17.7%**) |
| Dvořák 9 | 15 → 15 | 0.5905 | 956 | 0.5905 | 956 | 0 (**0.0%**) |
| Brahms 1 | 21 → 14 | 0.9351 | 3689 | 0.6123 | 2339 | 1350 (**36.6%**) |
| Mahler 5 | 38 → 21 | 0.8149 | 1647 | 0.7497 | 1342 | 305 (**18.5%**) |
| **pooled** | | 0.7966 | 9051 | **0.6361** | 6934 | **2117 (23.4%)** |

⚠️ **The raw column is the benchmark headline and stays that way.** The
condensed column attributes; it does not flatter. Truth symbols fall 6151 →
5689 while predicted symbols are unchanged at 5211, so merging parts moves the
symmetric **denominator** as well as the numerator — the same trap the
resolution arm sprang from the other side. Read the edits: pooled 9051 → 6934.

⚠️ **Both columns are re-measured together against the same prediction bytes**,
whose sha256 is recorded per row in `results-condensation-arm.json`, and the raw
column is re-computed rather than read out of `results.json`. It has to be: the
predictions are gitignored, a parallel workstream re-exported all five of them
mid-measurement, and the raw pooled is 9051 here against the 9050 at the top of
this file entirely because of §2's fix. A ratio between a raw number from one
tree and a condensed number from another is not an attribution.

**Where the edits go is the finding, and it is not where the bucket said.**

| | raw | condensed | Δ |
|---|--:|--:|--:|
| entire staff insert/delete | 2676 | **182** | −2494 |
| entire measure insert/delete | 3540 | 2030 | −1510 |
| wrong note | 2054 | **3696** | +1642 |
| every other note-level bucket | 781 | 1026 | +245 |
| **total** | **9051** | **6934** | **−2117** |

4004 edits leave the two structural buckets and **1887 of them come straight
back as note-level errors** — 47%. Merging the parts does not delete that
content; it re-charges it. Once a condensed staff is *matched* to its printed
counterpart, the second voice's notes stop being an unread part and start being
notes the reader missed, one by one. That half was never convention: it is
reading failure the raw framing had hidden inside a structural bucket. So the
condensation convention is worth **23.4%** of the pooled edit budget, and
`wrong note` — 22.7% of the raw corpus — is **53.3%** of the condensed one.

**Dvořák is the control, and it is an exact no-op.** Its 15-into-15 allocation
asks `partsToVoices` to change nothing, and it changes nothing: the file it
writes differs from the untouched truth **only** in music21's randomly
regenerated instrument ids (0 non-id diff lines over 98 KB), and the score is
identical to the edit — 0.5905, 956 edits, 792 truth symbols, both ways. Note
counts are preserved on every row too (Beethoven 147 → 147, Brahms 482 → 482,
Mahler 27 → 27), so nothing is being merged away. That is what makes the other
four rows' numbers readable at all; without it the arm would be untrustworthy
and this section would say so instead.

⚠️ **What the condensed truth is NOT.** It is not a reconstruction of the
printed page. Two resting parts merged onto one staff keep two stacked whole
rests where the page prints one, and a printed staff the reference has no part
for cannot be created at all (§9). It is the minimal mechanical removal of the
part-count mismatch — enough to price the convention, not a second ground truth
anyone should score against as the headline.

Two further checks, because both were open risks in SCOPING.md:

- **musicdiff aligns parts by POSITION, not by name** (risk 5). `partsToVoices`
  drops `partName`, which would matter if the aligner used it. Restoring the
  twelve printed staff names onto the Beethoven condensed truth and re-scoring
  gives 0.6180 / 1100 edits and a byte-identical category breakdown. The name
  loss is free.
- **Mahler's mapping ambiguity is priced** (risk 4, and see §9). Its allocation
  has three genuinely 50/50 splits between two *printed* staves. Taking the
  other branch of all three gives 1350 edits against 1342 — **eight edits, 0.5%
  of the row's budget, against the 305 the condensation explains**. Recorded as
  `condensation.sensitivity_allocation`; `condensation_arm.py --sensitivity`
  re-runs it.

Still not a defect to fix in the pipeline — printed scores condense; that is
what a printed score is. But **a pooled scan figure is dominated by how much
each edition condenses** — 0.0% of Dvořák's budget against 36.6% of Brahms's —
and per-row reading is mandatory.

### 4. Clefs on Dvořák's Simrock print (see §2 for the export half)

Nine of Dvořák's fifteen staves print a non-treble clef (bass on Fagotti,
Trombone basso, Tympani, Violoncello, Contrabasso; C-clefs on Tromboni and
Viola). The per-measure reader gets them; the summarising `staff.clef` field and
the export do not — **the export half is fixed as of `6d11a34`** (see §2's
note); `staff.clef` is still `'treble'` on all fifteen. Brahms by contrast reads
**14/14 including alto and tenor**, so this is edition-specific, not a general
clef failure.

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

### 9. Mahler's page prints 22 staves, five of them ONE-LINE — 182 edits, and this file said 21

Found while building §3's allocation, which needed the printed staff layout and
therefore had to count it. Two things, and the second corrects this directory.

**A five-line staff detector cannot find a one-line staff, by construction.**
That is the entire residual `entire staff insert/delete` in the condensed
column: 182 edits, all Mahler, exactly the four percussion parts (Becken,
Grosse Trommel, Kleine Trommel, Tamtam) whose printed staves are a single rule.
Every other row goes to zero. It is a real limit rather than a tuning miss —
`staff_detector` searches for five-line groups — and 182 pooled edits prices it
for the first time.

**The page prints a 22nd staff that the reference has no part for.** Between
`Grosse Trommel` and `Kleine Trommel` the Peters plate prints a *third* one-line
staff labelled `Becken / Gr.Trommel } von einem geschlagen` — cymbal and bass
drum struck by one player — with its own 2/2 and its own quarter rest. Counted
by horizontal projection over the music body at 300 dpi: 17 five-line groups,
then **five** evenly spaced single rules 52–53 px apart, and each of the five
one-line margin labels centres on a rule to within 6 px rather than between two
of them (`Pauken`, the sixth label, centres on its five-line staff). `works.json`
previously recorded four one-line staves and a 21-staff page; it is corrected,
with the evidence, in that row's `page.n_staves_note` and `condensation`.

The consequence for §3 is that the condensed Mahler truth has **21 parts against
22 printed staves** and cannot represent that staff at all. It is also why
Mahler's map lives in `condensation.staves_as_printed` and not in `staves`: a
`staves` map is joined to the prediction's parts *positionally* by the note
recall arm, and five of these staves are invisible to the detector, so that join
would be wrong from staff 13 down.

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
| `results-condensation-arm.json` | yes | §3's raw-vs-condensed arm, with the sha256 of every file it scored |
| `scan_eval.py` | yes | the runner |
| `condensation_arm.py` | yes | §3: re-scores the existing predictions against an as-printed truth |
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
- **The pooled 0.7960 is dominated by condensation**, which varies per edition —
  measured at **23.4% of the pooled edit budget**, from 0.0% on Dvořák to 36.6%
  on Brahms (§3). Track the rows; the pooled number is a headline, not a
  diagnostic.
- **Mahler has no hand-read staff map in `staves`**, so it contributes to
  OMR-NED but not to the note-recall table. §3 needed the printed layout and
  established it — 17 five-line staves plus **five** one-line percussion staves
  (§9) — but it lives in `condensation.staves_as_printed`, because the note
  recall arm joins `staves` to the prediction positionally and five of these
  staves are ones the detector cannot see. Turning it into a note-recall map
  means teaching `scan_eval.note_recall` about undetectable staves first.
- **This benchmark writes nothing into
  `benchmarks/omr-ned-2026-08/current-accuracy.json` or CLAUDE.md's
  `accuracy:begin name=headline` block.** Those are defined as the engraved
  orchestral figure. If the scan figure ever needs a present-tense home it should
  get its own record and its own marker in `accuracy_record._BLOCKS`, following
  that design rather than fighting it.
