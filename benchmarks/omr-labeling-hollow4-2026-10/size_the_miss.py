"""ROADMAP 2.4b step 2 -- size the hollow-head miss on Sean's hand truth.

    python3 benchmarks/omr-labeling-hollow4-2026-10/size_the_miss.py \
        --page data/hand-truth/pages/imslp317803/0.json \
        --record c0.25=<rec.json> --record c0.10=<rec.json> [--out miss.json]

Reads one hand-truth page (Sean's half/whole heads, page pixels) and one or more
GATHER+ADJUDICATE records of the same page made with the same weights at different
detector confidence floors. For every truth hollow head it says:

  found_hollow   a record box overlapping it is a half/whole notehead class
  found_black    the best overlapping record box is a BLACK notehead class (wrong class)
  found_other    overlapped only by a non-notehead box (a dynamic, a tie, ...)
  missing        no record box overlaps it at all

and, for each, what is around it in Sean's own boxes: tie/slur, ledger line,
stem, another notehead (chord or second), augmentation dot, and whether the head
is ON a staff line. A record box counts as the head if IoU >= 0.3 OR the truth
centre lies inside it and the record box is no more than 2x the truth area.

Controls (rule 7): (a) matching the truth against ITSELF finds 100%; (b) matching it
against the truth shifted by 3 head-widths finds ~0%. The script exits 1 if either
control fails to behave.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from tools.omr.hand_truth import store as ST  # noqa: E402
from tools.omr.hand_truth import score as SC  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

HOLLOW = ("noteheadHalf", "noteheadWhole", "noteheadDoubleWhole")
BLACK = ("noteheadBlack",)


def is_hollow(cls: str) -> bool:
    return cls.startswith(HOLLOW)


def is_black(cls: str) -> bool:
    return cls.startswith(BLACK)


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    if i <= 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / ua


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


def overlaps(a, b, pad=0.0):
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


def touches(truth_rect, other, pad):
    return overlaps(truth_rect, other, pad)


def same_head(t, r):
    if iou(t, r) >= 0.3:
        return True
    cx, cy = (t[0] + t[2]) / 2, (t[1] + t[3]) / 2
    return r[0] <= cx <= r[2] and r[1] <= cy <= r[3] and area(r) <= 2.0 * area(t)


def context(t, boxes, ss):
    """What Sean's boxes put around truth head ``t`` (page px)."""
    ctx = []
    pad = 0.15 * ss
    for b in boxes:
        if b.rect == t:
            continue
        c, r = b.cls, b.rect
        if c == "ledgerLine" and overlaps(t, r, pad):
            ctx.append("ledger")
        elif c in ("tie", "slur"):
            # an arc's box is wide; "through" = its box covers the head's centre column
            # and reaches within 0.6 ss of the head vertically.
            cx = (t[0] + t[2]) / 2
            if r[0] <= cx <= r[2] and overlaps(t, r, 0.6 * ss):
                ctx.append(c)
        elif c == "stem" and overlaps(t, r, pad):
            ctx.append("stem")
        elif c == "augmentationDot" and overlaps(t, r, 0.8 * ss):
            ctx.append("dot")
        elif c.startswith("notehead") and r != t and overlaps(t, r, 0.3 * ss):
            ctx.append("neighbour-head")
        elif c.startswith("accidental") and overlaps(t, r, 1.0 * ss):
            ctx.append("accidental")
    return sorted(set(ctx))


def classify(truth_heads, read_glyphs):
    out = []
    for tb in truth_heads:
        t = tb.rect
        cands = [g for g in read_glyphs if same_head(t, g.rect)]
        hol = [g for g in cands if is_hollow(g.cls)]
        blk = [g for g in cands if is_black(g.cls)]
        if hol:
            best = max(hol, key=lambda g: iou(t, g.rect))
            kind = "found_hollow"
        elif blk:
            best = max(blk, key=lambda g: iou(t, g.rect))
            kind = "found_black"
        elif cands:
            best = max(cands, key=lambda g: iou(t, g.rect))
            kind = "found_other"
        else:
            best, kind = None, "missing"
        out.append((tb, kind, best))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", type=Path, required=True)
    ap.add_argument("--record", action="append", required=True, help="label=path")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()

    page = ST.load(a.page)
    boxes = list(page.boxes)
    heads = [b for b in boxes if is_hollow(b.cls)]
    blacks = [b for b in boxes if is_black(b.cls)]
    ss = statistics.median([b.rect[3] - b.rect[1] for b in blacks]) if blacks else 50.0
    print(f"page {page.edition}:{page.pdf_page_index}  hollow truth heads {len(heads)}  "
          f"(black {len(blacks)})  staff space ~{ss:.0f}px (median black-head height)")
    print("truth origin x class:", dict(collections.Counter((b.cls[8:], b.origin) for b in heads)))

    # controls ---------------------------------------------------------------------------
    class G:  # a stand-in record box
        def __init__(s, cls, rect):
            s.cls, s.rect = cls, rect
    self_read = [G(b.cls, b.rect) for b in heads]
    shift = 3 * (statistics.median([b.rect[2] - b.rect[0] for b in heads]))
    shifted = [G(b.cls, (b.rect[0] + shift, b.rect[1], b.rect[2] + shift, b.rect[3])) for b in heads]
    c1 = sum(1 for _t, k, _b in classify(heads, self_read) if k == "found_hollow")
    c2 = sum(1 for _t, k, _b in classify(heads, shifted) if k == "found_hollow")
    print(f"control self-match {c1}/{len(heads)} (must be all)   shifted-by-3-heads {c2}/{len(heads)} (must be ~0)")
    ok = (c1 == len(heads)) and (c2 <= max(1, len(heads) // 10))
    if not ok:
        print("CONTROL FAILED -- numbers withheld")
        return 1

    report = {"page": f"{page.edition}:{page.pdf_page_index}", "truth_hollow": len(heads), "records": {}}
    for spec in a.record:
        label, path = spec.split("=", 1)
        run = RO.load_run(path)
        glyphs = SC.read_glyphs(run, page.pdf_page_index)
        res = classify(heads, glyphs)
        kinds = collections.Counter(k for _t, k, _b in res)
        hol_all = [g for g in glyphs if is_hollow(g.cls)]
        # record hollow boxes that match no truth head: not scored for precision here (truth is
        # complete for the hollow family only in the cells inspected) -- count only.
        extra = [g for g in hol_all if not any(same_head(t.rect, g.rect) for t in heads)]
        ctx_by_kind = collections.defaultdict(collections.Counter)
        rows = []
        for tb, kind, best in res:
            cx = context(tb.rect, boxes, ss)
            for c in (cx or ["none"]):
                ctx_by_kind[kind][c] += 1
            rows.append({"id": tb.id, "cls": tb.cls, "origin": tb.origin, "kind": kind,
                         "rect": [round(v) for v in tb.rect],
                         "context": cx,
                         "read_cls": best.cls if best else None,
                         "read_score": getattr(best, "score", None) if best else None,
                         "adjudicate": best.status if best and hasattr(best, "status") else None})
        report["records"][label] = {
            "path": path, "glyphs_on_page": len(glyphs),
            "hollow_boxes_gathered": len(hol_all),
            "kinds": dict(kinds),
            "found_hollow_pct": round(100 * kinds.get("found_hollow", 0) / len(heads), 1),
            "context_by_kind": {k: dict(v) for k, v in ctx_by_kind.items()},
            "hollow_boxes_matching_no_truth_head": len(extra),
            "rows": rows,
        }
        r = report["records"][label]
        print(f"\n[{label}] hollow boxes gathered {r['hollow_boxes_gathered']}; truth heads: {r['kinds']}  "
              f"-> hollow-class recall {r['found_hollow_pct']}%   extra hollow boxes (no truth head) {len(extra)}")
        conf = collections.Counter((x["cls"][8:], (x["read_cls"] or "-")[8:]) for x in rows)
        r["class_confusion_truth_vs_read"] = {f"{a}->{b}": n for (a, b), n in conf.items()}
        print(f"  truth class -> read class: {r['class_confusion_truth_vs_read']}")
        print(f"  around each: {r['context_by_kind']}")
        miss = [x for x in rows if x["kind"] != "found_hollow"]
        for x in miss:
            print(f"    {x['kind']:<12} {x['cls'][8:]:<18} {x['origin']:<17} ctx={x['context']} read={x['read_cls']} "
                  f"adj={x['adjudicate']} rect={x['rect']}")
    if a.out:
        a.out.write_text(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
