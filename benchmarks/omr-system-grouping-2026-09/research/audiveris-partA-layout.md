# Audiveris reference — PART A: Layout & structure recognition

2026-09-01. Sub-agent deep-dive for the ReEngrave team. **Documenting
algorithms, techniques, parameters and architecture only** — facts and ideas,
which are not copyrightable. Audiveris is **AGPL-3.0**; nothing here is verbatim
source or a line-by-line paraphrase for porting. Where an approach is specific
enough that any reuse should be clean-room, it is flagged **⚠ clean-room**.
File:line pointers let a human open the original — they are *not* an instruction
to copy it.

**Source provenance.** Line numbers are the GitHub **master** branch as of
2026-09-01, package root `app/src/main/java/org/audiveris/omr/`. Docs are
`audiveris.github.io/audiveris/_pages/explanation/steps/` (fetched via the raw
`docs/_pages/...` markdown). Tags on every claim:
**[DOC]** official handbook · **[SRC]** source read directly · **[INFERENCE]**
my reasoning from the two · **[NOT FOUND]** looked, did not confirm.

**Scope.** LOAD, BINARY, SCALE, GRID (staff-line filaments + scale + **part**
formation — system grouping lives in the sibling file `audiveris-grid.md` and is
not repeated), HEADERS (clef/key/time), MEASURES, TEXTS. Each step: (1) what &
technique, (2) params + file:line, (3) how it categorizes, (4) failure handling
& switches, (5) ReEngrave's approach + the gap, (6) adoptability. Ranked
adoptable list at the end.

**One cross-cutting fact to hold in mind.** Audiveris measures a **SCALE** —
interline, line thickness, beam thickness — as step 3, *before staves or any
symbol exist*, and then expresses essentially every downstream threshold as a
fraction of interline or of line thickness (`Scale.Fraction`,
`Scale.LineFraction` in the source). ReEngrave has no such standalone step: its
"scale" is a by-product of staff detection (a single median line spacing). Most
of the divergences below flow from that one architectural difference. [SRC][INFERENCE]

---

## Pipeline placement

Audiveris runs a fixed ~20-step pipeline; my scope is the classical-CV front
half, all of which precede symbol/notehead recognition. [DOC]

| Audiveris step | package | my section |
|---|---|---|
| LOAD | `sheet/` (Picture, image load) | §1 |
| BINARY | `image/` filters | §2 |
| SCALE | `sheet/Scale*.java` | §3 |
| GRID | `sheet/grid/`, `sheet/StaffManager` | §4 (filaments, clustering, parts) |
| HEADERS | `sheet/header/`, `sheet/clef/`, `sheet/key/`, `sheet/time/` | §5 |
| (STEM_SEEDS … CURVES … symbol steps) | — | out of scope |
| MEASURES | `sheet/rhythm/MeasuresBuilder` | §6 |
| TEXTS | `text/`, `text/tesseract/` | §7 |

ReEngrave's classical-CV front half lives in `tools/omr/`:
`preprocessing.py` → `staff_detector.py` (+ `system_grouping.py`,
`header_ink.py`) → `measure_extractor.py` → header readers
(`staff_header.py`, `clef_geometry.py`/`clef_locator.py`,
`key_signature_*.py`) → `staff_labels*.py`/`contextual.py`. YOLO runs *after*
this layout layer. [SRC]

---

## §1 — LOAD

**(1) What & technique.** LOAD reads the input (image or PDF page) into a
grayscale `Picture` / `RunTable` and hands a source image to BINARY. Audiveris
accepts raster images and PDFs; PDF pages are rasterized on import. [DOC]

**(2) Params / pointers.** `sheet/Picture.java`, `sheet/BookManager`,
`image/` package. Import DPI / rendering resolution is a book-level setting.
[NOT FOUND — did not open Picture.java for exact defaults; low value for our
purposes.]

**(3) Categorization.** None — LOAD is I/O + grayscale normalization.

**(4) Failure handling.** Missing/low-resolution input is surfaced as a
book-level warning; interline sanity is enforced later in SCALE (§3.4).

**(5) ReEngrave + gap.** `preprocessing.render_page` (`preprocessing.py:28`)
renders **PDF only** via PyMuPDF (`fitz`) at a chosen DPI (CLI default 600, web
300), `page.get_pixmap(dpi=…)`, then binarize+deskew. There is no image-file
load path in the module and no persisted intermediate. Repo research already
flagged a real LOAD-adjacent hazard ReEngrave has and Audiveris avoids by
construction: a **fixed DPI silently produces zero staves** on editions with a
tiny PDF mediabox (a 2.38″×2.82″ Brahms page → 713×846 px → 0 staves), so the
research recommends **normalizing to a target pixel height (~3000–3500 px), not a
fixed DPI** (`repo-state.md:427-446`). [SRC]

**(6) Adoptability.** Nothing to port from LOAD itself. The one adoptable idea is
external to Audiveris: **resolution normalization to a target interline/pixel
height**, which is exactly what a SCALE-first design (§3) buys you.

---

## §2 — BINARY (binarization)

**(1) What & technique.** Converts grayscale → black/white with a per-pixel
adaptive threshold by default. Two filters exist: **GLOBAL** (one constant
threshold, legacy) and **ADAPTIVE** (current default), plus a source-level
identity/no-op path. [DOC]

**(2) Params / pointers.** [DOC] The handbook gives the adaptive rule as
`threshold = mean_coeff · mean + std_dev_coeff · std_dev` over a pixel's local
neighborhood, defaults **`mean_coeff = 0.7`**, **`std_dev_coeff = 0.9`**; GLOBAL
default threshold **`140`**. Pixel ≤ threshold → black, else white. Filter and
coefficients are settable at default/book/sheet scope (`image/AdaptiveFilter`,
`image/GlobalFilter`; UI in `sheet/ui/BinarizationBoard.java`). [SRC — file
existence] The formula is the **Niblack/Sauvola family** (local mean plus a
multiple of local standard deviation). [INFERENCE]

**(3) Categorization.** Binary foreground (ink) vs background (paper); every
later step operates on runs of foreground. [DOC]

**(4) Failure handling & switches.** Choosing GLOBAL vs ADAPTIVE and tuning the
two coefficients is the documented recourse for uneven scans; the adaptive
default is specifically to survive uneven illumination and yellowed paper. [DOC]

**(5) ReEngrave + gap.** `preprocessing.binarize` (`preprocessing.py:76`) uses
**true Sauvola** (`skimage.filters.threshold_sauvola`, `window_size=25`,
`k=0.2`), paper=255/ink=0. So both engines are in the same adaptive family and
for the same reason; ReEngrave literally uses Sauvola while Audiveris uses its
own mean+σ variant. **Effectively no gap** — this is the one stage where
ReEngrave and Audiveris already agree in spirit. ReEngrave additionally
**deskews** right after binarizing (Hough on near-horizontal lines, ±5° cap,
`preprocessing.deskew:98`); Audiveris keeps a `sheet/Skew.java` object
[SRC — file exists in the tree] and, per its architecture, works in a de-skewed
*coordinate frame* rather than resampling the raster — I did not open
`Skew.java` to confirm it never rotates pixels. [INFERENCE]

**(6) Adoptability.** Low value — ReEngrave's Sauvola is at least as good.
Worth stealing only if scans with strong local gradients defeat Sauvola: expose
the **filter choice + coefficients** as a per-document knob the way Audiveris
does. The **skew-as-coordinate-frame** idea (don't resample the raster; carry an
angle) is a cleaner alternative to ReEngrave's `warpAffine` deskew, which
INTER_NEAREST-resamples every pixel and can only correct ±5°. Clean, easy.

---

## §3 — SCALE (the master unit)

**(1) What & technique.** Before staves exist, Audiveris scans **vertical runs**
of the binary image column by column and builds run-length **histograms**, whose
peaks yield the sheet's fundamental lengths: **interline**, **line thickness**,
**beam thickness**. [DOC][SRC `sheet/ScaleBuilder.java`]

- **Black histogram** = lengths of every foreground (black) vertical run. Its
  **first peak = staff-line thickness**; a **second peak = beam thickness**
  (beams are the next-most-common uniform black vertical extent). [DOC]
- **Combo histogram** = each white (background) run length **plus the black runs
  immediately above and below** it → i.e. **line-center to line-center**. Its
  main peak = **interline** (staff spacing). A **second combo peak** appears when
  the sheet has **two staff populations** (e.g. a normal staff size and a smaller
  cue/ossia size), giving a **second interline**. [DOC]

**(2) Params / pointers.** [SRC] `ScaleBuilder.java` inner `Constants`
(lines 468–537):

| constant | line | default | meaning |
|---|---|---|---|
| `minInterline` | :471 | **11 px** | reject interline below this |
| `maxInterline` | :476 | **100 px** | reject above this |
| `maxLineRatio` | :501 | **0.5** | max line-thickness / interline |
| `beamMinFraction` | :505 | **0.45** | min beam-height / interline |
| `beamMaxFraction` | :509 | **0.95** | max beam-height / interline |
| `minSecondRatio` | :493 | **1.2** | min 2nd-combined-peak / 1st (two-population detect) |
| `maxSecondRatio` | :497 | **1.9** | max 2nd/1st (2.0 gave a false 2nd peak on a merged grand staff) |
| `minGainRatio` | :481 | 0.03 | peak-extension gain floor |
| `minDerivativeRatio` | :485 | 0.025 | derivative acceptance for peak bounds |
| `minBlackRatio` | :489 | 0.001 | min foreground fraction of the whole image |
| `maxWhiteHeightRatio` | :526 | 0.25 | cap white run length as ratio of image height |
| `maxBlackHeightRatio` | :530 | 0.08 | cap black run length as ratio of image height |
| `minCountRatio` | :534 | 0.4 | significant count as ratio of highest count |

Peaks are found by a **height threshold plus derivative analysis** for the
precise min/max around each peak. [DOC] The resulting `Scale` object
(`sheet/Scale.java`) is the master unit — `Scale.toPixels(Scale.Fraction)` and
`Scale.LineFraction` convert every downstream constant into pixels. [SRC]

**(3) Categorization.** Turns raw pixels into three named lengths + optional
"second population" flag. Everything after this is sized relative to them — the
handbook: these values "fundamentally determine the dimensions of almost all the
music elements to be detected." [DOC]

**(4) Failure handling & switches.** `minInterline`/`maxInterline` bound the
answer; `minBlackRatio` refuses near-blank pages; the black histogram may show
**no clear second peak** when a sheet has no beams (single population), which is
tolerated (beam thickness left unset). The two-population combo peak is guarded
tightly (`minSecondRatio 1.2 … maxSecondRatio 1.9`) because a merged grand staff
can fake a second peak. [SRC]

**(5) ReEngrave + gap.** **This is ReEngrave's single biggest structural gap in
the layout front-half.** ReEngrave has **no SCALE step**. Spacing is derived
*inside* staff detection as `_page_line_spacing` = median over detected 5-line
groups of `(line5−line1)/4` (`staff_detector.py:210`). Consequences:
- **Circular dependency**: you need the spacing to detect faint staves (the comb
  pass, `_comb_match_staves`), but the spacing comes from the staves the strict
  pass already found. Audiveris breaks this — scale is known before any staff.
- **No beam thickness as a unit.** ReEngrave never measures a global beam scale;
  `line_detection.py` finds beams morphologically per-cell but there is no sheet
  constant. Audiveris's beam thickness feeds beam detection sizing downstream.
- **No two-population handling.** A page mixing normal and cue/ossia staff sizes
  has no "second interline" concept; ReEngrave's `_reject_spacing_outliers`
  (`staff_detector.py:220`) instead *drops* groups >1.6× the median spacing,
  which is the opposite move — it discards small/large populations rather than
  modeling them.
- ReEngrave does express many thresholds "in staff spaces" (good, same spirit as
  `Scale.Fraction`), but line thickness is measured **per-staff/per-cell**
  (`header_ink.measure_staff_line`, `staff_line_removal.py`) rather than once
  globally, so the same fact is recomputed many times and can disagree between
  cells. [SRC]

**(6) Adoptability.** **HIGH — top pick.** A standalone SCALE step from
vertical-run-length histograms is a clean, well-understood, framework-agnostic
idea (the histogram method is classic OMR, older than Audiveris — porting the
*technique* carries no AGPL risk; do not lift their peak-bounds state machine
verbatim, ⚠ clean-room the exact `Constants`). Payoffs specific to ReEngrave's
known problems: (a) breaks the spacing↔detection circularity; (b) a page-level
interline that would have caught the tiny-mediabox zero-staff bug and the
DPI-dependent answers (`repo-state.md:427-446`); (c) a beam-thickness unit for
`line_detection`; (d) native two-population support for cue/ossia pages instead
of the current outlier-drop. Medium effort (one new module + rewiring
`_page_line_spacing` consumers).

---

## §4 — GRID: staff-line filaments, clustering, parts

> System grouping / barline-connection is covered in `audiveris-grid.md`. This
> section covers only what that file does **not**: filament detection, the
> line→staff clustering, and brace-group → part formation.

### §4a Staff-line filament detection

**(1) What & technique.** [DOC][SRC `glyph/dynamic/FilamentFactory.java`,
`sheet/grid/LinesRetriever.java`] Foreground pixels are split by a **max-line-
thickness gate** (a bit above the SCALE line thickness, to admit ledger lines):
runs thicker than the gate go to a **vertical LAG** (note/stem ink); the rest
form **horizontal runs → sections** in a **horizontal LAG** ("LAG" = Audiveris's
run-adjacency section graph; I do not assert an acronym expansion [INFERENCE]).
Adjacent sections are grown into **long, thin filaments** meant to be portions of
staff lines. Filaments are:
- **straightness/thickness filtered** — a filament too thick or non-straight is
  rejected;
- used to compute a **global sheet slope** from the **top 10%** longest
  filaments, then any filament whose slope deviates from the sheet slope is
  rejected;
- fitted as **curves** (`CurvedFilament`) or straight lines (`StraightFilament`)
  — so a *wavy/warped* staff line is modeled natively, not assumed horizontal.

**(2) Params / pointers.** [SRC] `FilamentFactory.java` `Constants`
(lines 1055–1116):

| constant | line | default | unit | meaning |
|---|---|---|---|---|
| `maxFilamentThickness` | :1075 | **1.5** | × line height | reject over-thick filament |
| `minCoreSectionLength` | :1086 | **0.5** | × interline | min section to seed a filament (lowered for staves with no start barline / percussion) |
| `maxCoordGap` | :1094 | **1.7** | × interline | bridge a gap *along* the line |
| `maxOverlapDeltaPos` | :1090 | **0.25** | × interline | max vertical offset between overlapping filaments (0.5 let half-notes bow the line) |
| `maxPosGap` | :1079 | **0.75** | × line height | max vertical gap to merge |
| `maxOverlapSpace` | :1098 | 0.16 | × interline | max horizontal space between overlapping filaments |
| `maxGapSlope` | :1055 | 0.5 | tangent | max slope across a bridged gap |
| `minSectionAspect` | :1060 | 3 | ratio | min section length/thickness |

`LinesRetriever.java` `Constants` (lines 1556–1652):

| constant | line | default | meaning |
|---|---|---|---|
| `topRatioForSlope` | :1556 | **0.1** | top-10% filaments define the global slope |
| `maxSlopeDiff` | :1565 | **0.025 rad** | reject filament whose slope ≠ sheet slope |
| `minRunLength` | :1618 | 0.25 × interline | min horizontal run considered |
| `minStaffLength` | :1646 | 30 × interline | min accepted staff length |
| `maxRightIndentation` | :1650 | 5 × interline | tolerate short right end |
| `stickerThickness` | :1592 | 1.0 × max line thickness | absorb "sticker" ink onto a line |
| `patternWidth` / `patternJitter` | :1626/:1630 | 1.0 / 0.25 × interline | staff-pattern probe |

**(3) Categorization.** A pixel-run is categorized as *staff-line ink* (thin,
long, on-slope) vs *everything else* (thick → vertical LAG) **before** any
symbol recognition. Filaments become `StaffLine`/`LineInfo` objects with a real
per-line curve. [SRC]

**(4) Failure handling & switches.** Non-straight / off-slope / too-thick
filaments are discarded; `purgeCrossingChunks` removes chunks where another glyph
crosses a line; ledger lines are admitted by the thickness gate margin; the
`sticker` machinery re-attaches ink that belongs to a line but was split off.
Staff editing is a manual UI recourse (`sheet/ui/StaffEditor.java`). [SRC]

**(5) ReEngrave + gap.** ReEngrave uses a **horizontal projection profile**, not
filaments: `_ink_profile` = ink pixels per row (`staff_detector.py:155`);
`find_peaks` with `height ≥ 0.35·page_width` and `prominence ≥ 0.30·range`
(`:161`) → candidate rows; greedy **5-peak grouping** with ±30% gap tolerance
(`_group_into_staves:179`). Divergences:
- **Row projection assumes near-horizontal lines** and leans on the upstream
  deskew; a warped/curved line smears across rows and loses prominence. Audiveris
  models each line as its own curve and never needs the page globally straight.
  ReEngrave partially compensates *downstream* (per-cell line wander in
  `staff_line_removal._anchor_rows`, `header_ink.measure_staff_line`) but the
  *detector* itself is row-global.
- **No thickness-based ink split.** ReEngrave has no equivalent of the
  vertical-LAG segregation that removes note/stem ink before line-finding; it
  separates staff-line rows from note rows purely by row ink-count + prominence,
  which is what forces the elaborate recovery machinery (comb pass, phantom
  rejection, misaligned-window refit, `_refit_misaligned_group` for a beam
  captured as a line — `staff_detector.py:782`). Audiveris's `maxFilamentThickness
  = 1.5× line` gate makes "a beam is not a staff line" a *front-of-pipeline*
  fact.
- ReEngrave's `_line_ink_runs_per_space` (`:686`, music ≤1.39 vs text ≥2.02
  runs/space) is a **runs-per-length** discriminator — conceptually close to
  Audiveris's `minSectionAspect`/run tests, and a genuinely nice ReEngrave
  invention for the text-as-staff problem.

**(6) Adoptability.** **Medium-high, but a big lift.** Full filament/section
LAG detection is a substantial rewrite and the exact merge/slope state machine
should be ⚠ clean-room. Two *pieces* are cleanly adoptable without the whole
rewrite: (a) a **thickness gate that removes runs thicker than ~1.5× the
(SCALE) line thickness before line-finding** — directly attacks the
beam-as-line failure ReEngrave patches with `_refit_misaligned_group`;
(b) **per-line curve fitting** (model each line as a low-order polynomial) so the
detector tolerates warp without a global deskew — ReEngrave already fits curves
per-cell, so promoting that to the detector is incremental.

### §4b Clustering lines into staves

**(1) What & technique.** [DOC][SRC `sheet/grid/ClustersRetriever.java`]
Filaments are vertically clustered using **combs** sampled at the SCALE
interline pitch: a comb is a vertical probe expecting N equally-spaced lines.
Valid staff configurations are **1-, 4-, 5-, 6-line** (5 standard; 4/6 for
tablature; 1 for one-line percussion) — chosen by processing switches. Audiveris
retrieves the **most popular line-count** across all combs and builds staves of
that size, then expands/merges partial clusters. [DOC][SRC lines 73–91, 1249]

**(2) Params / pointers.** [SRC] `ClustersRetriever.java` `Constants`
(lines 1387–1439):

| constant | line | default (× interline) | meaning |
|---|---|---|---|
| `samplingDx` | :1387 | 1 | dx between vertical comb samples |
| `maxExpandDy` | :1399 | **0.175** | dy to aggregate a filament into a cluster |
| `maxExpandDx` | :1395 | 2 | dx to aggregate |
| `maxMergeDx` | :1403 | 6 | dx to merge two multi-line clusters |
| `maxMergeDy` | :1411 | 0.4 | dy to merge clusters |
| `maxMergeCenterDy` | :1415 | 1.0 | center dy to merge |
| `clusterYMargin` | :1419 | 2 | rough margin around a cluster |
| `minClusterLengthRatio` | :1431 | 0.2 | min cluster length / median |

**(3) Categorization.** Each validated comb → a `Staff` (standard / one-line /
tablature) by its line count. Boundaries come purely from detected line
positions. [DOC]

**(4) Failure handling.** Config switches gate which line-counts are legal
(tablature off ⇒ 5-line only; one-line staves opt-in). Under-length clusters are
rejected by `minClusterLengthRatio`; the "most popular size" vote resolves
mixed evidence. [DOC][SRC]

**(5) ReEngrave + gap.** ReEngrave clusters by the same *goal* (five roughly
equal gaps) but greedily on **peak rows**, not interline-pitch combs:
`_group_into_staves` accepts any 5-peak window whose gaps are within ±30% of
their mean. It validates **only 5-line** (+ a bolt-on one-line percussion path,
`_single_line_staff_rows:412`); no 4/6-line/tablature. It has no
"most-popular-size" vote — instead a **comb-recovery** pass
(`_comb_match_staves:248`) that re-reads the page at the *already-measured*
spacing to rescue faint staves, plus phantom rejection. Net: ReEngrave's design
is a special case (5-line, single population) with hand-built recovery for the
faint-staff case that Audiveris's most-popular-size + expand/merge handles more
generally. [SRC]

**(6) Adoptability.** Medium. The **interline-pitch comb + most-popular-size
vote** is a clean, general replacement for ReEngrave's greedy grouping that would
also fold in 4/6/1-line staves; it pairs naturally with a real SCALE step (§3).
⚠ clean-room the expand/merge thresholds. If ReEngrave stays 5-line-only, lower
priority.

### §4c Parts (brace/bracket grouping) — **ReEngrave has no equivalent**

**(1) What & technique.** [DOC][SRC `sheet/grid/BarsRetriever.java`,
`sheet/grid/PartGroup.java`, `sheet/Part.java`] After systems are known,
Audiveris searches **on the left of the system's start column** for **braces,
brackets, and square groups** (`BarsRetriever.java:120,148`). Braces are found by
looking, at each staff start, for a **brace peak** whose filament runs through a
**top / [middle] / bottom** portion and building a **curved brace filament**
(`buildBraceFilament:239`, `braceConstructor` = `CurvedFilament.Constructor`,
:224). A left bar-peak overlapped by a brace symbol is removed (the brace, not a
barline, owns that column). The grouping symbols populate `PartGroup` objects
(`PartGroup.PartGroupingSymbol`), and **braces in the left margin drive the
gathering of staves into `Part`s** (a brace over two staves = one keyboard part;
a bracket over a family = a group). [DOC][SRC]

**(2) Params / pointers.** [SRC] `BarsRetriever.java` (brace/bracket logic
:120–260, `braceConstructor` :224); `PartGroup.java` (the group model);
`BraceInter.java` (the recognized brace). Bracket serif detection uses a
`serifConstructor`. Exact bracket/brace constants live in `BarsRetriever`'s
`Constants` block [NOT FOUND — did not enumerate; the *mechanism* is the point].

**(3) Categorization.** A left-margin vertical mark is categorized as
**brace** (curved, spans a part) vs **bracket** (straight with serifs, spans a
family group) vs **barline** — and that category *defines the part boundary*.
Order matters: systems first, then parts refine within them (see
`audiveris-grid.md`). [DOC][SRC]

**(4) Failure handling.** The maintainer's own comment marks this code
"rather fragile" (quoted in `audiveris-grid.md`). A bracket/brace that fails
detection falls back to system-level grouping. Cross-system part identity is
reconciled later by **logical-part collation** (`score/PartCollation.java`,
`score/LogicalPart.java`) on staff-count + line-count + part names. [SRC][DOC]

**(5) ReEngrave + gap.** **ReEngrave has no glyph-level brace/bracket detection
at all** (confirmed in `repo-state.md:132-146`: "No glyph-level detection of any
of them exists"). Its analogue is `system_grouping._assign_groups`
(`system_grouping.py:172`), which sets a `Staff.group_index` by splitting a
system where **barline bridging density < median × 0.5** — i.e. it *infers*
bracket-group boundaries from where barlines stop crossing, never localizing the
bracket. Part **identity** (which instrument) is then supplied separately by
`contextual.py` from margin labels, and the dossier join keys on labels, never on
a detected brace. So ReEngrave splits "wind/brass/string" groups by an
emergent barline-gap signal that `repo-state.md` documents as **edition-
dependent and the cause of the standing F1 over-merge failures**. A real brace/
bracket detector is named there as "the single largest unexploited signal."

**(6) Adoptability.** **HIGH — top pick, and specifically de-risks the grouping
work.** A **left-margin brace/bracket detector** (curved-filament brace between
top/middle/bottom portions; straight-with-serifs bracket) is a clean classical-CV
idea and would give ReEngrave a *direct* structural cue for part boundaries
instead of the edition-fragile barline-density proxy. It runs before YOLO (as in
Audiveris), so it is classical CV in the left margin — no new training class
needed (and the DSv2 model has no system-bracket class anyway,
`audiveris-grid.md`). Medium effort; the brace's curved-filament construction is
the specific part to ⚠ clean-room. This is the highest-leverage adopt for the
system-grouping benchmark this directory exists for.

---

## §5 — HEADERS (clef, key, time)

**Sequence & extent.** Audiveris reads each staff header **clef → key → time**,
left to right (`sheet/header/HeaderBuilder.java`). The header **extent** runs
from the measure start to `header.start + largestOffset`, capped at
`maxHeaderWidth = 15 × interline` (`HeaderBuilder.java:389`), the boundary being
"the first significant space right after the clef … until the next really wide
space." [DOC][SRC] Clef, key, and time each get their own builder with a
lookup ROI sized in interline units.

### §5a CLEF

**(1) What & technique.** [DOC][SRC `sheet/clef/ClefBuilder.java`,
`sig/inter/ClefInter.java`] A rectangular **ROI** at the staff start is scanned;
**elementary glyphs** (connected black-pixel ensembles) are extracted, aggregated
(`GlyphCluster`), and submitted to the **trained shape classifier**
(`ShapeClassifier.getInstance()`, `ClefBuilder.java:157`) which returns a ranked
list of **acceptable clef shapes**: `G_CLEF`(+`_SMALL`/`_8VA`/`_8VB`),
`C_CLEF`, `F_CLEF`(+`_SMALL`/`_8VA`/`_8VB`), `PERCUSSION_CLEF`. [SRC]

**(2) Params / pointers.** [SRC] `ClefBuilder.java` `Constants` (lines 686–723):
`maxClefEnd = 4.5 × interline` (clef must end within 4.5 interline of measure
start), `aboveStaff = 3.0`, `belowStaff = 3.25` (ROI vertical reach),
`beltMargin 0.15`, `xCoreMargin 0.2`, `yCoreMargin 0.5`. The ROI **cannot
vertically extend past a neighboring staff** to avoid catching an adjacent clef
(:292). [SRC]

**(3) How it categorizes = shape-class + line-position.** The classifier gives
the **shape family**; the **line the clef names** is then computed geometrically,
exactly as ReEngrave does independently:
- `G_CLEF*` → always `ClefKind.TREBLE` (fixed line). [SRC `ClefInter.java:508`]
- `C_CLEF`, `F_CLEF`, `F_CLEF_SMALL` are **mutable**: `kindOf(glyph.center, shape,
  staff)` derives the kind from the **glyph's vertical center → pitch**
  (`ClefInter.java:511-514`). For a C-clef, `cKindOf(pitch)` maps
  **pitch −2 → TENOR, 0 → ALTO, 2 → MEZZO_SOPRANO, 4 → SOPRANO**
  (`ClefInter.java:473-482`). The comment is explicit that "the kind changes if a
  C_CLEF / F_CLEF is moved up or down" (:260). [SRC]

This is **the same core insight as ReEngrave's `clef_geometry.py`** — a C-clef is
one glyph on different lines, so the line-position (not a class label) names it —
arrived at independently in both codebases.

**(4) Failure handling & switches.** Multiple candidate shapes are ranked and
resolved against key/measure context (`ClefKeyRelation`); a one-line staff
forces `PERCUSSION_CLEF` unless another shape is strong (`ClefInter.java:207`);
the ROI clamp prevents cross-staff bleed. [SRC]

**(5) ReEngrave + gap.** `clef_geometry.resolve_clef` (`clef_geometry.py:239`):
the YOLO/DSv2 detector supplies the **family** (G/C/F) from its class; geometry
snaps the bbox center to the nearest of 5 staff lines → `(family, line)` → clef
name; C-clefs only by default; abstains when residual > 0.35 spacing or the staff
lacks a clean 5-line read. `clef_locator.py` is a **classical-CV C-clef finder**
for scans where *no model* detects a clef (19th-c. C-clef prints, zero detections
even at conf 0.03). **The geometry half matches Audiveris; the gap is
detection**: Audiveris has a *trained clef classifier* that reliably *finds* the
clef and names its family, whereas ReEngrave's whole documented clef weakness is
that the DSv2 detector often finds no clef (or misfamilies it) on orchestral
scans (CLAUDE.md "clef detection is the documented ceiling"). Audiveris also
sizes its search ROI (`maxClefEnd 4.5`, `aboveStaff/belowStaff`) exactly like
ReEngrave's header window — but drives it with a classifier, not a general
object detector. [SRC]

**(6) Adoptability.** The geometry is already shared — validation, not adoption.
The adoptable idea is Audiveris's **dedicated, ROI-bounded clef shape
classifier** (a small model trained only to find & family-classify a clef in the
header ROI) as a replacement for asking the general YOLO detector to also do
clefs — this is essentially the "clef specialist" ReEngrave has tried and shelved
(CLAUDE.md `OMR_CLEF_WEIGHTS`), but Audiveris's version works because it is
**paired with the line-position geometry and a tight ROI**, not asked to
class-label alto vs tenor. Medium effort; conceptual, no code to lift.

### §5b KEY SIGNATURE

**(1) What & technique.** [DOC][SRC `sheet/key/KeyBuilder.java`,
`KeyColumn.java`, `KeyExtractor.java`, `KeyRoi.java`, `KeySlice.java`] A key sig
is a run of same-type accidentals in fixed order (**FCGDAEB** sharps, **BEADGCF**
flats), at positions fixed by clef (`KeyBuilder.java:82-88`). Audiveris:
1. On the **staff-line-removed** image, takes a **horizontal projection** of the
   header region and finds **peaks = "stem-like" portions**: **one stem per
   flat, two per sharp** (`KeyBuilder.java:96`).
2. Works **two concurrent hypotheses in parallel — all-flats vs all-sharps** —
   because the naive "flat has a trailing space, sharp doesn't" test is fragile
   (:118). The x-delta discriminates: **~0.5+ interline between the two stems of a
   sharp**, **~1+ interline between flats / between first-stems of adjacent
   sharps** (:97-99), with `maxSharpDelta` / `minFlatDelta` constants
   (`KeyBuilder.java:780/784`).
3. **Slices** the projection into one vertical region per accidental from the
   stem peaks + hypothesis (:93), and submits each slice's glyph compound to the
   **shape classifier** to validate the accidental (:123).
4. **Empty slices are force-segmented and re-recognized within the slice only**
   (:125) — i.e. a missed accidental is recovered by re-running recognition where
   the pattern says one must be.
5. Each accidental's pitch is checked **against the pitch sequence the clef
   candidate imposes** (:113); the last slice must be **followed by space** to fix
   the count (:126, via `min/max FlatTrail` / `SharpTrail` constants :744-764).
6. Across a system, `KeyColumn` **aligns slice abscissae between staves** and
   resolves inconsistencies (:multi-staff alignment). [DOC][SRC]

**(2) Params / pointers.** [SRC] `KeyBuilder.java` `Constants` (lines ~692–788):
`coreStemLength`, `stdGlyphHeight`, `minPeakCumul`, `peakAreaQuorum`,
`preStaffMargin`, `maxFirstPeakOffset`, `maxPeakWidth`,
`maxFlatHeading`, `std/min/maxFlatTrail`, `std/min/maxSharpTrail`,
`minSharp/FlatLightPeakDx`, `maxPeakDx`, **`maxSharpDelta` (:780)**,
**`minFlatDelta` (:784)**, `maxDeltaPitch_*`. Header width cap 15 interline
(§5). [SRC]

**(3) How it categorizes.** Sharp vs flat = **stem-count per peak (2 vs 1) + x-
delta pattern**, confirmed by the classifier per slice; count = number of
validated slices; identity (which sharps/flats) is forced by the fixed order and
the clef-imposed pitches. [DOC]

**(4) Failure handling.** Two-hypothesis parallelism, per-slice re-recognition of
empty slices, the trailing-space check, clef-pitch validation, and cross-staff
column alignment are all robustness layers. If a staff's key can't be resolved it
is left empty and reconciled from the system column. [DOC][SRC]

**(5) ReEngrave + gap.** `key_signature_geometry.fit_key_signature`
(`key_signature_geometry.py:241`) fits **already-observed accidental staff-
positions** to per-clef **slot tables** (`SHARP_PITCHES`/`FLAT_PITCHES`,
written out per clef incl. the tenor-clef exception — same exception Audiveris
names), **prefix-only**, solving a single shared glyph-anchor offset, recovering
**interior** gaps (slots seen at 1,2,4 ⇒ "four flats, third missed") but never
extending past the last observation, and abstaining out of tolerance.
`key_signature_vote.py` reconciles across staves/systems ≈ Audiveris's
`KeyColumn`. **Shared design: positional fit conditioned on the clef, cross-staff
vote.** The gaps vs Audiveris:
- ReEngrave **fits positions of things already detected** (the YOLO
  `keySharp`/`keyFlat` markers, or CV-located clusters); Audiveris **detects the
  accidentals itself** from the header projection + stem-count + per-slice
  classifier, so it does not depend on an external notehead detector seeing key
  markers at all — precisely the recall problem CLAUDE.md reports ("key sig recall
  about a half"; "the model finds *zero* key markers" on the header crop).
- ReEngrave *infers* an interior missed accidental from the pattern; Audiveris
  *re-recognizes* it in the forced slice — a stronger recovery.
- ReEngrave has no stem-count sharp/flat discriminator (it trusts the detector's
  class); Audiveris's **1-stem-flat / 2-stem-sharp projection peak** is a
  detector-free way to decide type. [SRC]

**(6) Adoptability.** **HIGH.** Two cleanly separable ideas: (a) the
**header-projection + stem-peak accidental detector** (one stem = flat, two =
sharp; x-delta ~0.5 vs ~1 interline) — a classical-CV key reader that does not
need the YOLO detector to have seen the accidentals, directly attacking
ReEngrave's ~50% key recall; (b) **force-segment-and-re-recognize an expected-
but-empty slot** rather than merely inferring it. Both pair with ReEngrave's
existing slot tables + vote. ⚠ clean-room the exact slice state machine and the
trailing-space constants. Medium effort; high payoff on a documented weakness.

### §5c TIME SIGNATURE

**(1) What & technique.** [DOC][SRC `sheet/time/HeaderTimeBuilder.java`,
`TimeBuilder.java`, `sig/inter/AbstractTimeInter.java` + `TimeWholeInter` /
`TimeNumberInter` / `TimePairInter` / `TimeCustomInter`] After the key, Audiveris
searches **three lookup regions** in the header:
- a **full-height** rectangle for **whole** shapes → `TimeWholeInter`:
  `COMMON_TIME`, `CUT_TIME`, or a combined glyph like `6/8`
  (`HeaderTimeBuilder.java:75,246 processWhole`);
- the **upper staff half** for a **numerator** digit;
- the **lower staff half** for a **denominator** digit
  (`processHalf(NUM|DEN)`, :418) → combined into a `TimePairInter` e.g. `[3,4]`
  (:78). [DOC][SRC]

**(2) Params / pointers.** [SRC] Three `HalfAdapter`s (whole/num/den, :101);
half ROI split at `roi.height/2` (:423). Shapes drawn from the classifier's
time vocabulary (`Shape.COMMON_TIME`, `Shape.CUT_TIME`, digit shapes).
System-consistency rule (below) is the key control. [SRC]

**(3) How it categorizes.** common/cut = a single **whole-shape** classification
in the full rectangle; numeric = a **numerator digit** (upper) + **denominator
digit** (lower) combined; a whole combined glyph (6/8) is also allowed as a whole
shape. `TimeCustomInter` covers exotic meters. [DOC][SRC]

**(4) Failure handling & switches.** **Strong system-level rule:** "**If, in a
staff header, no time signature was found, the search within the current system
is abandoned**" — i.e. a system either has the same time sig on all staves or
none (`HeaderTimeBuilder` doc). `score/TimeSignatureFixer.java` reconciles time
sigs across the page afterward. [DOC][SRC]

**(5) ReEngrave + gap.** `rhythm.parse_time_signature`
(`rhythm.py:195`) reads time-sig **digit detections** (dropping left-edge
instrument-number misreads), and `backfill_page_time_signatures` (`rhythm.py:525`)
infers a page meter conservatively from a dominant **C/cut-C glyph** else a
**per-column beat-sum vote**, staying `null` on dense pages rather than guessing
(CLAUDE.md; branch note). Gaps vs Audiveris:
- ReEngrave has **no numerator/denominator ROI split** — it relies on the general
  digit detector, which CLAUDE.md says "often misclassifies time-sig digits," so
  the field is null for many pages. Audiveris's **upper-half/lower-half geometric
  split + trained digit classifier** is a cleaner, more targeted reader.
- ReEngrave *infers* meter from beat-sums (a rhythm-side back-fill); Audiveris
  *recognizes* it from the header. Different philosophies — ReEngrave's beat-sum
  vote has no Audiveris analogue and is arguably more robust on unreadable prints,
  but it can't read an explicit meter the detector missed.
- ReEngrave has a per-staff **disagreement flag**
  (`transcribe._flag_time_signature_disagreement`) but **not** Audiveris's
  hard "all-or-none per system" rule. [SRC]

**(6) Adoptability.** Medium. The **numerator/denominator half-ROI reader**
(upper half → numerator, lower half → denominator, full height → common/cut) is a
clean, small classical-CV/classifier idea ReEngrave lacks and could add beside
its beat-sum back-fill. The **"same meter across a system or none" consistency
rule** is a cheap, high-precision guard worth adopting directly. Low-medium
effort.

---

## §6 — MEASURES

**(1) What & technique.** [DOC][SRC `sheet/rhythm/MeasuresBuilder.java`,
`MeasureStack.java`, `Measure.java`] Barlines themselves are found back in
**GRID** (`StaffProjector` peaks → `BarlineInter` / `StaffBarlineInter`; see
`audiveris-grid.md`). The **MEASURES** step, at **system level**, "ensures
barline consistency and builds all measures" (`MeasuresBuilder.java:62`): it
groups a staff's barlines (`buildGroups`, :111), builds a `StaffBarline` per
staff, and assembles a **`MeasureStack`** — one measure spanning **all staves /
parts of the system**, column-aligned. A `Measure` is the part-level slice of a
stack. [SRC]

**(2) Params / pointers.** [SRC] `MeasuresBuilder.java` `staffBarsMap`
(:86), `buildGroups` (:111); `MeasureStack.java` (the system-wide stack model);
`sheet/rhythm/MeasuresStep.java` (step wiring). Barline geometry constants live
in the GRID barline classes, not here. [SRC]

**(3) How it categorizes.** A vertical column that is a barline on the staves is
promoted to a **system-wide measure boundary** by cross-staff **consistency**;
the measure is a **stack** object (first-class), not a per-staff crop. Repeats,
double barlines etc. are barline *kinds* attached to the `StaffBarline`. [SRC]

**(4) Failure handling.** Cross-staff inconsistency is *reconciled* into a
consistent stack (that is the builder's stated job); rhythm-level checks come
later (`MeasureRhythm`, `MeasureFixer`, `PageRhythm`). [SRC]

**(5) ReEngrave + gap.** ReEngrave **fuses barline detection and measure
building** into `measure_extractor.py` and its unit of output is a **per-(staff ×
measure) image cell**, not a system stack:
- Barlines: per-staff morphological vertical opening + connected-component shape
  filter (height ≥ **0.80** span, width < **0.7** spacing, aspect ≥ 8,
  `_detect_barlines_in_window:70`), then a **system-level vote** with thresholds
  **tiered by system size** (≤2 all agree … >12 staves 50%, `detect_barlines:315`)
  and an **inter-staff connectivity** gate (real barline drawn *through* the gaps:
  0.4 filter / 0.7 rescue, `_intersystem_connectivity:203`), plus an **open-score
  detector** (if few accepted columns are connected, the score is one-staff-per-
  voice and votes stand alone, :362).
- Measures: `_measure_x_boundaries:458` uses **median** staff `x_start` for the
  system edge (guards a runaway staff), drops edge barlines within 2 spacings,
  absorbs a short tail; cells are canonically upscaled. A `resegment_fused_
  measures` pass re-splits >2×-median-width cells.

The **cross-staff agreement Audiveris gets structurally from the MeasureStack,
ReEngrave gets statistically from a vote + connectivity + resegmentation.** The
gap is the missing **stack abstraction**: ReEngrave has no object that says "this
is one measure of the system spanning these staves," so cross-staff facts
(same bar count, same boundaries) are re-derived repeatedly
(`majority_bars_by_system`, the resegmentation steering) rather than being an
invariant of the data model. This is also why a **merged system raises the vote
threshold and can lose all its barlines** (`repo-state.md:152`) — a failure mode
a stack built from column-aligned StaffBarlines does not have. [SRC]

**(6) Adoptability.** Medium-high (architectural). Adopt the **MeasureStack as a
first-class, system-spanning object** built from column-aligned per-staff
barlines — it makes "every staff in a system shares bar boundaries" an invariant
instead of a vote, and would retire the resegmentation/steering machinery and the
merged-system-loses-barlines bug. This is a data-model change, not a snippet;
conceptual, no AGPL exposure. Also cleanly adoptable: **separate barline
detection (in the staff/grid pass) from measure assembly** so the two are not
entangled as they are today.

---

## §7 — TEXTS (OCR + role classification) — **ReEngrave's largest TEXTS gap**

**(1) What & technique.** [SRC `text/SheetScanner.java`, `text/tesseract/
TesseractOCR.java`, `text/TextBuilder.java`, `text/TextRole.java`; TEXTS
handbook page is empty — "Documentation not yet provided"] Audiveris:
1. **Erases the music** — recognized inters + staff lines are removed to produce a
   **clean text-only image** (`SheetScanner.getCleanImage`, `TextsCleaner`,
   :127).
2. Runs **Google Tesseract on the WHOLE sheet** in **MULTI_BLOCK** layout mode
   (`SheetScanner.scanSheet:163`, `OcrUtil.scan(..., LayoutMode.MULTI_BLOCK,
   ...)`:177) — one OCR pass over the page, not per-region.
3. Structures output as **`TextLine` → `TextWord` → `TextChar`** (sentence /
   word / glyph hierarchy; `TextBuilder.java`).
4. **Classifies each line into a role** by geometry (`TextRole.guess`,
   `TextRole.java:123`). [SRC]

**(2) OCR engine.** [SRC] `TesseractOCR` is "an OCR service built on Google
Tesseract engine" (`TesseractOCR.java:55`), bound via **JavaCPP/bytedeco
presets** (`org.bytedeco:tesseract` in `app/build.gradle:93`; `TessBaseAPI`,
`GetAvailableLanguagesAsVector`). Language packs are `*.traineddata`
(`LANGUAGE_FILE_EXT`, :77); the bundled **tessdata tag is `4.1.0`**
(`gradle.properties:10`), i.e. LSTM-capable Tesseract 4/5-line models. Exact
library minor version [NOT FOUND — set via a gradle variable I did not resolve].

**(3) How it categorizes text roles.** [SRC] `TextRole` enum (:51): **Lyrics,
ChordName, Title, Direction, Number, PartName, Creator(+Arranger/Composer/
Lyricist), Rights, EndingNumber, Metronome, UnknownRole**. `guess()` decides by
**position and shape**, not content dictionaries:
- vertical **StaffPosition** (ABOVE / WITHIN / BELOW staves) and **part**
  position (`:163-167`);
- **first system? last system?** (`:157-160`) — creators/title live on system 1;
- **page-centered** (Title/Number, `:180-182`), **left-of-staves** (Lyricist /
  Metronome, `:216`), **right-aligned** (Composer, `:222`);
- **title height** ≥ `minTitleHeight` ⇒ Title else Number (`:198,233`);
- **tiny/short** sentence, **all-chord-symbols** ⇒ ChordName (`:145,208`),
  **italic** hint, **has-vowel** hint for lyrics (`:202`);
- close-to-staff + not chords ⇒ **Direction** (`:226-230`). [SRC]

**(4) Failure handling & switches.** Processing switches gate roles
(`lyricsAboveStaff`, metronome allowed, manual mode); `UnknownRole` is the safe
default; roles are user-correctable (`sig/ui/SentenceRoleTask.java`). Running OCR
on the **music-erased** image is itself the main robustness move — Tesseract
never sees noteheads. [SRC]

**(5) ReEngrave + gap.** **ReEngrave does no raster OCR and recognizes only
instrument margin labels.** `staff_labels.read_staff_labels`
(`staff_labels.py:159`) reads the **PDF text layer** (PyMuPDF), maps PDF-pt →
deskewed-px (replicating the render+deskew transform, `_pdf_to_pixel_transform:77`
— skipping the deskew step would be a real error, ~17 px at 1°), keeps spans
**left of the staves**, groups by nearest staff, joins per staff, and looks the
joined string up in a fixed **instrument lexicon** (`instruments.py`). Fallbacks
for text-layer-less scans are **Surya** (`staff_labels_surya.py`) and **Claude
vision** (`staff_labels_vision.py`). The gaps:
- **No general OCR** — only ~28% of IMSLP PDFs carry a usable text layer
  (`staff_labels.py:6`); the rest need Surya/vision, and even then ReEngrave
  reads **only instrument names**. Titles, tempo/direction words, lyrics, chord
  names, rehearsal marks, endings are **entirely unread** (CLAUDE.md: "SKIP free
  text — no class exists"). Audiveris reads and *roles* all of them.
- **No role taxonomy** — ReEngrave has one implicit role (instrument/part name);
  Audiveris has ~12, assigned by position.
- **No "erase music then OCR"** — ReEngrave never OCRs the raster, so it cannot
  reach text on scans without a text layer except via the paid/vision path. [SRC]

**(6) Adoptability.** **HIGH (for breadth), and philosophically the biggest
difference.** Two clean, framework-agnostic ideas: (a) **erase recognized
music + staff lines, then run one whole-sheet OCR pass** (Tesseract is itself
AGPL, but the *pipeline pattern* is not; ReEngrave already erases staff lines in
`staff_line_removal.py`, so a "clean sheet" image is within reach); (b) the
**position-based role taxonomy** — classify a recognized text line into
title/creator/direction/lyric/chord/part-name by staff-position + page-centering
+ height + first/last-system, no content dictionary. ReEngrave could adopt the
role rules on top of *any* text source (PDF layer, Surya, vision) to get
titles/directions/lyrics it currently discards. ⚠ clean-room the exact
`guess()` decision tree; the *taxonomy and cues* are the idea. Low-medium effort
for the role classifier; larger for a full OCR integration.

---

## Top adoptable ideas from this slice (ranked)

1. **A standalone SCALE step from vertical-run-length histograms** (§3).
   Interline + line-thickness + beam-thickness as page-level master units, before
   staves. Breaks ReEngrave's spacing↔detection circularity, would have caught
   the tiny-mediabox zero-staff and DPI-dependent bugs, gives `line_detection` a
   beam unit, and adds native two-population (cue/ossia) support. Classic
   technique (no AGPL risk to the *method*); ⚠ clean-room the peak-bounds
   constants. **Highest structural payoff.**

2. **A left-margin brace/bracket detector for part formation** (§4c).
   ReEngrave has *no* brace/bracket detection and infers group boundaries from an
   edition-fragile barline-density proxy that causes the standing grouping
   over-merges. A curved-filament brace + serif-bracket detector gives a direct
   structural part cue, runs before YOLO (classical CV), needs no new training
   class. **Directly de-risks this directory's system-grouping benchmark.**

3. **A header-projection key-signature reader (1-stem-flat / 2-stem-sharp) with
   force-re-recognition of empty slots** (§5b). Detects accidentals from the
   header itself instead of depending on the YOLO detector seeing key markers —
   attacks ReEngrave's documented ~50% key recall — and pairs with its existing
   slot tables + cross-staff vote.

Honorable mentions: the **MeasureStack** as a first-class system-spanning object
(§6, retires the vote/resegmentation machinery and the merged-system-loses-
barlines bug); the **numerator/denominator half-ROI time reader + "same meter
per system or none" rule** (§5c); and the **position-based text-role taxonomy**
(§7) to recover titles/directions/lyrics ReEngrave currently discards.

**Two validations (not gaps):** ReEngrave's **clef-by-geometry** (`clef_geometry
.py`) is the *same* insight as Audiveris's `ClefInter.kindOf`/`cKindOf` (C-clef
line from glyph center), and its **Sauvola binarization** matches Audiveris's
adaptive-filter intent — both arrived at independently.
