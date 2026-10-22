"""ROADMAP 2.194 -- where the record's VERDICT and ABSTENTION bytes go, and which reasons fire how often.

Reads `verdicts.jsonl` and `abstentions.jsonl` of the frozen-sample slices line by line (never whole). Per quantity: rows, bytes,
and bytes by field (`considered`, `basis`, `used`, `missing`, `correlated`, ...). Reason counts per (quantity, outcome, reason).
Read-only; writes results/verdicts.json.
"""
from __future__ import annotations
import argparse, collections, json, os

ROOT = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records"
FIELDS = ("considered", "basis", "used", "missing", "declined", "excluded", "correlated", "candidates", "detail", "value", "reason")

def scan(path, is_abst=False):
    rows = collections.Counter(); byts = collections.Counter(); fb = collections.Counter(); reasons = collections.Counter()
    n = 0
    with open(path, "rb") as fh:
        for line in fh:
            n += 1
            try: o = json.loads(line)
            except Exception: continue
            q = o.get("quantity"); rows[q] += 1; byts[q] += len(line)
            for f in FIELDS:
                if f in o: fb[f] += len(json.dumps(o[f]))
            reasons[(q, o.get("outcome", "abstained" if is_abst else None), o.get("reason"))] += 1
    return n, rows, byts, fb, reasons

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="20261020-night"); ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args(); out = {}
    for plate in ("litolff", "brahms"):
        d = os.path.join(ROOT, f"lane-report-slices-{a.tag}", plate)
        nv, rows, byts, fb, reasons = scan(os.path.join(d, "verdicts.jsonl"))
        na, arows, abyts, afb, areasons = scan(os.path.join(d, "abstentions.jsonl"), True)
        tv = sum(byts.values()); ta = sum(abyts.values())
        print(f"== {plate}: verdicts {nv} rows {tv/1e6:.0f} MB; abstentions {na} rows {ta/1e6:.0f} MB")
        print("   verdict bytes by field:", {f: f"{100*b/tv:.0f}%" for f, b in fb.most_common(8)})
        print(f"   {'verdict quantity':36s} {'rows':>7s} {'MB':>6s} {'%':>5s}")
        for q, b in byts.most_common(a.top): print(f"   {str(q):36s} {rows[q]:7d} {b/1e6:6.1f} {100*b/tv:5.1f}")
        out[plate] = {"verdict_rows": nv, "verdict_bytes": tv, "abst_rows": na, "abst_bytes": ta,
                      "verdict_bytes_by_field": dict(fb), "verdict_by_quantity": {str(q): {"rows": rows[q], "bytes": byts[q]} for q in rows},
                      "reasons": [{"quantity": str(q), "outcome": str(oc), "reason": str(r), "n": n} for (q, oc, r), n in reasons.most_common()],
                      "abstention_reasons": [{"quantity": str(q), "reason": str(r), "n": n} for (q, oc, r), n in areasons.most_common()]}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "results", "verdicts.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
