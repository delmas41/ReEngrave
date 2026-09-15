#!/usr/bin/env python3
"""A MUTATION BATTERY OVER THE INSTRUMENTS, because the instruments ARE the
deliverable of this job.

This session ships no rule — it ships a measured REFUSAL — so there is no
adjudicator to mutate. What there is, is three probes whose zeros and whose
`--check` exits carry the whole argument, and CLAUDE.md's own standard applies
to them unchanged: *a control that cannot fail is worse than no check*, and
*one red arm is not a battery*.

Each arm breaks one guard and asserts the probe NOTICES — by changing its exit
code, or by moving a number it reports. An arm that leaves both unchanged is a
SURVIVOR and is reported as one.

⚠️ **POSITIVE CONTROL FIRST.** `POSITIVE_unmutated` runs the same command with
no mutation and asserts the expected baseline. Without it every "the arm was
caught" reading is worthless, because a probe that is broken to begin with
fails every arm for free.

⚠️ **THE TREE IS RESTORED FROM A BYTE SNAPSHOT TAKEN BEFORE THE FIRST ARM, AND
THE RESTORE IS VERIFIED** — never from git. CLAUDE.md records a battery that
`git checkout`ed its subject when HEAD did not have the function under test and
destroyed the change it had just certified:

    A mutation battery must leave the tree as it FOUND it — which is not the
    same as leaving it as GIT has it.

    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/mutation_battery.py
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

SCORE_FRAMES = HERE / "probe" / "score_frames.py"
OPENING = HERE / "probe" / "where_the_opening_sits.py"
REACH = HERE / "arbiter_reach.py"

#: Two pages: one CONTINUATION page (every answer false) and the MOVEMENT
#: START (a real printed `C` on every staff). Both are needed — the premise
#: check can only fire on the second, and the false populations only exist on
#: the first.
FAST = ["--only", "beet5lit-p056", "brahms1-p045"]


def _snapshot(paths):
    return {p: p.read_bytes() for p in paths}


def _restore(snap):
    for p, data in snap.items():
        p.write_bytes(data)
    for p, data in snap.items():
        got = p.read_bytes()
        if hashlib.sha256(got).hexdigest() != hashlib.sha256(data).hexdigest():
            raise SystemExit(f"RESTORE FAILED for {p} — the tree is NOT as it "
                             f"was found. Fix by hand before doing anything.")


def _run(cmd, cwd=ROOT):
    proc = subprocess.run([sys.executable, "-u"] + cmd, cwd=cwd,
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def _patch(path, old, new):
    src = path.read_text()
    if src.count(old) != 1:
        raise SystemExit(f"BAD ANCHOR in {path.name}: {src.count(old)} "
                         f"occurrences of {old!r} (need exactly 1). "
                         f"Reported as an ERROR, never as a silent pass.")
    path.write_text(src.replace(old, new))


# ── the arms ────────────────────────────────────────────────────────────────
#
# (name, file, old, new, expectation) — `expectation(rc, out)` returns True
# when the probe NOTICED the mutation.

def _dead(rc, out):
    return rc != 0 and ("DEAD" in out or "PREMISE BROKEN" in out)


def _premise_fired(rc, out):
    return "PREMISE BROKEN" in out


ARMS = [
    ("score_frames: the reader never answers", SCORE_FRAMES,
     "    ranked = trace.get(\"scores\") or []",
     "    ranked = []",
     _dead),
    ("score_frames: the positive control is never stamped", SCORE_FRAMES,
     "    if template is None:\n        return None",
     "    if True:\n        return None",
     _dead),
    ("score_frames: the premise check can never fire", SCORE_FRAMES,
     "        voted = vote_system_time_signature(reads, n_staves=len(reads))",
     "        voted = None",
     lambda rc, out: not _premise_fired(rc, out)),
    ("score_frames: --only silently matches nothing", SCORE_FRAMES,
     "        pages = [p for p in PAGES if p[0] in set(args.only)]",
     "        pages = []",
     _dead),
    ("score_frames: the bar-head window is the whole cell", SCORE_FRAMES,
     "    width = int(round(spaces * spacing))",
     "    width = 10 ** 6",
     lambda rc, out: "head_last" in out and _head_last_rate(out) > 0.10),
    ("opening sweep: the reader never reads the printed meter", OPENING,
     "            found = locate_time_signature(crop)",
     "            found = None",
     _dead),
    ("arbiter_reach: the artefact grep loses its positive control", REACH,
     "        if '\"raw\"' in text:",
     "        if False:",
     lambda rc, out: "the positive control is ZERO" in out),
    ("arbiter_reach: both counts read one quantity", REACH,
     '                   r"n_staves_spoke[=:]\\s*len\\((\\w+)\\)"),',
     '                   r\'"staves_reading_it":\\s*sorted\\((\\w+)\\)\'),',
     lambda rc, out: "the 'two readers' claim is FALSE" in out),
]


def _head_last_rate(out):
    for line in out.splitlines():
        if line.strip().startswith("head_last"):
            for tok in line.split():
                if tok.startswith("(") and tok.endswith("%)"):
                    try:
                        return float(tok.strip("()%")) / 100.0
                    except ValueError:
                        return 0.0
    return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "out" / "mutation-battery.log"))
    args = ap.parse_args()

    files = sorted({SCORE_FRAMES, OPENING, REACH})
    snap = _snapshot(files)
    lines = []

    def say(s):
        print(s, flush=True)
        lines.append(s)

    cmds = {
        SCORE_FRAMES: ["benchmarks/omr-meter-cautionary-arbiter-2026-09/probe/"
                       "score_frames.py", "--check"] + FAST
                      + ["--out", "/tmp/mb-score-frames.json"],
        OPENING: ["benchmarks/omr-meter-cautionary-arbiter-2026-09/probe/"
                  "where_the_opening_sits.py", "--check",
                  "--out", "/tmp/mb-opening.json"],
        REACH: ["benchmarks/omr-meter-cautionary-arbiter-2026-09/"
                "arbiter_reach.py", "--check",
                "--out", "/tmp/mb-reach.json"],
    }

    # ── POSITIVE CONTROL ────────────────────────────────────────────────────
    say("POSITIVE_unmutated — the baseline every arm is judged against")
    ok = True
    for path, cmd in cmds.items():
        rc, out = _run(cmd)
        note = ""
        if path is SCORE_FRAMES:
            good = _premise_fired(rc, out) and "DEAD" not in out
            note = (f"premise fired={_premise_fired(rc, out)} "
                    f"head_last rate={_head_last_rate(out):.2%}")
        elif path is OPENING:
            good = rc == 0 and "CHECK OK" in out
        else:
            good = rc == 3 and "reach ZERO" in out
        ok = ok and good
        verdict = "OK" if good else "⚠️ NOT THE EXPECTED BASELINE"
        say(f"    {path.name:<28} rc={rc} {verdict} {note}")
    if not ok:
        _restore(snap)
        say("BASELINE WRONG — every arm below would be meaningless. Stopping.")
        pathlib.Path(args.out).write_text("\n".join(lines) + "\n")
        return 2

    survivors = []
    for i, (name, path, old, new, expect) in enumerate(ARMS, 1):
        try:
            _patch(path, old, new)
        except SystemExit as exc:
            _restore(snap)
            say(f"{i:>2}. {name}\n    {exc}")
            survivors.append(name + " (BAD ANCHOR)")
            continue
        rc, out = _run(cmds[path])
        caught = bool(expect(rc, out))
        _restore(snap)
        say(f"{i:>2}. {'RED  ' if caught else 'SURVIVED'} {name}   (rc={rc})")
        if not caught:
            survivors.append(name)

    _restore(snap)
    say(f"\n{len(ARMS)} arms, {len(ARMS) - len(survivors)} red, "
        f"{len(survivors)} survivors")
    for s in survivors:
        say(f"    SURVIVOR: {s}")
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text("\n".join(lines) + "\n")
    return 1 if survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
