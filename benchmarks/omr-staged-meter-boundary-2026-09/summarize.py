"""Reduce the (large, gitignored) staged records to the small committed
artefacts: one `<arm>.meter.json` per run plus one `REPORT.txt` holding every
table and every control.

⚠️ THE RECORDS ARE BUILD PRODUCTS AND ARE NOT COMMITTED -- 2-10 MB each. What
is committed is what a reader needs to check the claims: the meter verdicts
with their full `detail`, and the report those tables were read off.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

#: (report tag -> the fixture the TRUTH table is keyed on)
FIXTURE_OF = {
    "full": "boundary-m150-180", "p0p3": "boundary-m150-180",
    "p2p3": "boundary-m150-180",
    "rev": "boundary-m204-232", "rev-p1p2": "boundary-m204-232",
    "revfix": "boundary-m204-232", "fullfix": "boundary-m150-180",
    "lit012fix": "litolff-984073", "lit6162fix": "litolff-984073",
}


def run(args):
    return subprocess.run([sys.executable,
                           str(HERE / "report_boundary.py")] + args,
                          cwd=ROOT, capture_output=True, text=True)


def main():
    lines = []
    records = sorted(p for p in (HERE / "out").glob("*.json")
                     if not p.name.endswith((".meter.json", ".coverage.json")))
    for rec in records:
        tag = rec.stem.rsplit("-", 1)[0]
        fixture = FIXTURE_OF.get(tag)
        if fixture is None:
            continue
        data = json.loads(rec.read_text())["record"]
        # ⚠️ THE ID LISTS ARE DROPPED AND REPLACED BY THEIR LENGTHS.
        # `considered`, `basis` and `correlated` are lists of observation and
        # verdict ids -- thousands per verdict, meaningless without the record
        # they index, and ~1000x the size of everything a reader of this
        # benchmark needs (the outcome, the reason, the value, the detail).
        # Regenerate the full record with `run_arms.py` if you need them.
        bulky = ("considered", "basis", "correlated")
        meters = []
        for v in data["verdicts"]:
            if v["quantity"] != "meter":
                continue
            row = {k: x for k, x in v.items() if k not in bulky}
            for k in bulky:
                row["n_" + k] = len(v.get(k) or [])
            meters.append(row)
        (HERE / "out" / f"{rec.stem}.meter.json").write_text(
            json.dumps(meters, indent=2, default=str))
    for tag, fixture in FIXTURE_OF.items():
        files = sorted(str(p) for p in (HERE / "out").glob(f"{tag}-*.json")
                       if not p.name.endswith((".meter.json", ".coverage.json"))
                       and p.stem.rsplit("-", 1)[0] == tag)
        if not files:
            continue
        got = run(files + ["--tag", fixture])
        lines.append(got.stdout.rstrip() + got.stderr.rstrip())
    (HERE / "out" / "REPORT.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
