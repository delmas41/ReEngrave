#!/usr/bin/env python3
"""l288_score: Sean's judged heads (l288_truth) against a record's standing ADJUDICATE duration verdict, GATHER+ADJUDICATE only.
Per entry: RIGHT (decided his value), IN (narrowed, value inside), OUT (narrowed, value not inside), WRONG (decided another), none.
Also prints the head's own readings (box, ink windows, tip) so a rule can be tested against them.

    python3 l288_score.py rec.json [rec2.json ...]
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))

from l288_population import build  # noqa: E402
from l288_truth import truth  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def find(rows, t):
    if "key" in t:
        return next((r for r in rows if r["key"] == t["key"]), None)
    best, bi = None, 0.3
    for r in rows:
        if r["page"] != t["page"] or not r["box_page"]:
            continue
        v = iou(r["box_page"], t["box"])
        if v > bi:
            best, bi = r, v
    return best


def klass(r, beats):
    if r["outcome"] == "decided":
        return "RIGHT" if abs((r["beats"] or 0) - beats) < 1e-6 else "WRONG"
    if r["outcome"] == "narrowed":
        return "IN" if beats in (r["cands"] or []) else "OUT"
    return "none"


def table(rows_by_rec, label_fn=None):
    out = []
    for t in truth():
        row = {"t": t}
        for name, rows in rows_by_rec.items():
            pages = {r["page"] for r in rows}
            if t["page"] not in pages:
                row[name] = None
                continue
            r = find(rows, t)
            row[name] = (r, klass(r, t["beats"]) if r else "nohead")
        out.append(row)
    return out


def main():
    recs = {Path(p).parent.name + "/" + Path(p).name: build(RD.load_run(p)) for p in sys.argv[1:]}
    for row in table(recs):
        t = row["t"]
        print(t["src"], t["movement"], "p", t["page"], "truth", t["beats"])
        for name, v in row.items():
            if name == "t" or v is None:
                continue
            r, k = v
            if r is None:
                print("   ", name, k)
                continue
            tip = r["tip"] or {}
            print("   ", name, k, f'{r["outcome"]}:{r["reason"]}', r["status"], "cls", r["cls"], "h", r["h_sp"], "w", r["w_sp"], "stem", r["stem"], r["side"],
                  "tip", tip.get("value"), tip.get("why"), "ink", {k2: v2 for k2, v2 in r["ink"].items() if v2})


if __name__ == "__main__":
    main()
