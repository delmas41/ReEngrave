"""Run a command in its own session, so nothing that reaps THIS process kills it.

A whole-work transcription is hours long. Launched from an agent harness's
background-task slot it is killed when that slot is reaped — the first attempt
reached page 87 of 88 and died with no traceback and no output, three hours
spent. `setsid(1)` does not exist on macOS, so the double fork is done here.

Usage:  daemonize.py <cmd> [args...]
"""
from __future__ import annotations

import os
import sys

if len(sys.argv) < 2:
    raise SystemExit("usage: daemonize.py <cmd> [args...]")

if os.fork():
    sys.exit(0)                 # parent returns to the shell immediately
os.setsid()                     # new session: no controlling terminal, new pgid
if os.fork():
    os._exit(0)                 # so the daemon can never reacquire one
devnull = os.open(os.devnull, os.O_RDWR)
os.dup2(devnull, 0)
os.dup2(devnull, 1)
os.dup2(devnull, 2)
os.execvp(sys.argv[1], sys.argv[1:])
