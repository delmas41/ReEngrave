"""The different-pitch tie links are THREE populations, not one. Separate them.

`omr-chord-tie-2026-09/probe/pairing_pitches.py` reports one number — a link
binds two different pitches — and names the pairing. Opening the geometry shows
three distinguishable causes, each needing a different repair (or none):

  SPELLING    the two heads are the SAME STAFF STEP and differ only in
              accidental (`F#4 -> F4`, `D#5 -> D5`). The canonical tie crosses
              a barline, the far head does not restate its accidental because
              the tie carries it, and `pitch_resolver` spells that head from
              the key signature alone. THE PAIRING IS RIGHT AND THE INVARIANT
              IS WRONG HERE: `export._pitch_step` already exists and says so in
              its own docstring. `pairing_pitches.py` compares SPELLED pitches
              and therefore counts these as defects.

  STEP_APART  the two heads are ONE STAFF STEP apart (`F#5 -> G5`, `B5 -> C6`).
              A tie cannot be a step; a two-note SLUR is exactly this. The
              suspect here is the arc's CLASS, not the pairing.

  WIDE        anything further apart. Only here is the pairing itself the
              leading suspect, and `rescuable` says whether a different choice
              among the candidates the rule already saw would have fixed it.

⚠️ The three are reported APART and never summed into a headline, because the
repairs differ — one is a probe artefact, one is a classification problem one
stage upstream, and only the third is the pairing's.

⚠️ STEP_APART is evidence about a POPULATION, not a verdict on any one arc: a
tie whose far head is misread by one staff position also lands here. It is
read beside the page's printed slur:tie ratio (`arc_population.py`), never on
its own.

    python3 .../split_causes.py <dir-or-file>... [--list N]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from geometry import walk  # noqa: E402
from tools.omr.export import _pitch_step  # noqa: E402

#: Diatonic ladder, so "one staff step apart" is a STAFF-POSITION question and
#: not a semitone one — `B5 -> C6` is a step and `F#5 -> G5` is a step.
_LETTERS = "CDEFGAB"


def _ladder(step: str | None) -> int | None:
    """`"F4"` -> its diatonic index, so adjacency is a difference of 1."""
    if not step or len(step) < 2 or step[0] not in _LETTERS:
        return None
    try:
        octave = int(step[1:])
    except ValueError:
        return None
    return octave * 7 + _LETTERS.index(step[0])


def classify(pl: str | None, pr: str | None) -> str:
    sl, sr = _pitch_step(pl), _pitch_step(pr)
    if sl is None or sr is None:
        return "UNREADABLE"
    if sl == sr:
        return "SPELLING"
    a, b = _ladder(sl), _ladder(sr)
    if a is None or b is None:
        return "UNREADABLE"
    return "STEP_APART" if abs(a - b) == 1 else "WIDE"


def main() -> int:
    args = sys.argv[1:]
    n_list = 0
    if "--list" in args:
        i = args.index("--list")
        n_list = int(args[i + 1])
        del args[i:i + 2]
    files: list[pathlib.Path] = []
    for a in args:
        p = pathlib.Path(a)
        files += sorted(p.glob("*.omr.json")) if p.is_dir() else [p]
    if not files:
        sys.stderr.write("FATAL: no `.omr.json`\n")
        return 2
    pooled: collections.Counter = collections.Counter()
    print(f"{'file':46s} {'same':>5s} {'SPELL':>6s} {'STEP':>5s} "
          f"{'WIDE':>5s} {'?':>3s} {'WIDE-rescuable':>15s}")
    for f in files:
        c: collections.Counter = collections.Counter()
        shown = 0
        for r in walk(json.loads(f.read_text())):
            left, right = r["pick_l"], r["pick_r"]
            if left is None or right is None or left[2] is right[2]:
                continue
            pl, pr = left[2].get("pitch"), right[2].get("pitch")
            if pl is not None and pl == pr:
                c["same"] += 1
                continue
            kind = classify(pl, pr)
            c[kind] += 1
            if kind == "WIDE":
                l_p = {d.get("pitch") for _, _, d in r["lefts"]}
                r_p = {d.get("pitch") for _, _, d in r["rights"]}
                if l_p & r_p:
                    c["WIDE_rescuable"] += 1
                if shown < n_list:
                    shown += 1
                    print(f"    WIDE {pl}->{pr} dy_heads="
                          f"{left[1] - right[1]:+.0f} nh_h={r['avg_nh_h']:.0f} "
                          f"dxL={left[0]:.0f} dxR={right[0]:.0f}")
        pooled += c
        print(f"{f.name[:46]:46s} {c['same']:5d} {c['SPELLING']:6d} "
              f"{c['STEP_APART']:5d} {c['WIDE']:5d} {c['UNREADABLE']:3d} "
              f"{c['WIDE_rescuable']:15d}")
    print("\n pooled: " + "  ".join(f"{k}={v}" for k, v in sorted(pooled.items())))
    if not (pooled["same"] + pooled["SPELLING"] + pooled["STEP_APART"]
            + pooled["WIDE"]):
        sys.stderr.write("⚠️ ZERO paired links — a dead instrument.\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
