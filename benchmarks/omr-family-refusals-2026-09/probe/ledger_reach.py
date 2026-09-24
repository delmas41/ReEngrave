"""Reach per candidate ledger reason, off the cached rows — ROADMAP 3.4g.

    python3 benchmarks/omr-family-refusals-2026-09/probe/ledger_reach.py

⚠️ READS THE CACHE `ledger_geometry.py` WROTE, so a tolerance can be re-priced
without re-loading 900 MB of record. The cache is the probe's own output and
nothing else writes it.
"""
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "out"


def main():
    for f in sorted(glob.glob(str(HERE / "ledger-rows-*.json"))):
        rs = json.load(open(f))
        ws = [r for r in rs if r["step"] is not None]
        print(Path(f).name, "n_boxes", len(rs), "with_page_frame", len(ws))
        for tol in (0.15, 0.20, 0.25, 0.30):
            on = [r for r in ws if r["line_gap"] <= tol]
            inside = [r for r in on if r["beyond"] == 0.0]
            tall = [r for r in rs
                    if (r["h_spaces"] or 0) > 0.5 or (r["aspect"] or 0) > 1.0]
            seen = {r["id"] for r in on}
            notr = [r for r in ws if r["id"] not in seen
                    and (r["offset"] is None or r["offset"] > tol)]
            kept = len(ws) - len(seen | {r["id"] for r in notr})
            print(f"   tol {tol:.2f}  on_a_staff_line {len(on):5d} "
                  f"(inside the band {len(inside):5d})  "
                  f"tall_not_a_rung {len(tall):3d}  "
                  f"not_at_a_rung_step {len(notr):5d}  kept {kept:5d}  "
                  f"| on_a_staff_line with a head over them "
                  f"{sum(1 for r in on if r['heads_over'] > 0):5d}")


if __name__ == "__main__":
    main()
