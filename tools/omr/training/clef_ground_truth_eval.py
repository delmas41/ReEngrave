"""Score clef reading against a hand-written ground-truth page.

Usage:
    python3 -m tools.omr.training.clef_ground_truth_eval \\
        --pdf /path/to/Nottebohm-Beethovens-Studien-1873.pdf \\
        --ground-truth benchmarks/omr-clef-geometry/nottebohm-p46-ground-truth.json \\
        --weights omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt

Reports two numbers that mean different things and should never be collapsed
into one:

  **precision on read clefs** — of the staves where some reader actually
  produced a clef, how many were right. This is the quality of clef *reading*.

  **coverage** — how many staves got a clef read at all. A staff with no read
  falls back to the position default, which is usually treble, and every pitch
  on it may then be transposed. Misses here are overwhelmingly upstream layout
  failures (the clef cropped out of the cell, or staff lines mis-grouped), not
  clef-reading failures, so mixing the two hides which half needs work.

Staves are matched to ground truth by vertical position on the page, which is
how the ground truth is written down — top to bottom — and avoids depending on
the pipeline's system grouping, which is itself unreliable on these pages.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _staves_in_page_order(page: dict) -> list[dict]:
    """Every staff on the page, ordered top to bottom by where it actually
    sits, rather than by the pipeline's system/staff indices."""
    out = []
    for system in page["systems"]:
        for staff in system["staves"]:
            if not staff["measures"]:
                continue
            out.append((min(m["bbox_page_px"][1] for m in staff["measures"]), staff))
    out.sort(key=lambda t: t[0])
    return [s for _y, s in out]


def evaluate(page: dict, expected: list[dict]) -> dict:
    staves = _staves_in_page_order(page)
    rows = []
    for i, want in enumerate(expected):
        got = staves[i] if i < len(staves) else None
        rows.append({
            "index": i,
            "system": want.get("system"),
            "expected": want["clef"],
            "read": got["clef"] if got else None,
            "source": (got.get("clef_source") if got else None),
        })
    read = [r for r in rows if r["source"]]
    correct_read = [r for r in read if r["read"] == r["expected"]]
    correct_all = [r for r in rows if r["read"] == r["expected"]]
    by_source: dict[str, list[dict]] = {}
    for r in read:
        by_source.setdefault(r["source"], []).append(r)
    return {
        "rows": rows,
        "n_staves_expected": len(expected),
        "n_staves_found": len(staves),
        "n_read": len(read),
        "n_correct_read": len(correct_read),
        "n_correct_overall": len(correct_all),
        "by_source": {
            s: {"n": len(v), "correct": sum(1 for r in v if r["read"] == r["expected"])}
            for s, v in by_source.items()
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--ground-truth", type=Path, required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--omr-json", type=Path,
                    help="Reuse an existing transcription instead of running OMR. "
                         "Must contain the ground truth's page.")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--imgsz", type=int, default=1280)
    args = ap.parse_args(argv)

    gt = json.loads(args.ground_truth.read_text())
    page_index = gt["pdf_page_index"]

    if args.omr_json:
        doc = json.loads(args.omr_json.read_text())
        matches = [p for p in doc["pages"] if p["page_index"] == page_index]
        if not matches:
            print(f"ERROR: {args.omr_json} has no page {page_index}")
            return 2
        page = matches[0]
    else:
        from ..transcribe import transcribe
        doc = transcribe(pdf_path=args.pdf, pages=[page_index], weights=args.weights,
                         dpi=args.dpi, imgsz=args.imgsz, progress=False)
        page = doc["pages"][0]

    result = evaluate(page, gt["clefs"])
    print(f"{gt['source']}")
    print(f"PDF page {page_index} (printed p.{gt.get('printed_page')})\n")
    print(f"{'':3} {'system':8} {'expected':13} {'read':13} {'source':12}")
    for r in result["rows"]:
        ok = "ok" if r["read"] == r["expected"] else "MISS"
        print(f"{r['index']:3} {str(r['system']):8} {r['expected']:13} "
              f"{str(r['read']):13} {str(r['source'] or '— not read —'):12} {ok}")
    print()
    n_read, n_ok = result["n_read"], result["n_correct_read"]
    print(f"staves expected / found      {result['n_staves_expected']} / {result['n_staves_found']}")
    print(f"clef READ on                 {n_read} staves")
    print(f"  precision on those         {n_ok}/{n_read}"
          f"{f'  ({n_ok/n_read:.0%})' if n_read else ''}")
    print(f"overall correct              {result['n_correct_overall']}/{result['n_staves_expected']}"
          f"   (the rest defaulted — no clef was read)")
    for s, v in sorted(result["by_source"].items()):
        print(f"    via {s:12} {v['correct']}/{v['n']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
