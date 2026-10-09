"""The STAGED reader with PERFECT EYES: Sean's boxes in place of the detector (plan C6).

    python3 -m tools.omr.hand_truth.perfect_eyes <page.json> --pdf <score> --out <dir>
        [--through adjudicate] [--no-surya] [--no-ocr]

Sean 2026-10-08: *"send out a copy of the work to lilypond so that I could
visually check each measure side by side."* Boxes are not music — something
has to turn them into notes and rhythm — so this runs the PRODUCT PATH
unchanged (``pipeline.run_staged``), handing it a detector that returns the
page's truth boxes instead of the model's. Everything after the detector is
the reader as it ships. It writes the record, the MusicXML, the ``.ly`` and,
where ``lilypond`` is on PATH, the PDF.

What the result means:

* a bar that looks WRONG beside the print is either a LABEL error (back to
  that cell) or a READER error — the reader misread perfect boxes, a finding
  for Phase 2, traceable with ``python3 -m tools.omr.staged.trace``;
* the same run is the CEILING: what the reader produces when the eyes are
  perfect, so a gap between it and a real run is the detector's share.

The stand-in sees exactly what a detector would: the boxes whose CENTRE lies
in the cell the pipeline cut (a mark cut through by a cell edge belongs to the
cell that holds most of it), in that cell's canonical frame, confidence 1.0.
``noise``, ``text`` and staff lines are not detector classes and are never
returned.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from tools.omr.hand_truth import store
from tools.omr.hand_truth.store import NOISE, TEXT, PageTruth

_NOT_DETECTOR = {NOISE, TEXT, "staff"}


class PageTruthDetector:
    """Duck-types ``YoloDetector.detect`` over a page store."""

    def __init__(self, page: PageTruth):
        self.page = page
        self.weights_path = f"hand-truth:{page.edition}:{page.pdf_page_index}"
        self.calls = 0

    def detect(self, cell: Any, conf_threshold: float = 0.25, imgsz: Optional[int] = None,
               iou_threshold: float = 0.7, agnostic_nms: bool = False, **_: Any) -> List[Any]:
        from tools.omr.template_matcher import SymbolDetection
        from tools.omr.yolo_detector import _class_name_to_category

        self.calls += 1
        if int(getattr(cell, "page_index", -1)) != self.page.pdf_page_index:
            return []
        x0, y0, x1, y1 = (float(v) for v in cell.bbox_page_px)
        h, w = cell.image.shape[:2]
        sx, sy = w / max(1e-9, x1 - x0), h / max(1e-9, y1 - y0)
        out = []
        for b in self.page.boxes:
            if b.cls in _NOT_DETECTOR:
                continue
            bx0, by0, bx1, by1 = b.rect
            cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
            if not (x0 <= cx < x1 and y0 <= cy < y1):
                continue
            l, t = (max(bx0, x0) - x0) * sx, (max(by0, y0) - y0) * sy
            r, btm = (min(bx1, x1) - x0) * sx, (min(by1, y1) - y0) * sy
            out.append(SymbolDetection(cell=cell, smufl_name=b.cls, category=_class_name_to_category(b.cls),
                                       x_canonical=int(round(l)), y_canonical=int(round(t)),
                                       width_canonical=max(1, int(round(r - l))),
                                       height_canonical=max(1, int(round(btm - t))), confidence=1.0))
        return sorted(out, key=lambda d: (d.x_canonical, d.y_canonical))


def run_on_prepared(page: PageTruth, prepared: Sequence, *, through: str = "infer",
                    surya: bool = False, ocr: bool = False, pdf_path: Any = None) -> Dict[str, Any]:
    """The stages over pages already prepared (the testable core)."""
    from tools.omr.staged import pipeline

    det = PageTruthDetector(page)
    result = pipeline.run_staged_on(prepared, detector=det, pdf_path=pdf_path,
                                    surya_fallback=surya, ocr_fallback=ocr, through=through)
    result.setdefault("provenance", {})["detector"] = {
        "kind": "hand-truth (perfect eyes)", "page": f"{page.edition}:{page.pdf_page_index}",
        "state": page.state, "boxes": len(page.boxes), "detect_calls": det.calls}
    return result


def write_outputs(result: Dict[str, Any], out_dir: Path, stem: str, *, through: str = "infer",
                  pdf: bool = True) -> Dict[str, str]:
    from tools.omr.staged import export as staged_export
    from tools.omr.staged import lilypond as staged_lily
    from tools.omr.staged.record_io import dumps_for_file

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {"record": str(out_dir / f"{stem}.record.json")}
    Path(paths["record"]).write_text(dumps_for_file(result, separators=(",", ":"), default=str))
    if through != "infer":
        return paths  # EXPORT runs only after INFER, exactly as the staged CLI refuses it
    xml, rep = staged_export.to_musicxml(result)
    paths["musicxml"] = str(out_dir / f"{stem}.musicxml")
    Path(paths["musicxml"]).write_text(xml)
    Path(paths["musicxml"] + ".coverage.json").write_text(json.dumps(rep, indent=2, default=str))
    ly, ly_rep = staged_lily.to_lilypond(result)
    paths["lilypond"] = str(out_dir / f"{stem}.ly")
    Path(paths["lilypond"]).write_text(ly)
    Path(paths["lilypond"] + ".coverage.json").write_text(json.dumps(ly_rep, indent=2, default=str))
    if pdf:
        from tools.omr.staged.__main__ import _render_pdf

        target = out_dir / f"{stem}.pdf"
        _render_pdf(Path(paths["lilypond"]), target)
        if target.exists():  # `lilypond` absent: the .ly is written and no PDF is claimed
            paths["pdf"] = str(target)
    return paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("page")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--through", default="infer", choices=("gather", "adjudicate", "evaluate", "infer"))
    ap.add_argument("--no-surya", action="store_true")
    ap.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args(list(argv) if argv is not None else None)
    page = store.load(Path(a.page))
    if page.state == "labeling":
        print("⚠️ this page is still being LABELED: the result shows the labels as they are now")
    from tools.omr.staged.pipeline import prepare_pages

    prepared = prepare_pages(a.pdf, [page.pdf_page_index], dpi=page.dpi)
    result = run_on_prepared(page, prepared, through=a.through, surya=not a.no_surya,
                             ocr=not a.no_ocr, pdf_path=a.pdf)
    stem = f"{page.edition}-p{page.pdf_page_index}-perfect-eyes"
    print(json.dumps(write_outputs(result, a.out, stem, through=a.through), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
