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
from typing import Optional

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


def _tree_id() -> Optional[str]:
    """The commit this tree is at, or None when that cannot be established.

    ⚠️⚠️ NONE IS THE WHOLE POINT, AND THE FIRST DRAFT GOT IT WRONG TWICE — both
    times by returning a string that COMPARES EQUAL TO ITSELF.

      * `except Exception: return "unknown"` — two arms built on a machine
        without git both stamped `"unknown"`, matched, and were silently
        reused. That is the exact failure this guard exists to prevent,
        reintroduced in its own fallback.
      * worse, and it never reached that `except`: `subprocess.run` WITHOUT
        `check=True` returns a non-zero exit as an empty stdout, no exception
        raised — so outside a git repo `sha` was `""`, the whole id was `""`,
        and two empty stamps matched too.

    So the rule is the one a DIRTY tree already forced: **anything that cannot
    uniquely name a tree must never compare equal to anything, including
    itself.** Expressed as None rather than as a clever string, and the caller
    then writes NO stamp — which the reader already refuses on. One mechanism,
    no special values.

    ⚠️ A dirty tree returns None for the same reason: a SHA cannot tell two
    sets of uncommitted edits apart, so it proves neither sameness nor
    difference.
    """
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, check=True)
    except Exception:                                         # noqa: BLE001
        return None
    if dirty.stdout.strip() or not sha.stdout.strip():
        return None
    return sha.stdout.strip()


def run(pdf: Path, pages: str, tag: str, arm: str, force: bool,
        weights: str = WEIGHTS, reuse_stale: bool = False) -> Path:
    out = HERE / "out" / f"{tag}-{arm}.json"
    stamp = out.with_suffix(".tree.txt")
    here = _tree_id()
    if out.is_file() and not force:
        # ⚠️⚠️ A CACHED ARM IS A CONTROL THAT CANNOT FAIL, and this harness had
        # the trap its own docstring warns about for `scan_eval`: an arm
        # re-run after a CODE CHANGE was silently reused, so the comparison
        # reported "identical" and the change looked inert. Nothing about the
        # output invited suspicion -- which is exactly the failure mode.
        # So a skip must PROVE the arm came from this tree, and refuse when it
        # cannot. Refusing costs a re-run; reusing costs a published number
        # that is wrong, and the asymmetry is not close.
        was = stamp.read_text().strip() if stamp.is_file() else None
        # ⚠️ `here is not None` is load-bearing: without it an unnameable tree
        # (None) would match a missing stamp (None) and skip.
        if here is not None and was == here:
            print(f"  {arm}: exists and was built from THIS tree ({here}) "
                  f"-- skipping")
            return out
        why = ("this tree cannot be named (dirty, or not a git checkout), so "
               "no reuse can be proved" if here is None
               else "no tree stamp beside it" if was is None
               else f"built from {was}, this tree is {here}")
        if not reuse_stale:
            raise SystemExit(
                f"  {arm}: REFUSING to reuse {out.name} -- {why}.\n"
                f"  A cached arm compared against a fresh one reports "
                f"'identical' whatever your change did.\n"
                f"  Re-run it (--force), give this run its own --tag, or "
                f"pass --reuse-stale if you truly mean to.")
        print(f"  {arm}: ⚠️ REUSING STALE {out.name} -- {why} (--reuse-stale)")
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
    # ⚠️ WRITING IS BEST-EFFORT AND NEVER FATAL: a record that cannot name its
    # tree is still a valid arm, and refusing to write one would trade real
    # work for metadata. It simply makes no claim — and the READER refuses on
    # the absence, which is where the information about "am I comparing?"
    # actually is.
    if here is not None:
        stamp.write_text(here + "\n")
    elif stamp.is_file():
        stamp.unlink()          # never let a NEW arm inherit an OLD stamp
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
    ap.add_argument("--reuse-stale", action="store_true",
                    help="reuse an arm this tree did not build. Only ever "
                         "correct when you know the change cannot reach it.")
    ap.add_argument("--weights", default=WEIGHTS,
                    help="scan input needs the hollow graft, not the engraved "
                         "checkpoint -- the staged CLI does no weight routing")
    a = ap.parse_args()
    print(f"{a.tag}: pages {a.pages}")
    for arm in a.arms.split(","):
        run(Path(a.pdf), a.pages, a.tag, arm.strip(), a.force, a.weights,
            a.reuse_stale)
