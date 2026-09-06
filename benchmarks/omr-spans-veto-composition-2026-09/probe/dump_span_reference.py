"""What each span's OWN reference names, and where it lands in the document's.

`dump_spans.py` shows the segmentation. When two page sets are cut into spans of
the same SHAPE and still disagree about the answer, the segmentation is not the
explanation and the span REFERENCE is: a span picks its reference off the
systems inside it, so a span that does not contain its movement's opening page
has no system that labels every staff, and the slots it cannot name are then
placed into the document reference by position alone.

This prints, per span: the reference system's own labels, and the global slot
each local slot maps onto (`slots.align`), beside the document reference's name
for that slot. A local slot with NO label landing on a global slot named
Trombone is the failure, printed as such.

Usage:  dump_span_reference.py CACHE-DIR --pages 0-87 [--pages 20-31,44-55 ...]
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import movement_reference                        # noqa: E402
from tools.omr.slots import (_slots_of, _views, align,          # noqa: E402
                             build_reference, labels_by_staff,
                             reference_view)

FINALE_ONLY = {"Piccolo", "Contrabassoon", "Trombone"}


def parse_pages(spec: str):
    out = []
    for part in spec.split(","):
        lo, hi = (part.split("-") + [None])[:2]
        out += list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    return sorted(set(out))


def load(cache: Path, pages):
    views_by_page = {}
    for i in pages:
        blob = cache / f"p{i:04d}.pkl"
        if not blob.exists():
            raise SystemExit(f"REFUSING: page {i} is not in {cache}")
        pws, labels = pickle.loads(blob.read_bytes())
        views_by_page[i] = _views(pws, labels_by_staff(labels))
    return views_by_page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("--pages", action="append", required=True)
    args = ap.parse_args()
    cache = Path(args.cache)

    for spec in args.pages:
        pages = parse_pages(spec)
        vbp = load(cache, pages)
        all_views = [vbp[i] for i in pages]
        flat = [v for pv in all_views for v in pv]
        document = build_reference(flat)
        doc_names = [s.instrument for s in document]
        print(f"=== --pages {spec}")
        print(f"  document reference ({len(document)} slots): "
              f"{[n or '-' for n in doc_names]}")
        rows = [(i, [v.size for v in vbp[i]]) for i in pages]
        spans = movement_reference.lineup_spans(rows)
        for span_pages in spans:
            span_views = [v for p in span_pages for v in vbp.get(p, [])]
            sv = reference_view(span_views)
            if sv is None:
                print(f"  span {min(span_pages)}-{max(span_pages)}: "
                      f"NO REFERENCE VIEW")
                continue
            local = _slots_of(sv)
            to_global = align(sv, document)
            print(f"  span {min(span_pages):3d}-{max(span_pages):3d}  "
                  f"reference system = page ? , {len(local)} slots")
            faults = 0
            for i, slot in enumerate(local):
                g = to_global[i]
                gname = doc_names[g] if 0 <= g < len(doc_names) else None
                bad = (slot.instrument is None and gname in FINALE_ONLY)
                faults += bad
                print(f"      local {i:2d} label={str(slot.instrument):14s} "
                      f"-> global {g:3d} named {str(gname):14s}"
                      f"{'   <-- UNLABELLED ONTO A FINALE-ONLY SLOT' if bad else ''}")
            print(f"      unlabelled local slots landing on a finale-only "
                  f"global slot: {faults}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
