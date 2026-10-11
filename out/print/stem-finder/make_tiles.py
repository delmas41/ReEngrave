"""ROADMAP 2.84 (stem finder): BLIND review tiles for Sean. NOT product code.

Nothing of ours is drawn: only the print, a big number, one plain question and red corner brackets on the SUBJECT (the
line or the note the question is about). Which strokes to ask about is decided from the scorer's own lists
(`stemlist.json`, written by the arm's record through `tools.omr.hand_truth.score`): every stroke the finder now
reads that Sean's page has no stem box under (so the print, not his boxes, must say), and every note whose standing
got WORSE than the base.

    python3 out/print/stem-finder/make_tiles.py --list stemlist.json --pdf <score.pdf> --page data/hand-truth/pages/imslp317803/0.json

Frame control, per tile (it can fail): share of the bracket that is ink, against the same box moved two staff spaces
in four directions; a tile whose bracket is not on ink is refused, not drawn.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "1.7-far-notes-review"))
sys.path.insert(0, str(HERE.parents[2]))

import phone_tile as P  # noqa: E402

from tools.omr.hand_truth import store  # noqa: E402
from tools.omr.hand_truth.session import _render  # noqa: E402

SPACE_PX = 50.0            # ~ one staff space at 600 dpi on this plate (only sizes the window)
WIN = (11.0, 6.5)          # window half-size in spaces


def ink_share(binary: np.ndarray, rect) -> float:
    x0, y0, x1, y1 = (int(round(v)) for v in rect)
    box = binary[max(0, y0):y1, max(0, x0):x1]
    return float(box.mean()) if box.size else 0.0


def frame_control(binary, rect, thin=False):
    """Ink share inside the box, against the same box moved. A thin line is moved just off itself (its width + 6 px,
    either side): two spaces away lands on the NEXT stem of a beamed group and reads as ink."""
    here = ink_share(binary, rect)
    w = rect[2] - rect[0]
    step = (w + 6.0) if thin else 2 * SPACE_PX
    moved = [ink_share(binary, (rect[0] + dx * step, rect[1] + dy * step, rect[2] + dx * step, rect[3] + dy * step))
             for dx, dy in (((1, 0), (-1, 0)) if thin else ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    return here, max(moved)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", type=Path, required=True)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--page", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--head-ids", default="", help="comma list of Sean's head ids to ask 'one stem or two'")
    a = ap.parse_args()
    page = store.load(a.page)
    img = _render(str(a.pdf), page.pdf_page_index, page.dpi)
    binary = img.binary < 128 if img.binary.dtype != bool else img.binary
    pix = (np.where(binary, 0, 255)).astype(np.uint8)
    lst = json.loads(a.list.read_text())
    subjects = []
    for inv in lst["invented"]:
        if inv["why"].startswith("touches a head") or inv["why"] == "no truth box under it":
            subjects.append(("line", inv["rect"], "Is the red line a stem?"))
    from tools.omr.hand_truth import score as S
    items = {t.id: t for t in S.truth_items(page)}
    for hid in [h for h in a.head_ids.split(",") if h]:
        it = items.get(hid)
        if it is not None:
            subjects.append(("head", list(it.rect), "1 stem or 2 stems?"))
    manifest, n_total = [], len(subjects)
    for n, (kind, rect, question) in enumerate(subjects, 1):
        x0, y0, x1, y1 = rect
        pad = 6
        br = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        here, moved = frame_control(binary, (x0, y0, x1, y1), thin=(kind == 'line'))
        if kind == 'line' and here < moved + 0.2:
            print('FRAME CONTROL FAILED for', rect, round(here, 3), round(moved, 3))
            return 3
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        win = (cx - WIN[0] * SPACE_PX, cy - WIN[1] * SPACE_PX, cx + WIN[0] * SPACE_PX, cy + WIN[1] * SPACE_PX)
        body, scale, (ox, oy) = P.crop_scaled(pix, win, width=1000)
        d = P.ImageDraw.Draw(body)
        P.corner_brackets(d, ((br[0] - ox) * scale, (br[1] - oy) * scale, (br[2] - ox) * scale, (br[3] - oy) * scale), thick=5, arm=24)
        top = P.banner(1000, n, question, [("red corners = what to look at", P.RED)], subtitle=f"Brahms 1, tile {n} of {n_total}")
        tile = P.compose(top, body)
        name = f"tile_{n:02d}.png"
        P.save_small(tile, a.out / name)
        manifest.append({"n": n, "file": name, "kind": kind, "page_box_600dpi": [round(v, 1) for v in rect],
                         "question": question, "frame_control_ink_here": round(here, 3), "frame_control_ink_moved_max": round(moved, 3)})
        print(name, kind, "frame", round(here, 3), "vs moved", round(moved, 3))
    (a.out / "manifest.json").write_text(json.dumps({"dpi": page.dpi, "note": "blind: nothing of ours is drawn", "tiles": manifest}, indent=1) + "\n")
    tmpl = {"judge": "sean", "question": "one answer per tile", "answers": {str(m["n"]): "" for m in manifest}}
    (a.out / "answers.template.json").write_text(json.dumps(tmpl, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
