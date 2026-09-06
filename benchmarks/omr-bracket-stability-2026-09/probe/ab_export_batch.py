"""Full-pipeline A/B of the exported MusicXML, flag off vs flag on, over a set
of PDFs.

This is deliberately STRONGER than an OMR-NED A/B and cheaper than one. A
byte-identical export implies an identical OMR-NED with no noise floor to argue
about, where the 20-row scan gate carries ~±6 edits of run-to-run noise and a
pooled figure would have to be read against it.

⚠ The direction-text reader is forced OFF in both arms. It is orthogonal to
bracket grouping and it is the one stage this repo records as non-deterministic
(Surya temperature), so leaving it on would put noise into a byte-identity
claim.

⚠ Each arm writes its own file. No shared output path, so there is no cached-
A/B trap: two arms that never write the same name cannot silently reuse each
other's work. The wall-clock line per arm is printed for the same reason.

Usage: ab_export_batch.py --page=0 --outdir DIR PDF...
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.transcribe import transcribe, DEFAULT_WEIGHTS   # noqa: E402
from tools.omr.export import to_musicxml                       # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for pdf in args.pdfs:
        tag = Path(pdf).stem
        texts: dict[str, str | None] = {}
        for flag in ("0", "1"):
            os.environ["OMR_BRACKET_COLUMNS"] = flag
            t0 = time.time()
            try:
                result = transcribe(pdf_path=Path(pdf), pages=[args.page],
                                    weights=DEFAULT_WEIGHTS, progress=False,
                                    dpi=args.dpi, read_direction_text=False)
                texts[flag] = to_musicxml(result)
            except Exception as exc:                          # noqa: BLE001
                print(f"  !! {tag} flag={flag}: {type(exc).__name__}: {exc}",
                      flush=True)
                texts[flag] = None
            (outdir / f"{tag}-flag{flag}.musicxml").write_text(texts[flag] or "")
            print(f"  {tag} flag={flag}: {len(texts[flag] or '')} bytes "
                  f"in {time.time() - t0:.0f}s", flush=True)
        same = texts["0"] is not None and texts["0"] == texts["1"]
        changed: list[str] = []
        if texts["0"] is not None and texts["1"] is not None and not same:
            d = difflib.unified_diff(texts["0"].splitlines(),
                                     texts["1"].splitlines(), n=0)
            changed = [ln for ln in d
                       if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
        rows.append({"pdf": tag, "identical": same,
                     "changed_lines": len(changed), "sample": changed[:12]})
        print(f"  -> {tag}: "
              f"{'BYTE-IDENTICAL' if same else str(len(changed)) + ' changed lines'}",
              flush=True)

    n_same = sum(r["identical"] for r in rows)
    print(f"\n{n_same} of {len(rows)} byte-identical")
    for r in rows:
        if not r["identical"]:
            print(f"  {r['pdf']}: {r['changed_lines']} lines")
            for ln in r["sample"]:
                print("      ", ln.rstrip())
    (outdir / "summary.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
