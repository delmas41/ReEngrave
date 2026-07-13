# Handoff prompt — clef fine-tune: end-to-end demo + hardening

Paste everything below the line into a fresh Claude Code session in the ReEngrave repo.

---

You're picking up finished OMR work in the ReEngrave repo (`/Users/seanjohnson/Desktop/ReEngrave`, run from this main checkout). A previous session fine-tuned the local YOLO clef detector and it worked. Your job: demo it end-to-end, then harden it. **Read this whole message before acting.**

## What was done (the win)
The production YOLO OMR model detects almost no clefs on real orchestral scans (9% detection, 0% type accuracy), so the pipeline defaults every staff to treble — the "all-treble disease." A previous session hand-labeled 62 real clef cells across 4 scores → fine-tuned the production checkpoint on only those (clean, frozen backbone, low LR) → **clef detection 9%→100%, type accuracy 0%→87%, no notehead forgetting.** Full write-up: `tools/omr/training/CLEF_FT_PHASE0_RESULTS.md`. Work is on branch `clef-phase0-eval`.

## Key files & paths
- **Production weights** (F1 98.8% Bach WTC) — **NEVER overwrite**: `omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`
- **New fine-tuned weights** (clef-fixed; demo/validate this): `omr-weights/deepscoresv2-yolov8l-clef-ft-2026-07-13.pt`
- Do NOT use `omr-weights/deepscoresv2-yolov8l-phase-j-mix-30ep.pt` (collapsed run).
- Working eval: `tools/omr/training/clef_count_eval.py`
- Clean training catalog (v5+v6 only): `data/user-labeled/v5-2026-07-12-clef`, `v6-2026-07-13-clef-diverse`, catalog at `data/user-labeled-clean/catalog.yaml`
- Eval cell sets (cells + verdicts): `benchmarks/omr-labeling-2026-07-12-clef/` (44 cells — the baseline set) and `benchmarks/omr-labeling-clef-diverse/` (151 cells, 47 labeled)
- Scores (real IMSLP scans): `/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/` — `PDF Scores/Mahler_5_.pdf`, `PDF Scores/IMSLP421137-PMLP03667-Ravel_Bolero.pdf`, `PDF Scores/IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf`, `IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf`

## Environment gotchas (don't relearn these the hard way)
- ultralytics 8.4.50 + torch 2.8 + MPS on the system python3. Train with `--device mps` (~15 min/30 epochs, freeze works); eval with `--device cpu`. MPS→CPU op-fallback warnings are harmless.
- **Use `imgsz 1280` everywhere.** The weights say "imgsz2048" but the runtime + these canonical cells work at 1280; higher imgsz makes the model over-detect phantom noteheads.
- **Do NOT trust catalog-val mAP** — it's ~0.002 even for the production model (over-detection on small cells). Use `clef_count_eval.py` (count-based) instead.
- Clef classes/indices: `clefG`=5 (treble), `clefCAlto`=6, `clefCTenor`=7, `clefF`=8, `clefUnpitchedPercussion`=9. `verdicts_to_yolo_labels` needs `--weights <production.pt>` to read class names.
- **v1–v4 user-labeled data is CONTAMINATED** (key-sig accidentals not distinguished from note accidentals). Only v5/v6 are clean. Exclude v1–v4 from any clef training.
- **Known bug:** `tools/omr/annotate/select_clef_cells.py` writes a minimal manifest (missing `cell_png_path`, `cell_canonical_w/h`), so `verdicts_to_yolo_labels` fails on it. If you make a new batch, fix the selector to write the full schema (copy the manifest-entry code from `select_cells_orchestral.py`), or post-patch `cells.json` (add `cell_png_path`=abs path, `cell_canonical_w/h`=PNG dims, `measure_index`=0, `source_tag`).

## Tasks (in order)

### 1. End-to-end Mahler demo — the payoff to show
Transcribe a Mahler orchestral page with BOTH weights and compare the per-staff clef read.
- Page: index 11 (printed p13, m.85 — production reads 26/26 treble). `python3 -m tools.omr.transcribe "<Mahler PDF>" --pages 11 --weights <weights.pt> --dpi 300 --out <out.omr.json>` (~14 min/dense page — background it).
- Compare `pages[].systems[].staves[].clef` in each omr.json. Expect production = all treble; fine-tuned = realistic mix (violas→alto, low instruments→bass, timpani→perc).
- **Acceptance:** fine-tuned reads a clef mix matching the actual page (verify against the score image).

### 2. Broaden the forgetting audit
Confirm no regression on non-clef detection.
- The Bach WTC verdict set (the F1 98.8% benchmark) is at `benchmarks/omr-phase3.4/verdicts-yolo-realft-ported/` (`wtc-*.verdict.json`). Locate its cell images, then build a verdict-F1 comparison (production vs fine-tuned) via IoU+class matching — or extend `clef_count_eval`'s logic to all classes.
- **Acceptance:** fine-tuned WTC F1 ≈ production's (no meaningful non-clef regression).

### 3. Fix alto/tenor confusion
The fine-tuned model reads 2 alto clefs as tenor (same C-clef, one line apart). Add alto examples.
- Fix the selector bug (above), extract more viola-staff (alto) cells, label → `v7`, rebuild the clean catalog (v5+v6+v7), re-fine-tune, re-eval.
- **Acceptance:** alto recall up (aim 3/3) without regressing tenor.

### 4. Deploy (only after 1–3 pass)
Set `OMR_WEIGHTS_PATH=omr-weights/deepscoresv2-yolov8l-clef-ft-2026-07-13.pt` (in `backend/.env` for the web app, or `--weights` for the CLI). Fully rewindable — revert the env var to roll back.

## Guardrails
- NEVER overwrite the production `.pt`. New weights → new files.
- Fine-tune ONLY on clean data (v5, v6, v7…); exclude v1–v4.
- Commit verdicts + results to branch `clef-phase0-eval`.
- The fine-tune recipe that worked: from the production checkpoint, `--extra-kwargs '{"lr0":0.001,"optimizer":"AdamW","freeze":10,"warmup_epochs":2,"cos_lr":true}'`, `--epochs 30 --imgsz 1280 --batch 8 --device mps`, take `last.pt`.
