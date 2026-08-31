"""Score clef reading on a page where the pipeline reads NO clef at all.

`eval_pipeline_clefs.py` scores 52 hand-read staves across three pages and reports
50/52. Those pages are ones where the detector already works, so that harness
cannot measure a reader whose entire value is on pages where it does not — and it
is why the clef specialist measured "+0" there while being transformative here.

Beethoven 5 p.48 is the complement: 17 staves, and the shipped default supplies a
clef for none of them. Every one falls back to the positional default, which
answers "treble" every time — so the page scores 8/17 by accident, on the eight
staves that genuinely are treble, and all nine errors are the documented
"non-treble read as treble".

    python3 benchmarks/omr-clef-geometry/eval_blind_page_clefs.py
    OMR_CLEF_WEIGHTS=omr-weights/deepscoresv2-yolov8l-clef-ft-boxfix-2026-07-13.pt \\
        python3 benchmarks/omr-clef-geometry/eval_blind_page_clefs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.transcribe import DEFAULT_WEIGHTS, transcribe  # noqa: E402

GT = Path(__file__).resolve().parent / "ground-truth-beet5-p48.json"


def main() -> int:
    gt = json.loads(GT.read_text())
    truth = {s["staff_index"]: s["clef"] for s in gt["staves"]}
    label = {s["staff_index"]: s["label"] for s in gt["staves"]}
    pdf = Path(gt["pdf"])
    if not pdf.exists():
        print(f"SKIPPED: PDF not on this machine ({pdf})")
        return 0

    weights = Path(DEFAULT_WEIGHTS)
    if not weights.exists():
        weights = Path(__file__).resolve().parents[2] / "omr-weights" / weights.name
    result = transcribe(pdf_path=pdf, pages=[gt["page_index"]],
                        weights=weights, dpi=gt["dpi"])

    got: dict[int, tuple[str | None, str]] = {}
    for page in result["pages"]:
        for system in page["systems"]:
            for staff in system["staves"]:
                got[staff["staff_index"]] = (staff.get("clef"),
                                             staff.get("clef_source") or "defaulted")

    correct = 0
    by_source: dict[str, list[int]] = {}
    print(f"\n{'staff':>5} {'part':<12} {'truth':<7} {'read':<7} {'source':<12}")
    print("-" * 50)
    for idx in sorted(truth):
        clef, source = got.get(idx, (None, "-"))
        good = clef == truth[idx]
        correct += good
        by_source.setdefault(source, []).append(good)
        print(f"{idx:>5} {label[idx]:<12} {truth[idx]:<7} {str(clef):<7} {source:<12}"
              f"{'' if good else '  WRONG'}")

    n = len(truth)
    print("-" * 50)
    print(f"correct: {correct}/{n} = {100 * correct / n:.0f}%\n")
    print(f"  {'source':<14}{'staves':>7}{'correct':>9}")
    for source, hits in sorted(by_source.items()):
        print(f"  {source:<14}{len(hits):>7}{sum(hits):>9}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
