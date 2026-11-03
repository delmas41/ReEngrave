"""ROADMAP 2.252 r4 -- the one shared lane report (`lane_report run --from gather`) on SAVED gathers, one per (plate, arm).

r4 has a GATHER flag (`OMR_HEAD_HOLE_POSITION`), so the OFF and ON arms are gathered apart (the same tree, master cells, shared
detector cache, `out/2.252r4/gather.sh`), and an EXPORT flag (`OMR_TIE_CARRIES_ACCIDENTAL`) that reads either. Everything after the
gather -- adjudicate..export, diff, judged, tiles -- is lane_report's own code.

    LANE_REPORT_SAMPLE=S.json python3 benchmarks/omr-arc-binding-2026-10/report_saved_gathers_r4.py \
        --saved litolff:off=A.json --saved litolff:on=B.json -- --from gather --flag OMR_HEAD_HOLE_POSITION ...
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import lane_report as L     # noqa: E402

saved = {}
argv = sys.argv[1:]
while argv and argv[0] == "--saved":
    key, path = argv[1].split("=", 1)
    saved[tuple(key.split(":"))] = pathlib.Path(path).resolve()
    argv = argv[2:]
if argv and argv[0] == "--":
    argv = argv[1:]


def _saved_gather(plate, arm, flag_env, pages, work, env0):
    p = saved[(plate, arm)]
    print("  saved gather %s %s -> %s" % (plate, arm, p), flush=True)
    return p


L.gather_one = _saved_gather
sys.argv = [sys.argv[0]] + argv
raise SystemExit(L.main())
