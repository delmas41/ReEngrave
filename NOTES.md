# ReEngrave — backlog / research notes

Forward-looking ideas. Not yet scoped, not yet scheduled. Surface these to Sean at the start of a ReEngrave session.

---

## YOLO training via symphony MusicXML × multiple IMSLP editions (2026-05-23)

**Idea**: avoid hand-labeling ~500 cells for measure-line detection by using existing symphony MusicXML as ground truth, then pulling every available PDF edition of those same symphonies from IMSLP and training YOLO to detect structural elements (measure lines, stems, rhythms) by comparing detections against the XML.

**Why it works for structural elements**:
- MusicXML *is* authoritative for measure boundaries, stem direction, rhythm.
- Sean already has the MusicXML for the symphonies in question — no labeling cost.
- IMSLP has multiple engraved editions of the canonical symphonies (Beethoven, Brahms, etc.) — instant data multiplier per work.

**Limits to remember**:
- MusicXML will likely be missing dynamics, expression marks, articulations, technique markings, and other notation the original score has. This pipeline is **only** useful for the structural classes the XML can verify. Dynamics / expression / technique training still needs another approach.

**Publisher/era as a transfer-learning axis**:
- Track edition, publisher, and publication date metadata per training PDF.
- Hypothesis: a model trained on, e.g., all Beethoven symphonies engraved by Breitkopf & Härtel in 1862–1890 will generalize to *other* composers' symphonies engraved by the same publisher in the same window — engraving conventions track the publisher/era, not the composer.
- This implies the training pipeline should be sliceable by publisher × era, not just by composer.

**Action item (research, no code yet)**:
- Investigate the major score publishers across symphonic repertoire and their active windows. Goal is a categorization scheme: publisher → era → engraving style. Likely candidates to map: Breitkopf & Härtel, Peters, Schirmer, Eulenburg, Universal Edition, Bärenreiter, Henle. For each: when active, what they engraved, distinguishing visual conventions.

**Status**: parked. No action this session — Sean wants this brought up next time he's actively working on ReEngrave.

---

## Plans surfaced 2026-05-24 from past sessions

Sean asked to recover suggestions he'd made across past YOLO-era sessions that hadn't carried into the current plan. The seven below are the ones that were absent or under-documented. Quotes are verbatim from his sessions.

### 1. Maestro Analyzer as a theory-constraint layer over OMR (highest leverage)

**Status (2026-05-24): SCOPED — see [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md).** Decisions locked: Bun CLI + thin Python wrapper, git submodule of gradus-vercel, scholarly seed = WTC I.1 + Beethoven 5/i + Brahms 4/iv + Chopin Ballade 1 + Debussy La Mer/i, MCP server deferred, music21 stays in parallel. Personal-use constraint applies. Next action: M0 (~1 day).


**Idea**: wire the existing `gradus-vercel/lib/maestroAnalyst/` TypeScript engine into ReEngrave as a *constraining* layer over YOLO output, not just as a post-hoc validator. Narrow ambiguous pitches by key + modulation + chromatic context; validate range; suggest enharmonic spellings. The MaestroAnalyst already covers cadence, enharmonicSpelling, keyDetection, modalAnalysis, pcSet, phraseSegmentation, pitch, pitchTendencyTags, rangeValidation, reduction, romanNumeral, scale, voiceLeading, xmlParser.

**Quotes**:
- "use a tool like maestro ananlyzer and determine what the potential notes couldbe based on key and even what chromatic notes would be more likely based on where the music is going by understanding modulations and the theory that is used to get there" (cool-kare)
- "I want to improve the maestroanalyzer to replace the music21 mcp by adding these functions: range validation, enharmonic spelling, xml parsing, basic pitch utilities" (jolly-noether)
- "Dose it make sense to add any access to the maestro analyzer or to the gradus vercel GKB for knowledge access to help" (hopeful-mayer)

**Current state**: not integrated. `grep maestro` in `backend/` and `tools/omr/` returns nothing. The only theory pass is reactive (`backend/modules/score_comparison.run_theory_checks`) and runs against the *final* MusicXML, not during OMR.

**What's needed to move**: decide on the integration shape — Python ↔ Node bridge vs. port the relevant analyst modules to Python vs. expose maestroAnalyst as an HTTP service. Then add a re-ranking step after `pitch_resolver` that takes the top-N candidates per notehead and asks maestroAnalyst to pick.

---

### 2. GKB (Gradus Knowledge Base) access for OMR context

**Idea**: let OMR query the GKB at gradus-vercel for context (composer/period/expected harmonic vocabulary) when transcribing.

**Quote**: "also use GKB at gradus vercel in any way that it is helpful" (jolly-noether)

**Current state**: Gradus *library* (reference MusicXMLs) is wired into ReEngrave for comparison; the GKB knowledge layer is not.

**What's needed**: bounded by item 1 — once the maestroAnalyst bridge exists, GKB access is the natural follow-on.

---

### 3. Expand training data: DoReMi + MUSCIMA++

**Idea**: don't stop at DeepScoresV2 — also train on Steinberg's DoReMi and MUSCIMA++ to broaden the model's exposure.

**Quotes**:
- "what about using a DOREMI baseline like steinberg's? https://github.com/steinbergmedia/DoReMi/releases/tag/v1.0" (objective-kare)
- "what other training can we do? more symbols from deepscore? DOREMI? MUSICIMA+++?" (objective-kare)

**Current state**: only DSv2 is in `tools/omr/training/`. DoReMi + MUSCIMA++ are not referenced anywhere.

**What's needed**: download + class-map both datasets, fold them into `prepare_yolo_data.py` and `build_catalog_yaml.py`. Re-train.

---

### 4. RTMDet / yolov8x@200ep escalation path

**Idea**: production weights are yolov8l@30ep — Sean approved the "all-the-way" run when ready.

**Quotes**:
- "I want to do this all the way full data set, yolov8x +200 epochs + the works. I can add more funds now or later but the rough estimates are ok with me" (cool-kare)
- "When we get to phase 3 should we use rtmdet instead of yolov8?" (cool-kare)
- "does our plan include using an anchor based object detector or checkpoints from github?" (objective-kare)

**Current state**: documented checkpoints stop at yolov8l-imgsz2048-ft-30ep. No RTMDet / yolov8x experiments are scheduled.

**What's needed**: define the comparison protocol (same verdict set, same imgsz) and budget a cloud run.

---

### 5. Multi-type barline classification

**Idea**: barlines aren't a single class — Sean explicitly wants single bar, double bar, final bar, and repeats distinguished. Currently classical CV detects "a barline" but not which kind.

**Quote**: "would it be bad to have a single bar line, double bar line, final bar line and repeats?" (objective-kare)

**Current state**: Phase 3.4 attempted barlines as a custom YOLO class and caused catastrophic forgetting. Currently: classical-CV barline detection, no type distinction. (See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.)

**What's needed**: either (a) post-process the classical-CV barline by inspecting pixel patterns to the left/right (double = two thin lines; final = thin + thick; repeat = thick + dots), or (b) re-introduce as YOLO classes once 200+ examples per type are labeled.

---

### 6. MusicXML repeat signs

**Idea**: MusicXML doesn't natively encode repeat marks the way humans see them — currently the export drops them.

**Quote**: "Mxl does not account for repeat signs - flag for follow up" (interesting-curran)

**Current state**: no handling in `tools/omr/export.to_musicxml()` or in the catalog labeler.

**What's needed**: detect repeats during OMR (tied to item 5) and emit `<barline location="left"><repeat direction="forward"/></barline>` etc. on export.

---

### 7. Confirm "just ink" as a label class

**Idea**: label noise/ink-artefacts explicitly during hand-labeling so the model learns to ignore them, instead of leaving them unclassified.

**Quote**: "It might be helpful also just to classify ink" (objective-kare)

**Current state**: unclear whether the annotate UI exposes "just ink" as a category. Check `tools/omr/annotate/static/archetypes/` and the cell.js picker categories.

**What's needed**: 5-minute verification. If absent, add a category labeled "noise/ink" and update `verdicts_to_yolo_labels.py` to either drop or remap those during YOLO label emission.
