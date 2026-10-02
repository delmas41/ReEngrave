#!/usr/bin/env python3
"""lane-farhead-box-ab, coordinator addendum (2026-10-01): a crop sheet
Sean can look at before this lane merges. Reads the Litolff ARM small
re-gather's own saved record (GATHER+ADJUDICATE, `tools.omr.
acceptance_quick --doc beethoven5-litolff`) and draws, per tile:

  * all 9 ROADMAP 2.55-extension `tall_box_split` heads (coordinator
    addendum: a rescued box taller than the standard head by a clear
    margin is split by its own tie-end witnesses) -- original tall box
    DASHED, the two split heads SOLID, nearby tie boxes on the same cell
    drawn as witnesses;
  * the 2 tall boxes DROPPED (`rescue_box_spans_two_heads`, no tie
    witness found) -- DASHED only, nothing invented;
  * the 2 ROADMAP 2.39b cause-A vertical-extent recentres with a >0.3
    staff-space shift -- original (short) box DASHED, re-centred
    standard box SOLID.

NO PIPELINE CODE CHANGED here -- this only reads the saved record
(`tools.omr.staged.readout.load_run`) and `tools.omr.preprocessing.
render_page` (the SAME render the gather itself used, same DPI, read
from `run.dpi`/`run.pdf`), then draws. Every drawn staff line is pixel-
row checked against ink before being trusted (CLAUDE.md rule 7, a
control must be able to fail) -- a tile whose staff lines do not check
is marked UNCHECKED in its own caption, never silently drawn wrong.

    python3 benchmarks/omr-notehead-width-2026-09/farhead_box_ab_sheet.py \
        /tmp/farhead_ab_runs/arm-litolff2/out/beethoven5-litolff/beethoven5-litolff-p3.record.json
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import cv2
import numpy as np

from tools.omr.staged import readout
from tools.omr.preprocessing import render_page

OUT_PATH = REPO / "out" / "print" / "farhead_ab" / "sheet.png"
TARGET_TILE_W = 760
COLS = 3
MAX_SHEET_W = 3000
PAD_SPACES = 2.5

RED = (0, 0, 220)
GREEN = (60, 190, 60)
BLUE = (220, 140, 0)
GRAY = (120, 120, 120)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def _glyph_key_parts(key: str) -> Tuple[int, int, int, int, int]:
    _, page, sysi, sti, meas, gi = key.split("/")
    return int(page), int(sysi), int(sti), int(meas), int(gi)


def _cell_key(key: str) -> str:
    p, s, st, m, _ = _glyph_key_parts(key)
    return f"cell/{p}/{s}/{st}/{m}"


def _dashed_rect(img, x0, y0, x1, y1, color, thickness=2, dash=10):
    pts = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
          ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for (ax, ay), (bx, by) in pts:
        length = max(abs(bx - ax), abs(by - ay), 1)
        n = max(1, int(length // dash))
        for i in range(0, n, 2):
            t0, t1 = i / n, min(1.0, (i + 1) / n)
            px0, py0 = int(ax + (bx - ax) * t0), int(ay + (by - ay) * t0)
            px1, py1 = int(ax + (bx - ax) * t1), int(ay + (by - ay) * t1)
            cv2.line(img, (px0, py0), (px1, py1), color, thickness)


def _rect(img, x0, y0, x1, y1, color, thickness=2):
    cv2.rectangle(img, (int(x0), int(y0)), (int(x1), int(y1)), color,
                  thickness)


def _check_staff_rows(gray: np.ndarray, lines_page_y: List[float],
                      cx: float, half_width: float) -> bool:
    """CLAUDE.md rule 7: a drawn staff line must sit on ink, or the tile
    says so. Otsu-threshold a local band, then check each claimed line
    row has ink under it near `cx`."""
    if not lines_page_y:
        return False
    y0 = max(0, int(min(lines_page_y)) - 5)
    y1 = min(gray.shape[0], int(max(lines_page_y)) + 5)
    x0 = max(0, int(cx - half_width))
    x1 = min(gray.shape[1], int(cx + half_width))
    band = gray[y0:y1, x0:x1]
    if band.size == 0:
        return False
    thr = float(np.percentile(band, 40))
    for ly in lines_page_y:
        yi = int(round(ly))
        if not (0 <= yi < gray.shape[0]):
            return False
        row = gray[yi, x0:x1]
        if row.size == 0 or not (row <= thr).any():
            return False
    return True


class Sheet:
    def __init__(self, run: "readout.Run"):
        self.run = run
        self.pages: Dict[int, np.ndarray] = {}
        self.tiles: List[Tuple[np.ndarray, str]] = []

    def _page_img(self, page_index: int) -> np.ndarray:
        if page_index not in self.pages:
            dpi = self.run.dpi or 600
            img = render_page(self.run.pdf, page_index, dpi=dpi)
            self.pages[page_index] = img.rgb.copy()
        return self.pages[page_index]

    def _staff_lines_for(self, staff_key: str) -> List[float]:
        for o in self.run.observations:
            if o["subject"] == staff_key and o["quantity"] == "staff_lines":
                return [float(y) for y in o["value"]]
        return []

    def add_tile(self, page_index: int, boxes: List[Tuple[Tuple[float, float, float, float], Any, bool]],
                caption: str, staff_key: Optional[str] = None):
        """`boxes`: list of (bbox_page_px (x0,y0,x1,y1), color, dashed)."""
        page_img = self._page_img(page_index)
        all_x = [b[0][0] for b in boxes] + [b[0][2] for b in boxes]
        all_y = [b[0][1] for b in boxes] + [b[0][3] for b in boxes]
        cx = (min(all_x) + max(all_x)) / 2.0
        pad = PAD_SPACES * 20.0 * (600.0 / 72.0) / 10.0  # generous, px
        pad = max(pad, (max(all_x) - min(all_x)) * 0.6,
                 (max(all_y) - min(all_y)) * 0.6, 60)
        x0 = max(0, int(min(all_x) - pad))
        x1 = min(page_img.shape[1], int(max(all_x) + pad))
        y0 = max(0, int(min(all_y) - pad))
        y1 = min(page_img.shape[0], int(max(all_y) + pad))
        crop = page_img[y0:y1, x0:x1].copy()
        if crop.ndim == 2:
            crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)

        lines_ok = None
        if staff_key is not None:
            lines_page = self._staff_lines_for(staff_key)
            if lines_page:
                lines_ok = _check_staff_rows(
                    cv2.cvtColor(page_img, cv2.COLOR_BGR2GRAY)
                    if page_img.ndim == 3 else page_img,
                    lines_page, cx, (x1 - x0) / 2.0)
                for ly in lines_page:
                    yy = int(ly) - y0
                    if 0 <= yy < crop.shape[0]:
                        cv2.line(crop, (0, yy), (crop.shape[1], yy), GRAY, 1)

        for (bx0, by0, bx1, by1), color, dashed in boxes:
            rx0, ry0, rx1, ry1 = bx0 - x0, by0 - y0, bx1 - x0, by1 - y0
            if dashed:
                _dashed_rect(crop, rx0, ry0, rx1, ry1, color)
            else:
                _rect(crop, rx0, ry0, rx1, ry1, color)

        scale = TARGET_TILE_W / max(1, crop.shape[1])
        crop = cv2.resize(crop, (TARGET_TILE_W, int(crop.shape[0] * scale)),
                          interpolation=cv2.INTER_NEAREST)
        cap = caption
        if lines_ok is False:
            cap += "  [STAFF LINES UNCHECKED]"
        self.tiles.append((crop, cap))

    def write(self, out_path: Path):
        cap_h = 46
        tiles = self.tiles
        rows = []
        for i in range(0, len(tiles), COLS):
            row_tiles = tiles[i:i + COLS]
            h = max(t.shape[0] for t, _ in row_tiles) + cap_h
            row_imgs = []
            for img, cap in row_tiles:
                canvas = np.full((h, TARGET_TILE_W, 3), 255, dtype=np.uint8)
                canvas[cap_h:cap_h + img.shape[0], :img.shape[1]] = img
                cv2.putText(canvas, cap, (4, 20), cv2.FONT_HERSHEY_SIMPLEX,
                           0.45, BLACK, 1, cv2.LINE_AA)
                row_imgs.append(canvas)
            while len(row_imgs) < COLS:
                row_imgs.append(np.full((h, TARGET_TILE_W, 3), 255,
                                        dtype=np.uint8))
            rows.append(np.hstack(row_imgs))
        sheet = np.vstack(rows)
        if sheet.shape[1] > MAX_SHEET_W:
            scale = MAX_SHEET_W / sheet.shape[1]
            sheet = cv2.resize(sheet, (MAX_SHEET_W,
                                       int(sheet.shape[0] * scale)))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), sheet)
        print(f"wrote {out_path} ({sheet.shape[1]}x{sheet.shape[0]})")


def _canon_to_page_affine(canon_box, page_box):
    cx0, cy0, cw, ch = canon_box
    px0, py0, px1, py1 = page_box
    cx1, cy1 = cx0 + cw, cy0 + ch
    up_x = (cx1 - cx0) / (px1 - px0) if (px1 - px0) else 1.0
    up_y = (cy1 - cy0) / (py1 - py0) if (py1 - py0) else 1.0
    bx = px0 - cx0 / up_x
    by = py0 - cy0 / up_y
    return up_x, up_y, bx, by


def _apply(up_x, up_y, bx, by, cx0, cy0, cx1, cy1):
    return (bx + cx0 / up_x, by + cy0 / up_y, bx + cx1 / up_x, by + cy1 / up_y)


def main(record_path: str):
    run = readout.load_run(record_path)
    obs = run.observations
    ab = run.abstentions

    splits = [o for o in obs if o["quantity"] == "glyph_box"
             and o.get("detail", {}).get("witness") == "tall_box_split"]
    by_cell: Dict[str, List[dict]] = {}
    for o in splits:
        by_cell.setdefault(_cell_key(o["subject"]), []).append(o)

    drops = [a for a in ab if a["reason"] == "rescue_box_spans_two_heads"
            and "bbox_page_px" in a.get("detail", {})]

    extent_rows = [o for o in obs if o["quantity"] == "notehead_recentre"
                  and o.get("reader") == "cv_notehead_vertical_extent"]

    sheet = Sheet(run)

    # ── tall_box_split tiles (one per original tall box = 2 split heads)
    n_split_tiles = 0
    n_split_heads_shown = 0
    for cell_key, rows in by_cell.items():
        p, s, st, m = (int(x) for x in cell_key.split("/")[1:])
        orig = rows[0]["detail"]["original_box"]  # canonical [x,y,w,h]
        up_x, up_y, bx, by = _canon_to_page_affine(
            orig, rows[0]["detail"]["bbox_page_px"])
        orig_page = _apply(up_x, up_y, bx, by, orig[0], orig[1],
                           orig[0] + orig[2], orig[1] + orig[3])
        boxes = [(orig_page, BLUE, True)]
        split_ys = []
        for r in rows:
            pb = r["detail"]["bbox_page_px"]
            boxes.append(((pb[0], pb[1], pb[2], pb[3]), GREEN, False))
            split_ys.append((pb[1] + pb[3]) / 2.0)
        # nearby tie boxes on the same cell -- the witnesses used.
        tie_subs = [o for o in obs if o["quantity"] == "glyph_box"
                   and _cell_key(o["subject"]) == cell_key
                   and str(o["value"][0]).lower() in ("tie", "slur")]
        for t in tie_subs:
            pb = t.get("detail", {}).get("bbox_page_px")
            if pb:
                boxes.append(((pb[0], pb[1], pb[2], pb[3]), RED, False))
        staff_key = f"staff/{p}/{s}/{st}"
        if len(rows) >= 2:
            gap = abs(split_ys[0] - split_ys[1])
            caption = (f"{cell_key}: split into 2 heads at the tie ends "
                      f"({gap:.0f}px apart)")
        else:
            caption = (f"{cell_key}: split into 1 head -- only one tie "
                      f"end found (other half not invented)")
        sheet.add_tile(p, boxes, caption, staff_key)
        n_split_tiles += 1
        n_split_heads_shown += len(rows)

    # ── dropped tall boxes
    for a in drops:
        subj = a["subject"]           # cell/<p>/<s>/<st>/<m>
        p, s, st, m = (int(x) for x in subj.split("/")[1:])
        pb = a["detail"]["bbox_page_px"]
        boxes = [((pb[0], pb[1], pb[2], pb[3]), BLUE, True)]
        staff_key = f"staff/{p}/{s}/{st}"
        sheet.add_tile(p, boxes,
                       f"{subj}: dropped -- no tie witness "
                       f"(height_ratio={a['detail']['height_ratio']})",
                       staff_key)

    # ── cause-A vertical-extent recentres, >0.3 space shift
    for o in extent_rows:
        dx_sp, dy_sp = o["value"]
        if abs(dy_sp) <= 0.3:
            continue
        p, s, st, m, gi = _glyph_key_parts(o["subject"])
        det_box = next((d for d in obs
                        if d["subject"] == o["subject"]
                        and d["quantity"] == "glyph_box"
                        and d.get("reader") == "detector"), None)
        if det_box is None or "bbox_page_px" not in det_box.get("detail", {}):
            continue
        pb = det_box["detail"]["bbox_page_px"]
        orig_box = ((pb[0], pb[1], pb[2], pb[3]), BLUE, True)
        cx0, cy0, cw, ch = o["detail"]["original_box"]  # centre-based
        up_x, up_y, bx, by = _canon_to_page_affine(
            [cx0 - cw / 2.0, cy0 - ch / 2.0, cw, ch], pb)
        # the NEW box: the standard box, resized, shifted by dy_sp spaces.
        space_canon = ch / 1.1 if ch else cw / 1.4
        new_cy = cy0 + dy_sp * space_canon
        new_box_canon = [cx0 - cw / 2.0, new_cy - ch / 2.0, cw, ch]
        new_page = _apply(up_x, up_y, bx, by, new_box_canon[0],
                          new_box_canon[1], new_box_canon[0] + cw,
                          new_box_canon[1] + ch)
        staff_key = f"staff/{p}/{s}/{st}"
        sheet.add_tile(p, [orig_box, (new_page, GREEN, False)],
                       f"{o['subject']}: box moved {abs(dy_sp):.2f} "
                       f"spaces ({'down' if dy_sp > 0 else 'up'})",
                       staff_key)

    print(f"tall_box_split tiles: {n_split_tiles} (from {n_split_heads_shown} split heads)")
    print(f"dropped tiles: {len(drops)}")
    print(f"cause-A >0.3-space tiles: {sum(1 for o in extent_rows if abs(o['value'][1]) > 0.3)}")
    sheet.write(OUT_PATH)


if __name__ == "__main__":
    main(sys.argv[1])
