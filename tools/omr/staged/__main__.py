"""CLI for the staged pipeline.

    # the three stages on a real PDF, with weights
    python3 -m tools.omr.staged score.pdf --pages 0-2 \
        --weights omr-weights/<file>.pt --out staged.json

    # no weights: every cell abstains READER_UNAVAILABLE and it still runs
    python3 -m tools.omr.staged score.pdf --pages 0

    # the A/B: compare against a legacy transcribe result
    python3 -m tools.omr.staged score.pdf --pages 0-2 --weights <...> \
        --against legacy.omr.json

⚠️ THIS RUNS NO BENCHMARK AND SCORES NOTHING. The divergence table is a
POPULATION, not a result: every `differ` row needs a human against the print
before it is a win or a loss.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_pages(spec: str) -> list:
    out = []
    for part in (spec or "0").split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="The staged pipeline: GATHER -> ADJUDICATE -> EVALUATE")
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="0")
    ap.add_argument("--weights", default=None,
                    help="YOLO weights. Omit to run with no detector at all -- "
                         "every cell abstains and the pipeline still completes.")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--against", default=None,
                    help="a legacy transcribe result JSON, for the divergence "
                         "table")
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args(argv)

    from . import legacy, pipeline

    detector = None
    if args.weights:
        from ..yolo_detector import YoloDetector
        detector = YoloDetector(args.weights)

    result = pipeline.run_staged(
        args.pdf, parse_pages(args.pages), detector=detector, dpi=args.dpi,
        conf_threshold=args.conf, imgsz=args.imgsz, progress=args.progress)

    if args.against:
        prepared = pipeline.prepare_pages(args.pdf, parse_pages(args.pages),
                                          dpi=args.dpi)
        from . import gather as G
        log = G.gather(prepared, detector=detector, conf_threshold=args.conf,
                       imgsz=args.imgsz)
        from . import adjudicate
        adjudicate.run(log)
        result["divergence"] = pipeline.divergence(log, legacy.load(args.against))

    text = json.dumps(result, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)

    _report(result)
    return 0


def _report(result: dict) -> None:
    adj = result["adjudication"]
    print("\n── ADJUDICATE ─────────────────────────────────────────", file=sys.stderr)
    print(f"  decided:   {adj['decided']}", file=sys.stderr)
    print(f"  abstained: {adj['abstained']}", file=sys.stderr)
    if adj["excluded_as_circular"]:
        print(f"  ⚠️ excluded as circular: {len(adj['excluded_as_circular'])}",
              file=sys.stderr)
    ag = result.get("agreement")
    if ag is not None:
        print("── GROUPS ─────────────────────────────────────────────",
              file=sys.stderr)
        for name, row in sorted(ag["per_redundancy"].items()):
            print(f"  {name}: {row['n_facts']} facts, "
                  f"{row['n_witnesses']} witnesses, "
                  f"{row['uninformative']} uninformative, {row['agreement']}",
                  file=sys.stderr)
        # ⚠️ A DECLARED redundancy that found nothing is named, because a zero
        # is a suspect and not a result.
        for key, gloss in (("declared_but_empty", "placed no fact"),
                           ("witnessed_by_nobody", "no witness spoke"),
                           ("checked_nothing",
                            "never two independent signals -- corroborated "
                            "NOTHING, however busy it looks")):
            if ag.get(key):
                print(f"  ⚠️ {key} ({gloss}): {ag[key]}", file=sys.stderr)
        print(f"  ⚠️ DISAGREEMENTS: {ag['n_disagreements']} "
              f"(each implicates its WHOLE group, not its dissenter)",
              file=sys.stderr)
    ev = result["evaluation"]
    print(f"── EVALUATE: {ev['counts']['fired']} fired, "
          f"{ev['counts']['skipped']} skipped", file=sys.stderr)
    print(f"── DECLARED STUBS: {len(result['stubs']['decisions'])} decisions, "
          f"{len(result['stubs']['consequences'])} consequences", file=sys.stderr)
    if "divergence" in result:
        print(f"── DIVERGENCE: {result['divergence']['counts']}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
