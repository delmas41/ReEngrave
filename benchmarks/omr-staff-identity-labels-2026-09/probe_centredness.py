#!/usr/bin/env python3
"""Is a margin block centred ON a staff, or BETWEEN two of them?

The Phase 2 (ii) discriminator, measured in the only unit that means one thing
everywhere: the LOCAL gap between the two ticks the block sits between.

    centredness = |(y - t_i) - (t_i+1 - y)| / (t_i+1 - t_i)

0.0 is exactly midway between two staves — where an engraver puts a name that
serves a braced pair. 1.0 is exactly on a tick — where an ordinary label sits.
The mean-spacing version of this number is NOT usable: an engraver opens the
gap between families, so Brahms 1's wind/brass boundary is half again the
within-family gap and the same printed position scores differently there.

⚠️ Read the two populations, not the threshold. A rule shipped on this needs a
gap with nothing in it, and this prints the sorted list so the gap can be seen
rather than asserted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                       # noqa: E402


def centredness(y: float, ticks: list[float]):
    """-> (score, i, j) for the tick pair the block lies between, or None."""
    for i in range(len(ticks) - 1):
        lo, hi = ticks[i], ticks[i + 1]
        if lo <= y <= hi:
            gap = hi - lo
            if gap <= 0:
                return None
            return abs((y - lo) - (hi - y)) / gap, i, i + 1
    return None


def main() -> int:
    d = json.loads((HERE / "blocks.json").read_text())
    rows = []
    for e in d:
        ticks = e.get("tick_ys") or []
        if len(ticks) < 2:
            continue
        for b in e["blocks"]:
            c = centredness(b["y"], ticks)
            if c is None:
                continue                       # outside the tick range entirely
            score, i, j = c
            hit = lookup(b["text"])
            rows.append({
                "row_id": e["row_id"], "system": e["system"],
                "centredness": round(score, 3), "between": (i, j),
                "text": b["text"],
                "resolves": (hit.instrument.name if hit and hit.instrument
                             else None),
            })
    rows.sort(key=lambda r: r["centredness"])
    print(f"{len(rows)} blocks lying between two ticks\n")
    print("--- most CENTRED-BETWEEN (candidate shared labels) ---")
    prev = None
    for r in rows[:26]:
        mark = ""
        if prev is not None and r["centredness"] - prev > 0.05:
            mark = "   <-- gap %.3f" % (r["centredness"] - prev)
        print(f"  c={r['centredness']:6.3f} {r['row_id'][:30]:30} s{r['system']} "
              f"{str(r['between']):8} {r['resolves'] or '-':14} "
              f"{r['text'][:40]!r}{mark}")
        prev = r["centredness"]
    print()
    for cut in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40):
        n = sum(1 for r in rows if r["centredness"] <= cut)
        named = sum(1 for r in rows
                    if r["centredness"] <= cut and r["resolves"])
        print(f"  cut {cut:.2f}: {n:>3} blocks shared, {named:>3} of them "
              f"name an instrument")
    (HERE / "centredness.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
