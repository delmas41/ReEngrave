# Scan vs engraved weight routing (2026-09-03)

The engraved-vs-scanned domain gap is the largest accuracy cliff in the
project — pooled OMR-NED **0.13–0.14 on the engraved orchestral benchmark
against 0.7960 on the five-publisher scan benchmark** — and since 2026-09-03
the two domains have different best-measured weights:

| domain | best-measured weights | evidence |
|---|---|---|
| scanned | `deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt` (production) | beet5-p1 half-notes 8→27, duration recall 0.388→0.435 (`omr-labeling-survey-2026-09/SHIP_RESULTS.md` §4b) |
| engraved | `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (prior production) | 11-work OMR-NED 0.1399 vs 0.1421 no-direction-text; mozart-sym41 +0.0146 under hollow (SHIP_RESULTS §4c) |

The hollow ship accepted the +0.0022 engraved cost because there was ONE
weights slot and ReEngrave's product is scanned scores. Routing removes the
forced choice: each domain gets the weights that measured best on it, and the
engraved side of the trade is un-paid. A side effect worth naming: the
recorded accuracy headline (0.1306 on `44a1745`) was measured with the PRIOR
weights and went stale the moment the hollow repoint landed — routing makes
default runs on engraved inputs use those weights again, so the recorded
figure describes shipped behavior once more.

## The discriminator, measured

A scanned page's ink arrives as a full-page **raster image**; an engraved
page's ink arrives as **vector drawings** (staff lines, stems, beams are path
ops in every typesetter measured, including non-LilyPond ones). Text is NOT a
discriminator — IMSLP 575951 is a scan WITH an OCR text layer, and the Mozart
K319 scan stamps 175 chars of text on a 0.962-coverage page.

`probe_pdf_domain.py`, 147 pages over 51 documents: 3 LilyPond benchmark
renders (engraved), the 5 scan-benchmark editions, and an every-7th systematic
sample of `library/editions` (43 docs — IMSLP scans plus, usefully, two real
digital typesets the sample caught: the Handel Messiah lead-sheet and
Kirchhoff *L'ABC musical*, both `--local`):

| signal | scan pages | engraved pages (incl. the 2 typesets) | gap |
|---|---|---|---|
| total raster coverage | **0.95 – 1.0+** (tiled Ravel: 8 strips × 0.143 = 0.999) | **0.000** | ~0.95 wide |
| vector drawing count | **0 – 4** | **428 – 2058** | empty over all 147 pages |

Both constants sit in measured gaps, not tuned:

- `SCAN_TOTAL_RASTER_COVERAGE = 0.5` — nearest populations 0.000 / 0.95.
  **Total** coverage, not max: the Ravel Durand scan is tiled into eight
  strips of 0.143 each and max-coverage would misread it.
- `ENGRAVED_MIN_DRAWINGS = 50` — 12× the observed scan maximum (4), 8.5×
  under the observed engraved minimum (428).

**Pages with neither signal abstain** (verdict `unknown`): the probe found
genuinely blank pages (Mozart K319 p1, Firebird p1: 0 images, 0 drawings, 0
text) and digital *title* pages whose only content is text (Kirchhoff p0).
A text-only rule was considered and dropped — every digital doc sampled has
hundreds of drawings on its MUSIC pages, so the doc-level verdict never needs
the risky text evidence.

Cost: ≤ 17 ms per page (dense LilyPond, `get_cdrawings`), ≤ 1 ms typical for
scans — noise against a multi-second model load.

## Document verdict: any scan page wins

Aggregated over exactly the pages being transcribed:

1. any page `scanned` → document **scanned**;
2. else any page `engraved` → document **engraved**;
3. else → **unknown** → DEFAULT_WEIGHTS.

The asymmetry is deliberate and matches the measured costs of misrouting.
Sending an engraved input to the scan weights costs +0.0022 pooled (the
hollow ship's measured, near-neutral delta); sending a scanned input to the
engraved weights forfeits the half-note gains (27 → 8 on beet5-p1) — so every
ambiguous case falls toward the scan/default side. Rule 1 also handles the
common real-world composite: an IMSLP scan behind a digitally-generated cover
page classifies scanned, because the music pages do.

## What routing deliberately does NOT touch

- **Explicit choice always wins.** A `--weights` flag, an `OMR_WEIGHTS_PATH`
  env var, or a caller passing `weights=` disables routing for that run — the
  same contract the clef-specialist slot has.
- **DPI.** The 300/600 split is a sparse-vs-dense trade
  (`benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md`), not a scan-vs-engraved
  one — both benchmark families are dense. Routing DPI off this verdict would
  change measured behavior on both benchmarks for no measured reason.
- **The clef-specialist weights.** `OMR_CLEF_WEIGHTS` is a separate,
  decoupled slot and is unaffected.
- **Missing engraved weights fail soft.** A machine holding only the
  production file logs one stderr line and runs everything on
  DEFAULT_WEIGHTS — routing can never make a previously-working machine fail.

## Where it lives

- `tools/omr/input_domain.py` — the classifier (`classify_pdf_domain`),
  stdlib-only at import, fitz lazily inside; never raises, abstains instead.
- `tools/omr/transcribe.py` — `ENGRAVED_WEIGHTS`, `_route_weights()` (the
  decision, injectable classifier, same seam shape as
  `_resolve_clef_weights`), and the `weights: str | None = None` default on
  `transcribe()`; the CLI's `--weights` now defaults to routing. The result
  JSON records `weight_routing` (verdict + per-page evidence + reason), and
  `weights` still records exactly what ran.
- `backend/modules/local_omr.py` — passes `weights=None` when
  `OMR_WEIGHTS_PATH` is unset, so the web app routes too (the container mounts
  the whole weights directory, both files present). The fail-fast check still
  fires before the job on the one file no run can proceed without.
- Every benchmark/eval harness passes `weights=` explicitly (verified across
  all 26 call sites), so **no benchmark figure changes**: `orchestral_eval`
  keeps its own default (the prior weights — which is also what routing now
  serves engraved inputs, so the recorded headline and shipped behavior agree),
  and `scan_eval` pins `DEFAULT_WEIGHTS` (= what routing serves scans).

## Verification (2026-09-03)

- `tools/omr/tests/test_input_domain.py` — 14 tests on synthetic PDFs built
  in-test, one per corpus trap: OCR text layer on a scan, tiled strips, blank
  page, text-only title page, small raster logo on an engraving, digital
  cover over a scan, page_indices restriction, unopenable file.
- `tools/omr/tests/test_weight_routing.py` — 21 tests on the routing seam:
  kill-switch (classifier never consulted), each verdict's target, env
  override, missing-engraved soft fallback (stderr, reason recorded),
  page-sample cap, JSON-ready provenance, absolute paths.
- Full OMR suite: 1758 passed; the one failure
  (`test_direction_text::test_the_env_var_restricts_the_rungs`) fails
  identically on the unstashed base — pre-existing, this worktree lacks
  `.venv-surya`.
- **Byte-identity A/B**, four full transcribe runs, compared field-for-field
  after stripping `runtime` and `weight_routing` only:

  | input | routed | vs explicitly pinned | result |
  |---|---|---|---|
  | LilyPond beet5 fixture | verdict `engraved` → prior weights, 20.8 ms | `--weights …imgsz2048-ft-30ep.pt` | **identical** (535 detections, 144 measures) |
  | Litolff beet5 scan p.1 (IMSLP 984073) | verdict `scanned` → hollow weights, 8.7 ms | `--weights …hollow-ft-2026-09-03.pt` | **identical** (460 detections, 192 measures) |

  So routing is exactly equivalent to the explicit choice on both sides of
  the fork, and the classification cost is ~9–21 ms against a multi-second
  model load.

## What would falsify the thresholds

A digital typesetter that draws music pages with under 50 vector paths (all
measured ones emit hundreds — staff lines alone), or a scan whose raster
covers under half the page. Neither exists in the 147-page corpus; if one
appears, it lands on `unknown` → default weights, i.e. current-production
behavior, and shows up in the result's `weight_routing.classification`
evidence for diagnosis. Re-run `probe_pdf_domain.py` before moving either
constant.
