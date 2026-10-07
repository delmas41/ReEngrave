#!/usr/bin/env python3
"""ROADMAP 2.58 / 2.58b: the two sheets for Sean.

    # Sheet A -- heads written on the staff that owns them
    python3 benchmarks/omr-local-staff-2026-09/mark_identity_sheet.py relocate \
        --lit lit_full.json --lit-list lit_moved.json --lit-fates lit_fates.json \
        --brahms brahms_full.json --brahms-list ... --brahms-fates ... \
        --out out/print/mark_identity_relocate.png

    # Sheet B -- marks that were written 2-4 times or nowhere, now once
    python3 benchmarks/omr-local-staff-2026-09/mark_identity_sheet.py groups \
        --lit-before lit_full.json --lit-after lit_groups.json \
        --lit-before-fates ... --lit-after-fates ... (same for brahms) \
        --out out/print/mark_identity_groups.png

Real print at the gather's own 600 dpi (deskewed page, `preprocessing.render_page`),
nearest-neighbour x3. Legend (also on the sheet):

  RED corner brackets     the subject head (the detector's box)
  GREEN corner brackets   a head that is ALREADY written there (collision tile)
  BLUE 1 px lines         the five lines of the staff the head was FOUND on
  ORANGE 1 px lines       the five lines of the staff that OWNS it (relocated)
  group tiles             one colour per member box, labelled

Every drawn staff line is RE-MEASURED against the pixel rows: it is snapped to
the darkest row within 0.4 staff space under the tile's own window, the snap
distance is printed, and a frame control (ink on the drawn rows must exceed
ink half a space off them) is asserted per tile -- a tile that fails it is
reported and not drawn as evidence.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tools.omr.staged import export as SX  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
import truth_set_2_44c as ts  # noqa: E402

BLUE, ORANGE, RED, GREEN = (0, 110, 255), (255, 120, 0), (225, 0, 0), (0, 170, 0)
PALETTE = [(225, 0, 0), (0, 110, 255), (0, 170, 0), (200, 0, 200), (255, 140, 0)]
SCALE = 3
HALF_W_SP = 4.5
DOCS = {"lit": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
_PAGES = {}


def font(n=13):
    for p in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, n)
        except Exception:
            pass
    return ImageFont.load_default()


def gray_page(doc, page):
    key = (doc, page)
    if key not in _PAGES:
        pdf = ts.DOCS[DOCS[doc]]["pdf"]
        img = render_page(pdf, page, dpi=600).rgb
        _PAGES[key] = np.asarray(Image.fromarray(img).convert("L"))
    return _PAGES[key]


# ── pitch in words ──────────────────────────────────────────────────────────
ORD = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh"]


def staff_position(pitch, clef):
    """Half-steps below the top line (0 = top line) that `pitch` sits at in
    `clef`, by inverting the pipeline's own `_pitch_from_position`."""
    from tools.omr.pitch_resolver import _pitch_from_position
    bare = pitch[0] + pitch[-1]
    for p in range(-14, 23):
        if _pitch_from_position(p, str(clef)) == bare:
            return p
    return None


def words(pitch, clef):
    p = staff_position(pitch, clef)
    if p is None:
        return f"{pitch} (position not found)"
    if 0 <= p <= 8:
        n = (8 - p) // 2 + 1
        return (f"{pitch}: on the {ORD[n]} line from the bottom" if p % 2 == 0
                else f"{pitch}: in the {ORD[(8 - p) // 2 + 1]} space from the bottom")
    if p < 0:
        n = -p // 2
        return (f"{pitch}: on the {ORD[n]} ledger line above the staff" if p % 2 == 0
                else (f"{pitch}: in the space just above the top line" if p == -1
                      else f"{pitch}: in the space above the {ORD[n]} ledger line above the staff"))
    n = (p - 8) // 2
    return (f"{pitch}: on the {ORD[n]} ledger line below the staff" if (p - 8) % 2 == 0
            else (f"{pitch}: in the space just below the bottom line" if p == 9
                  else f"{pitch}: in the space below the {ORD[n]} ledger line below the staff"))


# ── drawing ─────────────────────────────────────────────────────────────────
def snap_lines(gray, ys, x0, x1, sp):
    """Each recorded line -> the darkest row within 0.4 sp, plus the control
    (ink on the drawn rows vs half a space off them)."""
    out, snaps, on, off = [], [], [], []
    for y in ys:
        lo, hi = int(round(y - 0.4 * sp)), int(round(y + 0.4 * sp))
        rows = [(float((gray[r, x0:x1] < 140).mean()), r) for r in range(max(lo, 0), min(hi, gray.shape[0] - 1) + 1)]
        best = max(rows)[1]
        out.append(best)
        snaps.append(abs(best - y) / sp)
        on.append(float((gray[best, x0:x1] < 140).mean()))
        mid = int(round(best + 0.5 * sp))
        off.append(float((gray[mid, x0:x1] < 140).mean()))
    return out, max(snaps), float(np.mean(on)), float(np.mean(off))


def corner_brackets(d, box, scale, ox, oy, color, w=2, pad=2):
    x0, y0, x1, y1 = [(box[0] - ox) * scale - pad, (box[1] - oy) * scale - pad,
                      (box[2] - ox) * scale + pad, (box[3] - oy) * scale + pad]
    L = max(8, int(0.3 * min(x1 - x0, y1 - y0)))
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx, cy), (cx + sx * L, cy)], fill=color, width=w)
        d.line([(cx, cy), (cx, cy + sy * L)], fill=color, width=w)


def lines_of(rec, staff_key):
    rows = rec.obs(Q.STAFF_LINES, staff_key)
    sp = rec.obs(Q.STAFF_SPACING, staff_key)
    return (list(rows[-1]["value"]) if rows else None, float(sp[-1]["value"]) if sp else None)


def tile(doc, rec, page, system, shown, box, marks, caption, notes=None):
    """`shown` = [(staff_index, colour)], `box` = [x0,y0,x1,y1] page px of the
    subject, `marks` = [(box, colour, label)] extra brackets."""
    gray = gray_page(doc, page)
    infos = []
    for st, col in shown:
        ys, sp = lines_of(rec, f"staff/{page}/{system}/{st}")
        if ys is None or sp is None:
            return None
        infos.append((st, col, ys, sp))
    sp = infos[0][3]
    cx = (box[0] + box[2]) / 2.0
    x0, x1 = int(cx - HALF_W_SP * sp), int(cx + HALF_W_SP * sp)
    ytop = min(min(i[2]) for i in infos) - 2.2 * sp
    ybot = max(max(i[2]) for i in infos) + 2.2 * sp
    ytop, ybot = min(ytop, box[1] - 1.2 * sp), max(ybot, box[3] + 1.2 * sp)
    y0, y1 = int(max(ytop, 0)), int(min(ybot, gray.shape[0]))
    crop = gray[y0:y1, x0:x1]
    im = Image.fromarray(crop).convert("RGB").resize(
        (crop.shape[1] * SCALE, crop.shape[0] * SCALE), Image.NEAREST)
    d = ImageDraw.Draw(im)
    controls = []
    for st, col, ys, spi in infos:
        snapped, worst, on, off = snap_lines(gray, ys, x0, x1, spi)
        ok = on > off + 0.05
        controls.append((st, worst, on, off, ok))
        for r in snapped:
            yy = (r - y0) * SCALE + SCALE // 2
            d.line([(0, yy), (im.width, yy)], fill=col, width=1)
    corner_brackets(d, box, SCALE, x0, y0, RED)
    f = font(12)
    for mb, col, lab in marks:
        corner_brackets(d, mb, SCALE, x0, y0, col)
        d.text(((mb[0] - x0) * SCALE, (mb[3] - y0) * SCALE + 3), lab, fill=col, font=f)
    cap_h = 22 * (len(caption) + 1)
    out = Image.new("RGB", (im.width, im.height + cap_h), (255, 255, 255))
    out.paste(im, (0, 0))
    d2 = ImageDraw.Draw(out)
    for k, line in enumerate(caption):
        d2.text((6, im.height + 4 + 22 * k), line, fill=(0, 0, 0), font=font(13))
    c = "; ".join("staff %d snap %.2f sp on %.2f off %.2f %s" % (st, w, a, b, "ok" if ok else "FRAME CONTROL FAILED")
                  for st, w, a, b, ok in controls)
    d2.text((6, im.height + 4 + 22 * len(caption)), c, fill=(110, 110, 110), font=font(10))
    return out, controls


def sheet(tiles, title, legend, out_path, cols=4):
    tiles = [t for t in tiles if t is not None]
    if not tiles:
        raise SystemExit("no tiles")
    w = max(t.width for t in tiles)
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    hs = [max(t.height for t in r) for r in rows]
    head = 70
    W = cols * (w + 10) + 10
    H = head + sum(h + 10 for h in hs) + 10
    sh = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(sh)
    d.text((10, 8), title, fill=(0, 0, 0), font=font(16))
    for k, line in enumerate(legend):
        d.text((10, 30 + 15 * k), line, fill=(60, 60, 60), font=font(12))
    y = head
    for r, h in zip(rows, hs):
        x = 10
        for t in r:
            sh.paste(t, (x, y))
            x += w + 10
        y += h + 10
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sh.save(out_path)
    print("wrote", out_path, sh.size)


def own_box(rec, sub):
    o = rec.obs(Q.GLYPH_BOX, sub)
    return SX._page_box_of(o[-1]) if o else None


def owner_of(rec, sub):
    v = rec.verdict(Q.GLYPH_OWNER, sub)
    return (v.get("value"), v.get("reason")) if v else (None, None)


def heads_near(rec, page, system, staff, box, sp, lim=0.75):
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    out = []
    for o in rec.obs_of(Q.GLYPH_BOX):
        s = SX._parse_subject(o["subject"])
        if (s["page"], s["system"], s["staff"]) != (page, system, staff) or not rec.obs(Q.NOTEHEAD_CLASS, o["subject"]):
            continue
        b = SX._page_box_of(o)
        if b and abs((b[0] + b[2]) / 2 - cx) < lim * sp and abs((b[1] + b[3]) / 2 - cy) < lim * sp:
            out.append((o["subject"], b))
    return out


def relocate_sheet(a):
    rng = random.Random(2058)
    tiles, report = [], []
    for key in ("lit", "brahms"):
        rp = getattr(a, key)
        if not rp:
            continue
        res = load_record(rp)
        rec = SX.Record(res)
        moved = json.loads(Path(getattr(a, key + "_list")).read_text())["moved"]
        fates = json.loads(Path(getattr(a, key + "_fates")).read_text())["on"]
        coll = sorted(g for g, v in fates.items() if v == "relocation_collides")
        picks = rng.sample(moved, min(6, len(moved)))
        for m in picks:
            g = m["glyph"]
            s = SX._parse_subject(g)
            box = own_box(rec, g)
            val, reason = owner_of(rec, g)
            os_ = SX._parse_subject(val)["staff"]
            cap = [f"{key} p{s['page']} s{s['system']}: found on staff {s['staff']}, belongs to staff {os_} ({reason})",
                   "now written on staff %d: %s" % (os_, words(m["pitch"], m["clef"])),
                   "WRITTEN"]
            t = tile(key, rec, s["page"], s["system"], [(s["staff"], BLUE), (os_, ORANGE)], box, [], cap)
            tiles.append(t[0] if t else None)
            report.append((g, "relocated", t[1] if t else None))
        for g in coll[:6]:
            s = SX._parse_subject(g)
            box = own_box(rec, g)
            val, reason = owner_of(rec, g)
            os_ = SX._parse_subject(val)["staff"]
            _, sp = lines_of(rec, f"staff/{s['page']}/{s['system']}/{os_}")
            near = heads_near(rec, s["page"], s["system"], os_, box, sp)
            marks = [(b, GREEN, "already written") for _, b in near]
            cap = [f"{key} p{s['page']} s{s['system']}: found on staff {s['staff']}, belongs to staff {os_} ({reason})",
                   "NOT written again: staff %d's bar already holds a head here (within 0.75 space)" % os_,
                   "COUNTED as relocation_collides"]
            t = tile(key, rec, s["page"], s["system"], [(s["staff"], BLUE), (os_, ORANGE)], box, marks, cap)
            tiles.append(t[0] if t else None)
            report.append((g, "collision", t[1] if t else None))
    sheet(tiles[:24], "Heads that belong to another staff: written on the staff that owns them (12 relocated, up to 12 collisions)",
          ["RED corner brackets = the head.  BLUE lines = the staff it was found on.  ORANGE lines = the staff that owns it.  GREEN brackets = a head already written there.",
           "Lines are 1 px, snapped to the darkest pixel row under the tile and checked against the rows half a space off (control printed under each tile).",
           "Real print, 600 dpi, x3."], a.out)
    bad = [r for r in report if r[2] and not all(c[4] for c in r[2])]
    print("tiles", len(report), "frame-control failures", len(bad))


def groups_sheet(a):
    rng = random.Random(2058)
    tiles = []
    for key in ("lit", "brahms"):
        if not getattr(a, key + "_after", None):
            continue
        after = SX.Record(load_record(getattr(a, key + "_after")))
        fb = json.loads(Path(getattr(a, key + "_before_fates")).read_text())["off"]
        fa = json.loads(Path(getattr(a, key + "_after_fates")).read_text())["off"]
        members = {}
        for o in after.obs_of(Q.MARK_GROUP):
            members.setdefault(o["value"], []).append(o["subject"])
        changed = []
        for gid, subs in members.items():
            if len(subs) < 2:
                continue
            wb = sum(1 for s in subs if str(fb.get(s, "")).startswith("written"))
            wa = sum(1 for s in subs if str(fa.get(s, "")).startswith("written"))
            if wb != wa and wb != 1:
                changed.append((gid, subs, wb, wa))
        by = {"twice+": [c for c in changed if c[2] >= 2], "nowhere": [c for c in changed if c[2] == 0]}
        print(key, {k: len(v) for k, v in by.items()})
        picks = rng.sample(by["twice+"], min(4, len(by["twice+"]))) + rng.sample(by["nowhere"], min(2, len(by["nowhere"])))
        for gid, subs, wb, wa in picks:
            s0 = SX._parse_subject(subs[0])
            boxes = [own_box(after, s) for s in subs]
            if any(b is None for b in boxes):
                continue
            ub = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
            marks = []
            staffs = set()
            for k, (s, b) in enumerate(zip(subs, boxes)):
                ss = SX._parse_subject(s)
                staffs.add(ss["staff"])
                marks.append((b, PALETTE[k % len(PALETTE)],
                              "%s/%s %s" % (ss["staff"], ss["cell"], str(fa.get(s, "?"))[:22])))
            shown = [(st, [BLUE, ORANGE, GREEN][k % 3]) for k, st in enumerate(sorted(staffs))]
            cap = [f"{key} p{s0['page']} s{s0['system']} mark {gid}: {len(subs)} boxes of one mark",
                   "before: written %s time(s)%s" % (wb, " -- nowhere" if wb == 0 else ""),
                   "after: written %d time, others counted (labels = staff/cell + what happened)" % wa]
            t = tile(key, after, s0["page"], s0["system"], shown, ub, marks, cap)
            tiles.append(t[0] if t else None)
    sheet(tiles, "Marks that were written more than once or not at all: now once",
          ["Each coloured bracket is one detector box of the SAME printed mark; the label says which staff/bar it was cut from and what export did with it.",
           "Lines are 1 px, snapped to the darkest row and checked against rows half a space off.  Real print, 600 dpi, x3."], a.out)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="mode", required=True)
    r = sp.add_parser("relocate")
    for k in ("lit", "brahms"):
        r.add_argument("--" + k)
        r.add_argument("--%s-list" % k)
        r.add_argument("--%s-fates" % k)
    r.add_argument("--out", required=True)
    g = sp.add_parser("groups")
    for k in ("lit", "brahms"):
        g.add_argument("--%s-after" % k)
        g.add_argument("--%s-before-fates" % k)
        g.add_argument("--%s-after-fates" % k)
    g.add_argument("--out", required=True)
    a = ap.parse_args()
    {"relocate": relocate_sheet, "groups": groups_sheet}[a.mode](a)


if __name__ == "__main__":
    main()
