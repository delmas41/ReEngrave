"""How long each stage and each page of ONE staged run took, and how much memory it held (ROADMAP 2.249).

⚠️ MEASURES, NEVER DECIDES. Nothing here reads or writes the `Log`; a run with the meter is the same run without it.
It exists because the 20261031-night Brahms gather ran 12 h 49 min with an EMPTY log (every print buffered, nothing
flushed) and was killed with no record and no way to tell "more work" from "same work, swapping" (2.246).

* `start()` opens a meter for the run (`pipeline.run_staged_on`); `stage(name)` times a stage; `page_done(...)` is
  called by `pipeline.PreparedPages` as each page's GATHER finishes. Every event prints ONE flushed line to STDERR
  (`[run] ...`) -- page, stage, seconds, RSS now, peak RSS -- so an overnight log can be watched as it goes.
* `finish()` closes it; `last()` is the closed meter's summary, which the CLI stamps into `provenance["run"]`
  (timing and memory are facts about the RUN, like the settings, never about the reading).
"""
from __future__ import annotations

import contextlib
import resource
import sys
import time
from typing import Any, Dict, Iterator, List, Optional

_CURRENT: Optional["Meter"] = None
_LAST: Optional[Dict[str, Any]] = None


def rss_bytes() -> Optional[int]:
    """Resident memory now, or None when psutil is missing."""
    try:
        import psutil
        return int(psutil.Process().memory_info().rss)
    except Exception:
        return None


def peak_rss_bytes() -> int:
    """The process's peak resident memory so far (`ru_maxrss` is bytes on macOS, KiB on Linux)."""
    m = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(m if sys.platform == "darwin" else m * 1024)


def _gb(b: Optional[int]) -> Optional[float]:
    return None if b is None else round(b / 1e9, 2)


class Meter:
    def __init__(self) -> None:
        self.t0 = time.time()
        self.stages: Dict[str, float] = {}
        self.stage_peak_gb: Dict[str, Optional[float]] = {}
        self.pages: List[Dict[str, Any]] = []

    def line(self, text: str) -> None:
        now = rss_bytes()
        print(f"[run] {time.time() - self.t0:8.0f}s  {text}  rss {_gb(now)} GB  peak {_gb(peak_rss_bytes())} GB",
              file=sys.stderr, flush=True)

    def page_done(self, page_index: Any, n: int, total: int, prepare_s: float, gather_s: float) -> None:
        self.pages.append({"page": page_index, "prepare_s": round(prepare_s, 1), "gather_s": round(gather_s, 1),
                           "rss_gb": _gb(rss_bytes()), "peak_rss_gb": _gb(peak_rss_bytes())})
        self.line(f"page {page_index} ({n}/{total}) prepare {prepare_s:.0f}s gather {gather_s:.0f}s")


def start() -> Meter:
    global _CURRENT
    _CURRENT = Meter()
    return _CURRENT


def current() -> Optional[Meter]:
    return _CURRENT


@contextlib.contextmanager
def stage(name: str) -> Iterator[None]:
    """Time one stage of the current run (a no-op when no run is open)."""
    m = _CURRENT
    if m is None:
        yield
        return
    m.line(f"{name} start")
    t = time.time()
    try:
        yield
    finally:
        m.stages[name] = round(m.stages.get(name, 0.0) + time.time() - t, 1)
        m.stage_peak_gb[name] = _gb(peak_rss_bytes())
        m.line(f"{name} done {time.time() - t:.0f}s")


def finish() -> Dict[str, Any]:
    """Close the current meter; its summary is `last()`."""
    global _CURRENT, _LAST
    m = _CURRENT
    _CURRENT = None
    if m is None:
        return {}
    _LAST = {"wall_s": round(time.time() - m.t0, 1), "stage_s": dict(m.stages),
             "peak_rss_gb_after_stage": dict(m.stage_peak_gb), "peak_rss_gb": _gb(peak_rss_bytes()),
             "pages": list(m.pages)}
    return _LAST


def last() -> Optional[Dict[str, Any]]:
    return _LAST
