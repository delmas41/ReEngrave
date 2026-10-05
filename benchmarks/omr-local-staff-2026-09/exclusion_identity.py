#!/usr/bin/env python3
"""lane-ledger-exclusion: default-output identity.  Dumps (position, reason) of
every one of the 55 far heads for the default read (fix1_far control) and for
the walk-only `drop_beyond_head`-free read, using ONLY keywords that exist on
the base tree, so the same file runs on both and the two JSONs are diffed.

    python3 exclusion_identity.py OUT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

CONTROL = dict(near_edge_ledgers=True, restore_masked_near_edge=True, far_side_ledger=True)
ARMS = {"control": {}, "plain": dict(near_edge_ledgers=False, restore_masked_near_edge=False,
                                     far_side_ledger=False),
        "conn": dict(connected_continuation=True)}


def main():
    out = {}
    for d in ts.DOCS:
        for h in ec.load_heads(d):
            for arm, kw in ARMS.items():
                out[f"{arm}|{h['subject']}"] = list(ec.score.reader_absolute_position(
                    h["gray"], h["lines"], h["box"], h["subject"], h["boxes"],
                    page_accidental_boxes=h["acc"], four_causes_cd=True,
                    **{**CONTROL, **kw}))
    Path(sys.argv[1]).write_text(json.dumps(out, indent=0, sort_keys=True))
    print(len(out), "reads ->", sys.argv[1])


if __name__ == "__main__":
    main()
