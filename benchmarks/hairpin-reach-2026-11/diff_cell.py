"""ROADMAP 2.254: what differs OFF vs ON inside one cell of the lane report's arms (verdict outcomes and GATHER row counts by quantity).

    python3 benchmarks/hairpin-reach-2026-11/diff_cell.py WORKDIR brahms 25/1/5/0
"""
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.judged import iter_array  # noqa: E402


def under(sub, cell):
    parts = (sub or "").split("/")
    return len(parts) >= 5 and "/".join(parts[1:5]) == cell


def collect(rec, cell):
    v, o = {}, collections.Counter()
    for it in iter_array(rec, "verdicts"):
        if under(it.get("subject"), cell):
            v[(it["subject"], it["quantity"])] = (it.get("outcome"), str(it.get("value"))[:60], it.get("reason"))
    return v


def main(work, plate, cell):
    off = collect(pathlib.Path(work) / ("%s.off.mini-record.json" % plate), cell)
    on = collect(pathlib.Path(work) / ("%s.on.mini-record.json" % plate), cell)
    diff = collections.Counter()
    shown = 0
    for k in sorted(set(off) | set(on)):
        if off.get(k) != on.get(k):
            diff[k[1]] += 1
            if shown < 25:
                print(k, "OFF", off.get(k), "ON", on.get(k))
                shown += 1
    print("differing verdicts by quantity:", dict(diff))


if __name__ == "__main__":
    main(*sys.argv[1:4])
