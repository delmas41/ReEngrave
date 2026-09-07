#!/usr/bin/env python3
"""Score arbitrary artefact paths through the identity harness's own scorer.

Nothing new is measured here: `load.py` and `score.py` are the phase-0 harness,
unmodified, so a row printed here is comparable to a row in
`omr-identity-harness-2026-09/FINDINGS.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HARNESS = (Path(__file__).resolve().parents[2]
           / "omr-identity-harness-2026-09" / "probe")
sys.path.insert(0, str(HARNESS))

import load as load_mod      # noqa: E402
import score as score_mod    # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: score_arms.py WORK PATH [PATH ...]")
        return 1
    work, paths = args[0], args[1:]
    reports = []
    for p in paths:
        doc = load_mod.load(Path(p).resolve(), work, Path(p).stem)
        reports.append((doc, score_mod.score(doc, "whole work 0-87")))
    print(score_mod.HEAD)
    for _doc, r in reports:
        print(score_mod.line(r))
    print()
    for doc, _r in reports:
        print(f"-- {doc.arm}: reference slots")
        for sl in sorted(doc.slot_instruments):
            print(f"     {sl:>3} {doc.slot_instruments[sl]:<16} "
                  f"{doc.slot_sources.get(sl)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
