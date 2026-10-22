"""Render an ENGRAVED fixture whose ink is known exactly, for the STAGED path.

    python3 benchmarks/omr-staged-engraved-2026-09/render_fixture.py \
        --work beethoven-sym5-mvt1 --first 1 --last 24 --out-dir <dir> --dpi 300

⚠️ WHY VEROVIO AND NOT LILYPOND. `benchmarks/omr-staged-meter-engraved-2026-09`
renders through `musicxml2ly` + LilyPond, which is right for the question it
asks (what does `Q.METER` decide per SYSTEM — nothing is scored against a truth
file). This lane needs a truth about the PAGE, and `tools/omr/page_truth.py`
gets one for free ONLY from a Verovio render, because the boxes and the image
come out of the SAME act. A LilyPond page has no per-glyph inventory at all.

⚠️ THE DPI IS THE SAME NUMBER ON BOTH SIDES OR NOTHING MATCHES. `page_truth`
emits its boxes in image pixels at `--dpi`; the staged pipeline rasterises the
PDF at its own `--dpi`. Two different values differ by a pure scale factor, and
the failure looks like a recognition result (counts agree, positions do not) —
the frame error `page_truth`'s own docstring records paying for once already.
So this script PRINTS the number the staged run must be given.

⚠️ EXCERPTING IS music21's, AND THE FILE IS THE SUBSTRATE. `measures()` carries
the prevailing meter into the excerpt's first bar on WRITE and a query against
the in-memory object says otherwise, so every fact quoted downstream is read
back off the written MusicXML — the rule `render_meter_change.meter_map`
already states.
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SCORE_DIR = Path("/Users/seanjohnson/Desktop/gradus-vercel/public/scores")


def excerpt(work_id: str, first: int, last: int, out_dir: Path) -> Path:
    from music21 import converter

    src = None
    for suffix in (".mxl", ".musicxml"):
        cand = SCORE_DIR / f"{work_id}{suffix}"
        if cand.is_file():
            src = cand
            break
    if src is None:
        raise FileNotFoundError(f"no score for {work_id} under {SCORE_DIR}")

    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = converter.parse(str(src))
    score = parsed.measures(first, last)
    xml = out_dir / f"{work_id}-m{first}-{last}.musicxml"
    score.write("musicxml", fp=str(xml))
    return xml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=300)
    a = ap.parse_args()

    xml = excerpt(a.work, a.first, a.last, a.out_dir)
    print(f"excerpt: {xml}  ({xml.stat().st_size} bytes)")

    from tools.omr.page_truth import build
    truth = build(xml, a.out_dir, dpi=a.dpi)

    print(f"\nrenderer {truth['renderer']}  dpi {truth['dpi']}  "
          f"pages {len(truth['pages'])}")
    print(f"render_fidelity: {json.dumps(truth['render_fidelity'])}")
    for p in truth["pages"]:
        c = Counter(s["family"] for s in p["symbols"])
        print(f"  page {p['page_index'] + 1}: {p['image_w']}x{p['image_h']} px, "
              f"{len(p['symbols'])} symbols")
        print(f"     {dict(c.most_common())}")
    print(f"\nPDF: {a.out_dir / truth['pdf']}")
    print(f"⚠️ the staged run MUST use --dpi {a.dpi}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
