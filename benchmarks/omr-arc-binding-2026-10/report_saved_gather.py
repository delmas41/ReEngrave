"""ROADMAP 2.252 r3 -- the one shared lane report (`lane_report run --from gather`) on ONE saved gather per plate.

The r3 flag (`OMR_UNISON_TIE_VOICE`) acts in EXPORT only, so OFF and ON read the same GATHER..INFER record: both arms are
handed the same saved gather (r2 flags + split ON, master cells, shared detector cache) instead of gathering it twice.
Everything after the gather -- export, diff, judged, tiles -- is lane_report's own code.

    LANE_REPORT_SAMPLE=S.json python3 benchmarks/omr-arc-binding-2026-10/report_saved_gather.py \
        --saved litolff=out/2.252u/litolff-p2-3.gathered.record.json -- run --from gather --flag OMR_UNISON_TIE_VOICE ...
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
    plate, path = argv[1].split("=", 1)
    saved[plate] = pathlib.Path(path).resolve()
    argv = argv[2:]
if argv and argv[0] == "--":
    argv = argv[1:]


def _saved_gather(plate, arm, flag_env, pages, work, env0):
    print("  saved gather %s %s -> %s" % (plate, arm, saved[plate]), flush=True)
    return saved[plate]


L.gather_one = _saved_gather
sys.argv = [sys.argv[0]] + argv
raise SystemExit(L.main())
