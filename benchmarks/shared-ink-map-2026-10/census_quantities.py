"""ROADMAP 2.194 -- where the record's rows and bytes come from, per quantity and reader.

Reads the frozen-sample slices (`library/_shared-records/lane-report-slices-<tag>/<plate>/observations.jsonl`), never a whole
record loaded into memory. Counts rows and JSON bytes per (quantity, reader) and per subject kind. Read-only.

    python3 benchmarks/shared-ink-map-2026-10/census_quantities.py [--tag 20261020-night] [--plate litolff|brahms|both]
"""
from __future__ import annotations
import argparse, collections, json, os, sys

ROOT = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records"

def kind_of(subject: str) -> str:
    parts = subject.split("/")
    return parts[0]

def census(path):
    rows = collections.Counter(); byts = collections.Counter(); readers = collections.Counter()
    kinds = collections.Counter(); kbytes = collections.Counter(); detail_keys = collections.defaultdict(collections.Counter)
    n = 0
    with open(path, "rb") as fh:
        for line in fh:
            n += 1
            try:
                o = json.loads(line)
            except Exception:
                continue
            q = o.get("quantity"); r = o.get("reader"); k = kind_of(str(o.get("subject", "")))
            rows[q] += 1; byts[q] += len(line); readers[(q, r)] += 1
            kinds[k] += 1; kbytes[k] += len(line)
            d = o.get("detail")
            if isinstance(d, dict):
                for key in d: detail_keys[q][key] += 1
    return n, rows, byts, readers, kinds, kbytes, detail_keys

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="20261020-night"); ap.add_argument("--plate", default="both")
    ap.add_argument("--top", type=int, default=40); ap.add_argument("--json", default=None)
    a = ap.parse_args()
    plates = ["litolff", "brahms"] if a.plate == "both" else [a.plate]
    out = {}
    for plate in plates:
        p = os.path.join(ROOT, f"lane-report-slices-{a.tag}", plate, "observations.jsonl")
        n, rows, byts, readers, kinds, kbytes, dk = census(p)
        total_b = sum(byts.values())
        print(f"== {plate}: {n} observation rows, {total_b/1e6:.1f} MB (slices, {a.tag})")
        print("   by subject kind (rows / MB):", {k: (kinds[k], round(kbytes[k]/1e6, 1)) for k in kinds})
        print(f"   {'quantity':40s} {'rows':>8s} {'MB':>7s} {'%bytes':>6s}  readers")
        for q, b in byts.most_common(a.top):
            rs = sorted({r for (qq, r) in readers if qq == q})
            print(f"   {str(q):40s} {rows[q]:8d} {b/1e6:7.1f} {100*b/total_b:6.1f}  {','.join(map(str, rs))[:60]}")
        out[plate] = {"rows": n, "bytes": total_b, "by_quantity": {str(q): {"rows": rows[q], "bytes": byts[q],
                      "readers": sorted({str(r) for (qq, r) in readers if qq == q}), "detail_keys": dict(dk[q].most_common(30))} for q in rows},
                      "by_kind": {k: {"rows": kinds[k], "bytes": kbytes[k]} for k in kinds}}
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)

if __name__ == "__main__":
    main()
