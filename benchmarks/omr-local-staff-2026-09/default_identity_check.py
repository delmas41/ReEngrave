#!/usr/bin/env python3
"""lane-ledger-edge-fix: prove the DEFAULT output is bit-identical.

Runs the round-8 reader (`four_causes_cd=True`, no new kwarg) over every
truth-set head with (A) the ledger_grid.py of the branch base
(`git show origin/lane-ledger-r8-main:tools/omr/annotate/ledger_grid.py`,
path given as argv[1]) swapped in, and (B) the current ledger_grid.py, and
compares (position, reason) per head.

    python3 benchmarks/omr-local-staff-2026-09/default_identity_check.py base_ledger_grid.py
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402
from tools.omr.annotate import ledger_grid as cur  # noqa: E402

base_path = sys.argv[1]
spec = importlib.util.spec_from_file_location("ledger_grid_base", base_path)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

heads = {d: ec.load_heads(d) for d in ts.DOCS}


def run(mod):
    score.lg = mod
    out = {}
    for d, hs in heads.items():
        for h in hs:
            out[h["subject"]] = score.reader_absolute_position(
                h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
                page_accidental_boxes=h["acc"], four_causes_cd=True)
    return out


a = run(base)
b = run(cur)
diff = [s for s in a if a[s] != b[s]]
print(f"heads compared: {len(a)}; (position, reason) differing: {len(diff)} {diff}")
sys.exit(1 if diff else 0)
