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

    ⚠️ Safe because NO test asserts the missing-interpreter error; the one
    place that failure mode is exercised raises `SuryaLabelError` directly.
    Nothing real is run: `interpreter()` only has to find a FILE, and every
    call that would use it is mocked.
    """
    monkeypatch.setenv("OMR_SURYA_PYTHON", sys.executable)
