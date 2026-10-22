"""ROADMAP 2.196 Q3. Tensor-level provenance of the accidental class rows in production. Read-only.
For model.22.cv3.{0,1,2}.2 (the 1x1 class conv), per accidental/key row and for contrast the 7 notehead rows the graft KEPT from the fine-tune:
exact equality prod vs {hollow-ft-2026-09-03, d25 epoch0 (the donor fine-tune), dsv2base}, and the max |delta| of the row vs dsv2base relative to the row's own max |w|.
Control that can fail: the kept notehead rows must equal d25 (and differ from dsv2base by a LARGE delta); if the accidental rows moved as much, the fine-tune taught them."""
import json, torch
W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
def sd(f):
    ck = torch.load(W + f, map_location="cpu", weights_only=False); m = ck.get("ema") or ck["model"]
    return {k: v.float() for k, v in m.state_dict().items()}
S = {"prod": sd("deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"), "hollowft": sd("deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"),
     "d25": sd("round5-sweep/distill25/epoch0.pt"), "base": sd("deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")}
names = json.load(open("/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/deepscoresv2_208_classes.json"))
L = ["model.22.cv3.0.2", "model.22.cv3.1.2", "model.22.cv3.2.2"]
kept = [n for n in ("noteheadHalfOnLine", "noteheadHalfInSpace", "noteheadWholeOnLine", "noteheadWholeInSpace", "noteheadHalfOnLineSmall", "noteheadHalfInSpaceSmall", "noteheadWhole")]
rows = [(n, i) for i, n in enumerate(names) if n in kept] + [(f"{n}[{i}]", i) for i, n in enumerate(names) if i in (59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 170, 171, 172, 173, 174)]
eq = lambda a, b, r: all(torch.equal(S[a][l + ".weight"][r], S[b][l + ".weight"][r]) and torch.equal(S[a][l + ".bias"][r], S[b][l + ".bias"][r]) for l in L)
print("%-28s %-9s %-9s %-9s | %-12s %-12s %-12s" % ("row", "prod=hFT", "prod=d25", "prod=base", "max|prod-base|", "max|d25-base|", "max|w| base"))
out = []
for n, r in rows:
    dpb = max((S["prod"][l + ".weight"][r] - S["base"][l + ".weight"][r]).abs().max().item() for l in L)
    ddb = max((S["d25"][l + ".weight"][r] - S["base"][l + ".weight"][r]).abs().max().item() for l in L)
    mw = max(S["base"][l + ".weight"][r].abs().max().item() for l in L)
    print("%-28s %-9s %-9s %-9s | %-12.2e %-12.2e %-12.2e" % (n, eq("prod", "hollowft", r), eq("prod", "d25", r), eq("prod", "base", r), dpb, ddb, mw))
# all other tensors: where does prod come from
ks = list(S["prod"]); same = lambda a: sum(torch.equal(S["prod"][k], S[a][k]) for k in ks)
print("tensors", len(ks), "prod==d25:", same("d25"), "prod==hollowft:", same("hollowft"), "prod==base:", same("base"))
ks2 = [k for k in ks if "model.22.cv3" not in k and ("running" not in k) and ("num_batches" not in k)]
print("non-head weight tensors (no BN buffers):", len(ks2), "prod==d25:", sum(torch.equal(S["prod"][k], S["d25"][k]) for k in ks2), "prod==hollowft:", sum(torch.equal(S["prod"][k], S["hollowft"][k]) for k in ks2), "prod==base:", sum(torch.equal(S["prod"][k], S["base"][k]) for k in ks2))
