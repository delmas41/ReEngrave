"""Which span reference each `OMR_SPAN_REFERENCE_FIT` arm ends up using.

Cheap, cache-only, and it is the thing the end-to-end number is downstream of:
one composition per span, inherited by every system in it.

Usage: which_reference.py CACHE --pages 0-85
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import movement_reference                        # noqa: E402
from tools.omr import slots as S                                # noqa: E402


def parse_pages(spec):
    out = []
    for part in spec.split(","):
        lo, hi = (part.split("-") + [None])[:2]
        out += list(range(int(lo), int(hi) + 1)) if hi else [int(lo)]
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("--pages", default="0-85")
    args = ap.parse_args()

    pages = parse_pages(args.pages)
    vbp = {}
    for i in pages:
        blob = Path(args.cache) / f"p{i:04d}.pkl"
        if not blob.exists():
            raise SystemExit(f"REFUSING: page {i} not in {args.cache}")
        pws, labels = pickle.loads(blob.read_bytes())
        vbp[i] = S._views(pws, S.labels_by_staff(labels))
    where = {id(v): (p, k) for p in pages for k, v in enumerate(vbp[p])}
    flat = [v for i in pages for v in vbp[i]]
    document = S.build_reference(flat)
    print(f"document reference ({len(document)}): "
          f"{[s.instrument or '-' for s in document]}")

    rows = [(i, [v.size for v in vbp[i]]) for i in pages]
    spans = movement_reference.lineup_spans(rows)
    print(f"spans: {[(min(s), max(s)) for s in spans]}")

    for mode in ("off", "refuse", "search"):
        os.environ["OMR_SPAN_REFERENCE_FIT"] = mode
        print(f"\n--- OMR_SPAN_REFERENCE_FIT={mode}")
        refused = False
        for sn, span_pages in enumerate(spans):
            span_views = [v for p in span_pages for v in vbp.get(p, [])]
            ranked = S.reference_candidates(span_views)
            cands = ranked if mode == "search" else ranked[:1]
            pick = None
            for k, sv in enumerate(cands):
                tg, bad = S._compose(sv, document)
                if bad is None or (bad and mode != "off"):
                    continue
                pick = (k, sv, tg, bad)
                break
            if pick is None:
                print(f"   span {sn} ({min(span_pages)}-{max(span_pages)}): "
                      f"REFUSED after {len(cands)} candidate(s) "
                      f"-> document-wide fallback for the WHOLE RUN")
                refused = True
                continue
            k, sv, tg, bad = pick
            p, sysno = where[id(sv)]
            print(f"   span {sn} ({min(span_pages)}-{max(span_pages)}): "
                  f"candidate #{k} = page {p} system {sysno}, {sv.size} staves,"
                  f" {len(sv.labels)} labels, contradictions={bad}")
            print(f"      labels : "
                  f"{[sv.labels.get(st.staff_index) or '-' for st in sv.staves]}")
            print(f"      -> global {list(tg)}")
        if refused:
            print("   => _align_by_span returns False; spans have no effect")
    os.environ.pop("OMR_SPAN_REFERENCE_FIT", None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
