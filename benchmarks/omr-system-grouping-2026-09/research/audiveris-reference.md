# Audiveris reference — how the mature engine categorizes & recognizes, mapped to ReEngrave

2026-09-01. Master index + ranked adoption backlog synthesizing three deep-dives:
- [audiveris-partA-layout.md](audiveris-partA-layout.md) — LOAD/BINARY/SCALE/GRID/HEADERS/MEASURES/TEXTS
- [audiveris-partB-symbols.md](audiveris-partB-symbols.md) — heads, stems/beams/ledgers, the glyph classifier
- [audiveris-partC-assembly.md](audiveris-partC-assembly.md) — the Symbol Interpretation Graph (SIG), reduction, chords/rhythm/parts
- [audiveris-grid.md](audiveris-grid.md) — the GRID/system-grouping deep-dive (system break rule)

## How to use this, and the license boundary

Audiveris is **AGPL-3.0**. This reference documents its *algorithms, parameters,
and architecture* (facts/ideas, not copyrightable) so ReEngrave can reimplement
independently. **Study the approach; do not copy or closely paraphrase the source
into `tools/omr/`.** Each detail file flags the parts that must be clean-room.
File:line pointers are for a human to look at the original, not to port.

## The one idea that recurs — and where ReEngrave diverges

Audiveris's through-line, at every stage: **measure a global SCALE first, hold
every competing reading of the same ink alive as a graded hypothesis, resolve
them together, and reason per-system.** ReEngrave instead **commits eagerly at
each stage and patches with abstaining post-hoc checks** — so its checks can
*flag* a disagreement but never *re-select* the better reading (the losing
hypothesis is already gone). Three places this bites hardest, and all three feed
the system-break fix:

1. **No SCALE step** → spacing↔detection circularity, the zero-staff/tiny-mediabox
   and DPI-dependence bugs.
2. **No brace/bracket detection** → part/system boundaries inferred from an
   edition-fragile barline-density proxy — the root of the grouping failures.
3. **No interpretation graph** → competing clef/key/pitch readings can't be
   reconciled by confidence, only voted or abstained.

Where they *independently converged* (worth noting — ReEngrave got these right):
clef-by-glyph-center **geometry** (not classification), **classical CV** for
stems/beams/ledgers (Audiveris never asks one learned model to box thin lines —
this validates ReEngrave's Phase-3.4 lesson), and adaptive/Sauvola binarization.

## Stage-by-stage map

| Pipeline stage | Audiveris technique | ReEngrave now | Gap / opportunity |
|---|---|---|---|
| Binarize | adaptive / Sauvola | `preprocessing.py` | converged |
| **Scale** | run-length histograms → interline + line + beam units, **before** staves exist; thresholds sized as fractions of it | median spacing computed *inside* staff detection | **CIRCULARITY**; DPI/mediabox bugs. **Adopt.** |
| Staff lines | horizontal filaments → clusters | `staff_detector` | roughly converged (see grid doc) |
| **Systems** | connection graph + privileged left "starting column"; **no gap-distance stage** | connectivity used as a veto over gap guesses | the break rule (this project) |
| **Parts / groups** | left-margin **brace/bracket** detected & measured | barline-density proxy | edition-fragile. **Adopt bracket detector.** |
| Clef | glyph-center geometry (pitch −2 tenor / 0 alto / 2 mezzo / 4 soprano) | `clef_geometry.py` | **CONVERGED** |
| **Key sig** | header projection (1-stem=flat / 2-stem=sharp) + force-re-recognize empty slots | `key_signature_geometry` (~50% recall) | header-projection reader. **Adopt.** |
| Time sig | numerator/denominator half-ROI + "same per system or none" | unreliable / often null | moderate |
| Measures | system-spanning **MeasureStack** | per-system in `measure_extractor` | partial |
| Text | whole-sheet **OCR** + role-by-position (title/direction/lyric/label) | margin instrument labels only | Tesseract already in stack |
| **Note heads** | **distance-transform template match** (Chamfer table; per-head weights fg 6 / hole 4 / ext 1 → separates black/void/whole; stem-seeded + pitch-snapped passes) | YOLO noteheads | over-count + black/void split. **Adopt templates.** |
| Stems / beams / ledgers | classical CV (filaments + scale-sized morphology) | `line_detection.py` CV | **CONVERGED** |
| Fixed symbols | shallow MLP over ~46-dim **moment** vector (not pixels) + `ShapeChecker` geometric gates + **per-shape grade floors** | YOLO 208-class + flat `conf 0.25` | grade floors + checker layer |
| **Assembly** | **SIG**: graded `Inter` vertices + **support** & **exclusion** edges + greedy fixpoint **reduction** selects a consistent maximal set | eager commit + abstaining `_flag_*` checks | can flag, not re-select. Adopt the *formula*, not the graph. |
| Chords / rhythm | voice assembly; measure marked `abnormal` **after** assembly; **abandoned** global rhythm search | `voicing` + narrow `_reconcile_measure_to_meter` | **converged-narrow** (Audiveris abandoning global search vindicates ReEngrave's ±1 reconciler) |
| Parts across systems | staff-geometry primary, OCR names secondary | margin-label primary | **inverse** — worth revisiting |

## Ranked adoption backlog (the working list)

Ranked by value × (low risk/effort). Each links to its detail file.

**Tier 1 — highest value, self-contained, low AGPL risk:**
1. **Standalone SCALE step** (A) — run-length histograms → interline/line/beam
   units before staff detection. Breaks the spacing↔detection circularity, fixes
   the DPI/tiny-mediabox failures, gives beams a real unit. Foundational; a
   classic technique with no method-level AGPL risk.
2. **Left-margin brace/bracket detector** (A + grid) — classical CV, runs before
   YOLO, no new training class. **Directly the missing cue for the system-break
   fix**: the bracket is ~3× the ink of the systemic barline, so it survives
   scans that kill the barline.
3. **Distance-transform note-head templates** (B) — Chamfer distance + weighted
   templates, seeded on detected stems and snapped to pitch ordinates. Fixes
   YOLO's notehead over-count and the black/void/whole split **with no model**,
   reusing pieces ReEngrave already has (staff lines, `pitch_resolver`, the
   Bravura `symbol_library/`, a staff-removed image).

**Tier 2 — strong, moderate effort:**
4. **Contextual-grade reconciler** (C) — the `(1+c)·g/(1+c·g)` support formula
   (~5 lines of math) applied where ReEngrave already arbitrates competing
   signals (clef: detector/geometry/locator/dossier; key; pitch). Turns
   "majority ≠ correct, so abstain" into a confidence-weighted winner. Reuses
   `key_signature_vote.py` / `clef_correction.py`.
5. **Overlap → exclusion → keep-stronger** (C) — a ~30-line post-detection pass:
   when two class-incompatible YOLO detections overlap (IoU ≥ ~0.05), keep the
   higher-confidence one. Principled attack on orchestral rest/notehead over-
   detection, replacing per-class NMS + flat conf cutoffs.
6. **Header-projection key reader** (A) — detect accidentals from the header
   projection itself instead of depending on YOLO seeing key markers. Attacks the
   documented ~50% key recall; reuses existing slot tables + cross-staff vote.
7. **Per-shape grade floors + `ShapeChecker` layer** (B) — replace the single
   flat `OMR_CONF_THRESHOLD` with a per-category floor table + a centralized
   post-classification registry that can reject/rewrite a detection.

**Tier 3 — worthwhile later:**
8. **Keep small graded candidate sets alive one stage longer** (C) so meter/theory
   checks can *select* rather than only flag (`pitch_resolver` already emits
   weighted top-N) — reduction-in-miniature.
9. **Whole-sheet OCR + text-role taxonomy** (A) — capture titles/directions/lyrics,
   not just margin labels.
10. **System-spanning MeasureStack abstraction** (A).

**Studied and rejected — too big or not magic:**
- **Full SIG port** (C) — an architecture-level rewrite. And it isn't magic:
  Audiveris's solver is *greedy*, and it *abandoned* its global rhythm search as
  impractical — which is exactly why ReEngrave's narrow beam-level reconciler is
  the right scope. Adopt the grade *formula* (item 4), not the graph.

## How this reference feeds the system-break fix

The grouping fix is not separate from this study — it *is* three items above,
composed:
- **#1 Scale** gives robust units, so the ~2px-systemic-barline problem is
  *measured*, not guessed at a fixed DPI.
- **#2 Bracket detector** supplies the constructive cue the current veto lacks —
  the one that survives when the barline doesn't (and the one thing that still
  works at a vocal gap, where barlines are conventionally absent).
- **#4 Contextual grade** is how we *combine* barline + bracket + header-column
  evidence into one confidence-weighted "system starts here" decision, instead of
  a single fragile ink veto — Audiveris's constructive, per-system philosophy
  applied to exactly ReEngrave's failure.

So the Audiveris way isn't just a reference for later; its top three items are
the design basis for the fix this project is building.
