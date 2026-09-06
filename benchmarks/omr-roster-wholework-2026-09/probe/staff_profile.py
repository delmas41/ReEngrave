"""Staff count per system for every page of a document — detector-free.

`slots.build_reference` picks "the largest size that appears more than once",
and `slots.align` can only delete on the reference side, so a system LARGER than
the reference loses its TOP staves and every staff below it takes the slot of
the staff above.  Both of those are decided entirely by this profile, which
costs a page render and `detect_staves` — no YOLO, no OCR, no contextual pass.

So this answers, cheaply and for a whole document, the question the roster's
premise rests on: is there ONE system size for the document, or does the
instrumentation step at a movement boundary?
"""
from __future__ import annotations

import json
import sys
import collections
import time
from pathlib import Path

from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves


def profile(pdf: Path, dpi: int = 600, limit: int | None = None):
    import fitz
    n = fitz.open(pdf).page_count
    if limit:
        n = min(n, limit)
    rows = []
    for pi in range(n):
        t0 = time.time()
        try:
            pws = detect_staves(render_page(pdf, pi, dpi=dpi))
        except Exception as exc:                                 # noqa: BLE001
            rows.append({"page": pi, "error": str(exc)[:120]})
            continue
        by_sys = collections.Counter(s.system_index for s in pws.staves)
        rows.append({"page": pi,
                     "systems": [by_sys[k] for k in sorted(by_sys)],
                     "staves": len(pws.staves),
                     "secs": round(time.time() - t0, 2)})
        r = rows[-1]
        print(f"  p{pi:3d}  systems={r['systems']}  staves={r['staves']}  "
              f"{r['secs']}s", flush=True)
    return rows


def main():
    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2])
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    print(f"### {pdf.name}", flush=True)
    rows = profile(pdf, limit=limit)
    sizes = collections.Counter(
        s for r in rows for s in r.get("systems", []))
    recurring = {k: v for k, v in sizes.items() if v > 1}
    print()
    print("system sizes  :", dict(sorted(sizes.items())))
    print("recurring     :", dict(sorted(recurring.items())))
    if recurring:
        print("build_reference would pick size:", max(recurring))
    print("largest system:", max(sizes) if sizes else None)
    out.write_text(json.dumps({"pdf": str(pdf), "rows": rows,
                               "sizes": dict(sizes)}, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
