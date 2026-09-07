"""A label dump in `dump_labels.py`'s shape, out of a composed run's own blob.

`compose.py`'s output already carries everything the swap detector needs and
nothing else does: `absent_instrument_veto.staff_slots` gives every staff its
`(page, system, staff_index)`, and `label_evidence` gives the resolved margin
name per `(page, staff_index)`. So a work that has a committed composed run —
Brahms 1, Beethoven 5 — can be measured with **no re-read at all**.

⚠️ `label_evidence` is the aligner's own view, i.e. already filtered to
`slots.MIN_LABEL_CONFIDENCE`, so a dump made this way must NOT be filtered
again. `--confidence` is written as `high` to say so, and
`selftest.py` checks one work both ways.

    labels_from_blob.py ARM.json --out out/labels-<work>.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    b = json.load(open(args.arm))["contextual"]["absent_instrument_veto"]
    per_page: dict[int, dict[int, list[int]]] = {}
    for s in b["staff_slots"]:
        per_page.setdefault(s["page_index"], {}).setdefault(
            s["system_index"], []).append(s["staff_index"])
    labels: dict[int, dict[int, str]] = {}
    for e in b["label_evidence"]:
        labels.setdefault(e["page_index"], {})[e["staff_index"]] = \
            e["instrument"]

    rows = []
    for page in sorted(per_page):
        systems = [len(per_page[page][si]) for si in sorted(per_page[page])]
        rows.append({
            "page": page,
            "systems": systems,
            "n_staves": sum(systems),
            "labels": [{"staff_index": k, "instrument": v,
                        "confidence": "high", "text": ""}
                       for k, v in sorted(labels.get(page, {}).items())],
        })
    Path(args.out).write_text(json.dumps(rows, indent=1))
    print(f"{len(rows)} pages, "
          f"{sum(len(r['labels']) for r in rows)} labels -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
