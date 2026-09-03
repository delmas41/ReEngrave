# Cloud imgsz-2048 hollow re-ship — runbook (2026-09-03)

The "do it properly" version of the 2026-09-03 hollow ship: fine-tune the
detector at the **native imgsz 2048** on a CUDA GPU (infeasible on the M1 Max —
9 h/epoch there is an MPS assigner-fallback artifact, not a real cost), on the
Phase-1 + Phase-2 hollow mix, and compare against current production.

**What ships vs. what beats it.** Fine-tune FROM the pre-hollow 2048 base
`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (the clean native-scale base the
896 ship only approximated). The number to beat is CURRENT production
`deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt` (the 896 ship) on the re-gate
axes below.

## The package (`reengrave-cloud.tgz`, ~166 MB)
```
tools/omr/training/{train_yolo,build_catalog_yaml,verdicts_to_yolo_labels}.py
                   deepscoresv2_208_classes.json          # nc=208 names (no torch needed to build the catalog)
data/user-labeled/v{1,2,3,4,7,8,9,10,11,12}-*             # dense base + Phase-1 + Phase-2 hollow (images+labels)
weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt         # base to fine-tune FROM
run_cloud_training.sh   oversample_dense.py   requirements-cloud.txt
```

## 1. Rent (vast.ai)
- **GPU**: ≥ 24 GB VRAM for imgsz-2048 (RTX 4090 24 GB works at batch 2–4;
  A6000/A100 40–80 GB at batch 4–8 and faster). Sort $/hr ascending, reliability
  > 95 %.
- **Disk**: ≥ 30 GB. **Image**: a `pytorch/pytorch:2.x-cuda12.x` devel image
  (needs `pip`; CUDA torch preinstalled).
- Verify hourly price before renting (budget: $59 credits; a few-epoch run is
  well under $5).

## 2. Connect + transfer (from the Mac)
```bash
# copy the SSH string from the vast.ai Instances tab once it is 'running':
#   ssh -p <PORT> root@<HOST>.vast.ai
scp -P <PORT> reengrave-cloud.tgz root@<HOST>.vast.ai:/workspace/
ssh -p <PORT> root@<HOST>.vast.ai
```
(If scp/ssh is refused, the account's SSH *public* key is not on the box — add
it in vast.ai → Account → SSH Keys, then re-create/refresh the instance.)

## 3. Bootstrap + train (on the box, inside tmux)
```bash
cd /workspace && tar xzf reengrave-cloud.tgz && cd reengrave-cloud
pip install -r requirements-cloud.txt
nvidia-smi                      # confirm the GPU + VRAM
tmux new -s train
# PRIMARY (ship candidate): v1-4 + v7,v8 + v9,v10,v11  — NO Tchaikovsky
BATCH=4 EPOCHS=10 ./run_cloud_training.sh primary
#   -> per-epoch checkpoints in runs/cloud-2048-primary/weights/epoch{0,1,...}.pt
#   (reduce BATCH to 2 if CUDA OOM; raise on a 40 GB+ card)
# detach: Ctrl-b d   reattach: tmux attach -t train
```
Monitor from a second SSH session: `tail -f runs/cloud-2048-primary/*/results.csv`.

Optionally, after primary, the **ablation** (measures the low-res Tchaikovsky
arm — expected to hurt, per its 0-completion):
```bash
BATCH=4 EPOCHS=10 ./run_cloud_training.sh ablation
```

## 4. Pull checkpoints back (from the Mac) → local re-gate
```bash
scp -P <PORT> 'root@<HOST>.vast.ai:/workspace/reengrave-cloud/runs/cloud-2048-primary/weights/epoch*.pt' \
    ~/Desktop/ReEngrave/omr-weights/cloud-2048/
```
Then LOCALLY, per checkpoint, run the same re-gate the 896 ship used:
- **dense-hold** (must stay ≈ 0.941): `wtc_forgetting_eval.py`
- **hollow-rise** (beet5-p1 scan): `hollow_eval.py` / `gate_all.py`
- **engraved 11-work** (must not materially regress): `orchestral_eval --omr-ned --no-direction-text`
Pick the earliest Pareto-optimal checkpoint (dense holds AND hollow up), exactly
as the ship run picked epoch 1. See GATE_RESULTS.md / SHIP_RESULTS.md for the
harness commands.

## 5. Destroy the instance
vast.ai → Instances → **Destroy** (billing stops; disk wiped). Do this as soon
as the epoch*.pt are safely on the Mac.

## Recipe (baked into run_cloud_training.sh)
- from `imgsz2048-ft-30ep.pt`, imgsz **2048**, `save_period=1`, patience 20,
  music-aug (`fliplr=0 flipud=0 hsv_h=0 hsv_s=0`), **nc=208** (no
  `--allow-nc-expansion` — a head reset is the Phase-3.4 collapse).
- dense base oversampled **3×** → hollow ~29 % of train cells (a clearer
  minority than the 896 ship's 2×/47 %, per next-steps-omr-2026-09-03's "higher
  dense ratio").
