"""Roadmap 1.1b control: pool a REAL record's id lists and prove nothing moved.

Loads one committed shared record whole, pools it with `record_io`, expands
the pooled text again, and requires the expansion to DEEP-EQUAL the original
`result` dict -- every key, every verdict, every id in every list, in order.
Then writes the pooled file beside `--out` and reports both sizes.

⚠️ THE CONTROL CAN FAIL, twice over: (1) `pool_id_lists` raises
`PoolMismatch` on its own output if any field does not expand back; (2) this
script separately compares the bare `json.loads` of the pooled text against
the original and REQUIRES THEM TO DIFFER -- a pooled file that a naive reader
sees as identical is a file in which nothing was pooled, and a size figure
from it would measure the compact-JSON change again rather than this one.

    python3 benchmarks/omr-ink-gather-2026-09/probe/pool_control.py <record.json> --out <pooled.json> [--pages N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import record_io as RIO  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record")
    ap.add_argument("--out", required=True, help="write the pooled record here")
    ap.add_argument("--pages", type=int, default=None,
                    help="pages in the record, for the MB/page figure")
    args = ap.parse_args(argv)

    t0 = time.time()
    text = Path(args.record).read_text()
    original = json.loads(text)
    t1 = time.time()
    print(f"{args.record}: {len(text) / 1e6:.1f} MB, loaded in {t1 - t0:.1f}s")

    pooled_text = RIO.dumps_for_file(original, separators=(",", ":"),
                                     default=str)
    t2 = time.time()
    print(f"pooled in {t2 - t1:.1f}s (includes the writer's own expand-and-"
          f"compare self-check)")

    naive = json.loads(pooled_text)
    n_pools = len(naive.get("record", {}).get(RIO.POOL_KEY) or {})
    if naive == original:
        print("FAIL: the pooled text reads identical to the original under "
              "bare json.loads -- nothing was pooled; sizes below would be "
              "meaningless")
        return 2
    print(f"naive reading differs from the original (as it must): "
          f"{n_pools} pools written")

    expanded = RIO.expand_result(json.loads(pooled_text))
    if expanded != original:
        # find the first difference so the failure names a row
        ov = original["record"]["verdicts"]
        ev = expanded["record"]["verdicts"]
        for a, b in zip(ov, ev):
            if a != b:
                bad = [k for k in a if a.get(k) != b.get(k)]
                print(f"FAIL: verdict {a['id']} differs after expansion in "
                      f"{bad}")
                return 2
        print("FAIL: expansion differs from the original outside the verdicts")
        return 2
    t3 = time.time()
    print(f"CONTROL: expand(pool(record)) == record, every key, in "
          f"{t3 - t2:.1f}s")

    Path(args.out).write_text(pooled_text)
    before = os.path.getsize(args.record)
    after = os.path.getsize(args.out)
    print(f"size: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB "
          f"({100 * after / before:.1f}%)")
    if args.pages:
        print(f"per page: {before / 1e6 / args.pages:.1f} -> "
              f"{after / 1e6 / args.pages:.1f} MB/page "
              f"(target < 20 MB/page)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
