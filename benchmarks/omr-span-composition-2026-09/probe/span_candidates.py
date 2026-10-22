"""Every system a span could use as its reference, and how each COMPOSES.

`_align_by_span` takes exactly one candidate — `reference_view(span)` — and
accepts whatever `align` does with it. This enumerates the alternatives and
prices each by the one hard constraint the module defines: a local slot named X
placed on a global slot named Y != X is a LABEL CONFLICT, and two
differently-named instruments are certainly not the same part.

Usage: span_candidates.py CACHE --pages 0-85
"""
from __future__ import annotations

import argparse
import collections
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


def conflicts(local_slots, document, to_global):
    idx_of = {sl.index: k for k, sl in enumerate(document)}
    out = []
    for i, g in enumerate(to_global):
        j = idx_of.get(g, -1)
        if j < 0:
            out.append((i, g, local_slots[i].instrument, "UNPLACED"))
            continue
        a, b = local_slots[i].instrument, document[j].instrument
        if a is not None and b is not None and a != b:
            out.append((i, g, a, b))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("--pages", default="0-85")
    args = ap.parse_args()

    pages = parse_pages(args.pages)
    vbp = {}
    for i in pages:
        blob = Path(args.cache) / f"p{i:04d}.pkl"
        pws, labels = pickle.loads(blob.read_bytes())
        vbp[i] = S._views(pws, S.labels_by_staff(labels))
    where = {id(v): (p, k) for p in pages for k, v in enumerate(vbp[p])}

    flat = [v for i in pages for v in vbp[i]]
    document = S.build_reference(flat)
    doc_names = [s.instrument for s in document]
    print(f"document reference ({len(document)}): "
          f"{[n or '-' for n in doc_names]}")

    rows = [(i, [v.size for v in vbp[i]]) for i in pages]
    spans = movement_reference.lineup_spans(rows)
    for sn, span_pages in enumerate(spans):
        span_views = [v for p in span_pages for v in vbp.get(p, [])]
        print(f"\n=== SPAN {sn}: pages {min(span_pages)}-{max(span_pages)}, "
              f"{len(span_views)} systems")
        sizes = collections.Counter(v.size for v in span_views)
        print(f"   size histogram: {dict(sorted(sizes.items()))}")
        chosen = S.reference_view(span_views)
        # the same filter reference_view applies, so candidates are exactly
        # what it was choosing between
        vs = [v for v in span_views if v.size]
        srt = sorted(v.size for v in vs)
        cap = srt[len(srt) // 2] * S.REFERENCE_MAX_SIZE_RATIO
        cands = [v for v in vs if v.size <= cap and not S._looks_merged(v)] or vs
        counts = collections.Counter(v.size for v in cands)
        recurring = [v for v in cands if counts[v.size] > 1] or cands
        # dedupe by (size, label sequence)
        seen = {}
        for v in recurring:
            key = (v.size, tuple(v.labels.get(st.staff_index)
                                 for st in v.staves))
            seen.setdefault(key, []).append(v)
        print(f"   recurring candidates: {len(recurring)} systems, "
              f"{len(seen)} distinct (size, label sequence) shapes")
        ranked = sorted(seen.items(),
                        key=lambda kv: (-kv[0][0], -sum(1 for x in kv[0][1]
                                                        if x is not None)))
        for (size, labs), group in ranked[:14]:
            v0 = group[0]
            to_global = S.align(v0, document)
            local_slots = S._slots_of(v0)
            cf = conflicts(local_slots, document, to_global)
            star = " <== reference_view's pick" if any(
                g is chosen for g in group) else ""
            print(f"   -- size={size} nlabels={sum(1 for x in labs if x)} "
                  f"x{len(group)} systems  first at page "
                  f"{where[id(v0)][0]} sys#{where[id(v0)][1]}{star}")
            print(f"      labels: {[x or '-' for x in labs]}")
            print(f"      -> global {list(to_global)}  CONFLICTS={len(cf)}")
            for i, g, a, b in cf:
                print(f"         local {i:2d} {a} -> global {g} {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
