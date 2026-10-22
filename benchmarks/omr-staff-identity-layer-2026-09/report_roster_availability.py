#!/usr/bin/env python3
"""Report the roster-availability distribution from whatever is CACHED.

MEASUREMENT ONLY, and read-only: it probes nothing. Separated from
`probe_roster_availability.py` so the distribution can be read at any point
during a long sweep, and so an interrupted sweep still reports.

⚠️ ALWAYS PRINTS HOW MANY DOCUMENTS IT READ, because a partial sweep's figure
is a figure about those documents. The sweep visits documents in an order that
cycles publishers, so a partial run spans houses rather than exhausting one —
that makes a partial distribution informative, NOT complete.

    python3 benchmarks/omr-staff-identity-layer-2026-09/report_roster_availability.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from probe_roster_availability import CACHE, report  # noqa: E402


def main():
    rows = []
    for p in sorted(CACHE.glob("*.json")):
        try:
            rows.append(json.loads(p.read_text()))
        except Exception:
            pass
    if not rows:
        raise SystemExit(f"REFUSING to report: no cached documents in {CACHE}")
    print(f"⚠️ PARTIAL-SWEEP REPORT — {len(rows)} documents cached "
          f"(of 234 in scope)\n")
    report(rows)


if __name__ == "__main__":
    main()
