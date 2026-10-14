"""2.4b BN-frozen fine-tune: train_yolo's arguments, but every BatchNorm layer is held in eval mode with momentum 0 for the whole run,
so running_mean/var cannot drift (the 2.4b re-assembly diff: conv weights moved <2%, BN statistics 3-23%). Batch statistics are not used either."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
ap = argparse.ArgumentParser()
for k in ("data", "weights", "project", "name", "device", "extra-kwargs"): ap.add_argument("--" + k)
for k in ("epochs", "imgsz", "batch", "workers", "patience"): ap.add_argument("--" + k, type=int)
for k in ("fliplr", "flipud", "hsv_h", "hsv_s"): ap.add_argument("--" + k, type=float)
a = ap.parse_args()
import torch.nn as nn
from ultralytics import YOLO
def freeze_bn(trainer):
    n = 0
    for m in trainer.model.modules():
        if isinstance(m, nn.modules.batchnorm._BatchNorm):
            m.eval(); m.momentum = 0.0; n += 1
    if not getattr(trainer, "_bn_msg", False): print(f"[bn-frozen] {n} BatchNorm layers in eval mode, momentum 0", flush=True); trainer._bn_msg = True
model = YOLO(a.weights)
for ev in ("on_train_start", "on_train_epoch_start", "on_train_batch_start"): model.add_callback(ev, freeze_bn)
kw = dict(data=a.data, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, device=a.device, patience=a.patience, project=a.project, name=a.name,
          workers=a.workers, fliplr=a.fliplr, flipud=a.flipud, hsv_h=a.hsv_h, hsv_s=a.hsv_s)
kw.update(json.loads(a.extra_kwargs or "{}"))
model.train(**kw)
