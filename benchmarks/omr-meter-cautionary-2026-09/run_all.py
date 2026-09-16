"""Run every probe and write `out/REPORT.txt` — the committed artefact every
figure in FINDINGS.md is read off.

⚠️ EACH PROBE'S EXIT CODE IS RECORDED AND THE WORST ONE IS RETURNED, so a
probe that declares itself DEAD (2) or whose own control FAILED (3) cannot be
lost inside a long log that ends in a table.

    python3 benchmarks/omr-meter-cautionary-2026-09/run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PROBES = ["probe_reach.py", "probe_contest.py", "probe_digit_reader.py",
          "probe_second_document.py"]


def main() -> int:
    out = HERE / "out" / "REPORT.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    chunks, worst = [], 0
    for name in PROBES:
        r = subprocess.run([sys.executable, str(HERE / name)], cwd=ROOT,
                           capture_output=True, text=True)
        worst = max(worst, r.returncode)
        chunks.append(f"### {name}   (exit {r.returncode})\n{r.stdout}")
        if r.returncode:
            chunks.append(f"--- stderr ---\n{r.stderr}")
        print(f"{name:<28} exit {r.returncode}")
    chunks.append(f"### worst exit code across all probes: {worst}\n")
    out.write_text("\n".join(chunks))
    print(f"wrote {out}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
