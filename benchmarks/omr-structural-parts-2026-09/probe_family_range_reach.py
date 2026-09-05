"""Can a FAMILY-level written range veto anything? Attribution before a build.

Consumer #2 of the bracket-block finding: `_dedupe_cross_staff_detections`
resolves a glyph claimed by two staves with four kinds of evidence — ladder,
written RANGE, notes-in-bar, then distance. The range comes from
`_staff_written_ranges(page, dossier)`, which returns `{}` outright when there
is no dossier. The scan benchmark runs with NO dossier by protocol, so **the
range veto never fires on any of the 20 rows** and every contested pair falls
through to the ladder and then to distance. The audit's proposal is that a
bracket block supplies a family-level constraint for free where no dossier
exists.

This asks the question that decides whether that is worth building, and it
costs seconds instead of the ~30 minutes per arm a re-transcription costs:

  A VETO ON THE IMPOSSIBLE NEEDS A NARROW RANGE. The existing veto works
  because ONE instrument's range is narrow — a bassoon cannot sound A♭1. A
  FAMILY's range is the UNION of its members', and a family holds both its
  smallest and largest instrument: woodwind spans piccolo to contrabassoon,
  string spans violin to contrabass. If the union spans essentially the whole
  page, the veto can never fire and the consumer is vacuous no matter how good
  the blocks are.

Measured two ways: the union ranges themselves, and the share of the corpus's
actual detected pitches that fall outside their own staff's family union.

    python3 benchmarks/omr-structural-parts-2026-09/probe_family_range_reach.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.instruments import INSTRUMENTS  # noqa: E402

FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures")
SUFFIX = ".reconciliation.omr.json"

_STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(pitch) -> int | None:
    """`{'step','octave','alter'}` or a string like 'A#4' -> MIDI number."""
    if isinstance(pitch, dict):
        step = str(pitch.get("step") or "").upper()[:1]
        if step not in _STEPS or pitch.get("octave") is None:
            return None
        return (_STEPS[step] + int(pitch.get("alter") or 0)
                + (int(pitch["octave"]) + 1) * 12)
    if isinstance(pitch, str) and pitch:
        step = pitch[0].upper()
        if step not in _STEPS:
            return None
        alter = pitch.count("#") - pitch.count("b", 1)
        tail = pitch.rstrip("0123456789")
        try:
            octave = int(pitch[len(tail):])
        except ValueError:
            return None
        return _STEPS[step] + alter + (octave + 1) * 12
    return None


def family_unions() -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for inst in INSTRUMENTS:
        rng = getattr(inst, "written_range", None)
        if not rng:
            continue
        lo, hi = int(rng[0]), int(rng[1])
        cur = out.get(inst.family)
        out[inst.family] = (min(lo, cur[0]), max(hi, cur[1])) if cur else (lo, hi)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(FIXTURES))
    args = ap.parse_args()

    unions = family_unions()
    print("A FAMILY'S UNION WRITTEN RANGE, from instruments.py\n")
    print(f"{'family':<12} {'lo':>4} {'hi':>4} {'semitones':>10}   widest members")
    for fam, (lo, hi) in sorted(unions.items(), key=lambda kv: -(kv[1][1] - kv[1][0])):
        members = [i for i in INSTRUMENTS
                   if i.family == fam and getattr(i, "written_range", None)]
        loi = min(members, key=lambda i: i.written_range[0]).name if members else "?"
        hii = max(members, key=lambda i: i.written_range[1]).name if members else "?"
        print(f"{fam:<12} {lo:>4} {hi:>4} {hi-lo:>10}   {loi} .. {hii}")

    # A staff of music spans roughly MIDI 36-96 in printed pitch; anything the
    # detector reads lives inside the cell, so this is the population the veto
    # would have to separate.
    print("\n\nWHAT SHARE OF DETECTED PITCHES A FAMILY UNION EXCLUDES\n")
    fx = Path(args.fixtures)
    pooled = Counter()
    print(f"{'row':<34} {'pitches':>8} {'outside own family':>19}")
    for p in sorted(fx.glob(f"*{SUFFIX}")):
        rid = p.name[:-len(SUFFIX)]
        result = json.loads(p.read_text())
        n = out = 0
        for page in result.get("pages", []):
            for sys_ in page.get("systems", []):
                for staff in sys_.get("staves", []):
                    fam = staff.get("instrument_family")
                    rng = unions.get(fam)
                    for measure in staff.get("measures", []):
                        for det in measure.get("detections", []):
                            if det.get("category") != "notehead":
                                continue
                            m = midi(det.get("pitch"))
                            if m is None:
                                continue
                            n += 1
                            if rng and not (rng[0] <= m <= rng[1]):
                                out += 1
        pooled["n"] += n
        pooled["out"] += out
        print(f"{rid:<34} {n:>8} {out:>19}")
    share = pooled["out"] / max(1, pooled["n"])
    print(f"\n{'TOTAL':<34} {pooled['n']:>8} {pooled['out']:>19}   "
          f"({share:.4f})")
    print("\nA veto fires only where ONE reading is outside its range and the "
          "other is inside\nits own. That requires the outside case to exist "
          "at all.")


if __name__ == "__main__":
    main()
