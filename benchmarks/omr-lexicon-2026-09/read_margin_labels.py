#!/usr/bin/env python3
"""Dump every RAW margin string a page's readers produce, with its resolution.

The lexicon is fed strings by `contextual._labels_for_page`, not by MusicXML
part names, so a lexicon change can only be judged on what the readers actually
emit. This runs the free ladder (PDF text layer, then Surya) over a list of
pages and writes one record per staff: the printed string, and what
`instruments.lookup` makes of it.

    python3 benchmarks/omr-lexicon-2026-09/read_margin_labels.py --pages pages.json --out labels.json

Reading is expensive and the strings do not change when the lexicon does, so the
dump is the artifact and `resolve_labels.py` scores it offline.

⚠️ BOTH readers run on every page by default, which is a WIDER net than
production takes — `contextual._labels_for_page` runs Surya only where the text
layer came back thin. That is deliberate here (a garbled OCR read is exactly the
population a lexicon change could misfire on) and it is the whole cost: a
25-staff Boléro page the text layer already answers still pays several minutes
of Surya. `--ladder` takes the production path instead, and is the right flag
when you want a faithful sample rather than the widest one.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402
from tools.omr.staff_labels import read_staff_labels     # noqa: E402
from tools.omr import staff_labels_surya                 # noqa: E402


def read_page(pdf: Path, page_index: int, dpi: int, *,
              ladder: bool = False) -> list[dict]:
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    if not pws.staves:
        return []
    text = read_staff_labels(pws)
    run_surya = staff_labels_surya.available() and not (ladder and text)
    out: list[dict] = []
    for reader, labels in (("text", text),
                           ("surya", staff_labels_surya.read_staff_labels_surya(pws)
                            if run_surya else [])):
        for lab in labels:
            out.append({"reader": reader, "staff_index": lab.staff_index,
                        "text": lab.text})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=Path, required=True,
                    help="JSON list of {id, pdf, page_index}")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--only", default=None, help="substring filter on id")
    ap.add_argument("--ladder", action="store_true",
                    help="production path: skip Surya where the text layer read "
                         "anything. Much cheaper, and a faithful sample rather "
                         "than the widest one.")
    args = ap.parse_args(argv)

    spec = json.loads(args.pages.read_text())
    records: list[dict] = []
    for entry in spec:
        if args.only and args.only not in entry["id"]:
            continue
        pdf = Path(entry["pdf"])
        if not pdf.is_file():
            print(f"  MISSING {entry['id']}: {pdf}", file=sys.stderr)
            continue
        for page_index in entry["page_indices"]:
            try:
                got = read_page(pdf, page_index, args.dpi, ladder=args.ladder)
            except Exception as exc:                       # noqa: BLE001
                print(f"  FAILED {entry['id']} p{page_index}: {exc}", file=sys.stderr)
                continue
            for rec in got:
                rec.update(source=entry["id"], page_index=page_index)
                records.append(rec)
            print(f"  {entry['id']} p{page_index}: {len(got)} labels", file=sys.stderr)

    args.out.write_text(json.dumps(records, indent=1, ensure_ascii=False))
    print(f"{len(records)} labels -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
