"""Score the engraved benchmark from its STORED transcriptions, this tree's export.

`orchestral_eval --omr-ned` regenerates every fixture from the score library on
each run — truth XML, LilyPond render, PDF, transcription — which is right for
a headline measurement and wrong for an A/B of the EXPORTER, twice over: it
costs half an hour, and it re-runs the detector, so a difference in the number
could be a difference in the reading.

This scores whatever is already in `fixtures/`, re-exporting each work's
`.omr.json` here and now — the same move `tools/omr/export_coverage.py` makes,
and for the same reason. Two arms differ only in the tree, never in the
transcription.

    python3 benchmarks/omr-hairpins-2026-09/score_export_arm.py --label after

It does NOT write `current-accuracy.json` and must not: `accuracy_record` is
fed by `orchestral_eval --omr-ned --record` alone, which refuses a partial run
for reasons its module docstring gives. This prints a figure for an A/B and
says so.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import accuracy_record, omr_ned  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402

FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--works", nargs="+", default=None)
    ap.add_argument("--label", default="arm")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--detail", default="AllObjects")
    args = ap.parse_args(argv)

    works = tuple(args.works or accuracy_record.BENCHMARK_WORKS)
    missing = [w for w in works
               if not (args.fixtures / f"{w}.omr.json").is_file()]
    if missing:
        print(f"no transcription on disk for {missing} — the counts are POOLED, "
              "so a missing work moves the figure. Run orchestral_eval first.",
              file=sys.stderr)
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="export-arm-"))
    pairs = []
    for work in works:
        result = json.loads((args.fixtures / f"{work}.omr.json").read_text())
        pred = tmp / f"{work}.musicxml"
        pred.write_text(to_musicxml(result))
        pairs.append((work, pred, args.fixtures / f"{work}.musicxml"))

    scored = omr_ned.score_batch(pairs, detail=args.detail)
    by_name = {p["name"]: p for p in scored.get("pairs", [])}

    print(f"\n{args.label}:  {'work':24s} {'OMR-NED':>8s} {'edits':>7s}")
    for work in works:
        p = by_name.get(work) or {}
        print(f"{'':<10} {work:24s} {p.get('omr_ned', float('nan')):>8.4f} "
              f"{p.get('omr_ed', 0):>7d}")
    print(f"\nPOOLED (A/B only — not the recorded headline): "
          f"{scored.get('overall_omr_ned'):.4f} / "
          f"{scored.get('overall_omr_ed')} edits")
    cats = scored.get("overall_categories") or {}
    for cat, n in sorted(cats.items(), key=lambda kv: -kv[1])[:8]:
        print(f"    {cat:38s} {n:>6d}")
    for cat in ("wrong crescendo", "wrong diminuendo"):
        print(f"    {cat:38s} {cats.get(cat, 0):>6d}")

    if args.out:
        args.out.write_text(json.dumps(
            {"label": args.label, "works": list(works), "scored": scored},
            indent=1) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
