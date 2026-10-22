"""ROADMAP 2.196. Build diagnostic weight files in memory-then-disk (NOT for production): prod with the accidental/key class rows replaced from another checkpoint.
Only the six cv3.*.{weight,bias} entries of the listed rows are touched; everything else is prod's, bit for bit (self-check printed).
usage: make_variants.py OUTDIR"""
import pathlib, sys, torch
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
W = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/omr-weights")
PROD = W / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
ROWS = [59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 170, 171, 172, 173, 174]
NAT = [61, 62, 68, 171]
L = ["model.22.cv3.0.2", "model.22.cv3.1.2", "model.22.cv3.2.2"]


def make(donor_path, rows, name):
    ck = torch.load(PROD, map_location="cpu", weights_only=False)
    don = torch.load(donor_path, map_location="cpu", weights_only=False)
    m = (ck.get("ema") or ck["model"]); dm = (don.get("ema") or don["model"])
    sd, dsd = m.state_dict(), dm.state_dict()
    changed = 0
    for l in L:
        for t in ("weight", "bias"):
            for r in rows:
                sd[f"{l}.{t}"][r] = dsd[f"{l}.{t}"][r].to(sd[f"{l}.{t}"].dtype)
                changed += 1
    m.load_state_dict(sd)
    ck["model"] = m; ck["ema"] = None
    p = OUT / name
    torch.save(ck, p)
    # self-check: everything outside the listed rows equals prod
    chk = torch.load(p, map_location="cpu", weights_only=False)["model"].state_dict()
    base = torch.load(PROD, map_location="cpu", weights_only=False)
    base = (base.get("ema") or base["model"]).state_dict()
    diff = [k for k in base if not torch.equal(base[k], chk[k])]
    print(name, "tensors differing from prod:", diff, "rows", rows)
    return p


make(W / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt", ROWS, "prod_with_dsv2base_accidental_rows.pt")
make(W / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt", NAT, "prod_with_dsv2base_natural_rows.pt")
