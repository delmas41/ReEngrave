"""Does the scan gate ever fire on an ENGRAVED page? -- the load-bearing check.

The gate skips the direction-word reader where a page is PROVABLY a scan,
worth ~267 s/page there for ~6 words. Its whole risk is the other side: an
engraved page wrongly called a scan loses a reader CLAUDE.md measures at 144
edits, 18.8% of the pooled engraved figure, and loses it silently.

⚠️ SO THE NUMBER THAT DECIDES THIS IS NOT THE GATE'S REACH ON SCANS -- it is
its FALSE-POSITIVE COUNT ON ENGRAVINGS, which must be zero. Reach only says
how much is saved; a single engraved false positive means the gate cannot
ship whatever it saves.

⚠️ It renders NOTHING. Both classifiers read the PDF's own structure and take
only `pdf_path` and `page_index`, so hundreds of pages cost seconds -- which
is what makes a corpus-wide answer affordable rather than a spot check.

    python3 benchmarks/omr-surya-staged-cost-2026-09/probe_scan_gate.py
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.direction_text import (page_is_engraved,          # noqa: E402
                                      page_is_scanned)


def classify(pdf: Path, index: int) -> str:
    page = SimpleNamespace(pdf_path=str(pdf), page_index=index)
    eng = page_is_engraved(page)
    scn = page_is_scanned(page)
    if eng and scn:
        return "BOTH"          # must never happen: the two proofs conflict
    if eng:
        return "engraved"
    if scn:
        return "scanned"
    return "ambiguous"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-per-pdf", type=int, default=3)
    ap.add_argument("--scans", type=int, default=60)
    ap.add_argument("--seed", type=int, default=20260916)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    import fitz

    engraved_pdfs = sorted(
        p for p in (REPO / "benchmarks").rglob("*.pdf")
        if "fixtures" in str(p) or "output" in str(p)
        or "noise-floor" in str(p) or "xstart-audit" in str(p))
    scan_pdfs = sorted((REPO / "library" / "editions").rglob("*.pdf"))
    random.Random(args.seed).shuffle(scan_pdfs)
    scan_pdfs = scan_pdfs[:args.scans]

    rows = []
    for family, pdfs in (("engraved-render", engraved_pdfs),
                         ("library-scan", scan_pdfs)):
        for pdf in pdfs:
            try:
                with fitz.open(pdf) as doc:
                    n = doc.page_count
            except Exception:                                 # noqa: BLE001
                continue
            for i in range(min(args.pages_per_pdf, n)):
                rows.append({"family": family, "pdf": str(pdf.name),
                             "page": i, "verdict": classify(pdf, i)})

    tally: dict[str, dict[str, int]] = {}
    for r in rows:
        tally.setdefault(r["family"], {}).setdefault(r["verdict"], 0)
        tally[r["family"]][r["verdict"]] += 1

    print("family              pages   engraved   scanned  ambiguous   BOTH")
    for fam, t in sorted(tally.items()):
        n = sum(t.values())
        print("  %-18s %5d %10d %9d %10d %6d"
              % (fam, n, t.get("engraved", 0), t.get("scanned", 0),
                 t.get("ambiguous", 0), t.get("BOTH", 0)))

    false_pos = [r for r in rows
                 if r["family"] == "engraved-render" and r["verdict"] == "scanned"]
    both = [r for r in rows if r["verdict"] == "BOTH"]
    print()
    print("⚠️ THE DECIDING NUMBER -- engraved pages the gate would SKIP: %d"
          % len(false_pos))
    for r in false_pos[:10]:
        print("     %s p%d" % (r["pdf"], r["page"]))
    if both:
        print("⚠️ %d page(s) proved BOTH -- the two classifiers contradict"
              % len(both))

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"tally": tally, "false_positives": false_pos, "both": both,
             "rows": rows}, indent=2))
        print("wrote", args.json_out)

    if both:
        return 2
    return 1 if false_pos else 0


if __name__ == "__main__":
    raise SystemExit(main())
