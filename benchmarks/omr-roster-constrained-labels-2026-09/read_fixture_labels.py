#!/usr/bin/env python3
"""Dump the PRODUCTION reader's margin strings for the engraved fixtures.

`benchmarks/omr-margin-window-truncation-2026-09/truncation.json` holds the
same page's text SPANS, joined without spaces (`'larinettiinB.'`). That is the
right artifact for asking whether ink is on the paper and the wrong one for
asking what the lexicon is handed: `staff_labels.read_staff_labels` joins spans
in reading order WITH spaces (`'larinetti in B.'`), and a rule that reads tokens
sees a completely different string. So the corpus is re-read through the
production path, off the committed control PDFs.

    python3 benchmarks/omr-roster-constrained-labels-2026-09/read_fixture_labels.py

Costs one render + one staff detect per fixture (~1 min for eleven). No YOLO
weights involved — this is phase 1 and the text layer.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page              # noqa: E402
from tools.omr.staff_detector import detect_staves           # noqa: E402
from tools.omr.staff_labels import read_staff_labels         # noqa: E402

DEFAULT_FIXTURES = (ROOT / "benchmarks" / "omr-margin-window-truncation-2026-09"
                    / "out" / "fixtures-control")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    ap.add_argument("--out", type=Path, default=BENCH / "fixture-labels.json")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args(argv)

    rows = []
    for pdf in sorted(args.fixtures.glob("*.pdf")):
        page = render_page(pdf, 0, dpi=args.dpi)
        pws = detect_staves(page)
        labels = read_staff_labels(pws)
        rows.append({"work": pdf.stem, "n_staves": len(pws.staves),
                     "labels": [{"staff_index": lab.staff_index,
                                 "text": lab.text} for lab in labels]})
        print(f"{pdf.stem:26} {len(pws.staves):3d} staves  "
              f"{len(labels):3d} labels")
    args.out.write_text(json.dumps(rows, indent=1) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
