"""Which lineup spans a given PAGE SET is cut into.

The boundary rule is a RUNNING MAXIMUM over the pages of the run
(`movement_reference`: "a page whose largest system is larger than every page
before it has proved the lineup GREW there"). A running maximum is anchored on
the FIRST PAGE OF THE RUN, so the same document cut into a different page set
can be cut into different spans -- which is exactly the difference between the
whole-work arm and a windowed one, and it is a property of the rule rather than
a bug in any page.

Reads the page cache `compose.py` wrote, so it costs nothing and cannot disagree
with the run it explains.

Usage:  dump_spans.py CACHE-DIR --pages 0-87 [--pages 20-31,44-55 ...]
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import movement_reference                        # noqa: E402
from tools.omr.slots import _views, labels_by_staff             # noqa: E402


def parse_pages(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        lo, hi = (part.split("-") + [None])[:2]
        out += list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    return sorted(set(out))


def page_systems(cache: Path, pages):
    rows = []
    for i in pages:
        blob = cache / f"p{i:04d}.pkl"
        if not blob.exists():
            raise SystemExit(f"REFUSING: page {i} is not in {cache}")
        pws, labels = pickle.loads(blob.read_bytes())
        views = _views(pws, labels_by_staff(labels))
        rows.append((i, [v.size for v in views]))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("--pages", action="append", required=True)
    args = ap.parse_args()
    cache = Path(args.cache)

    for spec in args.pages:
        pages = parse_pages(spec)
        rows = page_systems(cache, pages)
        spans = movement_reference.lineup_spans(rows)
        print(f"=== --pages {spec}   ({len(pages)} pages)")
        running = 0
        marks = []
        for page, sizes in rows:
            top = max(sizes) if sizes else 0
            if top > running:
                marks.append((page, running, top))
                running = top
        print(f"  running-maximum steps (page: prev -> new): "
              + ", ".join(f"{p}: {a}->{b}" for p, a, b in marks))
        print(f"  spans taken: {len(spans)}")
        for s in spans:
            sizes = [max(sz) if sz else 0
                     for p, sz in rows if p in set(s)]
            print(f"    pages {min(s):3d}-{max(s):3d}  ({len(s):2d} pages)  "
                  f"largest system in span = {max(sizes) if sizes else 0}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
