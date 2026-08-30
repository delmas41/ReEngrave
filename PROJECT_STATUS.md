# ReEngrave — Project Status

**Last updated:** 2026-08-29 (clef accuracy measured end to end; the July label batches landed)

This document is a snapshot. For day-to-day reference docs see
[CLAUDE.md](CLAUDE.md). For parked research ideas see [NOTES.md](NOTES.md).

---

## Scope

**Personal-use only** (re-affirmed 2026-05-24). Sean is the sole user. The Stripe payment gate and multi-user infra are already built but no longer the optimization target — design decisions should minimize complexity and ongoing cost, not maximize generality. The only acceptable interaction surface for new tooling is Claude Code itself (Claude sessions running locally, calling Bash / Python / YOLO). No new long-running services / MCP servers / HTTP proxy routes / UI surfaces unless Sean explicitly promotes them.

## TL;DR

ReEngrave has **two converged tracks** living together on `main`, plus an optional theory layer:

1. **A web app for music-score quality control** — upload a PDF, run OMR, review diffs, export. Auth + payments wired in. Built March 2026, iterated through April–May.
2. **An in-house YOLO + classical-CV OMR pipeline** — `tools/omr/`, fine-tuned on DeepScoresV2 (F1 98.8% on the Bach WTC verdict set). Built May 2026 across 49 commits / Phase 1 → Phase 4m.
3. **Maestro theory layer** (shipped 2026-05-24) — `tools/maestro_bridge/` (TypeScript, runs host-side via node/tsx) + `backend/modules/theory_layer.py`. Env-gated: harmony/rhythm validation, scholarly cross-check against 5 seed works, and in-pipeline pitch re-ranking with auto-correction (M4, local-YOLO pipeline only). See [docs/maestro-integration-plan.md](docs/maestro-integration-plan.md).

**Current activity (August 2026): reading the staff HEADER — clef and key signature — by geometry rather than classification.** Twenty-five merges since the last audit, in three arcs:

- **July — deterministic verification layers.** Five internal-consistency checks (time-sig, rhythm sums, measure counts, transposition-aware key agreement, advisory clef-from-register) that ABSTAIN where detection is blind rather than guess. Two training experiments were run properly and **disproven**: ScoreAug/Augraphy domain augmentation made real-cell recall worse, not better, and fine-tuning the detector on clef cells collapses dense-page noteheads. Both are dead recipes; don't retry them.
- **August — a trusted Phase-1 baseline.** Layout had no regression baseline at all, which had blocked several fixes. Now: a hand-verified ground-truth fixture, a corpus probe, and xfails for known gaps. That unblocked real bugs — phantom staves, music deleted after a false barline, staff-line removal being a no-op on thick-line prints, body text detected as staves.
- **August — the header layer.** Clef *reading* is now measured rather than classified (alto/tenor/soprano are the same glyph on different lines, so no classifier can separate them), and key signatures are read by fitting accidental POSITIONS to the slot table for (clef, N) and reconciling across the page.
- **August — contextual analysis, and the over-detection bug it turned up.** The pipeline now knows *which staff is which instrument*: systems from vertical connectivity (43% → 86%), instrument identity from the PDF text layer and, for scans, from a margin reader, and stable part slots across systems and pages. Re-running the whole-pipeline validation for the first time since May then exposed the single largest accuracy bug in the project — `imgsz` was set so high the detector was reporting 2–4× the notes that exist. Fixing it took end-to-end pitch precision from **0.144 to 1.000** on the keyboard fixture.
- **August 29 — external truth, and an orchestral benchmark to prove it on.** The pipeline can now be given a **dossier**: the meter, measure count and per-part written clef and key signature of the work it is reading, generated from MusicXML rather than hand-authored (`tools/omr/dossier.py`, 97 orchestral movements in `data/dossiers/`). It both CHECKS a reading and SEEDS it — clef detection has resisted a fine-tune, ensemble voting and a CV locator, and none of that matters if the clef is simply known. Alongside it, `benchmarks/omr-orchestral-e2e/` renders a Gradus MusicXML excerpt back to PDF, so every note on a conductor's page is known by construction — the first note-level accuracy measurement on orchestral texture. On it, Beethoven 5 now reads **recall 1.000, precision 0.988, duration 1.000**, and Mahler 5 reports 24 notes against a truth of 24. Four defects were found and fixed by that benchmark alone: overlapping measure cells letting two staves each keep the same notehead, a beam counter with no upper bound (it reported eight-beam notes — a 1024th), a beam cluster tolerance sitting inside the duplicate mode, and a meter parser that wrote `<beats>686</beats>` into MusicXML.

---

## What works today

### End-to-end OMR (CLI)

```bash
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly  # → out.pdf
```

All 5 benchmark PDFs (Bach WTC, Mozart, Beethoven, Chopin, Debussy) produce LilyPond that compiles to PDF with **zero errors** — only bar-check warnings on measures whose summed durations don't match the time signature exactly. F1 98.8% on the 25-cell Bach WTC verdict set. See [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md) for the full Phase 4 story.

### Theory layer (optional, env-gated)

With `MAESTRO_BRIDGE_ENABLED=true`, OMR output is enriched with key detection, rhythm/beat-mapping validation, and a scholarly cross-check against curated reference analyses (5 seed works). With `MAESTRO_PITCH_RERANK_ENABLED=true`, ambiguous noteheads are re-ranked against the detected key during local-YOLO OMR and auto-corrected above a confidence threshold. Runs host-side (node/tsx + the `gradus` submodule) — **not available inside the Docker container by design** (personal-use scope; the container has no Node).

### Web app pipeline

```
Upload PDF → ReEngrave (pick: local YOLO or Claude Vision) → Review
  ├── Vision diff (paid)            — Claude Vision flags per-measure differences
  └── Theory check (free)           — music21 rhythm/range/enharmonic sanity
→ Export (musicxml | lilypond | pdf)

Parallel: Gradus Library
  ├── Upload master reference XMLs
  └── Multi-source comparison (2-6 XMLs, music21 measure agreement matrix)
```

Auth: JWT + httpOnly refresh cookie, 8-hr access tokens.
Payments: Stripe webhook, $5/score for Vision diff, admin-email bypass.

### Local YOLO pipeline modules (`tools/omr/`)

| Module | Function |
|---|---|
| `transcribe.py` | Entry point — PDF → structured JSON |
| `export.py` | JSON → LilyPond / MusicXML (incl. voice splitting via `<backup>`) |
| `yolo_detector.py` | ultralytics YOLOv8l wrapper |
| `line_detection.py` | Classical-CV stems + beams (Phase 4f) |
| `rhythm.py` | Note durations from notehead class + beam count + flag pairing + dots |
| `voicing.py` | Same-x notehead chord grouping + stem-direction voice splitting |
| `pitch_resolver.py` | Notehead y-position → diatonic pitch, with key sig + inline accidentals |
| `staff_detector.py` | 5-line staff detection via horizontal projection clustering |
| `measure_extractor.py` | Barline detection + canonical-cell extraction |
| `preprocessing.py` | PDF → PageImage (render, binarize, deskew) |
| `staff_line_removal.py` | Optional staff-removed cell variant |
| `annotate/` | FastAPI labeling UI — triage mode + draw-from-scratch mode (2026-06-09) |
| `training/` | DSv2 prep + ultralytics training scripts |
| `tests/` | 680 unit tests |

### Reading the staff header (`tools/omr/staff_header.py` + friends)

On by default in `transcribe`; `--no-header-reading` turns it off. No extra weights needed.

- **The header window is measured from the page**, not taken from the staff-start measure cell — on degraded prints that cell routinely begins *past* the clef. Measured over 26 pages of 20 scores, 233/455 staves have a clef inside their measured window (`benchmarks/omr-key-signature/probe_header_windows.py`).
- **Clefs are read by geometry** (`clef_geometry.py`) — which staff line the glyph is centred on. Exact rather than probabilistic, and it is the only thing that can separate alto from tenor from soprano. A classical-CV locator (`clef_locator.py`) finds C clefs the detector cannot see at any confidence.
- **Key signatures are read by position** (`key_signature_geometry.py`) and reconciled across staves and systems (`key_signature_vote.py`). Both the detector's markers and the locator's clusters go through the same vote.

**End-to-end clef accuracy is 96%, and the detector does most of the work.**
Measured on 52 hand-read staves across three pages
(`benchmarks/omr-clef-geometry/eval_pipeline_clefs.py`, re-run on the merged tree
2026-08-29):

| pipeline | correct | notes |
|---|---:|---|
| readers only | 48/52 (92%) | detector 37/39, positional default 9/11, CV locator 2/2 |
| `--contextual` | 49/52 (94%) | a part keeps its clef between systems (`slot_continuity`) |
| `--contextual --dossier` | **50/52 (96%)** | the work's parts joined to the page on the margin LABELS, never on the clefs |

This is the number that matters downstream — a staff carries its clef into every
pitch on it and into which slot table its key signature is fitted. It is far
better than the CV-locator coverage figures quoted elsewhere in this repo, which
are about that one reader and predate the `imgsz` fix. **Every remaining error is
a non-treble clef read as treble**, and the last two are the same Pastoral viola,
on a page carrying no label below the strings to anchor the dossier join.

Measured, given a correct clef, on 42 hand-read orchestral staves: **18 correct / 0 wrong / 16 missed / 8 correct abstentions**. End to end on a clean engraving (Bach WTC p.17) 10/10. End to end on degraded orchestral prints it is far lower — 2 staves of 20 on Beethoven 6 p.2, none on Beethoven 5 p.2 — because a staff whose clef is only the positional default is skipped by design. **Key signatures inherit the clef problem, and clef coverage is the ceiling on both.**

### Contextual analysis — which staff is which instrument (`tools/omr/`)

A human reading a large score deduces most of it from context: which staves transpose,
what instrument order to expect, what the natural groupings are. The pipeline now does
some of that.

- **`system_grouping.py`** — systems from **vertical connectivity**, not gap size. A
  system break is a gap no vertical ink crosses, because barlines and the bracket run
  through a system and nothing runs between two of them. System-count accuracy **43% →
  86%** over 14 bracket-verified pages, and spurious single-staff "systems" 19 → 0. The
  same pass recovers the instrument-family grouping as `Staff.group_index` (verified on
  Beethoven 9: 4 woodwinds | 2 horns | 5 strings).
- **`instruments.py` + `staff_labels.py`** — instrument identity from the PDF's text
  layer, free. 18/65 IMSLP score PDFs have one; **79% of labelled staves resolve**. The
  lexicon maps a printed label to instrument, family, default clef, written range and
  transposition (`fifths_offset = -fifths(key_name)`). Scored against the `<part-list>`
  of 111 orchestral works in the Gradus MusicXML library — what engravers actually
  wrote, with no OCR in between — it reads **99% of 2,345 real part names**, and 95 of
  105 symphonic works come out in score order
  (`benchmarks/omr-score-order-2026-08/`). Monotone order turns out to be a sharper
  test of a lexicon than coverage, because a misread label usually still READS: `Basso`
  resolved cleanly and resolved *wrong*, and only the order showed it. The 10 that
  remain are real layout variation — voices printed below the strings, Tchaikovsky's
  banda — and are deliberately not encoded.
- **`staff_labels_vision.py`** — the same for scans, reading the margin with Claude.
  Opt-in (`vision_fallback=True`), because it costs money — about a cent per system, and
  bounded per *work* rather than per page since slots propagate one reading. Validated
  against the text layer as free ground truth: **25 agree, 0 disagree, 30 recovered,
  0 missed** on 76 staves.
- **`slots.py`** — stable part identity across systems and pages, by **monotone sequence
  alignment**. Index matching fails because a system omits the staves of instruments
  tacet through it. **100% label purity**, 198/217 staves assigned.
- **`clef_correction.py`** — proposes a clef from the instrument's written range where
  no reader read one. Gated on `staff["clef_source"]` being absent, never on a scan for
  clef detections: the geometry readers emit no detection, so a scan would overwrite a
  confidently-read clef.

Benchmarks: `benchmarks/omr-system-grouping-2026-08/`, `benchmarks/omr-margin-labels-2026-08/`.

### Dossiers and the orchestral benchmark (2026-08-29)

```bash
python3 -m tools.omr.training.build_dossiers            # 97 works -> data/dossiers/
python3 -m tools.omr.transcribe score.pdf --dossier beethoven-sym5-mvt1
python3 -m tools.omr.training.orchestral_eval           # note accuracy on a conductor's page
```

| work | parts | measures | notes (omr/truth) | recall | precision | duration |
|---|---|---|---:|---:|---:|---:|
| beethoven-sym5-mvt1 | 18/18 | 8/8 | 82/81 | **1.000** | **0.988** | **1.000** |
| brahms-sym1-mvt1 | 21/21 | 7/7 | 508/505 | 0.717 | 0.713 | 0.865 |
| mahler-sym5-mvt1 | 38/38 | 8/8 | **24/24** | 0.917 | 0.917 | 0.318 |

Facts are stored as **written** pitch, so a transposing staff needs no
correction. Slot-level checks abstain unless the parts join the page's staves;
forcing that join measured F1 0.064 and must not be retried. The MusicXML feeds
verification and benchmarking, **not** label generation.

Two cautions carried out of that work. The benchmark's paper size must scale
with the part count — rendering 38 parts on A4 leaves ~1 staff-space between
staves and manufactures a failure mode that does not exist
(`STAFF_LADDER_PHASING.md` records the wrong diagnosis it produced). And
`rhythm.py`'s tuning comments assume a canonical line spacing of 24–48 px; it is
**100**, so re-derive rather than scale when touching those constants.

### Hand-labeled training data (`data/user-labeled/`)

| Version | Cells | Content |
|---|---|---|
| `v1-2026-05-18-orchestral` | 60 | Beet 5 + Mahler 5 orchestral cells; cleaned 2026-06 to remove structural-element boxes (staff/stem/beam → background) |
| `v2-2026-06-08-beet5` | 37 | Beethoven 5 pp. 45–75; heavy FP-drop batch (480 FPs dropped, 37 FNs added) |
| `v3-2026-06-09-mahler5` | 35 | Mahler 5, draw-from-scratch |
| `v4-2026-06-10-la-mer` | 29 | Debussy *La Mer*, draw-from-scratch |
| `v5-2026-07-12-clef` | 15 | Phase-0 clef batch — Mahler, 15 clefs incl. 3 alto + 2 tenor |
| `v6-2026-07-13-clef-diverse` | 47 | Cross-score clef diversity — 10 alto, 10 tenor, 14 bass, 13 treble |

v5 and v6 sat on `clef-phase0-eval` as the only copy until 2026-08-29. **v6's
label images were symlinks into a gitignored `cells/` directory** — one `git
clean` from being labels with no images; they are real PNGs now.

`catalog.yaml` still unions v1–v4 only, deliberately. Adding 62 clef-heavy cells
narrows the density prior, and that is precisely what collapsed dense-page
noteheads 2506 → 114 in the clef fine-tune. Preserving labels and training on
them are separate decisions.

---

## The catalog-training experiment (2026-05-23 → 05-25) — concluded, not merged

The headline NOTES.md idea — *train YOLO from symphony MusicXML × IMSLP editions instead of hand-labeling* — **was executed** across Phases A–L on branch `claude/interesting-curran-3ca1b7` (43 commits, never merged to main). Outcome:

- **The catalog itself worked.** 65/65 IMSLP editions aligned to MusicXML (Phase D); per-cell YOLO label generation shipped (Phase E); 154k labels emitted across 26 movements (Phase G).
- **Training on it failed, repeatedly.** Phase H (catalog-augmented fine-tune): collapsed. Phase I (fixed a ~50px x-offset in catalog labels): still collapsed. Phase J (mix-mode, briefly promoted): Phase K diagnosed a class-ID collision with DSv2 and the collapse stood. Phase L (slot remap to DSv2-free slots): **still collapsed** on Beethoven 5.
- **Verdict:** catalog-augmented YOLO training is a dead end with the current recipe. Structural elements (stems/beams/barlines) stay with classical CV; symbol-class improvement comes from **hand-labeling via the annotate UI** (the current June work).

**Loose end:** `omr-weights/deepscoresv2-yolov8l-phase-j-mix-30ep.pt` (84 MB, from the collapsed Phase J run) still sits next to the production weights. **Do not use it.** Production remains `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`.

The branch also carries **post-experiment OMR improvements that may still be valuable** (see "Unmerged work" below).

---

## Unmerged work on branches

Audit **2026-08-29**, verified with `git cherry` and by comparing file contents —
not by commit count, which lies here. Several branches listed as unmerged in the
2026-08-28 audit had in fact landed; their commits differ only because they were
squashed or re-merged. Anything not listed is an archive of a concluded experiment.

| Branch | State | Disposition |
|---|---|---|
| `claude/reengraved-score-evaluation-cd4c92` | **Landed** | The paper-size fix and the beam-dedup corrections are on `main`. |
| `claude/omr-score-order-prior` | **Landed** | Every file identical to `main`; the lexicon work arrived as `9711138`. Branch is stale metadata. |
| `claude/omr-info-retention-erasure-c26534` | **Landed** | Nothing unlanded. |
| `claude/recognition-improvement-next-2f1709` | **Landed** | Nothing unlanded. |
| `clef-phase0-eval` | **Labels landed 2026-08-29** | v5, v6, three labeling batches (79 verdicts) and the audit tooling are on `main`. Its code half was redundant, its docs conflict with two months of newer files, and its weights stay unused. The branch is now an archive. |
| `claude/omr-clef-tenor-fixture` | **Deliberately held back** | The F-clef dot veto fires on C clefs; the fix takes the engraved reference sheet 4/5 → 5/5 and orchestral clef precision 1/2 → 3/4. But the clefs it gains open the key-signature gate on staves the key-sig reader misreads, taking Beethoven 6 p.2 from 2 correct/0 wrong to 0/2 — for no clef gain in the output, since the header clef only picks a slot table. The commit message says so itself. Ship once the viola misread is fixed; reasons in `benchmarks/omr-clef-geometry/NEXT_SESSION_HEADER_CLUSTER.md`. |
| `claude/omr-dossier-verification-layer-eaf6d0` | **The one open decision** | 4 commits, July. A *parallel* dossier implementation: hand-typed `tools/omr/dossiers/*.json` where `main` generates `data/dossiers/` from the Gradus MusicXML. Slice 1 (meter back-fill + column notation-math) is superseded, but **Phase 2/3 and dossier-steered re-segmentation — acting on a known bar count — have no equivalent on `main`**, whose `resegment_fused_measures` is driven by cross-staff consistency instead. Worth an assessment, not a merge: it has drifted seven weeks and uses a different data model. |
| `claude/interesting-curran-3ca1b7` | Archive + one live thread | Catalog experiment Phases A–L (concluded; do not retrain from it) **plus** 2026-05-25 `line_detection` improvements still worth a cherry-pick review. Its label-EMITTER half is validated prior art for MXL-guided auto-labeling. |
| `claude/scoreaug-fair-test-a2928e`, `claude/training-domain-augmentation-a29baf` | Archives | The two **disproven** training experiments. Do not deploy their weights; do not retry the recipes. |
| `claude/magical-bhabha` | 1 commit (March) | **Real MusicXML measure-level patching in `export_module`** — the #1 web-app TODO. Pre-consolidation code; evaluate against current `export_module`. |
| `claude/peaceful-kapitsa` | 1 commit (March) | SQLite-backed persistent job queue replacing FastAPI `BackgroundTasks`. Same: pre-consolidation; evaluate or discard. |
| `claude/quizzical-bell` | 1 commit (April) | The parked `/engrave` skill (Claude Vision-only OMR). Superseded; safe to delete. |

**Method note.** `git merge-tree <base> <a> <b>` — the deprecated three-argument
form — reports no conflict on trees that plainly conflict. It said `clef-phase0-eval`
merged cleanly; `git merge-tree --write-tree main clef-phase0-eval` correctly
reports conflicts in `CLAUDE.md`, `tools/omr/README.md` and `transcribe.py`. Use
the two-argument form, and check its exit code.

---

## What does not yet work / known limitations


- **Detection was massively over-reporting until 2026-08-28.** `imgsz` defaulted to 2048
  in the CLI and 1280 in the backend, and both were far too large. `imgsz` is now derived
  **per cell** (`yolo_detector.imgsz_for_cell`, targeting a shown staff space of 16 px);
  `--imgsz 512` is the best fixed value and `--imgsz 2048` reproduces the old behaviour.
  Anything measured before that date — notehead counts, "100% pitch coverage", the
  July confidence probe's false-positive flood — was measured through this and may need
  re-reading. `benchmarks/omr-imgsz-sweep-2026-08/findings.md` and
  `benchmarks/omr-detector-scale/RESULTS.md`.

  The mechanism is *not* that "ultralytics letterboxes to `imgsz²` regardless of cell
  size" — an early account that this document repeated. `predict` builds
  `LetterBox(imgsz, auto=rect)` and scales the **longest side** to `imgsz`, padding only
  to a stride multiple, so what the model is shown is
  `canonical staff space × imgsz / longest side of cell`. That depends on the cell, which
  is why the fix is a rule rather than a number: a constant lands inside the good band on
  wide header cells and past its edge on the narrow interior cells of the same page.
- **The F1 98.8% was never measured at a setting the pipeline used.**
  `training/eval_on_score_cells.py` calls `detect()` without an `imgsz`, so it ran at the
  wrapper's old default of **640** while the pipeline ran 2048. It now inherits the
  per-cell rule, so re-running it would produce a comparable number for the first time —
  but the quoted 98.8% still refers to the old 640 run, and is repeated unqualified
  elsewhere in this file.
- **Instrument identity needs a text layer or a paid vision call.** 18/65 corpus PDFs
  have a text layer; the rest need `vision_fallback=True`.
- **One-line percussion staves are invisible.** `_group_into_staves` accepts only
  five-peak windows, so a single-line staff produces no `Staff` at all and every staff
  below it carries a `staff_index` one lower than its true slot. Proven in
  `tools/omr/tests/test_system_grouping.py`.
**OMR**

- **Custom YOLO classes (barlines, textDynamic) caused catastrophic forgetting.** Phase 3.4 expanded `nc` from 208 → 214; F1 collapsed to 79.3%. Currently: barlines via classical CV; textDynamic not detected. Re-introduce when there are 200+ examples per new class or seed with synthetic warm-up. See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.
- **OMR time-signature digit detection is unreliable** — the DSv2 model often misclassifies digit glyphs, so `time_signature` is `null` for many pages. The deterministic layer (merged 2026-07-11) filters left-edge instrument-number misreads, propagates a detected C / cut-C, and back-fills from a per-column beat-sum vote, but abstains rather than guessing on dense pages. Root cause is a synthetic→real domain gap, not a threshold.
- **Clef COVERAGE is the ceiling on the whole header layer.** Reading is solved — where a clef reaches the reader it is named correctly essentially always (7/7 on the hand-checked page, 0 false positives on 10 pages of Bach piano). Coverage on main is 43 of 191 header cells (23%) on Nottebohm and 3 of 168 (2%) on orchestral — the unmerged dot-veto fix would take the orchestral figure to 13. One branch of `locate_clef` holds the rest: the clef fuses into a cluster bigger than any C clef and the search stops. Measure it with `benchmarks/omr-clef-geometry/probe_clef_rejection.py`; three approaches are already measured and closed in `NEXT_SESSION_HEADER_CLUSTER.md`.
- **The header clef is computed and then thrown away.** `transcribe` reads a clef per staff in the header pass, uses it only to choose a key-signature slot table, and never writes it to the output — the measure pass then defaults the staff to treble. Everything the locator learns about orchestral clefs is currently spent on key signatures alone.
- **The key-signature vote can be captured by a repeated misread.** Cross-system agreement is treated as corroboration, but a systematic misread — same engraving, same glyph, same print quality — repeats by construction. Measured on Beethoven 6 p.2: two systems of one misread viola staff set the page's modal reference and rejected the one correct reading on it.
- **Two training recipes are DISPROVEN — do not retry.** ScoreAug/Augraphy domain augmentation made dense real-cell notehead recall *worse* than the clean control (0.652 → 0.384 → 0.122), and was best on synthetic validation while worst on real pages. Fine-tuning the shared detector on clef cells fixes clefs and collapses dense-page noteheads (2506 → 114). See `benchmarks/omr-phase*/` and the branch archives.
- **Per-measure beat sums on busy keyboard music** are close to but not exactly the time signature — LilyPond bar-check warnings typically report fractional offsets (1/32, 3/32) rather than full-beat errors.
- **Dense orchestral conductor's scores** (Mahler 5, Debussy La Mer) have more false negatives on small dynamics + grace notes. Path forward: the active hand-labeling rounds via `tools/omr/annotate`.

**Web app**

- **MusicXML correction patching is a stub** on main. Accepted diffs are written as XML comments, not actual measure replacements. (An unmerged March implementation exists on `claude/magical-bhabha` — unevaluated.)
- **PDF.js crop region in `DiffCard` is incomplete** — full crop viewport implementation has a TODO.
- **No database migrations.** Schema changes require dropping the DB.
- **Background tasks use FastAPI `BackgroundTasks` (no queue).** Server restart during a long OMR job loses the job. (Unmerged March job-queue implementation on `claude/peaceful-kapitsa` — unevaluated.)
- **Frontend type field names still say "audiveris"** (`audiveris_confidence`, `min_audiveris_confidence`, `pattern_type: 'audiveris_failure'`). They now refer to the primary OMR engine; rename when there's a migration story.

**Theory layer**

- Host-side only (needs node/tsx + the `gradus` submodule); the Docker backend container cannot run it. By design under the personal-use scope, but worth remembering when a web-app OMR run shows no theory enrichment.
- M4 pitch re-ranking applies to the **local YOLO pipeline only** (Vision OMR emits no pitch candidates).

---

## How we got here — major milestones

| Date | Milestone |
|---|---|
| 2026-03-25 | Initial ReEngrave scaffold — FastAPI + React + Audiveris OMR + Claude Vision diff |
| 2026-03-26 | Auth (JWT + httpOnly refresh) + Stripe payments + Docker stack + 79 backend tests |
| 2026-03-26 | Production deployment stack (Traefik + Let's Encrypt) + restructured 3-step UI |
| 2026-04-06 | Spiked a `/engrave` Claude Code skill (Claude Vision OMR only) — parked when Vision OMR proved too inaccurate on orchestral scores |
| 2026-05-22 | Phase 4 session — built full `tools/omr` pipeline: pitch / rhythm / voicing / line detection / LilyPond + MusicXML exporters / 156 tests / real-world validation on 5 PDFs. F1 98.8% on Bach WTC verdicts. |
| 2026-05-23 | Phase 1 connectivity-aware barline acceptance for orchestral pages + cross-cell tie pairing + voice splitting via `<backup>` + octave-clef pitch support |
| 2026-05-23 | **Consolidation.** Pruned 460MB of stale benchmark overlay dumps, merged YOLO pipeline into main. Local YOLO becomes primary OMR engine, Claude Vision OMR secondary, Audiveris removed entirely. Gradus library + multi-source XML comparison + theory checks landed in the same merge. |
| 2026-05-23 → 05-25 | **Catalog-training experiment** (Phases A–L, branch `claude/interesting-curran-3ca1b7`): IMSLP × MusicXML label generation worked (65/65 editions, 154k labels); every training attempt collapsed (H, I, J, K, L). Conclusion: stick with classical CV for structure + hand-labeling for symbols. Never merged. |
| 2026-05-24 | **Maestro theory layer shipped** (M0–M4 + follow-ups A/B, on main): bridge CLI, harmony/rhythm validation, scholarly cross-check (5 seed works), in-pipeline pitch re-ranking with auto-correction, wired into both OMR engines behind env flags. |
| 2026-06-08 → 06-10 | **Hand-labeling round on Beethoven 5.** Draw-from-scratch labeling mode + box delete (commit 1fe5484). Label set `v2-2026-06-08-beet5` (37 cells) created; v1 cleaned of structural-element boxes. Batches: 05-24 ✅ (became v2), 06-09 ✅ (35/36, not yet converted), 06-10 in progress (21/36), 06-08 abandoned. |
| 2026-06-10 | **Process audit** — docs refreshed, stale worktrees/branches pruned, orphaned label data committed. |
| 2026-07-10 → 07-13 | **Deterministic verification layers.** Five internal-consistency checks merged (time-sig disagreement, column rhythm sums, cross-staff measure counts, transposition-aware key agreement, advisory clef-from-register) — a safety net that abstains where detection is blind. Capstone: `docs/internal-consistency-checks.md`. Also the `catalog.yaml` nc=208 cap + `train_yolo.py` nc guard, closing the Phase-3.4 silent-head-reset footgun. |
| 2026-07-13 | **Two training recipes disproven, properly.** A fair three-way fine-tune showed ScoreAug/Augraphy domain augmentation is *worse* than the clean control on real cells, and best on synthetic validation — i.e. synthetic validation is misleading here. Separately, clef fine-tuning fixes clefs and collapses dense-page noteheads. Both dead; the real levers are verification layers and real data. |
| 2026-08-28 | **Phase 1 finally has a trusted baseline** — a hand-verified ground-truth fixture, a corpus probe and xfails for known gaps. That unblocked fixes that had been parked for want of one: phantom-staff collapse, music deleted after a false barline, staff-line removal being a total no-op on thick-line prints (0.9% → 89.7%), and paragraphs of body text being detected as staves. |
| 2026-08-28 | **The staff-header layer.** Clef reading by geometry rather than classification (`clef_geometry.py` + a CV C-clef locator), key signatures by fitting accidental positions to the slot table and reconciling across the page (`key_signature_*.py`), both working from one measured header window (`staff_header.py`). 18 correct / 0 wrong on 42 hand-read orchestral staves given a correct clef; 10/10 end-to-end on a clean engraving. |
| 2026-08-28 | **Retuned against the new Phase-1 geometry, and found a live defect.** The gap-bridging x-extent fix broke an invariant the header window relied on; correcting it took the two orchestral ground-truth pages from 6 correct / 7 wrong to 18 / 0, and turned two *shipped* wrong key signatures on Beethoven 6 p.2 into two correct ones. Also fixed brace residue blocking the clef search (Nottebohm coverage 32 → 43 cells). |
| 2026-08-28 | **Contextual analysis + the over-detection fix.** Systems by connectivity (43% → 86%), instrument identity from the text layer and, for scans, a margin reader, stable part slots (100% label purity), clef from instrument range. Re-running the whole-pipeline validation for the first time since May found `imgsz` over-reporting notes 2–4×; fixing it took end-to-end pitch precision 0.144 → 1.000 on the keyboard fixture, and every metric on every fixture improved. Also disproved clef-from-key-fit with measurements. |

---

## What's parked / next up

Immediate, in dependency order — the first two unlock the third:

1. **Fix the viola key-signature misread.** On Beethoven 6 p.2 the viola staff reads one sharp against a true one flat *under a correct alto clef*, so this is the key-signature reader, not the clef. It is the single thing blocking `claude/omr-clef-tenor-fixture` from merging. Reproduce: `python3 benchmarks/omr-key-signature/eval_key_signatures.py --mode component --page pastoral-p2`, ordinal 7.
2. **Clef coverage on orchestral prints.** 76% of Beethoven 5 header cells are rejected for one reason — an oversized cluster — at a height median of 7.2 staff spaces against a 5-space limit. Genuinely tall, not residue. Scoped, with three approaches already closed, in `benchmarks/omr-clef-geometry/NEXT_SESSION_HEADER_CLUSTER.md`.
3. **Then: write the header clef to the output.** It is read and discarded today. Once coverage and precision justify it, this is where clef work starts reaching the exported score rather than only the key-signature gate.

Also open:

4. **Decide whether v5/v6 enter the training catalog.** Six label versions are now on `main` (223 cells) but `catalog.yaml` unions only v1–v4. Adding the 62 clef cells is a *training* decision with a known hazard — it narrows the density prior, which is what collapsed dense-page noteheads 2506 → 114 — so it wants a measured run behind `wtc_forgetting_eval.py`, not a rebuild. The retrain can no longer silently re-trigger the Phase 3.4 head-reset collapse (nc=208 cap + `train_yolo.py` guard).
5. **Assess `claude/omr-dossier-verification-layer-eaf6d0`** — the last branch with capability `main` lacks (dossier-steered re-segmentation on a known bar count). Then the two March web-app implementations: measure-level MusicXML patching and the persistent job queue.

Parked (carried from NOTES.md — see there for full context):

- **GKB access for OMR context** — natural follow-on now that the maestro bridge exists.
- **DoReMi + MUSCIMA++ training data** — expand beyond DSv2.
- **RTMDet / yolov8x@200ep escalation** — Sean already approved the full run.
- **Multi-type barline classification** — single / double / final / repeat (classical-CV post-processing is the likely route).
- **MusicXML repeat signs** — currently dropped on export.
- **"Just ink" label class** — verified 2026-06-10: the annotate UI does **not** expose a noise/ink class. Add one if hard-negative-by-omission proves insufficient.
- ~~YOLO training via symphony MusicXML × IMSLP editions~~ — **executed and concluded** (see catalog-experiment section).
- ~~Maestro Analyzer as theory-constraint layer~~ — **shipped M0–M4** (2026-05-24).

---

## Repository layout (where to find things)

- **Web app entry:** [`backend/main.py`](backend/main.py) (all routes), [`frontend/src/App.tsx`](frontend/src/App.tsx) (all pages).
- **OMR pipeline:** [`tools/omr/`](tools/omr/) with [`tools/omr/README.md`](tools/omr/README.md) as the deep-dive.
- **Theory layer:** [`tools/maestro_bridge/`](tools/maestro_bridge/) (TypeScript CLI + `gradus` submodule), [`backend/modules/theory_layer.py`](backend/modules/theory_layer.py), [`backend/modules/maestro_bridge.py`](backend/modules/maestro_bridge.py), plan + results in [`docs/maestro-integration-plan.md`](docs/maestro-integration-plan.md).
- **Training:** [`tools/omr/training/`](tools/omr/training/). Cloud-GPU notes in `HANDOFF_PREMIUM_TRAINING.md` + `VAST_AI_SETUP.md`. Hand-labeled data: [`data/user-labeled/`](data/user-labeled/).
- **Benchmarks:** [`benchmarks/`](benchmarks/). The headline write-up is [`benchmarks/omr-phase4-session/retrospective.md`](benchmarks/omr-phase4-session/retrospective.md).
- **Setup & operational reference:** [`CLAUDE.md`](CLAUDE.md).
- **Open ideas:** [`NOTES.md`](NOTES.md) — including the **contextual analysis roadmap**.
- **Cross-session picture (2026-08-28):** [`docs/state-of-play-2026-08-28.md`](docs/state-of-play-2026-08-28.md).

---

## How to run things (quick reference)

```bash
# Full web stack (requires omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt)
docker compose up -d
# → http://localhost

# Standalone OMR CLI (no Docker)
python3 -m tools.omr.transcribe score.pdf --out out.json
python3 -m tools.omr.export out.json --format lilypond --out out.ly
lilypond out.ly

# Theory layer (host-side; one-time setup)
git submodule update --init && (cd tools/maestro_bridge && npm install)
MAESTRO_BRIDGE_ENABLED=true MAESTRO_PITCH_RERANK_ENABLED=true python3 ... # see CLAUDE.md

# Hand-label more cells (full flow: CLAUDE.md → "Hand-label cells for OMR training")
python3 -m tools.omr.annotate.select_cells_orchestral --out-dir benchmarks/omr-labeling-NEW --plan "tag=/path/to/score.pdf:12:6"
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-NEW
# → http://127.0.0.1:5050

# Train a new YOLO checkpoint
python3 tools/omr/training/train_yolo.py
```

See [CLAUDE.md](CLAUDE.md) for the full operational reference.
