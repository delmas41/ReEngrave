"""Which heads flip under a 2 px box shift with the ink-edge jut, and what the jut test saw there."""
from __future__ import annotations
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J
from tools.omr.annotate import ledger_grid as lg

if __name__ == "__main__":
    L, fp, far = J.prepare("beethoven5-litolff", 3)
    base = J.run(L, fp, far, "ink")
    for dx, dy in ((0, -2), (-2, -2), (2, 2), (2, -2), (-2, 2)):
        sh = J.run(L, fp, far, "ink", dx, dy)
        print("shift", dx, dy, J.tal(sh))
        for s in base:
            if base[s][1] != sh[s][1]:
                print("   ", s, "base", base[s][:2], "shifted", sh[s][:2], "|", sh[s][2][:70])
