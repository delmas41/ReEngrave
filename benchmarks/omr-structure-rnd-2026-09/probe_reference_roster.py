"""Why the slot aligner does not see the Beethoven 5 p.4 mis-join.

MEASUREMENT ONLY — reads committed transcriptions, writes nothing, changes no
pipeline behaviour.

⚠️ FIXTURE PROVENANCE. The 20-row scan gate lives ONLY in the reconciliation
worktree, suffix `.reconciliation.omr.json`. The main checkout's `fixtures/`
still holds the 11-row `..graft09` set — a script pointed there measures the
old gate and says nothing about this one.

The question: `export._stitch_slots` joins by ordinal and refuses on a count
mismatch; `_stitch_slots_by_slot` (OMR_SLOT_STITCH) joins by the slot the
contextual aligner assigned. On the eight rows where the ordinal join SUCCEEDS,
does the aligner disagree with it anywhere — and in particular on Beethoven 5
p.4, where the ordinal join is known to succeed WRONGLY (system 2 prints a
Timpani staff system 1 does not, so everything from slot 6 down shifts by one)?
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures"
)
SUFFIX = ".reconciliation.omr.json"


def systems_of(doc):
    return [s for pg in doc.get("pages", []) for s in pg.get("systems", [])
            if s.get("staves")]


def main() -> int:
    paths = sorted(FIXTURES.glob(f"*{SUFFIX}"))
    # An audit that can return "nothing found" must first prove it looked at
    # something.
    assert paths, f"EMPTY INPUT — no fixtures under {FIXTURES}"
    print(f"fixtures: {len(paths)} from {FIXTURES}")

    rows = sys.argv[1:] or [
        "beethoven-sym5-mvt1-984073-p4",
        "beethoven-sym5-mvt1-575951-p4",
        "beethoven-sym5-mvt1-984073-p2",
    ]
    n_staves = 0
    for row in rows:
        path = FIXTURES / f"{row}{SUFFIX}"
        if not path.exists():
            print(f"\n!! MISSING {path}")
            continue
        doc = json.loads(path.read_text())
        systems = systems_of(doc)
        print(f"\n=== {row}   systems={len(systems)} "
              f"sizes={[len(s['staves']) for s in systems]} ===")
        for si, sysm in enumerate(systems):
            for st in sysm["staves"]:
                n_staves += 1
                print(f"  sys{si} pos{st.get('staff_index'):>2} "
                      f"slot={st.get('slot_index'):>3} "
                      f"instr={str(st.get('instrument')):<14} "
                      f"src={str(st.get('instrument_source')):<22} "
                      f"clef={st.get('clef')}")
        ctx = doc.get("contextual") or {}
        print(f"  contextual keys: {sorted(ctx.keys())}")
        ref = ctx.get("reference")
        if ref:
            print("  reference slots:")
            for slot in ref:
                print(f"    {slot}")
    assert n_staves, "EMPTY INPUT — no staves inspected"
    print(f"\nstaves inspected: {n_staves}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
