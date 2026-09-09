"""Run the meter arms over the engraved boundary fixture, one process each.

⚠️ EVERY ARM GETS ITS OWN OUTPUT PATH AND ITS OWN ENVIRONMENT DICT. Two traps
this repo has already paid for are avoided by construction here:

  * `env $VARS python3 ...` in zsh does NOT word-split an unquoted expansion,
    so a two-variable arm silently sets ONE variable whose value contains the
    other's name -- and the arm that exists to turn a flag on runs with it off,
    returning a clean byte-identical "no reach" (handoff 2026-09-09 §4.1).
    Here the environment is a dict handed to `subprocess`.
  * a cached A/B: `scan_eval` returns early on an existing output file. This
    writes a distinct `--out` per arm and refuses to start if one exists
    unless `--force`.

    python3 benchmarks/.../run_arms.py --pages 0-3 --tag full
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WEIGHTS = ("tools/omr/training/data/weights/"
           "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")

#: ⚠️ ENGRAVED WEIGHTS, NOT THE SCAN PRODUCTION ONES. This fixture is a
#: LilyPond render, and `transcribe`'s own weight routing serves the imgsz2048
#: checkpoint to digitally engraved input (0.1399 vs 0.1421 pooled). The
#: staged CLI does no routing, so the choice is made here and recorded.

ARMS = {
    "OFF":   {},
    "CARRY": {"OMR_METER_CARRY": "1"},
    "BARS":  {"OMR_METER_FROM_BARS": "1"},
    "BOTH":  {"OMR_METER_CARRY": "1", "OMR_METER_FROM_BARS": "1"},
}


def run(pdf: Path, pages: str, tag: str, arm: str, force: bool,
        weights: str = WEIGHTS) -> Path:
    out = HERE / "out" / f"{tag}-{arm}.json"
    if out.is_file() and not force:
        print(f"  {arm}: exists, skipping ({out.name}) -- pass --force to redo")
        return out
    env = dict(os.environ)
    env["OMR_SURYA_KEEP_ALIVE"] = "0"       # unattended: own the worker
    # ⚠️ Both flags are set EXPLICITLY in every arm, including to "0", so an
    # arm never inherits a flag from the shell that invoked it.
    env["OMR_METER_CARRY"] = "0"
    env["OMR_METER_FROM_BARS"] = "0"
    env.update(ARMS[arm])
    cmd = [sys.executable, "-m", "tools.omr.staged", str(pdf),
           "--pages", pages, "--weights", weights, "--out", str(out)]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    (HERE / "out" / f"{tag}-{arm}.err").write_text(proc.stderr)
    if proc.returncode != 0:
        raise SystemExit(f"{arm} FAILED (exit {proc.returncode}); see .err")
    print(f"  {arm}: {time.time() - t0:.0f}s  carry="
          f"{env['OMR_METER_CARRY']} bars={env['OMR_METER_FROM_BARS']}  -> {out.name}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=str(HERE / "fixtures" / "boundary-m150-180.pdf"))
    ap.add_argument("--pages", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--arms", default="OFF,CARRY,BARS,BOTH")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--weights", default=WEIGHTS,
                    help="scan input needs the hollow graft, not the engraved "
                         "checkpoint -- the staged CLI does no weight routing")
    a = ap.parse_args()
    print(f"{a.tag}: pages {a.pages}")
    for arm in a.arms.split(","):
        run(Path(a.pdf), a.pages, a.tag, arm.strip(), a.force, a.weights)
