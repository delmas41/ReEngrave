# Handoff — FAIR test: does ScoreAug augmentation help, beyond plain fine-tuning?

**Why this exists.** A prior run (2026-07-13, vast.ai 4090) trained yolov8l
**from COCO** on the ScoreAug-augmented dense set and got near-zero recall on real
orchestral cells (memory `project_domain_augmentation`). That was *not* a clean
augmentation test: (a) from-COCO undertrains vs the production checkpoint, and
(b) there was **no control** to isolate augmentation's effect. This run fixes
both.

## The experiment — 3 models, ONE rented box

| Model | What | Weights |
|---|---|---|
| **Baseline** | production, unchanged | `omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (nc=208) |
| **Arm A** | fine-tune production on the **AUGMENTED** dense set | `data/deepscoresv2-yolo-scoreaug/data.yaml` |
| **Arm B** (control) | fine-tune production on the **CLEAN** dense set | `data/deepscoresv2-yolo/data.yaml` |

Arm A and Arm B use the **identical recipe** (below). The **only** difference is
Arm A's train split carries ScoreAug/Augraphy-degraded twins of the pages; Arm B
sees the clean pages only. Both share the **same clean val** (build_scoreaug
points `val:` at the original prepared val), so their val metrics are directly
comparable.

**This is a real fine-tune, NOT a head reset.** Production is nc=208 and the data
is nc=208, so `train_yolo.py`'s nc-guard *passes* — do **NOT** pass
`--allow-nc-expansion` (that flag is only for the from-COCO/214 case, and here it
would mask a genuine mismatch if one ever appeared).

**Success = Arm A beats Arm B on dense notehead recall AND neither regresses the
WTC keyboard set** → augmentation genuinely helps beyond plain fine-tuning.

## Where eval runs

Eval runs **on the Mac** (it has torch 2.8 + ultralytics 8.4.50; the cell PNGs +
WTC verdicts are all in the main checkout). The box is **only** for training.
So the box never needs the cells — it needs code + DSv2 + blanks + the production
weights (the fine-tune starting point). Ship back just the two `best.pt`.

---

## 1. Rent + provision the box (RTX 4090, ~$0.34–0.40/hr, 120 GB disk)

SSH key `vast.ai-training-20260514` is already registered and equals the Mac's
`~/.ssh/id_ed25519`. If a host throws an OCI/container error on boot, destroy it
(≈ no charge) and pick another. zsh does **not** word-split unquoted vars — put
ssh options inline.

```bash
# from the Mac; SSH_DEST is what vast.ai shows, e.g. root@ssh5.vast.ai -p 12345
SSH="ssh -o StrictHostKeyChecking=accept-new"
$SSH $SSH_DEST 'nvidia-smi --query-gpu=name,memory.total --format=csv && python3 -V'
```

Env on the box:

```bash
source /venv/main/bin/activate    # vast pytorch image
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
uv pip install ultralytics augraphy opencv-python-headless
```

Code onto the box (exclude the heavy training/data dir):

```bash
# from the Mac, in the worktree root:
tar czf /tmp/reengrave-omr.tgz --exclude='tools/omr/training/data' tools/omr
scp /tmp/reengrave-omr.tgz $SSH_DEST_SCP:/root/       # SSH_DEST_SCP uses -P for port
$SSH $SSH_DEST 'mkdir -p /root/re && tar xzf /root/reengrave-omr.tgz -C /root/re'
# the labels/catalog aren't needed on the box (eval is local); code is.
```

Production weights → box (Mac→box scp drops ~52 MB mid-transfer; use rsync with
resume in a retry loop):

```bash
until rsync -e "ssh -p $PORT" --partial --append --progress \
    /Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    root@$HOST:/root/re/omr-weights/ ; do echo "retry rsync"; sleep 2; done
```

Work in tmux on the box (`tmux new -s train`); everything below runs there, in
`/root/re`.

## 2. Build BOTH datasets (clean = Arm B, augmented = Arm A)

```bash
cd /root/re
# TISMIR blank pages (~186 MB, sha-verified, idempotent)
python3 -m tools.omr.training.augment_scoreaug --download-blanks \
    --blanks-dir tools/omr/training/data/blanks

# DSv2 dense: downloader only DOWNLOADS — untar it yourself; --src is the SUBDIR;
# prepare runs as a MODULE (relative imports). (These 3 fixes are from the prior run.)
python3 -m tools.omr.training.download_dataset --out data/deepscoresv2
tar -xzf data/deepscoresv2/ds2_dense.tar.gz -C data/deepscoresv2
python3 -m tools.omr.training.prepare_yolo_data \
    --src data/deepscoresv2/ds2_dense --dst data/deepscoresv2-yolo
#  -> data/deepscoresv2-yolo/data.yaml   ← Arm B (clean), nc=208, 1362 train + 352 val

# augmented twin set (train only degraded; val stays clean and identical)
python3 -m tools.omr.training.build_scoreaug_dataset \
    --prepared data/deepscoresv2-yolo \
    --out      data/deepscoresv2-yolo-scoreaug \
    --blanks-dir tools/omr/training/data/blanks \
    --fraction 0.5 --augs-per-image 1 --seed 41 --require-augraphy
#  -> data/deepscoresv2-yolo-scoreaug/data.yaml   ← Arm A (augmented)
```

Quick sanity before spending GPU: both data.yaml should be nc=208, and the
augmented train dir should have ~1.5× the clean train image count.

## 3. Fine-tune — TWO runs, identical recipe (differ only in --data + --name)

```bash
# smoke first (≈1 min; catches env/path issues):
python3 -m tools.omr.training.train_yolo --smoke --device 0

# recipe knobs (both arms): fine-tune from PRODUCTION, low LR, short, music-safe.
# NO --allow-nc-expansion (nc matches → guard passes → head is PRESERVED).
# hsv_v (0.4) + mosaic (1.0) are left at ultralytics defaults (benign scan aug);
# only the direction/hue augs are zeroed. lr0=0.001 (10× below the from-COCO run).

# ---- Arm A: AUGMENTED ----
python3 -m tools.omr.training.train_yolo \
    --data data/deepscoresv2-yolo-scoreaug/data.yaml \
    --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    --epochs 15 --imgsz 1280 --batch 2 --device 0 --patience 8 \
    --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 --degrees 2 \
    --project runs --name ft-scoreaug-armA \
    --extra-kwargs '{"lr0": 0.001, "lrf": 0.01, "warmup_epochs": 1}'

# ---- Arm B: CLEAN control (same recipe, clean data) ----
python3 -m tools.omr.training.train_yolo \
    --data data/deepscoresv2-yolo/data.yaml \
    --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    --epochs 15 --imgsz 1280 --batch 2 --device 0 --patience 8 \
    --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 --degrees 2 \
    --project runs --name ft-clean-armB \
    --extra-kwargs '{"lr0": 0.001, "lrf": 0.01, "warmup_epochs": 1}'
```

> **`--batch 2` is load-bearing.** DSv2 dense pages carry 3–4k objects each, and
> yolov8's TaskAlignedAssigner OOMs at batch ≥ 8 on a 24 GB card (it silently
> CPU-thrashes and it/s collapses). Batch 2 fits a 4090 at ~7–9 GB. Do not raise
> it on a 24 GB card.

> **Why no backbone freeze.** Freezing (`freeze: 10`) would protect WTC harder,
> but domain-texture robustness lives in the *early* backbone conv layers — the
> exact layers a freeze would pin. Freezing could blunt the mechanism under test
> and yield a false "augmentation doesn't help." Low LR + 15 epochs + same-class
> data is the forgetting guard instead; the WTC bar (§5) verifies it worked. If
> the WTC bar fails, re-run both arms with `{"freeze": 10, ...}` and re-compare.

Each run ≈ 30–45 min (Arm A longer — 1.5× images). Watch `nvidia-smi`; watch
`runs/ft-*/results.csv` for the val curves (used in §5 to check both arms
converged — if Arm B plateaus by ~ep10, Arm A's extra steps don't confound the
comparison).

## 4. Ship the two best.pt back to the Mac

```bash
# from the Mac:
mkdir -p /Users/seanjohnson/Desktop/ReEngrave/omr-weights/scoreaug-fair-test
for arm in ft-scoreaug-armA ft-clean-armB; do
  until rsync -e "ssh -p $PORT" --partial --append --progress \
      root@$HOST:/root/re/runs/$arm/weights/best.pt \
      /Users/seanjohnson/Desktop/ReEngrave/omr-weights/scoreaug-fair-test/$arm-best.pt ; do
    echo "retry"; sleep 2; done
done
# also grab results.csv for the convergence check:
rsync -e "ssh -p $PORT" root@$HOST:'/root/re/runs/ft-*/results.csv' /tmp/  # rename per-arm
```

**Then DESTROY the box** (vast.ai console). Training is done; eval is local.

## 5. Eval — 3-way, on the Mac (this is the payoff)

Run from the worktree root (`PYTHONPATH=.`), `--repo-root` = the MAIN checkout
(has the gitignored cell PNGs + WTC verdicts). `W=/Users/seanjohnson/Desktop/ReEngrave/omr-weights`.

### 5a. DENSE WIN — notehead recall on 140 hand-labeled real orchestral cells

```bash
PYTHONPATH=. python3 -m tools.omr.training.eval_dense_recall \
    --weights $W/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
              $W/scoreaug-fair-test/ft-scoreaug-armA-best.pt \
              $W/scoreaug-fair-test/ft-clean-armB-best.pt \
    --labels production armA armB \
    --repo-root /Users/seanjohnson/Desktop/ReEngrave \
    --imgsz 1280 --conf 0.25 --device cpu \
    --json-out benchmarks/scoreaug-fair-test/dense_recall_1280.json
# (140 cells: beet5 76 / mahler5 35 / lamer 29 = 534 GT noteheads. recall is the
#  metric; precision is confounded by incomplete human GT.)
# Also run --imgsz 2048 as a resolution sanity check (production is native-2048).
```

### 5b. WTC REGRESSION bar — must not drop keyboard-Bach recall vs Baseline

`wtc_forgetting_eval.py` builds model-agnostic GT from the ported WTC verdicts
(TP boxes + FN points) and scores two checkpoints. Run it twice (prod-vs-A,
prod-vs-B); `--prefix wtc` restricts to the 20 keyboard-Bach cells. The absolute
F1 here is a *different* scoring than the historical 98.8% — what matters is the
**recall DELTA vs production ≈ 0** (no forgetting).

```bash
M=/Users/seanjohnson/Desktop/ReEngrave
for arm in armA:ft-scoreaug-armA armB:ft-clean-armB; do
  tag=${arm%%:*}; run=${arm##*:}
  PYTHONPATH=. python3 -m tools.omr.training.wtc_forgetting_eval \
    --prod $W/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
    --ft   $W/scoreaug-fair-test/$run-best.pt \
    --cells-dir $M/benchmarks/omr-phase2.5/cells \
    --detections-dir benchmarks/omr-phase3.4/detections-yolo-realft \
    --verdicts-dir   benchmarks/omr-phase3.4/verdicts-yolo-realft-ported \
    --prefix wtc --imgsz 1280 --conf 0.25 --match center --device cpu \
    --json-out benchmarks/scoreaug-fair-test/wtc_$tag.json
done
```

## 6. Verdict

- **A > B on dense recall AND both WTC deltas ≈ 0** → augmentation helps beyond
  plain fine-tuning. Promote Arm A's `best.pt` as a candidate (do NOT overwrite
  production until a wider check).
- **A ≈ B on dense recall** → augmentation adds nothing over plain fine-tuning
  (the degradation isn't the active ingredient).
- **Either arm drops WTC recall materially** → forgetting; the fine-tune recipe
  is too hot / needs the freeze variant before any promotion.

Commit the eval JSON/txt + a short `RESULTS.md` to
`benchmarks/scoreaug-fair-test/`. Update memory `project_domain_augmentation`.

## Cost / time

Provision ~20 min · datasets ~25 min · 2 fine-tunes ~75 min · ship back ~10 min
→ **~2–2.5 h, ~$1–2.** Eval is local (free, ~15 min on CPU).
