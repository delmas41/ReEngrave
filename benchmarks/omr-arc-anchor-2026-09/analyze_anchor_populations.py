"""Sweep anchor windows over the raw per-end records and report, per
(dx_out_max, dx_in_max, dy_max, edge_exempt) arm, how many real arcs stay
anchored and how many fakes anchor falsely — split by fake family.

An arc is "anchored" when every end is either CUT-EXEMPT (within
edge_exempt spaces of the cell's left/right edge) or has a notehead inside
the window, AND at least one end has an actual notehead anchor (an arc
exempt at both ends asserts nothing).
"""
import itertools
import json
from pathlib import Path

A = Path("benchmarks/omr-arc-anchor-2026-09")


def anchored(row, dx_out, dx_in, dy_max, edge_exempt):
    n_anchored = 0
    for end in row["ends"]:
        hit = any(-dx_in <= dx <= dx_out and dy <= dy_max
                  for dx, dy in end["nh"])
        if hit:
            n_anchored += 1
        elif end["edge_sp"] > edge_exempt:
            return False
    return n_anchored >= 1


def main():
    rows = json.load(open(A / "anchor_populations.json"))
    print(f"{'dx_out':>6} {'dx_in':>6} {'dy':>4} {'edge':>5} | "
          f"{'real kept':>9} {'jag anch':>8} {'bleed anch':>10}")
    n_real = sum(r["kind"] == "real" for r in rows)
    n_jag = sum(r["family"] == "jag" for r in rows)
    n_bleed = sum(r["family"] == "bleed" for r in rows)
    for dx_out, dx_in, dy_max, edge in itertools.product(
            (1.0, 2.0, 3.0), (0.5, 1.0, 2.0), (1.0, 1.5, 2.0, 3.0), (0.5,)):
        rk = ja = bl = 0
        for r in rows:
            a = anchored(r, dx_out, dx_in, dy_max, edge)
            if r["kind"] == "real":
                rk += a
            elif r["family"] == "jag":
                ja += a
            else:
                bl += a
        print(f"{dx_out:6.1f} {dx_in:6.1f} {dy_max:4.1f} {edge:5.1f} | "
              f"{rk:4d}/{n_real:<4d} {ja:3d}/{n_jag:<4d} {bl:4d}/{n_bleed:<5d}")


if __name__ == "__main__":
    main()
