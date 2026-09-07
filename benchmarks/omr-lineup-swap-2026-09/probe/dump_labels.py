"""Dump the margin-label evidence a lineup-boundary rule could see, per page.

Reads the committed phase-1 + margin-reader caches (`compose.py`'s `PageCache`
pickles) and writes one JSON row per page:

    {page, systems: [n_staves...], peak, labels: [{staff_index, instrument,
     confidence, text}], n_matched}

⚠️ `StaffLabel.staff_index` is numbered ACROSS THE PAGE, not per system — the
same convention `draft_windows` documents — so the per-system split is done
here by staff ordinal, using the system sizes phase 1 recorded.

    dump_labels.py CACHEDIR --out out/labels-<work>.json
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for blob in sorted(Path(args.cache).glob("p*.pkl")):
        page_index = int(blob.stem[1:])
        pws, labels = pickle.loads(blob.read_bytes())
        sizes: dict[int, int] = {}
        for st in pws.staves:
            sizes[st.system_index] = sizes.get(st.system_index, 0) + 1
        systems = [sizes[k] for k in sorted(sizes)]
        rows.append({
            "page": page_index,
            "systems": systems,
            "n_staves": len(pws.staves),
            "labels": [
                {"staff_index": l.staff_index,
                 "instrument": l.instrument.name if l.instrument else None,
                 "confidence": l.confidence,
                 "text": l.text}
                for l in labels
            ],
        })
    Path(args.out).write_text(json.dumps(rows, indent=1))
    print(f"{len(rows)} pages -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
