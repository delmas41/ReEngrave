"""Is every held edition a SCAN? -- the measured verdict against IMSLP's label.

Sean, 2026-09-22, on the catalog reporting only 7 `Typeset` of 289:
*"Or maybe they are all scans because they came from IMSLP..."*

That is a claim the tree can settle without weights, without a gather and
without a raster pass over the music: `input_domain.classify_pdf_domain` is
`OMR_WEIGHT_ROUTING`'s own shipped classifier, it reads the PDF's INTERNAL
STRUCTURE (vector drawings against a full-page raster), its gap is EMPTY over
147 probed pages, and it ABSTAINS on doubt.

⚠️ TWO WITNESSES, REPORTED APART. `image_type` is IMSLP's crowd-sourced label
and the verdict is a measurement; where they disagree that is a fact worth
having, which is why this prints a CROSS-TAB and never a correction.

    python3 benchmarks/omr-document-identity-2026-09/classify_library.py \
        --out benchmarks/omr-document-identity-2026-09/out/library-domains.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.input_domain import classify_pdf_domain  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    cat = json.loads((REPO / "data/score-library/catalog.json").read_text())
    eds = [e for e in cat["entries"] if e.get("kind") == "edition"]
    lib = REPO / "library"

    rows = []
    t0 = time.perf_counter()
    for i, e in enumerate(eds):
        if args.limit and i >= args.limit:
            break
        pdf = lib / e["path"]
        if not pdf.is_file():
            rows.append({"path": e["path"], "verdict": "NOT_ON_DISK",
                         "image_type": e.get("image_type")})
            continue
        c = classify_pdf_domain(pdf)
        pages = c.pages
        rows.append({
            "path": e["path"],
            "publisher": e.get("publisher"),
            "publisher_year": e.get("publisher_year"),
            "plate": e.get("plate"),
            "has_text_layer": e.get("has_text_layer"),
            "image_type": e.get("image_type"),
            "verdict": c.verdict,
            "ms": round(c.ms, 1),
            "n_pages_probed": len(pages),
            "page_verdicts": dict(Counter(p.verdict for p in pages)),
            "max_raster_coverage": round(
                max((p.total_raster_coverage for p in pages), default=0.0), 3),
            "max_drawings": max((p.n_drawings for p in pages), default=-1),
        })
        if (i + 1) % 25 == 0:
            print(f"  ... {i+1}/{len(eds)}", flush=True)
    elapsed = time.perf_counter() - t0

    # ---- the cross-tab, which is the whole output -------------------------
    tab = Counter((str(r.get("image_type")), r["verdict"]) for r in rows)
    print(f"\n{len(rows)} editions, {elapsed:.1f}s "
          f"({elapsed / max(len(rows), 1) * 1000:.0f} ms each)\n")
    print(f"{'IMSLP image_type':<18}{'MEASURED verdict':<20}{'n':>5}")
    print("-" * 43)
    for (lab, ver), n in sorted(tab.items(), key=lambda x: -x[1]):
        print(f"{lab:<18}{ver:<20}{n:>5}")

    print(f"\nMEASURED: {dict(Counter(r['verdict'] for r in rows))}")
    print(f"LABEL:    {dict(Counter(str(r.get('image_type')) for r in rows))}")

    dis = [r for r in rows
           if (r.get("image_type") == "Typeset") != (r["verdict"] == "engraved")]
    print(f"\nDISAGREEMENTS (label Typeset xor measured engraved): {len(dis)}")
    for r in dis:
        print(f"  {str(r.get('image_type')):<12} -> {r['verdict']:<9} "
              f"cov={r.get('max_raster_coverage')} "
              f"draw={r.get('max_drawings')}  {Path(r['path']).name[:78]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        {"n": len(rows), "seconds": round(elapsed, 1),
         "cross_tab": [{"image_type": k[0], "verdict": k[1], "n": v}
                       for k, v in sorted(tab.items(), key=lambda x: -x[1])],
         "rows": rows}, indent=1))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
