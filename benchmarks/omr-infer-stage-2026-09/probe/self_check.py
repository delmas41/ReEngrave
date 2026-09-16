"""Score INFER by an invariant it did NOT read — no truth file required.

⚠️⚠️ THE TRAP THIS SCRIPT EXISTS TO REFUSE: **do not score an inference by the
quantity it consumed.** If a rule collapses a duration USING the bar sum, then
scoring it BY bar-fill is scoring it by the thing it optimises — the fault
CLAUDE.md records against the tie-pairing repair, where *"same-y and same-pitch
are near equivalent, and the rule is being scored by a quantity it optimises"*.

So this script does not simply print a number. It first proves the invariant is
INDEPENDENT of the rule under test, and REFUSES to print a score when it is
not. A caveat printed beside a number is read as a number.

Two independence conditions, both checked:

  1. `infer.scoring_conflict(rule, invariant_inputs)` must be empty. The rule
     declares what it `reads`; `collapse_duration_by_column` reads
     `onset_column`, `event`, `duration`, `glyph_box` and NOT `meter`.
  2. ⚠️ `OMR_METER_FROM_BARS` MUST BE OFF, and this is the subtle one. That
     flag lets a system's own BAR SUMS name its meter — and bar-fill compares
     a bar's sum against the `<time>` in the same file. With it on, the
     denominator is derived from the very quantity the rule moves, and the
     test becomes circular through a flag nobody would think to check. Off by
     default; asserted here rather than assumed.

⚠️ AND A SELF-CHECK IS A REPORT AND AN ALARM, NEVER AN OBJECTIVE. `bar_fill`
deliberately fails only when the instrument assessed NOTHING, never on a
threshold, because a bar-fill number used as a gate is gamed by emitting FEWER
symbols — an inference stage optimising it would learn to SUPPRESS, which is
the same trap OMR-NED's symmetry set from the other direction. Nothing here
returns a pass/fail on the number, and nothing in `tools/` reads it.

    python3 benchmarks/omr-infer-stage-2026-09/probe/self_check.py \
        --off out/export-off.musicxml --on out/export-on.musicxml
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import infer                                # noqa: E402
from tools.omr.staged.record import Q                             # noqa: E402

BAR_FILL = ROOT / "benchmarks/omr-rest-sizing-2026-09/probe/bar_fill.py"

#: What `bar_fill.py` reads: a bar's own note durations, against the `<time>`
#: the same file declares. Named here so condition 1 is a computation rather
#: than a claim.
BAR_FILL_INPUTS = (Q.METER,)


def independence_report() -> int:
    """Prove the invariant is independent of every rule, or refuse."""
    infer._ensure_rules()
    bad = 0
    print("── INDEPENDENCE ──────────────────────────────────────────────")
    for r in infer.RULES:
        clash = infer.scoring_conflict(r, BAR_FILL_INPUTS)
        mark = "REFUSED" if clash else "ok"
        print(f"  {r.inference.value}: reads {list(r.reads)}")
        print(f"      vs bar_fill inputs {list(BAR_FILL_INPUTS)} -> {mark}"
              + (f" (shares {list(clash)})" if clash else ""))
        bad += bool(clash)

    from_bars = os.environ.get("OMR_METER_FROM_BARS", "0").strip()
    on = from_bars in ("1", "true", "yes", "on")
    print(f"  OMR_METER_FROM_BARS={from_bars!r} -> "
          + ("REFUSED: the meter would be derived from the bar sums this "
             "rule moves" if on else "ok"))
    bad += bool(on)
    return bad


def run_bar_fill(path: str, bar_beats: float) -> str:
    out = subprocess.run(
        [sys.executable, str(BAR_FILL), path, "--bar-beats", str(bar_beats)],
        capture_output=True, text=True)
    return out.stdout + out.stderr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True, help="the flag-OFF export")
    ap.add_argument("--on", required=True, help="the flag-ON export")
    ap.add_argument("--bar-beats", type=float, default=2.0,
                    help="the movement's printed bar length. Litolff "
                         "Beethoven 5 mvt 1 is 2/4 throughout.")
    a = ap.parse_args()

    bad = independence_report()
    if bad:
        print("\n⚠️⚠️ REFUSING TO PRINT A SCORE. The invariant is not "
              "independent of the rule under test, so any number here would "
              "measure the quantity the rule optimises. Fix the rule's "
              "`reads`, or score it with a different invariant, or say "
              "plainly that no self-check exists for it.", file=sys.stderr)
        return 2

    print("\n── BAR FILL, flag OFF ────────────────────────────────────────")
    print(run_bar_fill(a.off, a.bar_beats))
    print("── BAR FILL, flag ON ─────────────────────────────────────────")
    print(run_bar_fill(a.on, a.bar_beats))
    print("⚠️ A REPORT AND AN ALARM, NEVER AN OBJECTIVE. Do not tune against "
          "these numbers: bar fill is gamed by emitting FEWER symbols, which "
          "is the direction that makes the file worse.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
