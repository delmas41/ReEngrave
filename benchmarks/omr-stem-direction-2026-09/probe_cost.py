"""WHAT DOES THE TIER COST? One load, the stem pass timed both ways.

⚠️ A CHANGE WORTH TWO VOICE TAGS IN THE FILE MUST NOT BE SLOW. The tier walks
every head of the bar for every beam of every STEMLESS head, and re-derives a
mate's direction once per stemless head rather than once per mate -- so a
dense conductor's cell pays it repeatedly. This measures that rather than
guessing at it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-infer-stage-2026-09"))

import reinfer                                                   # noqa: E402
from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as RH           # noqa: E402
from tools.omr.staged.record import Q                            # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    a = ap.parse_args()
    rec = json.load(open(a.record))
    rec = rec["record"] if "record" in rec else rec

    out = {}
    for name, enabled in (("off", False), ("on", True)):
        log = reinfer.rebuild(rec, skip_verdicts=frozenset({Q.STEM_DIRECTION}))
        real = RH._direction_from_a_beam_mate
        if not enabled:
            RH._direction_from_a_beam_mate = lambda *x, **k: None
        t0 = time.time()
        try:
            adjudicate.run(log, order=(Q.STEM_DIRECTION,))
        finally:
            RH._direction_from_a_beam_mate = real
        out[name] = time.time() - t0
        print(f"{name:>4}: stem_direction pass {out[name]:8.2f} s")
    print(f"\nthe tier costs {out['on'] - out['off']:+.2f} s "
          f"({out['on'] / max(1e-9, out['off']):.1f}x) on four pages")
    (HERE / "out" / "cost.json").write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
