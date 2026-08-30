"""Re-run the July 2026 detection-confidence probe on the current tree.

The July probe (`benchmarks/omr-detection-probe-2026-07/findings.md`) concluded
that the orchestral wall is a synthetic->real DOMAIN gap rather than a threshold
problem, and it is the stated reason the project stopped trying to improve
detection. It rested partly on a false-positive flood — noteheads 2.4-3.5x when
the confidence dropped to 0.10 — measured at `imgsz 2048` on narrow orchestral
cells, which is exactly the geometry the 2026-08-28 `imgsz` fix was about. So
the flood needed re-measuring before the conclusion could be trusted.

Same two pages, same two thresholds, same DPI. What changed underneath: `imgsz`
is now derived per cell, and `_staff_x_extent` no longer loses the staff's left
edge, so the cells themselves are different (and include the header).

    python3 benchmarks/omr-detection-probe-2026-08/rerun_july_probe.py

Pages live in the gitignored score corpus; a machine without them gets a clear
message rather than a traceback.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.transcribe import transcribe  # noqa: E402

SCORES = Path(
    "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores"
)
WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"

# (label, pdf, page_index, printed meter) — the July probe's two pages: movement
# first pages, where the meter is printed prominently after the clef, i.e. the
# detector's best case.
PAGES = [
    ("bolero-p1", SCORES / "IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 1, "3/4"),
    ("mahler5-p1", SCORES / "Mahler_5_.pdf", 1, "2/4"),
]
CONFS = (0.25, 0.10)
DPI = 300

# A time-signature digit within this many canonical pixels of the cell's left
# edge is the instrument-number misread the July probe filtered out; a real
# meter is printed after the clef.
EDGE_X = 16


def counts(result: dict) -> dict:
    dets = [
        (d, st)
        for page in result["pages"]
        for sysm in page["systems"]
        for st in sysm["staves"]
        for m in st["measures"]
        for d in m["detections"]
    ]
    time_sigs = [(d, st) for d, st in dets if d["class"].startswith("timeSig")]
    return {
        "noteheads": sum(1 for d, _ in dets if d["class"].startswith("notehead")),
        "time_sig_real": sum(1 for d, _ in time_sigs if d["bbox"][0] >= EDGE_X),
        "time_sig_edge": sum(1 for d, _ in time_sigs if d["bbox"][0] < EDGE_X),
        "clef_dets": sum(1 for d, _ in dets if "clef" in d["class"].lower()),
        "staves_with_clef_read": sum(
            1
            for page in result["pages"]
            for sysm in page["systems"]
            for st in sysm["staves"]
            if st.get("clef_source")
        ),
        "staves": sum(
            len(sysm["staves"]) for page in result["pages"] for sysm in page["systems"]
        ),
    }


def main() -> int:
    if not WEIGHTS.exists():
        print(f"no weights at {WEIGHTS}", file=sys.stderr)
        return 1
    out: dict[str, dict] = {}
    for label, pdf, page_index, meter in PAGES:
        if not pdf.exists():
            print(f"{label:12s} SKIP (missing {pdf.name})")
            continue
        out[label] = {"printed_meter": meter}
        for conf in CONFS:
            result = transcribe(
                pdf_path=pdf, pages=[page_index], weights=WEIGHTS,
                dpi=DPI, conf_threshold=conf,
            )
            c = counts(result)
            out[label][str(conf)] = c
            print(f"{label:12s} conf={conf:<5} staves={c['staves']:3d} "
                  f"clef_read={c['staves_with_clef_read']:3d} "
                  f"noteheads={c['noteheads']:5d} "
                  f"timesig real={c['time_sig_real']} edge={c['time_sig_edge']}")
    dest = Path(__file__).resolve().parent / "results.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
