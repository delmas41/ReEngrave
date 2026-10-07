"""Mutation battery for the stem-attribution PROBES.

⚠️ WHY THE PROBES. This lane changed nothing under `tools/`: it delivers a set
of measurements and a refusal. So the thing whose correctness the conclusion
rests on is the instrument, and the instrument is what must be mutated.

Every rule this repo has paid for is honoured:

  * a BYTE snapshot is taken before arm 1, restores come from it, and each
    restore is VERIFIED by hash -- *a mutation battery must leave the tree as
    it FOUND it, which is not the same as leaving it as GIT has it*;
  * an IN-FLIGHT SENTINEL is written before the first arm and removed on a
    clean exit, so an interrupted battery cannot leave a mutation on disk
    looking like an ordinary edit;
  * a POSITIVE CONTROL in the same class runs FIRST -- the unmutated tree must
    be GREEN, or every red below means nothing;
  * ⚠️⚠️ THE JUDGE READS FAILED TEST IDS, NEVER PYTEST'S SUMMARY LINE. That
    line ends " in 0.57s" and differs between two runs of an unmutated tree;
    two batteries in this repo were measuring nothing for exactly that reason.
    An arm is RED only when the test NAMED for it is in the failed set;
  * `PYTHONDONTWRITEBYTECODE=1` -- `shutil.copy2` preserves mtime, so a `.pyc`
    from one arm satisfies Python's (mtime, size) check in a later one and it
    imports UNMUTATED code, reporting NOT RED indistinguishably from a gap;
  * a dirty tree is REFUSED without `--force`.

    python3 benchmarks/omr-stem-attribution-2026-09/mutate.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROBE = HERE / "probe"
TESTS = HERE / "test_probes.py"
SENTINEL = HERE / ".mutation-in-flight"

#: (arm name, file, exact source to replace, replacement, test that must go RED)
ARMS = [
    ("overlap: touching boundary becomes strict",
     PROBE / "reach.py",
     "return (ax <= bx + bw and ax + aw >= bx\n"
     "            and ay <= by + bh and ay + ah >= by)",
     "return (ax < bx + bw and ax + aw > bx\n"
     "            and ay < by + bh and ay + ah > by)",
     "test_the_touching_boundary_is_INCLUDED_by_both"),

    ("overlap: x test loses its width term",
     PROBE / "reach.py",
     "return (ax <= bx + bw and ax + aw >= bx",
     "return (ax <= bx and ax + aw >= bx",
     "test_agrees_on_a_grid_of_boxes_including_the_touching_case"),

    ("overlap: y test always true",
     PROBE / "reach.py",
     "and ay <= by + bh and ay + ah >= by)",
     "and True)",
     "test_a_pair_separated_in_Y_ONLY_is_rejected_by_both"),

    ("cell_of: takes one segment too few",
     PROBE / "reach.py",
     'return "cell/" + "/".join(parts[1:5])',
     'return "cell/" + "/".join(parts[1:4])',
     "test_a_glyph_subject_maps_to_its_cell"),

    ("cell_of: invents a cell for a staff subject",
     PROBE / "reach.py",
     '    if parts[0] == "cell":\n        return subject\n    return ""',
     '    if parts[0] == "cell":\n        return subject\n    return subject',
     "test_a_staff_subject_has_no_cell_and_says_so"),

    ("end_gap: measures from the FAR end",
     PROBE / "reach.py",
     "    return min(abs(hcy - stroke[1]),\n"
     "               abs(hcy - (stroke[1] + stroke[3]))) / hh",
     "    return max(abs(hcy - stroke[1]),\n"
     "               abs(hcy - (stroke[1] + stroke[3]))) / hh",
     "test_a_head_at_the_head_EDGE_scores_a_half"),

    ("end_gap: normalised by the STROKE, reintroducing the frac defect",
     PROBE / "reach.py",
     "    hh = max(head[3], 1e-6)\n"
     "    hcy = head[1] + head[3] / 2.0",
     "    hh = max(stroke[3], 1e-6)\n"
     "    hcy = head[1] + head[3] / 2.0",
     "test_it_is_SCALE_FREE_in_the_stroke_length"),

    ("chord_shadow: admits strokes carrying several heads",
     PROBE / "chord_shadow.py",
     "            if len(members) != 1:\n                continue",
     "            if len(members) < 1:\n                continue",
     "test_a_stroke_carrying_TWO_heads_is_not_reported_at_all"),

    ("chord_shadow: the x window is unbounded",
     PROBE / "chord_shadow.py",
     "if (abs(cx2 - hcx) <= max(hb[2], b2[2])",
     "if (abs(cx2 - hcx) <= 1e9",
     "test_a_head_far_away_in_x_is_NOT_a_shadow"),

    ("chord_shadow: the y span is not checked",
     PROBE / "chord_shadow.py",
     "and sb[1] - hh <= cy2 <= sb[1] + sb[3] + hh):",
     "and True):",
     "test_a_head_outside_the_strokes_y_span_is_NOT_a_shadow"),

    ("chord_shadow: never records a shadow",
     PROBE / "chord_shadow.py",
     "                    shadows.append(",
     "                    _ = (",
     "test_a_partner_at_the_same_x_inside_the_span_is_found"),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def failed_ids(env) -> tuple[int, set[str]]:
    """Run the suite; return (exit code, the set of FAILED test names).

    ⚠️ The judge is this set, never the summary line.
    """
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS), "-q", "--no-header",
         "-rf", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(ROOT), env=env)
    ids = set()
    for line in r.stdout.splitlines():
        m = re.match(r"FAILED\s+\S+::(\S+?)::(\S+)", line) or \
            re.match(r"FAILED\s+\S+::(\S+)", line)
        if m:
            ids.add(m.group(m.lastindex))
    return r.returncode, ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="run despite a dirty tree")
    ap.add_argument("--out", default=str(HERE / "out" / "mutation-battery.json"))
    a = ap.parse_args()

    if SENTINEL.exists():
        print("REFUSING: an in-flight sentinel is present. A previous battery "
              "was interrupted and may have left a mutation on disk:\n"
              f"  {SENTINEL.read_text()}", file=sys.stderr)
        return 2

    files = sorted({str(f) for _n, f, _o, _r, _t in ARMS})
    dirty = subprocess.run(["git", "status", "--porcelain"] + files,
                           capture_output=True, text=True,
                           cwd=str(ROOT)).stdout.strip()
    if dirty and not a.force:
        print("REFUSING: the files this battery mutates are dirty; commit "
              f"first or pass --force.\n{dirty}", file=sys.stderr)
        return 2

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    # ── POSITIVE CONTROL, FIRST ──────────────────────────────────────────
    code, ids = failed_ids(env)
    if code != 0 or ids:
        print(f"REFUSING: the unmutated tree is not green "
              f"(exit {code}, failed {sorted(ids)}). Every red below would "
              f"mean nothing.", file=sys.stderr)
        return 2
    print("POSITIVE CONTROL: unmutated tree is GREEN\n")

    snap = Path(tempfile.mkdtemp(prefix="stem-attr-battery-"))
    originals = {}
    for f in files:
        p = Path(f)
        dst = snap / p.name
        shutil.copy2(p, dst)
        originals[f] = (sha(p), dst)
    SENTINEL.write_text(json.dumps(
        {"snapshot": str(snap),
         "files": {f: h for f, (h, _d) in originals.items()}}, indent=1))

    results, red = [], 0
    try:
        for name, path, old, new, test in ARMS:
            src = path.read_text()
            if src.count(old) != 1:
                results.append({"arm": name, "status": "BAD ANCHOR",
                                "occurrences": src.count(old)})
                print(f"  BAD ANCHOR  {name} ({src.count(old)} occurrences)")
                continue
            path.write_text(src.replace(old, new))
            code, ids = failed_ids(env)
            is_red = test in ids
            red += 1 if is_red else 0
            results.append({"arm": name, "file": path.name, "expects": test,
                            "status": "RED" if is_red else "SURVIVED",
                            "failed": sorted(ids)})
            print(f"  {'RED     ' if is_red else 'SURVIVED'}  {name}"
                  + ("" if is_red else f"   (failed: {sorted(ids)})"))
            # restore from the SNAPSHOT, and verify
            shutil.copy2(originals[str(path)][1], path)
            assert sha(path) == originals[str(path)][0], \
                f"restore of {path} did not reproduce the snapshot"
    finally:
        for f, (h, dst) in originals.items():
            shutil.copy2(dst, Path(f))
            if sha(Path(f)) != h:
                print(f"⚠️ RESTORE FAILED for {f}", file=sys.stderr)
        SENTINEL.unlink(missing_ok=True)
        shutil.rmtree(snap, ignore_errors=True)

    code, ids = failed_ids(env)
    clean = (code == 0 and not ids)
    print(f"\n{red} of {len(ARMS)} arms RED; "
          f"tree restored and green: {clean}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(
        {"arms": len(ARMS), "red": red, "restored_green": clean,
         "results": results}, indent=1))
    return 0 if (red == len(ARMS) and clean) else 1


if __name__ == "__main__":
    raise SystemExit(main())
