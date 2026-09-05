#!/usr/bin/env python3
"""A/B the shared-block rule: every staff whose LADDER answer changed.

Reads two `probe_ladder.py` outputs — one produced with `_surya_worker._assign`
snapping every block to its nearest tick, one with the `_SHARE_CENTREDNESS`
rule — and prints each staff whose pipeline-faithful resolution moved, beside
the printed truth where the row has one.

    python3 ab_shared_blocks.py BEFORE.json AFTER.json

⚠️ SCORED ON THE LADDER COLUMN, NOT THE PER-RUNG ONE. What matters is what
`contextual` is handed, and the ladder's Tesseract merge is keyed on raw label
presence, so a staff Surya answered unresolvably is closed to the rung below.
The per-rung column would credit the fix for staves the pipeline never sees.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                       # noqa: E402


def index(path):
    d = json.loads(Path(path).read_text())
    out = {}
    for r in d["rows"]:
        for s in r["staves"]:
            out[(s["row_id"], s["system"], s["position"])] = s
    return out


def main() -> int:
    a, b = index(sys.argv[1]), index(sys.argv[2])
    keys = sorted(set(a) | set(b))
    moved, cnt = [], Counter()
    for k in keys:
        x, y = a.get(k), b.get(k)
        if x is None or y is None:
            cnt["MISSING_ONE_SIDE"] += 1
            continue
        rx, ry = x.get("ladder_resolved"), y.get("ladder_resolved")
        if rx == ry:
            cnt["same"] += 1
            continue
        t = y.get("TRUTH_name")
        ti = None
        if t:
            h = lookup(t)
            ti = h.instrument.name if (h and h.instrument) else None
        verdict = ("GAINED" if rx is None and ry else
                   "LOST" if ry is None else "CHANGED")
        if ti:
            verdict += " correct" if ry == ti else " WRONG"
        cnt[verdict] += 1
        moved.append((k, x.get("ladder_text"), rx, y.get("ladder_text"), ry,
                      t, ti, verdict))

    print("ladder resolution, before -> after:", dict(cnt))
    print()
    for k, tx, rx, ty, ry, t, ti, v in moved:
        print(f"  {v:16} {k[0][:30]:30} s{k[1]} p{k[2]:>2}")
        print(f"      before {tx!r} -> {rx}")
        print(f"      after  {ty!r} -> {ry}")
        if t:
            print(f"      TRUTH  {t!r} ({ti})")
    print()
    for tag, idx in (("BEFORE", a), ("AFTER", b)):
        res = sum(1 for s in idx.values() if s.get("ladder_resolved"))
        tr = [s for s in idx.values() if s.get("TRUTH_name")]
        ok = sum(1 for s in tr
                 if s.get("ladder_resolved") and s["ladder_resolved"] ==
                 (lambda h: h.instrument.name if h and h.instrument else None)(
                     lookup(s["TRUTH_name"])))
        bad = sum(1 for s in tr
                  if s.get("ladder_resolved") and s["ladder_resolved"] !=
                  (lambda h: h.instrument.name if h and h.instrument else None)(
                      lookup(s["TRUTH_name"])))
        print(f"{tag}: ladder-resolved {res}/{len(idx)} = {res/len(idx):.3f}"
              f"   | truth-scored correct {ok}, WRONG {bad}, of {len(tr)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
