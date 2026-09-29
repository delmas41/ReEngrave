"""ROADMAP 2.18c -- print crops for Sean: stem-tip flag ink read where the
detector never boxed a flag.

Reads the saved p1 record ONCE (`record_io.load_record`), re-decides it on
this tree (`review.rerun`), and for each subject recomputes -- through
`adjudicate_duration`'s own helpers -- the head's own stem, its side, and
the matching `Q.STEM_TIP_INK` reading. Style after
`benchmarks/omr-missing-notes-2026-09/probe/crop_2_18b.py`: the FILED
staff a shaded labelled band over its own `Q.STAFF_LINES`, the head
bracketed thick red, a staff-space ruler down the left.

  GREEN box    the head's own read stem
  YELLOW box   the tested tip-ink window (the matching end only)
  ORANGE box   a blocker inside that window (why it abstained, if it did)

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL: the filed staff's own lines must be
darker than a half-space off them on the render, or the crop is REFUSED.

    python3 benchmarks/omr-missing-notes-2026-09/probe/crop_flag_2_18c.py \\
        <record.json> <subjects.json>

`subjects.json` is a list of `[glyph_key, why]` pairs (see
`price_flag_2_18c.py`'s own output, or pass a hand-picked list).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

OUT_DIR = HERE.parent / "out" / "print"
DPI = 600


def _frame_ok(arr, line_ys, spacing, *, margin=8.0):
    a = arr if arr.ndim == 2 else arr.mean(axis=2)
    h, w = a.shape
    x0, x1 = int(w * 0.15), int(w * 0.85)
    on, off = [], []
    half = max(1, int(round(spacing / 2.0)))
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(a[y, x0:x1].mean())
        off.append((a[y - half, x0:x1].mean() + a[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    c = float(sum(off) / len(off) - sum(on) / len(on))
    return c >= margin, c


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    from tools.omr.staged import adjudicate as A
    from tools.omr.staged import adjudicators          # noqa: F401
    from tools.omr.staged import gather as G
    from tools.omr.staged.adjudicators import rhythm as RH
    from tools.omr.staged.record import Kind, Q, Scope, Subject
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    rec_path, subjects_path = sys.argv[1:3]
    doc = load_record(rec_path)
    rec = doc["record"]
    subjects = json.loads(Path(subjects_path).read_text())
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    spec = A.REGISTRY[Q.DURATION]
    pdf = doc["provenance"]["settings"]["args"]["pdf"]

    by_cell, lines_of, spacing_of = {}, {}, {}
    for o in rec["observations"]:
        sub = Subject.from_key(o["subject"])
        if o["quantity"] == Q.STAFF_LINES and sub.kind is Kind.STAFF:
            lines_of[o["subject"]] = [float(y) for y in o["value"]]
        elif o["quantity"] == Q.STAFF_SPACING and sub.kind is Kind.STAFF:
            spacing_of[o["subject"]] = float(o["value"])
        c = sub.at(Kind.CELL)
        if c is not None:
            by_cell.setdefault(c.to_key(), []).append(o)

    def fit(ck):
        xs, ys = [], []
        for o in by_cell[ck]:
            d = o.get("detail") or {}
            if o["quantity"] == Q.GLYPH_BOX and "bbox_page_px" in d:
                _, x, y, w, h = o["value"]
                px0, py0, px1, py1 = d["bbox_page_px"]
                xs += [(x, px0), (x + w, px1)]
                ys += [(y, py0), (y + h, py1)]
        ax = np.polyfit([a for a, _ in xs], [b for _, b in xs], 1)
        ay = np.polyfit([a for a, _ in ys], [b for _, b in ys], 1)
        return lambda x, y: (ax[0] * x + ax[1], ay[0] * y + ay[1])

    pm = fitz.open(pdf)[1].get_pixmap(dpi=DPI)
    page = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
            if pm.n >= 3 else
            Image.frombytes("L", (pm.width, pm.height), pm.samples)
            .convert("RGB"))
    arr = np.asarray(page.convert("L"), dtype=float)
    font = ImageFont.load_default(size=20)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, refused = [], []

    for n, (s, why) in enumerate(subjects, 1):
        sub = Subject.from_key(s)
        staff = sub.at(Kind.STAFF).to_key()
        cell = sub.at(Kind.CELL)
        ck = cell.to_key()
        lines = lines_of[staff]
        sp = spacing_of.get(staff, 27.0)
        ok, contrast = _frame_ok(arr, lines, sp)
        if not ok:
            refused.append({"subject": s, "why": f"FRAME CONTROL {contrast:.1f}"})
            continue
        ev = A.Evidence(log, sub, spec)
        head_box = RH._xywh_head(ev.rows(Q.GLYPH_BOX)[-1].value)
        stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
        side, _sv = RH._own_stem_side(ev)
        own = RH._stems_on(head_box, stems)
        tip_ink, tip_rows = RH._stem_tip_flag_ink(ev, cell, own, side)

        space_rows = ev.rows(Q.CELL_STAFF_SPACE, scope=Scope.SELF_AND_ANCESTORS,
                             subject=cell)
        space = float(space_rows[-1].value) if space_rows else None
        window = None
        if own and side in ("up", "down") and space:
            sx0, sy0, sw, sh = RH._xywh(own[0])
            sx1, sy1 = sx0 + sw, sy0 + sh
            end = "top" if side == "up" else "bottom"
            tip_y, into_sign = (sy0, 1.0) if end == "top" else (sy1, -1.0)
            near = G.STEM_TIP_INK_NEAR_SPACES * space
            far = G.STEM_TIP_INK_FAR_SPACES * space
            width = G.STEM_TIP_INK_WIDTH_SPACES * space
            wy0, wy1 = sorted((tip_y + into_sign * near, tip_y + into_sign * far))
            window = (sx1, wy0, sx1 + width, wy1)

        P = fit(ck)
        box = [o for o in by_cell[ck] if o["subject"] == s
               and o["quantity"] == Q.GLYPH_BOX][0]
        px0, py0, px1, py1 = box["detail"]["bbox_page_px"]
        ys = [py0, py1] + lines
        cx0 = int(max(0, px0 - 9 * sp))
        cx1 = int(min(page.width, px1 + 9 * sp))
        cy0 = int(max(0, min(ys) - 5 * sp))
        cy1 = int(min(page.height, max(ys) + 5 * sp))
        Z = 3
        crop = page.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        T = lambda x, y: ((x - cx0) * Z, (y - cy0) * Z)

        overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        big = ImageFont.load_default(size=max(30, int(sp * Z * 0.8)))
        rgb = (0, 170, 60)
        top, bot = T(0, min(lines))[1], T(0, max(lines))[1]
        od.rectangle([0, top, crop.width, bot], fill=rgb + (50,))
        for ly in lines:
            y = T(0, ly)[1]
            od.line([(0, y), (crop.width, y)], fill=rgb + (200,), width=4)
        label = f"{staff} (FILED staff)"
        tw = od.textlength(label, font=big)
        ty = top + (bot - top) / 2 - big.size / 2
        od.rectangle([30, ty - 4, 30 + tw + 12, ty + big.size + 6],
                     fill=(255, 255, 255, 220), outline=rgb + (255,), width=4)
        od.text((36, ty), label, fill=rgb + (255,), font=big)
        crop = Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB")
        dr = ImageDraw.Draw(crop)

        def rect(b, colour, width=4):
            x0, y0, x1, y1 = b
            a, c = T(*P(x0, y0)), T(*P(x1, y1))
            dr.rectangle([a, c], outline=colour, width=width)

        for st in own:
            sx0, sy0, sw, sh = RH._xywh(st)
            rect((sx0, sy0, sx0 + sw, sy0 + sh), (0, 160, 0), 5)
        if window is not None:
            rect(window, (230, 170, 0), 4)

        bx0, by0 = T(px0, py0)
        bx1, by1 = T(px1, py1)
        arm = max(14, int((bx1 - bx0) * 0.5))
        for (ax_, ay_, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                   (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax_ - dx * 6, ay_ - dy * 6),
                     (ax_ + dx * arm, ay_ - dy * 6)], fill=(220, 0, 0), width=8)
            dr.line([(ax_ - dx * 6, ay_ - dy * 6),
                     (ax_ - dx * 6, ay_ + dy * arm)], fill=(220, 0, 0), width=8)
        step, y, k = sp * Z, T(0, min(lines))[1], 0
        while y < crop.height:
            dr.line([(2, y), (16 if k % 5 else 26, y)], fill=(0, 90, 200),
                    width=2)
            y += step
            k += 1

        dv = log.verdict(Q.DURATION, sub)
        v_desc = (f"{dv.outcome.value}:{dv.reason}"
                  if dv is not None else "?")
        name = f"flag-2.18c-{n:02d}.png"
        title = [
            (f"#{n:02d}  {s}  ({why})  stem {side}", (0, 0, 0)),
            (f"duration verdict: {v_desc}", (80, 0, 120)),
            (f"tip_ink: {tip_ink}  (matched rows: "
             f"{[(r.value, r.detail.get('right'), r.detail.get('left')) for r in tip_rows]})",
             (0, 0, 0)),
            ("GREEN own stem  YELLOW tested tip-ink window", (0, 0, 0)),
            ("Q: printed value of the bracketed note? does it print a "
             "FLAG hanging from the stem inside the yellow window?", (0, 0, 0)),
        ]
        band = 22 * (len(title) + 1)
        out = Image.new("RGB", (crop.width, crop.height + band), "white")
        out.paste(crop, (0, band))
        cd = ImageDraw.Draw(out)
        for i, (text, color) in enumerate(title):
            cd.text((6, 4 + i * 22), text, fill=color, font=font)
        out.save(OUT_DIR / name)
        manifest.append({
            "n": n, "file": name, "subject": s, "why_chosen": why,
            "stem_direction": side, "tip_ink": tip_ink,
            "duration_verdict": v_desc,
            "frame_contrast": round(contrast, 2),
            "page_box": [round(c, 1) for c in (px0, py0, px1, py1)],
            "question": ("printed value of the bracketed note; does it "
                         "print a flag hanging from the stem inside the "
                         "yellow window"),
            "VERDICT_none_yet": None,
        })
        print("wrote", name)
    (OUT_DIR / "flag-2.18c-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.18c",
        "record": rec_path,
        "dpi": DPI, "crops": manifest, "refused": refused}, indent=2))
    for r in refused:
        print("REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
