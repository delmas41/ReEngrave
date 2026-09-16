"""A FOURTH witness, and it was already in the tree: `build_sheet.py`'s
`out_of_sync`.

The cleanup sheet already detected this defect and scored it — 30 attention
points per system whose parts disagree about which bar they are in — using
nothing but the system map's own `first_measure` values. It was written for
the human, not for this repair, so it is an independent reading of the same
fact. Run it over a system map from each arm.

    python3 .../probe/out_of_sync.py MAP.json [MAP2.json ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print("usage: out_of_sync.py SYSTEM-MAP.json ...", file=sys.stderr)
        return 2
    rc = 0
    for arg in argv:
        payload = json.loads(Path(arg).read_text())
        print("=" * 70)
        print(Path(arg).name)
        print("=" * 70)
        bad = 0
        for entry in payload["systems"]:
            firsts = sorted({r["first_measure"] for r in entry["staves"]})
            spread = (max(firsts) - min(firsts)) if len(firsts) > 1 else 0
            if spread:
                bad += 1
            print("  p%d/s%-4d firsts=%-14s out_of_sync=%d%s"
                  % (entry["page"], entry["system"],
                     ",".join(str(f) for f in firsts), spread,
                     "   <-- the parts disagree" if spread else ""))
        print("  systems out of sync: %d of %d   (30 attention points each "
              "on the cleanup sheet)" % (bad, len(payload["systems"])))
        rc = rc or (1 if bad else 0)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
