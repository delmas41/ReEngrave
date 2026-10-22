"""Re-measure ``durations.json`` (the fast/slow tier source) in ONE command.

    python3 -m tools.omr.tests.measure_durations [--out PATH] [--allow-dirty] [-- <extra pytest args>]

Run it on a machine that HAS the score library, weights and venvs (Sean's):
a container without them skips those tests in ~0 s and a skip is not a
measurement. Not named ``test_*`` so pytest never collects it.

Runs the FULL suite (``pytest tools/omr/tests --durations=0 -q
-p no:cacheprovider``, no ``-m``), sums setup+call+teardown seconds per FILE
and writes the same JSON shape ``conftest.py`` reads: a ``measured_on`` header
(git_head, date, command, wall_seconds, test_seconds_reported), then
``{repo-relative posix path: seconds}`` sorted slowest first. A file whose
every test skipped is NOT written (it would read as measured-fast; it stays
on conftest's text rule) and is listed in ``measured_on.unmeasured_all_skipped``.
Refuses a dirty tree (CLAUDE.md 4b) unless --allow-dirty, and refuses ``-m``.
"""
import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_OUT = Path(__file__).resolve().parent / "durations.json"


class _PerFile:
    """pytest plugin: seconds and outcomes per test file, all three phases."""

    def __init__(self):
        self.seconds = defaultdict(float)
        self.ran = defaultdict(int)       # reports that were not skips
        self.seen = set()

    def pytest_runtest_logreport(self, report):
        path = report.nodeid.split("::", 1)[0]
        self.seen.add(path)
        self.seconds[path] += report.duration
        if not report.skipped:
            self.ran[path] += 1


def _git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--allow-dirty", action="store_true",
                    help="measure from a dirty tree anyway (the header says so)")
    ap.add_argument("pytest_args", nargs="*", help="after `--`: extra pytest args")
    args = ap.parse_args(argv)
    extra = args.pytest_args
    if any(a == "-m" or (a.startswith("-m") and not a.startswith("--")) for a in extra):
        ap.error("no -m filter: a tier-filtered run would omit the slow files")
    head, dirty = _git("rev-parse", "HEAD"), bool(_git("status", "--porcelain",
                                                      "--untracked-files=no"))
    if dirty and not args.allow_dirty:
        sys.exit("refusing: git tree is dirty (CLAUDE.md 4b: not a baseline). "
                 "Commit/clean it, or pass --allow-dirty.")

    import pytest
    plugin = _PerFile()
    # the whole suite unless the caller named test paths after `--`
    target = [] if any(not a.startswith("-") for a in extra) else ["tools/omr/tests"]
    cmd = ["pytest", *target, "--durations=0", "-q", "-p", "no:cacheprovider", *extra]
    start = time.monotonic()
    rc = pytest.main(cmd[1:], plugins=[plugin])
    wall = time.monotonic() - start
    if rc not in (0, 1):                  # 1 = some tests failed; time is still real
        sys.exit(f"pytest did not complete (exit {rc}); nothing written")

    skipped_only = sorted(p for p in plugin.seen if plugin.ran[p] == 0)
    files = {p: round(s, 2) for p, s in plugin.seconds.items() if p not in skipped_only}
    header = {
        "git_head": head,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": " ".join(cmd),
        "wall_seconds": round(wall),
        "test_seconds_reported": round(sum(plugin.seconds.values()), 1),
    }
    if dirty:
        header["dirty"] = True
    if rc == 1:
        header["pytest_exit"] = 1         # failures present; durations still measured
    if skipped_only:
        header["unmeasured_all_skipped"] = skipped_only
    ordered = dict(sorted(files.items(), key=lambda kv: -kv[1]))
    args.out.write_text(json.dumps({"measured_on": header, **ordered}, indent=2) + "\n",
                        encoding="utf-8")
    print(f"wrote {args.out}: {len(ordered)} files, {len(skipped_only)} all-skipped left "
          f"unmeasured, wall {wall:.0f}s")
    return 0


if __name__ == "__main__":
    # Everything after a bare `--` is pytest's; argparse would eat it otherwise.
    raise SystemExit(main(None))
