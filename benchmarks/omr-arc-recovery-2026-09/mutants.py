"""Mutation battery for the stem probes.

⚠️ ONE RED ARM IS NOT A BATTERY -- this repo measured five of six arms
surviving behind one that did not. Every arm is applied to a SNAPSHOT of the
tree, never to the working copy: *a battery that `git checkout`s the files it
mutates is not isolated from anything else running beside it*, which cost a
sibling session its first three-arm run.

⚠️ A BATTERY OF REFUSAL TESTS CAN PASS BY REFUSING EVERYTHING, so arm 0 is a
POSITIVE control in the same class -- it makes every head reachable, and the
tests asserting a stem changes NOTHING must go red.

⚠️ A MISSING ANCHOR IS REPORTED AS AN ERROR, NEVER AS A PASS. The fermata
battery silently mutated a different function because its anchor occurred
twice; every replacement here asserts its anchor occurs EXACTLY once.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS = "tools/omr/tests/test_staged_export.py"
SEL = "Stem or Legacy"

LEG = "tools/omr/export.py"
STG = "tools/omr/staged/export.py"

ARMS = [
    ("0 POSITIVE CONTROL: every head reachable", LEG,
     "xs.extend(x_probes.get(id(det)) or ())",
     "xs.extend([ax, ax + aw])"),
    ("1 probes never built", STG,
     "    probes: Dict[int, List[float]] = {}",
     "    return {}\n    probes: Dict[int, List[float]] = {}"),
    ("2 the canonical offset used as a PAGE offset (no scale)", STG,
     "head_cx_page + (s[0] + s[2] / 2.0 - head_cx_canon) * scale",
     "head_cx_page + (s[0] + s[2] / 2.0 - head_cx_canon)"),
    ("3 any stem in the cell attaches to any head", STG,
     "mine = [s for s in pool if _boxes_overlap(s, head_box)]",
     "mine = list(pool)"),
    ("4 the probe REPLACES the head centre instead of joining it", LEG,
     "            xs = [x_centre]",
     "            xs = [] if (x_probes or {}).get(id(det)) else [x_centre]"),
    ("5 the probes are not passed to the pairing", STG,
     "breaks, voice_of,\n                                          x_probes=x_probes)",
     "breaks, voice_of)"),
    ("6 the counter counts every note, not every stemmed one", STG,
     'counters["arc_notes_reachable_at_a_stem"] += len(x_probes)',
     'counters["arc_notes_reachable_at_a_stem"] += 1'),
    ("7 the stem's LEFT edge stands in for its centre", STG,
     "s[0] + s[2] / 2.0 - head_cx_canon",
     "s[0] - head_cx_canon"),
]


def run_arm(name: str, rel: str, a: str, b: str) -> str:
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        shutil.copytree(ROOT / "tools", tmp / "tools",
                        ignore=shutil.ignore_patterns("training", "annotate",
                                                      "symbol_library", "*.pt"),
                        dirs_exist_ok=True)
        p = tmp / rel
        s = p.read_text()
        if s.count(a) != 1:
            return f"BAD ANCHOR ({s.count(a)} matches)  {name}"
        p.write_text(s.replace(a, b))
        out = subprocess.run(
            [sys.executable, "-m", "pytest", TESTS, "-q", "-k", SEL],
            cwd=tmp, capture_output=True, text=True,
            env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin:/usr/local/bin",
                 "HOME": str(pathlib.Path.home())})
        tail = (out.stdout or "") + (out.stderr or "")
        return ("RED       " if "failed" in tail or "error" in tail.lower()
                else "SURVIVED  <-- A GAP  ") + name
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for arm in ARMS:
        print(run_arm(*arm), flush=True)
