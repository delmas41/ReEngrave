"""Test-wide isolation from MACHINE state.

⚠️⚠️ WHY THIS EXISTS. `staff_labels_surya.SENTINEL` defaults to the USER'S
REAL path (`~/.cache/datalab/surya/llamacpp_server.json`), which is how Surya's
keep-alive server advertises itself. A test that reads it sees whatever is
running on the machine at that moment, and `stop_server()` reads that same file
to decide what to kill.

CLAUDE.md records what that costs when it goes wrong: *"an agent tidying up
after itself ran `pkill -f llama-server` and killed the resident server a
SIBLING agent was reading through, costing that agent a multi-hour
transcription"* — and *"one machine has one server"*.

Every test that needs the sentinel today monkeypatches it correctly. **That is
per-test discipline, and the failure mode of per-test discipline is the test
somebody writes next.** A test that forgets does not fail loudly: it reads the
user's real machine, and on the `stop_server` path it can reach for a server
another session is using. This makes the isolation STRUCTURAL, so forgetting is
not possible.

⚠️ It is HARDENING, not a fix for an observed failure. An agent reported 9
failures in `test_surya_worker_session.py` on 2026-09-17; three full-suite runs
across two trees could not reproduce them, the file passes alone on both, and
the four files touching that module pass together. The cause is NOT established
and this does not claim to have found it.
"""
from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def _never_touch_the_real_surya_sentinel(monkeypatch, tmp_path):
    """Point SENTINEL at a per-test temp path, for EVERY test.

    A test that deliberately sets its own sentinel still wins — it
    monkeypatches after this fixture has run.
    """
    from tools.omr import staff_labels_surya

    monkeypatch.setattr(staff_labels_surya, "SENTINEL",
                        tmp_path / "llamacpp_server.json", raising=False)


@pytest.fixture(autouse=True)
def _do_not_require_an_optional_local_install(monkeypatch):
    """The suite must not depend on `.venv-surya` existing.

    ⚠️⚠️ THIS IS THE CAUSE OF THE "FLAKY" FAILURES, FOUND 2026-09-17 AND
    REPRODUCED ON DEMAND. Two agents reported ~9 failures in
    `test_surya_worker_session.py` that I could not reproduce. Neither
    contention nor test order: **`VENV_DIR` is computed from the module's own
    location, so in a git WORKTREE it points at that worktree's `.venv-surya`,
    which does not exist** — CLAUDE.md records the trap ("a fresh git worktree
    has NEITHER venv"). My worktree had the symlink and passed; both agent
    worktrees did not and failed. Running the same file in an agent worktree
    reproduces it every time.

    The tests mock the worker PROCESS but not `interpreter()`, so they hit a
    real environment probe before reaching the contract they exist to pin —
    and that contradicts the file's own docstring, *"NO TEST HERE STARTS A
    REAL WORKER."* If none starts a worker, none needs an interpreter.

    ⚠️ The mechanism is not invented here: `test_surya_runaway_read.py`
    already does exactly this for itself. That is per-file discipline, whose
    failure mode is every file that forgot — which is the other three.

    ⚠️⚠️ IT FALLS BACK, IT DOES NOT OVERRIDE — and the first version got that
    wrong. Setting the env unconditionally pointed a tree that HAS
    `.venv-surya` at a plain `python3` with no surya in it, which broke
    `test_a_block_that_swallows_the_whole_crop_is_rejected_not_assigned`: that
    test builds a real image and takes the real read path. 32 passed without
    the fixture, 2 failed with it. **A fix for a missing dependency must not
    replace a present one.**

    ⚠️ Safe because NO test asserts the missing-interpreter error; the one
    place that failure mode is exercised raises `SuryaLabelError` directly.
    Nothing real is run in the mocked tests: `interpreter()` only has to find
    a FILE, and every call that would use it is mocked.
    """
    from tools.omr import staff_labels_surya

    if (staff_labels_surya.VENV_DIR / "bin" / "python").is_file():
        return          # a real interpreter exists — do NOT override it

    monkeypatch.setenv("OMR_SURYA_PYTHON", sys.executable)


# ---------------------------------------------------------------------------
# Fast/slow test tiers, DERIVED from measured durations rather than hand-listed
# ---------------------------------------------------------------------------
#
# `durations.json` (committed, sibling of this file) is a snapshot from a full
# run of `pytest tools/omr/tests --durations=0`, summed per FILE across its
# setup/call/teardown phases. Nothing here restates that measurement — this
# hook only reads it and decides where the line falls.
#
# The threshold is COMPUTED, not a literal: it is the smallest per-file
# duration such that every file at or below it sums to under
# `_FAST_BUDGET_SECONDS` of measured test time, over the files this file's
# own duration data actually covers. That keeps the split self-adjusting if
# `durations.json` is ever re-measured, rather than freezing today's number
# into the source.
#
# On top of the duration cut, a file is ALWAYS slow if its own name or source
# text references machine-local, gitignored state this repo's CLAUDE.md
# documents as a trap in a fresh checkout or worktree — the score `library/`,
# `omr-weights/`, `.venv-surya`, `.venv-omrned`, or a PDF fixture path — because
# those tests can differ in cost (or availability) by machine in a way a
# duration measured on one machine cannot promise for another.
#
# A test FILE that carries no entry in `durations.json` at all (a new file,
# never measured) is FAST by duration — it cannot inherit a large number it
# was never charged — but the content check still applies to it independently,
# so a brand-new test that touches `library/` is still slow on day one.
import json as _json
import re as _re

_TESTS_DIR = __import__("pathlib").Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[2]          # tools/omr/tests -> tools/omr -> tools -> repo root
_DURATIONS_FILE = _TESTS_DIR / "durations.json"
_FAST_BUDGET_SECONDS = 100.0

_CONTENT_SLOW_PATTERN = _re.compile(
    r"library/|omr-weights|\.venv-surya|\.venv-omrned|\.pdf[\"']"
)


def _load_measured_durations():
    """{repo-relative posix path: measured seconds}, or {} if unreadable.

    Never raises: a missing or corrupt durations.json must not break
    collection — it should just mean nothing is slow BY DURATION (the
    content check is unaffected), which is the same "fast by default"
    behaviour a brand-new, unmeasured file gets.
    """
    try:
        with open(_DURATIONS_FILE, encoding="utf-8") as f:
            raw = _json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in raw.items() if isinstance(v, (int, float))}


def _derive_slow_by_duration(durations):
    """The set of files whose measured duration puts them over the line.

    Greedy from the SMALLEST measured file up: keep adding to the fast pile
    while it stays under budget. The first file that would tip it over, and
    everything at or above that file's own duration, is slow. Returns
    (slow_file_set, threshold_seconds, fast_sum_seconds).
    """
    ascending = sorted(durations.items(), key=lambda kv: kv[1])
    cumulative = 0.0
    threshold = 0.0
    fast_files = set()
    for path, seconds in ascending:
        if cumulative + seconds < _FAST_BUDGET_SECONDS:
            cumulative += seconds
            fast_files.add(path)
            threshold = seconds
        else:
            break
    slow_by_duration = {path for path in durations if path not in fast_files}
    return slow_by_duration, threshold, cumulative


_MEASURED_DURATIONS = _load_measured_durations()
_SLOW_BY_DURATION, _SLOW_THRESHOLD_SECONDS, _FAST_TIER_MEASURED_SECONDS = (
    _derive_slow_by_duration(_MEASURED_DURATIONS)
)

_CONTENT_SCAN_CACHE = {}


def _file_matches_slow_content(abs_path):
    """Does this file's own NAME or SOURCE reference machine-local state?

    Cached per absolute path — collection visits many items per file, and a
    file's own text does not change mid-run.
    """
    cached = _CONTENT_SCAN_CACHE.get(abs_path)
    if cached is not None:
        return cached
    if _CONTENT_SLOW_PATTERN.search(str(abs_path).replace("\\", "/")):
        result = True
    else:
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        result = bool(_CONTENT_SLOW_PATTERN.search(text))
    _CONTENT_SCAN_CACHE[abs_path] = result
    return result


def _repo_relative_posix(abs_path):
    try:
        rel = abs_path.relative_to(_REPO_ROOT)
    except ValueError:
        return str(abs_path).replace("\\", "/")
    return str(rel).replace("\\", "/")


def pytest_collection_modifyitems(config, items):
    """Apply `slow` to every item whose FILE is slow by duration or content.

    Marking is per-file, not per-test: a file's measured total already sums
    every test in it, and content references (a PDF fixture, `library/`, a
    venv) are properties of the file, not of one function inside it.
    """
    for item in items:
        abs_path = __import__("pathlib").Path(str(item.fspath)).resolve()
        rel_path = _repo_relative_posix(abs_path)
        is_slow = (
            rel_path in _SLOW_BY_DURATION
            or _file_matches_slow_content(abs_path)
        )
        if is_slow:
            item.add_marker(pytest.mark.slow)


def pytest_report_header(config):
    return (
        f"fast/slow tiers: threshold={_SLOW_THRESHOLD_SECONDS:.2f}s/file, "
        f"fast-tier measured sum={_FAST_TIER_MEASURED_SECONDS:.2f}s "
        f"(from {_DURATIONS_FILE.name}, budget={_FAST_BUDGET_SECONDS:.0f}s)"
    )
