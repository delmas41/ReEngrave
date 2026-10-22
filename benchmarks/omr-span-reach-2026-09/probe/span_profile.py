"""Does THIS document take more than one lineup span? — phase 1 only.

`movement_reference.lineup_spans` is a function of one thing: the
`(page_index, [system sizes])` profile. And that profile comes out of phase 1
alone — `detect_staves` sets `system_index`, so the sizes are known before any
detector, any margin reader and any export runs.

So the question "could this work exercise the span code at all" costs a render
and a staff detection per page, and nothing else. That is the cheap screen this
whole shortlist is built on: a work that takes ONE span cannot execute the code
under test, and no amount of running it further will change that.

⚠️ It answers reach, NOT correctness. A confirmed boundary says the code has
something to do on this document; whether the names either side of it are right
is the expensive question, and needs `compose.py`.

Caching: one pickle per page under `--cache`, holding only the sizes, so a
re-run of any arm is free and a wider page range only pays for its new pages.

    span_profile.py PDF --out out.json [--pages 0-78] [--dpi 600] [--cache DIR]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr import movement_reference                      # noqa: E402
from tools.omr.preprocessing import render_page               # noqa: E402
from tools.omr.staff_detector import detect_staves            # noqa: E402


def parse_pages(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        lo, hi = (part.split("-") + [None])[:2]
        out += list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    return sorted(set(out))


def page_count(pdf: Path) -> int:
    import fitz
    with fitz.open(pdf) as doc:
        return doc.page_count


def sizes_for_page(pdf: Path, i: int, dpi: int, cache: Path | None
                   ) -> list[int]:
    blob = cache / f"p{i:04d}.json" if cache else None
    if blob is not None and blob.exists():
        return json.loads(blob.read_text())
    pws = detect_staves(render_page(pdf, i, dpi=dpi))
    by_system: dict[int, int] = {}
    for s in pws.staves:
        by_system[s.system_index] = by_system.get(s.system_index, 0) + 1
    sizes = [by_system[k] for k in sorted(by_system)]
    if blob is not None:
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_text(json.dumps(sizes))
    return sizes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default=None, help="default: every page")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args()

    pdf = Path(args.pdf)
    pages = parse_pages(args.pages) if args.pages else list(
        range(page_count(pdf)))
    cache = Path(args.cache) if args.cache else None

    profile: list[tuple[int, list[int]]] = []
    t0 = time.time()
    for i in pages:
        sizes = sizes_for_page(pdf, i, args.dpi, cache)
        profile.append((i, sizes))
        print(f"  p{i:3d} peak={max(sizes) if sizes else 0:3d} {sizes}",
              file=sys.stderr, flush=True)
    elapsed = time.time() - t0

    spans = movement_reference.lineup_spans(profile)
    out = {
        "source": "span_profile.py",
        "pdf": str(pdf),
        "dpi": args.dpi,
        "pages": pages,
        "profile": {str(i): s for i, s in profile},
        "spans": spans,
        "n_spans": len(spans),
        "span_ranges": [[s[0], s[-1]] for s in spans if s],
        "seconds": round(elapsed, 1),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1, sort_keys=True)
    print(f"\n{pdf.name}: {len(pages)} pages in {elapsed:.0f}s -> "
          f"{len(spans)} span(s) {out['span_ranges']}")
    for s in spans:
        peaks = [max(dict(profile)[p]) if dict(profile)[p] else 0 for p in s]
        print(f"   pages {s[0]}-{s[-1]} ({len(s)}p) peak sizes "
              f"{sorted(set(peaks))}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
