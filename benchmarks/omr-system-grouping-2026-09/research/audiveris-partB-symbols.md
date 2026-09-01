# Audiveris Part B — Symbol Detection & Fixed-Shape Classification

2026-09-01. Deep-dive (sub-agent). Sources: official repo `github.com/Audiveris/audiveris`
(master, AGPL-3.0) + handbook `audiveris.github.io/audiveris` + official
`Audiveris/omr-dataset-tools` wiki. **Clean-room notice:** everything below is
algorithm / parameter / architecture (facts, not copyrightable), written in my
own words for independent reimplementation. No Audiveris source is reproduced or
close-paraphrased. Citations are `file` + method/constant name (+ line number as
a locator; line numbers come from a summarizing fetch and are approximate — the
method/constant name is the reliable anchor).

Tags: **[DOC]** handbook · **[SRC]** read in source · **[INFERENCE]** reasoned ·
**[NOT FOUND]** looked, absent.

---

## 0. The headline — Audiveris's *division of labor* (the key insight)

Audiveris does **not** run one detector over the page. It splits recognition
into three engines by *what kind of thing* is being found, and each engine is
matched to the geometry of its target:

| Engine | Handles | Why this engine | Where |
|---|---|---|---|
| **Distance-transform template matching** | note **heads** (black / void / whole + cross/diamond/triangle/circle motifs) | heads are a small fixed set of rigid shapes whose exact pixel geometry and *pitch position* matter | `image/Template.java`, `image/TemplateFactory.java`, `sheet/note/NoteHeadsBuilder.java` [SRC] |
| **Learned shape classifier** (shallow neural net on *moment* features) | every fixed-shape symbol that is **not** a head or a thin line: clefs, accidentals, rests, flags, dynamics, articulations, ornaments, time digits, tuplets, dots | these vary in font/style and are best learned, but they are compact blobs where a moment descriptor is stable | `classifier/BasicClassifier.java`, `glyph/GlyphCluster.java` [SRC] |
| **Classical CV** (filaments + morphology + connected components) | **stems, beams, ledgers** (and staff lines, barlines) | thin/elongated ink that a bounding box or a moment vector describes badly; found geometrically instead | `sheet/stem/*`, `sheet/beam/*`, `sheet/ledger/*` [SRC/DOC] |

**The decision rule is geometric, not learned.** Rigid + pitch-critical → template.
Thin/elongated → classical CV. Everything else compact → learned classifier. This
is the single most important thing to carry back to ReEngrave: Audiveris *never
asks one model to learn both thin lines and fixed shapes*, and it *never asks the
learned classifier to place heads*. ReEngrave arrived at the same split from the
opposite direction — it uses one YOLO model for the compact-symbol job and was
forced to peel stems/beams out to classical CV (`line_detection.py`) and to peel
head *placement* out to `pitch_resolver.py` — but it has not peeled heads out of
YOLO detection, which is exactly the seam Audiveris cuts most deliberately (§6.1).

Ordering matters too: STEM_SEEDS → BEAMS → LEDGERS → **HEADS** → STEMS → …
→ SYMBOLS. Heads are found *before* full stems, seeded by stem *seeds* and by
ledger/line pitch positions; the learned classifier (SYMBOLS) runs late, on the
ink left over after heads/stems/beams/ledgers are removed. [DOC] handbook step
pages; [SRC] `OmrStep`/`*Step.java` ordering.

---

## 1. HEADS — distance-transform template matching (centerpiece #1)

This is the technique most unlike ReEngrave's YOLO, and the one most worth
copying. [DOC] `steps/heads/` + [SRC] `image/Template.java`,
`image/TemplateFactory.java`, `sheet/note/NoteHeadsBuilder.java`.

### 1.1 The distance table (the image side of the match)

Audiveris does not correlate a template against raw pixels. It builds a
**distance table** over the sheet once (`image/DistanceTable.java`,
`image/ChamferDistance.java`, built in `sheet/note/DistancesBuilder.java`): each
pixel holds the **Euclidean (Chamfer-approximated) distance to the nearest
foreground/black pixel**, with foreground = 0. Pixels belonging to already-known
structures — **staff lines, ledgers, stems** — are set to **−1 ("ignore")** so
they neither help nor hurt a head match. [DOC] heads page: *"the euclidian
distance from the (x,y) pixel to the nearest foreground (black) pixel"*, `−1` for
ignored locations. This means the head matcher sees a *clean* field with the
thin-line clutter already subtracted — the same instinct as ReEngrave feeding
`image_no_staff` to its CV, but generalized to a full distance field.

### 1.2 The template (the model side of the match)

A `Template` is a list of **key points**, each an expected distance value `d`
(`image/Template.java`, `PixelDistance`) [SRC]:

- `d == 0` → **foreground** (the inked ring/body of the head),
- `d < 0` → **hole** (the interior white of a void/whole head — negative distance
  marks "this should be *empty*, and the deeper inside the hole, the more so"),
- `d > 0` → **background** (exterior; should be white, at a known distance).

Templates are **generated from a music font**, not hand-drawn
(`TemplateFactory.buildTemplate`, `TemplateSymbol.buildImage`): render the SMuFL
glyph to gray, binarize to FORE/BACK by alpha+color threshold, **flood-fill the
interior seed points** to mark HOLE pixels, then run **Chamfer distance**
(`ChamferDistance.Short().compute()`) to fill background distances and assign
negative distances inside the holes (`buildDistances`, `setHoleDistances`). [SRC]
Templates are keyed by **(MusicFamily font, pointSize/interline, Shape)** in a
per-family/size `Catalog` — so a head template is always at the sheet's own
scale (interline), never resized at match time. Shapes templated = `ShapeSet.Heads`:
oval black/void/whole/breve + small variants + cross / diamond / triangle-down /
circle-X motifs. [SRC] `TemplateFactory` line ~1035.

### 1.3 The match score (the weighting is the clever bit)

`Template.evaluate()` slides the key points over the distance table at a location
and computes a **weighted mean of per-pixel distances** (lower = better match),
with three weights [SRC/DOC]:

| region | weight | constant name |
|---|---:|---|
| foreground (`d==0`) | **6.0** | "weight for template foreground pixels" |
| hole / interior background (`d<0`) | **4.0** | "weight for interior background pixels" |
| exterior background (`d>0`) | **1.0** | "weight for exterior background pixels" |

Foreground evidence dominates (6×); the **interior gets its own heavy weight
(4×)** and *this is what separates black from void from whole*: a **black** head
must have ink where a void head has a hole, so scoring the interior against the
distance field with a 4× weight makes a black-vs-void confusion expensive. A
final reclassification guard, `minHoleWhiteRatio = 0.2` in `NoteHeadsBuilder`,
downgrades a nominally-BLACK head to VOID when its interior is actually ≥20% white
[SRC]. Exterior gets 1× — enough to punish a template that floats in a blob but
not so much that neighbouring ink kills a real head.

Acceptance / early-abandon constants (`Template` / `NoteHeadsBuilder`) [SRC]:
`maxDistanceHigh ≈ 0.5` (worst acceptable), `maxDistanceLow ≈ 0.40` (a *good*
match), `reallyBadDistance ≈ 1.0` (stop evaluating this location — a speed
guard), `dilation ≈ 0.2` (erosion applied to a matched head so it does not
re-trigger neighbours).

### 1.4 Two passes, and pitch-constrained placement

`NoteHeadsBuilder.buildHeads()` runs **two passes per staff** [SRC]:

1. **Stem-seed pass** (`processStaff(…, true)` → `Scanner.lookupSeeds`): only near
   detected **stem seeds**, using stem-anchored templates (`LEFT_STEM`,
   `RIGHT_STEM` anchors — see §1.5), exploring small x/y offset grids
   (`computeXOffsets` length = maxStem, pattern 0,±1,±2…; `computeYOffsets`). It
   records the actual seed→head abscissa `dx` for later consolidation.
2. **Full-range pass** (`processStaff(…, false)` → `Scanner.lookupRange`): scans
   all abscissae over the staff/ledger extent. **Black-head candidate abscissae
   are pre-filtered by "head spots"** (`HeadSpotsBuilder`,
   `getRelevantBlackAbscissae`) — a cheap morphological pre-detection that says
   "a black blob is roughly here" so the expensive template scan is not run
   everywhere; void/whole (hollow) templates are tried more broadly.

Crucially, the **vertical position is not free** — it is snapped to pitch.
`getTheoreticalOrdinate(x)` maps each candidate pitch (line = even pitch, space =
odd pitch, ledgers included) to a y, and the y-search only wanders ±`maxOpenDy`
(≈0.2 interline in spaces) / `maxClosedDy` (0 on lines) around it [SRC]. So a head
can only land where a note could actually sit. Competing candidates are then
pruned: `isSameAs` (same location within `maxTemplateDx ≈ 0.375` interline → keep
higher grade), `overlaps` (→ formal exclusion in the graph), and
`filterSeedConflicts` (x-based vs seed-based head resolved by IoU with a
`gradeMargin ≈ 0.1` boost to the seed-based one; `minIouHeads ≈ 0.1`). [SRC]

### 1.5 Anchors — how a head knows where its stem attaches

`Template.addAnchors()` stamps named reference points on each template: `CENTER`,
`MIDDLE_LEFT/RIGHT`, and stem points (`LEFT_STEM`, `RIGHT_STEM`, `TOP_LEFT_STEM`…)
[SRC]. `getOffset(anchor)` converts an anchor to a pixel offset from the template
corner. This is how the head-detection and stem-linking steps agree on the exact
attach point without re-deriving it — the seed pass positions templates *by* the
stem anchor.

**Head output** = a `HeadInter` with shape (black/void/whole + motif), pitch
position, and an **intrinsic grade** derived from the template distance (a good
distance ~0.40 maps to a high grade; see §5).

---

## 2. STEM SEEDS & STEMS — classical CV (vertical filaments)

[DOC] `steps/stem_seeds/`, `steps/stems/`; [SRC] `sheet/stem/*`.

- **Scale first.** The SCALE step estimates interline, staff-line thickness and
  beam thickness from **histograms of vertical run-lengths** (combo histogram =
  black run + following white run → interline; black histogram peaks → line
  thickness, then beam thickness). STEM_SEEDS separately measures **stem
  thickness** from a histogram of horizontal black runs in staff areas with
  lines/barlines/headers removed. [DOC] `sheet_scale`. This global scale is what
  lets every later threshold be expressed in *interline fractions* rather than
  pixels — the same normalization ReEngrave gets by rescaling cells to a canonical
  staff span.
- **Seeds = vertical filaments.** Build straight vertical filaments from vertical
  ink sections that are *slim enough and long enough*, thickening with compatible
  adjacent sections up to the stem-thickness limit. Each filament is scored on
  **slope, straightness, length, cleanliness (few adjacent pixels, high black
  fraction, low white fraction)**; check rigor scales with a **sheet-quality
  setting (synthetic / standard / poor)**. Survivors are tagged `VERTICAL_SEED`.
  [DOC] `VerticalsBuilder`, `StemSeedsStep` [SRC].
- **Seeds feed everything.** Seeds are consumed by beams, ledgers, **heads**
  (§1.4) and finally full stem assembly (`StemsRetriever`, `StemBuilder`,
  `StemChecker`, `HeadLinker`, `BeamLinker`), which stitches seeds + head anchors
  + beam ends into real stems and prunes with `StemChecker`. [SRC]

**Contrast with ReEngrave:** ReEngrave's `line_detection.detect_stems` is a *much
simpler* single-pass morphological opening (vertical kernel ≈ `2.0×0.8` interline
tall) + connected-components + range/edge/aspect filters + a bespoke
"drop-paired-strokes" rule to reject sharp/natural verticals. Audiveris's
filament approach is a genuine *straight-line fit* with slope/straightness/
cleanliness scoring and a quality dial, and it recovers *broken* stems by
thickening from sections — both things ReEngrave's opening cannot do (a broken
stem falls under the height floor and is dropped). See §6.2.

---

## 3. BEAMS — morphological "spots" (thick slanted ink)

[DOC] `steps/beams/`; [SRC] `sheet/beam/SpotsBuilder.java`, `BeamsBuilder.java`,
`BeamStructure.java`.

Pipeline (`SpotsBuilder`) [SRC]:
1. Start from the **no-staff** image; suppress stem-like ink (filter horizontal
   runs narrower than max stem thickness).
2. **Median 3×3 → Gaussian** smoothing.
3. **Morphological closing** with a **circular structuring element** whose
   diameter = `beamThickness × beamCircleDiameterRatio` (default **0.8**) — i.e.
   a disk ~80% of a beam's thickness. Closing fills a true beam into a solid
   "spot" while thinner ink collapses. This is the crux: the structuring element
   is *sized to the measured beam scale*, so "thick" is defined relative to the
   sheet.
4. **Binarize** the closed gray image (beam-spot threshold ≈ **140**; a separate
   head-spot pass uses ≈ **170**), build vertical runs → `RunTable` →
   `GlyphFactory.buildGlyphs`, tag `GlyphGroup.BEAM_SPOT`.

Then `BeamsBuilder` filters each spot by **width, mean thickness, and center-line
slope (least-squares)**, examines the **top/bottom borders of the most
significant vertical sections** for straight, consistently-sloped edges, and
**splits a thick spot into N stacked elementary beams** before emitting beam
`Inter`s. [DOC] Beams are then linked to stems (`BeamLinker`). Cue/grace beams are
a separate smaller-scale pass (`CueBeamsStep`). [SRC]

**Contrast with ReEngrave:** ReEngrave's `detect_beams` also uses a horizontal
opening + connected components, but its decisive filter is *"a beam is horizontal
ink that ≥2 stems END at"* (`_attached_stem_count`) plus run-counting to split
stacked bars (`_stacked_bar_count`) — it leans on stems to *define* a beam.
Audiveris defines a beam morphologically first (disk-closing at beam scale), then
*validates* geometry, then links stems. Both split stacked beams by counting, and
both size the kernel to the beam/staff scale. Audiveris's scale-sized disk-closing
is more robust to sloped beams than a rectangular opening (a rectangle at a slope
under-fills; a disk does not), which is precisely the failure mode ReEngrave
documents (sloped beams fill 43–46% of their box). See §6.3.

---

## 4. LEDGERS — short horizontal filaments, grown outward

[DOC] `steps/ledgers/`; [SRC] `sheet/ledger/LedgersFilter.java`,
`LedgersBuilder.java`, `LedgersPostAnalysis.java`.

- **Prolog** (`LedgersFilter`): from the no-staff image, erase each staff's band
  (augmented by a half-interline margin) so only extra-staff ink remains; make a
  horizontal `RunTable`; build sections by joining only adjacent runs with
  identical start/end abscissae.
- **Core** (`LedgersBuilder`): a horizontal **stick factory** builds short
  straight horizontal filaments (the horizontal mirror of stem seeds). Ledgers are
  found **progressively outward**: one interline above the staff and going up one
  interline at a time; one interline below and going down — each new ledger must
  be adjacent to the previous line/ledger. Weighted validation: min length,
  thickness bounds, straightness, **vertical-position accuracy**, and **convexity
  on the horizontal ends** (white pixels above *and* below the tip — a real ledger
  is a free-floating dash, not a continuation of other ink).
- **Epilog** (`LedgersPostAnalysis`): compute mean/σ of ledger attributes over the
  whole system and re-filter outliers on spacing/thickness before REDUCTION.

**Contrast with ReEngrave:** ReEngrave has **no dedicated ledger detector** —
`ledgerLine` exists as a DSv2/YOLO class but the notes call ledger lines
"low-value" to box, and pitch of ledger-line notes is handled purely by
`pitch_resolver` extrapolating the staff-line ladder past the staff. Audiveris's
"grow one interline at a time, require convex ends" is a cheap, deterministic
ledger finder ReEngrave lacks entirely. See §6.4.

---

## 5. THE GLYPH CLASSIFIER — learned fixed-shape recognition (centerpiece #2)

This is the other thing most unlike YOLO. It names **rests, flags, accidentals,
clefs, dynamics, articulations, ornaments, time digits, tuplets, dots** — every
compact fixed shape that is not a head and not a thin line.

### 5.1 What model — and the basic/deep history (important, and current)

- **Active default = `BasicClassifier`** [SRC], whose own header calls it *"the
  pre-DL4J classifier, based on a home-built shallow network operating on
  MixGlyphDescriptor."* It is a **single-hidden-layer MLP**: input =
  `descriptor.length()`; **one hidden layer with as many cells as the output**;
  output = one neuron per physical shape (`createModel`). Trained by
  backprop with `learningRate 0.1`, `momentum 0.9`, `L2 lambda 1e-4`,
  `maxEpochs 100`; features **Z-normalized** (subtract mean, divide by σ) using
  stored `BasicNorms`. Persisted as **`basic-classifier.zip`** (marshalled
  weights + normalization vectors). [SRC] `classifier/BasicClassifier.java`.
- **A "deep" classifier exists only historically / externally.** `ShapeClassifier`
  (the indirection point) currently returns `BasicClassifier` and has the deep
  path **commented out** (`getSecondInstance`, `useDeepClassifier=false`) [SRC].
  **There is no `DeepClassifier.java` (or any `Deep`/`CNN`/`Conv` file) in the
  current `classifier/` package** [SRC — full dir listing]. The DL4J CNN is
  described in the official `omr-dataset-tools` wiki as a **6-layer network**
  (`Convolution → Subsampling → Convolution → Subsampling → Dense → Output`) *"very
  similar to the one in use within Audiveris V5"* on **DeepLearning4J** [DOC].
  **So: Audiveris V5 shipped/experimented with a DL4J CNN, but current master
  defaults to — and appears to only ship — the shallow moment-based net; the deep
  classifier lives in the companion dataset-tools project and is disabled in the
  app.** [INFERENCE from SRC+DOC — a strong, load-bearing finding for ReEngrave:
  the most mature engine walked *back* from a deep image CNN to a shallow
  moment-feature net for compact-symbol naming.]

### 5.2 Input representation — MOMENTS, not pixels (the load-bearing difference)

The active classifier is fed **`MixGlyphDescriptor`** [SRC]: a compact
**feature vector**, `LENGTH = ARTMoments.MOMENT_COUNT + GeoGlyphDescriptor.MOMENT_COUNT(=10) + 1(aspect)`:

- **ART moments** — MPEG-7 **Angular Radial Transform** region-shape coefficients
  (angular × radial grid, excluding the (0,0) DC term). [SRC — count not read
  directly; MPEG-7 ART is a 12×3 grid = 36, i.e. **~35 excluding DC** — [INFERENCE]].
- **10 geometric moments** (`GeoGlyphDescriptor`, `GeometricMoments`, computed at
  the sheet interline for scale-normalization) [SRC].
- **aspect ratio** (height/width) [SRC].

So the total input is a **~46-dimensional normalized moment vector** [INFERENCE on
the exact ART count]. There is a *second*, unused-by-default `ImgGlyphDescriptor`
that flattens a glyph into a **fixed 24×48 = 1152-pixel image** (`ScaledBuffer`,
`WIDTH=24`, `HEIGHT=48`, interline-normalized to reference INTERLINE=5, **centroid-
centered** with averaging on down-scale) — that is the *deep* classifier's input,
kept for training-data export but not driving recognition. [SRC]

**This is the crux for ReEngrave.** Audiveris's working classifier describes a
symbol by *rotation/scale-stable moments of a normalized blob*, decided in
isolation, and only ~46 numbers wide. YOLO describes symbols by *learned
convolutional features over raw page pixels with spatial context*. The moment
route needs the glyph already segmented (which the CV steps provide) but is tiny,
fast, retrainable on a handful of samples, and immune to the density/scale prior
that wrecks ReEngrave's YOLO at the wrong `imgsz`.

### 5.3 How candidate glyphs are formed — combine sections, then classify

Audiveris does not have pre-drawn boxes to classify; it **builds** them. In the
SYMBOLS step, after heads/stems/beams/ledgers ink is removed, the remaining ink
**sections** are aggregated into candidate glyphs by **`GlyphCluster`** [SRC]:

- Sort parts by **descending weight**; use the heaviest as a **seed**.
- **Recursively add nearby "outlier" parts** that the `GlyphLink` graph connects
  within `maxPartGap`; a `considered` set prevents re-evaluating the same subset.
- **Prune before classifying**: reject a combination whose total weight is too
  high/low or whose bounding box exceeds shape-plausible limits.
- For each surviving combination, build a compound glyph
  (`GlyphFactory.buildGlyph`) and call `adapter.evaluateGlyph()` → the classifier.

So the classifier is asked *"what is this particular grouping of sections?"* for
many groupings, and the graph-distance + weight/bbox pruning keeps the
combinatorics bounded. This "**try connected-section combinations, classify each,
keep the best consistent set**" is fundamentally different from one forward pass
of a detector, and it is how Audiveris copes with broken/merged glyphs.

### 5.4 The shape vocabulary

`glyph/Shape.java` defines **~180+ enum constants**, partitioned into **physical**
(trainable, appearance-defined; up to `LAST_PHYSICAL_SHAPE`) and **logical**
(context-defined) shapes; the classifier only outputs **physical** shapes
(`ShapeSet.allPhysicalShapes`, `getPhysicalShapeNames`). [SRC] Families
(`glyph/ShapeSet.java` sets) [SRC]:

Clefs (G/F/C/percussion + small/change variants) · Accidentals (flat, natural,
sharp, double-sharp, double-flat) · Time (TIME_ZERO…TIME_NINE, COMMON/CUT,
predefined ratios) · Rests (multiple/long/breve…128th) · Flags (FLAG_1…FLAG_5
up/down + small) · Heads (the oval/cross/diamond/triangle/circle motif sets — but
these go to the *template* matcher, not the learned net) · Articulations (accent,
tenuto, staccato, staccatissimo, marcato, arpeggiato) · Dynamics (P…FFF, MF, SFZ,
crescendo/diminuendo) · Ornaments (trill, turn, turn-inverted, mordent) · Digits
(0–5, for time & tuplets) · Tuplets (3, 6) · Barlines/repeats · Octave marks
(8va/15ma/22) · Key items (KEY_FLAT_1…7, KEY_SHARP_1…7) · Braces/brackets/
ledger/stem/staff (structural markers).

**Cross-reference to ReEngrave's DSv2 208-class space** (`deepscores_classes.py`,
135-class snapshot): the *families* overlap almost exactly, but the granularity
differs. DSv2 splits by geometry the classifier would rather learn as one
(`noteheadBlackOnLine` vs `…InSpace` vs `…Small` = 16 head classes; Audiveris has
one BLACK head template + pitch snapping). Audiveris folds *on/in-line* into
geometry (pitch), not into the label — the opposite of DSv2, which bakes it into
the class. That directly explains why ReEngrave's YOLO wastes capacity on
line/space/small head variants that a geometry step could recover for free.

### 5.5 Output — a shape + a grade, then geometric checks

- `Evaluation` = **{shape, grade, failure}** [SRC]. Grade is *"larger is better,
  generally provided by the neural network classifier in the range 0–1"*; special
  sentinels `ALGORITHM=2.0`, `MANUAL=3.0` mark non-classifier assignments.
- `AbstractClassifier.getSortedEvaluations` returns all shapes sorted by grade;
  `evaluate(...)` filters by `minGrade`, a `count` cap, and — when
  `Condition.CHECKED` — runs **`ShapeChecker`** (§5.6), skipping any evaluation
  whose `failure` got set and de-duplicating shapes a check rewrote. A glyph too
  small (`minWeight ≈ 0.04` of a reference area) is rejected as noise
  (`isBigEnough`). [SRC]

### 5.6 `ShapeChecker` — context-aware post-classification (a distinct, adoptable layer)

`glyph/ShapeChecker.java` [SRC] is a **framework of geometric/contextual checks
that gate or rewrite the classifier's raw answer**. Each `Checker` targets a shape
set and returns pass/fail; a fail annotates `eval.failure` (rejecting that shape,
falling through to the next candidate), and a pass may **rewrite the shape**
(`correctShape`). Concrete examples read from source:

- **MeasureRest**: a physical half/whole-rest candidate is resolved to
  `HALF_REST` vs `WHOLE_REST` **by pitch position** (the rest hangs from vs sits
  on the line — pitch×2 lookup tables); rejected near a stem or off a tablature
  range. *(The half/whole rest glyph is genuinely ambiguous in isolation; only
  pitch disambiguates.)*
- **NotWithinWidth**: reject any physical shape whose box falls outside the
  system's horizontal bounds (brackets/braces/text exempt).
- **Text**: reject "text" whose height/pitch exceeds limits (≤4.0 interline title,
  ≤2.5 lyric) — separates symbols from words.
- **Tuplet**: reject unless pitch position within `maxTupletPitchPosition ≈ 17`.
- **BelowStaff (pedals)** / **AboveStaff (markers)**: pedal marks must be below the
  staff (pitch > 4), segno/coda markers above (pitch < −4).

This is a *centralized, per-shape geometric sanity layer sitting between the
classifier and the graph* — ReEngrave has the same instincts but scattered as
ad-hoc gates (rest y-band, staff-vicinity text gate in `template_matcher.py`; the
internal-consistency checks in `transcribe`). See §6.6.

### 5.7 Grades — intrinsic vs contextual, and per-shape floors

`glyph/Grades.java` [SRC]:
- **Intrinsic grade** = the classifier's own confidence, **scaled ×`intrinsicRatio
  = 0.8`** to leave headroom for context.
- **Contextual grade** = intrinsic **boosted by supporting relations** in the
  symbol-interpretation graph (a head that has a stem and a beam is more credible
  than one alone); `minContextualGrade = 0.5`, `goodInterGrade = 0.5`.
- **Per-shape acceptance floors** — different symbols are trusted at different
  levels: `symbolMinGrade 0.15`, `ratherGoodHeadGrade 0.3`, `goodBeamGrade 0.35`,
  `timeMinGrade 0.1`, `clefMinGrade 0.03`, `keySigMinGrade 0.01`,
  `minInterGrade 0.1`. A clef is accepted at grade 0.03 (few things look like a
  clef, and it's structurally load-bearing) while a generic symbol needs 0.15.

**ReEngrave uses a single flat `OMR_CONF_THRESHOLD = 0.25` for every class.** The
per-shape floor + an intrinsic/contextual split is a direct, cheap upgrade (§6.7).

---

## 6. Flags, rests, dots — the rest of the fixed-shape families

- **Flags** — no separate detector; `FLAG_1…FLAG_5` (up/down + small) are physical
  classifier shapes recognized in SYMBOLS, then linked to a stem end. [SRC — no
  flag file in `sheet/symbol/`; flags in `ShapeSet.Flags`.] ReEngrave carries the
  same DSv2 flag classes but must fight false flags with height/vicinity gates
  (`template_matcher.py`) because YOLO fires flag-shaped text; Audiveris avoids
  that because the classifier only sees a *segmented glyph near a stem*, not raw
  page text.
- **Rests** — physical classifier shapes (`ShapeSet.Rests`); half/whole
  disambiguation is a **`ShapeChecker` pitch check** (§5.6), and multi-measure
  rests get a dedicated `MultipleRestsBuilder`. [SRC]
- **Augmentation dots** — handled by **`sheet/symbol/DotFactory.java`** [SRC], a
  **two-pass disambiguator** because one round dot can be augmentation / staccato /
  repeat / (part of a) fermata:
  - *First pass (instant)*: cheap tests while symbols are built —
    `instantCheckRepeat` (dot at a barline & correct pitch → `RepeatDotInter` +
    `RepeatDotBarRelation`), `instantCheckStaccato` (dot hugging a head-chord →
    articulation), and `instantDotChecks` rejecting dots stuck to a staff line /
    ledger (`checkDistanceToConcreteLine`, reject within **0.3 interline** of a
    line).
  - *Second pass (late, once all symbols exist)*: `lateNoteAugmentationCheck`
    links a dot to the nearest note/rest chord (`AugmentationDotInter` +
    `AugmentationRelation`); `lateDotAugmentationCheck` finds the *second* dot of a
    double-dot; `lateRepeatChecks` pairs upper/lower repeat dots.
  ReEngrave has `augmentationDot` as a YOLO class (mapped to `structural`) but
  **no disambiguation** from staccato/repeat and no dot→note linking — this is a
  known gap the DotFactory pattern fills. See §6.5.

---

## 7. Map to ReEngrave — right / wrong / adoptable, per seam

ReEngrave today (`tools/omr/`, CLAUDE.md): one **YOLOv8l** (208-class DSv2 space)
run on canonically-rescaled **measure cells** at a target staff-space of 16 px
(`yolo_detector.imgsz_for_cell`); class names → SMuFL categories
(`_CATEGORY_MAP`); **classical CV** for stems/beams (`line_detection.py`);
**geometric** pitch from notehead-y + clef anchors (`pitch_resolver.py`). A
**legacy `template_matcher.py`** (sliding-window NCC for heads + Hu-moment screen
→ NCC for other CCs) predates and parallels the YOLO path.

### 6.1 HEADS — biggest opportunity
- Audiveris right: heads via **distance-transform templates**, scale-locked to
  interline, **pitch-constrained y**, stem-seeded, black/void/whole separated by
  the **interior weight**. Deterministic, no training, no density prior.
- ReEngrave wrong: YOLO note detection is a **learned bounding-box** job with a
  brutal scale cliff (the `TARGET_STAFF_SPACE_PX=16` comment: past ~25 px it finds
  *fragments*, note count 1.4–1.9× truth). It over-reports and mis-locates.
- **Adoptable — and ReEngrave already owns every ingredient:** it has staff lines
  + clef + pitch positions (`pitch_resolver`), a **Bravura SMuFL archetype
  library** (`symbol_library/`), a staff-removed image, and even a legacy NCC head
  matcher. Swapping NCC-on-raw-pixels for **Chamfer-distance templates on a
  distance table with 6/4/1 foreground/hole/exterior weighting**, seeded on
  `detect_stems` output and snapped to `pitch_resolver`'s theoretical ordinates,
  is a near-drop-in that would fix both the over-count and the black/void split
  without any model. This is the single highest-value port.

### 6.2 STEMS
- Audiveris right: **straight-filament fit** with slope/straightness/cleanliness
  scoring + a **sheet-quality dial**, recovering broken stems by thickening
  sections.
- ReEngrave: `detect_stems` is a one-shot vertical opening + CC + filters + a
  clever "drop paired accidental strokes" rule. It **cannot** recover a broken
  stem (falls under the height floor) and hard-codes thresholds it had to tune per
  corpus.
- Adoptable: a straightness/slope score and section-thickening would harden stems
  on degraded scans; the quality dial is a good pattern (ReEngrave's DPI/imgsz
  tradeoff is the same "input quality changes the right threshold" problem).

### 6.3 BEAMS
- Audiveris right: **disk-closing sized to measured beam thickness** (ratio 0.8),
  robust to slope; splits stacked bars by section analysis.
- ReEngrave right in spirit: also scale-sized kernel + stacked-bar counting, and
  its **"≥2 stems must END at it"** filter is arguably a *stronger* beam/slur/tie
  discriminator than Audiveris's geometry-only spot filter.
- Adoptable: replace ReEngrave's **rectangular** horizontal opening with a
  **disk/elliptical** structuring element to stop under-filling sloped beams (the
  documented 43–46% fill problem) — keep the stem-end quorum as the validator.

### 6.4 LEDGERS
- Audiveris right: a real **grow-outward-one-interline-at-a-time** ledger finder
  with **convex-end** validation.
- ReEngrave: **none** (ledger pitch is extrapolated, ledgers not detected).
- Adoptable: cheap deterministic ledger detection would improve extreme-range
  pitch accuracy and give a second cue for high/low heads.

### 6.5 AUGMENTATION DOTS
- Audiveris right: **DotFactory two-pass** disambiguation + dot→note linking +
  double-dot chaining + "not on a staff line" guard.
- ReEngrave: detects `augmentationDot` but never disambiguates or links it.
- Adoptable: the two-pass pattern (instant cheap checks, then late context checks
  once heads/barlines exist) ports cleanly onto ReEngrave's post-pass architecture.

### 6.6 POST-CLASSIFICATION CHECKS
- Audiveris right: **`ShapeChecker`** centralizes per-shape geometric/context
  gating (clef at staff start, rest-pitch, tuplet pitch range, text height,
  pedal/marker side).
- ReEngrave: the same logic exists but **scattered** — the rest y-band gate,
  staff-vicinity text gate, flag min-height gate (`template_matcher.py`), and the
  five internal-consistency checks (`transcribe`). No single framework.
- Adoptable: refactor those gates into one **check registry keyed by category**
  that can *reject or rewrite* a detection — makes the rules testable and
  extensible, and is where the half/whole-rest-by-pitch and clef-at-start checks
  would live.

### 6.7 CONFIDENCE / GRADE
- Audiveris right: **per-shape minimum grades** (clef 0.03 … symbol 0.15) +
  **intrinsic (×0.8) vs contextual** grade.
- ReEngrave: a single flat `OMR_CONF_THRESHOLD=0.25` for all classes.
- Adoptable: a per-class floor table (structurally-critical, low-confusion shapes
  like clefs accepted lower; noisy shapes higher) and a contextual boost for
  detections that satisfy relations (a head with a stem) — cheap precision/recall
  wins without retraining.

### 6.8 THE ARCHITECTURE LESSON — validates ReEngrave's Phase 3.4 decision
Audiveris's split (template heads / learned classifier for compact fixed shapes /
classical CV for thin lines) is the *designed-in* version of what ReEngrave learned
the hard way: **Phase 3.4's 208→214 class expansion caused catastrophic forgetting
(F1 79.3%), and barlines/beams/stems are now "learned via classical CV not YOLO."**
Audiveris **never** puts thin lines or head-placement in its learned model, and its
learned model is a **tiny moment MLP retrained on a handful of samples**, not a
208-class detector. The `omr-dataset-tools` history — a DL4J CNN experimented with,
then the app defaulting back to the shallow moment net — is a second, independent
data point that a **big image CNN is not obviously the right tool for naming
compact music glyphs** once you can segment them. ReEngrave's memory already
records that DSv2-dense fine-tuning and domain augmentation are dead ends; Audiveris
suggests the productive direction is *better segmentation + a small
moment/template recognizer + a contextual grade*, not a bigger detector.

---

## 8. Ranked top adoptable ideas

1. **Distance-transform head templates (§1, §6.1).** Chamfer distance table with
   staff/ledger/stem pixels set to −1; per-head templates weighted
   foreground 6 / hole 4 / exterior 1; two passes (stem-seeded + pitch-snapped
   full scan); black↔void resolved by interior white ratio (0.2). ReEngrave has
   every input already. Fixes the YOLO over-count and the black/void split with
   **no model**. Highest value, lowest new-dependency cost.
2. **Per-shape grade floors + intrinsic/contextual split (§5.7, §6.7).** Replace
   the single 0.25 threshold with a per-category floor table and a small
   contextual boost for detections that satisfy relations. Trivial to implement,
   immediate precision/recall control.
3. **A centralized `ShapeChecker`-style post-classification layer (§5.6, §6.6).**
   Fold ReEngrave's scattered gates + the internal-consistency checks into one
   category-keyed registry that can reject *or rewrite* a detection (half/whole
   rest by pitch, clef-at-staff-start, text-height, tuplet pitch range).
4. **DotFactory-style two-pass dot disambiguation (§6, §6.5).** Instant cheap
   checks then late context linking; adds augmentation/staccato/repeat separation
   and dot→note relations ReEngrave lacks.
5. **Moment-feature recognizer as a cheap second opinion for compact shapes
   (§5.1–5.2).** A ~46-dim ART+geometric+aspect vector into a tiny MLP (or even
   nearest-neighbour, which is what ReEngrave's Hu-moment screen already half-is)
   is retrainable on a handful of samples and immune to the density/scale prior —
   a good disagreement detector against YOLO on rests/accidentals/clefs.
6. **Disk (not rectangle) structuring element for beam spots, sized to beam scale
   (§3, §6.3).** One-line change that stops sloped-beam under-fill; keep the
   stem-end quorum as validator.
7. **Deterministic grow-outward ledger detector with convex-end test (§4, §6.4).**
   Fills a total gap; improves extreme-range pitch.

---

## 9. Gaps / caveats in this research

- **[NOT FOUND]** exact `ARTMoments` ANGULAR/RADIAL/MOMENT_COUNT (file path 404'd);
  the ~35 ART / ~46-total feature count is [INFERENCE] from the MPEG-7 ART standard
  (12×3 grid) and the read `MixGlyphDescriptor.LENGTH` formula. The *shape* of the
  finding (moments, not pixels; tiny vector) is [SRC]-solid.
- The SYMBOLS handbook page is **[NOT FOUND]** ("documentation not yet provided");
  §5.3 comes from `GlyphCluster.java` source, not docs.
- Line numbers are from a summarizing fetch and are **approximate locators**; every
  claim is anchored to a named method/constant a human can grep.
- REDUCTION / the full symbol-interpretation graph (how intrinsic grades become
  contextual, exclusions resolved) is **out of this slice's scope** (interpretation
  graph = another Part) — touched only where it defines the classifier's *output*.
- License: all above is algorithm/parameter/architecture stated conceptually for
  clean-room reimplementation. No Audiveris code is quoted. If any ReEngrave port
  is undertaken, implement from these descriptions, not from reading the AGPL
  source into the ReEngrave (non-AGPL) tree.
