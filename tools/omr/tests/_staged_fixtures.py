"""Shared helpers for the staged-pipeline tests (ROADMAP 0.4a).

Not collected by pytest (leading underscore, no `test_` prefix). Holds only
what several test files built identically; a fixture that builds one specific
scene stays in the file whose tests describe that scene.
"""
from tools.omr.staged.record import Log


def fresh_log() -> Log:
    """An empty append-only record."""
    return Log()
