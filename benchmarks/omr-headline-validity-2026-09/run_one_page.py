"""Run ONE real scanned page through the pipeline at the scan gate's protocol.

Sean asked for this explicitly — *"run the PDF through it to see what it
captures"* — so this does a FRESH transcription rather than reading the stored
fixture, and writes both the raw JSON and the exported MusicXML into this
benchmark's own directory. The protocol is copied from
`benchmarks/omr-scan-e2e-2026-09/works.json` (600 dpi, no dossier, pipeline
defaults), not re-decided here.

    OMR_SURYA_KEEP_ALIVE=0 python3 \
        benchmarks/omr-headline-validity-2026-09/run_one_page.py \
        --row beethoven-sym5-mvt1-984073-p1

⚠️ `OMR_SURYA_KEEP_ALIVE=0` on purpose: the resident Surya server is SHARED and
an unattended run must not depend on state it is not allowed to repair.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402
from tools.omr.transcribe import DEFAULT_WEIGHTS, transcribe  # noqa: E402

SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
OUT = BENCH / "live-run"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", required=True)
    args = ap.parse_args(argv)

    doc = json.loads((SCAN / "works.json").read_text())
    protocol = doc["protocol"]
    row = next(r for r in doc["rows"] if r["row_id"] == args.row)
    pdf = library_root() / row["edition"]["catalog_path"]
    page = row["page"]["pdf_page_index"]

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"transcribing {pdf.name} page {page} at {protocol['dpi']} dpi …",
          flush=True)
    t0 = time.time()
    result = transcribe(pdf_path=pdf, pages=[page],
                        weights=str(DEFAULT_WEIGHTS),
                        dpi=protocol["dpi"],
                        conf_threshold=protocol["conf_threshold"],
                        imgsz=protocol["imgsz"], dossier=None,
                        read_direction_text=protocol["read_direction_text"],
                        progress=False)
    result["_seconds"] = round(time.time() - t0, 1)
    (OUT / f"{args.row}.live.omr.json").write_text(
        json.dumps(result, default=str) + "\n")
    (OUT / f"{args.row}.live.omr.musicxml").write_text(to_musicxml(result))
    print(f"done in {result['_seconds']}s -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
