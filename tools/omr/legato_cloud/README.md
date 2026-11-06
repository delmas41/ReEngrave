# LEGATO on a cloud GPU — orchestral second opinion

oemer can't read conductor scores (it hard-asserts a 2-staff grand staff).
**LEGATO** is a full-page vision model that emits ABC notation and handles
orchestral pages, but it needs a ~20 GB model and a CUDA GPU (or Apple MPS).
This is the cloud-GPU path: run LEGATO on a rented GPU to get ABC, then diff
locally on your Mac with the CPU-only bridge.

Split of work:
- **GPU box** (rented, ~$0.30–0.80/hr): page image → ABC JSON. That's all.
- **Your Mac** (local, free): ABC JSON + pipeline `.omr.json` → clef/time-sig
  reconciliation report via `tools/omr/oemer_second_opinion.py`.

## 1. Prep locally (on your Mac)

Render the page image and produce the pipeline `.omr.json` you'll diff against.
Worked example = Mahler 5, PDF page index 11 (printed p.13):

```bash
cd /Users/seanjohnson/Desktop/ReEngrave    # main checkout (has the YOLO weights)

# Render the page LEGATO will read:
python3 -c "from tools.omr.oemer_second_opinion import render_pdf_page as r; \
  r('/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores/Mahler_5_.pdf', 11, 'mahler-p13.png', dpi=200)"

# Pipeline read of that page (skip if you already have an .omr.json for it):
python3 -m tools.omr.transcribe \
  '/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores/Mahler_5_.pdf' \
  --pages 11 --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
  --dpi 300 --out mahler-p13.omr.json
```

## 2. Rent a GPU

vast.ai or RunPod, a 24 GB card (RTX 3090/4090) is ample; fp16 needs ~14 GB.
Prefer a `pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime` image (torch preinstalled).
See `tools/omr/training/VAST_AI_SETUP.md` — same flow you used for training.

## 3. Upload + run (on the GPU box)

Copy `mahler-p13.png` and `run_on_gpu.sh` up (scp, or the provider's file UI), then:

```bash
bash run_on_gpu.sh mahler-p13.png
# -> writes  out/mahler-p13_guangyangmusic_legato_abc.json
```

First run downloads ~20 GB of weights (a few minutes). Then destroy the box.

## 4. Bring it back + diff (on your Mac)

Download the `*_abc.json` next to your `.omr.json`, then:

```bash
python3 -m tools.omr.oemer_second_opinion --engine legato \
  --omr-json mahler-p13.omr.json --page 0 \
  --legato-abc mahler-p13_guangyangmusic_legato_abc.json
```

`--legato-abc` accepts LEGATO's predictions JSON directly (no manual extract).
The report flags where the pipeline and LEGATO disagree on clef / time
signature — the measures worth a human look. On the Mahler page the pipeline
read all-treble with the meter abstained, so expect LEGATO to supply the meter
and the bass/alto clefs the pipeline missed.

## Notes

- `LEGATO_MODEL=guangyangmusic/legato-small bash run_on_gpu.sh ...` uses the
  smaller model (less VRAM, lower accuracy) for a cheaper smoke test.
- Batch multiple pages: `bash run_on_gpu.sh p1.png p2.png p3.png`.
- The diff step is CPU-only and needs no GPU — keep the rented box only for
  step 3.
