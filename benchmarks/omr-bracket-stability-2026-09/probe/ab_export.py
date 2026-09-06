"""Full-pipeline A/B of the exported MusicXML for one page, both arms.

⚠ The direction-text reader is forced OFF in both arms. It is orthogonal to
bracket grouping and it is the one stage this repo records as
non-deterministic (Surya temperature), so leaving it on would put noise into a
byte-identity claim.

The cue-C control (`probe_cue_c_reach.py`) says the change cannot reach the
barlines on the scan gate; this checks the whole export anyway, on the rows
most exposed to it, because "cannot reach" is a claim about the code and this
is a claim about the file.

Each arm writes its own file — no shared output path, so there is no cached-A/B
trap to fall into.

Usage: ab_export.py PDF --page=0 --tag=bach [--weights ...]
"""
from __future__ import annotations

import argparse
import difflib
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.transcribe import transcribe, DEFAULT_WEIGHTS   # noqa: E402
from tools.omr.export import to_musicxml                       # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    paths = {}
    for flag in ("0", "1"):
        os.environ["OMR_BRACKET_COLUMNS"] = flag
        t0 = time.time()
        result = transcribe(pdf_path=Path(args.pdf), pages=[args.page],
                            weights=DEFAULT_WEIGHTS, progress=False,
                            dpi=args.dpi, read_direction_text=False)
        xml = to_musicxml(result)
        p = OUT / f"ab-export-{args.tag}-flag{flag}.musicxml"
        p.write_text(xml)
        paths[flag] = p
        print(f"  arm flag={flag}: {len(xml)} bytes in {time.time() - t0:.0f}s")

    a = paths["0"].read_text().splitlines()
    b = paths["1"].read_text().splitlines()
    if a == b:
        print(f"\n{args.tag}: BYTE-IDENTICAL")
        return
    diff = list(difflib.unified_diff(a, b, "flag0", "flag1", n=1))
    changed = [ln for ln in diff if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
    print(f"\n{args.tag}: {len(changed)} changed lines")
    only_names = all("part-name" in ln or "instrument-name" in ln
                     or "<part-abbreviation" in ln for ln in changed)
    print(f"  every changed line is a part NAME: {only_names}")
    for ln in diff[:60]:
        print("   ", ln.rstrip())


if __name__ == "__main__":
    main()
