"""ROADMAP 2.312 r2 -- Brahms p0 far heads read by the ledger count, against Sean's hand-labelled page
(data/hand-truth/pages/imslp317803/0.json, cells he swept `all-ink`): the true position of a far head is counted from HIS ledgerLine
boxes (those over the head's columns, between the staff's outer line and the head) and HIS head class (OnLine / InSpace).

    PYTHONPATH=. python3 benchmarks/ledger-count-2026-11/r2_brahms_truth.py REREAD.json [REREAD2.json]

Prints per file: far heads read (pos), matched to a labelled head in a fully swept cell, right / wrong, and every wrong one.
"""
import json
import sys

from tools.omr.staged import lane_report as LR

T = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
swept = {c["id"] if isinstance(c, dict) and "id" in c else k for k, c in
         (T["cells"].items() if isinstance(T["cells"], dict) else enumerate(T["cells"]))
         if "all-ink" in str((c or {}).get("inspected") if isinstance(c, dict) else "")}
heads = [b for b in T["boxes"] if b["cls"].startswith("notehead")]
ledgers = [b for b in T["boxes"] if b["cls"] == "ledgerLine"]
lines = {}
for l in open(LR.RECORDS / "claim-readout-slices-2306-smp4-bra" / "observations.jsonl"):
    if '"quantity": "staff_lines"' in l[:200] and '"subject": "staff/0/' in l[:200]:
        o = json.loads(l)
        lines[o["subject"]] = [float(v) for v in o["value"]]


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u > 0 else 0.0


def truth_pos(th, ys):
    r = th["rect"]
    sp = (ys[-1] - ys[0]) / 4.0
    cy = (r[1] + r[3]) / 2.0
    above = cy < ys[0]
    edge = ys[0] if above else ys[-1]
    on = "OnLine" in th["cls"]
    n = 0
    for lb in ledgers:
        q = lb["rect"]
        if q[2] < r[0] or q[0] > r[2]:
            continue
        ly = (q[1] + q[3]) / 2.0
        d = (edge - ly) if above else (ly - edge)
        far = (edge - r[1]) if above else (r[3] - edge)
        if 0.3 * sp < d < far:
            n += 1
    if n == 0 and on:
        return None                  # an on-line head with no labelled ledger: not a far head of this kind
    off = 2 * n if on else 2 * n + 1
    return -off if above else 8 + off


def main(paths):
    for p in paths:
        d = json.load(open(p))["heads"]
        right = wrong = unmatched = 0
        bad = []
        for s, v in d.items():
            if v["got"][0] != "pos":
                continue
            st = "staff/" + "/".join(s.split("/")[1:4])
            ys = lines.get(st)
            if ys is None:
                continue
            best = max(heads, key=lambda h: iou(h["rect"], v["box"]), default=None)
            if best is None or iou(best["rect"], v["box"]) < 0.3 or (swept and best.get("cell_id") not in swept):
                unmatched += 1
                continue
            tp = truth_pos(best, ys)
            if tp is None:
                unmatched += 1
                continue
            if tp == v["got"][1]:
                right += 1
            else:
                wrong += 1
                bad.append((s, v["got"][1], tp, v["got"][2][:60]))
        print(p, "read:", right + wrong + unmatched, "| scored right", right, "wrong", wrong, "| not scored", unmatched,
              "| swept cells", len(swept))
        for b in bad:
            print("   WRONG", b)


if __name__ == "__main__":
    main(sys.argv[1:])
