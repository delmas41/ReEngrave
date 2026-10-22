"""Export-only A/B over the 11 ENGRAVED fixtures, switched by env var.

The scan half of this shape is `benchmarks/omr-dynamics-staged-2026-09/probe/
reexport_arm.py`; the engraved fixtures are laid out differently (`<w>.omr.json`
beside `<w>.musicxml`, no `.truth.` infix and no tag), so this is that probe's
mirror rather than a flag on it.

⚠️ IT CAN ONLY SEE AN EXPORT-SIDE CHANGE. `transcribe._pair_ties_in_staff` runs
inside `transcribe`, so a change THERE is invisible here and the zero this
would report would be the instrument, not the result. Checked rather than
assumed: `grep -n _pair_ties_in_staff tools/omr/export.py` returns three hits
and ALL THREE ARE COMMENTS — the function is never called there — while
`OMR_ARC_RECLASS`, the flag this was built to price, is read inside
`export.py` itself. So this arm can see the flag and could NOT see a change to
the pairing.

⚠️ Each arm exports in a FRESH SUBPROCESS so an env read at import time cannot
leak between arms, and each row's transcription md5 is recorded so a reader can
check the transcribe half was held identical rather than trust it.

    python3 .../engraved_arm.py --arms off=OMR_ARC_RECLASS=0 on=OMR_ARC_RECLASS=1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.omr_ned import score_pair  # noqa: E402

DEFAULT_FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"

_EXPORT = (
    "import json,pathlib,sys;"
    "sys.path.insert(0, sys.argv[3]);"
    "from tools.omr.export import to_musicxml;"
    "pathlib.Path(sys.argv[2]).write_text("
    "to_musicxml(json.loads(pathlib.Path(sys.argv[1]).read_text())))"
)


def _export(src: pathlib.Path, dst: pathlib.Path, pairs: list[str]) -> None:
    env = dict(os.environ)
    for pair in pairs:
        key, _, value = pair.partition("=")
        env[key] = value
    subprocess.run([sys.executable, "-c", _EXPORT, str(src), str(dst),
                    str(ROOT)], check=True, env=env)


def _tied(path: pathlib.Path) -> tuple[int, int]:
    text = path.read_text(errors="replace")
    return (len(re.findall(r'<tied[^>]*type="start"', text)),
            len(re.findall(r'<tied[^>]*type="stop"', text)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=pathlib.Path, default=DEFAULT_FIXTURES)
    ap.add_argument("--arms", nargs="+", required=True,
                    help="name=ENV=VALUE ...")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--work-dir", type=pathlib.Path,
                    default=ROOT / "benchmarks" / "omr-tie-pairing-2026-09"
                    / "out" / "arms")
    args = ap.parse_args()

    arms = []
    for spec in args.arms:
        name, _, envspec = spec.partition("=")
        arms.append((name, [envspec]))
    if len({tuple(e) for _, e in arms}) < len(arms):
        sys.stderr.write("FATAL: two arms with the SAME environment — an A/B "
                         "that cannot differ reports 'identical' whatever the "
                         "change did.\n")
        return 2
    args.work_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for omr in sorted(args.fixtures.glob("*.omr.json")):
        stem = omr.name[: -len(".omr.json")]
        truth = args.fixtures / f"{stem}.musicxml"
        if truth.is_file():
            rows.append((stem, omr, truth))
    if not rows:
        sys.stderr.write("FATAL: no fixture pairs — a dead instrument.\n")
        return 2

    report = {"fixtures": str(args.fixtures), "n_rows": len(rows),
              "arms": [a for a, _ in arms], "rows": []}
    totals = {a: 0 for a, _ in arms}
    tied_totals = {a: [0, 0] for a, _ in arms}
    n_differ = 0
    for stem, omr, truth in rows:
        md5 = hashlib.md5(omr.read_bytes()).hexdigest()
        row = {"row_id": stem, "transcription_md5": md5}
        digests = {}
        for name, envs in arms:
            dst = args.work_dir / f"{stem}.{name}.musicxml"
            _export(omr, dst, envs)
            res = score_pair(pred=dst, truth=truth)
            starts, stops = _tied(dst)
            totals[name] += res["omr_ed"]
            tied_totals[name][0] += starts
            tied_totals[name][1] += stops
            digests[name] = hashlib.md5(dst.read_bytes()).hexdigest()
            row[name] = {"omr_ned": res["omr_ned"], "omr_ed": res["omr_ed"],
                         "tied_start": starts, "tied_stop": stops,
                         "md5": digests[name]}
        if len(set(digests.values())) > 1:
            n_differ += 1
        report["rows"].append(row)
        print(f"{stem[:30]:32s} " + "  ".join(
            f"{a}={row[a]['omr_ed']:5d}/{row[a]['tied_start']:3d}"
            for a, _ in arms))
    report["summed_edits"] = totals
    report["tied"] = tied_totals
    report["files_that_differ"] = n_differ
    print("\nsummed edits: " + "  ".join(f"{a}={totals[a]}" for a, _ in arms))
    print("<tied> start/stop: " + "  ".join(
        f"{a}={tied_totals[a][0]}/{tied_totals[a][1]}" for a, _ in arms))
    print(f"files that DIFFER between arms: {n_differ} of {len(rows)}")
    if n_differ == 0:
        sys.stderr.write("⚠️ ZERO files differ — either the change is inert "
                         "or the arm could not see it. Do not read the edit "
                         "delta as a result.\n")
    if args.out:
        args.out.write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
