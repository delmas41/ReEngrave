"""2.115: how the two cut-offs (size gate, minimum shift) were chosen -- the rule re-run over a grid on the same populations as measure_truth.py.
Each cell: moved / hollow->? changes as "b>h" = black-or-between reading becomes hollow, "h>b" = hollow reading lost. usage: sweep.py"""
import sys
sys.path.insert(0, "."); sys.path.insert(0, "benchmarks/omr-head-recentre-2026-10")
import explore as X, measure_truth as M
from tools.omr.staged import gather as G
hs, clean, n = X.heads()
rast = {"brahms": X.raster(X.BRA, 0), "litolff": X.raster(X.LIT, 1)}
print("pop: brahms black/hollow, litolff hollow/other;  cell = moved  nonhollow->hollow  hollow->nonhollow  black->nonblack")
for gate in (0.7, 0.8, 0.9, 1.0, 1.1):
    for shift in (0.10, 0.15, 0.20, 0.30):
        G.RECENTRE_PART_SIZE_GATE = gate; G.RECENTRE_PART_MIN_SHIFT_SPACES = shift
        rows = M.table(hs, rast, "x")
        cells = []
        for pg, lab in (("brahms", "black"), ("brahms", "hollow"), ("litolff", "hollow"), ("litolff", "other")):
            v = [r for r in rows if r["page"] == pg and r["label"] == lab]
            mv = sum(r["moved"] for r in v)
            up = sum(1 for r in v if M.state(r["before"]) != "hollow" and M.state(r["after"]) == "hollow")
            dn = sum(1 for r in v if M.state(r["before"]) == "hollow" and M.state(r["after"]) != "hollow")
            bk = sum(1 for r in v if M.state(r["before"]) == "black" and M.state(r["after"]) != "black")
            cells.append(f"{mv:3d} {up:2d} {dn:2d} {bk:2d}")
        print(f"gate {gate:.1f} shift {shift:.2f} | " + " | ".join(cells))
