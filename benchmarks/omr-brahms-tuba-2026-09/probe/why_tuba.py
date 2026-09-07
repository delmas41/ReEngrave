"""Why is Brahms 1's finale slot 9 named `Tuba`?

Measures, rather than asserts, the mechanism:

1. the `instrument_source` of every emitted `Tuba` staff record, from the
   committed compose blobs (no re-transcription);
2. the layout fit reproduced OFFLINE from the same blob's own
   label/roster-sourced slots, so the proposal can be inspected part by part;
3. the alignment ARITHMETIC — what `align_to_layout` scores for the winning
   layout, and what the alternative reading (slot 9 as a CONTINUATION of the
   trombone part) would have scored.

Usage:  why_tuba.py BLOB.json [BLOB.json ...]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.score_layouts import (  # noqa: E402
    LAYOUTS, ScoreLayout, align_to_layout, fit_layouts)


def blob_of(path: str) -> dict:
    r = json.loads(Path(path).read_text())
    b = (r.get("contextual") or {}).get("absent_instrument_veto")
    if not b:
        raise SystemExit(f"REFUSING: {path} has no absent_instrument_veto block")
    return r, b


def main(paths: list[str]) -> None:
    for path in paths:
        r, b = blob_of(path)
        print(f"\n{'=' * 72}\n{path}\n{'=' * 72}")
        si = {s["slot"]: s for s in b["slot_instruments"]}
        slot_of = {(s["page_index"], s["system_index"], s["staff_index"]):
                   s["slot"] for s in b["staff_slots"]}

        # ── 1. the instrument_source split over every emitted Tuba record ────
        tuba_slots = {k for k, v in si.items() if v["instrument"] == "Tuba"}
        recs = [k for k, sl in slot_of.items() if sl in tuba_slots]
        src = collections.Counter(si[slot_of[k]]["source"] for k in recs)
        print(f"reference_size={b['reference_size']}  slots named Tuba: "
              f"{sorted(tuba_slots)}")
        print(f"staff records landing on a Tuba slot: {len(recs)}")
        print(f"  instrument_source split: {dict(src)}")
        pages = sorted({k[0] for k in recs})
        print(f"  pages: {pages[0]}-{pages[-1]}  ({len(pages)} pages)"
              if pages else "  pages: none")

        # ── 2. the fit, reproduced from the blob's own read evidence ─────────
        labels = {k: v["instrument"] for k, v in si.items()
                  if v["source"] in ("label", "roster")}
        n = b["reference_size"]
        print(f"\nlabels fed to fit_layouts (n={n}): "
              f"{ {k: labels[k] for k in sorted(labels)} }")
        fit = fit_layouts(n, labels=labels, clefs=None)
        if fit is None:
            print("  fit_layouts -> None")
            continue
        print(f"  best layout: {fit.layout.name}  "
              f"score/staff={fit.score_per_staff:.3f}")
        print(f"  voters: {fit.considered}")
        for i, (a, g, s) in enumerate(
                zip(fit.assignment, fit.agreement, fit.support)):
            mark = "   <<< the fault" if si.get(i, {}).get(
                "instrument") == "Tuba" else ""
            sup = {k: round(v, 2) for k, v in sorted(
                s.items(), key=lambda kv: -kv[1])}
            print(f"   {i:2d} emitted={si.get(i, {}).get('instrument'):<14s}"
                  f" src={si.get(i, {}).get('source'):<12s}"
                  f" fit={str(a):<14s} agr={g:.2f} {sup}{mark}")

        # ── 3. the arithmetic ───────────────────────────────────────────────
        print("\n  per-layout score/staff, all layouts:")
        rows = []
        for lay in LAYOUTS:
            total, assign = align_to_layout(lay, n, labels, None)
            rows.append((total / n, lay.name, assign))
        for sc, name, assign in sorted(rows, reverse=True):
            at9 = assign[9] if len(assign) > 9 else None
            print(f"   {sc:8.3f}  {name:<22s} slot9={at9}")
    print()


if __name__ == "__main__":
    main(sys.argv[1:])
