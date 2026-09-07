#!/usr/bin/env python3
"""The language, from the HEAD of the document — the page that spells it out.

## Why this exists, and it is the whole finding

`measure_reach.py` votes the language out of the committed 1422-label margin
dump and reads it on 9 of 12 documents. The three it cannot read include
`beethoven6-504082`, which is the ONE document carrying the fault this work was
commissioned for (`Tb.` -> Tuba on a score whose `Tb.` is Tromboni).

That is not a property of the document. The dump SAMPLES ten pages, roughly
every ninth, and page 0 is not among them — and page 0 is where a score prints
its roster in full. Reading that one page turns the document from "no
diagnostic evidence at all" into `it` at 7 votes and share 1.00.

⚠️ **A second instance of the identity harness's regime rule**
(`benchmarks/omr-identity-harness-2026-09`, which refuses to pool across
page-set regimes): the same document, the same code, two page sets, and the
signal goes from ABSENT to UNANIMOUS. A reach figure without its regime is not
a reach figure.

## Why the raw text layer and not the margin reader

⚠️ `staff_labels.read_staff_labels` returns ZERO labels on that page while its
text layer plainly holds `Oboi. / Clarinetti inB / Fagotti. / Corni in F. /
Violino J. / Violino II. / Viola. / Violoncello e Basso.` — a movement-head
page indents its first system and carries a title block, and 15 "staves" are
detected where the music has twelve. That is a reader-reach defect and it is
not this module's to fix.

It also does not need fixing for THIS signal, which is the design point worth
keeping: **language detection has a lower evidential bar than identity.** A
name has to be joined to the right staff to name it; a language only has to be
READ. So the head-page vote runs on raw text-layer spans in the left margin,
with no staff join at all, and the strings that are junk resolve to nothing and
cast no vote.

    python3 benchmarks/omr-score-language-2026-09/probe/language_from_head.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

BENCH = Path(__file__).resolve().parents[1]
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import score_language as L        # noqa: E402

LEXICON = ROOT / "benchmarks/omr-lexicon-2026-09"

#: A margin label lives in the left of the page. Wide enough for an indented
#: movement-head system, narrow enough to leave the music's own OCR garbage out
#: — and the garbage costs nothing anyway, because it resolves to no alias.
MARGIN_FRACTION = 0.30

#: Span length bounds: one character is an OCR mark, forty is a tempo sentence.
MIN_CHARS, MAX_CHARS = 2, 40


def head_strings(pdf: Path, pages: list[int]) -> list[str]:
    """Left-margin text-layer spans on the given pages, in reading order."""
    doc = fitz.open(pdf)
    try:
        out: list[str] = []
        for idx in pages:
            if idx < 0 or idx >= doc.page_count:
                continue
            page = doc[idx]
            limit = page.rect.x0 + MARGIN_FRACTION * page.rect.width
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"].strip()
                        if (MIN_CHARS <= len(text) <= MAX_CHARS
                                and span["bbox"][0] < limit):
                            out.append(text)
        return out
    finally:
        doc.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=Path, default=LEXICON / "pages.json")
    ap.add_argument("--head", type=int, default=1,
                    help="how many leading pages to read (default 1)")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    docs = json.loads(args.pages.read_text())
    rows = []
    hdr = (f"{'document':34s} {'spans':>6s} {'diag':>5s} {'lang':>5s} "
           f"{'share':>6s} {'votes'}")
    print(f"head pages read: 0..{args.head - 1}   margin: left "
          f"{MARGIN_FRACTION:.0%} of the page\n")
    print(hdr)
    print("-" * 78)
    for doc in docs:
        pdf = Path(doc["pdf"])
        if not pdf.is_file():
            print(f"{doc['id']:34s} {'--':>6s}  (pdf missing)")
            rows.append({"document": doc["id"], "pdf_missing": True})
            continue
        strings = head_strings(pdf, list(range(args.head)))
        reading = L.detect(strings)
        votes = {k: v for k, v in reading.votes.items() if v}
        print(f"{doc['id']:34s} {len(strings):6d} {reading.n_diagnostic:5d} "
              f"{reading.language or '--':>5s} {reading.share:6.2f} {votes}")
        rows.append({"document": doc["id"], "spans": len(strings),
                     "diagnostic_votes": reading.n_diagnostic,
                     "language": reading.language,
                     "share": round(reading.share, 4),
                     "votes": reading.votes, "mixed": reading.is_mixed})

    named = [r for r in rows if r.get("language")]
    have = [r for r in rows if not r.get("pdf_missing")]
    print("-" * 78)
    print(f"\nlanguage read on {len(named)} of {len(have)} documents with a PDF "
          f"({len(named)/len(have):.3f}) from {args.head} page(s) each")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"head_pages": args.head, "margin_fraction": MARGIN_FRACTION,
             "documents": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
