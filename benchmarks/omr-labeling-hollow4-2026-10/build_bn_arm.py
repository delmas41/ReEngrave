"""2.4b re-assembly arm C (diagnostic, found by the tensor diff): arm B (fine-tune + production's non-hollow class rows) AND the
BatchNorm RUNNING STATISTICS (running_mean/var, num_batches_tracked) put back to production's. The 1-epoch fine-tune moved conv
weights <2% but the BN statistics 3-23% (the training mix's activation statistics) -- the cheapest 'features' suspect.
  build_bn_arm.py --armB in.pt --out out.pt"""
import argparse, torch
ap = argparse.ArgumentParser(); ap.add_argument("--armB"); ap.add_argument("--out"); a = ap.parse_args()
PROD = "omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
P = torch.load(PROD, map_location="cpu", weights_only=False)["model"].state_dict()
ck = torch.load(a.armB, map_location="cpu", weights_only=False); sd = ck["model"].state_dict()
n = 0
for k in sd:
    if k.endswith(("running_mean", "running_var", "num_batches_tracked")):
        sd[k] = P[k].clone(); n += 1
ck["model"].load_state_dict(sd); torch.save(ck, a.out)
chg = [k for k in sd if k in P and not torch.equal(sd[k], P[k])]
print(f"restored {n} BN buffers; tensors still differing from production: {len(chg)} (conv weights + hollow rows + cv2 etc.)")
