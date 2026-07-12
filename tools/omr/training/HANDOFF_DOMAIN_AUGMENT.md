# Handoff — Domain-Augmentation Retrain (ScoreAug + Augraphy → yolov8l)

**Goal:** close the synthetic→real orchestral detection gap *at the source* by
domain-augmenting the DSv2 training set (real-scan paper texture / bleed /
low-toner) and retraining yolov8l **from COCO**. Designed to ride the **same
GPU box you're running LEGATO on** — LEGATO gives the contextual clef/meter
second opinion, this gives a stronger detector; we measure both head-to-head.

Driven by the **other (GPU) session**. Everything below is copy-paste.

---

## 0. Guardrails — do NOT wander into these

- **Hand-label fine-tuning is proven-worse** — fine-tuning the production
  checkpoint on the hand-labeled cells *lowered* WTC F1 97.8% → 90.5% even with
  the correct replay recipe. We are **not** doing that. Training data = DSv2.
- **Catalog training is dead** — the Phase A–L catalog experiment always
  collapsed. Don't retry it.
- **Keep nc=208.** Do not add the 6 custom classes (that's the 214 head-reset
  that cratered F1 to 79.3%). Train from the COCO **alias** so a fresh 208-class
  head is built — see the gotcha in §5.
- **Recipe = ScoreAug blank-composite + show-through + Augraphy (6 effects, NO
  BadPhotoCopy).** Already baked in (`AUGRAPHY_SAFE_EFFECTS`). BadPhotoCopy is
  numba-unstable on numba 0.60 / numpy 2.0 (crashes mid-batch on some sizes).

## What's already done (host session, no GPU)

- Recipe decided + committed: `augment_scoreaug.py` — BadPhotoCopy dropped from
  the default safe-list (its builder case is kept for later re-enable).
- Wiring built + committed: **`build_scoreaug_dataset.py`** (turns a prepared
  YOLO dataset into an augmented one with a trainable `data.yaml`; augments
  **train only**, keeps **val clean**).
- **Phase-1 dry-run PASSED locally** (CPU): stand-in nc=208 dataset → augment
  (augraphy ON, 6 effects, 51 real TISMIR blanks) → `train_yolo.py` from
  `yolov8l.pt` alias → **208-class head built**, degraded images + clean val
  trained 1 epoch, no crash. `test_augment_scoreaug.py`: 16/16 pass.
- Offline visual preview confirmed labels stay pixel-aligned, ink survives
  (0 / 2.6M ink px lightened), texture is realistic.

---

## 1. Code onto the box

```bash
git fetch && git checkout claude/training-domain-augmentation-a29baf
# recipe + build_scoreaug_dataset.py + this doc all live on this branch
```

## 2. Env (add to the LEGATO box — CUDA 12.4 already there)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
pip install ultralytics augraphy            # augraphy pulls numba/scikit — fine on Linux
# pyyaml comes with ultralytics; build_scoreaug_dataset needs it
```

## 3. TISMIR blank pages (~186 MB, sha-verified, idempotent)

```bash
python3 -m tools.omr.training.augment_scoreaug --download-blanks \
    --blanks-dir tools/omr/training/data/blanks
# -> 51 real scanned blank IMSLP pages under data/blanks/{seamed,seamless}/
```

## 4. DSv2 download + prepare (clean set)

```bash
# dense (~6.5 GB) — recommended first pass
python3 tools/omr/training/download_dataset.py --out data/deepscoresv2
python3 tools/omr/training/prepare_yolo_data.py \
    --src data/deepscoresv2 --dst data/deepscoresv2-yolo
# -> data/deepscoresv2-yolo/{images,labels}/{train,val} + data.yaml (nc=208)
#    (--full for the ~80 GB complete set: merge_shards.py first — see HANDOFF_PREMIUM_TRAINING.md)
```

## 5. Domain-augment the TRAIN split  ← the new step

```bash
python3 -m tools.omr.training.build_scoreaug_dataset \
    --prepared data/deepscoresv2-yolo \
    --out      data/deepscoresv2-yolo-scoreaug \
    --blanks-dir tools/omr/training/data/blanks \
    --fraction 0.5 --augs-per-image 1 --seed 41 --require-augraphy
# -> data/deepscoresv2-yolo-scoreaug/data.yaml
#    train = originals + degraded twins (+50% imgs);  val = the ORIGINAL clean val
```

Then **train from COCO `yolov8l.pt`**:

```bash
# smoke first (catches env issues in ~1 min):
python3 -m tools.omr.training.train_yolo --smoke --device 0

python3 -m tools.omr.training.train_yolo \
    --data data/deepscoresv2-yolo-scoreaug/data.yaml \
    --weights yolov8l.pt \
    --epochs 50 --imgsz 1280 --batch 16 --device 0 --patience 15 \
    --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 --hsv_v 0.4 --mosaic 1.0 --degrees 2 \
    --name ds2-yolov8l-scoreaug \
    --extra-kwargs '{"cls": 1.0, "lr0": 0.01, "warmup_epochs": 5}'
# run the full train in tmux. A100/full: --batch 8 --epochs 100 (see HANDOFF_PREMIUM_TRAINING.md)
```

> ⚠️ **GOTCHA (verified in the dry-run): `--weights` must be the ALIAS
> `yolov8l.pt`, NOT a path to a downloaded file.** `train_yolo.py` skips its
> nc-consistency guard only for download aliases; a *path* to an existing COCO
> `.pt` (80 classes) vs data nc=208 hard-fails the guard. The alias downloads
> COCO and lets ultralytics build a fresh 208-class head — exactly what we want.

> ⚠️ **Keep the music-safe aug flags** (`--fliplr 0 --flipud 0 --hsv_h 0
> --hsv_s 0 --degrees 2`). Ultralytics' *defaults* would horizontally flip and
> HSV-jitter the score (meaningless/harmful for notation). These layer on top
> of the ScoreAug photometric degradation, which handles the paper-domain part.

## 6. LEGATO second opinion — the clef/time-sig session's turn-key handoff

The clef/time-sig session (branch `claude/clef-time-signature-weights-6d6e38`)
staged a **self-contained** LEGATO run at `/Users/seanjohnson/Desktop/legato-handoff/`
(`run_on_gpu.sh` + `mahler-p13.png` = Mahler 5 printed p.13). LEGATO reads the
full page and emits **clef + time-sig in the ABC header** = the contextual
signal our detector misses.

**Run it FIRST, before the long training** (so its ~14 GB VRAM is free), and it
won't touch the training env — `run_on_gpu.sh` builds its **own** venv
(torch 2.6.0) and pulls ~20 GB weights to `~/.cache/huggingface`:

```bash
# upload legato-handoff/run_on_gpu.sh + mahler-p13.png to the box, then:
bash run_on_gpu.sh mahler-p13.png
# -> out/mahler-p13_guangyangmusic_legato_abc.json
#    download that back to /Users/seanjohnson/Desktop/legato-handoff/ on the Mac
```

The clef/time-sig session then diffs it **locally (CPU, no GPU)** against the
pipeline's `mahler-p13.omr.json`:

```bash
python3 -m tools.omr.oemer_second_opinion --engine legato \
    --omr-json mahler-p13.omr.json --page 0 \
    --legato-abc mahler-p13_guangyangmusic_legato_abc.json
```

That LEGATO ABC is the second-opinion baseline for §7's head-to-head. *(Use
LEGATO as second-opinion / eval only — NOT as training labels; that would trip
the hand-label guardrail.)*

**Running both on one box:** LEGATO and the training use **separate venvs**
(torch 2.6.0 vs cu124) so they don't collide; run LEGATO **first** (minutes,
frees its VRAM), then train. Size the box for **both**: disk **≥60 GB**
(~20 GB LEGATO weights + dense DSv2 ~6.5 GB + prepared/augmented + two torch
installs), and a **24 GB card** (RTX 3090) covers each phase since they run
sequentially.

## 7. Evaluate — regression guard + domain-gap win

```bash
# a) REGRESSION GUARD — must hold ≈ F1 98.8% on the 25-cell Bach WTC verdict set
#    (clean printed music). Score the new best.pt over benchmarks/omr-phase2.5/verdicts/
#    via tools/omr/annotate/score.py (see tools/omr/README.md weights table).

# b) DOMAIN-GAP WIN — recall on held-out REAL orchestral scans.
#    The user-labeled cells (data/user-labeled/v1..v4, real scans, NOT in DSv2)
#    are the natural real-domain val set. Build a val-only nc=208 data.yaml from
#    them and run model.val() -> per-class recall, watching clefG/clefF/clefC*,
#    timeSig*, and the small dynamics/grace notes.

python3 tools/omr/training/eval_on_score_cells.py \
    --weights <run>/weights/best.pt --data data/deepscoresv2-yolo-scoreaug/data.yaml
```

**Success = WTC F1 held ≈98.8% AND orchestral clef/time-sig/small-symbol recall
up vs the current production checkpoint** (`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`).
Then compare against LEGATO's clef/meter reads on the same pages — the best
answer may be an ensemble (LEGATO's header feeding the deterministic layer).

## 8. Ship weights home (only if it wins)

```bash
scp <run>/weights/best.pt \
    <home>/tools/omr/training/data/weights/deepscoresv2-yolov8l-scoreaug-50ep.pt
# Promote to production (transcribe.py DEFAULT_WEIGHTS) ONLY if §7 passed both bars.
```

---

## Cost / time

| Path | GPU | DSv2 | time | cost |
|---|---|---|---|---|
| cheap first pass | RTX 3090 | dense | ~12–16 h | **~$8–15** |
| premium | A100 40GB | full | ~25–35 h | ~$35–50 |

## Defaults chosen this session (override if you want)

- Recipe: ScoreAug blank + show-through + augraphy (6 effects, no BadPhotoCopy)
- `--fraction 0.5 --augs-per-image 1 --seed 41`
- dense DSv2 + 3090 first (cheap hypothesis test); scale to full + A100 only if
  the gap measurably closes.

## Other gotchas

- `build_scoreaug_dataset` keeps **val clean** by pointing `val:` at the original
  prepared val (absolute path). Don't augment val.
- `data/user-labeled/catalog.yaml` has an absolute `path:` to the *main* checkout
  — irrelevant here (we build a fresh `data.yaml`), but if you ever train off the
  catalog, rebuild it (`build_catalog_yaml.py`) so `path:` matches the box.
- Base GPU setup (torch install, tmux, download, scp, destroy instance):
  `VAST_AI_SETUP.md` (3090/dense) and `HANDOFF_PREMIUM_TRAINING.md` (A100/full).
