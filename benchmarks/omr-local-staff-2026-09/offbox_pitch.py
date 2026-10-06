"""lane-offbox-check: the ledger pitch (spaces between consecutive measured ledger rows, and staff edge -> first rung)
per document, from the replayed rungs of RUN 2 -- used as the starting pitch for the interpolation in `Rows`.
Only gaps in [0.8, 1.8] sp count (a bigger gap hides a missed ledger).

  python3 offbox_pitch.py
"""
import json, sys
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_check as C

res = json.loads(Path("/private/tmp/claude-501/ex/offbox.json").read_text())
for doc in res:
    M = json.loads(Path(f"/private/tmp/claude-501/ex/m_RUN2_{doc}.json").read_text())["heads"]
    H = res[doc]["heads"]["RUN2"]
    first, between = [], []
    for s, m in M.items():
        if not m.get("repro") or s not in H:
            continue
        lines = H[s]["lines"]
        top, bot = min(lines), max(lines)
        sp = (bot - top) / 4.0
        for side, edge in ((-1, top), (1, bot)):
            ys = sorted(side * (y - edge) / sp for y in m["rungs"] if side * (y - edge) > 0.4 * sp)
            prev = 0.0
            for i, d in enumerate(ys):
                g = d - prev
                if 0.8 <= g <= 1.8:
                    (first if i == 0 else between).append(g)
                prev = d
    print(doc, "first-rung gap median %.3f (n=%d, p10 %.2f p90 %.2f)" % (np.median(first), len(first), np.percentile(first, 10), np.percentile(first, 90)),
          "| rung-to-rung median %.3f (n=%d, p10 %.2f p90 %.2f)" % (np.median(between), len(between), np.percentile(between, 10), np.percentile(between, 90)))
