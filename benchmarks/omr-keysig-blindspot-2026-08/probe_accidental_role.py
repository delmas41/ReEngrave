"""The key-signature "blindness" is a class-ROLE mismatch, not a detection failure.

`benchmarks/omr-detection-probe-2026-08/findings.md` records that Beethoven 5
p.15's key-signature flats are undetected at conf 0.25, 0.10 and 0.05 alike, and
calls that "a genuine blindness to one class on one kind of print". It is not.
The detector finds the flats; it labels them `accidentalFlat` (an inline
accidental) rather than `keyFlat` (a key-signature marker). The whole
key-signature path — `_detect_key_sig_from_cell`, `_key_sig_read_from_dets`,
`key_signature_locator` — consumes only `keySharp`/`keyFlat`, so those
detections are discarded before anything positional runs.

`_detect_key_sig_from_cell` states the assumption in its own docstring:
"the detector's keySharp / keyFlat markers (which DSv2 emits distinctly from
inline accidentals)". On this print it does not.

This probe measures what changes if the SAME slot-table fit is given the
accidental detections instead: per staff, the fit from key markers (what ships)
against the fit from accidentals, using each staff's real clef from a pipeline
run rather than an assumed treble.

    python3 benchmarks/omr-keysig-blindspot-2026-08/probe_accidental_role.py \
        --pdf <score.pdf> --page 15 --dpi 600
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.key_signature_geometry import fit_key_signature  # noqa: E402
from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.transcribe import (  # noqa: E402
    _DETECTOR_FIT_CONFIG, _staff_positions_for, transcribe,
)
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell  # noqa: E402


def clefs_by_staff(pdf: Path, page_index: int, dpi: int, weights: Path) -> dict[int, str]:
    """Each staff's clef as the production pipeline reads it."""
    result = transcribe(pdf_path=pdf, pages=[page_index], weights=weights, dpi=dpi)
    out: dict[int, str] = {}
    for pg in result["pages"]:
        for sysm in pg["systems"]:
            for st in sysm["staves"]:
                if st.get("clef"):
                    out[st["staff_index"]] = st["clef"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--weights", default="/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
                                         "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")
    args = ap.parse_args()

    pdf, weights = Path(args.pdf), Path(args.weights)
    clefs = clefs_by_staff(pdf, args.page, args.dpi, weights)
    pws = detect_barlines(detect_staves(render_page(pdf, args.page, dpi=args.dpi)))
    header = header_cells_for_page(pws)
    det = YoloDetector(weights, device="auto")

    print(f"\n{'staff':>5} {'clef':>8} {'keyF':>5} {'keyS':>5} {'accF':>5} {'accS':>5} "
          f"{'markers':>8} {'accidentals':>12}")
    print("-" * 66)
    marker_read = accidental_new = 0
    for si in sorted(header):
        cell = header[si]
        if len(cell.staff_line_ys_canonical) != 5:
            continue  # one-line staff: no geometry to fit against
        clef = clefs.get(si)
        dets = det.detect(cell, conf_threshold=args.conf, imgsz=imgsz_for_cell(cell))

        def group(prefix):
            return [d for d in dets if d.smufl_name.lower().startswith(prefix)]

        kf, ks = group("keyflat"), group("keysharp")
        af, as_ = group("accidentalflat"), group("accidentalsharp")

        def fit(marks, acc):
            if not marks or clef is None:
                return None
            pos = _staff_positions_for(marks, cell)
            if pos is None:
                return None
            r = fit_key_signature(pos, clef, acc, _DETECTOR_FIT_CONFIG)
            return r.fifths if r is not None and r.fifths else None

        mk = fit(kf, "b") if len(kf) >= len(ks) else fit(ks, "#")
        ac = fit(af, "b") if len(af) >= len(as_) else fit(as_, "#")
        marker_read += mk is not None
        accidental_new += (ac is not None and mk is None)
        print(f"{si:>5} {str(clef):>8} {len(kf):>5} {len(ks):>5} {len(af):>5} {len(as_):>5} "
              f"{str(mk):>8} {str(ac):>12}")

    print("-" * 66)
    print(f"staves the shipping marker path reads: {marker_read}")
    print(f"staves the accidental path would ADD:  {accidental_new}")


if __name__ == "__main__":
    main()
