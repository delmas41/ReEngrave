"""The mutation battery for the measure-numbering change.

Every arm must go RED, and a POSITIVE CONTROL arm must be GREEN on the
unmutated tree -- a battery that only breaks things passes by breaking
everything, and one red arm is not a battery.

    python3 benchmarks/omr-measure-numbering-2026-09/mutate.py
    python3 benchmarks/omr-measure-numbering-2026-09/mutate.py --list

⚠️⚠️ IT `git checkout`s THE FILES IT MUTATES, AND THAT DESTROYS UNCOMMITTED
WORK -- INCLUDING YOUR OWN. CLAUDE.md records this as a collision with a
SIBLING session; it is also self-destructive, and this session proved it by
running the battery over its own uncommitted change and watching the first
arm's cleanup revert the change under test. **A battery cannot restore what
was never committed**, so it now REFUSES to start when any file it would
mutate is dirty. `--force` exists for nothing: there is no case where
discarding an unrecorded edit is the right outcome.

⚠️ An ANCHOR occurring more than once is reported as an ERROR rather than
silently mutating the first match: the fermata battery once mutated a
different function than the one it named, and the part-join battery mutated
the wrong one of two `pdf_path` forwards.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "tools/omr/staged/export.py"
ARM = ROOT / "benchmarks/omr-cleanup-count-2026-09/export_arm.py"

TESTS = ["tools/omr/tests/test_staged_export.py"]

#: (name, file, anchor, replacement, why)
ARMS = [
    # ⚠️ AN EARLIER VERSION OF THIS ARM SURVIVED AND WAS AN EQUIVALENT MUTANT
    # OF ITS OWN WRITING: `i + 1 if run is part[0] else base + i + 1` differs
    # from the real rule only when a part's FIRST system is not the
    # document's, which no fixture here builds. Replaced rather than tested
    # around -- an arm that cannot go red teaches the next reader to skim the
    # list.
    ("number-restarts-every-system", EXPORT,
     "            number = base + i + 1",
     "            number = i + 1",
     "the bar's number must not restart at each system"),
    ("base-is-a-running-total", EXPORT,
     "        base = starts[(run.page, run.system)]",
     "        base = sum(r.n_measures for r in "
     "part[:[id(x) for x in part].index(id(run))])",
     "THE ORIGINAL BUG. A running per-part total instead of the "
     "document's own bar sequence."),
    ("width-is-a-min", EXPORT,
     "            width[k] = max(width.get(k, 0), int(run.n_measures))",
     "            width[k] = min(width.get(k, 1 << 30), int(run.n_measures))",
     "a `min` lets an over-read staff spill into the next system's range"),
    ("systems-unsorted", EXPORT,
     "    for k in sorted(width):",
     "    for k in list(width):",
     "reading order is the document's, not dict insertion order"),
    ("offsets-never-accumulate", EXPORT,
     "        at += width[k]",
     "        at += 0",
     "every system starting at 1 is the same defect from the other side"),
    ("off-by-one", EXPORT,
     "            number = base + i + 1",
     "            number = base + i",
     "MusicXML measures are 1-based"),
    ("duplicate-counter-never-fires", EXPORT,
     "                1 if number in seen else 0)",
     "                0)",
     "the counter's positive control -- a silent duplicate is worse than "
     "the running count this replaces"),
    ("duplicate-counter-absent-when-zero", EXPORT,
     "            counters[\"measure_number_written_twice\"] += (\n"
     "                1 if number in seen else 0)",
     "            if number in seen:\n"
     "                counters[\"measure_number_written_twice\"] += 1",
     "`absent` must not read as `zero` -- the "
     "`empty_bars_padded_without_meter` lesson"),
    ("starts-computed-per-part", EXPORT,
     "    starts = system_bar_starts(parts)",
     "    starts = system_bar_starts([parts[-1]] if parts else [])",
     "a system nobody in THIS part stands on has no width -- the "
     "per-part view is the thing that was wrong"),
    ("system-map-re-derives-the-numbering", ARM,
     "    starts = sx.system_bar_starts(parts)",
     "    starts = {k: 0 for k in {(r.page, r.system) "
     "for p in parts for r in p}}",
     "the anti-drift arm: a second copy of the rule sends a human to the "
     "wrong bars"),
]


def run_tests() -> bool:
    p = subprocess.run([sys.executable, "-m", "pytest", *TESTS, "-x", "-q"],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args(argv)

    if args.list:
        for name, path, _a, _r, why in ARMS:
            print("%-38s %-18s %s" % (name, path.name, why))
        return 0

    # ⚠️ THE GUARD. `git checkout --` restores from the INDEX, so an
    # uncommitted edit to a mutated file is gone the moment the first arm
    # cleans up. Measured the hard way: this battery reverted the very change
    # it was written to test.
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *{str(p) for _n, p, *_ in ARMS}],
        cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if dirty:
        print("REFUSING TO RUN -- a file this battery mutates is dirty, and "
              "`git checkout` would DISCARD it:")
        for ln in dirty.splitlines():
            print("   " + ln)
        print("Commit first. There is no --force.")
        return 2

    print("POSITIVE CONTROL (unmutated tree must be GREEN) ...", end=" ",
          flush=True)
    ok = run_tests()
    print("GREEN" if ok else "RED  <-- the battery cannot say anything")
    if not ok:
        return 2

    bad = []
    for name, path, anchor, repl, why in ARMS:
        if args.only and args.only != name:
            continue
        text = path.read_text()
        n = text.count(anchor)
        if n != 1:
            print("%-38s ERROR anchor occurs %d times" % (name, n))
            bad.append(name)
            continue
        path.write_text(text.replace(anchor, repl))
        try:
            green = run_tests()
        finally:
            subprocess.run(["git", "checkout", "--", str(path)], cwd=ROOT,
                           check=True)
        print("%-38s %s   %s" % (name, "SURVIVED <--" if green else "red ",
                                 why))
        if green:
            bad.append(name)

    print()
    if bad:
        print("SURVIVORS / ERRORS: %s" % ", ".join(bad))
        return 1
    print("all %d arms red, positive control green."
          % len([a for a in ARMS if not args.only or a[0] == args.only]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
