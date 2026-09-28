#!/usr/bin/env python3
"""ROADMAP 2.11b, step 1 — MEASURE the per-family `Q.CLEF_POSITION` band,
off the records, before any code changes.

2.11 found that a `clefG` detector box on Brahms 1 p.6 `staff/6/1/3` sits at
`Q.CLEF_POSITION` 19.36 (~5.7 staff spaces below the bottom line — a
neighbouring staff's clef bleeding into this staff's padded cell) and
decides `treble` UNOPPOSED, because `adjudicate_clef` reads `Q.CLEF_GLYPH`
and never reads the position row filed beside it. This probe answers, from
the three acceptance documents' own records (`benchmarks/acceptance/
manifest.json`), read-only, no gather:

  * where each clef FAMILY's detector box actually centres, in
    `Q.CLEF_POSITION` steps (half-spaces down from the staff's TOP line,
    lines at 0/2/4/6/8 — `gather.py`'s own unit);
  * the GAP in that histogram that separates "printed on or near this
    staff" from "a neighbour's clef in the padding";
  * how many rows the cut would flag, per document, per family.

⚠️ STREAMED, NOT LOADED. The Litolff and Breitkopf shared records are
280-480 MB and this machine is running a heavy whole-movement re-gather
concurrently (roadmap item 0) — `record_io.load_record` parses the WHOLE
file (observations, abstentions, verdicts and their pooled id lists) into
memory at once, which is the wrong tool for reading two quantities.
`tools.omr.positional_store.stream_observations` (roadmap 1.1b) yields one
`record.observations` item at a time via `ijson`, one in flight, and never
touches `verdicts` or the pools at all — the same property `record_slim.py`
relies on. This probe reads ONLY observations, so streaming loses nothing
it needs.

The `y_center` match between a `Q.CLEF_GLYPH` row (reader=DETECTOR) and its
`Q.CLEF_POSITION` row (reader=GEOMETRY) is the SAME join `adjudicate_clef.
_on_staff_rows` already performs per-staff — done here across a whole
document at once, keyed on `(subject, y_center)` because two different
staves' glyphs can legitimately share a y_center value once cast to float
(the padded cell reaches a neighbour's ink, per CLAUDE.md Sec.10).

Usage:
    python3 benchmarks/omr-clef-geometry-2026-09/probe/price_position_bands.py \
        --manifest benchmarks/acceptance/manifest.json \
        --out-json benchmarks/omr-clef-geometry-2026-09/out/position-bands.json
    # one document only, while iterating:
    ... --only beethoven5-engraved
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.omr.positional_store import stream_observations    # noqa: E402
from tools.library.score_library import library_root          # noqa: E402
from tools.omr.clef_geometry import clef_family                # noqa: E402


def _resolve(root: str, path: str) -> Path:
    base = library_root() if root == "library" else _REPO
    return base / path


def _band(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"n": 0}
    s = sorted(values)
    return {"n": len(s), "min": round(s[0], 3), "max": round(s[-1], 3),
             "median": round(statistics.median(s), 3)}


def _largest_gap(values: List[float]) -> Optional[Tuple[float, float, float]]:
    """`(low, high, width)` of the widest empty run between two SORTED,
    DE-DUPLICATED values — the same idiom 2.11's own docstring used
    ("nothing between +3.5 and +13.3") to name a cut from an absence rather
    than a guess."""
    uniq = sorted(set(round(v, 4) for v in values))
    if len(uniq) < 2:
        return None
    best = max(range(len(uniq) - 1), key=lambda i: uniq[i + 1] - uniq[i])
    return uniq[best], uniq[best + 1], round(uniq[best + 1] - uniq[best], 3)


def price(record_path: Path, doc_id: str) -> Dict[str, Any]:
    # (subject, y_center) -> [(class_name, score)] for the DETECTOR's own
    # clef glyph rows.
    glyphs_by_key: Dict[Tuple[str, float], List[Tuple[str, Optional[float]]]] = {}
    # (subject, y_center) -> position value, GEOMETRY reader.
    positions_by_key: Dict[Tuple[str, float], float] = {}
    n_glyph_rows = 0

    for o in stream_observations(record_path):
        q = o.get("quantity")
        if q == "clef_glyph" and o.get("reader") == "detector":
            d = o.get("detail") or {}
            yc = d.get("y_center")
            if yc is None:
                continue
            n_glyph_rows += 1
            key = (o["subject"], round(float(yc), 3))
            glyphs_by_key.setdefault(key, []).append(
                (str(o["value"]), o.get("score")))
        elif q == "clef_position" and o.get("reader") == "geometry":
            d = o.get("detail") or {}
            yc = d.get("y_center")
            if yc is None:
                continue
            key = (o["subject"], round(float(yc), 3))
            try:
                positions_by_key[key] = float(o["value"])
            except (TypeError, ValueError):
                continue

    by_family: Dict[str, List[float]] = {}
    unmatched = 0
    matched = 0
    rows: List[Dict[str, Any]] = []
    for key, glyphs in glyphs_by_key.items():
        pos = positions_by_key.get(key)
        for class_name, score in glyphs:
            fam = clef_family(class_name)
            if fam is None:
                continue
            if pos is None:
                unmatched += 1
                continue
            matched += 1
            by_family.setdefault(fam, []).append(pos)
            rows.append({"subject": key[0], "family": fam,
                         "class": class_name, "score": score,
                         "position": round(pos, 3)})

    bands = {fam: _band(v) for fam, v in sorted(by_family.items())}
    gaps = {fam: _largest_gap(v) for fam, v in by_family.items()}

    return {
        "document": doc_id,
        "n_glyph_rows_seen": n_glyph_rows,
        "n_matched_to_a_position_row": matched,
        "n_unmatched": unmatched,
        "bands_by_family": bands,
        "largest_gap_by_family": gaps,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="benchmarks/acceptance/manifest.json")
    ap.add_argument("--only", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    results = []
    all_by_family: Dict[str, List[float]] = {}
    for doc in manifest["documents"]:
        if args.only and doc["id"] != args.only:
            continue
        rp = _resolve(doc["record"]["root"], doc["record"]["path"])
        if not rp.exists():
            print(f"-- {doc['id']}: MISSING {rp}", file=sys.stderr)
            continue
        print(f"-- pricing {doc['id']} ({rp.name}, "
              f"{rp.stat().st_size / 1e6:.0f} MB, streamed)...", file=sys.stderr)
        result = price(rp, doc["id"])
        for row in result["rows"]:
            all_by_family.setdefault(row["family"], []).append(row["position"])
        results.append(result)
        print(f"   glyph rows {result['n_glyph_rows_seen']}, "
              f"matched {result['n_matched_to_a_position_row']}, "
              f"unmatched {result['n_unmatched']}", file=sys.stderr)
        for fam, band in result["bands_by_family"].items():
            print(f"   {fam}: {band}  gap={result['largest_gap_by_family'].get(fam)}",
                  file=sys.stderr)

    pooled = {
        "bands_by_family": {fam: _band(v) for fam, v in sorted(all_by_family.items())},
        "largest_gap_by_family": {fam: _largest_gap(v) for fam, v in all_by_family.items()},
    }
    print("-- POOLED across all documents priced --", file=sys.stderr)
    for fam, band in pooled["bands_by_family"].items():
        print(f"   {fam}: {band}  gap={pooled['largest_gap_by_family'].get(fam)}",
              file=sys.stderr)

    out = {"per_document": results, "pooled": pooled}
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(out, indent=2))
        print(f"-- wrote {args.out_json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
