"""Page truth -> YOLO cell labels, so every box Sean labels can also train (Sean 2026-10-08).

One truth feeds both the tests and the detector. Three refusals keep that from
undoing itself:

1. **A held-out page never trains** (``data/hand-truth/held-out.json``, Sean
   2026-10-08): a page cannot be test truth for weights that were trained on
   it — the detector would be graded on ink it memorised.
2. **A page still being labeled never trains** (state ``labeling``); ``checked``
   or later does.
3. **A cell not inspected for every bit of ink is skipped.** Anything unboxed
   on a training cell is BACKGROUND (CLAUDE.md §9) — that is how a one-epoch
   fine-tune took beams 127 -> 0. A whole-ink cell's empty space is real
   background; a partly-swept cell's is not.

The class vocabulary, first-index rule and line format are the existing
converter's (``training.verdicts_to_yolo_labels``), so a box exported here
indexes exactly like every version already in ``data/user-labeled``.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

import numpy as np

from tools.omr.hand_truth.completeness import families_covered
from tools.omr.hand_truth.store import NOISE, REPO, TEXT, PageTruth, StoreError
from tools.omr.training.verdicts_to_yolo_labels import (
    DEEPSCORES_208_JSON,
    _emit_yolo_line,
    load_class_names,
    name_to_first_index,
)

HELD_OUT_PATH = REPO / "data" / "hand-truth" / "held-out.json"


def held_out_pages(path: Path = HELD_OUT_PATH) -> Set[Tuple[str, int]]:
    d = json.loads(Path(path).read_text())
    return {(p["edition"], int(p["pdf_page_index"])) for p in d["pages"]}


def class_index(include_custom: bool = False) -> Dict[str, int]:
    names = load_class_names(None, DEEPSCORES_208_JSON)
    idx = name_to_first_index(names)
    if not include_custom:
        # nc=208 by default, exactly as build_catalog_yaml caps the catalog.
        idx = {n: i for n, i in idx.items() if i < 208}
    return idx


def cell_lines(page: PageTruth, cell_id: str, index: Dict[str, int]) -> Tuple[list, Counter]:
    """YOLO lines for one cell in its canonical frame, and what was not written."""
    c = page.cell(cell_id)
    lines, skipped = [], Counter()
    for box, r, _clipped in page.boxes_in_cell(cell_id):
        if box.cls in (NOISE, TEXT):
            skipped[f"not_a_detector_class:{box.cls}"] += 1
            continue
        line = _emit_yolo_line(class_name=box.cls,
                               bbox={"x": r[0], "y": r[1], "w": r[2] - r[0], "h": r[3] - r[1]},
                               img_w=c.canonical_w, img_h=c.canonical_h, class_index=index)
        if line is None:
            skipped[f"not_in_vocabulary:{box.cls}"] += 1
        else:
            lines.append(line)
    return lines, skipped


def export_page(page: PageTruth, page_image: Optional[np.ndarray], out_dir: Path, *,
                held_out: Optional[Iterable[Tuple[str, int]]] = None,
                index: Optional[Dict[str, int]] = None) -> Dict:
    """Write ``images/`` + ``labels/`` for every whole-ink cell of ``page``.

    ``page_image`` is the page raster at ``page.dpi`` (H x W or H x W x C); pass
    ``None`` to write labels only (a dry run that still applies every refusal).
    """
    held = set(held_out if held_out is not None else held_out_pages())
    if (page.edition, page.pdf_page_index) in held:
        raise StoreError(f"{page.edition} page {page.pdf_page_index} is HELD OUT: it is test "
                         "truth and never trains")
    if page.state == "labeling":
        raise StoreError(f"{page.edition} page {page.pdf_page_index} is still being labeled")
    if page_image is not None and page_image.shape[:2] != (page.height, page.width):
        raise StoreError(f"page image {page_image.shape[:2]} is not the page's "
                         f"{(page.height, page.width)}")
    index = index if index is not None else class_index()
    out_dir = Path(out_dir)
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    if page_image is not None:
        (out_dir / "images").mkdir(parents=True, exist_ok=True)
    written, not_whole_ink, skipped = [], [], Counter()
    for c in page.cells:
        if families_covered(c.inspected) is not None:
            not_whole_ink.append(c.id)
            continue
        name = f"{page.edition}-p{page.pdf_page_index}-{c.id}"
        lines, sk = cell_lines(page, c.id, index)
        skipped += sk
        (out_dir / "labels" / f"{name}.txt").write_text("".join(l + "\n" for l in lines))
        if page_image is not None:
            import cv2

            x0, y0, x1, y1 = (int(round(v)) for v in c.rect)
            crop = page_image[max(0, y0):y1, max(0, x0):x1]
            crop = cv2.resize(crop, (c.canonical_w, c.canonical_h), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(out_dir / "images" / f"{name}.png"), crop)
        written.append(name)
    return {
        "edition": page.edition,
        "pdf_page_index": page.pdf_page_index,
        "state": page.state,
        "cells_written": len(written),
        "cells_skipped_not_whole_ink": not_whole_ink,
        "boxes_not_written": dict(sorted(skipped.items())),
    }
