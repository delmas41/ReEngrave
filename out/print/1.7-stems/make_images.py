"""ROADMAP 1.7 (stems): the commonest ways a stem is lost, as phone-sized images (1000 px wide, stacked).

NOT product code: a diagnostic image maker. Run from the repo root:

    python3 out/print/1.7-stems/make_images.py --page data/hand-truth/pages/imslp317803/0.json \
        --record <the acceptance_quick record> --runs <a record gathered with OMR_VERTICAL_RUNS> --pdf <the score pdf>

Every number drawn on an image is read off the scorer's own report (``tools.omr.hand_truth.score``), nothing is
re-derived here. Each image is one cause; the TOP is the print with the head bracketed in red, the BOTTOM is the
same window with Sean's stem box (green), every stem the CV reader found (blue), the strokes the stem finder
refused (orange, with the filter that refused them) and "NO STEM FOUND" written where none was.

FRAME CONTROL, per image (it can fail): the share of the head's box that is ink, against the same box moved two
staff spaces in four directions. A frame that is wrong reads about equal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "1.7-far-notes-review"))
sys.path.insert(0, str(HERE.parents[2]))

import phone_tile as P  # noqa: E402  (banner, fonts, crop_scaled: the committed phone-tile helpers)

from tools.omr.hand_truth import score as S  # noqa: E402
from tools.omr.hand_truth import score_stems as SS  # noqa: E402
from tools.omr.hand_truth import store  # noqa: E402
from tools.omr.hand_truth.session import _render  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402
from tools.omr.staged import record_io  # noqa: E402

WIN_W_SP, WIN_H_SP = 14.0, 8.0
LEGEND = [("red = the head   ", P.RED), ("green = Sean's stem   ", P.GREEN), ("blue = stem we found   ", P.BLUE),
          ("orange = refused", P.ORANGE)]

#: One entry per image: the truth stem (or cell) the window is centred on, the one-line cause, the facts line.
SPECS = [
    dict(n=1, anchor="b4087", title="Cause: run too wide",
         note="Two heads a third apart touch, and the stem finder sees ONE run about a space wide."),
    dict(n=2, anchor="b4119", title="Run too wide, with a beam",
         note="The same refusal. A beam box and a slur box of Sean's also touch this stem (the table in FINDINGS 8.4 "
              "holds the rates)."),
    dict(n=3, anchor="b4310", title="Run too wide, low staff",
         note="The same fusing on staff 0.11 (it reads an alto clef): the loss is not confined to the top staves."),
    dict(n=4, anchor="b4064", title="Cause: pair rule",
         note="One head. A 2.4-space stroke 0.5 sp to its left, which lies on the accidental Sean boxed beside "
              "the head, pairs with the real stem under the 'accidental pair' rule, and the pair is dropped."),
    dict(n=5, anchor="b4083", title="Pair rule, on a chord",
         note="A real stem found and then dropped as one half of a pair; its neighbour is lost to the too-wide run."),
    dict(n=6, anchor="b4177", title="Wrong stem: a flag's curve",
         note="The real stem was refused; the two heads took the rising curve of the flag, which stands against their "
              "right edge and lies on Sean's flag box, as their stem."),
    dict(n=7, anchor="q709", title="Found, not attached",
         note="The stem is found and stands against the head box, but the attach rule has no tolerance: no_stem."),
    dict(n=8, anchor="CELL:s0-st3-m0", title="Invented: not stems",
         note="65 of the 68 'stems' that are not Sean's lie on a clef, key signature, digit, accidental, flag or rest."),
]


def ink_frame(binary: np.ndarray, rect, sp: float):
    """Share of the head box that is ink, vs the box moved 2 spaces up/down/left/right."""
    def share(r):
        x0, y0, x1, y1 = (int(round(v)) for v in r)
        h, w = binary.shape
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0:
            return 0.0
        return float((binary[y0:y1, x0:x1] < 128).mean())
    here = share(rect)
    moved = [share((rect[0] + dx * sp, rect[1] + dy * sp, rect[2] + dx * sp, rect[3] + dy * sp))
             for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2))]
    return here, float(np.mean(moved))


PLACED = []


def label(draw, xy, text, color, size=34, anchor_right=False):
    """A boxed label; slides down until it overlaps no label already placed on this image."""
    f = P.font(size)
    w = P.text_w(draw, text, f)
    x, y = xy
    if anchor_right:
        x -= w
    for _ in range(30):
        box = (x - 5, y - 3, x + w + 5, y + size + 5)
        if not any(box[0] < o[2] and box[2] > o[0] and box[1] < o[3] and box[3] > o[1] for o in PLACED):
            break
        y += size + 12
    PLACED.append(box)
    draw.rectangle(box, fill=(255, 255, 255), outline=color, width=3)
    draw.text((x, y), text, font=f, fill=color)


def fitted_banner(number, title, subtitle):
    """``phone_tile.banner`` with the title shrunk until it fits beside the number."""
    im = P.banner(P.WIDTH, number, "", LEGEND, subtitle=subtitle)
    d = ImageDraw.Draw(im)
    d.rectangle([200, 8, P.WIDTH, 92], fill=(255, 255, 255))
    for size in (58, 54, 50, 46, 42, 38):
        f = P.font(size)
        if P.text_w(d, title, f) <= P.WIDTH - 214 - 10:
            break
    d.text((214, 22), title, font=f, fill=P.INK)
    return im


ATTACH = {"right": "attached its own stem", "abstained_stem_not_found": "no stem attached (none was found)",
          "abstained_stem_was_found": "no stem attached although the stem was found",
          "wrong_invented_stem": "attached a stroke that is not Sean's stem", "wrong_other_stem": "attached another stem",
          "head_missed": "head not found"}
STEPS = {1: "a second", 2: "a third", 3: "a fourth", 4: "a fifth"}


def dashed(draw, box, color, width=4, dash=14):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        n = max(abs(bx - ax), abs(by - ay))
        k = 0
        while k < n:
            k2 = min(n, k + dash)
            sx, sy = ax + (bx - ax) * k / n, ay + (by - ay) * k / n
            ex, ey = ax + (bx - ax) * k2 / n, ay + (by - ay) * k2 / n
            draw.line([sx, sy, ex, ey], fill=color, width=width)
            k += 2 * dash


def corner_bracket(draw, box, color, t=6, n=26):
    x0, y0, x1, y1 = box
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.line([x, y, x + sx * n, y], fill=color, width=t)
        draw.line([x, y, x, y + sy * n], fill=color, width=t)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True, type=Path)
    ap.add_argument("--record", required=True, type=Path)
    ap.add_argument("--runs", required=True, type=Path)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    page = store.load(a.page)
    run = RO.load_run(str(a.record))
    other = record_io.load_record(str(a.runs))
    runs = SS.read_vertical_runs(other, page.pdf_page_index)
    img = _render(a.pdf, page.pdf_page_index, page.dpi)
    ink = SS.InkColumns(img.binary < 128)
    rep = S.score(page, run, derive=True, stem_cause_inputs={"runs": runs, "ink": ink})
    st = rep["_stems"]
    m, cv = st["_match"], st["_cv"]
    items = {it.id: it for it in rep["_items"]}
    heads_rows = {r["truth_id"]: r for r in st["heads"]["_rows"]}
    miss_facts = {r["id"]: r for r in st["cv_stem"]["missed_facts"]["missed"]}
    bands = {b.cell_id: b for b in S.staff_bands(page)}
    all_cv = SS.read_cv_stems(run, page.pdf_page_index).stems       # every Q.STEM row on the page, scored cell or not
    truth_stems = [it for it in rep["_items"] if it.family == "stem"]
    truth_heads = [it for it in rep["_items"] if it.family == "notehead"]
    sc_to_t = {t.idx: t for t in m.truth}
    manifest = []
    table = ["MEASURED FACTS behind each stem image of ROADMAP 1.7 (stems). No conclusion is drawn here.", ""]
    for spec in SPECS:
        n = spec["n"]
        anchor_stem = None
        if spec["anchor"].startswith("CELL:"):
            cell = next(c for c in page.cells if c.id == spec["anchor"][5:])
            band = bands[cell.id]
            sp = band.space
            cx, cy = cell.rect[0] + 7.0 * sp, S._cy((0, band.lines[0], 0, band.lines[-1]))
            focus_heads = []
        else:
            anchor_stem = items[spec["anchor"]]
            sp = bands[anchor_stem.cell_id].space
            cx, cy = S._cx(anchor_stem.rect), S._cy(anchor_stem.rect)
            focus_heads = SS.head_has_stem((0, 0, 0, 0), [], sp) or [h for h in truth_heads
                                                                      if SS._box_gap(h.rect, anchor_stem.rect) <= SS.HEAD_STEM_TOUCH_SPACES * sp]
        win_h = max(WIN_H_SP, (SS._y_len(anchor_stem.rect) / sp + 2.0) if anchor_stem is not None else 0.0)
        box = (cx - WIN_W_SP / 2 * sp, cy - win_h / 2 * sp, cx + WIN_W_SP / 2 * sp, cy + win_h / 2 * sp)
        crop, scale, (ox, oy) = P.crop_scaled(img.rgb, box, width=P.WIDTH)

        def to_px(r):
            return ((r[0] - ox) * scale, (r[1] - oy) * scale, (r[2] - ox) * scale, (r[3] - oy) * scale)

        def inside(r):
            return r[2] > box[0] and r[0] < box[2] and r[3] > box[1] and r[1] < box[3]

        PLACED.clear()
        top = crop.copy()
        td = ImageDraw.Draw(top)
        for h in focus_heads:
            corner_bracket(td, to_px(h.rect), P.RED)
        bot = crop.copy()
        bd = ImageDraw.Draw(bot)
        refused = [r for r in runs if inside(r["rect"]) and not r["outcome"].startswith("accepted")
                   and any(SS.runs_at(t.rect, sp, [r]) for t in truth_stems if inside(t.rect))
                   and not r["outcome"].startswith("too TALL")]
        for r in refused:
            dashed(bd, to_px(r["rect"]), P.ORANGE)
        for c in all_cv:
            if inside(c.rect):
                bd.rectangle(to_px(c.rect), outline=P.BLUE, width=4)
        for t in truth_stems:
            if inside(t.rect):
                bd.rectangle(to_px(t.rect), outline=P.GREEN, width=3)
        facts = []
        found_any = False
        for t in truth_stems:
            if not inside(t.rect):
                continue
            tx0, ty0, tx1, ty1 = to_px(t.rect)
            if t.idx in m.found:
                found_any = found_any or t is anchor_stem
                continue
            word = miss_facts.get(t.id, {}).get("run_refused_for")
            side_left = (tx0 + tx1) / 2 > 0.6 * crop.width
            label(bd, (tx0 - 8 if side_left else tx1 + 8, (ty0 + ty1) / 2 - 20), "NO STEM FOUND", P.RED, 30,
                  anchor_right=side_left)
            if word and t is anchor_stem:
                label(bd, (min(max(tx0 - 120, 8), crop.width - 330), ty1 + 10), "refused: " + " + ".join(word),
                      P.ORANGE, 30)
        if anchor_stem is not None:
            fr = miss_facts.get(anchor_stem.id) or {}
            facts.append(f"Sean's stem is {fr.get('length_spaces', round(SS._y_len(anchor_stem.rect) / sp, 2))} spaces tall "
                         f"with {fr.get('heads_on_it', len(focus_heads))} head(s) on it"
                         + (f", the closest two {STEPS.get(fr.get('closest_heads_apart_in_steps'), 'far')} apart"
                            if fr.get("closest_heads_apart_in_steps") else ""))
            for r in fr.get("vertical_runs_at_its_column", []):
                facts.append(f"the stem finder's run here was refused as {r['outcome'].split(' (')[0].upper()}: "
                             f"{r['width_spaces']} wide x {r['height_spaces']} tall (staff spaces; it takes at most 0.6 wide)")
            if "ink_longest_unbroken_run_spaces" in fr:
                facts.append(f"the ink along Sean's stem is unbroken for {fr['ink_longest_unbroken_run_spaces']} spaces "
                             f"(the finder needs 1.6): the stem is on the page")
            for pw in fr.get("paired_with", []):
                facts.append(f"its pair partner: a {pw['height_spaces']}-space stroke {abs(pw['centre_offset_spaces'])} spaces "
                             f"to the {'right' if pw['centre_offset_spaces'] > 0 else 'left'}; "
                             f"{'one of Sean' + chr(39) + 's stems' if pw['is_a_truth_stem'] else 'not one of Sean' + chr(39) + 's stems'}"
                             f"; it lies on: {pw['lies_on']}")
            for h in focus_heads:
                row = heads_rows.get(h.id, {})
                if row.get("attach") != "right":
                    corner_bracket(bd, to_px(h.rect), P.RED, t=5, n=22)
                    label(bd, (to_px(h.rect)[2] + 10, to_px(h.rect)[1] - 4),
                          "no stem attached" if str(row.get("attach", "")).startswith("abstained")
                          else "wrong stroke attached", P.RED, 26)
                if "gap_to_found_stem_spaces" in row:
                    facts.append(f"head {h.id}: the stem we found stands {row['gap_to_found_stem_spaces']} spaces from the "
                                 "head box; the attach rule takes only boxes that overlap")
                dirs = {"right": "direction right", "abstained": "direction not read", "wrong": "direction WRONG",
                        "no_truth": "direction read"}
                facts.append(f"head {h.id}: {ATTACH.get(row.get('attach'), row.get('attach'))}; "
                             f"{dirs.get(row.get('direction'), row.get('direction'))}")
            hh = [(ink_frame(img.binary, h.rect, sp)) for h in focus_heads]
            frame = (f"frame control: ink inside the bracket {np.mean([a for a, _ in hh]):.2f} vs moved "
                     f"{np.mean([b for _, b in hh]):.2f}" if hh else "")
        else:
            inv_rows = {cv_c.row_id for cv_c in cv.stems if cv_c.idx in set(m.invented)}
            win = [c for c in all_cv if inside(c.rect)]
            not_sean = [c for c in win if c.row_id in inv_rows]
            facts.append(f"{len(not_sean)} of the {len(win)} stems we found in this window are not Sean's: "
                         "they stand on the clef and the key signature, where he drew no stem")
            frame = ""
        f_h = P.font(30, False)
        lines = [spec["note"]] + facts + ([frame] if frame else [])
        # wrap
        wrapped = []
        probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        for ln in lines:
            words, cur = ln.split(), ""
            for w in words:
                if P.text_w(probe, (cur + " " + w).strip(), f_h) <= P.WIDTH - 28:
                    cur = (cur + " " + w).strip()
                else:
                    wrapped.append(cur)
                    cur = w
            wrapped.append(cur)
        sub = f"Brahms 1 (Breitkopf), pdf 0, " + (f"cell {anchor_stem.cell_id}" if anchor_stem else spec["anchor"][5:])
        banner = fitted_banner(n, spec["title"], sub)
        strip_h = 46
        foot_h = 12 + 38 * len(wrapped)
        total_h = banner.height + strip_h + top.height + strip_h + bot.height + foot_h
        out = Image.new("RGB", (P.WIDTH, total_h), (255, 255, 255))
        out.paste(banner, (0, 0))
        y = banner.height
        d = ImageDraw.Draw(out)
        for text, im in (("THE PRINT (red brackets mark the head)", top),
                         ("WHAT SEAN BOXED AND WHAT WE FOUND", bot)):
            d.rectangle([0, y, P.WIDTH, y + strip_h], fill=(225, 225, 230))
            d.text((12, y + 6), text, font=P.font(32), fill=P.INK)
            y += strip_h
            out.paste(im, (0, y))
            y += im.height
        d.rectangle([0, y, P.WIDTH, total_h], fill=(255, 255, 255))
        yy = y + 8
        for ln in wrapped:
            d.text((14, yy), ln, font=f_h, fill=P.INK)
            yy += 38
        path = a.out / f"stem_{n:02d}.png"
        out.save(path)
        manifest.append({"n": n, "anchor": spec["anchor"], "cause": spec["title"], "file": path.name,
                         "window_page_px": [round(v) for v in box]})
        table.append(f"=== image {n}  {spec['title']}  ({spec['anchor']})")
        table.extend("    " + ln for ln in [spec["note"]] + facts + ([frame] if frame else []))
        table.append("")
        print("wrote", path)
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    (a.out / "table.txt").write_text("\n".join(table) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
