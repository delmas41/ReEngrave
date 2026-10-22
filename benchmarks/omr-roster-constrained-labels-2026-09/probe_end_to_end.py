#!/usr/bin/env python3
"""The production label ladder, flag OFF vs ON, on real pages of both families.

The reach probe scores strings; this one runs
`contextual._labels_for_page` — the wiring — over pages that are actually read,
and diffs the resolutions staff by staff. It is the check that the layer is
wired where it is documented to be wired, and that OFF really is OFF.

    python3 benchmarks/omr-roster-constrained-labels-2026-09/probe_end_to_end.py \
        --library-root /Users/seanjohnson/Desktop/ReEngrave

⚠️ `library/` is machine-local and gitignored, so from a git WORKTREE this must
be pointed at the main checkout — the same trap
`benchmarks/omr-margin-window-truncation-2026-09/probe_edge_separation.py`
records, where an absent library reads as "no page has this fault".

⚠️ The free ladder here is the TEXT LAYER only (`--no-surya`, the default).
Surya's server is shared between sessions and CLAUDE.md forbids blanket-killing
it; the pages chosen carry a text layer, so the rung is not needed to reach the
labels this measures.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import contextual, work_roster as W          # noqa: E402
from tools.omr.preprocessing import render_page             # noqa: E402
from tools.omr.staff_detector import detect_staves          # noqa: E402

#: (id, family, path under the library root or an absolute path, page, work-id
#: override). The engraved fixtures are build products OUTSIDE the store, so
#: they need the override; the editions do not and are read the way production
#: reads them.
PAGES = [
    ("beethoven5-575951 p1", "scan+textlayer",
     "library/editions/beethoven/symphony-5-op67/"
     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp575951.pdf",
     0, None),
    ("ravel-bolero p1", "scan+textlayer",
     "library/editions/ravel/bolero-m-81/"
     "ravel--bolero-m-81--2016--imslp421137.pdf", 0, None),
    ("tchaikovsky-sym6-mvt2 (fixture)", "engraved",
     "benchmarks/omr-orchestral-e2e/fixtures/tchaikovsky-sym6-mvt2.pdf",
     0, "tchaikovsky--symphony-6"),
    ("mozart-sym40-mvt1 (fixture)", "engraved",
     "benchmarks/omr-orchestral-e2e/fixtures/mozart-sym40-mvt1.pdf",
     0, "mozart--symphony-40"),
]


class _NoAssist:
    mode = "none"


def read(pdf: Path, page_index: int, dpi: int) -> list:
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    return contextual._labels_for_page(
        pws, pdf, page_index, assist=_NoAssist(), budget=[0],
        surya_fallback=False, ocr_fallback=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--library-root", type=Path, default=ROOT)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", type=Path, default=BENCH / "end-to-end.json")
    args = ap.parse_args(argv)

    rows = []
    for name, family, rel, page_index, override in PAGES:
        pdf = Path(rel) if Path(rel).is_absolute() else args.library_root / rel
        if not pdf.is_file():
            print(f"{name:34} MISSING {pdf}")
            continue
        os.environ.pop("OMR_ROSTER_LABELS", None)
        os.environ.pop("OMR_WORK_ID", None)
        W._roster_for_pdf.cache_clear()
        off = read(pdf, page_index, args.dpi)

        os.environ["OMR_ROSTER_LABELS"] = "1"
        if override:
            os.environ["OMR_WORK_ID"] = override
        on = read(pdf, page_index, args.dpi)
        os.environ.pop("OMR_ROSTER_LABELS", None)
        os.environ.pop("OMR_WORK_ID", None)

        def named(labels):
            return {lab.staff_index: (lab.text,
                                      lab.instrument.name if lab.instrument else None,
                                      lab.confidence) for lab in labels}
        a, b = named(off), named(on)
        changed = [(i, a[i], b[i]) for i in sorted(a) if a[i] != b[i]]
        roster = W.work_roster(override) if override else W.roster_for_pdf(pdf)
        print(f"{name:34} {family:16} {len(a):3d} labels  "
              f"roster={'yes' if roster else 'NO '}  changed={len(changed)}")
        for i, x, y in changed:
            print(f"    staff {i:2d}  {x[0]!r:26} {str(x[1]):>12} [{x[2]}]"
                  f"  ->  {str(y[1]):<12} [{y[2]}]")
        rows.append({"page": name, "family": family, "labels": len(a),
                     "roster": bool(roster), "changed": len(changed),
                     "diff": [{"staff": i, "text": x[0], "off": x[1],
                               "on": y[1]} for i, x, y in changed]})

    args.out.write_text(json.dumps(rows, indent=1) + "\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
