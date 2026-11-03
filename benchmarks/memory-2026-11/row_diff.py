"""Row-by-row diff of two staged record FILES, streamed (ijson), ignoring timing keys (ROADMAP 2.249; reads only).

usage: row_diff.py A.record.json B.record.json [--ignore ms,seconds]

Rows are paired by position in `record.observations` / `.abstentions` / `.verdicts` (a deterministic run files them in
the same order with the same ids); `pools` and every other envelope key except `provenance` are compared whole.
Prints per (array, quantity) how many rows differ and the first differing rows. Exit 0 = identical apart from the
ignored keys and provenance.
"""
import argparse, json, sys
from collections import Counter
import ijson

ap = argparse.ArgumentParser()
ap.add_argument("a"); ap.add_argument("b")
ap.add_argument("--ignore", default="ms")
ap.add_argument("--show", type=int, default=5)
args = ap.parse_args()
IGN = set(args.ignore.split(","))


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in IGN}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def first_path(x, y, path=""):
    if type(x) != type(y):
        return path, x, y
    if isinstance(x, dict):
        for k in list(x) + [k for k in y if k not in x]:
            if x.get(k, "<absent>") != y.get(k, "<absent>"):
                return first_path(x.get(k, "<absent>"), y.get(k, "<absent>"), f"{path}.{k}")
    if isinstance(x, list):
        if len(x) != len(y):
            return path + f"[len {len(x)} vs {len(y)}]", None, None
        for i, (u, v) in enumerate(zip(x, y)):
            if u != v:
                return first_path(u, v, f"{path}[{i}]")
    return path, x, y


bad = 0
diffs = Counter(); shown = 0
for arr in ("observations", "abstentions", "verdicts"):
    with open(args.a, "rb") as fa, open(args.b, "rb") as fb:
        ia = ijson.items(fa, f"record.{arr}.item", use_float=True)
        ib = ijson.items(fb, f"record.{arr}.item", use_float=True)
        n = 0
        while True:
            x = next(ia, None); y = next(ib, None)
            if x is None and y is None:
                break
            n += 1
            if x is None or y is None:
                print(f"{arr}: one record has more rows (row {n})"); bad += 1
                break
            sx, sy = strip(x), strip(y)
            if sx != sy:
                diffs[(arr, x.get("quantity"), y.get("quantity"))] += 1; bad += 1
                if shown < args.show:
                    shown += 1
                    p, u, v = first_path(sx, sy)
                    print(f"DIFF {arr} row {n} id {x.get('id')}/{y.get('id')} {x.get('quantity')} {x.get('subject')}: "
                          f"at {p}: {json.dumps(u, default=str)[:300]} -> {json.dumps(v, default=str)[:300]}")
        print(f"{arr}: {n} rows compared")
for key in ("pools",):
    with open(args.a, "rb") as fa, open(args.b, "rb") as fb:
        pa = dict(ijson.kvitems(fa, f"record.{key}")); pb = dict(ijson.kvitems(fb, f"record.{key}"))
    if pa != pb:
        print(f"{key} differ"); bad += 1
ENVELOPE = ("summary", "adjudication", "agreement", "evaluation", "stubs", "inference", "weight_routing", "stopped_after",
            "divergence")
ka, kb = {}, {}
for k in ENVELOPE:
    with open(args.a, "rb") as fa, open(args.b, "rb") as fb:
        ka[k] = next(ijson.items(fa, k, use_float=True), "<absent>")
        kb[k] = next(ijson.items(fb, k, use_float=True), "<absent>")
for k in sorted(set(ka) | set(kb)):
    if strip(ka.get(k)) != strip(kb.get(k)):
        p, u, v = first_path(strip(ka.get(k)), strip(kb.get(k)))
        print(f"envelope key {k} differs at {p}: {json.dumps(u, default=str)[:200]} -> {json.dumps(v, default=str)[:200]}")
        bad += 1
for k, v in diffs.most_common():
    print("differing rows", k, v)
print("IDENTICAL apart from", sorted(IGN), "and provenance" if not bad else f"{bad} differences")
sys.exit(1 if bad else 0)
