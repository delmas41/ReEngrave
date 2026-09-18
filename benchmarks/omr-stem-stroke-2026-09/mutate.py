"""THE MUTATION BATTERY for the column-profile stroke reader.

One red arm is not a battery. Every assertion in
`tools/omr/tests/test_line_detection_stroke_reader.py` is meant to fail when
the thing it names is broken, and the only way to know is to break each one.

⚠️⚠️ THE RESTORE RULES, ALL THREE EARNED BY THIS REPO THE HARD WAY.

1. **A battery must leave the tree as it FOUND it — which is not the same as
   leaving it as source control has it.** A battery that restores from HEAD
   destroys any uncommitted change, and CLAUDE.md records one doing exactly
   that to the change it had just certified: ten arms went red, the file came
   back from HEAD, HEAD did not have the function, and the tests that had
   just passed were testing code no longer on disk. So this takes a BYTE
   SNAPSHOT before the first arm and restores from that, then VERIFIES the
   restore by hash.

2. **An INTERRUPTED battery obeys neither.** A snapshot held only in memory
   dies with the process, leaving a mutation on disk that looks exactly like
   a legitimate edit — found once by a later probe reporting an impossible
   zero, not by review. So the snapshot is written to DISK and an in-flight
   SENTINEL is written beside it; a run that finds a sentinel refuses to
   start and names each file at risk with the hash it should have.

3. **A dirty tree is refused without `--force`**, because a battery cannot
   tell its own mutation from an edit someone else is mid-way through.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAP = HERE / "out" / ".mutate-snapshot"
SENTINEL = HERE / "out" / ".mutate-in-flight.json"

TARGET = ROOT / "tools" / "omr" / "line_detection.py"
TESTS = "tools/omr/tests/test_line_detection_stroke_reader.py"

# (name, file, find, replace, the test that MUST go red)
ARMS = [
    ("the flag defaults ON", TARGET,
     'os.environ.get(STEM_STROKE_ENV, "0")',
     'os.environ.get(STEM_STROKE_ENV, "1")',
     "test_the_flag_is_OFF_by_default"),
    ("the OFF test becomes a DENY-list", TARGET,
     'in (\n        "1", "true", "yes", "on")',
     'not in ("0", "", "off", "no", "false")',
     "test_only_an_explicit_ON_word_turns_it_on"),
    # WARNING: RE-AIMED. This arm first named `test_the_flag_is_OFF_by_
    # default`, which only calls `stem_stroke_enabled()` and therefore cannot
    # see `detect_stems` ignoring it. A test named for a hazard it does not
    # reach is this repo's best-camouflaged fault: the NAME is what a reviewer
    # trusts and the only part they cannot check by reading.
    ("the reader runs regardless of the flag", TARGET,
     "    if enable_stroke_reader:",
     "    if True:",
     "test_flag_off_is_IDENTICAL_and_flag_on_DIFFERS"),
    ("the reader never runs", TARGET,
     "    if enable_stroke_reader:",
     "    if False:",
     "test_flag_off_is_IDENTICAL_and_flag_on_DIFFERS"),
    ("the reader SUBSTITUTES instead of adding", TARGET,
     "            if any(_boxes_overlap(band, s) for s in out):\n"
     "                continue\n            out.append(band)",
     "            out = [band]",
     "test_flag_off_is_IDENTICAL_and_flag_on_DIFFERS"),
    ("a band cut by the width cap is ADMITTED", TARGET,
     "        if h < min_h or h > max_h or w > max_w:",
     "        if h < min_h or h > max_h:",
     "test_a_TALL_wide_block_yields_no_band"),
    ("the column extent is FIRST-TO-LAST, not the longest run", TARGET,
     "    has = best > 0\n    bot = bend\n    top = bend - best + 1",
     "    has = m.any(axis=0)\n    bot = h_px - 1 - np.argmax(m[::-1], axis=0)\n"
     "    top = np.argmax(m, axis=0)",
     "test_a_column_holding_TWO_runs_takes_its_LONGEST"),
    ("the EDGE filter is dropped", TARGET,
     "        if x0 < edge_margin or x0 + w > cell_w - edge_margin:",
     "        if False:",
     "test_a_stroke_at_the_CELL_EDGE_is_refused"),
    ("the height CAP is dropped", TARGET,
     "        if h < min_h or h > max_h or w > max_w:",
     "        if h < min_h or w > max_w:",
     "test_a_stroke_too_TALL_is_refused"),

    # WARNING: A LONGER ANCHOR. `if h / max(1, w) < 3.0:` occurs TWICE in
    # line_detection.py -- once in `detect_stems`' component loop and once in
    # the profile -- so the short anchor mutated whichever came first. The
    # same fault CLAUDE.md records the fermata battery committing.
    ("the ASPECT filter is dropped", TARGET,
     "        if h / max(1, w) < 3.0:\n            continue\n        out.append("
     "LineDetection(\n            smufl_name=\"stem\", category=\"stem\",",
     "        if False:\n            continue\n        out.append("
     "LineDetection(\n            smufl_name=\"stem\", category=\"stem\",",
     "test_a_wide_block_yields_no_band"),
    ("the agree tolerance is ignored (all columns band together)", TARGET,
     "            if d > agree_px:",
     "            if False:",
     "test_two_ADJACENT_strokes_at_different_heights_are_two_bands"),

]

# ⚠️⚠️ TWO ARMS ARE HELD OUT AS **EQUIVALENT MUTANTS**, NAMED HERE RATHER
# THAN LEFT IN THE LIST, because an arm that can never go red trains the next
# reader to ignore every other one.
#
#   * *the height FLOOR is dropped* (`h < min_h`). The profile's `long_mask`
#     is an opening by `(1, min_h)`, so no run shorter than the floor is in
#     the mask at all. The opening IS the floor, enforced upstream.
#   * *the profile skips the vertical opening* (`long_mask = ink`). The
#     mirror of the same identity: with raw ink every inked column enters the
#     profile, but a column's LONGEST RUN is unchanged for runs at or above
#     the floor and every shorter one is then refused by `h < min_h`.
#
# ⚠️ Those two facts together say the opening is **redundant with the height
# floor** and could be deleted. It is NOT deleted here: every figure in this
# benchmark was taken with it in, and removing it would mean re-taking four
# measurements to show the outputs are identical. Scoped, not done.
#
# ⚠️ A POSITIVE CONTROL IN THE SAME CLASS. A battery of refusal arms can pass
# by refusing everything, so one arm makes the reader accept NOTHING and must
# fail the tests that assert it FINDS a stem -- not the ones that assert it
# refuses junk.
POSITIVE = ("the reader accepts nothing at all", TARGET,
            "        out.append(LineDetection(\n            smufl_name=\"stem\", "
            "category=\"stem\",",
            "        continue\n        out.append(LineDetection(\n            "
            "smufl_name=\"stem\", category=\"stem\",",
            "test_the_column_profile_finds_it")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dirty() -> list[str]:
    r = subprocess.run(["git", "status", "--porcelain", "--", "tools/"],
                       cwd=ROOT, capture_output=True, text=True, check=True)
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def run_tests(node: str | None) -> bool:
    """True when pytest passes."""
    target = f"{TESTS}::{node}" if node is None else TESTS
    cmd = [sys.executable, "-m", "pytest", "-q", "-x", TESTS]
    if node:
        cmd += ["-k", node]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if SENTINEL.exists():
        info = json.loads(SENTINEL.read_text())
        print("REFUSING TO START: a previous battery was interrupted and its "
              "mutation may still be on disk.", file=sys.stderr)
        for f, h in info["hashes"].items():
            cur = sha(ROOT / f) if (ROOT / f).exists() else "MISSING"
            ok = "ok" if cur == h else "*** DIFFERS ***"
            print(f"   {f}  should be {h[:12]}  is {cur[:12]}  {ok}",
                  file=sys.stderr)
        print(f"   restore from {SNAP} then delete {SENTINEL}", file=sys.stderr)
        return 2

    d = dirty()
    if d and not a.force:
        print("REFUSING TO START: tools/ is dirty and a battery cannot tell "
              "its own mutation from somebody's edit. --force to override.",
              file=sys.stderr)
        for ln in d:
            print("   " + ln, file=sys.stderr)
        return 2

    files = sorted({f for _n, f, *_r in ARMS + [POSITIVE]})
    SNAP.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for f in files:
        rel = str(Path(f).relative_to(ROOT))
        shutil.copy2(f, SNAP / Path(f).name)
        hashes[rel] = sha(Path(f))
    SENTINEL.write_text(json.dumps({"hashes": hashes}, indent=1))
    print(f"snapshot of {len(files)} file(s) in {SNAP}; sentinel written")

    def restore():
        for f in files:
            shutil.copy2(SNAP / Path(f).name, f)
        bad = [f for f in files
               if sha(Path(f)) != hashes[str(Path(f).relative_to(ROOT))]]
        if bad:
            print(f"RESTORE FAILED for {bad}", file=sys.stderr)
            return False
        return True

    rows = []
    try:
        print("\n== the POSITIVE CONTROL first: if this is not red, the arms "
              "below prove nothing")
        for name, f, find, repl, node in [POSITIVE] + ARMS:
            src = Path(f).read_text()
            if src.count(find) != 1:
                rows.append((name, node, f"BAD ANCHOR ({src.count(find)} hits)"))
                print(f"  {'BAD ANCHOR':<12} {name}")
                continue
            Path(f).write_text(src.replace(find, repl))
            try:
                passed = run_tests(node)
            finally:
                if not restore():
                    return 2
            rows.append((name, node, "not red" if passed else "RED"))
            print(f"  {'RED' if not passed else 'NOT RED':<12} {name}"
                  f"   [{node}]")
    finally:
        ok = restore()
        SENTINEL.unlink(missing_ok=True)
        print(f"\nrestore verified: {ok}; sentinel cleared")

    print("\n== baseline: the suite must PASS on the restored tree")
    base = run_tests(None)
    print(f"   {'PASS' if base else 'FAIL'}")

    red = sum(1 for _n, _t, r in rows if r == "RED")
    bad = [r for r in rows if r[2].startswith("BAD ANCHOR")]
    survived = [r for r in rows if r[2] == "not red"]
    print(f"\n{len(rows)} arms: {red} RED, {len(survived)} survived, "
          f"{len(bad)} BAD ANCHOR")
    for r in survived + bad:
        print(f"   ⚠️  {r[2]:<24} {r[0]}   [{r[1]}]")
    (HERE / "out" / "mutation-battery.json").write_text(json.dumps(
        {"arms": [{"arm": n, "test": t, "result": r} for n, t, r in rows],
         "red": red, "survived": len(survived), "bad_anchor": len(bad),
         "baseline_passes": base}, indent=1))
    return 0 if (red == len(rows) and base) else 1


if __name__ == "__main__":
    raise SystemExit(main())
