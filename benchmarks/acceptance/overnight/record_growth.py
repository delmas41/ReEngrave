"""Why did a record change size? Rows and approximate bytes per (array, quantity), BASE vs TAG, streamed (no whole-record load).
Bytes = len(json.dumps(row)), an approximation of the file share. Lists the biggest growers.
python3 record_growth.py BASE.record.json TAG.record.json [top]
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
from pathlib import Path                                  # noqa: E402
from tools.omr.staged.judged import iter_array            # noqa: E402


def tally(path):
    n, b = collections.Counter(), collections.Counter()
    for arr in ("observations", "abstentions", "verdicts"):
        for r in iter_array(Path(path), arr):
            k = (arr, r.get("quantity"))
            n[k] += 1
            b[k] += len(json.dumps(r, default=str))
    return n, b


def main():
    a, b = sys.argv[1], sys.argv[2]
    top = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    na, ba = tally(a)
    nb, bb = tally(b)
    print("file size MB: BASE %.0f  TAG %.0f   (x%.2f)" % (os.path.getsize(a) / 1e6, os.path.getsize(b) / 1e6, os.path.getsize(b) / os.path.getsize(a)))
    for arr in ("observations", "abstentions", "verdicts"):
        sa = sum(v for k, v in na.items() if k[0] == arr)
        sb = sum(v for k, v in nb.items() if k[0] == arr)
        ya = sum(v for k, v in ba.items() if k[0] == arr)
        yb = sum(v for k, v in bb.items() if k[0] == arr)
        print("  %-13s rows %8d -> %8d   ~MB %6.0f -> %6.0f" % (arr, sa, sb, ya / 1e6, yb / 1e6))
    grow = sorted(set(na) | set(nb), key=lambda k: -(bb[k] - ba[k]))
    print("biggest growth by ~bytes (array / quantity: rows, ~MB):")
    for k in grow[:top]:
        print("  %-13s %-34s rows %8d -> %8d   ~MB %6.1f -> %6.1f" % (k[0], k[1], na[k], nb[k], ba[k] / 1e6, bb[k] / 1e6))


if __name__ == "__main__":
    main()
