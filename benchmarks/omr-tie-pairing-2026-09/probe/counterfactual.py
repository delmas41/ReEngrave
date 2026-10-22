"""REACH BEFORE ACCURACY: what could a different PAIRING CHOICE reach at best?

`dy_vs_pitch.py` says 108 of 302 scan links bind two heads that are far apart on
the staff — the population where the pairing itself is the leading suspect. It
does not say whether the rule had a better option. This asks the counterfactual
over the candidates the rule ALREADY SAW, so it is an upper bound on any repair
that only changes WHICH candidate is picked:

  argmin_dx      what ships: nearest in x on each side, independently, with no
                 y preference at all — the "distance is nearly a coin flip"
                 shape this repo has now recorded for noteheads, hairpins and
                 dynamic letters.
  argmin_dy      pick the (left, right) PAIR whose two heads sit at the most
                 similar y, dx as the tie-break. Uses no pitch: a tie joins one
                 staff position to itself, and that is a fact about boxes.
  oracle_pitch   pick any pair whose two pitches match. NOT a candidate repair —
                 it reads the answer. It is the CEILING, printed so the honest
                 gain of `argmin_dy` can be read against what is even possible.

⚠️ An improvement here is an improvement in PAIRING AGREEMENT, not in ties
being correct: a rule that pairs two spurious same-position detections agrees
with itself perfectly. Read it as a bound.

    python3 .../counterfactual.py <dir-or-file>...
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

_SAME_MAX = 0.25  # staff spaces; the `dy~0` band of `dy_vs_pitch.py`


def _pairs(r):
    for dxl, yl, dl in r["lefts"]:
        for dxr, yr, dr in r["rights"]:
            if dl is dr:
                continue
            yield dxl, yl, dl, dxr, yr, dr


def main() -> int:
    files: list[pathlib.Path] = []
    for a in sys.argv[1:]:
        p = pathlib.Path(a)
        files += sorted(p.glob("*.omr.json")) if p.is_dir() else [p]
    if not files:
        sys.stderr.write("FATAL: no `.omr.json`\n")
        return 2
    c: collections.Counter = collections.Counter()
    for f in files:
        for r in walk(json.loads(f.read_text())):
            cands = list(_pairs(r))
            if not cands:
                continue
            c["links"] += 1
            nh = r["avg_nh_h"]

            def score(pick):
                dxl, yl, dl, dxr, yr, dr = pick
                same_y = abs(yl - yr) / nh <= _SAME_MAX
                pl, pr = dl.get("pitch"), dr.get("pitch")
                return same_y, (pl is not None and pl == pr)

            shipped = min(cands, key=lambda t: (t[0], t[3]))
            # `_pair_ties_in_staff` picks each side independently; reproduce
            # that rather than a joint argmin over dx, or the control would be
            # measuring a rule nobody runs.
            bl = min(r["lefts"], key=lambda t: t[0])[2]
            br = min(r["rights"], key=lambda t: t[0])[2]
            shipped = next((p for p in cands if p[2] is bl and p[5] is br),
                           shipped)
            by_dy = min(cands, key=lambda t: (abs(t[1] - t[4]) / nh, t[0], t[3]))
            oracle = next(
                (p for p in cands
                 if p[2].get("pitch") is not None
                 and p[2].get("pitch") == p[5].get("pitch")), None)
            for name, pick in (("shipped", shipped), ("argmin_dy", by_dy)):
                sy, sp = score(pick)
                c[f"{name}_same_y"] += sy
                c[f"{name}_same_pitch"] += sp
            c["oracle_exists"] += oracle is not None
            if oracle is not None and shipped[2] is oracle[2] \
                    and shipped[5] is oracle[5]:
                c["shipped_is_oracle"] += 1
            if oracle is not None and by_dy[2] is oracle[2] \
                    and by_dy[5] is oracle[5]:
                c["argmin_dy_is_oracle"] += 1
            if len(cands) > 1:
                c["links_with_a_choice"] += 1
    n = c["links"]
    if not n:
        sys.stderr.write("⚠️ ZERO links — a dead instrument.\n")
        return 2
    print(f"links with at least one candidate pair : {n}")
    print(f"  ...of which more than one option     : {c['links_with_a_choice']}")
    print(f"  ...for which a same-pitch pair EXISTS: {c['oracle_exists']}")
    print()
    print(f"{'rule':12s} {'heads at one staff position':>28s} "
          f"{'same pitch':>11s} {'== oracle':>10s}")
    for name in ("shipped", "argmin_dy"):
        print(f"{name:12s} {c[f'{name}_same_y']:28d} "
              f"{c[f'{name}_same_pitch']:11d} {c[f'{name}_is_oracle']:10d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
