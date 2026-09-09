"""Score an EXPORT-SIDE change over the 20-row scan gate WITHOUT re-transcribing.

⚠️ THIS IS NOT A SHORTCUT AROUND `scan_eval`, IT IS THE OTHER HALF OF IT.
`scan_eval.run_pipeline` transcribes (hours, needs weights and `library/`) and
then does exactly one more thing: `pred.write_text(to_musicxml(result))`. A
change that acts on an ALREADY-MADE transcription cannot move the first half,
so re-running it measures the detector's own jitter and nothing else. This
re-runs only the second half, over the `.omr.json` files a real arm already
wrote, and scores them against the same trimmed truths.

⚠️ **WHAT IT THEREFORE CANNOT SEE.** Anything upstream of the exporter: a
detection that would have been made differently, a staff grouped differently, a
CV rung that did not run. Use it for export-side arms ONLY, and say so.

⚠️ **AND IT PINS THE TRANSCRIPTIONS BY HASH.** Two arms compared here must come
from the SAME `.omr.json` files or the delta is not the export change; the
report records each row's transcription md5 so a later reader can check that
rather than trust it.

    python3 benchmarks/omr-dynamics-staged-2026-09/probe/reexport_arm.py \
        --fixtures benchmarks/omr-scan-e2e-2026-09/fixtures --tag -hpoff \
        --arms off=OMR_PARTIAL_DYNAMICS=off complete=OMR_PARTIAL_DYNAMICS=complete
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.omr_ned import score_pair  # noqa: E402


def _rows(fixtures: pathlib.Path, tag: str) -> list[str]:
    out = []
    for p in sorted(fixtures.glob(f"*.{tag}.omr.json")):
        rid = p.name[: -len(f".{tag}.omr.json")]
        if (fixtures / f"{rid}.truth.musicxml").is_file():
            out.append(rid)
    return out


def _export(src: pathlib.Path, dst: pathlib.Path, env_pairs: list[str]) -> None:
    """Export in a SUBPROCESS, so an env-read at import time cannot leak.

    ⚠️ Deliberate: several flags in `export.py` are read inside a function, but
    one arm importing the module with a different environment than the next is
    exactly the cached-A/B failure in a smaller box. A fresh process per arm
    removes the question.
    """
    env = dict(os.environ)
    for pair in env_pairs:
        k, _, v = pair.partition("=")
        env[k] = v
    proc = subprocess.run(
        [sys.executable, "-m", "tools.omr.export", str(src),
         "--format", "musicxml", "--out", str(dst)],
        cwd=str(ROOT), env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"export failed for {src}:\n{proc.stderr[-2000:]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=pathlib.Path,
                    default=ROOT / "benchmarks/omr-scan-e2e-2026-09/fixtures")
    ap.add_argument("--tag", default="-hpoff",
                    help="which arm's transcriptions to re-export from")
    ap.add_argument("--arms", nargs="+", required=True,
                    help="name=VAR=value[,VAR=value] — first arm is the control")
    ap.add_argument("--work-dir", type=pathlib.Path,
                    default=ROOT / "benchmarks/omr-dynamics-staged-2026-09/out/reexport")
    ap.add_argument("--out", type=pathlib.Path, default=None)
    args = ap.parse_args()

    rows = _rows(args.fixtures, args.tag)
    if not rows:
        sys.stderr.write(f"FATAL: no `*.{args.tag}.omr.json` in {args.fixtures}. "
                         "A missing fixture reads as a zero.\n")
        return 2
    args.work_dir.mkdir(parents=True, exist_ok=True)

    arms = []
    for spec in args.arms:
        name, _, envs = spec.partition("=")
        arms.append((name, [e for e in envs.split(",") if e]))

    report = {"tag": args.tag, "n_rows": len(rows), "arms": [a for a, _ in arms],
              "rows": []}
    for rid in rows:
        src = args.fixtures / f"{rid}.{args.tag}.omr.json"
        truth = args.fixtures / f"{rid}.truth.musicxml"
        entry = {"row_id": rid,
                 "transcription_md5": hashlib.md5(src.read_bytes()).hexdigest()}
        for name, envs in arms:
            dst = args.work_dir / f"{rid}.{name}.musicxml"
            _export(src, dst, envs)
            res = score_pair(pred=dst, truth=truth, name=f"{rid}.{name}")
            text = dst.read_text()
            entry[name] = {
                "omr_ned": res["omr_ned"], "omr_ed": res["omr_ed"],
                "categories": res.get("categories", {}),
                "n_dynamics": text.count("<dynamics>"),
                "n_other_dynamics": text.count("<other-dynamics>"),
                "n_wedge": text.count("<wedge "),
            }
        report["rows"].append(entry)
        base = arms[0][0]
        line = f"{rid:34s}"
        for name, _ in arms:
            d = entry[name]["omr_ed"] - entry[base]["omr_ed"]
            line += (f"  {name}={entry[name]['omr_ed']:5d}"
                     + (f"({d:+d})" if name != base else "      "))
        print(line + f"   dyn " + " ".join(
            f"{n}={entry[n]['n_dynamics']}" for n, _ in arms))

    print("\n⚠️ PER ROW. No pooled figure — see scan_arm_table.py's docstring.")
    for name, _ in arms:
        tot = sum(r[name]["omr_ed"] for r in report["rows"])
        print(f"  {name:12s} summed edits over {len(rows)} rows: {tot}"
              + ("   (control)" if name == arms[0][0] else
                 f"   delta {tot - sum(r[arms[0][0]]['omr_ed'] for r in report['rows']):+d}"))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
