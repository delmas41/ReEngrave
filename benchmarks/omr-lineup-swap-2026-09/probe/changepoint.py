"""Where inside a span do the printed names STOP AGREEING? — the support profile.

`lineup_spans` keys on staff COUNT and is silent about a swap at constant size.
The candidate signal is the margin labels. This probe computes, for every
candidate split page `q` inside a span, how many staff ORDINALS the full
systems either side disagree about — and prints the whole profile, so a rule
can be designed against the shape rather than fitted to one page.

    ORDINAL SUPPORT for a split at q
      an ordinal i supports q when the full systems LEFT of q have a clear
      majority name A at i, those at/right of q have a clear majority name B,
      and A != B.

The definition of a FULL system is `score_full_systems.py`'s: staff count equal
to the maximum system size in the span. Ordinals correspond across full systems
of one lineup; they do not across reduced ones, which is why reduced systems
are excluded and not merely down-weighted.

    changepoint.py LABELS.json --spans 0-40,41-98      # count-rule spans
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

#: A side of a candidate split needs this many full systems to speak.
MIN_SIDE_SYSTEMS = 3
#: An ordinal needs this many observed labels on a side to speak for it.
MIN_SIDE_OBS = 3
#: ...and that side's majority must be this share of them.
MIN_MAJORITY = 0.6


def full_systems(rows, first, last):
    """`[(page, system_index, [name|None])]` for the span's full systems."""
    inspan = [r for r in rows if first <= r["page"] <= last]
    sizes = [n for r in inspan for n in r["systems"]]
    if not sizes:
        return [], 0
    # Same merge cap as `movement_reference._peaks` / `_full_systems`: one page
    # read as a single 28-staff system must not become "the span's lineup".
    ordered = sorted(sizes)
    cap = ordered[len(ordered) // 2] * 2.0
    pages_at = {}
    for r in inspan:
        for n in r["systems"]:
            if n <= cap:
                pages_at.setdefault(n, set()).add(r["page"])
    # The width must RECUR — `build_reference`'s test. A size seen on one page
    # is a segmentation wobble (Brahms 1's finale reads 17 once against 16).
    recurring = [n for n, ps in pages_at.items() if len(ps) >= 2]
    if not recurring:
        return [], 0
    size = max(recurring)
    out = []
    for r in inspan:
        by_staff = {l["staff_index"]: l["instrument"] for l in r["labels"]}
        offset = 0
        for si, n in enumerate(r["systems"]):
            if n == size:
                out.append((r["page"], si,
                            [by_staff.get(offset + k) for k in range(n)]))
            offset += n
    return sorted(out), size


def majority(vals):
    seen = [v for v in vals if v is not None]
    if len(seen) < MIN_SIDE_OBS:
        return None, 0.0
    name, n = collections.Counter(seen).most_common(1)[0]
    return name, n / len(seen)


def support_at(left, right):
    """`(n_support, n_agree, detail)` for one candidate split."""
    if not left or not right:
        return 0, 0, []
    width = len(left[0][2])
    sup = agree = 0
    detail = []
    for i in range(width):
        a, fa = majority([s[2][i] for s in left])
        b, fb = majority([s[2][i] for s in right])
        if a is None or b is None:
            continue
        if fa < MIN_MAJORITY or fb < MIN_MAJORITY:
            continue
        if a != b:
            sup += 1
            detail.append((i, a, b))
        else:
            agree += 1
    return sup, agree, detail


def profile(systems):
    """`[(q, support, agree, detail)]` over every candidate split page."""
    pages = sorted({p for p, _s, _l in systems})
    out = []
    for q in pages[1:]:
        left = [s for s in systems if s[0] < q]
        right = [s for s in systems if s[0] >= q]
        if len(left) < MIN_SIDE_SYSTEMS or len(right) < MIN_SIDE_SYSTEMS:
            continue
        sup, agree, detail = support_at(left, right)
        out.append((q, sup, agree, detail))
    return out


def parse_spans(spec):
    out = []
    for part in spec.split(","):
        lo, hi = part.split("-")
        out.append((int(lo), int(hi)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("labels")
    ap.add_argument("--spans", required=True)
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args()

    rows = json.load(open(args.labels))
    for first, last in parse_spans(args.spans):
        systems, size = full_systems(rows, first, last)
        print(f"\n=== span {first}-{last}: full size {size}, "
              f"{len(systems)} full systems ===")
        prof = profile(systems)
        if not prof:
            print("  no candidate split has enough systems on both sides")
            continue
        best = max(prof, key=lambda r: r[1])
        for q, sup, agree, detail in prof:
            mark = "  <== BEST" if (q, sup) == (best[0], best[1]) else ""
            print(f"  q={q:3d}  support={sup:2d}  agree={agree:2d}{mark}")
            if args.detail and detail:
                for i, a, b in detail:
                    print(f"        ordinal {i:2d}: {a} | {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
