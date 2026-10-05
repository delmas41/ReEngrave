#!/usr/bin/env python3
"""lane-ledger-template-fix round 5 (2026-10-04): what does the "is it really a
notehead" rule (`shape_from_page.symbol_gate`) remove from the mean-shape source
set and the control pool, and is it removing real heads? Writes a seeded random
contact sheet per document: REMOVED heads (top) and KEPT heads (bottom), each tile
the head's box in red with its class / confidence and (for removed) the reason.

    python3 benchmarks/omr-local-staff-2026-09/symbol_gate_report.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import truth_set_2_44c as ts  # noqa: E402
import score_truth_set_rungs as score  # noqa: E402
import shape_from_page as sfp  # noqa: E402

OUT = REPO / "out" / "print" / "ledgers"
SEED = 5
N_TILES = 24
COLS = 8
TILE_SP = 2.6


def tile(gray, h, label, colour):
    sp = h["spacing"]
    x0, y0, x1, y1 = h["box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = int(TILE_SP * sp)
    X0, Y0 = int(cx) - r, int(cy) - r * 3 // 2
    H, W = gray.shape
    g = np.full((r * 5, r * 2), 255, np.uint8)
    sx0, sy0, sx1, sy1 = max(0, X0), max(0, Y0), min(W, X0 + r * 2), min(H, Y0 + r * 5)
    g[sy0 - Y0:sy1 - Y0, sx0 - X0:sx1 - X0] = gray[sy0:sy1, sx0:sx1]
    z = max(1, int(round(170 / g.shape[1])))
    img = cv2.cvtColor(cv2.resize(g, None, fx=z, fy=z, interpolation=cv2.INTER_AREA if z == 1 else cv2.INTER_CUBIC), cv2.COLOR_GRAY2BGR)
    img = cv2.resize(img, (170, int(170 * g.shape[0] / g.shape[1])), interpolation=cv2.INTER_AREA)
    f = 170.0 / g.shape[1]
    cv2.rectangle(img, (int((x0 - X0) * f), int((y0 - Y0) * f)), (int((x1 - X0) * f), int((y1 - Y0) * f)), colour, 1)
    canvas = np.full((img.shape[0] + 34, 170, 3), 255, np.uint8)
    canvas[:img.shape[0]] = img
    for i, t in enumerate(label):
        cv2.putText(canvas, t[:30], (2, img.shape[0] + 12 + i * 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1, cv2.LINE_AA)
    return canvas


def sheet(tiles, title):
    if not tiles:
        return np.full((30, 600, 3), 255, np.uint8)
    h = max(t.shape[0] for t in tiles)
    rows = (len(tiles) + COLS - 1) // COLS
    g = np.full((rows * h + 26, COLS * 172, 3), 255, np.uint8)
    cv2.putText(g, title, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    for i, t in enumerate(tiles):
        r, c = divmod(i, COLS)
        g[26 + r * h:26 + r * h + t.shape[0], c * 172:c * 172 + 170] = t
    return g


def main() -> int:
    report = {}
    for doc in ts.DOCS:
        loaded = ts.load_doc(doc)
        pages = score.PageCache(loaded["cfg"])
        heads = sfp.in_staff_heads(doc, loaded, pages)
        sfp.annotate_heads(doc, loaded, pages, heads)
        # mean-shape source set: filled, on-line, lemon-gated, isolated by boxes
        src_before = [h for h in heads if h["kind"] == "filled" and h["isolated_boxes"] and h["meas"].get("ok_lemon") and h["pos"] % 2 == 0]
        src_after = [h for h in src_before if h["symbol"]["ok"]]
        removed = [h for h in src_before if not h["symbol"]["ok"]]
        # control pool (oval gate)
        pool_before = [h for h in heads if h["kind"] == "filled" and h["isolated_boxes"] and h["meas"]["ok"]]
        pool_after = [h for h in pool_before if h["symbol"]["ok"]]
        reasons = {}
        for h in removed:
            for r in h["symbol"]["reasons"]:
                k = r.split(" ")[0] + " " + (r.split(" ")[1] if len(r.split(" ")) > 1 else "")
                reasons[k] = reasons.get(k, 0) + 1
        report[doc] = dict(mean_shape_source_before=len(src_before), after=len(src_after), removed=len(removed),
                           removed_reasons=reasons, control_pool_before=len(pool_before), control_pool_after=len(pool_after),
                           sean_subjects_in_removed=[h["subject"] for h in removed if h["subject"] in ("glyph/1/1/12/4/0", "glyph/1/0/2/6/3")],
                           sean_subjects_symbol={h["subject"]: h["symbol"] for h in heads if h["subject"] in ("glyph/1/1/12/4/0", "glyph/1/0/2/6/3")})
        print(doc, json.dumps({k: v for k, v in report[doc].items() if k != "sean_subjects_symbol"}))
        print("  Sean's two (symbol check):", {k: {kk: vv for kk, vv in v.items()} for k, v in report[doc]["sean_subjects_symbol"].items()})
        rnd = random.Random(SEED)
        rem_s = rnd.sample(removed, min(N_TILES, len(removed)))
        kept_s = rnd.sample(src_after, min(N_TILES, len(src_after)))
        def lab(h):
            return [f"{h['subject'][6:]} pos{h['pos']}", f"{h['cls'][9:]} {h['symbol']['detector_score']:.2f}" if h['symbol']['detector_score'] is not None else str(h['cls']),
                    ("; ".join(h["symbol"]["reasons"]) or f"stem {h['symbol']['stem_run_sp']:.1f}sp")]
        rt = [tile(pages.get(h["page"]), h, lab(h), (0, 0, 255)) for h in rem_s]
        kt = [tile(pages.get(h["page"]), h, lab(h), (0, 160, 0)) for h in kept_s]
        a = sheet(rt, f"{doc}: REMOVED by the symbol rule ({len(rem_s)} of {len(removed)}, seed {SEED})")
        b = sheet(kt, f"{doc}: KEPT in the mean-shape source ({len(kept_s)} of {len(src_after)}, seed {SEED})")
        w = max(a.shape[1], b.shape[1])
        def pad(x):
            o = np.full((x.shape[0], w, 3), 255, np.uint8); o[:, :x.shape[1]] = x; return o
        cv2.imwrite(str(OUT / f"symbol_gate_{doc.split('-')[0]}.jpg"), np.vstack([pad(a), pad(b)]), [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    (OUT / "symbol_gate_report.json").write_text(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
