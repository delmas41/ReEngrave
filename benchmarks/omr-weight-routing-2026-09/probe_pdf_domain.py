"""Measure the signals that separate a scanned PDF from a digitally engraved one.

The weight router needs to classify a PDF's pages as SCANNED (ink arrives as a
full-page raster image) or ENGRAVED (ink arrives as vector drawings + fonts)
before the YOLO model loads.  This probe measures the candidate signals over a
labeled corpus so the classifier's thresholds are read off a gap, not guessed:

  - per-image page coverage (a scan is one image covering the page)
  - image stream filters (scans: CCITTFaxDecode / JBIG2Decode / DCTDecode)
  - vector drawing count (engraving: thousands of paths; scans: ~none)
  - embedded font count and extractable text length
    (NOT sufficient alone: IMSLP 575951 is a scan WITH an OCR text layer)

Corpus:
  ENGRAVED: LilyPond renders from the orchestral e2e benchmark fixtures
            (main checkout, read-only) + any *.pdf under benchmark fixture
            dirs known to be LilyPond output.
  SCANNED:  the five scan-benchmark rows (works.json -> library catalog paths)
            + an every-Nth systematic sample of library/editions (IMSLP scans;
            vector-dominant outliers in this set are surfaced for hand-check,
            not silently trusted).

Usage:  python3 benchmarks/omr-weight-routing-2026-09/probe_pdf_domain.py
Writes: benchmarks/omr-weight-routing-2026-09/probe_results.tsv
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF

BENCH = Path(__file__).resolve().parent
MAIN_CHECKOUT = Path("/Users/seanjohnson/Desktop/ReEngrave")
LIBRARY_EDITIONS = MAIN_CHECKOUT / "library" / "editions"
ENGRAVED_FIXTURE_DIRS = [
    MAIN_CHECKOUT / "benchmarks" / "omr-orchestral-e2e" / "fixtures",
]
SCAN_WORKS_JSON = BENCH.parent / "omr-scan-e2e-2026-09" / "works.json"

MAX_PAGES_PER_DOC = 3
EDITION_SAMPLE_EVERY = 7  # ~40 of 289, systematic (deterministic) sample


def page_features(doc: fitz.Document, pno: int) -> dict:
    page = doc[pno]
    t0 = time.perf_counter()
    area = abs(page.rect)

    # Raster images: how much of the page do they cover, and how are they coded?
    infos = page.get_image_info()
    covs = []
    for info in infos:
        bbox = fitz.Rect(info["bbox"])
        covs.append(abs(bbox) / area if area else 0.0)
    filters = set()
    for img in page.get_images(full=True):
        xref = img[0]
        filt = doc.xref_get_key(xref, "Filter")
        if filt and filt[0] != "null":
            filters.add(filt[1].strip("[]/ ").replace("/", "+"))

    n_fonts = len(page.get_fonts())
    text_chars = len(page.get_text("text").strip())

    # Vector drawings — potentially slow on dense engraving, so time-boxed by
    # measurement, not by a guard: the probe records the cost.
    t_draw = time.perf_counter()
    try:
        n_drawings = len(page.get_cdrawings())
    except Exception:
        n_drawings = -1
    draw_ms = (time.perf_counter() - t_draw) * 1000.0

    return {
        "n_images": len(infos),
        "max_img_cov": round(max(covs), 3) if covs else 0.0,
        "tot_img_cov": round(min(sum(covs), 9.999), 3),
        "filters": "+".join(sorted(filters)) or "-",
        "n_drawings": n_drawings,
        "n_fonts": n_fonts,
        "text_chars": text_chars,
        "ms_total": round((time.perf_counter() - t0) * 1000.0, 1),
        "ms_drawings": round(draw_ms, 1),
    }


def gather() -> list[tuple[str, Path]]:
    corpus: list[tuple[str, Path]] = []

    for d in ENGRAVED_FIXTURE_DIRS:
        for pdf in sorted(d.glob("*.pdf")):
            corpus.append(("engraved", pdf))

    rows = json.loads(SCAN_WORKS_JSON.read_text())
    seen = set()
    for row in rows if isinstance(rows, list) else rows.get("rows", []):
        cat = row.get("edition", {}).get("catalog_path")
        if cat:
            p = MAIN_CHECKOUT / "library" / cat if not str(cat).startswith("library") \
                else MAIN_CHECKOUT / cat
            if p.exists() and p not in seen:
                corpus.append(("scan-bench", p))
                seen.add(p)

    editions = sorted(LIBRARY_EDITIONS.rglob("*.pdf"))
    for i, pdf in enumerate(editions):
        if i % EDITION_SAMPLE_EVERY == 0 and pdf not in seen:
            corpus.append(("library", pdf))
    return corpus


def main() -> None:
    corpus = gather()
    out = BENCH / "probe_results.tsv"
    cols = ["label", "pdf", "page", "n_images", "max_img_cov", "tot_img_cov",
            "filters", "n_drawings", "n_fonts", "text_chars",
            "ms_total", "ms_drawings"]
    lines = ["\t".join(cols)]
    n_docs = 0
    for label, pdf in corpus:
        try:
            doc = fitz.open(pdf)
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP {pdf}: {exc}", file=sys.stderr)
            continue
        n_docs += 1
        for pno in range(min(MAX_PAGES_PER_DOC, doc.page_count)):
            try:
                f = page_features(doc, pno)
            except Exception as exc:  # noqa: BLE001
                print(f"SKIP {pdf} p{pno}: {exc}", file=sys.stderr)
                continue
            rel = str(pdf).replace(str(MAIN_CHECKOUT) + "/", "")
            lines.append("\t".join(str(x) for x in (
                label, rel, pno, f["n_images"], f["max_img_cov"],
                f["tot_img_cov"], f["filters"], f["n_drawings"], f["n_fonts"],
                f["text_chars"], f["ms_total"], f["ms_drawings"])))
        doc.close()
    out.write_text("\n".join(lines) + "\n")
    print(f"{n_docs} docs -> {out}")

    # Console summary: distribution of the two load-bearing signals per label.
    import statistics as st
    rows = [dict(zip(cols, ln.split("\t"))) for ln in lines[1:]]
    for lab in ("engraved", "scan-bench", "library"):
        sub = [r for r in rows if r["label"] == lab]
        if not sub:
            continue
        cov = sorted(float(r["max_img_cov"]) for r in sub)
        drw = sorted(int(r["n_drawings"]) for r in sub)
        ms = sorted(float(r["ms_total"]) for r in sub)
        print(f"\n{lab}: {len(sub)} pages")
        print(f"  max_img_cov  min={cov[0]:.3f} med={st.median(cov):.3f} max={cov[-1]:.3f}")
        print(f"  n_drawings   min={drw[0]} med={st.median(drw):.0f} max={drw[-1]}")
        print(f"  ms_total     med={st.median(ms):.0f} max={ms[-1]:.0f}")
        low_cov = [r for r in sub if float(r["max_img_cov"]) < 0.5]
        if lab != "engraved" and low_cov:
            print(f"  OUTLIERS (max_img_cov < 0.5) — hand-check these:")
            for r in low_cov[:10]:
                print(f"    {r['pdf']} p{r['page']} cov={r['max_img_cov']} "
                      f"draw={r['n_drawings']} fonts={r['n_fonts']}")
        if lab == "engraved":
            high_cov = [r for r in sub if float(r["max_img_cov"]) >= 0.5]
            for r in high_cov[:10]:
                print(f"  OUTLIER (image-dominant engraved?): {r['pdf']} p{r['page']}")


if __name__ == "__main__":
    main()
