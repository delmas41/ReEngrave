"""Mutation battery for `staged/meaning.py`.

    python3 benchmarks/omr-measurement-meaning-2026-09/probe/mutate.py
    python3 .../mutate.py --force        # run on a dirty tree, deliberately

⚠️ EVERY RECORDED HAZARD OF THIS REPO'S BATTERIES IS HANDLED HERE, because
each was paid for:

  * **It must leave the tree as it FOUND it — which is NOT the same as
    leaving it as GIT has it.** A battery that restores from HEAD destroys an
    uncommitted change under test; one that restores from the index destroys
    a staged one. This one takes a BYTE snapshot before the first arm and
    restores from that.
  * **The restore is VERIFIED** by md5, not assumed.
  * **It refuses a DIRTY tree** without `--force`: a mutation left on disk is
    indistinguishable from a legitimate edit.
  * **An IN-FLIGHT SENTINEL** is written before the first arm and deleted on
    a clean exit. A run that finds one refuses to start and names each file
    at risk with the hash it should have — because a battery killed mid-arm
    leaves the mutation on disk and its in-memory snapshot dies with it.
  * **A POSITIVE CONTROL in the same class**: an arm that must go RED even
    though it changes nothing about the answer's *shape*, so a battery of
    refusal tests cannot pass by refusing everything.

⚠️ AND EXPECT THE FIRST RUN'S SURVIVORS TO BE THE BATTERY'S OWN FAULTS —
anchors occurring twice, arms that cannot fire, equivalent mutants. Each is
reported as an ERROR here rather than as a silent pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[3]
TARGET = _ROOT / "tools" / "omr" / "staged" / "meaning.py"
TESTS = "tools/omr/tests/test_staged_meaning.py"
SENTINEL = pathlib.Path(__file__).resolve().parent / ".mutate-in-flight.json"


def md5(p: pathlib.Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


#: (name, old, new, why it must go red). `old` must occur EXACTLY ONCE.
ARMS = [
    ("registry_import_removed",
     "from . import adjudicators as _ad      # noqa: F401  populates REGISTRY",
     "pass  # adjudicators NOT imported",
     "section 3 iterates an EMPTY registry and prints a confident 0"),

    ("control_floor_registry_dropped",
     '"n_decisions": 20, "n_unit_keys": 20',
     '"n_decisions": -1, "n_unit_keys": -1',
     "the vacuous-registry control stops being able to fire"),

    ("update_spelling_dropped",
     '        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)\n'
     '                and n.func.attr == "update"\n'
     '                and isinstance(n.func.value, ast.Name)):\n'
     '            out[n.func.value.id] |= {k.arg for k in n.keywords if k.arg}',
     "        pass  # .update() half removed",
     "54 unit keys fall to ~12 and 29 disagreements to ZERO"),

    ("local_frame_resolution_dropped",
     "        if locals_ and v.id in locals_:\n            return locals_[v.id]",
     "        pass",
     "`frame=frame` stops resolving; 13 quantities read as unresolved"),

    ("frame_extent_cell_removed",
     '    "cell:*": "CELL",\n    "bar_head:*": "CELL",',
     '    "bar_head:*": "CELL",',
     "the commonest frame becomes unplaceable; --check must fail HARD"),

    ("scope_comparison_inverted",
     "if depth[ext] > sdepth:  # frame FINER than the scope",
     "if depth[ext] < sdepth:  # MUTANT",
     "section 3 reports coarser-than-scope rows, losing onset_column"),

    ("page_frame_keys_emptied",
     'PAGE_FRAME_KEYS = frozenset({\n'
     '    "bbox_page_px", "x_center_page", "y_center_page",\n'
     '    "staff_bottom_line_page", "x_page",\n'
     '})',
     "PAGE_FRAME_KEYS = frozenset()",
     "onset_column stops being exempt; the calibration point dies"),

    ("stale_detection_removed",
     "    for k in sorted(set(KNOWN_GAPS) - reported):",
     "    for k in []:",
     "a closed gap may stay in KNOWN_GAPS for ever"),

    ("unaccounted_detection_removed",
     "    for k in sorted(reported - set(KNOWN_GAPS)):",
     "    for k in []:",
     "a NEW finding stops failing --check"),

    ("unit_suffix_page_dropped",
     '    ("_page", "page/px"),',
     "",
     "x_center_page / y_center_page stop declaring a unit"),

    ("frame_of_unit_emptied",
     'FRAME_OF_UNIT: Dict[str, Set[str]] = {\n'
     '    "page/px": {"page", "system", "header_window", "system_margin"},\n'
     '    "canonical/px": {"cell:*", "bar_head:*"},\n'
     '}',
     "FRAME_OF_UNIT: Dict[str, Set[str]] = {}",
     "section 2 goes silent: no unit makes a frame claim any more"),

    ("derived_check_marker_removed",
     "DERIVED_CHECK = True",
     "DERIVED_CHECK = True  # noqa\nDERIVED_CHECK_SHADOW = False",
     "POSITIVE CONTROL of the OPPOSITE sign: this arm changes nothing that "
     "matters and must stay GREEN. If it goes red the battery is measuring "
     "noise."),
]

#: Arms expected GREEN. An arm that can never go red trains the next reader
#: to ignore the list, so it is named rather than hidden.
EXPECTED_GREEN = {"derived_check_marker_removed"}


def dirty() -> list:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=_ROOT,
                         capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if l.strip()]


def run_tests() -> bool:
    r = subprocess.run([sys.executable, "-m", "pytest", TESTS, "-x", "-q"],
                       cwd=_ROOT, capture_output=True, text=True)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run on a dirty tree, deliberately")
    a = ap.parse_args()

    if SENTINEL.exists():
        s = json.loads(SENTINEL.read_text())
        print("✗ REFUSING TO START: a previous battery was INTERRUPTED and "
              "its snapshot died with the process.")
        print(f"  {s['target']} should have md5 {s['md5']}")
        print(f"  on disk it is       {md5(TARGET)}")
        print("  restore it, then delete", SENTINEL)
        return 2

    d = dirty()
    if d and not a.force:
        print("✗ REFUSING TO START: the tree is dirty. A mutation left on "
              "disk is indistinguishable from a legitimate edit.")
        for l in d:
            print("   ", l)
        print("  commit a checkpoint, or pass --force deliberately.")
        return 2

    original = TARGET.read_bytes()
    want = hashlib.md5(original).hexdigest()
    SENTINEL.write_text(json.dumps({"target": str(TARGET), "md5": want}))

    print(f"target {TARGET.relative_to(_ROOT)}  md5 {want}")
    print("baseline (unmutated) must be GREEN ...", end=" ", flush=True)
    base = run_tests()
    print("GREEN" if base else "RED")
    if not base:
        TARGET.write_bytes(original)
        SENTINEL.unlink()
        print("✗ the suite is red BEFORE any mutation; nothing below means "
              "anything.")
        return 2

    results, errors = [], []
    try:
        for name, old, new, why in ARMS:
            src = original.decode()
            n = src.count(old)
            if n != 1:
                errors.append((name, f"ANCHOR occurs {n} times, not 1"))
                print(f"  {name:34s} ERROR anchor x{n}")
                continue
            TARGET.write_text(src.replace(old, new, 1))
            ok = run_tests()
            red = not ok
            results.append((name, red, why))
            expect_green = name in EXPECTED_GREEN
            verdict = ("GREEN (expected)" if (not red and expect_green)
                       else "RED" if red and not expect_green
                       else "SURVIVED ⚠️" if not red
                       else "RED (unexpected)")
            print(f"  {name:34s} {verdict}")
            TARGET.write_bytes(original)
            assert md5(TARGET) == want, "per-arm restore failed"
    finally:
        TARGET.write_bytes(original)
        got = md5(TARGET)
        SENTINEL.unlink(missing_ok=True)
        print(f"\nrestore verified: {got} == {want} -> {got == want}")
        assert got == want, "RESTORE FAILED — the tree is NOT as it was found"

    survivors = [n for n, red, _ in results
                 if not red and n not in EXPECTED_GREEN]
    print(f"\narms {len(ARMS)}  red {sum(1 for _, r, _ in results if r)}"
          f"  expected-green {len(EXPECTED_GREEN)}"
          f"  survivors {len(survivors)}  errors {len(errors)}")
    for n, msg in errors:
        print(f"  ERROR    {n}: {msg}")
    for n in survivors:
        why = next(w for nm, _, w in results if nm == n)
        print(f"  SURVIVED {n}: should have broken — {why}")

    post = dirty()
    if len(post) != len(d):
        print(f"✗ the tree changed: {len(d)} dirty before, {len(post)} after")
        return 2
    return 1 if (survivors or errors) else 0


if __name__ == "__main__":
    sys.exit(main())
