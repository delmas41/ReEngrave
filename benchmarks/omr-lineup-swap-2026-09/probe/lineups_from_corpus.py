"""The identity harness's hand-read lineups, in `--lineups` shape.

⚠️ A BUILD PRODUCT, not truth. The truth for Beethoven 5 and Brahms 1 lives in
`benchmarks/omr-identity-harness-2026-09/probe/corpus.py` and is not copied
here — a hand reading held in two places is a hand reading that can disagree
with itself.

    lineups_from_corpus.py beet5 --out out/lineups-beet5.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1].parent
                       / "omr-identity-harness-2026-09" / "probe"))

import corpus  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = [{"first": lo, "last": hi, "size": n, "lineup": names,
             "read_off": f"corpus.LINEUPS[{args.work!r}] — "
                         f"{corpus.PUBLISHER.get(args.work, '')}"}
            for lo, hi, n, names in corpus.LINEUPS[args.work]]
    Path(args.out).write_text(json.dumps(rows, indent=1))
    print(f"{len(rows)} lineups -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
