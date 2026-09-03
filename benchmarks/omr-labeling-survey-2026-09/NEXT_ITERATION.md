# Next iteration — keep the half-note gain, kill the completeness regression

**Context:** `CLOUD_2048_RESULTS.md` (the cloud imgsz-2048 run: p29 reads
half-notes much better — with-duration recall 0.435→0.605 — but regresses the
5-page scan-e2e 0.7512→0.7761 by detecting fewer rests/accidentals; Sean chose
KEEP PRODUCTION, ITERATE). Production scan weights are untouched. p29 checkpoints
staged at `omr-weights/cloud-2048{,-30ep,-ablation}/` (gitignored, 50 total).

## The one fix that matters

The completion pass only labeled **black noteheads + augmentation dots**, so on
the hollow cells **rests and accidentals were unlabeled background** — and 30
epochs learned to suppress them. **Fully complete the cells** (add rests +
accidentals) and the same long fine-tune keeps the half-note gain without the
completeness loss.

## Ordered steps

1. **Fill out the cells (Sean's labeling).** Over the SAME hollow cell-sets
   (v7–v12: `benchmarks/omr-labeling-hollow{,2,3}-2026-09-*`), run single-symbol
   **rests** and **accidentals** passes so every cell is complete. Two options,
   decide per batch: (a) human single-symbol passes (safest — the round-2 audit
   dropped model rests/accidentals as FP-prone: restWhole on slur arcs,
   accidentalDoubleSharp on trills); (b) an *audited* detector completion for
   just those classes if it proves clean on the sparse cells. Stamp
   `inspected_passes` so coverage is provable. Serve one batch at a time on :5050
   as in Phase 2.
2. **Re-convert** the fully-completed cells → refreshed v9–v12 (and v7/v8 if
   re-completed). `verdicts_to_yolo_labels` + the completion merge scripts.
3. **Widen the scan-e2e benchmark to the non-German publishers** (Sean asked):
   add rows for **Universal/Mahler 1, Novello/Elgar 1, Durand/La mer** on pages
   DIFFERENT from the training cells. Each needs a **verified measure window**
   (which reference measures the scanned page covers) — the harness refuses an
   unverified window. Needs reference MusicXML per edition (Mahler/La mer yes;
   check Elgar). This is the benchmark that must gate the next ship.
4. **Re-run the cloud 2048** (`CLOUD_HANDOFF.md` / `run_cloud_training.sh`, ~$0.50
   / ~30 min) on the fully-completed mix. **Drop Tchaikovsky v12** (ablation
   confirmed it halves the gain). Keep imgsz-2048 training, 3× dense oversample,
   `save_period=1`.
5. **Re-gate on BOTH axes — they DISAGREE.** `gate_all.py` (beet5-p1 hollow =
   note recall, where p29 won) AND the widened `scan_eval.py` (full-symbol
   OMR-NED, publisher-diverse, where p29 lost). The narrow one alone would have
   shipped a regression. Ship only if BOTH hold: half-note gain kept AND
   scan-e2e not regressed.
6. **Ship the winning checkpoint into the SCAN slot only** (`DEFAULT_WEIGHTS` in
   `tools/omr/transcribe.py` — the router's "Scanned PDF Weights"; engraved input
   routes to `ENGRAVED_WEIGHTS` and is unaffected). Sean wants both slots labeled
   plainly (**Scanned PDF Weights** / **Digital Engraving Weights**). Back up the
   old file, verify the shipped weights LOAD (nc=208) and route correctly, admit
   the versions to `catalog-versions.txt`, get Sean's explicit OK before the live
   repoint.

## Settled facts (don't re-litigate)

- **imgsz is a NON-FACTOR** at inference (byte-identical 512/1024/1280 — canonical
  cell rescaling). Keep OMR_IMGSZ small; the "best at ~1048" idea is the old
  full-page path, not this cell-based pipeline. TRAINING at imgsz-2048 is a
  *separate* knob that held dense recall over 30 epochs (896 collapsed after
  epoch 1) — keep it, though it's confounded with epochs/oversample.
- **Tchaikovsky v12 (low-res) hurts** — its cells complete to ZERO black
  noteheads; defer low-res to its own methodology.
- **A scan checkpoint's engraved score is irrelevant** (router sends engraved
  elsewhere) — judge scan checkpoints on scan benchmarks only.

## Multi-session hygiene (learned the hard way this session)

- **Work in your OWN dedicated worktree off origin/main**, not the shared main
  checkout — it was `git checkout`'d onto another session's branch mid-task and
  deleted tracked files. Push your branch to main additively; `git fetch` + rebase
  when origin/main moves (it moved ~6× during this session). See
  `feedback_shared_checkout_collision`.
- **Worktree venv gotcha:** `.venv-omrned` / `.venv-surya` are gitignored (main
  checkout only). Symlink them in, or set `OMRNED_PYTHON`, or scan_eval/omr_ned
  refuse. Weights: pass ABSOLUTE paths (the relative `DEFAULT_WEIGHTS` string only
  resolves from the repo root, and the file is gitignored — absent in a worktree).
- Build tarballs with `COPYFILE_DISABLE=1` (macOS bsdtar bundles `._*` files that
  Linux globs read as label `.txt` → UnicodeDecodeError).
