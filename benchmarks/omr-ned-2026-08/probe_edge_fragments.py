"""Is an edge-touching notehead a note, or a slice of the staff next door?

`transcribe._drop_clipped_notehead_fragments` throws away notehead detections
that sit flush against a measure cell's top or bottom edge and are far too short
to be a notehead. This is the measurement that constant rests on, run against
whatever transcriptions are on disk so it can be re-checked on a new score
rather than taken on trust.

    python3 -m tools.omr.training.orchestral_eval          # writes the .omr.json
    python3 benchmarks/omr-ned-2026-08/probe_edge_fragments.py

WHAT TO LOOK FOR. The claim is that a notehead is one staff space tall — that
is what a notehead IS — so the fragments and the notes should separate with
nothing in between. On the three benchmark works when this was written:

    interior noteheads      594, heights 0.61 - 1.12 spaces, none below 0.60
    edge-touching, real      10, heights 0.77 - 0.99   (a crop that grazes a note)
    edge-touching, fragments 10, heights 0.29 - 0.56   (the "legato" g, a 6/8's 8,
                                                        the staff above's notes)

Run against a transcription made BEFORE the rule shipped and both groups appear;
against one made after, only the ten real ones do.

The threshold sits in the empty band between 0.56 and 0.77. If a new score puts
anything in that band, the rule needs re-deciding, not re-tuning.

READ IT AFTER THE PIPELINE, NOT DURING. The JSON is post-`_dedupe_cross_staff_
detections`, so a fragment the deduper would have removed anyway never appears
here — which is exactly why Beethoven and Mahler show nothing while the run
counter reports drops on them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
DEFAULT_WORKS = ("beethoven-sym5-mvt1", "brahms-sym1-mvt1", "mahler-sym5-mvt1")

#: Must match `transcribe._CLIPPED_NOTEHEAD_MAX_SPACES`; restated rather than
#: imported so the probe reports what the pipeline does even when run from a
#: checkout whose pipeline has moved.
LIMIT_SPACES = 0.6


def survey(path: Path) -> dict:
    result = json.loads(path.read_text())
    edge, interior = [], []
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                spacing = (staff.get("staff_geometry") or {}).get("line_spacing_px")
                if not spacing:
                    continue
                for measure in staff.get("measures", []):
                    _, cell_top, _, cell_bottom = measure["bbox_page_px"]
                    for det in measure.get("detections", []):
                        if det.get("category") != "notehead":
                            continue
                        box = det.get("bbox_page")
                        if not box:
                            continue
                        _, y, _, h = box
                        record = {
                            "height_spaces": h / spacing,
                            "class": det["class"],
                            "staff": staff["staff_index"],
                            "measure": measure["measure_index"],
                            "confidence": det.get("confidence"),
                        }
                        touches = y <= cell_top + 1 or y + h >= cell_bottom - 1
                        (edge if touches else interior).append(record)
    return {
        "dropped_by_the_rule": result.get("n_clipped_notehead_fragments_dropped"),
        "edge": sorted(edge, key=lambda r: r["height_spaces"]),
        "interior": sorted(interior, key=lambda r: r["height_spaces"]),
    }


def report(name: str, survey_result: dict) -> None:
    interior = survey_result["interior"]
    edge = survey_result["edge"]
    print(f"\n=== {name}")
    print(f"  the rule dropped {survey_result['dropped_by_the_rule']} detections "
          f"during the run (some of which the deduper would also have removed)")
    if interior:
        heights = [r["height_spaces"] for r in interior]
        below = sum(1 for h in heights if h < LIMIT_SPACES)
        print(f"  interior noteheads {len(interior):4d}   "
              f"{heights[0]:.2f} - {heights[-1]:.2f} spaces, {below} below "
              f"{LIMIT_SPACES}")
    print(f"  edge-touching       {len(edge):4d}")
    for r in edge:
        verdict = "fragment" if r["height_spaces"] < LIMIT_SPACES else "note"
        print(f"     h={r['height_spaces']:.2f}  {r['class']:22s} "
              f"staff {r['staff']:2d} m{r['measure']}  "
              f"conf={r['confidence']:.2f}  {verdict}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--works", nargs="+", default=list(DEFAULT_WORKS))
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    args = ap.parse_args(argv)

    for work_id in args.works:
        path = args.fixtures / f"{work_id}.omr.json"
        if not path.is_file():
            print(f"{work_id}: no transcription on disk — run orchestral_eval first")
            continue
        report(work_id, survey(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
