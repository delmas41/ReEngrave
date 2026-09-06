"""How much of the corpus can this change even reach?

`OMR_LABEL_MERGE_QUALITY` only ever acts where the PDF text layer produced
labels: with no text layer the early return never fires (`_well_covered([])` is
False) and the merge key has nothing to rank. So the population is exactly the
editions carrying a usable text layer -- and that is a fact about the store, not
about the pipeline, so it can be counted cheaply before anything slow is run.

Stage 1 (`--census`) counts text-layer editions across the score library.
Stage 2 (default) runs the real ladder both ways on the first page of each one
and reports how many staves change.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")


def _editions() -> list[Path]:
    return sorted(LIB.rglob("*.pdf"))


def _has_text(pdf: Path, pages: int = 3) -> tuple[bool, int]:
    """Does this PDF carry a text layer, and how many chars on early pages?"""
    import pymupdf
    try:
        doc = pymupdf.open(pdf)
    except Exception:                                        # noqa: BLE001
        return False, 0
    total = 0
    for i in range(min(pages, doc.page_count)):
        try:
            total += len(doc[i].get_text().strip())
        except Exception:                                    # noqa: BLE001
            pass
    doc.close()
    return total > 0, total


def census(out: Path | None) -> list[dict]:
    rows = []
    for pdf in _editions():
        has, n = _has_text(pdf)
        rows.append({"pdf": str(pdf), "has_text_layer": has, "text_chars": n})
    n_with = sum(1 for r in rows if r["has_text_layer"])
    print(f"{len(rows)} editions in the store, "
          f"{n_with} carry a text layer on their first 3 pages "
          f"({n_with / max(1, len(rows)):.1%})")
    for r in rows:
        if r["has_text_layer"]:
            print(f"  {r['text_chars']:>8} chars  {Path(r['pdf']).name}")
    if out:
        out.write_text(json.dumps(rows, indent=2))
    return rows


def compare(rows: list[dict], page: int, dpi: int, out: Path | None) -> None:
    """Run the real ladder both ways on the text-layer editions."""
    from tools.omr import contextual
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from benchmarks import __name__ as _unused           # noqa: F401
    import importlib
    probe = importlib.import_module(
        "benchmarks.omr-label-ladder-2026-09.probe_ladder_rungs")

    class _NoAssist:
        mode = "none"

    results = []
    for r in rows:
        if not r["has_text_layer"]:
            continue
        pdf = Path(r["pdf"])
        try:
            pws = detect_staves(render_page(pdf, page, dpi=dpi))
        except Exception as exc:                             # noqa: BLE001
            print(f"  SKIP {pdf.name}: {exc}")
            continue
        arms = {}
        for flag in ("0", "1"):
            os.environ["OMR_LABEL_MERGE_QUALITY"] = flag
            t0 = time.time()
            labs = contextual._labels_for_page(
                pws, pdf, page, assist=_NoAssist(), budget=[0])
            arms[flag] = {
                "consumable": probe._consumable(labs),
                "usable": contextual._usable(labs),
                "raw": len(labs),
                "seconds": round(time.time() - t0, 2),
                "by_staff": {str(l.staff_index):
                             [l.text, l.instrument.name if l.instrument else None,
                              l.confidence, l.matched] for l in labs},
            }
        os.environ.pop("OMR_LABEL_MERGE_QUALITY", None)
        off, on = arms["0"], arms["1"]
        changed = [i for i in set(off["by_staff"]) | set(on["by_staff"])
                   if off["by_staff"].get(i) != on["by_staff"].get(i)]
        results.append({"pdf": str(pdf), "page": page, "n_staves": len(pws.staves),
                        "off": off, "on": on, "staves_changed": sorted(changed, key=int)})
        print(f"  {pdf.name[:56]:56s} staves={len(pws.staves):>3} "
              f"consumable {off['consumable']:>3} -> {on['consumable']:>3}  "
              f"changed={len(changed):>3}  "
              f"{off['seconds']:>5.1f}s -> {on['seconds']:>5.1f}s")

    d_cons = sum(r["on"]["consumable"] - r["off"]["consumable"] for r in results)
    d_staff = sum(len(r["staves_changed"]) for r in results)
    n_staves = sum(r["n_staves"] for r in results)
    extra = sum(r["on"]["seconds"] - r["off"]["seconds"] for r in results)
    print()
    print(f"{len(results)} text-layer pages, {n_staves} staves: "
          f"consumable labels {d_cons:+d}, staves whose label text changes "
          f"{d_staff} ({d_staff / max(1, n_staves):.1%}), "
          f"wall time {extra:+.1f}s total")
    if out:
        out.write_text(json.dumps(results, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", action="store_true",
                    help="only count text-layer editions; run nothing slow")
    ap.add_argument("--census-json", default=None)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out")
    args = ap.parse_args()

    rows = census(Path(args.census_json) if args.census_json else None)
    if args.census:
        return 0
    print()
    compare(rows, args.page, args.dpi, Path(args.out) if args.out else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
