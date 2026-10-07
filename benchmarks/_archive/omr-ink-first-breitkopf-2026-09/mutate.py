"""Mutation battery for `probe_ink_first_breitkopf.py`.

⚠️ A CONTROL CAN ONLY BE MUTATION-TESTED IN A STATE WHERE IT FAILS, which is
this repo's own correction from `omr-vertical-runs-page-2026-09`: three of that
battery's first-run survivors were controls sitting at their ceiling, where
mutating them changed nothing. So every arm here names the OBSERVABLE it
expects to move, and an arm is RED only when that observable actually moves --
never merely when the exit code changes.

⚠️ IT RUNS ON THE SMALL COMMITTED PILOT RECORD, not the 460 MB one: the arms
test the probe's logic, and the logic does not know how many pages it was
given.

THREE PROPHYLACTICS, all three paid for by this repo:
  * a byte snapshot taken BEFORE the first arm, restored and VERIFIED BY HASH,
    because `git checkout` restores what GIT has and not what the tree had;
  * an in-flight SENTINEL, because a battery killed mid-arm leaves the
    mutation on disk and `git status` cannot tell it from a real edit;
  * `PYTHONDONTWRITEBYTECODE=1` in every arm, because `shutil.copy2` preserves
    mtime and a stale `.pyc` then satisfies Python's (mtime, size) check --
    the arm imports the UNMUTATED code and reports NOT RED.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PROBE = os.path.join(HERE, "probe_ink_first_breitkopf.py")
SNAP = os.path.join(HERE, ".probe.snapshot")
SENTINEL = os.path.join(HERE, ".battery-in-flight")
PILOT = os.path.join(
    ROOT, "benchmarks/omr-ink-first-2026-09/out/brahms1-breitkopf-p2.gather.json")

#: (name, anchor, replacement, observable[, extra-args])
#: `observable` is a substring-keyed LINE of the probe's output; an arm is RED
#: when that line's text changes (or when the REFUSED/DEAD line appears or
#: disappears).
#:
#: ⚠️⚠️ THE LAST FIELD IS THE BATTERY'S OWN CORRECTION. Two arms SURVIVED the
#: first run and neither was a probe defect: the document-identity gate and the
#: empty-side DEAD guard were both sitting at their CEILING on the pilot
#: record -- class agreement is already 22/22 and neither side is empty, so
#: deleting either changed nothing. A control can only be mutation-tested in a
#: state where it FAILS, so those two arms now run against `--wrong-join` and
#: `--drop-junk`, the probe's two fault-reproducing positive controls.
ARMS = [
    ("ink box read as [x,y,w,h]",
     "    x0, y0, x1, y1 = (float(v) for v in b)\n"
     "    if not (x1 > x0 and y1 > y0):",
     "    x0, y0, x1, y1 = (float(b[0]), float(b[1]),\n"
     "                      float(b[0]) + float(b[2]), float(b[1]) + float(b[3]))\n"
     "    if not (x1 > x0 and y1 > y0):",
     "B1 ink corners reproduce width_spaces"),

    ("box-convention control loses its teeth",
     "        wrong_errs.append(abs(x1 / sp - float(d[\"width_spaces\"])))",
     "        wrong_errs.append(abs((x1 - x0) / sp - float(d[\"width_spaces\"])))",
     "control has TEETH"),

    ("document-identity gate accepts any class",
     "        if want is None or got == want:",
     "        if True:",
     "REFUSED", ("--wrong-join",)),

    ("attribution ignores the piece's fill",
     "            w = ia * max(fill, 1e-6) if attribution == \"fill\" else ia",
     "            w = ia",
     "MERGE: piece extent / box extent"),

    ("the primary piece is the SMALLEST overlap, not the largest",
     "    touching.sort(key=lambda t: -t[0])",
     "    touching.sort(key=lambda t: t[0])",
     "MERGE: piece extent / box extent"),

    ("the join is made in the CANONICAL frame, mixing conventions",
     "def page_corners(row):",
     "def page_corners(row):\n"
     "    if row.get('quantity') == 'ink':\n"
     "        b = row['detail']['ink_bbox_canonical']\n"
     "        return tuple(float(v) for v in b)",
     "MERGE: piece extent / box extent"),

    ("AUC always reports the null",
     "    if not pos or not neg:\n        return float(\"nan\")\n    s = 0.0",
     "    if not pos or not neg:\n        return float(\"nan\")\n    return 0.5\n    s = 0.0",
     "BOX ALONE: box width (spaces)"),

    ("the SPECK stratum swallows everything",
     "    if big < speck_cut:",
     "    if big < speck_cut * 100:",
     "SPECK"),

    ("the vertical stratum uses invented bounds, not the shipped ones",
     "    if (h_sp >= STEM_MIN_H_SPACES and w_sp <= STEM_MAX_W_SPACES):",
     "    if (h_sp >= 0.1 and w_sp <= 99.0):",
     "VERTICAL"),

    ("cannot_tell is counted as a confirmed notehead",
     "REAL = {\"stem_printed_down\", \"stem_printed_up\", \"no_stem_printed\"}",
     "REAL = {\"stem_printed_down\", \"stem_printed_up\", \"no_stem_printed\",\n"
     "        \"cannot_tell\"}",
     "SEPARATION SET"),

    ("the DEAD guard on an empty separation side is removed",
     "    if not pos or not neg:\n        P(\"  DEAD: one side of the separation is empty on this record.\")",
     "    if False:\n        P(\"  DEAD: one side of the separation is empty on this record.\")",
     "DEAD: one side of the separation", ("--drop-junk",)),
]

#: ⚠️ THE TERMINAL REFUSALS, SPELLED OUT. A bare `"DEAD" in output` test broke
#: the moment the probe grew a WITHIN-STRATUM section that prints
#: `-- too few, DEAD` per bucket on a perfectly healthy run: the battery's own
#: positive control then reported the unmutated probe as refusing, and every
#: arm below it as meaningless. A guard keyed on a substring of ordinary
#: output is not a guard.
TERMINAL = ("REFUSED: a control failed",
            "DEAD: one side of the separation",
            "DEAD: not one adjudicated subject",
            "DEAD: this record carries NO ink rows")


def refused(text):
    return any(m in text for m in TERMINAL)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def run(extra=()):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run(
        [sys.executable, PROBE, "--record", PILOT, *extra],
        cwd=ROOT, capture_output=True, text=True, env=env)
    return p.stdout + p.stderr


def lines_for(text, key):
    return [ln for ln in text.splitlines() if key in ln]


def main():
    if os.path.exists(SENTINEL):
        print("REFUSED: an earlier battery did not finish. The tree may hold "
              f"a mutation. Expected probe sha in {SENTINEL}; compare it "
              "against the file before deleting the sentinel.")
        return 2
    shutil.copyfile(PROBE, SNAP)
    before = sha(PROBE)
    with open(SENTINEL, "w") as f:
        f.write(before + "\n" + PROBE + "\n")

    try:
        base = run()
        if refused(base):
            print("POSITIVE CONTROL FAILED: the unmutated probe refuses on the "
                  "pilot record, so no arm below means anything.")
            print(base[-2000:])
            return 2
        print(f"positive control: unmutated probe runs, "
              f"{len(base.splitlines())} lines of output")
        # ⚠️ the two fault-reproducing arms must themselves be shown to reach
        # their failing state BEFORE any mutation, or their arms are vacuous.
        wj = run(("--wrong-join",))
        dj = run(("--drop-junk",))
        print(f"positive control: --wrong-join REFUSES  "
              f"{'yes' if refused(wj) else 'NO -- arm is vacuous'}")
        print(f"positive control: --drop-junk reaches DEAD "
              f"{'yes' if refused(dj) else 'NO -- arm is vacuous'}\n")
        baselines = {(): base,
                     ("--wrong-join",): wj,
                     ("--drop-junk",): dj}

        red = 0
        with open(SNAP) as f:
            src = f.read()
        for arm in ARMS:
            name, anchor, repl, key = arm[:4]
            extra = arm[4] if len(arm) > 4 else ()
            n = src.count(anchor)
            if n != 1:
                print(f"  BAD ANCHOR ({n} matches): {name}")
                continue
            with open(PROBE, "w") as f:
                f.write(src.replace(anchor, repl, 1))
            got = run(extra)
            ref = baselines[tuple(extra)]
            b_obs, g_obs = lines_for(ref, key), lines_for(got, key)
            moved = b_obs != g_obs
            print(f"  [{'RED ' if moved else 'SURVIVED'}] {name}")
            if not moved:
                print(f"        observable {key!r} did not move:")
                for ln in b_obs[:2]:
                    print(f"          base: {ln.strip()[:100]}")
                for ln in g_obs[:2]:
                    print(f"          arm : {ln.strip()[:100]}")
            red += bool(moved)
        print(f"\n{red}/{len(ARMS)} RED, {len(ARMS)-red} survived")
    finally:
        shutil.copyfile(SNAP, PROBE)
        after = sha(PROBE)
        ok = after == before
        print(f"restore {'VERIFIED' if ok else 'FAILED'} "
              f"({before[:12]} -> {after[:12]})")
        if ok:
            os.remove(SENTINEL)
            os.remove(SNAP)
    return 0


if __name__ == "__main__":
    sys.exit(main())
