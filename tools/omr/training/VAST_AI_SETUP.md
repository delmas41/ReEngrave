# Vast.ai setup guide — train YOLOv8 on DeepScoresV2

Estimated cost: **~$8–15 round-trip** (1 round of training, including dataset download + a small buffer for restarts).
Estimated wall time: **~12–16 hours** for 50 epochs at imgsz=1280, batch=16 on an RTX 3090. (~6–10h on an A100, ~16–24h on a 4090 if it's all you can get.)

## 1. Create an account & add credit

1. Go to **https://vast.ai**, sign up.
2. Verify email.
3. Go to **Billing** → add **$25** to your account (one safe round-trip + buffer).
4. (Optional but recommended) Enable **2-factor auth**.

## 2. Pick an instance

In the **Search Console** (left nav):

- **GPU**: `RTX 3090` (cheapest viable). `RTX 4090` and `A100` work too if available.
- **Disk space**: `≥ 50 GB` — dataset is ~12 GB extracted plus run artifacts. Don't skimp; running out mid-training is the most common failure.
- **Internet**: `> 100 Mbps download` — dataset is ~6.5 GB compressed.
- **Reliability**: `> 95%` (sort by this column descending). Spot instances can be interrupted, but the ones with high reliability scores rarely get pre-empted in a 16-hour window.
- **Sort by**: `$/hr` ascending.
- **Image**: Click "Edit" next to "Image" and choose **`pytorch/pytorch:2.4.0-cuda12.4-cudnn9-devel`** (or any PyTorch 2.x + CUDA 12.x image). The image must include `pip` and `git`.

Look for an instance around **$0.20–0.50/hr** for an RTX 3090. Click **Rent**.

## 3. Wait for it to start, then connect

Vast.ai's "Instances" tab shows status. When it transitions from `creating` → `running`, copy the SSH connection string. It looks like:

```
ssh -p <port> root@<host>.vast.ai -L 8080:localhost:8080
```

The `-L 8080:localhost:8080` is for tunneling Vast.ai's Jupyter (you can skip this if you prefer pure terminal).

Open a terminal on your Mac and run that command. Accept the host key.

## 4. Bootstrap the environment

Inside the SSH session:

```bash
# Verify GPU is visible
nvidia-smi

# Create a working directory
mkdir -p /workspace/reengrave-training
cd /workspace/reengrave-training

# Clone or scp the training scripts. Easiest: scp from your Mac in a NEW terminal:
#   (run this on your Mac, NOT in the SSH session)
#   scp -P <port> -r ~/Desktop/ReEngrave/.claude/worktrees/cool-kare-05197c/tools/omr/training root@<host>.vast.ai:/workspace/reengrave-training/

# OR: clone your repo if you've pushed it
# git clone <your-repo-url> .

# Install Python deps
pip install -r training/requirements-training.txt

# Verify ultralytics works
python -c "from ultralytics import YOLO; print('ultralytics ok')"
```

## 5. Download the dataset (~30 min on a 100 Mbps link)

```bash
cd /workspace/reengrave-training
python -m training.download_dataset --out data/deepscoresv2/
```

This pulls ~6.5 GB from Zenodo. If it stalls, re-run — the script is idempotent.

Verify:

```bash
ls -lh data/deepscoresv2/
# Expect: a few large .zip / .tar.gz files + an extracted images/ + annotations/ subdir
```

## 6. Convert annotations to YOLO format (~5 min)

```bash
python -m training.prepare_yolo_data \
  --src data/deepscoresv2/ \
  --dst data/deepscoresv2-yolo/
```

Verify:

```bash
ls data/deepscoresv2-yolo/
# Expect: data.yaml, images/, labels/
head data/deepscoresv2-yolo/data.yaml
# Should show ~146 class names
```

## 7. Smoke test (1 epoch, ~2 min) — make sure the env works

```bash
python -m training.train_yolo \
  --data data/deepscoresv2-yolo/data.yaml \
  --imgsz 1280 \
  --device 0 \
  --smoke
```

If this succeeds, you'll see `runs/detect/train/weights/best.pt`. **Stop and verify before committing to the full run.**

## 8. The actual training run (12–16 hours)

```bash
# Use tmux so it survives if your SSH disconnects
tmux new -s train

# Inside tmux:
python -m training.train_yolo \
  --data data/deepscoresv2-yolo/data.yaml \
  --epochs 50 \
  --imgsz 1280 \
  --batch 16 \
  --device 0 \
  --patience 10

# Detach with: Ctrl-b, then d
# Re-attach later with: tmux attach -t train
```

Monitor from another terminal (also SSH'd in):

```bash
# Latest metrics
tail -f /workspace/reengrave-training/runs/detect/train/results.csv

# GPU usage
watch -n 5 nvidia-smi
```

Expected timeline:
- **Epoch 1**: ~25 min (initial loads + caching)
- **Epochs 2–50**: ~15–18 min each
- **Total**: ~12–16h
- **Early-stop**: with `--patience 10`, it'll stop if val mAP doesn't improve for 10 consecutive epochs (typically saves you ~2–4h)

## 9. Evaluate on your real cells

After training completes:

```bash
python -m training.eval_on_score_cells \
  --weights runs/detect/train/weights/best.pt \
  --cells benchmarks/omr-phase2.5/cells.json
```

This runs the freshly-trained YOLO on the WTC + Beethoven cells and reports:
- DeepScoresV2 val mAP@0.5 (intrinsic measure)
- Detection counts on each WTC/Beethoven cell (sanity check that the model finds music symbols, not "birds" and "apples" like the COCO baseline)

## 10. Bring the weights home

From your Mac (not the Vast.ai instance), in a new terminal:

```bash
scp -P <port> root@<host>.vast.ai:/workspace/reengrave-training/runs/detect/train/weights/best.pt \
    ~/Desktop/ReEngrave/.claude/worktrees/cool-kare-05197c/tools/omr/training/data/weights/deepscoresv2-yolov8m-50ep.pt
```

The `best.pt` is typically ~50 MB. Save it locally and you can stop the Vast.ai instance.

## 11. Destroy the instance

In Vast.ai's web console: **Instances** tab → your instance → **Destroy**. The disk is wiped; you stop being billed.

(If you forget this, you keep paying $0.20–0.50/hour forever. Set a calendar reminder.)

## 12. Run inference locally

Back on your Mac:

```bash
cd ~/Desktop/ReEngrave/.claude/worktrees/cool-kare-05197c

python -m tools.omr.annotate.run_yolo \
  --weights tools/omr/training/data/weights/deepscoresv2-yolov8m-50ep.pt \
  --cells benchmarks/omr-phase2.5/cells.json \
  --out benchmarks/omr-phase3.1/
```

Then run the scorer on the resulting detections to compare against the template matcher:

```bash
python -m tools.omr.annotate.score \
  --verdicts-dir benchmarks/omr-phase2.5/verdicts \
  --detections-dir benchmarks/omr-phase3.1/detections-yolo/ \
  --out-dir benchmarks/omr-phase3.1/results-yolo/
```

Open `benchmarks/omr-phase3.1/results-yolo/report.md` for the side-by-side P/R numbers.

---

## Cost-saving tips

1. **Don't pre-pay** more than the round-trip cost. Vast.ai credit is non-refundable.
2. **Use spot/interruptible** instances if reliability is >95% — usually 30-50% cheaper.
3. **Smoke-test before the full run.** If the env breaks on epoch 1, you eat ~$1 of wasted time; if it breaks on epoch 30, you eat $5–10.
4. **Set early-stop patience** to 10. Usually saves 2–4 hours.
5. **Monitor `nvidia-smi`** — if GPU utilization is below 60%, batch size or imgsz can probably go up.

## Common failures & recoveries

| Symptom | Cause | Fix |
|---|---|---|
| "CUDA out of memory" | batch too large for the GPU's VRAM | reduce `--batch` to 8 or 4 |
| Dataset download stalls mid-way | flaky Zenodo connection | re-run download script (idempotent) |
| Training stops at epoch ~30 with patience-exit | val mAP plateaued | this is FINE — keep `best.pt` |
| SSH disconnects, training stops | not using tmux | always use tmux; re-attach with `tmux attach` |
| weights file is huge (>500 MB) | accidentally grabbed `last.pt` not `best.pt` | use `best.pt` |
| mAP after 50 epochs is <0.30 | wrong dataset/config | check data.yaml class count = 146 |

## What to do AFTER you have weights

Once `best.pt` is on your Mac:

1. Run `eval_on_score_cells` and check that the model finds noteheads on WTC cells (not 0 detections like COCO weights).
2. Compare side-by-side against the template matcher via the existing scorer on the same verdict cells.
3. **Decide based on measured numbers** whether to (a) use YOLO as a second voting engine alongside the template matcher, (b) replace the template matcher entirely, or (c) keep training (more epochs, larger model, fine-tune from this baseline on hand-annotated user corrections).

The plan calls for option (a) — multi-engine voting — but measure first.
