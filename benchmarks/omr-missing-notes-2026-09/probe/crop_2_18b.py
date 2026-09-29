"""ROADMAP 2.18b -- print crops for Sean: strokes dropped as beyond the stem tip
(class B), flags now attached through the tolerance, and the two regressions.

Reads the saved p1 record ONCE (`record_io.load_record`), re-decides it on
this tree (`review.rerun`), and for each subject recomputes -- through
`adjudicate_duration`'s own helpers -- which strokes are on the far side
(2.18), beyond the tip (2.18b) or kept, and which flags attach. `price_2_18b.py`'s
output supplies the value before (tolerance 0 = the 2.18 tree) and after.
Style after `benchmarks/omr-owner-domain-2026-09/crop_losers_2_6b.py`: the
FILED staff a shaded labelled BAND over its own `Q.STAFF_LINES`, the head
bracketed thick red, a staff-space ruler down the left.

  GREEN box   the head's own read stem
  BLUE box    a stroke kept (stem side, within reach or reached by a stem)
  RED X       a stroke DROPPED by 2.18b (past the tip, no read stem reaches it)
  GREY X      a stroke dropped by 2.18 (far side of the stem)
  ORANGE box  a flag the head now carries

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL: the filed staff's own lines must be
darker than a half-space off them on the render, or the crop is REFUSED.

    python3 benchmarks/omr-missing-notes-2026-09/probe/crop_2_18b.py \\
        <record.json> <price_2_18b.json>
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

#: Chosen by hand from the heads 2.18b changed in bars EXPORT writes (plus
#: one it deliberately left alone): four class-B heads, two flags joined
#: through the tolerance, the new wrong answer (a flag the detector named
#: 16th), one class-B head still wrong after the fix, and one head the rule-8
#: guard kept narrowed -- a crop set that shows only the wins is not evidence.
SUBJECTS = [
    ("glyph/1/1/10/1/3", "B"), ("glyph/1/1/10/1/4", "B"),
    ("glyph/1/1/11/1/0", "B"), ("glyph/1/1/10/7/4", "B, still wrong"),
    ("glyph/1/1/9/7/5", "flag"), ("glyph/1/1/3/3/2", "flag"),
    ("glyph/1/1/9/0/13", "regression: flag class says 16th"),
    ("glyph/1/0/3/3/11", "rule-8 guard kept it narrowed"),
]


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


def _v(d):
    if not d:
        return "?"
    if d.get("outcome") != "decided":
        return d.get("outcome")
    return d.get("beats")


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    from tools.omr.staged import adjudicate as A
    from tools.omr.staged import adjudicators          # noqa: F401
    from tools.omr.staged.adjudicators import rhythm as RH
    from tools.omr.staged.record import Kind, Q, Scope, Subject
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR

    rec_path, price_path = sys.argv[1:3]
    doc = load_record(rec_path)
    rec = doc["record"]
    price = json.loads(Path(price_path).read_text())
    changed = price["changed_off_to_all"]
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

    for n, (s, why) in enumerate(SUBJECTS, 1):
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
        kept, _cv, _yolo = RH._kept_beams(ev, cell)
        stems = ev.rows(Q.STEM, scope=Scope.SELF_AND_ANCESTORS, subject=cell)
        side, _sv = RH._own_stem_side(ev)
        kept, far = RH._on_stem_side(kept, head_box, side)
        tol = RH._join_tolerance(ev, cell)
        own = RH._stems_on(head_box, stems)
        kept_all = kept
        kept, beyond = RH._beyond_own_stem(kept, stems, own, side, tol)
        flags, _lv = RH._attached_flags(ev, cell, own, tol)
        joined, _att = RH._stem_joined(kept, stems, head_box)
        hb = head_box
        _c, possible = RH._beam_levels(kept, hb[0] + hb[2] / 2.0, hb[2],
                                       joined)
        guarded = bool(beyond) and not possible and not _lv
        if guarded:            # the adjudicator's rule-8 guard, mirrored
            kept, beyond = kept_all, []
        boxes = RH._cell_boxes(ev, cell)

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

        def rect(b, colour, width=4, cross=False):
            x, y, w, h = b
            a, c = T(*P(x, y)), T(*P(x + w, y + h))
            if cross:
                dr.line([a, c], fill=colour, width=width)
                dr.line([(a[0], c[1]), (c[0], a[1])], fill=colour, width=width)
            else:
                dr.rectangle([a, c], outline=colour, width=width)

        for st in own:
            rect(RH._xywh(st), (0, 160, 0), 5)
        for b in kept:
            rect(RH._xywh(b), (0, 60, 230))
        for b in far:
            rect(RH._xywh(b), (140, 140, 140), 3, cross=True)
        for b in beyond:
            rect(RH._xywh(b), (230, 0, 0), 5, cross=True)
        for f in flags:
            fb = RH._xywh_head(boxes[f.subject.to_key()].value)
            rect(fb, (255, 140, 0), 5)

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

        before, after = changed.get(s, [None, None])
        name = f"beams-2.18b-{n:02d}.png"
        title = [
            (f"#{n:02d}  {s}  ({why})  stem {side}", (0, 0, 0)),
            (f"before 2.18b: {_v(before)}   after 2.18b: {_v(after)} beats",
             (80, 0, 120)),
            ("GREEN own stem  BLUE kept stroke  RED X dropped by 2.18b (past "
             "the tip, no stem reaches it)  GREY X far side (2.18)  ORANGE "
             "flag read", (0, 0, 0)),
            ("Q: printed value of the bracketed note? Is any RED-X stroke "
             "this note's beam?", (0, 0, 0)),
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
            "stem_direction": side, "before_2_18b": before,
            "after_2_18b": after, "frame_contrast": round(contrast, 2),
            "strokes_dropped_beyond_tip": len(beyond),
            "strokes_far_side": len(far), "strokes_kept": len(kept),
            "flags_attached": len(flags), "rule_8_guard": guarded,
            "page_box": [round(c, 1) for c in (px0, py0, px1, py1)],
            "question": ("printed value of the bracketed note; is any RED-X "
                         "stroke this note's beam"),
            "VERDICT_none_yet": None,
        })
        print("wrote", name)
    (OUT_DIR / "beams-2.18b-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.18b",
        "record": ("scratch base.record.json -- Breitkopf 317803 pdf p1, "
                   "gathered on 6309396a, dirty False, --no-surya --no-ocr "
                   "--no-roster; re-decided on this tree; not committed"),
        "dpi": DPI, "crops": manifest, "refused": refused}, indent=2))
    for r in refused:
        print("REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
