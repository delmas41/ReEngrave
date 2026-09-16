"""The worker session: one model load per run instead of one per call.

⚠️ NO TEST HERE STARTS A REAL WORKER. The 650M GGUF load is ~17 s and a test
suite that pays it is a test suite nobody runs. What is pinned is the
CONTRACT: both callers go through one dispatcher, a session is used when
open, and EVERY failure mode falls back to the one-shot spawn rather than
losing a page.
"""
from __future__ import annotations

import json
import unittest
from unittest import mock

from tools.omr import staff_labels_surya as S


class _FakeProc:
    """A worker that answers, or misbehaves in one named way."""

    def __init__(self, replies=None, *, ready=True, dies_after=None,
                 silent=False, garbage=False):
        self._replies = list(replies or [])
        self.stdin = mock.MagicMock()
        self.stdout = mock.MagicMock()
        self.stderr = mock.MagicMock()
        self.pid = 4242
        self._dies_after = dies_after
        self._silent = silent
        self._garbage = garbage
        self._sent = 0
        self.returncode = None
        self.killed = False
        first = json.dumps({"ready": True}) + "\n" if ready else ""
        self.stdout.readline.side_effect = self._readline
        self._queued = [first] if first else [""]

    def _readline(self):
        if self._queued:
            return self._queued.pop(0)
        if self._garbage:
            return "not json\n"
        if not self._replies:
            return ""
        return json.dumps(self._replies.pop(0)) + "\n"

    def poll(self):
        if self._dies_after is not None and self._sent > self._dies_after:
            self.returncode = 9
            return 9
        return None

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        self.returncode = 0
        return 0


def _open(proc, *, select_ready=True):
    """Open a session over a fake worker, with `select` stubbed."""
    ready = ([proc.stdout], [], []) if select_ready else ([], [], [])
    return (mock.patch.object(S, "available", lambda: True),
            mock.patch.object(S.subprocess, "Popen", lambda *a, **k: proc),
            mock.patch.object(S, "select",
                              mock.MagicMock(select=lambda *a, **k: ready)))


class TestTheSessionIsUsedWhenOpen(unittest.TestCase):

    def test_a_job_goes_to_the_open_worker_and_not_to_a_spawn(self):
        proc = _FakeProc([{"crops": [{"text": "legato"}]}])
        ctxs = _open(proc)
        with ctxs[0], ctxs[1], ctxs[2], \
                mock.patch.object(S.subprocess, "run") as spawn:
            with S.worker_session():
                out = S._dispatch({"crops": ["x"]}, timeout_s=5,
                                  keep_alive=False)
        self.assertEqual(out, {"crops": [{"text": "legato"}]})
        spawn.assert_not_called()

    def test_the_session_counts_its_jobs(self):
        proc = _FakeProc([{"crops": []}, {"crops": []}])
        ctxs = _open(proc)
        with ctxs[0], ctxs[1], ctxs[2]:
            with S.worker_session() as st:
                S._dispatch({"crops": ["a"]}, timeout_s=5, keep_alive=False)
                S._dispatch({"crops": ["b"]}, timeout_s=5, keep_alive=False)
                self.assertEqual(st["jobs"], 2)

    def test_it_closes_and_leaves_no_session_behind(self):
        proc = _FakeProc([{"crops": []}])
        ctxs = _open(proc)
        with ctxs[0], ctxs[1], ctxs[2]:
            with S.worker_session():
                pass
        self.assertIsNone(S._SESSION)


class TestEveryFailureIsAFallbackNeverALoss(unittest.TestCase):
    """⚠️ An optimisation that can lose a page is not one. Each arm below is
    a way the worker can misbehave, and each must end in a one-shot spawn."""

    def _falls_back(self, proc, **kw):
        ctxs = _open(proc, **kw)
        done = {"spawned": False}

        def _fake_run(*a, **k):
            done["spawned"] = True
            return mock.Mock(returncode=0, stdout=json.dumps({"crops": []}),
                             stderr="")
        with ctxs[0], ctxs[1], ctxs[2], \
                mock.patch.object(S.subprocess, "run", _fake_run):
            with S.worker_session():
                S._dispatch({"crops": ["x"]}, timeout_s=5, keep_alive=False)
        return done["spawned"]

    def test_a_worker_that_never_reports_ready(self):
        self.assertTrue(self._falls_back(_FakeProc([], ready=False)))

    def test_a_worker_that_goes_silent(self):
        self.assertTrue(self._falls_back(_FakeProc([{"crops": []}]),
                                         select_ready=False))

    def test_a_worker_that_answers_garbage(self):
        self.assertTrue(self._falls_back(_FakeProc([], garbage=True)))

    def test_a_worker_that_died(self):
        self.assertTrue(self._falls_back(_FakeProc([{"crops": []}],
                                                   dies_after=-1)))

    def test_POSITIVE_CONTROL_a_healthy_worker_does_NOT_spawn(self):
        self.assertFalse(self._falls_back(_FakeProc([{"crops": []}])))

    def test_a_broken_session_is_closed_so_later_calls_do_not_retry_it(self):
        proc = _FakeProc([], garbage=True)
        ctxs = _open(proc)
        with ctxs[0], ctxs[1], ctxs[2], \
                mock.patch.object(S.subprocess, "run",
                                  lambda *a, **k: mock.Mock(
                                      returncode=0,
                                      stdout=json.dumps({"crops": []}),
                                      stderr="")):
            with S.worker_session():
                S._dispatch({"crops": ["x"]}, timeout_s=5, keep_alive=False)
                self.assertIsNone(S._SESSION)


class TestItIsANoOpWhereItShouldBe(unittest.TestCase):

    def test_surya_absent(self):
        with mock.patch.object(S, "available", lambda: False):
            with S.worker_session() as st:
                self.assertIsNone(st)
                self.assertIsNone(S._SESSION)

    def test_explicitly_disabled(self):
        with S.worker_session(enabled=False) as st:
            self.assertIsNone(st)

    def test_no_session_means_dispatch_spawns(self):
        self.assertIsNone(S._SESSION)
        self.assertIsNone(S._session_dispatch({"crops": []}, 5))


class TestBothCallersShareOneDispatcher(unittest.TestCase):
    """⚠️ If only one of them used the session the per-page saving would be
    half taken, and any timing of it would be meaningless."""

    def test_neither_caller_spawns_directly_any_more(self):
        import inspect
        for fn in (S.read_crops_surya, S.read_crops_text):
            src = inspect.getsource(fn)
            self.assertIn("_dispatch(", src, fn.__name__)
            self.assertNotIn("subprocess.run", src, fn.__name__)

    def test_the_gather_opens_one(self):
        import inspect
        from tools.omr.staged import pipeline
        src = inspect.getsource(pipeline.run_staged_on)
        self.assertIn("worker_session()", src)


if __name__ == "__main__":
    unittest.main()


class TestItStopsOnlyTheServerItStarted(unittest.TestCase):
    """⚠️ The first version trusted surya's atexit and the claim was
    WITHDRAWN -- a server turned up half an hour later whose pid sat inside
    the test's own range. An atexit does not run on a kill, and the check had
    been taken too early. These arms pin the narrow rule that replaced it."""

    def _teardown(self, before_pid, after):
        stopped = {"called": False}
        with mock.patch.object(S, "resident_server", lambda: after), \
                mock.patch.object(S, "stop_server",
                                  lambda: stopped.__setitem__("called", True)):
            S._stop_server_this_session_started(before_pid)
        return stopped["called"]

    def test_a_server_that_APPEARED_is_ours_and_is_stopped(self):
        self.assertTrue(self._teardown(None, {"pid": 999}))

    def test_a_server_that_was_ALREADY_THERE_is_left_alone(self):
        """Somebody else's. CLAUDE.md: never blanket-kill by name, and only
        stop one when you know nothing else is reading."""
        self.assertFalse(self._teardown("999", {"pid": 999}))

    def test_a_DIFFERENT_pid_than_the_one_that_was_there_is_ours(self):
        self.assertTrue(self._teardown("111", {"pid": 222}))

    def test_no_server_at_all_is_a_no_op(self):
        self.assertFalse(self._teardown(None, None))

    def test_the_session_calls_it_on_the_way_out(self):
        import inspect
        src = inspect.getsource(S.worker_session)
        self.assertIn("_stop_server_this_session_started(before_pid)", src)
        self.assertIn("before = resident_server()", src)
