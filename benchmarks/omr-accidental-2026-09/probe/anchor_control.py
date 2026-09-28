"""ROADMAP 2.7 — does the FLAT ANCHOR correction close the second mode?

`gap_histogram.py` run twice, at `--anchor-flat 0.5` (the uncorrected box
centre) and at Bravura's `0.715`, on both documents. ⚠️ A CONTROL THAT CAN
FAIL: if the second mode in the dy histogram is not the flats' ascender, the
correction moves nothing and the two rows read the same.

    python3 probe/anchor_control.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARED = Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
RECORDS = {
    "litolff": SHARED / "beethoven5-litolff-mvt1-whole-20260923.record.json",
    "brahms": SHARED / "brahms1-breitkopf-mvt1-whole-20260923.record.json",
}


def main() -> int:
    out_dir = HERE.parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, path in RECORDS.items():
        for anchor in ("0.5", "0.715"):
            dest = out_dir / f"anchor-control-{label}-{anchor}.json"
            subprocess.run(
                [sys.executable, str(HERE / "gap_histogram.py"),
                 "--record", str(path), "--label", label,
                 "--anchor-flat", anchor, "--out", str(dest)],
                stdout=subprocess.DEVNULL, check=True)
            d = json.loads(dest.read_text())["dy_positions_inside_dx_window"]
            h = [c for _e, c in d["hist_0_to_4_step_0.1"]]
            row = {
                "document": label, "anchor_flat": float(anchor),
                "n": d["n"],
                "within_0.7_positions": sum(h[:7]),
                "second_mode_0.7_to_1.4": sum(h[7:14]),
                "beyond_1.4": sum(h[14:]),
                "median": d["median"], "p75": d["p75"],
                "hist_first_16_bins": d["hist_0_to_4_step_0.1"][:16],
            }
            rows.append(row)
            print(f"{label:8s} anchor={anchor:5s} n={d['n']:5d} "
                  f"|dy|<0.7: {row['within_0.7_positions']:5d}  "
                  f"0.7-1.4: {row['second_mode_0.7_to_1.4']:5d}  "
                  f">=1.4: {row['beyond_1.4']:4d}  "
                  f"median={d['median']}  p75={d['p75']}")
    (out_dir / "anchor-control.json").write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
