"""ROADMAP 2.253 step 0 -- what the record holds over a page region (what a mark's ink becomes today).

    python3 benchmarks/page-claim-order-2026-11/what.py PLATE PAGE x0 y0 x1 y1      # 600-dpi page px
Prints every GATHER row (observations + abstentions, 20261029-night slices) whose page box overlaps the region, and the
detector boxes' verdict family where ADJUDICATE filed one (verdicts.jsonl).
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count as C  # noqa: E402


def box_of(o):
    d = o.get("detail") or {}
    b = d.get("bbox_page_px")
    if isinstance(b, list) and len(b) == 4 and all(isinstance(x, (int, float)) for x in b):
        return b
    v = o.get("value")
    if o.get("quantity") == "claimed_area" and isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
        return v
    return None


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def what(plate, page, region):
    hits = []
    for name in ("observations.jsonl", "abstentions.jsonl"):
        for o in C.rows(C.SLICES / plate, name):
            s = o.get("subject", "")
            parts = s.split("/")
            if len(parts) < 2 or parts[1] != str(page):
                continue
            b = box_of(o)
            if b and overlap(b, region):
                hits.append((name[:3], o))
    subs = {o["subject"] for _, o in hits}
    verd = collections.defaultdict(list)
    for v in C.rows(C.SLICES / plate, "verdicts.jsonl"):
        if v.get("subject") in subs:
            verd[v["subject"]].append((v.get("quantity"), str(v.get("value"))[:40], v.get("status")))
    for src, o in hits:
        d = o.get("detail") or {}
        print(src, o["subject"], o["quantity"], str(o.get("value"))[:50], o.get("reader"),
              d.get("owner") or d.get("why") or o.get("reason") or "", [round(x) for x in box_of(o)])
        for q, val, st in verd.get(o["subject"], [])[:8]:
            print("     verdict", q, val, st)


if __name__ == "__main__":
    a = sys.argv[1:]
    what(a[0], int(a[1]), [float(x) for x in a[2:6]])
