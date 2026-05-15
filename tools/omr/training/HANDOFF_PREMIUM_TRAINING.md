# Handoff prompt — premium DeepScoresV2 training run

Drop the block below into a fresh Claude Code session to launch the
"actually fund the project" YOLO training run. The session has its own
context, so the prompt is fully self-contained.

## Before you paste

1. **Add Vast.ai credit**. Current balance is ~$24.58. The premium run
   needs ~$40-60 of credit to be safe. Sign in to vast.ai → Billing → Add
   Credit → $50.
2. **Confirm the SSH key is still on your account**. If `ssh-keygen` was
   re-run since last time, the old key won't work. Check at
   https://cloud.vast.ai/manage-keys/ — should show one ed25519 key
   labeled `vast.ai-training-...`.

## The prompt

```
I want to do a "premium" DeepScoresV2 YOLO training run on Vast.ai. The
prior session got us a baseline (mAP50 42% with yolov8m on the small
dense subset). This run scales up: full dataset, bigger model, more
epochs, music-aware augmentation. Target mAP50: 50-58%.

Working directory: /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/cool-kare-05197c/

Read these first:
  - .claude/plans/i-have-tried-several-unified-sphinx.md (skim "Phase 3" + "Operating Principle")
  - tools/omr/training/HANDOFF_PREMIUM_TRAINING.md (this doc)
  - tools/omr/training/VAST_AI_SETUP.md (full Vast.ai walkthrough)
  - The 2 most recent AttemptLog entries:
    /Users/seanjohnson/Desktop/gradus-vercel/scripts/attempt-log-entries/2026-05-15-omr-phase3-trained-yolo.json
  - benchmarks/omr-phase3/comparison-trained.md (baseline numbers + remaining gaps)

WHAT'S ALREADY BUILT (do not rebuild):
  - tools/omr/training/{download_dataset,prepare_yolo_data,train_yolo,eval_on_score_cells}.py
  - tools/omr/yolo_detector.py (wrapper)
  - tools/omr/annotate/run_yolo.py (drives YOLO over the verdict cells)
  - tools/omr/training/data/weights/deepscoresv2-yolov8m-r{1,2}-*.pt (baselines)

WHAT MIGHT BE WORTH IMPROVING BEFORE THIS RUN (free, ~30 min):
  - Expand _CATEGORY_MAP in tools/omr/yolo_detector.py to cover the top-30
    DeepScoresV2 class names. Right now ~37% of YOLO detections come back
    category="unknown" because we only mapped ~50 of 208 SMuFL names. A
    quick expansion pass (use deepscoresv2_classes.py + the names you see
    in benchmarks/omr-phase3/r2/_summary.json sample_class_labels) would
    make the comparison-against-template-matcher report way more readable
    when the new model is done.

THE TRAINING CONFIG (change ONLY if you have a justified reason):

  Instance:
    - GPU: A100 40GB (preferred — fits yolov8l batch=8 at imgsz=1280
      comfortably) OR RTX 4090 24GB (cheaper but tighter VRAM)
    - CPU: AVX2-required (Haswell 2013+ or any Ryzen) — DO NOT pick
      i7-3770 / Ivy Bridge era. The previous session lost 15min and $0.06
      to that. Filter Vast.ai search to confirm CPU model name BEFORE
      renting.
    - Disk allocation: 250 GB (compressed dataset 75 GB + extracted 100 GB
      + run artifacts 50 GB + buffer)
    - Internet: ≥ 1 Gbps download recommended (75 GB Zenodo pull)
    - Reliability: > 95%
    - On-demand (not interruptible — too long a run to risk preemption)

  Training (yolov8l, full dataset):
    python3 -m training.train_yolo \
      --data data/deepscoresv2-yolo/data.yaml \
      --weights yolov8l.pt \
      --epochs 100 \
      --imgsz 1280 \
      --batch 8 \
      --device 0 \
      --patience 20 \
      --workers 8 \
      --fliplr 0 --flipud 0 \
      --hsv_h 0 --hsv_s 0 --hsv_v 0.4 \
      --mosaic 1.0 \
      --degrees 2 \
      --name ds2-yolov8l-full \
      --extra-kwargs '{"cls": 1.0, "lr0": 0.01, "warmup_epochs": 5}'

  Notes on every flag:
    - yolov8l (not x): yolov8x's edge on this dataset size is small and
      training time roughly doubles. l is the sweet spot.
    - imgsz=1280 (not 2048): 2048 fits but doubles per-iter time for ~2-4
      mAP gain. Not worth it for our use case.
    - epochs=100 patience=20: model will likely early-stop around ep 60-80.
    - fliplr=0 flipud=0: music symbols are direction-sensitive (a sharp
      isn't a backwards sharp). DO NOT remove these.
    - hsv_h=0 hsv_s=0: engraved music is monochrome. Hue/sat aug would
      synthesize impossible colors and may hurt the model.
    - hsv_v=0.4: keep brightness aug — real scans vary in brightness.
    - degrees=2: small rotation range for scan-skew robustness. Don't go
      higher; staff lines are horizontal in real music.
    - cls=1.0: keep ultralytics' default classification loss weight.
      Higher would overweight cls vs box; not needed at 208 classes.
    - lr0=0.01: ultralytics default. The Adam vs SGD auto-pick will run.

  Estimated:
    - Wall time: 25-35 hours
    - Cost: $35-50 on A100 40GB at ~$1.30/hr
    - Expected mAP50: 50-58%

EXECUTION PLAN (autonomous):

  1. Find an instance per the spec above. Filter for GPU=A100 40GB,
     disk >= 250 GB, reliability > 95%. Sort by $/hr.
  2. Pick one in $1.00-$1.60/hr range. Show me the candidate before
     renting (don't rent without confirmation).
  3. Provision with the same NVIDIA CUDA template + 250 GB container
     size as the prior session.
  4. SSH in, install pip deps:
       pip3 install --break-system-packages --index-url https://download.pytorch.org/whl/cu124 torch torchvision
       pip3 install --break-system-packages ultralytics
  5. scp tools/omr/training/ to /workspace/reengrave-training/
  6. Download dataset:
       python3 -m training.download_dataset --full --out data/deepscoresv2/
     (~10-30 min depending on network)
  7. Extract:
       tar -xzf data/deepscoresv2/ds2_complete.tar.gz -C data/deepscoresv2/
     (~5-10 min)
  8. Prepare YOLO format:
       python3 -m training.prepare_yolo_data \
         --src data/deepscoresv2/ds2_complete \
         --dst data/deepscoresv2-yolo
     (~5 min)
  9. Smoke train (1 epoch on synthetic):
       python3 -m training.train_yolo --weights yolov8l.pt --smoke --device 0
     Verify env works.
  10. Launch full training in tmux with the config above. Set up a Monitor
      that emits one line per epoch (look at /private/tmp/.../prior session
      for the pattern; use the FIXED-PATH variant that picks results.csv
      by mtime not alphabetically).
  11. Monitor: every notification, just acknowledge briefly with the
      epoch's mAP50. Do not break the user's flow with paragraphs.
  12. When training completes (or early-stops):
      a. SCP best.pt to tools/omr/training/data/weights/
         deepscoresv2-yolov8l-full-100ep.pt
      b. DESTROY the instance immediately (the meter ticks until you do)
      c. Run YOLO on the 30 verdict cells (tools/omr/annotate/run_yolo.py)
         — same as prior session
      d. Build a new comparison-trained-v2.md including:
         - Side-by-side: yolov8m-r1, yolov8m-r2, yolov8l-full
         - mAP50 per class category if available from the val report
         - Per-cell detection counts on our 30 cells
         - Inference time delta
      e. Write an AttemptLog entry at scripts/attempt-log-entries/
         YYYY-MM-DD-omr-phase3-premium-yolo.json
      f. git add + commit

  HARD STOPPING RULES:
    - If training doesn't show GPU utilization > 50% within 5 min of start,
      stop and investigate.
    - If credit drops below $5 BEFORE training is in its final 10 epochs,
      destroy the instance and report. Don't run dry.
    - If the instance gets preempted: it shouldn't (we picked on-demand),
      but if it does, pull the latest checkpoint via Vast's web console
      auto-snapshot if available; otherwise document and stop.
    - If anything in the bootstrap fails twice, destroy the instance and
      ask me before retrying.

OUT OF SCOPE FOR THIS SESSION:
  - Don't fine-tune on the existing yolov8m weights — train from yolov8l
    pretrained COCO start.
  - Don't change the augmentation flags from what's specified above.
  - Don't expand to ds2_dense + ds2_complete training jointly.
  - Don't try multi-GPU.
  - Don't port verdicts onto YOLO detections (separate task; do AFTER
    this run).

REPORT BACK with:
  - Final mAP50, mAP50-95, recall on val set
  - Side-by-side comparison vs yolov8m baseline
  - Cost spent
  - Any unexpected issues
  - The path of the new best.pt locally

START NOW.
```

## Quick reference — what changed in our scripts since the last run

- `tools/omr/training/train_yolo.py` now has CLI flags for music-aware
  augmentation overrides (`--fliplr`, `--flipud`, `--hsv_h`, `--hsv_s`,
  `--hsv_v`, `--mosaic`, `--mixup`, `--degrees`, `--cls`, `--box`) and a
  generic `--extra-kwargs` JSON pass-through. The flags above use them.

- `tools/omr/training/download_dataset.py` already supports `--full` for
  ds2_complete. No change needed.

- The default `--name` is `ds2-yolov8m`; the new run uses
  `--name ds2-yolov8l-full` so its outputs go to a separate directory.

## What's NOT in this prompt

- The new session won't expand `_CATEGORY_MAP` automatically — it's
  flagged as a "do this if you have time" item, not gated on. If you
  want it done first, tell the new session to do that before training.

- The new session won't port verdicts onto YOLO detections — that's a
  separate task after the new model exists. Tell it to do that AFTER
  training if you want measurable precision/recall numbers vs the
  template matcher's 92.4%.
