"""The four possible slips in Sean's labels on Brahms 317803 page 0, as phone-sized singles (Sean 2026-10-10:
"show me the four possible slips").

    python3 out/print/1.7-label-slips/make_slips.py --page <page.json> --record <record.json> --pdf <score.pdf>

Each image shows Sean's box with its class written plainly, and the question at the bottom. Sean's page is only
read. Not product code. The dashed outline on slip 3 stands where the missing 8 should be, estimated from the staves whose
6/8 are boxed (no box of his, and none of our detector's, exists to draw).
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "out" / "print" / "1.7-far-notes-review"))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import phone_tile as P  # noqa: E402
from tools.omr.hand_truth import score as S  # noqa: E402
from tools.omr.hand_truth import store  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

GREEN_D = (0, 110, 30)


def dashed(d, rect, color, width=8, dash=22, gap=14):
    x0, y0, x1, y1 = rect
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        L = max(abs(bx - ax), abs(by - ay))
        n = int(L // (dash + gap)) + 1
        for i in range(n):
            s0, s1 = i * (dash + gap), min(L, i * (dash + gap) + dash)
            d.line([ax + (bx - ax) * s0 / L, ay + (by - ay) * s0 / L, ax + (bx - ax) * s1 / L,
                    ay + (by - ay) * s1 / L], fill=color, width=width)


def question_panel(width, lines, size=44):
    f = P.font(size)
    d0 = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    wrapped = []
    for ln in lines:
        wrapped += textwrap.wrap(ln, width=max(10, int((width - 40) / (size * 0.52)))) or [""]
    h = 30 + len(wrapped) * (size + 12) + 20
    im = Image.new("RGB", (width, h), (255, 244, 190))
    d = ImageDraw.Draw(im)
    d.line([0, 0, width, 0], fill=(190, 160, 0), width=6)
    y = 24
    for ln in wrapped:
        d.text((20, y), ln, font=f, fill=P.INK)
        y += size + 12
    return im


def tag(d, x, y, text, color, size=34, fill=(255, 255, 255)):
    f = P.font(size)
    w = int(d.textlength(text, font=f)) + 20
    d.rectangle([x, y, x + w, y + size + 14], fill=fill, outline=color, width=4)
    d.text((x + 10, y + 5), text, font=f, fill=color)


def window(img, cx0, cy0, cx1, cy1):
    return P.crop_scaled(img, (cx0, cy0, cx1, cy1))


def draw_box(d, rect, x0, y0, scale, color, width, label=None, label_pos="above", size=30):
    r = [(rect[0] - x0) * scale, (rect[1] - y0) * scale, (rect[2] - x0) * scale, (rect[3] - y0) * scale]
    d.rectangle(r, outline=color, width=width)
    if label:
        ty = r[1] - size - 22 if label_pos == "above" else r[3] + 8
        tag(d, max(4, r[0] - 6), ty, label, color, size)
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True, type=Path)
    ap.add_argument("--record", required=True, type=Path)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    page = store.load(a.page)
    run = RO.load_run(str(a.record))
    img = np.asarray(render_page(str(a.pdf), page.pdf_page_index, dpi=page.dpi).rgb).copy()
    bands = S.staff_bands(page)
    sp = float(np.median([b.space for b in bands]))
    boxes = page.boxes

    def cell_boxes(cell_id):
        c = page.cell(cell_id)
        return [b for b in boxes if c.rect[0] <= S._cx(b.rect) < c.rect[2] and c.rect[1] <= S._cy(b.rect) < c.rect[3]]

    def band(cell_id):
        return next(b for b in bands if b.cell_id == cell_id)

    manifest = []

    def finish(n, title, legend, body, question, meta):
        title, _, sub = title.partition("|")
        top = P.banner(body.width, n, title.strip(), legend, sub.strip())
        im = P.compose(top, body, question_panel(body.width, question))
        fn = f"slip_{n}.png"
        P.save_small(im, a.out / fn)
        manifest.append({"slip": n, "file": fn, **meta})

    GL = [("green = Sean's box, its class written beside it", GREEN_D)]

    # 1 ----------------------------------------------------------------- the third key-signature flat
    cid = "s0-st3-m0"
    bd = band(cid)
    here = cell_boxes(cid)
    subj = next(b for b in here if b.cls == "accidentalFlat" and S._cx(b.rect) < page.cell(cid).rect[0] + 500)
    ctx = [b for b in here if b.cls in ("clefF", "keyFlat", "timeSig6", "timeSig8", "accidentalFlat")
           and S._cx(b.rect) < page.cell(cid).rect[0] + 500]
    X0 = min(b.rect[0] for b in ctx) - 0.8 * sp
    X1 = max(b.rect[2] for b in ctx) + 0.8 * sp
    Y0, Y1 = bd.lines[0] - 2.6 * sp, bd.lines[-1] + 2.6 * sp
    body, scale, (x0, y0) = window(img, X0, Y0, X1, Y1)
    d = ImageDraw.Draw(body)
    for b in ctx:
        if b is not subj:
            draw_box(d, b.rect, x0, y0, scale, GREEN_D, 4, b.cls, "above", 24)
    r = draw_box(d, subj.rect, x0, y0, scale, GREEN_D, 11)
    tag(d, 10, body.height - 70, f"SEAN'S BOX (thick): {subj.cls}", GREEN_D, 38, (225, 255, 230))
    finish(1, "Slip 1 of 4 | Staff 4, Bassoon, bar 1",
           GL, body, ["The third flat after the clef is boxed as accidentalFlat, an ordinary flat.",
                      "Is it a flat of the KEY SIGNATURE (class keyFlat), or an ordinary flat?"],
           {"cell": cid, "box": subj.id, "class": subj.cls, "origin": subj.origin,
            "question": "key-signature flat or an ordinary flat?",
            "effect": "the key reads -2 from the boxes; the record reads -3"})

    # 2 ----------------------------------------------------------------- the 8 of a 9/8 boxed as a whole note
    cid = "s0-st5-m7"
    bd = band(cid)
    here = cell_boxes(cid)
    subj = next(b for b in here if b.id == "q713")
    nine = [b for b in here if b.cls == "timeSig9"]
    ctx = nine + [subj]
    X0 = min(b.rect[0] for b in ctx) - 4.5 * sp
    X1 = max(b.rect[2] for b in ctx) + 4.5 * sp
    Y0, Y1 = bd.lines[0] - 1.4 * sp, bd.lines[-1] + 1.4 * sp
    body, scale, (x0, y0) = window(img, X0, Y0, X1, Y1)
    d = ImageDraw.Draw(body)
    for b in nine:
        draw_box(d, b.rect, x0, y0, scale, GREEN_D, 4, b.cls, "above", 28)
    draw_box(d, subj.rect, x0, y0, scale, GREEN_D, 11)
    tag(d, 10, body.height - 70, f"SEAN'S BOX (thick): {subj.cls}", GREEN_D, 36, (225, 255, 230))
    finish(2, "Slip 2 of 4 | Staff 6, end of the system",
           GL, body, ["The lower digit under the 9 is boxed as noteheadWholeInSpace (a whole note).",
                      "Is it the 8 of a 9/8, a time-signature digit (timeSig8)?"],
           {"cell": cid, "box": subj.id, "class": subj.cls, "origin": subj.origin,
            "question": "the 8 of a 9/8, or a whole note?"})

    # 3 ----------------------------------------------------------------- the 8 of a 6/8 with no box
    cid = "s0-st4-m0"
    bd = band(cid)
    c = page.cell(cid)
    here = cell_boxes(cid)
    six = next(b for b in here if b.cls == "timeSig6")
    # Neither Sean nor our detector has a box on this digit. Where it stands is estimated from the 8-under-6 offsets of
    # the staves whose 6/8 ARE boxed: the median of (8 box - 6 box), corner by corner, applied to this staff's 6.
    offs = []
    for k in range(14):
        m0 = f"s0-st{k}-m0"
        cb = cell_boxes(m0)
        six_k = [b for b in cb if b.cls == "timeSig6"]
        eight_k = [b for b in cb if b.cls == "timeSig8"]
        if six_k and eight_k and k != 4:
            offs.append([e - s_ for e, s_ in zip(eight_k[0].rect, six_k[0].rect)])
    off = np.median(np.array(offs), axis=0)
    eight_rect = tuple(float(v) for v in (np.array(six.rect) + off))
    ctx = [b for b in here if b.cls in ("clefF", "keyFlat") and S._cx(b.rect) < c.rect[0] + 500] + [six]
    X0 = min(b.rect[0] for b in ctx) - 0.8 * sp
    X1 = six.rect[2] + 2.6 * sp
    Y0, Y1 = bd.lines[0] - 1.8 * sp, bd.lines[-1] + 1.8 * sp
    body, scale, (x0, y0) = window(img, X0, Y0, X1, Y1)
    d = ImageDraw.Draw(body)
    for b in ctx:
        draw_box(d, b.rect, x0, y0, scale, GREEN_D, 4, b.cls, "above", 24)
    dr = [(eight_rect[0] - x0) * scale - 8, (eight_rect[1] - y0) * scale - 8,
          (eight_rect[2] - x0) * scale + 8, (eight_rect[3] - y0) * scale + 8]
    dashed(d, dr, (200, 90, 0), 8)
    tag(d, 10, body.height - 120, "dashed = NO BOX of Sean's here", (200, 90, 0), 36, (255, 240, 220))
    tag(d, 10, body.height - 66, "(estimated from the other staves' 6/8)", (200, 90, 0), 28, (255, 240, 220))
    finish(3, "Slip 3 of 4 | Staff 5, Contrabassoon, bar 1",
           GL, body, ["The 6 is boxed (timeSig6). The digit under it, the 8 of 6/8, has no box.",
                      "Is it a time-signature 8 that still needs a box?"],
           {"cell": cid, "box": None, "class": None, "boxed_neighbour": six.id,
            "unboxed_digit_page_rect_estimated": [round(v, 1) for v in eight_rect],
            "estimate": f"median (8 box - 6 box) over {len(offs)} staves whose 6/8 are boxed; neither Sean nor our detector "
                        "has a box on this digit",
            "question": "the 8 of a 6/8 with no box: does it need one?"})

    # 4 ----------------------------------------------------------------- two far heads with no ledger-line box
    cid = "s0-st0-m6"
    bd = band(cid)
    heads = [b for b in boxes if b.id in ("q133", "q136")]
    assert len(heads) == 2
    ledgers = [b for b in boxes if S.family(b.cls) == "ledger_line"]
    hc = sum(S._cx(b.rect) for b in heads) / 2
    X0, X1 = hc - 5.5 * sp, hc + 5.5 * sp
    Y0, Y1 = min(b.rect[1] for b in heads) - 1.6 * sp, bd.lines[-1] + 1.0 * sp
    body, scale, (x0, y0) = window(img, X0, Y0, X1, Y1)
    d = ImageDraw.Draw(body)
    thick = max(8, int(round(2.9 * scale)))
    P.staff_lines(d, [(y - y0) * scale for y in bd.lines], body.width, P.ORANGE, thick)
    P.staff_label(d, body.width - 235, int((bd.lines[0] - y0) * scale) - 14, "STAFF 1", "Flute", P.ORANGE)
    for b in ledgers:
        if b.rect[2] > X0 and b.rect[0] < X1 and b.rect[3] > Y0 and b.rect[1] < Y1:
            draw_box(d, b.rect, x0, y0, scale, P.BLUE, 5)
    for b in heads:
        draw_box(d, b.rect, x0, y0, scale, GREEN_D, 11)
    classes = sorted({b.cls for b in heads})
    tag(d, 10, 22, "SEAN'S 2 BOXES (thick): " + " / ".join(classes), GREEN_D, 30, (225, 255, 230))
    tag(d, 10, 22 + 56, "blue = his ledger-line boxes", P.BLUE, 30)
    finish(4, "Slip 4 of 4 | Staff 1, Flute, bar 7",
           [("green = Sean's box, class beside it; orange = Staff 1 (Flute); blue = his ledger-line boxes", GREEN_D)],
           body,
           ["Two heads far above the staff have no ledger-line box under them.",
            "Are there ledger lines under them (box them), and do they belong to this staff?"],
           {"cell": cid, "boxes": [b.id for b in heads], "classes": [b.cls for b in heads],
            "question": "ledger lines under these two far heads? and which staff?"})

    (a.out / "manifest.json").write_text(json.dumps({
        "what": "The four possible slips in Sean's labels, Brahms 317803 page 0 (read, never written). Staff numbers count "
                "from the top of the page (1 = top).", "truth_page": f"{page.edition}:{page.pdf_page_index}",
        "slips": manifest}, indent=1) + "\n")
    print(json.dumps([m["file"] for m in manifest]))


if __name__ == "__main__":
    main()
