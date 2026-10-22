# A scan-domain tracking table — scoping (2026-09-01)

**Nothing here has been run.** This is the design pass: which works can be
measured, which six to start with, how the reference gets trimmed to the window
a page actually covers, and what the runner should look like. No pipeline code
was touched and no YOLO inference was run — every number below comes from
`pdfinfo`/`pdfimages`, from rendering pages with PyMuPDF and reading them, or
from parsing the reference MusicXML.

## Why

The engraved orchestral benchmark sits at pooled OMR-NED **0.1364**
(`benchmarks/omr-orchestral-e2e/`, via `orchestral_eval`). It renders a Gradus
MusicXML through LilyPond and scores the transcription against the file it
rendered from, so a failure there is a failure of recognition on dense music and
cannot be blamed on print quality — deliberately.

The one real-scan measurement this repository has ever taken is Beethoven 5 p.1
at **0.8706** (`benchmarks/omr-first-run-2026-08/FINDINGS.md`). One page, one
work, and explicitly *not* a tracking number. Sean's actual input is scanned
IMSLP PDFs. So the scan domain is where the pipeline is used and the domain
about which almost nothing is measured.

This benchmark turns it into a per-work table so scan-side systematic bugs can
be found and fixes priced.

### Protocol rules inherited, not re-decided

- **Defaults, and NO `--dossier`.** `data/dossiers/` is generated from the same
  Gradus MusicXML used here as truth, so seeding hands the run its own answer
  key. (`--dossier` may be run as a *separate reported arm*, never as the
  headline.)
- **Page structure is established without the pipeline.** The thing under test
  may not define its own truth.
- **The page is the truth, not the file.** Where the printed edition and the
  reference disagree about a clef or a key signature, the page wins — a correct
  reading must not be scored wrong. (Beethoven 5: Breitkopf-family print gives
  Trombe and Timpani no key signature; the Gradus file gives them three flats.)
- ⚠️ **Agreement across staves is not a check when the error is shared.** The
  first run scored page 1 against *seventeen* measures; it has sixteen. Five
  tacet staves independently agreed on 17, because a 2/4's digits align into a
  full-height column six pixels wide — exactly a barline's width — and all five
  print the same time signature. What separates them is that a barline
  *continues past the staff into the gap* (1.00 reach) and a meter does not
  (0.05). Every count in this document is a **first-pass visual read** and is
  marked as needing build-phase re-verification for exactly this reason.

---

## 1. The pairs: 27 works have both an edition PDF and reference MusicXML

`data/score-library/catalog.json` holds 1980 entries — 235 editions across 228
`work_id`s and 1745 reference encodings across 965. The join is on `work_id`
(genre + number, not title). **27 works have both.** All 31 edition PDFs and all
reference files for those 27 were verified present on disk under
`/Users/seanjohnson/Desktop/ReEngrave/library/`;
`tools.library.score_library.library_root()` resolves to the main checkout from
inside this worktree (`MACHINE_ROOT/library`), so nothing needs copying.

Resolution/encoding read from `pdfimages -list` on page 3 of each file (page 1
is often a cover with a different image); page count and text layer from the
catalog.

| work_id | imslp | pgs | text | page-3 image | ppi | reference movements |
|---|---|--:|:--:|---|--:|---|
| bach--concerto-3 (Brandenburg 3) | 468678 | 24 | no | 2285×3274 jbig2 | 300 | mvt1,2,3 |
| bach--concerto-4 (Brandenburg 4) | 457279 | 42 | no | 4862×6460 ccitt | 600 | mvt1,2,3 |
| bach--das-wohltemperierte-klavier-i | 932182 | 115 | yes | *born-digital typeset* | — | bwv846 only |
| beethoven--symphony-1 | 74 | 43 | yes | 5425×7219 jbig2 | 600 | mvt1–4 |
| beethoven--symphony-2 | 503997 | 61 | yes | 5425×7219 jbig2 | 600 | mvt1–4 |
| beethoven--symphony-3 | 504077 | 89 | yes | 5425×7219 jbig2 | 600 | mvt1–4 |
| beethoven--symphony-4 | 504078 | 73 | yes | 5425×7219 jbig2 | 600 | mvt1–4 |
| **beethoven--symphony-5** | **984073** | 88 | no | **2897×3813 ccitt** | 600 | mvt1–4 (+piano arr.) |
| **beethoven--symphony-5** | **575951** | 87 | yes | **5409×7207 jbig2** | 599 | same |
| beethoven--symphony-6 | 504082 | 79 | yes | 5433×7225 jbig2 | 600 | mvt1–5 |
| beethoven--symphony-7 | 504084 | 89 | yes | 5464×7248 jbig2 | 600 | mvt1–4 |
| beethoven--symphony-8 | 504091 | 63 | yes | 5456×7242 jbig2 | 600 | mvt1–4 |
| beethoven--symphony-9 | 516488 | 189 | yes | 5425×7219 jbig2 | 600 | mvt1–4 |
| brahms--ein-deutsches-requiem | 317461 | 190 | no | 3108×3812 ccitt | 600 | 1 movement only |
| **brahms--symphony-1** | **317803** | 86 | no | **5276×6940 ccitt** | 531–535 | mvt1–4 |
| brahms--symphony-1 | 516790 | 86 | yes | 2851×3598 jbig2 | 300 | mvt1–4 |
| brahms--symphony-2 | 23103 | 73 | no | **950×1128 JPEG colour** | 400 | mvt1–4 |
| brahms--symphony-3 | 317593 | 86 | no | 4960×7015 ccitt | 600 | mvt1–4 |
| brahms--symphony-4 | 317596 | 99 | no | 4960×7015 ccitt | 600 | mvt1–4 |
| bruckner--symphony-5 | 518282 | 180 | no | 2381×3189 ccitt | 300 | mvt1–4 (+Trio) |
| **dvorak--symphony-9** | **405834** | 80 | no | **5088×6976 jbig2** | 601/600 | mvt1,3,4 (+full) |
| holst--the-planets | 1014401 | 190 | no | 3516×5157 ccitt *stencil* | 600 | mvt1–7 (+full) |
| **mahler--symphony-5** | *local* | 245 | no | **4385×5857 jbig2** | 600 | mvt1,2,3 |
| mozart--symphony-40 | 984555 | 49 | no | 6897×8528 ccitt | **1200** | mvt1–4 |
| mozart--symphony-41 | 73 | 56 | yes | 2300×3171 ccitt | ~320 | mvt1–4 (+full) |
| **mozart--symphony-41** | **984556** | 56 | no | 6897×8528 ccitt | **1200** | mvt1–4 (+full) |
| ravel--bolero | 421137 | 41 | yes | *born-digital typeset* | — | 1 (single-movement work) |
| tchaikovsky--1812-overture | 23744 | 73 | no | 2164×3142 ccitt | ~285 | 1 (single-movement work) |
| tchaikovsky--symphony-4 | 377460 | 226 | no | 4480×6342 ccitt | 600 | mvt1,2,4 |
| tchaikovsky--symphony-6 | 504312 | 159 | yes | 5718×7210 jbig2 | 600 | mvt1,2,3 (+full) |
| tchaikovsky--symphony-6 | 922722 | 224 | yes | 1685×2467 **JPX rgb + jbig2 smask** | 300 | same |

### How you tell which movement a reference file covers

The filename is `composer--work--movement--source.ext`, and the movement field
is the catalog's `variant`. Two tiers of trust:

- `source: gradus` orchestral files use `mvtN` — reliable, and that is where
  every candidate below draws its truth.
- `source: gradus-assets` files carry whatever the encoder wrote: `no`,
  `Selig sind, die la Leid tragen`, `Ravel_Bolero`, `Trio. Im gleichen Tempo`.
  Open these before believing them.

⚠️ **Never trust an embedded movement title** (CLAUDE.md, score-library
section): the Mahler 5 export repeats *"I. Trauermarsch"* as the movement title
of every movement. The reliable identification is what this scoping did —
parse the file and compare its **meter, part list and measure count** against
the printed page.

⚠️ **`mvt1` absent ≠ no first movement.** Bolero and the 1812 Overture are
single-movement works whose only reference is the whole piece; their `variant`
is a title fragment. Both *do* cover the music page 1 starts.

### Works with no usable first-movement pair

- `bach--das-wohltemperierte-klavier-i` — reference is BWV846 only, and the
  edition is a 2024 **born-digital typeset** with no raster image at all. Not a
  scan; belongs in an engraved control, not here.
- `ravel--bolero` — same: born-digital A3 typeset, no raster.
- `brahms--ein-deutsches-requiem` — one movement encoded, and it is not the
  page the PDF opens on.

---

## 2. The six proposed rows

Ranked. Rows 1–4 are the recommended first cut if the build phase wants to
start smaller; 5–6 are deliberate stress cases.

### Row 1 — `beethoven-sym5-mvt1` / IMSLP **984073** / PDF page **index 1**

The edition the existing measurement used, so the table opens with a row that
already has a number. Provenance from
`benchmarks/omr-first-run-2026-08/probe_page_measures.py`:
`IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf`, `PAGE = 1`,
`DPI = 600` — the legacy path
`~/Documents/Gradus-Assets/Scores/Scores For Gradus/…` still resolves, and the
library copy is
`editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf`.

| | |
|---|---|
| scan | 2897×3813 ccitt bitonal @600 ppi, page 347.6×457.6 pt, no text layer |
| first music page | PDF index **1** (index 0 is a cover) |
| page holds | 1 system, **12 staves**, **mm. 1–16** |
| how the count was established | five tacet staves, full-height columns that continue past the staff (`probe_page_measures.py`); 16 after the 17→16 correction |
| reference | `beethoven--symphony-5--mvt1--gradus.mxl` — 18 parts, 502 measures, 2/4 from m1, m1 is a **full** 2/4 bar (ql 2.0, no pickup), first repeat at m124 |
| condensation | 18 reference parts → 12 printed staves |
| existing score | OMR-NED **0.8706** (1723 edits / 1123 truth + 856 pred), 66% of it whole-measure and whole-staff inserts |

### Row 2 — `beethoven-sym5-mvt1` / IMSLP **575951** / PDF page **index 0**

**The cheapest row in the table and possibly the most informative.** Same work,
same 12-staff layout, same Italian part names (`Flauti / Oboi / Clarinetti in B.
/ Fagotti / Corni in Es. / Trombe in C. / Timpani in C.G. / Violino I. /
Violino II. / Viola. / Violoncello. / Basso.`), same 2/4, same key signatures
including the bare Corni/Trombe/Timpani — verified by rendering and reading the
page. First-pass rest count on the tacet Flauti staff: **16 measures**, matching
the independently-established 16 on row 1.

So the ground truth is (hypothesis) *identical* and the only things that change
are **scan resolution and the text layer**:

| | 984073 | 575951 |
|---|---|---|
| raster | 2897×3813 ccitt | **5409×7207 jbig2** |
| text layer | no | **yes** |
| PDF pages | 88 (cover + 87) | 87 |
| page 1 of music | index 1 | index **0** |

Page counts differ by exactly the cover, so the offset is `984073[k+1] ==
575951[k]`. **Confirm that on 2–3 pages in the build phase before reusing the
measure map.**

⚠️ Two cautions. (1) This is *not* a pure scan-quality A/B — the text layer
turns on the free `staff_labels.read_staff_labels` rung, which feeds part naming
and `contextual._fill_defaulted_clefs`, and a filled clef *does* reach OMR-NED.
Report it as "resolution + text layer", not "resolution". (2) The two files are
visibly **not the same print run**: 575951 carries a modern English title line
and running heads (`2 SYMPHONY NO. 5 (1)`), i.e. a reprint of the same plates,
while the catalog gives both the identical provenance *"Henry Litolff's Verlag,
Braunschweig, 1870, plate 2769"*. See "Catalog and doc discrepancies" below.

### Row 3 — `dvorak-sym9-mvt1` / IMSLP **405834** / PDF page **index 4**

**The only 1:1 part↔staff pair in the whole library.** The printed page carries
15 staves — Flauti, Oboi, Clarinetti in A, Fagotti, Corni I.II. in E, Corni
III.IV. in C, Trombe in E, Tromboni I.II., Trombone basso, Tympani A.E.H.,
Violino I, Violino II, Viola, Violoncello, Contrabasso — and the reference has
**exactly 15 parts** in the same order. Every other candidate condenses.

That matters because it is the one row where OMR-NED measures recognition
rather than the export's part model: no `entire staff insert/delete` floor, no
condensation arithmetic, and the dossier join (in the separate `--dossier` arm)
does not abstain.

| | |
|---|---|
| scan | 5088×6976 jbig2 (indexed) @601×600 ppi, page 610×837 pt, no text layer |
| first music page | PDF index **4**. Index 2 is a **Contents** page for a two-symphony volume with *Symphony No. 8* struck through — this PDF is an extract, and its contents page independently names movement I as *Adagio* at printed page 183. Index 3 is blank. (The horizontal-run probe called index 2 "music": it was reading the table rules and the strikethrough.) |
| page holds | 1 system, 15 staves, **mm. 1–8** (first-pass: 8 whole-bar rests on the tacet *Trombe in E*, 8 cells between barlines) |
| reference | `dvorak--symphony-9--mvt1--gradus.mxl` — 15 parts, 452 measures, **4/8** from m1 changing to 2/4 at m24, m1 a full 4/8 bar (ql 2.0), repeat start m24 |
| density | **sparse** — most of the page is whole-bar rests, a deliberate contrast to rows 4–5 |

### Row 4 — `brahms-sym1-mvt1` / IMSLP **317803** / PDF page **index 0**

Same music as an engraved benchmark work, so this is the first **engraved-vs-scan
delta on identical notes**: Brahms 1 scores 0.1709 on the LilyPond render.

| | |
|---|---|
| scan | ccitt bitonal ~5276×6940 @~533 ppi, page 711.6×936.3 pt, no text layer. **Per-page raster dimensions vary** (5248/5280/5276/5270…) — individually scanned and deskewed sheets |
| first music page | PDF index **0** — "Symphonie Nr.1 (C moll) für großes Orchester", *Un poco sostenuto* |
| page holds | 1 system, **14 staves**, **mm. 1–7** |
| how counted | tacet *2 Trompeten in C* staff: notes in m1 then six whole-bar rests → 7 cells; the *Pauken* staff agrees |
| **barline-independent cross-check** | the system ends with a **cautionary 9/8** printed after the final barline, and the reference changes meter to 9/8 **at measure 8**. The page therefore ends at m7 — established without counting anything |
| reference | 21 parts, 513 measures, 6/8 → 9/8 @ m8 → 6/8 @ m9; m1 a full 6/8 bar (ql 3.0); repeat start m40, key change m191 |
| condensation | 21 → 14 |

That cross-check is the model the other rows should aspire to: a fact from the
reference (meter change at m8) confirming a count taken from the ink, with no
shared failure mode between them.

### Row 5 — `mahler-sym5-mvt1` / local scan / PDF page **index 1**

Densest page in the set, same music as an engraved benchmark work (Mahler scores
0.0455 engraved), and **the anacrusis case**.

| | |
|---|---|
| scan | 4385×5857 jbig2 bitonal @600 ppi, page 523.8×703.3 pt, no text layer, Edition Peters No. 3087b |
| first music page | PDF index **1** — index 0 is the Peters **title page** (my staff-row probe called it "MUSIC" because the decorative frame's rules look like staff lines; visual check is what caught it) |
| page holds | 1 system; printed page 3; German part names; staff count **~19, not yet counted exactly** (the percussion block is tightly spaced — build phase must count it) |
| window | **reference mm. 0–8**: a quarter-rest pickup cell, then 8 full bars (first-pass; 8 whole-bar rests on the tacet *Vier Flöten* staff, 9 cells including the pickup) |
| reference | 38 parts, 416 measures, 2/2; **measure 0** has ql 1.0 and `paddingLeft` 3.0 — a quarter-note upbeat, the solo trumpet fanfare, and the printed page shows exactly that: a quarter rest before the first barline |
| condensation | 38 → ~19, the largest in the set |

### Row 6 — `bach-brandenburg3-mvt1` / IMSLP **468678** / PDF page **index 0**

Baroque chamber texture, lowest resolution in the set, and **the opposite
anacrusis convention** — which is the reason to keep it.

| | |
|---|---|
| scan | 2341×3277 / 2285×3274 jbig2 @300 ppi, page 561.8×786.5 pt, no text layer, Edition Peters Nr.4412 |
| first music page | PDF index **0** — "KONZERT G-DUR / КОНЦЕРТ G-DUR", printed page 59 (an offprint from a collected volume) |
| staves | 11 instrumental + Cembalo on 2 staves = 13 in system 1 |
| system 1 | a narrow **pickup cell** (two sixteenths) then **4 full bars**; the next block opens with a boxed **5**, which is the confirmation |
| ⚠️ numbering | the print numbers the first **full** bar as 1; the reference numbers the **pickup** as measure 1 (`m#1` ql 0.5, `paddingLeft` 3.5). So printed bar *n* = reference measure *n+1*, and system 1 = **reference mm. 1–5** |
| ⚠️ structure | the page shows three blocks: full score, then a 10-staff strings block and a 2-staff Cembalo block **both carrying the boxed 5**. Almost certainly one system with the continuo set apart — an open question for the build phase, and a system-grouping stress case |
| reference | 11 parts, 137 measures, 4/4 |
| page window | **not established** — system 1 is mm. 1–5; the second system's count is TBD |

Three complications at once (off-by-one numbering, ambiguous system structure,
lowest dpi). Excellent as a stress row, wrong as a first row.

### Deliberately not chosen, and why (all remain available)

| candidate | why it is interesting | why not first |
|---|---|---|
| `mozart--symphony-41` / 984556, index 0 | 1200 ppi (highest in the store), clean classical layout, common time, **two systems** of 10 staves — tests the cross-system stitch on a scan | system-1 count read as ~11 but not confirmed, and the page total was not established; 17 reference parts → 10 staves, and the reference carries *Corno in F* parts the page does not print |
| `mozart--symphony-40` / 984555, index 0 | 1200 ppi, sparse classical | ⚠️ **this edition prints the revised Oboi + Clarinetti on two extra staves ABOVE the main system**, with a footnote saying so. Two physically separated blocks, an Oboi staff appearing twice, and a reference whose 11 parts do not map onto that. Genuine, and a bad place to start |
| `brahms--symphony-2` / 23103 | the **worst scan in the library** — 950×1128 **colour JPEG** on a 171×203 pt page. The only true colour/greyscale raster besides Tchaikovsky 6 Eulenburg | so far outside the rest of the distribution that it would dominate a pooled figure. Add later as a named stress row |
| `tchaikovsky--symphony-6` / 922722 | only JPX-RGB + jbig2-smask hybrid; 300 ppi | untested encoding path; worth one row once the table is stable |
| `tchaikovsky--symphony-4` / 377460 | Jurgenson 1882, a different engraving tradition, 600 ppi ccitt | **visibly skewed** — the horizontal-run probe finds ~0 full-width dark rows on pages that are plainly music. Good rotation stress; needs its own ground-truth care |
| `holst--the-planets` / 1014401 | 1921 Goodwin & Tabb, `stencil` raster type, very large forces | 190 pages, huge staff counts; expensive ground truth |
| `beethoven--symphony-1/2/3/4/6/7/8/9` | eight more works from **one consistent series** (Litolff 1870, plates 2765–2773), all jbig2 ~600 ppi **with text layers**, all with mvt1–4 references | the obvious way to grow the table later without new scan-quality variables |
| `bruckner--symphony-5` / 518282 | 300 ppi ccitt, BrucknerAGA 1935 | nothing wrong with it; simply out-ranked |

---

## 3. Trimming the reference — design

The page covers measures *A..B* of a movement; the reference covers the whole
movement. Everything below was verified on this host today.

### 3a. The measure map is INPUT, never derived

A per-work JSON file states the window. It is hand-verified and it is the only
place the window is stated. The runner **must not** infer it from the OMR (that
is the thing being scored), and must not infer it from a probe run at scoring
time either — the probe is how the number was *established*, not how it is
*consumed*. Reusable machinery for establishing it:

- `benchmarks/omr-first-run-2026-08/probe_page_measures.py` — the tacet-staff
  full-height-column counter, **including the fix** for the time-signature trap
  (`MAX_BARLINE_WIDTH_SPACES`, plus `BELOW_STAFF_PX` / `BELOW_STAFF_MIN_INK`
  requiring the column to continue past the staff). It is hard-coded to one PDF
  and one page with hand-entered staff y-bands; the build phase should
  generalise it to take `(pdf, page, [(name, y0, y1)])` and keep the constants.
  Its own docstring records that a cross-staff variant was tried and **discarded
  for failing where the pipeline fails**.
- `benchmarks/omr-first-run-2026-08/eval_first_run.py` — the printed-staff →
  reference-part map, the hand-read clef/key columns, and the multiset
  `exact`/`step`/`with_duration` scoring. Directly reusable as the per-work
  note-recall arm beside OMR-NED.

⚠️ **Two things in `eval_first_run.py` must change if it is reused.**
(1) `TRUTH_MXL` points at `~/Desktop/gradus-vercel/public/scores/…` — pre-library
and outside the store; it should come from the catalog. (2) `pitches()` slices
`measures[first-1:last]` — **positional**, which silently disagrees with
measure numbers on any pickup work. It coincides for Beethoven 5 (numbered from
1, no pickup) and is off by one for Mahler (numbered from 0) and Bach 3.

### 3b. Where trimming runs, and with what

| | host `python3` | `.venv-omrned/bin/python` |
|---|---|---|
| Python | 3.9.6 | **3.14.4** |
| music21 | 8.3.0 | **10.5.0** |
| musicdiff | — | **5.2** |

Verified semantics, in **both** interpreters, on the real reference files:

```
Stream.measures(numberStart, numberEnd)      # matches measure NUMBERS, INCLUSIVE
Stream.measures(..., indicesNotNumbers=True) # positional, end EXCLUSIVE
```

On `mahler--symphony-5--mvt1--gradus.mxl` (numbered from 0):

| call | result |
|---|---|
| `measures(1, 4)` | 4 measures, numbers `[1,2,3,4]` — **the pickup is dropped** |
| `measures(0, 4)` | 5 measures, numbers `[0,1,2,3,4]`, first ql 1.0, `paddingLeft` 3.0 |
| `measures(0, 4, indicesNotNumbers=True)` | 4 measures `[0,1,2,3]` |

`measures()` preserves all 38 parts, and its `collect=` argument re-attaches
`Clef / TimeSignature / Instrument / KeySignature` (10.5.0 adds `MetronomeMark`)
at the head of the window — which is what makes a mid-movement window valid and
is harmless at m1. 8.3.0 takes those arguments positionally; 10.5.0 makes them
keyword-only. **Pass them by keyword** and the same call works in both.

**Recommendation: trim in `.venv-omrned` and write `.musicxml`.**

Three reasons, one of which is not optional:

1. **Both files handed to musicdiff must share one extension.**
   `tools/omr/_omrned_worker.py:_stage` sets `suffix = ".musicxml"` whenever the
   pair's suffixes differ, and then **converts both through music21** — which
   its own comment warns "launders syntax errors … musicdiff deliberately parses
   the prediction leniently and the truth strictly, and a conversion here erases
   that distinction." Handing it a raw `.mxl` truth beside a `.musicxml`
   prediction therefore launders the *prediction*. The truth must be written out
   as `.musicxml` regardless; the only real choice is which music21 writes it.
2. Trimming in the venv means the file is produced and consumed by the **same
   music21 10.5.0** that musicdiff parses with — no cross-version round trip on
   the ground truth. The host's 8.3.0 emits real warnings on these files
   (`Line <dashes> stop without start`, `Could not import wedge`).
3. There is precedent for a venv-side standalone script:
   `.venv-omrned/bin/python benchmarks/omr-ned-2026-08/dump_ops.py PRED TRUTH`.

Verified round trip in the venv: parse `.mxl` → `measures(0,4)` → `write
("musicxml")` (111 KB) → re-parse gives 38 parts, 5 measures, numbers
`[0,1,2,3,4]`, first measure ql 1.0 with `paddingLeft` 3.0 intact.

⚠️ **`orchestral_eval` trims on the HOST** (`parsed.measures(first,
last_used)`, music21 8.3.0) and its truth files go to musicdiff that way. Moving
the scan benchmark to venv-side trimming means the two benchmarks prepare truth
differently. That is defensible — they are different corpora and the pooled
figures are not comparable anyway — but it must be **stated in the runner's
docstring**, and a `--trim-on-host` flag should exist so the difference can be
measured rather than assumed.

### 3c. Anacrusis and repeats

**Anacrusis — the reason the map needs an anchor, not just a length.** The two
conventions are both present in the corpus:

| work | reference numbering | printed numbering |
|---|---|---|
| Beethoven 5, Brahms 1, Dvorák 9, Mozart 40/41 | m1 is a full bar | same |
| **Mahler 5** | pickup is measure **0** | pickup unnumbered; first full bar is 1 |
| **Bach Brandenburg 3** | pickup is measure **1** | pickup unnumbered; first full bar is 1 → **reference is +1 against the print** |

So the metadata may not say "the page holds K measures". It must say **which
reference measure numbers** the page covers, and separately whether the leading
one is a pickup. Concretely: `first_ref_measure` / `last_ref_measure` (passed
straight to `measures()`, which is inclusive and number-based), plus
`leading_pickup: true|false` recorded so a report can explain a short first bar
rather than flagging it. Derive nothing from a length.

**Repeats — musicdiff compares the WRITTEN measure sequence.**
`_omrned_worker.py` calls `musicdiff.diff_ml_training` on the parsed scores;
nothing calls `.expandRepeats()`, and music21 does not expand on parse. So a
`|:` in the truth is a barline property, not a duplication — which is what we
want, since the pipeline emits the written sequence too (and currently drops
repeat barlines entirely, a known limitation). Every proposed page-1 window sits
before the first repeat mark anyway (Beethoven 5 end-repeat m124, Brahms 1 start
m40, Dvorák 9 start m24, Mozart 41 end m120), so **repeats do not bite on any
row in the first cut**. They will the moment the table extends past page 1:
`measures()` on a window that opens after a `Repeat(direction='start')` yields a
dangling end-repeat. Guard it in the trimmer — strip unmatched `bar.Repeat`
objects from the trimmed window and say in the metadata that it happened.

### 3d. The structural floor, and an optional way to remove it

66% of the Beethoven 5 first-run's edits were whole-measure and whole-staff
inserts, because the reference has 18 parts and the print condenses to 12. That
floor is **constant per work**, so deltas across pipeline changes stay
meaningful — reporting the `entire staff insert/delete` share alongside the
score is enough to keep it honest, and is the cheapest correct answer.

If the build phase wants it removed, `Score.partsToVoices` does the job and was
verified in the venv:

```python
alloc = [[0,1],[2,3],[4,5],[6,7],[8,9],[10,11],[12],[13],[14],[15],[16],[17]]
merged = trimmed.partsToVoices(voiceAllocation=alloc, permitOneVoicePerPart=False)
# 18 parts -> 12 parts; part 0 measure 1 carries 2 voices; writes valid MusicXML
```

The allocation list is exactly the `parts` column of `eval_first_run.py`'s
`STAVES` table, so it is already hand-verified for Beethoven 5. **Do not adopt
this as the headline truth without measuring it** — the pipeline emits voices via
`<backup>`, and whether musicdiff scores a two-voice truth measure against a
two-voice prediction fairly is a question to answer, not assume. Propose it as a
second reported column (`omr_ned_asprinted`) with `omr_ned_asis` kept as the
primary, so the two can be compared before either is trusted.

### 3e. Per-work metadata format

One JSON file per row under `benchmarks/omr-scan-e2e-2026-09/works/`, committed.
Everything the runner needs and nothing it can derive:

```jsonc
{
  "row_id": "beethoven-sym5-mvt1-984073-p1",
  "work_id": "beethoven--symphony-5",          // catalog join key
  "edition": {
    "catalog_path": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "imslp_id": "984073",
    "publisher_as_catalogued": "Henry Litolff's Verlag, Braunschweig, 1870, plate 2769",
    "raster": "2897x3813 ccitt bitonal @600ppi",
    "has_text_layer": false
  },
  "reference": {
    "catalog_path": "reference/beethoven/symphony-5/beethoven--symphony-5--mvt1--gradus.mxl",
    "movement": "mvt1",
    "n_parts": 18, "n_measures": 502, "meter_at_start": "2/4"
  },
  "page": {
    "pdf_page_index": 1,                        // 0-based, as transcribe --pages
    "printed_page": 1,
    "n_systems": 1,
    "n_staves": 12
  },
  "window": {
    "first_ref_measure": 1,                     // -> measures(first, last), inclusive
    "last_ref_measure": 16,
    "leading_pickup": false,
    "established_by": "probe_page_measures.py, five tacet staves, all agree on 16",
    "verified_by": "sean/claude 2026-08-31; corrected from 17 (time-signature column)",
    "confidence": "verified"                    // verified | first_pass | unknown
  },
  "staves": [                                   // printed staff -> reference parts,
    {"name": "Flauti", "parts": [0,1], "clef": "treble", "key": -3},
    {"name": "Timpani in C.G.", "parts": [12], "clef": "bass", "key": 0}
    // ... hand-read off the SCAN, not taken from the reference
  ],
  "notes": "Print gives Trombe/Timpani no key signature; the Gradus file gives them three flats. The page wins."
}
```

`confidence` is load-bearing: the runner should **refuse to report a pooled
figure** while any row is `first_pass`, and print the per-row scores anyway. A
pooled number computed over an unverified window is exactly the 0.8706-against-17-measures
mistake with more decimal places.

---

## 4. Build plan

### Files

| path | committed? | what |
|---|:--:|---|
| `benchmarks/omr-scan-e2e-2026-09/SCOPING.md` | yes | this file |
| `benchmarks/omr-scan-e2e-2026-09/works/*.json` | yes | the per-work metadata above — hand-verified, irreplaceable |
| `benchmarks/omr-scan-e2e-2026-09/probe_page_measures.py` | yes | generalised tacet-staff counter (from `omr-first-run-2026-08`), the tool that *establishes* a window |
| `benchmarks/omr-scan-e2e-2026-09/RESULTS.md` | yes | the report that cites the numbers |
| `benchmarks/omr-scan-e2e-2026-09/results.json` | yes | small; the table behind RESULTS.md |
| `tools/omr/training/scan_eval.py` | yes | the runner |
| `tools/omr/_scantruth_worker.py` | yes | venv-side trimmer, `_omrned_worker.py`'s sibling — **must not import `tools.*`** |
| `benchmarks/omr-scan-e2e-2026-09/fixtures/` | **no** | trimmed truth, `*.omr.musicxml`, page PNGs, `.ly`/`.pdf` |

`.gitignore` conventions to follow (root `.gitignore`, lines 74–124):
`benchmarks/**/*.omr.json` is already ignored globally ("Commit the REPORT that
cites the numbers, not the dump it read them from"), and rendered fixtures get
an explicit directory line — `benchmarks/omr-orchestral-e2e/fixtures/` and
`benchmarks/omr-end-to-end/fixtures/` are the precedent, so add
`benchmarks/omr-scan-e2e-2026-09/fixtures/`. Page renders are covered by the
same principle (`benchmarks/*/page-thumbnails/`, `benchmarks/**/crops/`) —
regenerable from the PDF in seconds. The alternative local pattern is
`benchmarks/omr-real-scan-notes-2026-08/pipeline-runs/.gitignore` (`*` +
`!.gitignore`), which keeps the rule next to what it ignores.

### Runner shape

```bash
python3 -m tools.omr.training.scan_eval                       # all verified rows
python3 -m tools.omr.training.scan_eval --rows beethoven-sym5-mvt1-984073-p1
python3 -m tools.omr.training.scan_eval --omr-ned --out results.json
python3 -m tools.omr.training.scan_eval --dossier             # the separate arm, never the headline
python3 -m tools.omr.training.scan_eval --include-first-pass  # opt in to unverified rows
```

Per row: resolve the PDF and reference through the catalog → `transcribe(pdf,
pages=[page_index], weights=DEFAULT_WEIGHTS, dossier=None, progress=False)` at
**defaults** → `to_musicxml` → trim the reference through the venv worker →
`omr_ned.score_batch([(row_id, pred, truth)])` once for the whole set (the
pooled figure is only meaningful computed together) → also run the
`eval_first_run`-style multiset note recall using the `staves` map.

Deliberately mirrored from `orchestral_eval`: one bad row must not stop the run;
`_optional_pass_failure`'s bug-vs-abstention split must be honoured, and the run
should **exit non-zero when an optional pass failed like a defect** — CLAUDE.md
records a documented on-by-default pass going dark for hours with a green suite
and an unmoved OMR-NED, and a new benchmark should not reintroduce that blind
spot.

⚠️ **Do not write into `benchmarks/omr-ned-2026-08/current-accuracy.json` or
CLAUDE.md's `accuracy:begin name=headline` block.** That record is defined as
the *engraved orchestral* pooled figure, and `orchestral_eval --record` refuses
even to write it when the run covered a different work set. If the scan figure
needs a present-tense home, follow the same pattern rather than fighting it: its
own record JSON in this directory and its own marker name in
`accuracy_record._BLOCKS` (e.g. `"scan": ("PROJECT_STATUS.md", _scan_headline)`),
so it too cannot drift from its measurement without a test going red.

### Suggested order

1. Rows 1 and 2 (Beethoven 5 ×2) — row 1 reproduces a known 0.8706 and validates
   the whole harness against an existing result; row 2 costs one page-offset
   check and buys the scan-quality/text-layer contrast.
2. Row 3 (Dvorák 9) — the clean 15/15 row; expect a much lower score, and if it
   is not much lower, the structural floor hypothesis is wrong and that is the
   finding.
3. Row 4 (Brahms 1) — first engraved-vs-scan delta on identical music.
4. Row 5 (Mahler 5) — exercises the anacrusis path end to end.
5. Row 6 (Bach 3) — only after the `+1` numbering anchor is proven on Mahler.

---

## 5. Open risks

1. **Every measure count in this document except Beethoven 5's is first-pass
   visual.** Brahms 1 (7) has a barline-independent cross-check and is the
   strongest; Dvorák (8) and Mahler (0–8) were read off tacet staves at 250 dpi;
   Mozart 41 and Bach 3 page totals are **not established**. Re-verify all of
   them with the generalised probe *and* a second, differently-failing signal
   before any pooled figure is quoted.
2. **Staff counts are not all established.** Mahler's percussion block was not
   counted exactly (~19 staves). Beethoven 5 (12), Brahms 1 (14), Dvorák (15)
   and Mozart 41 (10 per system) were read off the page.
3. **The 984073↔575951 page offset is a hypothesis** (88 = cover + 87; index 1 ↔
   index 0). Confirm on several pages before sharing a measure map.
4. **`partsToVoices` truth is unvalidated against musicdiff.** It produces a
   valid file; whether the score it yields is *fair* is unmeasured.
5. **Part matching inside musicdiff is not understood here.** The prediction's
   parts are named by instrument (or by coordinate when contextual finds
   nothing) and the truth's by the encoder. Whether musicdiff aligns parts by
   position or by name changes what a condensed page costs. Check before reading
   a category breakdown.
6. **The known scan-domain failure will dominate and is not a regression.**
   Half noteheads are invisible on a bitonal scan — Beethoven 5 p.1 prints 68 and
   the pipeline detects 8, duration recall 0.381 against step recall 0.714, with
   the LilyPond control at duration recall *equal* to pitch recall. Four fixes
   are already recorded as failed (`DURATIONS.md`); the lever is a labeling batch.
   Expect it to sit under every row, and report duration separately so it does
   not mask movement elsewhere. It may also behave differently on the
   greyscale/colour rasters (Brahms 2, Tchaikovsky 6 Eulenburg) — which is a
   reason to add one of them eventually.
7. **`OMR_DPI` is 300 in the container and 600 on the CLI, on purpose**, and the
   right value is coupled to `OMR_IMGSZ` and depends on the music. The runner
   must pin one and say which; "defaults" is ambiguous until it does.
8. **Front matter is not detectable by ink alone.** A horizontal-rule probe
   called Mahler's decorated title page "music", and found ~0 staff rows on the
   plainly-musical Mozart 40 and Tchaikovsky 4 pages because those scans are
   **skewed**. First-music-page numbers must be eyeballed, as they were here.

## 6. Catalog and doc discrepancies found while scoping

Neither blocks the benchmark; both should be recorded.

- **Two visibly different Beethoven 5 files carry identical provenance.**
  IMSLP 984073 and 575951 are both catalogued as *"Henry Litolff's Verlag,
  Braunschweig, 1870, plate 2769"*, but 575951 has a modern English title line
  and running heads (`2 SYMPHONY NO. 5 (1)`) that 984073 does not — a later
  reprint of the same plates, most likely. The music engraving does look
  identical (same 12 staves, same part names, same key signatures), so the
  provenance is *approximately* right and *literally* wrong.
- **`eval_first_run.py` calls 984073 "Breitkopf"** ("Breitkopf prints Trombe and
  Timpani with no key signature") while the catalog says Litolff. One of the two
  is wrong; the observation about the key signatures is correct either way.
- **`eval_first_run.py` and `orchestral_eval.py` still read from
  `~/Desktop/gradus-vercel/public/scores/`**, outside the score library. Not
  broken — the directory exists — but new code should go through the catalog.
