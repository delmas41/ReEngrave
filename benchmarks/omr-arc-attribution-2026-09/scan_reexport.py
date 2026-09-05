"""Re-export a scan-e2e row's CACHED transcription under a new tag.

The arc-attribution change is export-only, so the scan A/B needs one YOLO run
per row and two exports — not two runs. This copies `<row>.<src>.omr.json` to
`<row>.<dst>.omr.json` and writes `<row>.<dst>.omr.musicxml` with the current
tree's exporter and whatever `OMR_ARC_ATTRIBUTION` says. `scan_eval.py --tag
<dst> --score-only` then scores it against the same trimmed truth.
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.export import to_musicxml  # noqa: E402

FIXTURES = ROOT / "benchmarks/omr-scan-e2e-2026-09/fixtures"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="+")
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    args = ap.parse_args()
    for rid in args.rows:
        src = FIXTURES / f"{rid}.{args.src}.omr.json"
        dst = FIXTURES / f"{rid}.{args.dst}.omr.json"
        if not src.is_file():
            raise SystemExit(f"missing {src}")
        if src != dst:
            shutil.copyfile(src, dst)
        result = json.loads(src.read_text())
        out = FIXTURES / f"{rid}.{args.dst}.omr.musicxml"
        out.write_text(to_musicxml(result))
        n = (result.get("_arc_attribution") or {}).get("n_reattributed")
        print(f"{rid}: {out.name} ({out.stat().st_size} bytes) "
              f"arcs_reattributed={n}")


if __name__ == "__main__":
    main()
