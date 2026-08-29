"""What clef does the PIPELINE finally put on each staff?

`eval_orchestral_clefs.py` scores the CV locator's precision, and
`probe_clef_rejection.py` scores coverage of the header window. Neither answers
the question everything downstream actually depends on: after the detector, the
locator, the header vote and the positional default have all had their say,
what clef does a staff end up with, and is it right?

That number matters more than the parts, because a staff carries its clef into
every pitch on it, and into which slot table its key signature is fitted. Three
of this project's threads ended by pointing at it (docs/next-steps-omr-2026-08-28.md).

Ground truth is the hand-read clefs already in
`benchmarks/omr-key-signature/ground_truth.json` — one `clef` per staff ordinal
within a system, for pages whose systems all carry the same instrumentation.

    python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py

Reports accuracy overall and split by SOURCE, because "wrong" means different
things: a clef the detector read wrongly is a detection error, while a staff
carrying the positional default was never read at all and is only right by
luck — the default is treble, and most staves are treble.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.contextual import apply_contextual_analysis  # noqa: E402
from tools.omr.transcribe import transcribe  # noqa: E402

TRUTH = REPO / "benchmarks" / "omr-key-signature" / "ground_truth.json"
WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"


def score_page(page: dict, weights: Path, dpi: int | None,
               contextual: bool = False) -> list[dict]:
    pdf = Path(page["pdf"])
    if not pdf.is_absolute():
        pdf = REPO / pdf
    if not pdf.exists():
        print(f"{page['id']:14s} SKIP (missing {pdf.name})")
        return []
    result = transcribe(
        pdf_path=pdf, pages=[page["page_index"]], weights=str(weights),
        dpi=dpi or page["dpi"],
    )
    if contextual:
        # The pass that proposes a clef from the instrument's own convention,
        # vetoed by the staff's register — and only where nothing read a clef.
        summary = apply_contextual_analysis(
            result, pdf_path=pdf, dpi=dpi or page["dpi"], apply_clefs=True)
        print(f"  {page['id']}: contextual — {summary.get('labelled_staves')} labels, "
              f"{summary.get('clefs_applied')} clef corrections applied")
    truth = {s["ordinal"]: s["clef"] for s in page["staves"]}
    rows = []
    for page_d in result["pages"]:
        for system in page_d["systems"]:
            staves = system["staves"]
            # Ground truth is by ordinal within the system, which only lines up
            # when the system has the instrumentation the truth describes. A
            # system with a different staff count is a different reading of the
            # page, and scoring it by ordinal would compare unrelated staves.
            if len(staves) != len(truth):
                print(f"  {page['id']}: system {system.get('system_index')} has "
                      f"{len(staves)} staves against {len(truth)} in ground "
                      f"truth — skipped, ordinals would not correspond")
                continue
            for ordinal, staff in enumerate(staves):
                rows.append({
                    "page": page["id"],
                    "system": system.get("system_index"),
                    "ordinal": ordinal,
                    "want": truth[ordinal],
                    "got": staff.get("clef"),
                    "source": staff.get("clef_source") or "default",
                })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, help="override each page's own DPI")
    ap.add_argument("--weights", type=Path, default=WEIGHTS)
    ap.add_argument("--out", type=Path, help="write the per-staff rows as JSON")
    ap.add_argument("--contextual", action="store_true",
                    help="run contextual analysis (instrument identity -> clef) first")
    args = ap.parse_args()
    if not args.weights.exists():
        print(f"no weights at {args.weights}", file=sys.stderr)
        return 1

    rows: list[dict] = []
    for page in json.loads(TRUTH.read_text())["pages"]:
        rows.extend(score_page(page, args.weights, args.dpi, args.contextual))
    if not rows:
        print("no pages scored")
        return 1

    by_source: dict[str, Counter] = {}
    for r in rows:
        c = by_source.setdefault(r["source"], Counter())
        c["n"] += 1
        c["ok"] += 1 if r["got"] == r["want"] else 0

    total = len(rows)
    correct = sum(1 for r in rows if r["got"] == r["want"])
    print(f"\n{total} staves with hand-read clefs")
    print(f"  correct overall: {correct}/{total} = {correct / total:.0%}")
    print(f"\n  {'source':12s} {'staves':>7} {'correct':>8} {'accuracy':>9}")
    for source, c in sorted(by_source.items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {source:12s} {c['n']:7d} {c['ok']:8d} {c['ok'] / c['n']:9.0%}")

    wrong = [r for r in rows if r["got"] != r["want"]]
    if wrong:
        print(f"\n  the {len(wrong)} wrong readings, by (want -> got):")
        for (want, got), n in Counter((r["want"], r["got"]) for r in wrong).most_common():
            print(f"    {want:7s} -> {got or 'none':7s}  x{n}")
    if args.out:
        args.out.write_text(json.dumps(rows, indent=2) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
