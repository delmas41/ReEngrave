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
    "brahms1eng": "brahms1-m1-22", "brahms4eng": "brahms4-m386-412",
    "brahms1scan": "brahms1-317803",
    # ⚠️ The `m2` runs are the SAME arms re-measured on the MERGED tree.
    # 221 lines of `rhythm.py` and 404 of `gather.py` landed on main between
    # the first measurement and the merge, and `gather.py` is where the
    # `Q.EVENT` / `Q.DURATION` rows these decisions read come from. A result
    # that is not re-run across a merge like that is an assumption.
    "m2full": "boundary-m150-180", "m2p0p3": "boundary-m150-180",
    "m2rev": "boundary-m204-232", "m2brahms1eng": "brahms1-m1-22",
    "m2brahms4eng": "brahms4-m386-412", "m2brahms1scan": "brahms1-317803",
    # `m3` = re-measured again after a SIBLING session's `_meter_fallbacks`
    # landed on main. That change reorders what a REFUSED carry does, which
    # is the branch two of these fixtures land on — so it is re-run, not
    # assumed. See the handoff's coordination section.
    "m3full": "boundary-m150-180", "m3p0p3": "boundary-m150-180",
    "m3rev": "boundary-m204-232", "m3brahms1eng": "brahms1-m1-22",
    "m3brahms4eng": "brahms4-m386-412", "m3brahms1scan": "brahms1-317803",
    # `m4` = the same arms again, with `_meter_changes` comparing a
    # candidate against the meter IN FORCE rather than against the
    # system's opening.
    "m4full": "boundary-m150-180", "m4rev": "boundary-m204-232",
    "m4brahms1eng": "brahms1-m1-22", "m4brahms4eng": "brahms4-m386-412",
    "m4brahms1scan": "brahms1-317803", "m4lit6162": "litolff-984073",
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
