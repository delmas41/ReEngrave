"""How long each stage and each page of ONE staged run took, and how much memory it held (ROADMAP 2.249).

⚠️ MEASURES, NEVER DECIDES. Nothing here reads or writes the `Log`; a run with the meter is the same run without it.
It exists because the 20261031-night Brahms gather ran 12 h 49 min with an EMPTY log (every print buffered, nothing
flushed) and was killed with no record and no way to tell "more work" from "same work, swapping" (2.246).

* `start()` opens a meter for the run (`pipeline.run_staged_on`); `stage(name)` times a stage; `page_done(...)` is
  called by `pipeline.PreparedPages` as each page's GATHER finishes. Every event prints ONE flushed line to STDERR
  (`[run] ...`) -- page, stage, seconds, physical footprint and RSS (now, peak) -- so an overnight log can be watched as it goes.
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


def footprint_bytes() -> "tuple[Optional[int], Optional[int]]":
    """(physical footprint now, lifetime peak) on macOS, else (None, None).

    ⚠️ ON macOS RSS OVERSTATES WHAT A RUN HOLDS: freed large blocks stay resident as MALLOC_LARGE_REUSABLE (measured on
    Brahms p0-1: RSS 10.4 GB, physical footprint 3.7 GB, 5.3 GB of it reusable) and the kernel takes them back
    under pressure without swapping. The footprint (`proc_pid_rusage` v4) is what memory pressure and swap answer to.
    """
    if sys.platform != "darwin":
        return None, None
    try:
        import ctypes
        import os

        class _RU(ctypes.Structure):
            _fields_ = [("uuid", ctypes.c_uint8 * 16), ("v", ctypes.c_uint64 * 40)]
        r = _RU()
        if ctypes.CDLL("/usr/lib/libproc.dylib").proc_pid_rusage(os.getpid(), 4, ctypes.byref(r)) != 0:
            return None, None
        return int(r.v[7]), int(r.v[28])      # ri_phys_footprint, ri_lifetime_max_phys_footprint
    except Exception:
        return None, None


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
        fp, fp_peak = footprint_bytes()
        mem = f"footprint {_gb(fp)} GB (peak {_gb(fp_peak)})  " if fp is not None else ""
        print(f"[run] {time.time() - self.t0:8.0f}s  {text}  {mem}rss {_gb(rss_bytes())} GB (peak {_gb(peak_rss_bytes())})",
              file=sys.stderr, flush=True)

    def page_done(self, page_index: Any, n: int, total: int, prepare_s: float, gather_s: float) -> None:
        fp, fp_peak = footprint_bytes()
        self.pages.append({"page": page_index, "prepare_s": round(prepare_s, 1), "gather_s": round(gather_s, 1),
                           "rss_gb": _gb(rss_bytes()), "peak_rss_gb": _gb(peak_rss_bytes()),
                           "footprint_gb": _gb(fp), "peak_footprint_gb": _gb(fp_peak)})
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
        m.stage_peak_gb[name] = _gb(footprint_bytes()[1] or peak_rss_bytes())
        m.line(f"{name} done {time.time() - t:.0f}s")


def finish() -> Dict[str, Any]:
    """Close the current meter; its summary is `last()`."""
    global _CURRENT, _LAST
    m = _CURRENT
    _CURRENT = None
    if m is None:
        return {}
    _LAST = {"wall_s": round(time.time() - m.t0, 1), "stage_s": dict(m.stages),
             "peak_gb_after_stage": dict(m.stage_peak_gb), "peak_rss_gb": _gb(peak_rss_bytes()),
             "peak_footprint_gb": _gb(footprint_bytes()[1]), "pages": list(m.pages)}
    return _LAST


def last() -> Optional[Dict[str, Any]]:
    return _LAST
