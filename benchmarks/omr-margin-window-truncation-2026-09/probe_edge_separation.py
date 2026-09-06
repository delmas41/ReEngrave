#!/usr/bin/env python3
"""Does the SHEET'S OWN LEFT EDGE separate a truncated margin label from a whole one?

Reads `truncation.json` (from `probe_truncation.py`) and reports the left edge,
in PDF points, of every margin span on the engraved fixtures, split by whether
that span is one the sheet cut. Pass `--library` to add the same figure over the
held editions, which is the control: a real score's margin text is laid out to
fit, so nothing there should sit on the edge.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]

MARGIN_LIMIT_PT = 140.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--truncation", type=Path, default=BENCH / "truncation.json")
    ap.add_argument("--library", action="store_true")
    # ⚠️ `library/` is machine-local and gitignored, so it exists only in the
    # MAIN checkout. From a worktree the default glob matches nothing and the
    # control silently reports zero pages — which reads exactly like "no real
    # score has this fault". Point it at the main checkout.
    ap.add_argument("--library-root", type=Path, default=ROOT)
    args = ap.parse_args()

    data = json.loads(args.truncation.read_text())
    trunc, intact = [], []
    for rec in data:
        cut = {t["on_the_sheet"].replace(" ", "") for t in rec["truncated"]}
        for span in rec["margin_spans_default"]:
            row = (span["x0"], rec["pdf"], span["text"])
            (trunc if span["text"].replace(" ", "") in cut else intact).append(row)
    trunc.sort()
    intact.sort()

    print("TRUNCATED margin spans, by left edge (pt):")
    for row in trunc:
        print(f"    {row[0]:7.2f}  {row[1]:28} {row[2]!r}")
    print("\nINTACT margin spans, ten smallest left edges (pt):")
    for row in intact[:10]:
        print(f"    {row[0]:7.2f}  {row[1]:28} {row[2]!r}")
    if trunc and intact:
        print(f"\nfixtures: {len(trunc)} truncated, {len(intact)} intact; "
              f"truncated max {max(r[0] for r in trunc):.2f} pt, "
              f"intact min {min(r[0] for r in intact):.2f} pt")

    if args.library:
        import fitz
        mins = []
        pattern = str(args.library_root / "library/editions/*/*/*.pdf")
        found = sorted(glob.glob(pattern))
        if not found:
            raise SystemExit(
                f"no editions under {pattern} — the store is machine-local and "
                "gitignored; pass --library-root pointing at the main checkout")
        for p in found:
            try:
                doc = fitz.open(p)
            except Exception:                                   # noqa: BLE001
                continue
            try:
                for i in range(min(3, doc.page_count)):
                    page = doc[i]
                    if len(page.get_text().strip()) < 40:
                        continue
                    xs = [s["bbox"][0]
                          for b in page.get_text("dict").get("blocks", [])
                          for l in b.get("lines", [])
                          for s in l.get("spans", [])
                          if len((s["text"] or "").strip()) > 2
                          and s["bbox"][0] < MARGIN_LIMIT_PT]
                    if xs:
                        mins.append((round(min(xs), 2),
                                     os.path.basename(p)[:44], i))
            finally:
                doc.close()
        mins.sort()
        print(f"\nLIBRARY CONTROL: {len(mins)} edition pages carry margin text.")
        print("ten smallest left edges (pt):")
        for m in mins[:10]:
            print(f"    {m[0]:7.2f}  {m[1]:46} p{m[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
