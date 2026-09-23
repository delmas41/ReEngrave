"""Per-quantity byte share of a staged record, without loading it twice.

Roadmap 1.1 prep: before designing the ink-summary schema, measure how much
of a record's on-disk size is `Q.INK` observation rows versus everything
else. Streams `record.observations`, `record.abstentions` and
`record.verdicts` with `ijson` (never `json.load`s the whole file) and sums a
compact-JSON byte-size PROXY per `quantity`.

⚠️ This is a PROXY, not the exact on-disk byte span of each row: the files
were written with `json.dumps(result, indent=2, default=str)` (pretty,
2-space indent), and this script re-serialises each item compactly
(`separators=(",", ":")`) to size it without re-walking the raw bytes. The
proxy total is reported alongside the real file size so the indentation
overhead is visible rather than silently absorbed into the per-quantity
numbers -- an approximation stated is not the same fault as an approximation
hidden.

    python3 benchmarks/omr-ink-gather-2026-09/probe/byte_share.py <record.json> [--top N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import ijson


def measure(path: str, top: int = 10) -> dict:
    file_size = os.path.getsize(path)
    proxy_bytes: Counter = Counter()
    proxy_count: Counter = Counter()
    total_proxy = 0
    total_rows = 0

    for array_name in ("observations", "abstentions", "verdicts"):
        prefix = f"record.{array_name}.item"
        with open(path, "rb") as f:
            for item in ijson.items(f, prefix):
                q = item.get("quantity", "?")
                size = len(json.dumps(item, separators=(",", ":"),
                                       default=str))
                proxy_bytes[(array_name, q)] += size
                proxy_count[(array_name, q)] += 1
                total_proxy += size
                total_rows += 1

    rows = sorted(proxy_bytes.items(), key=lambda kv: -kv[1])
    result = {
        "path": path,
        "file_bytes": file_size,
        "file_mb": round(file_size / 1e6, 1),
        "proxy_total_bytes": total_proxy,
        "proxy_total_mb": round(total_proxy / 1e6, 1),
        # how much bigger the real file is than the compact-JSON proxy sum --
        # indentation, punctuation, top-level keys outside the three arrays.
        "overhead_ratio": round(file_size / total_proxy, 3) if total_proxy else None,
        "total_rows": total_rows,
        "top": [
            {
                "array": arr,
                "quantity": q,
                "proxy_bytes": b,
                "proxy_mb": round(b / 1e6, 1),
                "share_of_proxy": round(b / total_proxy, 4) if total_proxy else None,
                "n_rows": proxy_count[(arr, q)],
                "bytes_per_row": round(b / proxy_count[(arr, q)], 1),
            }
            for (arr, q), b in rows[:top]
        ],
    }
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record", help="path to a staged .record.json")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--json", action="store_true",
                     help="machine-readable output")
    args = ap.parse_args(argv)

    result = measure(args.record, top=args.top)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"{args.record}")
    print(f"  file:  {result['file_mb']} MB ({result['file_bytes']} bytes)")
    print(f"  proxy: {result['proxy_total_mb']} MB compact-JSON sum over "
          f"{result['total_rows']} rows "
          f"(overhead ratio file/proxy = {result['overhead_ratio']})")
    print(f"  top {args.top} by proxy bytes:")
    for row in result["top"]:
        print(f"    {row['array']:12s} {row['quantity']:22s} "
              f"{row['proxy_mb']:8.1f} MB  {row['share_of_proxy']*100:6.2f}%  "
              f"n={row['n_rows']:7d}  {row['bytes_per_row']:6.1f} B/row")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
