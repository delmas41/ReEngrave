"""How many ties does the file hold, against how many the TRUTH holds?

⚠️ OMR-NED is the wrong scorer for a change that REMOVES elements: it is
symmetric, so it rewards under-prediction, and this project has already
recorded a case where a ratio fell while the edit count rose. A change that
deletes eight ties from a page whose truth holds one is unambiguously right,
and the metric charges it. So the inventory is reported directly.

⚠️ IT IS ONE-SIDED, exactly as `omr-chord-tie-2026-09/probe/tie_resolves.py`
is: a count landing on the truth's count does NOT mean the ties are on the
right notes. Over-emission is a defect it can see; misplacement is not. Read
it as a bound, never as accuracy.

    python3 .../tie_inventory.py --fixtures <dir> --arms off=... on=...
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

ARMS_DIR = ROOT / "benchmarks" / "omr-tie-pairing-2026-09" / "out" / "arms"


def starts(path: pathlib.Path) -> int:
    return len(re.findall(r'<tied[^>]*type="start"', path.read_text(errors="replace")))


def main() -> int:
    args = sys.argv[1:]
    fixtures = pathlib.Path(args[args.index("--fixtures") + 1])
    arms = args[args.index("--arms") + 1:]
    rows = []
    for truth in sorted(fixtures.glob("*.musicxml")):
        if truth.name.endswith(".omr.musicxml"):
            continue
        stem = truth.name[: -len(".musicxml")]
        exported = {a: ARMS_DIR / f"{stem}.{a}.musicxml" for a in arms}
        if not all(p.is_file() for p in exported.values()):
            continue
        rows.append((stem, starts(truth),
                     {a: starts(p) for a, p in exported.items()}))
    if not rows:
        sys.stderr.write("FATAL: no exported arm beside a truth — run "
                         "engraved_arm.py first. A dead instrument.\n")
        return 2
    print(f"{'work':30s} {'truth':>6s} " +
          " ".join(f"{a:>7s}" for a in arms) + "   over-emission")
    tot_t = 0
    tot = {a: 0 for a in arms}
    for stem, t, got in rows:
        tot_t += t
        for a in arms:
            tot[a] += got[a]
        over = "  ".join(f"{a}:{got[a] - t:+d}" for a in arms)
        print(f"{stem[:30]:30s} {t:6d} " +
              " ".join(f"{got[a]:7d}" for a in arms) + f"   {over}")
    print(f"{'POOLED':30s} {tot_t:6d} " +
          " ".join(f"{tot[a]:7d}" for a in arms))
    print("absolute over/under-emission vs truth: " + "  ".join(
        f"{a}={tot[a] - tot_t:+d}" for a in arms))
    print("summed |per-work error|: " + "  ".join(
        f"{a}={sum(abs(g[a] - t) for _, t, g in rows)}" for a in arms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
