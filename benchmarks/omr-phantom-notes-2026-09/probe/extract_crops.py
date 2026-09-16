"""Pull the PRINT out of the committed side-by-side artefact.

⚠️ This container has no `omr-weights/` and no `library/`, so no page can be
rasterised here (`docs/cloud-session-capabilities-2026-09-09.md`). The only
copy of the Litolff plate that reaches this session is the set of data-URI PNGs
embedded in
`benchmarks/omr-cleanup-count-2026-09/out/side-by-side-p1-p4.html`, one per
printed system, written by `build_sidebyside.py` on a machine that had both.

Exits non-zero if it finds none -- an empty crop set would otherwise let a
"looked at the print" claim be made over nothing.
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
HTML = HERE / "benchmarks/omr-cleanup-count-2026-09/out/side-by-side-p1-p4.html"

IMG = re.compile(r'data:image/png;base64,([A-Za-z0-9+/=]+)')
# The section heading carries the system's identity and its measure span.
HEAD = re.compile(r"<div class='head'>(.*?)</div>", re.S)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", default=str(HTML))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = Path(args.html).read_text(errors="replace")
    blobs = IMG.findall(text)
    if not blobs:
        print("DEAD: no embedded PNG found in the side-by-side artefact",
              file=sys.stderr)
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Context: the nearest preceding <section> heading, so a crop can be named.
    heads = [re.sub(r"<[^>]+>", " ", h).strip() for h in HEAD.findall(text)]
    print(f"REACH  sections={len(heads)}  embedded PNGs={len(blobs)}")
    for i, h in enumerate(heads):
        print(f"  section {i}: {' '.join(h.split())[:150]}")

    for i, b in enumerate(blobs):
        raw = base64.b64decode(b)
        p = out / f"crop{i:02d}.png"
        p.write_bytes(raw)
        print(f"  wrote {p.name}  {len(raw)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
