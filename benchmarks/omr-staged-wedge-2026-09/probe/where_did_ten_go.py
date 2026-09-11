"""46 decided, 20 written, 16 counted as dropped — where are the other TEN?

⚠️ `wedge_balance` calls them `absorbed_by_a_shared_event` and its `balanced`
flag is a `<=`, so it passes WITHOUT explaining them. A residue a control
tolerates is exactly what this repo has been bitten by (`symbol_ledger.
coverage_check` reporting `balanced=False` on 9 of 20 rows and being read by
nobody), so this opens it instead of naming it.

It is deliberately NOT a guess checked afterwards: the first suspicion was
"they are the 10 DEGENERATE ones" purely because 10 == 10, which is the
coincidence-as-diagnosis this file exists to refuse.

    python3 .../probe/where_did_ten_go.py /tmp/wedge/brahms.json
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3]))
sys.path.insert(0, str(HERE.parents[1]))

from wedge_only_arm import replay                                 # noqa: E402
from tools.omr.staged import adjudicate                           # noqa: E402
from tools.omr.staged import adjudicators                         # noqa: E402,F401
from tools.omr.staged import export as SX                         # noqa: E402
from tools.omr.staged.record import Q                             # noqa: E402


def main(path: str) -> int:
    whole = json.load(open(path))
    rec = whole["record"]
    log = replay(rec)
    adjudicate.run(log, order=(Q.WEDGE_ANCHOR,))
    got = [v for v in log.to_json()["verdicts"]
           if v["quantity"] == Q.WEDGE_ANCHOR]
    decided = [v for v in got if v["outcome"] == "decided"]

    on = json.loads(json.dumps(whole))
    on["record"]["verdicts"] = [v for v in rec["verdicts"]
                                if v["quantity"] != Q.WEDGE_ANCHOR] + got

    r = SX.Record(on)
    parts, *_ = SX.build(r)

    # every notehead the exporter actually wrote, by glyph key
    written_heads = set()
    part_of = {}
    for pi, part in enumerate(parts):
        for run in part:
            for cell in run.cells.values():
                for det in cell.detections:
                    if det.get("category") == "notehead" and det.get("glyph"):
                        written_heads.add(str(det["glyph"]))
                        part_of[str(det["glyph"])] = pi

    buckets: collections.Counter = collections.Counter()
    for v in decided:
        a, b = (v["value"] or ["", ""])[:2]
        ha, hb = str(a) in written_heads, str(b) in written_heads
        if not ha and not hb:
            buckets["NEITHER end reached a cell"] += 1
        elif not ha or not hb:
            buckets["ONE end reached a cell (counted as dropped)"] += 1
        elif part_of.get(str(a)) != part_of.get(str(b)):
            buckets["the two ends are in DIFFERENT parts"] += 1
        elif str(a) == str(b):
            buckets["degenerate: one note, start == stop"] += 1
        else:
            buckets["both ends written, distinct notes"] += 1

    print(f"{len(decided)} decided hairpins:")
    for name, n in buckets.most_common():
        print(f"  {n:4}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
