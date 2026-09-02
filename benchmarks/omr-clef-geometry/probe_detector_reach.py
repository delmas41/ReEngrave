"""Why does the detector supply a clef on only some staves — and would the
header crop reach the rest?

`eval_pipeline_clefs --wide` says the detector is 98% accurate on the 97 staves
of 166 it reaches, and that the 69 it does not reach fall to the positional
default, which is wrong 17 times. That makes "get the detector to fire more
often" the largest measured lever in the whole clef layer, and the first
question is whether it needs a better model at all.

It may not. The detector reads the staff-START MEASURE CELL. `staff_header`
exists because on real prints the header is often not inside that cell — the
same failure that made key signatures unreadable until they were re-read from a
measured window. `transcribe._header_cell_beats_measure_cell` already switches
the clef readers to the header crop, but only where the measure cell begins more
than a staff space past the window, deliberately conservatively.

So this measures, per staff on the hand-read orchestral pages:

  * what the detector reads from the measure cell,
  * what it reads from the header cell,
  * whether the existing gate would have switched (it redirects only the CV
    locator and the specialist — the DETECTOR always reads the measure cell,
    and the header crop's clef is computed for the key-signature slot table
    and then thrown away),
  * and the hand-read truth.

    python3 benchmarks/omr-clef-geometry/probe_detector_reach.py
    python3 benchmarks/omr-clef-geometry/probe_detector_reach.py --per-staff

The number that matters is the bottom line: staves the measure cell misses that
the header cell reads CORRECTLY, against those it reads WRONGLY. This is a
proposal for a change, not a change; a wrong clef transposes every note on its
staff, so the second column has to be small before anything is switched.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines,
    extract_measures,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import (  # noqa: E402
    header_cells_for_page,
    header_windows_for_page,
)
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr.transcribe import (  # noqa: E402
    _clef_from_dets,
    _header_cell_beats_measure_cell,
)
from probe_cluster_too_big import C_CLEFS, orchestral_pages  # noqa: E402

WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"


def family(clef: str | None) -> str:
    if clef is None:
        return "none"
    return "C" if clef in C_CLEFS else clef


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--weights", type=Path, default=WEIGHTS)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=None,
                    help="None matches the pipeline, which sizes "
                         "inference per cell (`imgsz_for_cell`)")
    ap.add_argument("--per-staff", action="store_true")
    args = ap.parse_args()
    if not args.weights.exists():
        print(f"no weights at {args.weights}", file=sys.stderr)
        return 1

    from tools.omr.yolo_detector import YoloDetector

    detector = YoloDetector(str(args.weights), device="auto")
    tally: Counter[str] = Counter()
    recovered_right: list[str] = []
    recovered_wrong: list[str] = []
    lost: list[str] = []
    wrong_today: list[str] = []
    gate_would_switch = 0

    for page in orchestral_pages():
        if not page.get("flat"):
            continue     # the flat corpus is the one matched staff-for-staff
        pdf = Path(page["pdf"]).expanduser()
        if not pdf.is_absolute():
            pdf = REPO / page["pdf"]
        if not pdf.exists():
            continue
        rendered = render_page(pdf, page["page_index"], dpi=page["dpi"])
        pws = detect_barlines(detect_staves(rendered))
        cells = resegment_fused_measures(pws, extract_measures(pws))
        remove_staff_lines(cells)
        windows = header_windows_for_page(pws)
        header_cells = header_cells_for_page(pws, windows=windows)
        first: dict[int, object] = {}
        for c in sorted(cells, key=lambda c: c.measure_index):
            first.setdefault(c.staff_index, c)
        ordered = sorted(pws.staves, key=lambda s: s.top_y)
        if len(ordered) != page["n_staves"]:
            continue
        for ordinal, staff in enumerate(ordered):
            truth = page["clefs"][ordinal]
            if truth is None:
                continue
            mcell = first.get(staff.staff_index)
            hcell = header_cells.get(staff.staff_index)
            kw = dict(conf_threshold=args.conf, imgsz=args.imgsz,
                      iou_threshold=0.7, agnostic_nms=False)
            m_clef = (_clef_from_dets(detector.detect(mcell, **kw))
                      if mcell is not None else None)
            h_clef = (_clef_from_dets(detector.detect(hcell, **kw))
                      if hcell is not None else None)
            gated = _header_cell_beats_measure_cell(
                windows.get(staff.staff_index), staff, mcell)
            gate_would_switch += int(gated)
            key = (f"measure={family(m_clef):<6} header={family(h_clef):<6} "
                   f"gate={'header' if gated else 'measure'}")
            tally[key] += 1
            # What the pipeline actually ends up with today. The DETECTOR
            # always reads the measure cell — `_header_cell_beats_measure_cell`
            # redirects only the CV locator and the optional specialist, not
            # `_detections_for_cell`'s own `detector.detect(cell, ...)`. The
            # header crop's clef is computed for the key-signature slot table
            # and then discarded.
            got = m_clef
            if got is None and (m_clef or h_clef):
                lost.append(f"{page['id']} s{staff.staff_index} truth={truth} "
                            f"measure={m_clef} header={h_clef} "
                            f"gate={'header' if gated else 'measure'}")
            elif got is not None and family(got) != family(truth):
                wrong_today.append(f"{page['id']} s{staff.staff_index} "
                                   f"truth={truth} got={got}")
            if m_clef is None and h_clef is not None:
                tag = (f"{page['id']} s{staff.staff_index} truth={truth} "
                       f"header={h_clef}{' [gate switches]' if gated else ''}")
                (recovered_right if family(h_clef) == family(truth)
                 else recovered_wrong).append(tag)
            if args.per_staff:
                print(f"    {page['id']:<12} s{staff.staff_index:<3} "
                      f"truth={truth:<8} measure={m_clef} header={h_clef} "
                      f"gate={'header' if gated else 'measure'}")

    total = sum(tally.values())
    print(f"\n{total} staves on the hand-read orchestral pages\n")
    for key, n in tally.most_common():
        print(f"  {n:>4}  {key}")
    print(f"\n  the existing gate would read the header on {gate_would_switch} "
          f"of {total}")
    print(f"\n  measure cell blank, header cell RIGHT: {len(recovered_right)}")
    for t in recovered_right:
        print(f"    {t}")
    print(f"\n  measure cell blank, header cell WRONG: {len(recovered_wrong)}")
    for t in recovered_wrong:
        print(f"    {t}")
    print(f"\n  READS THE GATE THROWS AWAY — one crop has a clef, the gate "
          f"picked the other: {len(lost)}")
    for t in lost:
        print(f"    {t}")
    print(f"\n  wrong clefs the detector supplies today: {len(wrong_today)}")
    for t in wrong_today:
        print(f"    {t}")
    print("\nA wrong clef transposes every note on its staff. The WRONG lists "
          "have to be\nsmall before any of this is switched on.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
