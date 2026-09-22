"""What the RECORD already says about the heads the widened join would reach.

⚠️ A HEAD THE JOIN RESCUES MAY ALREADY HAVE AN ANSWER. `no_stem` is the
abstention the reach probe counts, but `_direction_from_a_beam_mate` sits in
the same branch and answers some of them already -- for those the repair moves
a REASON, not a value, and this project's own rule is that a record
improvement must not be quoted as a file improvement.

⚠️ IT READS THE RECORD'S COMMITTED VERDICTS AND DOES NOT RE-DECIDE. That is a
statement about the tree the record was GATHERED on, not about today's tree;
the A/B is what speaks for today's.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import stream_array  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--reach", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    reach = json.loads(Path(a.reach).read_text())
    want = {r["head"] for r in reach["rows"]}
    mates = {m for r in reach["rows"] for m in r["mates"]}

    got, got_mates = {}, {}
    n = 0
    for v in stream_array(a.record, "verdicts"):
        n += 1
        if v.get("quantity") != "stem_direction":
            continue
        s = v.get("subject", "")
        rec = {"outcome": v.get("outcome"), "reason": v.get("reason"),
               "value": v.get("value")}
        if s in want:
            got[s] = rec
        if s in mates:
            got_mates[s] = rec

    out = {
        "label": a.label or Path(a.record).name,
        "verdicts_streamed": n,
        "heads_reached": len(want),
        "verdict_found_for": len(got),
        "by_reason": dict(Counter(
            (r["outcome"], r["reason"]) for r in got.values()).most_common()),
        "mates_by_reason": dict(Counter(
            (r["outcome"], r["reason"]) for r in got_mates.values()
        ).most_common()),
        "rows": {k: got[k] for k in sorted(got)},
    }
    printable = {k: v for k, v in out.items() if k != "rows"}
    printable["by_reason"] = {f"{k[0]}/{k[1]}": v
                              for k, v in out["by_reason"].items()}
    printable["mates_by_reason"] = {f"{k[0]}/{k[1]}": v
                                    for k, v in out["mates_by_reason"].items()}
    print(json.dumps(printable, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(
            {**printable, "rows": out["rows"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
