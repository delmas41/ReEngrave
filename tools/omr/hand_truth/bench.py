"""The bridge between a page store and the labeling UI Sean already uses.

Sean labels ONE CELL AT A TIME in ``tools/omr/annotate/server`` with the same
hotkeys as before; the page store is where the boxes live. This module:

``write_bench``
    lays a page out as an ordinary bench directory — ``cells.json``,
    ``cells/<id>.png``, ``detections/<id>.json``, ``verdicts/<id>.verdict.json``
    and an ``all-ink`` ``batch_config.json`` — so the server needs no new UI.
    Detection ids ARE page ids (``q*`` pre-fill, ``b*`` drawn, ``L*`` staff
    line), so they survive every regeneration of the files.

``sync_cell``
    folds one saved cell verdict back into the page (the server calls it after
    every save, and the UI autosaves, so it is idempotent):

    ====================  ==========================================================
    on a pre-fill (q*)    TP -> confirmed; FP -> rejected; fixed class/box -> fixed
    on a truth box        FP -> removed (Sean's latest word); fixed -> edited
    an added box          drawn into the page in page pixels, keyed ``<cell>#<id>``
                          so a re-save updates it instead of drawing it twice;
                          an added box Sean deleted is removed from the page
    a staff line (L*)     all five TP -> lines right; any FP / moved -> lines wrong
    inspected_passes      copied to the cell (``all-ink`` = every family)
    ====================  ==========================================================

``refresh_cells``
    rewrites the detection and verdict files of every cell the changed boxes
    touch, so a box drawn in one cell is already there, marked TP, when Sean
    opens its overlapping neighbour — one mark, one box.

A text box carries its words in the UI's Notes field; one with no words yet is
held back (and flagged) until Sean types them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import numpy as np

from tools.omr.hand_truth.store import (
    ALL_INK_PASS, TEXT, Box, PageTruth, Rect, StoreError,
)

#: The quick-pick slots for the whole-ink pass: the 27-class draw-rich palette
#: (pass-configs/draw-rich.json) plus the whole-ink families it lacked. The
#: UI's escape hatch still reaches every other class.
ALL_INK_SLOTS: List[str] = [
    "noteheadBlack", "noteheadHalf", "noteheadWhole", "stem", "beam", "ledgerLine",
    "flag8thUp", "flag8thDown", "augmentationDot", "accidentalFlat", "accidentalSharp",
    "accidentalNatural", "keyFlat", "keySharp", "keyNatural", "restQuarter", "rest8th",
    "rest16th", "restHalf", "restWhole", "slur", "tie", "dynamicP", "dynamicF",
    "dynamicCrescendoHairpin", "dynamicDiminuendoHairpin", "clefG", "clefF", "clefCAlto",
    "barlineSingle", "articStaccatoAbove", "text", "noise",
]
#: Classes the picker offers only in page-store mode. Neither trains the
#: detector (export_yolo skips both); both exist so every bit of ink can be boxed.
PAGE_TRUTH_CLASSES: List[str] = ["text", "noise"]

STAFF_LINE_CLASS = "staff"


def _cell_rect_px(r: Rect) -> Dict[str, int]:
    x0, y0, x1, y1 = r
    return {"x": int(round(x0)), "y": int(round(y0)),
            "w": max(1, int(round(x1 - x0))), "h": max(1, int(round(y1 - y0)))}


def _bbox_to_rect(b: Dict) -> Rect:
    x, y, w, h = (float(b.get(k, 0)) for k in ("x", "y", "w", "h"))
    return (x, y, x + w, y + h)


def _overlaps(a: Rect, b: Rect) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def _first_cell_of_staff(page: PageTruth) -> Dict[tuple, str]:
    out: Dict[tuple, tuple] = {}
    for c in page.cells:
        if c.kind != "measure" or c.system is None or c.staff is None or not c.staff_line_ys:
            continue
        key = (c.system, c.staff)
        if key not in out or (c.measure or 0) < out[key][0]:
            out[key] = (c.measure or 0, c.id)
    return {k: v[1] for k, v in out.items()}


def _staff_line_dets(page: PageTruth, cell_id: str) -> List[Dict]:
    """Five thin 'staff' boxes on a staff's first cell: TP each if the line is right."""
    c = page.cell(cell_id)
    out = []
    for i, y in enumerate(c.staff_line_ys or []):
        out.append({"id": f"L{c.system}.{c.staff}.{i}", "smufl_name": STAFF_LINE_CLASS,
                    "category": "structural", "x": 0, "y": int(round(y)) - 3,
                    "w": c.canonical_w, "h": 6, "confidence": 1.0})
    return out


def cell_detections(page: PageTruth, cell_id: str) -> List[Dict]:
    """What the UI shows in a cell: pre-fills, truth boxes from elsewhere, staff lines."""
    c = page.cell(cell_id)
    dets: List[Dict] = []
    for b, r, _ in page.boxes_in_cell(cell_id):
        if b.ref and b.ref.startswith(f"{cell_id}#"):
            continue  # Sean's own drawing in THIS cell is shown as his added box
        dets.append({"id": b.id, "smufl_name": b.cls, "category": "", **_cell_rect_px(r),
                     "confidence": 1.0, "source": f"truth:{b.origin}"})
    for q in page.queue:
        if _overlaps(q.rect, c.rect):
            x0, y0, x1, y1 = q.rect
            cx0, cy0, cx1, cy1 = c.rect
            r = c.to_cell((max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)))
            dets.append({"id": q.id, "smufl_name": q.cls, "category": "", **_cell_rect_px(r),
                         "confidence": float(q.score if q.score is not None else 0.0),
                         "source": q.source})
    if _first_cell_of_staff(page).get((c.system, c.staff)) == cell_id:
        dets.extend(_staff_line_dets(page, cell_id))
    return dets


def _det_state(d: Dict, verdict: Optional[str], notes: str = "") -> Dict:
    return {"id": d["id"], "verdict": verdict, "model_predicted_class": d["smufl_name"],
            "human_corrected_class": None, "model_predicted_category": d.get("category", ""),
            "human_corrected_category": None,
            "model_bbox": {k: d[k] for k in ("x", "y", "w", "h")}, "human_bbox": None,
            "confidence": d.get("confidence", 0.0), "notes": notes}


def _write_cell_files(page: PageTruth, bench: Path, cell_id: str) -> None:
    dets = cell_detections(page, cell_id)
    (bench / "detections" / f"{cell_id}.json").write_text(
        json.dumps({"cell_id": cell_id, "detections": dets}, indent=1))
    vp = bench / "verdicts" / f"{cell_id}.verdict.json"
    prior = json.loads(vp.read_text()) if vp.exists() else {}
    keep = {d["id"]: d for d in prior.get("detections", [])}
    truth_ids = {b.id for b in page.boxes}
    out = []
    for d in dets:
        old = keep.get(d["id"])
        if d["id"] in truth_ids:
            st = _det_state(d, "TP", notes=(old or {}).get("notes", ""))  # already truth
        elif old is not None:
            st = {**_det_state(d, old.get("verdict")),
                  **{k: old.get(k) for k in ("human_corrected_class", "human_corrected_category",
                                             "human_bbox", "notes") if old.get(k) is not None}}
        else:
            st = _det_state(d, None)
        out.append(st)
    state = {"cell_id": cell_id, "schema_version": 2,
             "labeled_at_utc": prior.get("labeled_at_utc"),
             "detections": out,
             "added_detections": prior.get("added_detections", []),
             "inspected_passes": prior.get("inspected_passes", [])}
    vp.write_text(json.dumps(state, indent=2))


def write_bench(page: PageTruth, cell_images: Dict[str, np.ndarray], bench: Path,
                pdf: str = "") -> Path:
    """Lay ``page`` out as a bench the annotate server serves unchanged."""
    import cv2

    bench = Path(bench)
    for d in ("cells", "detections", "verdicts"):
        (bench / d).mkdir(parents=True, exist_ok=True)
    manifest = []
    for c in page.cells:
        img = cell_images.get(c.id)
        if img is None:
            raise StoreError(f"no image for cell {c.id}")
        if img.shape[:2] != (c.canonical_h, c.canonical_w):
            raise StoreError(f"cell {c.id}: image {img.shape[:2]} is not its canonical "
                             f"{(c.canonical_h, c.canonical_w)}")
        cv2.imwrite(str(bench / "cells" / f"{c.id}.png"), img)
        manifest.append({
            "cell_id": c.id, "pdf": pdf, "page": page.pdf_page_index, "kind": c.kind,
            "system_index": c.system, "staff_index": c.staff, "measure_index": c.measure,
            "cell_png_path": str(Path("cells") / f"{c.id}.png"),
            "staff_line_ys_canonical": list(c.staff_line_ys or []),
            "cell_canonical_w": c.canonical_w, "cell_canonical_h": c.canonical_h,
            "page_rect_px": list(c.rect), "edition": page.edition,
        })
        _write_cell_files(page, bench, c.id)
    (bench / "cells.json").write_text(json.dumps(manifest, indent=1))
    (bench / "batch_config.json").write_text(json.dumps({
        "pass_name": ALL_INK_PASS,
        "note": "EVERY bit of ink in the cell (Sean 2026-10-08). Confirm a pre-fill with t, "
                "reject with f, fix with c / b, draw what nobody proposed. Printed words: class "
                "'text' and type them in Notes. Specks and bleed-through: 'noise'. On a staff's "
                "first cell, mark each of the five thin 'staff' boxes t if that line is right.",
        "classes": ALL_INK_SLOTS,
    }, indent=1))
    return bench


def _flag_once(page: PageTruth, kind: str, message: str, cell_id: str) -> None:
    if not any(f.kind == kind and f.cell_id == cell_id and f.status == "open" and f.message == message
               for f in page.flags):
        page.raise_flag(kind, message, by="check:sync", cell_id=cell_id)


def sync_cell(page: PageTruth, bench: Path, cell_id: str) -> Set[str]:
    """Fold ``verdicts/<cell_id>.verdict.json`` into ``page``. Returns touched cell ids."""
    bench = Path(bench)
    c = page.cell(cell_id)
    vp = bench / "verdicts" / f"{cell_id}.verdict.json"
    if not vp.exists():
        return set()
    v = json.loads(vp.read_text())
    queue_ids = {q.id for q in page.queue}
    truth_ids = {b.id for b in page.boxes}
    touched: Set[str] = {cell_id}
    rects_changed: List[Rect] = []

    lines: Dict[tuple, List[Optional[str]]] = {}
    for d in v.get("detections", []):
        did, verdict = d.get("id", ""), d.get("verdict")
        new_cls = d.get("human_corrected_class") or None
        new_rect = c.to_page(_bbox_to_rect(d["human_bbox"])) if d.get("human_bbox") else None
        if did.startswith("L"):
            key = tuple(int(x) for x in did[1:].split(".")[:2])
            lines.setdefault(key, []).append(verdict if not d.get("human_bbox") else "MOVED")
            continue
        if did in queue_ids:
            if verdict == "TP":
                rects_changed.append(page.confirm_prefill(did, cell_id).rect)
            elif verdict == "FP":
                q = next(q for q in page.queue if q.id == did)
                rects_changed.append(q.rect)
                page.reject_prefill(did)
            elif verdict in ("WRONG_CATEGORY", "WRONG_BBOX"):
                rects_changed.append(page.fix_prefill(did, cell_id, cls=new_cls,
                                                      cell_rect=_bbox_to_rect(d["human_bbox"])
                                                      if d.get("human_bbox") else None).rect)
        elif did in truth_ids:
            if verdict == "FP":
                gone = page.remove_box(did)
                rects_changed.append(gone.rect)
                if gone.ref:
                    _drop_added(bench, gone.ref)
                    touched.add(gone.ref.split("#", 1)[0])
            elif verdict in ("WRONG_CATEGORY", "WRONG_BBOX") and (new_cls or new_rect):
                b = page.box(did)
                if (new_cls and new_cls != b.cls) or (new_rect and new_rect != b.rect):
                    old = b.rect
                    page.edit_box(did, cls=new_cls, rect=new_rect)
                    rects_changed += [old, b.rect]
                    if b.ref:
                        _rewrite_added(page, bench, b)
                        touched.add(b.ref.split("#", 1)[0])
    for (sy, st), vs in lines.items():
        try:
            s = page.staff(sy, st)
        except StoreError:
            continue
        if any(x in ("FP", "WRONG_BBOX", "WRONG_CATEGORY", "MOVED") for x in vs):
            s.lines_right = False
        elif vs and all(x == "TP" for x in vs):
            s.lines_right = True
        else:
            s.lines_right = None

    present = set()
    for a in v.get("added_detections", []):
        ref = f"{cell_id}#{a.get('id', '')}"
        present.add(ref)
        cls = (a.get("human_class") or "").strip()
        if not cls or not a.get("bbox"):
            continue
        rect = c.to_page(_bbox_to_rect(a["bbox"]))
        text = (a.get("notes") or "").strip() or None
        note = None if cls == TEXT else text
        b = page.box_by_ref(ref)
        if cls == TEXT and not text:
            _flag_once(page, "text_without_words", f"type the printed words of {ref} in Notes", cell_id)
            continue
        if b is None:
            b = page.draw(cell_id, cls, _bbox_to_rect(a["bbox"]), text=text if cls == TEXT else None,
                          note=note)
            b.ref = ref
            rects_changed.append(b.rect)
        elif b.cls != cls or b.rect != rect or (cls == TEXT and b.text != text) or b.note != note:
            old = b.rect
            b.cls, b.rect = cls, rect
            b.text = text if cls == TEXT else None
            b.note = note
            b.validate()
            rects_changed += [old, rect]
    for b in [b for b in page.boxes if b.ref and b.ref.startswith(f"{cell_id}#") and b.ref not in present]:
        page.remove_box(b.id)
        rects_changed.append(b.rect)

    page.mark_inspected(cell_id, v.get("inspected_passes", []))
    for r in rects_changed:
        touched |= {o.id for o in page.cells if _overlaps(o.rect, r)}
    return touched


def _added_file(bench: Path, ref: str):
    cell_id, added_id = ref.split("#", 1)
    vp = Path(bench) / "verdicts" / f"{cell_id}.verdict.json"
    return vp, (json.loads(vp.read_text()) if vp.exists() else None), added_id


def _drop_added(bench: Path, ref: str) -> None:
    """Sean removed, from a neighbour, a box he had drawn here: drop the drawing too,
    or the next save of this cell would draw it again."""
    vp, v, aid = _added_file(bench, ref)
    if v is None:
        return
    v["added_detections"] = [a for a in v.get("added_detections", []) if a.get("id") != aid]
    vp.write_text(json.dumps(v, indent=2))


def _rewrite_added(page: PageTruth, bench: Path, b: Box) -> None:
    vp, v, aid = _added_file(bench, b.ref)
    if v is None:
        return
    c = page.cell(b.ref.split("#", 1)[0])
    for a in v.get("added_detections", []):
        if a.get("id") == aid:
            a["human_class"] = b.cls
            a["bbox"] = _cell_rect_px(c.to_cell(b.rect))
    vp.write_text(json.dumps(v, indent=2))


def refresh_cells(page: PageTruth, bench: Path, cell_ids: Iterable[str]) -> None:
    for cid in sorted(set(cell_ids)):
        _write_cell_files(page, Path(bench), cid)


def on_saved(page_path: Path, bench: Path, cell_id: str) -> Set[str]:
    """The server's hook: load the page, fold the save in, refresh neighbours, save."""
    from tools.omr.hand_truth.store import load

    page = load(page_path)
    touched = sync_cell(page, bench, cell_id)
    # The saved cell's own file is the UI's; only NEIGHBOURS are rewritten here,
    # plus the saved cell's detections (a confirmed pre-fill is now truth).
    refresh_cells(page, bench, touched)
    page_path.write_text(json.dumps(page.to_json(), indent=1, sort_keys=True) + "\n")
    return touched
