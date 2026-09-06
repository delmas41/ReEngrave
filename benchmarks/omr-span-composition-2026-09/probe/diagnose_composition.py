"""WHY does the span reference land where it does? Measure, do not assert.

The four candidate mechanisms the handoff names:
  1. the label term is not live in the composition call (labels empty / mis-keyed)
  2. the document reference's slots carry no `instrument` at those positions
  3. monotonicity FORCES it (the label cost is paid because nothing else fits)
  4. something else

This prints, for the composition call of every span:
  * which PAGE and SYSTEM the span reference was read off, with each staff's
    label AND the raw margin text behind it;
  * whether `view.labels` is non-empty at the composition call (mechanism 1);
  * whether the document slots carry instruments (mechanism 2);
  * the MONOTONE ENVELOPE: for each local slot, the globals it could reach at
    all given m locals into n globals (mechanism 3);
  * the DP's chosen embedding scored term by term, beside every hand-named
    alternative embedding, so "the wrong one scored higher" is a number.

Usage: diagnose_composition.py CACHE --pages 0-85 [--alt SPAN:g0,g1,...]
"""
from __future__ import annotations

import argparse
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


def load(cache, pages):
    out = {}
    for i in pages:
        blob = Path(cache) / f"p{i:04d}.pkl"
        if not blob.exists():
            raise SystemExit(f"REFUSING: page {i} not in {cache}")
        pws, labels = pickle.loads(blob.read_bytes())
        out[i] = (pws, labels)
    return out


def score_embedding(view, reference, mapping, group_map):
    """`mapping[i]` = POSITION in reference for local staff i (or -1)."""
    denom = max(1, view.size - 1)
    positions = [i / denom for i in range(view.size)]
    labels = [view.labels.get(st.staff_index) for st in view.staves]
    total, rows, used = 0.0, [], set()
    for i, j in enumerate(mapping):
        if j < 0:
            continue
        used.add(j)
        st, ref = view.staves[i], reference[j]
        lab = 0.0
        if labels[i] is not None and ref.instrument is not None:
            lab = (S.SCORE_LABEL_MATCH if labels[i] == ref.instrument
                   else S.SCORE_LABEL_CONFLICT)
        grp = 0.0
        if group_map is not None:
            allowed = group_map.get(st.group_index)
            if allowed is not None:
                grp = (S.SCORE_GROUP_MATCH if ref.group_index in allowed
                       else S.SCORE_GROUP_CONFLICT)
        pos = S.SCORE_POSITION_WEIGHT * (1.0 - abs(positions[i] - ref.position))
        total += lab + grp + pos
        rows.append((i, j, labels[i], ref.instrument, lab, grp, round(pos, 3)))
    gaps = len(reference) - len(used)
    total += S.GAP_PENALTY * gaps
    return round(total, 4), gaps, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("--pages", default="0-85")
    ap.add_argument("--alt", action="append", default=[],
                    help="SPAN:comma-separated global POSITIONS per local")
    args = ap.parse_args()

    pages = parse_pages(args.pages)
    loaded = load(args.cache, pages)
    vbp = {i: S._views(pws, S.labels_by_staff(labels))
           for i, (pws, labels) in loaded.items()}
    raw_by_page = {i: labels for i, (_p, labels) in loaded.items()}
    flat = [v for i in pages for v in vbp[i]]
    document = S.build_reference(flat)
    print(f"document reference: {len(document)} slots")
    for sl in document:
        print(f"   g{sl.index:2d} group={sl.group_index} "
              f"instrument={sl.instrument} pos={sl.position:.4f}")
    print(f"MECHANISM 2 CHECK: document slots WITH an instrument: "
          f"{sum(1 for s in document if s.instrument is not None)} of "
          f"{len(document)}")

    rows = [(i, [v.size for v in vbp[i]]) for i in pages]
    spans = movement_reference.lineup_spans(rows)
    alts = {}
    for a in args.alt:
        k, v = a.split(":", 1)
        alts.setdefault(int(k), []).append([int(x) for x in v.split(",")])

    for sn, span_pages in enumerate(spans):
        span_views = [v for p in span_pages for v in vbp.get(p, [])]
        sv = S.reference_view(span_views)
        print(f"\n=== SPAN {sn}: pages {min(span_pages)}-{max(span_pages)}, "
              f"{len(span_views)} systems")
        if sv is None:
            print("   NO REFERENCE VIEW")
            continue
        where = None
        for p in span_pages:
            for k, v in enumerate(vbp.get(p, [])):
                if v is sv:
                    where = (p, k)
        print(f"   reference system: page {where[0]} system#{where[1]} "
              f"size={sv.size}")
        print(f"   MECHANISM 1 CHECK: view.labels has {len(sv.labels)} entries, "
              f"keyed {sorted(sv.labels)[:20]}")
        print(f"   staff_index of staves: "
              f"{[st.staff_index for st in sv.staves]}")
        raw = {l.staff_index: (l.text,
                               l.instrument.name if l.matched else None,
                               l.confidence)
               for l in raw_by_page[where[0]]}
        for i, st in enumerate(sv.staves):
            t, nm, cf = raw.get(st.staff_index, ("<none>", None, "-"))
            print(f"      local {i:2d} staff_index={st.staff_index:2d} "
                  f"group={st.group_index} "
                  f"label={str(sv.labels.get(st.staff_index)):14s} "
                  f"raw={t!r:26s} matched={nm} conf={cf}")

        m, n = sv.size, len(document)
        print(f"   MECHANISM 3 CHECK: monotone envelope for m={m} into n={n}")
        for i in range(m):
            print(f"      local {i:2d} can reach globals "
                  f"{i}..{n - (m - i)}")

        mode = S.group_term_mode()
        gm = (None if mode == "off" else
              {g: {g} for g in {st.group_index for st in sv.staves}}
              if mode == "ordinal" else S.map_groups(sv, document))
        print(f"   group term mode={mode} map={gm}")

        chosen_idx = S.align(sv, document)
        idx_of = {sl.index: k for k, sl in enumerate(document)}
        chosen = [idx_of.get(g, -1) for g in chosen_idx]
        tot, gaps, rws = score_embedding(sv, document, chosen, gm)
        print(f"   CHOSEN embedding {chosen}  total={tot} gaps={gaps}")
        for i, j, lab, ins, lt, gt, pt in rws:
            flag = "  <-- LABEL CONFLICT" if lt < 0 else ""
            print(f"      l{i:2d}->g{j:2d}  label={str(lab):14s} "
                  f"slot={str(ins):14s} lab={lt:+5.1f} grp={gt:+4.1f} "
                  f"pos={pt:+.3f}{flag}")
        for alt in alts.get(sn, []):
            t2, g2, r2 = score_embedding(sv, document, alt, gm)
            print(f"   ALT embedding    {alt}  total={t2} gaps={g2} "
                  f"(chosen - alt = {round(tot - t2, 4)})")
            for i, j, lab, ins, lt, gt, pt in r2:
                flag = "  <-- LABEL CONFLICT" if lt < 0 else ""
                print(f"      l{i:2d}->g{j:2d}  label={str(lab):14s} "
                      f"slot={str(ins):14s} lab={lt:+5.1f} grp={gt:+4.1f} "
                      f"pos={pt:+.3f}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
