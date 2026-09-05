#!/usr/bin/env python3
"""One disagreement, with both tiers' EVIDENCE side by side — for a human.

The classifier can say a work names Piccolo and a page does not.  It cannot say
whether the edition condenses the piccolo onto the flute staff, whether the
label was there and misread, or whether this printing genuinely has no piccolo.
Only the raw strings can, and both tiers store theirs verbatim for exactly this.

    python3 .../show_disagreement.py --verdict both --limit 12
    python3 .../show_disagreement.py --work-id brahms--symphony-1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from tools.library import edition_instrumentation as ed  # noqa: E402
from tools.library.score_library import CATALOG_PATH, load_catalog  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    ap.add_argument("--verdict")
    ap.add_argument("--work-id")
    ap.add_argument("--explained-by")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    catalog = load_catalog(args.catalog)
    works, editions = catalog.get("works", {}), catalog.get("editions", {})
    rows = ed.compare_catalog(catalog)
    if args.verdict:
        rows = [r for r in rows if r["verdict"] == args.verdict]
    if args.work_id:
        rows = [r for r in rows if r["work_id"] == args.work_id]
    if args.explained_by:
        rows = [r for r in rows if r.get("missing_explained_by") == args.explained_by]

    for row in rows[: args.limit]:
        held = editions[row["path"]]
        fact = held["instrumentation"]
        work = (works.get(row["work_id"], {}) or {}).get("instrumentation", {})
        print("=" * 78)
        print(f"{row['work_id']}   {row['verdict']}"
              f"  ({row.get('missing_explained_by', '')})")
        print(f"  {row['path']}")
        print(f"  score_type {fact['score_type']}"
              f"  yield {fact['quality']['yield']}"
              f"  page {fact['quality']['roster_page']}"
              f"  staves {fact['quality']['system_staves']}")
        print(f"\n  WORK raw ({work.get('roster_field', '-')}):")
        print("    " + (work.get("raw", {}).get("InstrDetail")
                        or work.get("raw", {}).get("Instrumentation") or "-")[:400])
        if work.get("unparsed"):
            print(f"    work-tier unparsed: {work['unparsed']}")
        print("\n  EDITION labels, verbatim, in printed order:")
        system = fact["raw"].get("system_index")
        idx = {i for item in fact["roster"] for i in item["staff_indices"]}
        idx |= {u["staff_index"] for u in fact["unparsed"]}
        for label in fact["raw"].get("labels", []):
            mark = " " if label["staff_index"] in idx else "~"   # other system
            print(f"   {mark}{label['staff_index']:3d}  {label['text']!r:34s}"
                  f" -> {label['instrument']}  ({label['confidence']})")
        print(f"    (roster taken from system {system}; ~ = another system)")
        if row.get("edition_missing"):
            print(f"\n  work only: {', '.join(row['edition_missing'])}")
        if row.get("edition_extra"):
            print(f"  page only: {', '.join(row['edition_extra'])}")
    print(f"\n{len(rows)} rows matched; showed {min(len(rows), args.limit)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
