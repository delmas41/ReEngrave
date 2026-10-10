#!/usr/bin/env python3
"""l281_miss_images: phone-friendly CONTEXT images of every miss of the 2.81 bare-stem rule, and the
manager's table of measured facts. ROADMAP 2.81 follow-up (Sean, 2026-10-10: *"Can we look closer at the 1/4
of quarters that are missing -- I would like to see if I can identify some patterns"*). No product code
changed; nothing here draws a conclusion.

EACH IMAGE is 1000 px wide, panels stacked (never side by side):
  header   a big image number; one line "Printed: <answer>. We read: <our candidates>"
  TOP      the clean print around the miss -- the whole bar, the neighbouring staff lines -- a red corner bracket
           on each missed note (numbered where a bar holds several) and NOTHING else
  BOTTOM   the same crop with OUR reading drawn on: the stem we attached (blue; or "no stem decided"), every
           stroke we REFUSED as a beam (orange, with the test that refused it in plain words), any beam we KEPT
           (green), the tip window the flag test looked in (dotted), any flag box (magenta)
  legend   the colours, baked in

THE PER-STROKE REFUSALS are not in the saved verdicts (they carry counts): `l281_miss_rebuild.py` re-runs
ADJUDICATE over the page's saved GATHER rows with the filters wrapped, after a control that must reproduce every
saved duration verdict on the page. The crop is the 600 dpi page raster (`preprocessing.render_page`, the
gather's frame), normalised to 1000 px wide. Each image carries its own frame control (staff-line contrast of the
record's lines over the print, vs the same lines moved half a space).

    python3 l281_miss_images.py --scratch DIR --scored b0-scored.json --out out/print/2.81-misses
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import l281_miss_list as ML  # noqa: E402
from l281_truth import Truth  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

WIDTH = 1000
RED = (220, 30, 30)
ORANGE = (240, 120, 0)
GREEN = (0, 150, 40)
BLUE = (30, 90, 230)
TEAL = (0, 140, 150)
MAGENTA = (190, 0, 190)
GREY = (90, 90, 90)
SAGITTA_MAX = 0.40            # rhythm.BEAM_SAGITTA_MAX_SPACES (2.74), restated only to print the limit
THICK_MIN = 1.75              # rhythm.BEAM_THICKNESS_RATIO_MIN (2.74)

PDFS = {
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
NAMES = {"brahms": "Brahms 1 (Breitkopf)", "litolff": "Beethoven 5 (Litolff)"}

WORDS = {   # refusal -> plain English
    "too_thin": "too thin", "one_stem": "touches one stem", "not_straight": "curved",
    "through_heads": "runs through the heads", "no_stem_at_ends": "no stem at its ends",
    "ledger_line": "a ledger line", "tremolo_slash": "a tremolo slash",
    "neighbour_staff_beam": "the next staff's beam", "decided_arc_ink": "ink of a slur/tie we found",
    "far_side_of_the_head": "on the far side of the head", "past_the_stem_tip": "past the stem's tip",
}
VALUE_NAME = {0.25: "sixteenth", 0.375: "dotted sixteenth", 0.5: "eighth", 0.75: "dotted eighth",
              1.0: "quarter", 1.5: "dotted quarter", 2.0: "half", 3.0: "dotted half", 4.0: "whole"}


def font(size, bold=False):
    for p in (("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
               "/System/Library/Fonts/Supplemental/Arial.ttf"),
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


# ─── the rows of a page, indexed ─────────────────────────────────────────────

class Rows:
    def __init__(self, path):
        d = json.loads(Path(path).read_text())
        self.heads, self.flags, self.strokes, self.ink = {}, collections.defaultdict(list), \
            collections.defaultdict(dict), {}
        self.stems, self.tips, self.tips_abs = collections.defaultdict(dict), collections.defaultdict(list), \
            collections.defaultdict(list)
        self.staff_lines, self.staff_spacing, self.cell_box, self.cell_space = {}, {}, {}, {}
        self.head_ink, self.reach = {}, {}
        self.cells_of_staff = collections.defaultdict(set)
        for o in d["observations"]:
            q, s = o["quantity"], o["subject"]
            if q == Q.GLYPH_BOX and isinstance(o["value"], list) and o["value"] \
                    and isinstance(o["value"][0], str):
                cls = o["value"][0]
                det = o.get("detail") or {}
                row = {"cls": cls, "canon": o["value"][1:5], "page": det.get("bbox_page_px")}
                if cls.startswith("notehead"):
                    self.heads[s] = row
                elif cls.startswith("flag"):
                    self.flags["cell/" + "/".join(s.split("/")[1:5])].append(dict(row, key=s))
            elif q == Q.BEAM_STROKE:
                self.strokes[s][o["id"]] = {"box": o["value"], "reader": o.get("reader")}
            elif q == Q.BEAM_STROKE_INK:
                det = o.get("detail") or {}
                self.ink[det.get("beam_row_id")] = det
            elif q == Q.STEM:
                self.stems[s][o["id"]] = o["value"]
            elif q == Q.STEM_TIP_INK:
                det = o.get("detail") or {}
                self.tips[s].append({"stem": det.get("stem_row_id"), "end": det.get("end"), "value": o["value"],
                                     "right": det.get("right"), "left": det.get("left"),
                                     "window": det.get("window_canonical"), "hooks": det.get("hooks")})
            elif q == Q.STAFF_LINES:
                self.staff_lines.setdefault(s, [float(v) for v in o["value"]])
            elif q == Q.STAFF_SPACING:
                self.staff_spacing.setdefault(s, float(o["value"]))
            elif q == Q.CELL_BOX:
                self.cell_box.setdefault(s, [float(v) for v in o["value"]])
                p = s.split("/")
                self.cells_of_staff["staff/" + "/".join(p[1:4])].add(int(p[4]))
            elif q == Q.CELL_STAFF_SPACE:
                self.cell_space.setdefault(s, float(o["value"]))
            elif q == Q.NOTEHEAD_INK:
                w = ((o.get("detail") or {}).get("ink_raw") or {}).get("windows") or {}
                self.head_ink[s] = {"value": o["value"], "center": w.get("center"), "ring": w.get("ring")}
            elif q == Q.HEAD_STEM_REACH:
                self.reach[s] = o["value"]
        for a in d["abstentions"]:
            if a["quantity"] == Q.STEM_TIP_INK:
                det = a.get("detail") or {}
                self.tips_abs[a["subject"]].append({"stem": det.get("stem_row_id"), "end": det.get("end"),
                                                    "reason": a.get("reason")})


def cell_of(key):
    return "cell/" + "/".join(key.split("/")[1:5])


def staff_of(key):
    return "staff/" + "/".join(key.split("/")[1:4])


class Frame:
    """The linear map the head's own two boxes (canonical `[x, y, w, h]`, page corners) define."""
    def __init__(self, head):
        cx, cy, cw, ch = head["canon"]
        self.px0, self.py0, px1, py1 = head["page"]
        self.cx, self.cy = cx, cy
        self.ax, self.ay = (px1 - self.px0) / float(cw), (py1 - self.py0) / float(ch)

    def box(self, b):               # canonical [x, y, w, h] -> page corners
        x, y, w, h = b
        return [self.px0 + (x - self.cx) * self.ax, self.py0 + (y - self.cy) * self.ay,
                self.px0 + (x + w - self.cx) * self.ax, self.py0 + (y + h - self.cy) * self.ay]

    def corners(self, b):           # canonical [x0, y0, x1, y1] -> page corners
        x0, y0, x1, y1 = b
        return self.box([x0, y0, x1 - x0, y1 - y0])

    def len_px(self, canon_len):
        return canon_len * self.ay


def cand_name(c):
    w = round(float(c.get("written") or 0), 4)
    return VALUE_NAME.get(w, f"{w} beats")


def reading_text(verdict):
    cands = sorted(verdict.get("candidates") or [], key=lambda c: -(c.get("beam_levels") or 0))
    names = [cand_name(c) for c in cands]
    if verdict.get("outcome") == "narrowed" and names:
        return " | ".join(names)
    if verdict.get("outcome") == "decided":
        return "decided"
    return verdict.get("outcome") or "?"


# ─── the facts ───────────────────────────────────────────────────────────────

def tip_state(R, key, cap_head):
    cell = cell_of(key)
    hs = cap_head["others"].get(Q.HEAD_STEM) or {}
    if hs.get("outcome") != "decided" or not hs.get("value"):
        return "no decided stem", {"head_stem": hs.get("outcome"), "why": hs.get("reason")}, None
    stem = hs["value"]
    side = cap_head["detail"].get("beam_side")
    if side not in ("up", "down"):
        r = R.reach.get(key)
        side = r if r in ("up", "down") else None
    if side is None:
        return "stem decided, direction unknown", {}, stem
    end = "top" if side == "up" else "bottom"
    for t in R.tips[cell]:
        if t["stem"] == stem and t["end"] == end:
            d = {"end": end, "right": t["right"], "left": t["left"], "window": t["window"]}
            if t["value"]:
                return "flag ink seen in the window", d, stem
            if t["right"] is not None and t["right"] >= 0.30:
                return "ink on both sides (not read as clean)", d, stem
            return "read: no flag ink in the window", d, stem
    for t in R.tips_abs[cell]:
        if t["stem"] == stem and t["end"] == end:
            return f"not read ({t['reason']}: a beam-stroke box lies in the window)" \
                if t["reason"] == "occupied" else f"not read ({t['reason']})", {"end": end}, stem
    return "no reading", {"end": end}, stem


def tip_window_page(R, F, key, stem_id, end):
    """The window the flag test looked in, as page corners: the row's own window if it was read, else the window
    `gather._observe_stem_tip_ink` WOULD have used (same constants), so a 'not read' tip is still shown."""
    cell = cell_of(key)
    for t in R.tips[cell]:
        if t["stem"] == stem_id and t["end"] == end and t["window"]:
            return F.corners(t["window"]), True
    box = R.stems[cell].get(stem_id)
    sp = R.cell_space.get(cell)
    if not box or not sp:
        return None, False
    x, y, w, h = box
    tip_y, into = (y, 1.0) if end == "top" else (y + h, -1.0)
    ya, yb = sorted((tip_y + into * 1.0 * sp, tip_y + into * 2.5 * sp))
    return F.corners([x + w, ya, x + w + 0.9 * sp, yb]), False


def stroke_facts(R, F, sid, story, head_page_box, lines, sp_page):
    """Measured facts of one candidate stroke, page px / staff spaces."""
    cell_boxes = None
    st = R.strokes_by_id.get(sid)
    box = F.box(st["box"])
    ink = R.ink.get(sid) or {}
    cx_, cy_ = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    hy = (head_page_box[1] + head_page_box[3]) / 2
    thick_px = ink.get("thickness_px")
    slope = None
    if thick_px:
        h_c, w_c = st["box"][3], st["box"][2]
        slope = math.degrees(math.atan2(max(0.0, h_c - thick_px), w_c)) if w_c else None
    inside = [round(l, 1) for l in lines if box[1] <= l <= box[3]]
    dist = min((abs(cy_ - l) for l in lines), default=None)
    why = story["why"]
    d = {"stroke": sid, "reader": story["reader"], "refused_by": why,
         "word": WORDS.get(why, why),
         "thickness_ratio": ink.get("thickness_ratio"),
         "thickness_vs_cut": (f"{ink['thickness_ratio']:.2f} vs {THICK_MIN}" if why == "too_thin"
                              and ink.get("thickness_ratio") is not None else None),
         "bow_spaces": ink.get("sagitta_spaces"),
         "stems_at_its_ends": [bool(e.get("found")) for e in (ink.get("end_stems") or [])],
         "width_spaces": round((box[2] - box[0]) / sp_page, 2), "height_spaces": round((box[3] - box[1]) / sp_page, 2),
         "slope_deg_est": None if slope is None else round(slope, 1),
         "centre_vs_head_spaces": round((cy_ - hy) / sp_page, 2),     # + = below the head's centre
         "over_or_under_the_heads": "under" if cy_ > hy else "over",
         "own_staff_lines_inside_its_box": len(inside),
         "centre_to_nearest_line_spaces": None if dist is None else round(dist / sp_page, 2),
         "on_a_staff_line": (dist is not None and dist <= 0.25 * sp_page),
         "page_box": [round(v, 1) for v in box]}
    return d


# ─── drawing ─────────────────────────────────────────────────────────────────

def dashed(draw, p0, p1, color, width, on=9, off=7):
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L == 0:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    t = 0.0
    while t < L:
        a, b = t, min(L, t + on)
        draw.line([(x0 + ux * a, y0 + uy * a), (x0 + ux * b, y0 + uy * b)], fill=color, width=width)
        t += on + off


def dashed_rect(draw, r, color, width=3):
    x0, y0, x1, y1 = r
    dashed(draw, (x0, y0), (x1, y0), color, width)
    dashed(draw, (x1, y0), (x1, y1), color, width)
    dashed(draw, (x1, y1), (x0, y1), color, width)
    dashed(draw, (x0, y1), (x0, y0), color, width)


def bracket(draw, r, color, width=4, arm=None):
    x0, y0, x1, y1 = r
    pad = 4
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    arm = arm or max(12, 0.45 * (y1 - y0))
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.line([(x, y), (x + dx * arm, y)], fill=color, width=width)
        draw.line([(x, y), (x, y + dy * arm)], fill=color, width=width)


def label(layer, draw, text, xy, color, f, placed, bg=(255, 255, 255, 185)):
    """A text plate at xy (top-left), nudged down while it overlaps a plate already placed."""
    x, y = xy
    w, h = draw.textbbox((0, 0), text, font=f)[2:]
    w += 8
    h += 6
    x = max(2, min(x, layer.size[0] - w - 2))               # never cut off by the panel's edge
    for _ in range(40):
        r = (x, y, x + w, y + h)
        if not any(not (r[2] < p[0] or r[0] > p[2] or r[3] < p[1] or r[1] > p[3]) for p in placed):
            break
        y += h + 2
    draw.rectangle((x, y, x + w, y + h), fill=bg)
    draw.text((x + 4, y + 1), text, fill=color, font=f)
    placed.append((x, y, x + w, y + h))


def local_lines(gray, lines, sp, xa, xb):
    """The five staff lines as the INK of this crop has them: each record line moved to the darkest row of the
    ink profile within 0.8 spaces of it (the profile is the mean darkness of a row across the crop, smoothed over
    5 px). Returns `(local lines, median offset from the record's lines in spaces)`; a line with no clear peak
    keeps the record's y."""
    H = gray.shape[0]
    xa, xb = max(0, int(xa)), min(gray.shape[1], int(xb))
    lo, hi = int(max(0, lines[0] - 1.5 * sp)), int(min(H, lines[-1] + 1.5 * sp))
    prof = (255.0 - gray[lo:hi, xa:xb]).mean(axis=1) / 255.0
    k = np.ones(5) / 5.0
    prof = np.convolve(prof, k, mode="same")
    out, offs = [], []
    for y in lines:
        a, b = int(round(y - 0.8 * sp)) - lo, int(round(y + 0.8 * sp)) - lo
        a, b = max(0, a), min(len(prof), b)
        if b - a < 3:
            out.append(float(y))
            continue
        j = a + int(np.argmax(prof[a:b]))
        if prof[j] < 1.4 * float(np.median(prof)) + 0.02:            # no clear peak: keep the record's line
            out.append(float(y))
            continue
        out.append(float(lo + j))
        offs.append((lo + j - y) / sp)
    return out, round(float(np.median(offs)), 2) if offs else None


def fit_text(draw, text, max_w, size, bold=False, min_size=18):
    while size > min_size:
        f = font(size, bold)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return font(min_size, bold)


# ─── one image ───────────────────────────────────────────────────────────────

def process(item, n, R, cap, page_img, truth, ctx):
    keys = item["keys"]
    head0 = R.heads[keys[0]]
    F = Frame(head0)
    cell = cell_of(keys[0])
    staff = staff_of(keys[0])
    lines = R.staff_lines[staff]
    sp = R.staff_spacing[staff]
    # the map is read off the first head's boxes; the others must agree (the frame control for the map)
    drift = 0.0
    for k in keys[1:]:
        h = R.heads[k]
        c = F.box(h["canon"])
        drift = max(drift, max(abs(c[i] - h["page"][i]) for i in range(4)))
    # ---- what we drew from: per head ----
    R.strokes_by_id = R.strokes[cell]
    head_boxes = [R.heads[k]["page"] for k in keys]
    rects = list(head_boxes)                 # everything the crop must hold (page px)
    stems_drawn, windows, strokes_drawn, flags_drawn = {}, [], {}, []
    head_info = []
    for i, k in enumerate(keys, 1):
        ch = cap["heads"][k]
        state, td, stem_id = tip_state(R, k, ch)
        hk_ = R.heads[k]
        hi_ = R.head_ink.get(k) or {}
        pb_ = hk_["page"]
        info = {"n": i, "key": k, "tip_state": state, "tip": {a: b for a, b in td.items() if a != "window"},
                "head": {"class": hk_["cls"], "ink_center": hi_.get("center"), "ink_ring": hi_.get("ring"),
                         "box_spaces": [round((pb_[2] - pb_[0]) / sp, 2), round((pb_[3] - pb_[1]) / sp, 2)],
                         "whole_rest_test": (cap["heads"][k]["others"].get(Q.NOTEHEAD_IS_A_WHOLE_REST) or {}).get("outcome")},
                "stem_decided": stem_id is not None,
                "head_stem": ch["others"].get(Q.HEAD_STEM), "verdict": ch["verdict"], "detail": ch["detail"]}
        if stem_id:
            sb = R.stems[cell].get(stem_id)
            if sb:
                stems_drawn.setdefault(stem_id, {"box": F.box(sb), "heads": []})["heads"].append(i)
                rects.append(F.box(sb))
                info["stem_length_spaces"] = round((F.box(sb)[3] - F.box(sb)[1]) / sp, 2)
            end = td.get("end")
            if end:
                w_, read = tip_window_page(R, F, k, stem_id, end)
                if w_:
                    dup = next((w for w in windows if all(abs(a - b) < 1.0 for a, b in zip(w["rect"], w_))), None)
                    if dup:
                        dup["heads"].append(i)
                    else:
                        windows.append({"rect": w_, "read": read, "heads": [i], "state": state})
                        rects.append(w_)
        for sid, s in ch["strokes"].items():
            if not s["candidate"]:
                continue
            st = R.strokes[cell].get(sid)
            if st is None:
                continue
            sd = strokes_drawn.setdefault(sid, {"story": s, "heads": []})
            sd["heads"].append(i)
        head_info.append(info)
    # flag boxes of the cell (detector) near the heads
    hx0 = min(b[0] for b in head_boxes) - 2.5 * sp
    hx1 = max(b[2] for b in head_boxes) + 3.5 * sp
    for fl in R.flags[cell]:
        pb = fl["page"]
        if pb and pb[2] >= hx0 and pb[0] <= hx1 and abs((pb[1] + pb[3]) / 2 - (head_boxes[0][1] + head_boxes[0][3]) / 2) < 9 * sp:
            flags_drawn.append(fl)
            rects.append(pb)
    truth_boxes = {"beam": [], "flag": [], "stem": []}
    if truth is not None:
        byid = {i.id: i for i in truth.items}
        for bid in item.get("truth_beam_ids") or []:
            truth_boxes["beam"].append(byid[bid].rect)
        for fid in item.get("truth_flag_ids") or []:
            truth_boxes["flag"].append(byid[fid].rect)
        for tid in item.get("truth_ids") or []:
            for s in truth.stem_of(byid[tid]):
                truth_boxes["stem"].append(s.rect)
        for r_ in truth_boxes["beam"] + truth_boxes["flag"]:
            rects.append(r_)
    # strokes the heads considered but that lie well off this staff (the next staff's beam, a slur two staves
    # away) would stretch the picture to twice its height: those within 5 spaces of the heads, stems and staff
    # are drawn; the others are LISTED under the picture and kept in the manifest, never dropped silently.
    cy0 = min([r[1] for r in rects] + [lines[0]]) - 3 * sp
    cy1 = max([r[3] for r in rects] + [lines[-1]]) + 3 * sp
    strokes_off = {}
    for sid in list(strokes_drawn):
        b = F.box(R.strokes[cell][sid]["box"])
        if b[3] < cy0 or b[1] > cy1:
            strokes_off[sid] = strokes_drawn.pop(sid)
        else:
            rects.append(b)
    # measured: how far the NEAREST candidate stroke lies from the tip of the stem we attached (staff spaces)
    for h in head_info:
        h["nearest_stroke_to_stem_tip_spaces"] = None
        if not h["stem_decided"]:
            continue
        sid_ = h["head_stem"]["value"]
        sb = R.stems[cell].get(sid_)
        side_ = h["detail"].get("beam_side")
        if not sb or side_ not in ("up", "down"):
            continue
        b = F.box(sb)
        tx, ty = (b[0] + b[2]) / 2.0, (b[1] if side_ == "up" else b[3])
        best = None
        for sid in cap["heads"][h["key"]]["strokes"]:
            if not cap["heads"][h["key"]]["strokes"][sid]["candidate"] or sid not in R.strokes[cell]:
                continue
            sbx = F.box(R.strokes[cell][sid]["box"])
            dx = max(sbx[0] - tx, 0.0, tx - sbx[2])
            dy = max(sbx[1] - ty, 0.0, ty - sbx[3])
            dd = math.hypot(dx, dy) / sp
            best = dd if best is None else min(best, dd)
        h["nearest_stroke_to_stem_tip_spaces"] = None if best is None else round(best, 2)
    # ---- the crop window ----
    cb = R.cell_box.get(cell)
    ex0 = min(r[0] for r in rects)
    ex1 = max(r[2] for r in rects)
    ey0 = min(r[1] for r in rects)
    ey1 = max(r[3] for r in rects)
    X0 = min(cb[0] if cb else ex0, ex0) - 3.0 * sp
    X1 = max(cb[2] if cb else ex1, ex1) + 3.0 * sp
    Y0 = min(ey0, lines[0]) - 3.0 * sp
    Y1 = max(ey1, lines[-1]) + 3.0 * sp
    if (X1 - X0) < 30 * sp:                    # at least ~30 spaces wide: the bar and a good part of its neighbours
        mx = (min(b[0] for b in head_boxes) + max(b[2] for b in head_boxes)) / 2.0
        X0, X1 = min(X0, mx - 15 * sp), max(X1, mx + 15 * sp)
    if (Y1 - Y0) < 14 * sp:
        mid = (Y0 + Y1) / 2
        Y0, Y1 = mid - 7 * sp, mid + 7 * sp
    X0, Y0, X1, Y1 = int(X0), int(Y0), int(X1), int(Y1)
    H, W = page_img.shape[:2]
    crop = np.full((Y1 - Y0, X1 - X0, 3), 255, np.uint8)
    xa, ya, xb, yb = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
    crop[ya - Y0:yb - Y0, xa - X0:xb - X0] = page_img[ya:yb, xa:xb]
    scale = WIDTH / float(X1 - X0)
    base = cv2.resize(crop, None, fx=scale, fy=scale,
                      interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
    ph, pw = base.shape[:2]

    def T(b):                                   # page corners -> panel pixels
        return [(b[0] - X0) * scale, (b[1] - Y0) * scale, (b[2] - X0) * scale, (b[3] - Y0) * scale]

    def panel(annotated):
        im = Image.fromarray(base).convert("RGBA")
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        placed = []
        if annotated:
            # flags (detector boxes)
            for fl in flags_drawn:
                r = T(fl["page"])
                d.rectangle(r, outline=MAGENTA + (255,), width=4)
                label(layer, d, f"flag box ({fl['cls'].replace('flag', '')})", (r[0], r[3] + 3), MAGENTA, font(22), placed)
            # the tip window
            for w in windows:
                r = T(w["rect"])
                dashed_rect(d, r, TEAL + (255,), 3)
                txt = "tip window: " + ("looked, no flag ink" if (w["read"] and "no flag" in w["state"]) else
                                        "flag ink seen" if w["read"] and "seen" in w["state"] else
                                        "could not look" if not w["read"] else w["state"])
                if len(w["heads"]) > 1:
                    txt += f" ({','.join(str(h) for h in w['heads'])})"
                label(layer, d, txt, (r[2] + 6, r[1] - 4), TEAL, font(21), placed)
            # the stem(s) we attached
            for sid, s in stems_drawn.items():
                r = T(s["box"])
                d.rectangle((r[0] - 2, r[1], r[2] + 2, r[3]), outline=BLUE + (255,), width=3)
                label(layer, d, "stem we attached" if len(keys) == 1 else "stem we attached (" +
                      ",".join(str(h) for h in s["heads"]) + ")", (r[2] + 6, (r[1] + r[3]) / 2 - 14), BLUE, font(21), placed)
            # strokes
            for sid, s in strokes_drawn.items():
                st = R.strokes[cell][sid]
                r = T(F.box(st["box"]))
                why = s["story"]["why"]
                if why == "kept":
                    d.rectangle(r, outline=GREEN + (255,), width=5)
                    label(layer, d, "beam we kept", (r[0], r[1] - 26), GREEN, font(22), placed)
                else:
                    d.rectangle(r, outline=ORANGE + (255,), width=4)
                    txt = WORDS.get(why, why)
                    ink = R.ink.get(sid) or {}
                    if why == "too_thin" and ink.get("thickness_ratio") is not None:
                        txt += f" ({ink['thickness_ratio']:.2f} x a staff line; needs {THICK_MIN})"
                    elif why == "not_straight" and ink.get("sagitta_spaces") is not None:
                        txt += f" (bow {ink['sagitta_spaces']:.2f} sp; limit {SAGITTA_MAX})"
                    label(layer, d, "refused: " + txt, (r[0], r[3] + 3), ORANGE, font(21), placed)
            # heads with no decided stem: say so
            nostem = [h for h in head_info if not h["stem_decided"]]
            if len(keys) == 1 and nostem:
                r = T(head_boxes[0])
                label(layer, d, "no stem decided", (r[0] - 4, r[3] + 24), BLUE, font(23, True), placed)
            elif nostem:
                label(layer, d, "no stem decided for: " + ", ".join(str(h["n"]) for h in nostem),
                      (8, 6), BLUE, font(23, True), placed)
        # the brackets (both panels)
        for i, hb in enumerate(head_boxes, 1):
            r = T(hb)
            bracket(d, r, RED + (255,))
            if len(keys) > 1:
                f_ = font(30, True)
                nw_ = d.textlength(str(i), font=f_)
                tx, ty = r[0] - nw_ - 10, (r[1] + r[3]) / 2 - 18
                d.text((tx, ty), str(i), fill=RED + (255,), font=f_, stroke_width=3, stroke_fill=(255, 255, 255, 255))
        im = Image.alpha_composite(im, layer).convert("RGB")
        return im

    top, bottom = panel(False), panel(True)
    # ---- frame control (can fail) ----
    # Everything drawn is placed by the head's own canonical->page map, so the control is whether the drawn
    # boxes land on INK: (1) each bracketed head's box holds the ink of a head, and holds more than the same box
    # moved diagonally by 1.6 head widths in the four directions; (2) the same for every stroke box drawn; the
    # moved copy is the control that must lose. The record's GLOBAL staff lines are compared with the LOCAL ones
    # read off this crop's own ink (a scanned staff tilts and wanders: CLAUDE.md §10) and the offset is reported;
    # the facts below that use staff lines use the LOCAL ones.
    gray = page_img.mean(axis=2)
    xa_, xb_ = int(max(0, X0)), int(min(W, X1))
    local, offset_sp = local_lines(gray, lines, sp, xa_, xb_)

    def ink_in(b):
        x0_, y0_, x1_, y1_ = [int(round(v)) for v in b]
        x0_, y0_ = max(0, x0_), max(0, y0_)
        x1_, y1_ = min(W, x1_), min(H, y1_)
        if x1_ <= x0_ or y1_ <= y0_:
            return 0.0
        return float((255.0 - gray[y0_:y1_, x0_:x1_]).mean() / 255.0)

    def moved(b, f=1.6):
        w_, h_ = b[2] - b[0], b[3] - b[1]
        return [[b[0] + dx * f * w_, b[1] + dy * f * h_, b[2] + dx * f * w_, b[3] + dy * f * h_]
                for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1))]
    h_true = [ink_in(b) for b in head_boxes]
    h_moved = [float(np.mean([ink_in(m) for m in moved(b)])) for b in head_boxes]
    s_boxes = [F.box(R.strokes[cell][sid]["box"]) for sid in strokes_drawn]
    s_true = [ink_in(b) for b in s_boxes]
    s_moved = [float(np.mean([ink_in(m) for m in moved(b, 1.0)])) for b in s_boxes]
    fc = {"heads_ink_inside_bracket": [round(v, 3) for v in h_true],
          "same_boxes_moved_diagonally": [round(v, 3) for v in h_moved],
          "stroke_boxes_ink_inside": [round(v, 3) for v in s_true],
          "stroke_boxes_moved_diagonally": [round(v, 3) for v in s_moved],
          "record_staff_lines_vs_local_ink_spaces": offset_sp,
          "map_drift_px": round(drift, 2)}
    # the stroke-box numbers are INFORMATION, not a gate: a detector box is loose around its stroke, and a
    # moved copy can land on a neighbour's ink; the bracketed heads are what must sit on ink
    fc["ok"] = bool(all(t > 0.25 and t > 1.5 * m for t, m in zip(h_true, h_moved)) and drift < 3.0)
    record_lines = list(lines)
    lines = local                          # every staff-line fact below is measured against the LOCAL lines
    # ---- the sheet ----
    printed = item["printed"]
    reads = [reading_text(h["verdict"]) for h in head_info]
    uniq = list(dict.fromkeys(reads))
    if len(uniq) == 1:
        we = uniq[0] + ", left undecided" if head_info[0]["verdict"]["outcome"] == "narrowed" else uniq[0]
    else:
        we = "; ".join(f"{u} ({','.join(str(i + 1) for i, r in enumerate(reads) if r == u)})" for u in uniq)
    later = item.get("later")
    if later:
        we += f"; bar math later settled it: {later}"
    if item["kind"] == "hand-truth-unboxed-flag":
        printed += " (a printed flag his page has no box for)"
    elif item["kind"].startswith("hand-truth"):
        printed += " (his boxes)"
    head_line = f"Printed: {printed}. We read: {we}"
    where = (f"{NAMES[item['movement']]}, pdf index {item['page']}, system {keys[0].split('/')[2]}, "
             f"staff {keys[0].split('/')[3]}, bar cell {keys[0].split('/')[4]}")
    src = {"tile": f"Sean's tile {item.get('tile', '')[5:]}", "hand-truth-beam": "hand-truth page, beamed group",
           "hand-truth-flag": "hand-truth page, flagged eighth", "hand-truth-unboxed-flag": "hand-truth page: the flag it does not box"}[item["kind"]]
    pad = 14
    HEAD_H = 138
    cap_h = 34
    info_lines = []
    for h in head_info:
        stem_txt = ("stem we attached: " + (f"{h['stem_length_spaces']} sp long" if h.get("stem_length_spaces") else "yes")
                    if h["stem_decided"] else "no stem decided")
        info_lines.append((f"{h['n']}. " if len(keys) > 1 else "") + f"{stem_txt}; tip: {h['tip_state']}")
    hk = R.heads[keys[0]]
    ink = R.head_ink.get(keys[0]) or {}
    head_fact = f"Head: detector class {hk['cls']}"
    if ink.get("center") is not None:
        head_fact += f"; ink centre {ink['center']:.2f}, ring {ink['ring']:.2f}"
    info_lines.insert(0, head_fact)
    if strokes_off:
        ws = collections.Counter(WORDS.get(v["story"]["why"], v["story"]["why"]) for v in strokes_off.values())
        info_lines.append("Also considered, off this picture: " + "; ".join(f"{n} x {w}" for w, n in ws.items()))
    legend = [(RED, "the note"), (GREEN, "beam we kept"), (ORANGE, "stroke refused as a beam + why"),
              (BLUE, "stem we attached"), (TEAL, "tip window (dotted)"), (MAGENTA, "flag box")]
    info_h = 8 + 30 * len(info_lines) + 8
    leg_h = 12 + 34 * 3 + 6
    total_h = HEAD_H + cap_h + ph + cap_h + ph + info_h + leg_h
    sheet = Image.new("RGB", (WIDTH, total_h), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    # header: big number, one line
    d.rectangle((0, 0, WIDTH, HEAD_H), fill=(32, 32, 40))
    d.ellipse((16, 14, 16 + 110, 14 + 110), fill=RED)
    nf = font(78, True)
    nw = d.textlength(str(n), font=nf)
    d.text((16 + 55 - nw / 2, 14 + 55 - 47), str(n), fill=(255, 255, 255), font=nf)
    tf = fit_text(d, head_line, WIDTH - 150 - 12, 32, bold=True, min_size=19)
    d.text((142, 24), head_line, fill=(255, 255, 255), font=tf)
    wf = fit_text(d, where, WIDTH - 150 - 12, 22, min_size=15)
    d.text((142, 74), where, fill=(200, 200, 210), font=wf)
    d.text((142, 104), src, fill=(255, 190, 90), font=font(22, True))
    y = HEAD_H
    d.rectangle((0, y, WIDTH, y + cap_h), fill=(235, 235, 235))
    d.text((12, y + 3), "THE PRINT (the red bracket marks the note)", fill=(20, 20, 20), font=font(24, True))
    sheet.paste(top, (0, y + cap_h))
    y += cap_h + ph
    d.rectangle((0, y, WIDTH, y + cap_h), fill=(235, 235, 235))
    d.text((12, y + 3), "WHAT WE READ", fill=(20, 20, 20), font=font(24, True))
    sheet.paste(bottom, (0, y + cap_h))
    y += cap_h + ph
    y += 8
    for ln in info_lines:
        lf = fit_text(d, ln, WIDTH - 24, 24, min_size=15)
        d.text((12, y), ln, fill=(30, 30, 30), font=lf)
        y += 30
    y += 8
    # legend (baked in), 2 columns
    for i, (c, t) in enumerate(legend):
        col, row = i % 2, i // 2
        x0, y0 = 12 + col * 500, y + row * 34
        sw = (x0, y0 + 6, x0 + 30, y0 + 28)
        if "dotted" in t:
            dashed_rect(d, sw, c, 3)
        else:
            d.rectangle(sw, outline=c, width=4)
        d.text((x0 + 38, y0 + 2), t, fill=(30, 30, 30), font=font(22))
    path = ctx["out"] / f"miss_{n:02d}.png"
    sheet.save(path, optimize=True)
    rec = {"image": n, "file": path.name, "kind": item["kind"], "tile": item.get("tile"), "printed": item["printed"],
           "we_read": we, "movement": item["movement"], "pdf_page": item["page"],
           "crop_page_px": [X0, Y0, X1, Y1], "scale": round(scale, 3), "frame_control": fc,
           "heads": head_info, "strokes_drawn": strokes_drawn_summary(strokes_drawn, R, F, head_boxes, lines, sp),
           "strokes_off_the_picture": strokes_drawn_summary(strokes_off, R, F, head_boxes, lines, sp),
           "windows": [{"rect": [round(v, 1) for v in w["rect"]], "read": w["read"]} for w in windows],
           "flag_boxes": [{"cls": f["cls"], "page": [round(v, 1) for v in f["page"]]} for f in flags_drawn],
           "truth_boxes": {k: [[round(v, 1) for v in r] for r in vs] for k, vs in truth_boxes.items()},
           "staff": {"local_lines": [round(l, 1) for l in lines], "record_lines": [round(l, 1) for l in record_lines],
                     "space_px": round(sp, 2)}}
    return rec, {"R": R, "F": F, "lines": lines, "sp": sp, "head_boxes": head_boxes, "truth_boxes": truth_boxes,
                 "cell": cell, "staff": staff}


def strokes_drawn_summary(strokes_drawn, R, F, head_boxes, lines, sp):
    out = []
    hb = head_boxes[0]
    for sid, s in strokes_drawn.items():
        f = stroke_facts(R, F, sid, s["story"], hb, lines, sp)
        f["for_heads"] = s["heads"]
        out.append(f)
    return out


def bars_text(R, key):
    p = key.split("/")
    cells = sorted(R.cells_of_staff["staff/" + "/".join(p[1:4])])
    return cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--scored", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--only", default=None, help="comma list of image numbers (debugging)")
    a = ap.parse_args()
    scratch = Path(a.scratch)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items = ML.all_items(a.scored)
    scored = {r["key"]: r for r in json.loads(Path(a.scored).read_text())}
    man = json.loads((ML.REVIEW / "manifest.json").read_text())
    tile_hidden = {t["id"]: t["hidden"] for t in man["tiles"]}
    truth = Truth()
    from tools.omr.preprocessing import render_page
    rows, pages = {}, {}
    manifest = {"question": "every miss of the 2.81 bare-stem rule, in context", "images": []}
    only = {int(x) for x in a.only.split(",")} if a.only else None
    for n, item in enumerate(items, 1):
        if only and n not in only:
            continue
        mv, pg = item["movement"], item["page"]
        if mv not in rows:
            rows[mv] = Rows(scratch / f"rows-{mv}.json")      # every page asked, indexed once per movement
        R = rows[mv]
        cap = json.loads((scratch / f"cap-{mv}-p{pg}.json").read_text())
        if (mv, pg) not in pages:
            pages[(mv, pg)] = render_page(PDFS[mv], pg, dpi=600).rgb if not (a.cache and mv == "brahms" and pg == 0
                                                                              and Path(a.cache).exists()) \
                else np.load(a.cache)
            if a.cache and mv == "brahms" and pg == 0 and not Path(a.cache).exists():
                np.save(a.cache, pages[(mv, pg)])
        # the later stage (tiles: the manifest; hand-truth members: the scored row)
        if item["kind"] == "tile":
            ls = tile_hidden[item["tile"]]["later_stages"]
            if ls.get("outcome") == "decided":
                w = ls.get("written")
                item["later"] = VALUE_NAME.get(round(float(w), 4), str(w)) if w is not None else "decided"
        rec, ctx2 = process(item, n, R, cap, pages[(mv, pg)], truth if mv == "brahms" and pg == 0 else None,
                            {"out": out})
        rec["items"] = {k: v for k, v in item.items() if k not in ("keys",)}
        # bars: where in the system, and the printed bar number where the page's first system makes it known
        cells = bars_text(R, item["keys"][0])
        c = int(item["keys"][0].split("/")[4])
        rec["bar"] = {"cell": c, "bars_in_system_incl_header_cell": len(cells),
                      "printed_bar": c if (mv == "brahms" and pg == 0 and item["keys"][0].split("/")[2] == "0") else None}
        # the beam that was MISSED, from Sean's boxes where they exist
        rec["missed_beam"] = missed_beam_facts(rec, ctx2, truth, R) if truth is not None else None
        manifest["images"].append(rec)
        print(f"miss_{n:02d}: {item['kind']} {item.get('tile', item.get('cell'))} frame control "
              f"{'ok' if rec['frame_control']['ok'] else 'FAILED'} {rec['frame_control']}", flush=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    write_table(manifest, out / "table.txt")
    bad = [m["image"] for m in manifest["images"] if not m["frame_control"]["ok"]]
    print("frame control failed on:", bad or "none")


def missed_beam_facts(rec, ctx, truth, R):
    """Measured facts of the beam(s) / flag(s) on Sean's page that the rule missed (page px)."""
    out = {"beams": [], "flags": []}
    lines, sp, hbs = ctx["lines"], ctx["sp"], ctx["head_boxes"]
    hy = sum((b[1] + b[3]) / 2 for b in hbs) / len(hbs)
    strokes = [(s["stroke"], s["page_box"], s) for s in rec["strokes_drawn"]]
    for r in ctx["truth_boxes"]["beam"]:
        cy_ = (r[1] + r[3]) / 2
        inside = [l for l in lines if r[1] <= l <= r[3]]
        # the record stroke that lies on it (IoU)
        best, bi = None, 0.0
        for sid, pb, s in strokes:
            ix = max(0.0, min(r[2], pb[2]) - max(r[0], pb[0]))
            iy = max(0.0, min(r[3], pb[3]) - max(r[1], pb[1]))
            u = (r[2] - r[0]) * (r[3] - r[1]) + (pb[2] - pb[0]) * (pb[3] - pb[1]) - ix * iy
            iou = ix * iy / u if u else 0.0
            if iou > bi:
                best, bi = s, iou
        thick = None
        if best and best.get("thickness_ratio") and best.get("height_spaces") is not None:
            pass
        w_sp, h_sp = (r[2] - r[0]) / sp, (r[3] - r[1]) / sp
        slope = math.degrees(math.atan2(max(0.0, (r[3] - r[1]) - 0.5 * sp), r[2] - r[0]))
        dist = min(abs(cy_ - l) for l in lines)
        # staff-line coincidence at the beam's two ends (the box's left and right quarter): does a line
        # pass through the box at the end where the stems stand?
        out["beams"].append({
            "side": "under the heads" if cy_ > hy else "over the heads",
            "width_spaces": round(w_sp, 2), "height_spaces": round(h_sp, 2),
            "slope_deg_est_(box_height_minus_half_a_space)": round(slope, 1),
            "own_staff_lines_inside_its_box": len(inside),
            "centre_to_nearest_staff_line_spaces": round(dist / sp, 2),
            "on_a_staff_line": dist <= 0.25 * sp,
            "centre_vs_staff": ("inside the staff" if lines[0] <= cy_ <= lines[-1] else
                                f"{round((cy_ - lines[-1]) / sp, 1)} sp below the staff" if cy_ > lines[-1] else
                                f"{round((lines[0] - cy_) / sp, 1)} sp above the staff"),
            "record_stroke_on_it": None if best is None else {"stroke": best["stroke"], "iou": round(bi, 2),
                                                               "refused_by": best["refused_by"],
                                                               "thickness_ratio": best["thickness_ratio"]},
            "page_box": [round(v, 1) for v in r]})
    for r in ctx["truth_boxes"]["flag"]:
        out["flags"].append({"page_box": [round(v, 1) for v in r],
                             "centre_vs_staff": ("inside the staff" if lines[0] <= (r[1] + r[3]) / 2 <= lines[-1] else
                                                 "below the staff" if (r[1] + r[3]) / 2 > lines[-1] else "above the staff")})
    return out


def write_table_per_head(manifest, path):
    """(superseded by `write_table`, kept for one-line-per-head diffs)"""
    L = []
    for m in manifest["images"]:
        for h in m["heads"]:
            sts = [s for s in m["strokes_drawn"] + m["strokes_off_the_picture"] if h["n"] in s["for_heads"]]
            ref = "; ".join(f"{s['word']}" + (f" [{s['thickness_vs_cut']}]" if s["thickness_vs_cut"] else "") +
                            (f" [bow {s['bow_spaces']:.2f} sp]" if s["refused_by"] == "not_straight" and s["bow_spaces"] is not None else "")
                            for s in sts) or "(no stroke considered)"
            L.append(f"image {m['image']:>2}  {'tile ' + m['tile'][5:] if m['tile'] else 'hand-truth':<11} "
                     f"{m['movement']:<7} p{m['pdf_page']:<2} sys {h['key'].split('/')[2]} staff {h['key'].split('/')[3]:>2} "
                     f"bar-cell {h['key'].split('/')[4]:>2} head {h['key'].split('/')[5]:>2} #{h['n']}  printed: {m['printed']}")
            L.append(f"          tip: {h['tip_state']}; stem decided: {'yes' if h['stem_decided'] else 'no (' + str((h['head_stem'] or {}).get('reason')) + ')'}"
                     f"; our reading: {m['we_read']}")
            L.append(f"          strokes: {ref}")
            for s in sts:
                L.append(f"             - {s['reader']:8s} {s['word']:<28s} ratio {s['thickness_ratio']} bow {s['bow_spaces']} "
                         f"stems-at-ends {s['stems_at_its_ends']} {s['width_spaces']}x{s['height_spaces']} sp "
                         f"slope~{s['slope_deg_est']} {s['over_or_under_the_heads']} the heads "
                         f"({s['centre_vs_head_spaces']:+} sp) lines-in-box {s['own_staff_lines_inside_its_box']} "
                         f"nearest-line {s['centre_to_nearest_line_spaces']} sp {'ON A LINE' if s['on_a_staff_line'] else ''}")
            if m.get("missed_beam"):
                for b in m["missed_beam"]["beams"]:
                    L.append(f"          his beam: {b['side']}; {b['width_spaces']}x{b['height_spaces']} sp; slope~"
                             f"{b['slope_deg_est_(box_height_minus_half_a_space)']} deg; {b['centre_vs_staff']}; "
                             f"lines in its box {b['own_staff_lines_inside_its_box']}; nearest line "
                             f"{b['centre_to_nearest_staff_line_spaces']} sp {'(ON A LINE)' if b['on_a_staff_line'] else ''}; "
                             f"record stroke on it: {b['record_stroke_on_it']}")
                for f in m["missed_beam"]["flags"]:
                    L.append(f"          his flag box: {f['centre_vs_staff']} {f['page_box']}")
    path.write_text("\n".join(L) + "\n")


def write_table(manifest, path):
    """The manager's table, ONE BLOCK PER IMAGE: MEASURED FACTS ONLY, no conclusion. Where a bar's heads share
    their strokes (a beam group) the strokes are listed once."""
    L = ["MEASURED FACTS of every miss of the 2.81 bare-stem rule. No conclusion is drawn here.",
         "tip: what Q.STEM_TIP_INK said at the end of the stem we attached; stem: Q.HEAD_STEM; strokes: every Q.BEAM_STROKE",
         "the head's duration verdict considered (CV or detector box), the test that refused it, its ink reading",
         "(thickness as a multiple of the staff line's own thickness at its columns, 2.74's cut is 1.75; bow in spaces,",
         "limit 0.40; a stem found at its left / right end), its box (width x height in staff spaces), a slope estimated",
         "from the box (box height less the measured thickness, over its width), where its centre sits against the heads",
         "(+ = below) and against the LOCAL staff lines (read off the print at the crop, not the record's global ones).",
         "bar-cell = the record's cell index in the system (cell 0 is the clef/key header; on Brahms pdf 0 system 0 it is",
         "the printed bar number).", ""]
    for m in manifest["images"]:
        h0 = m["heads"][0]["key"].split("/")
        who = f"tile {m['tile'][5:]}" if m["tile"] else "hand-truth"
        L.append(f"=== image {m['image']:>2}  {who}  {m['movement']} pdf {m['pdf_page']}  system {h0[2]}  staff {h0[3]}  "
                 f"bar-cell {h0[4]} of {m['bar']['bars_in_system_incl_header_cell']}"
                 + (f" (printed bar {m['bar']['printed_bar']})" if m['bar'].get('printed_bar') is not None else "")
                 + f"   printed: {m['printed']}   we read: {m['we_read']}")
        fcx = m["frame_control"]
        L.append(f"    frame control: heads' ink inside the bracket {fcx['heads_ink_inside_bracket']} vs moved "
                 f"{fcx['same_boxes_moved_diagonally']}; record staff lines vs local ink {fcx['record_staff_lines_vs_local_ink_spaces']} sp")
        for h in m["heads"]:
            hs = h["head_stem"] or {}
            tp = h.get("tip") or {}
            dens = (f" (right band {tp['right']}, left band {tp['left']}; flag if right >= 0.30 and left <= 0.20)"
                    if tp.get("right") is not None else "")
            hd = h["head"]
            L.append(f"    head #{h['n']:<2} {h['key']}  {hd['class']}, box {hd['box_spaces'][0]}x{hd['box_spaces'][1]} sp, "
                     f"ink centre {hd['ink_center']} ring {hd['ink_ring']}")
            L.append(f"             tip: {h['tip_state']}{dens}  | stem: "
                     + (f"decided, {h.get('stem_length_spaces')} sp long" if h["stem_decided"]
                        else f"not decided ({hs.get('outcome')}: {hs.get('reason')})")
                     + f"  | nearest candidate stroke to the stem tip: {h.get('nearest_stroke_to_stem_tip_spaces')} sp"
                     f"  | direction used: {h['detail'].get('beam_side')}  | counters: ink-refused "
                     f"{h['detail'].get('beams_not_by_ink')} {h['detail'].get('beams_not_by_ink_why')}, arc "
                     f"{h['detail'].get('beams_decided_arc')}, neighbour {h['detail'].get('beams_neighbour_staff')}, "
                     f"far side {h['detail'].get('beams_far_side')}")
        if m["flag_boxes"]:
            L.append("    detector flag boxes near: " + "; ".join(f"{f['cls']} {f['page']}" for f in m["flag_boxes"]))
        else:
            L.append("    detector flag boxes near: none")
        for where, group in (("", m["strokes_drawn"]), (" (off the picture)", m["strokes_off_the_picture"])):
            for s in group:
                t = f" ratio {s['thickness_ratio']:.2f}" if s["thickness_ratio"] is not None else ""
                L.append(f"    stroke{where} {s['reader']:8s} for heads {s['for_heads']}: {s['word']}"
                         + (f" [{s['thickness_vs_cut']}]" if s["thickness_vs_cut"] else "")
                         + f" |{t} bow {s['bow_spaces']} stems-at-ends {s['stems_at_its_ends']} | "
                         f"{s['width_spaces']}x{s['height_spaces']} sp, slope~{s['slope_deg_est']} deg, "
                         f"{s['over_or_under_the_heads']} the heads ({s['centre_vs_head_spaces']:+} sp) | local staff lines inside its box "
                         f"{s['own_staff_lines_inside_its_box']}, centre {s['centre_to_nearest_line_spaces']} sp from the nearest"
                         + (" (ON A LINE)" if s["on_a_staff_line"] else ""))
        if not m["strokes_drawn"] and not m["strokes_off_the_picture"]:
            L.append("    strokes: none was a candidate")
        mb = m.get("missed_beam")
        if mb:
            for b in mb["beams"]:
                rs = b["record_stroke_on_it"]
                L.append(f"    HIS BEAM (hand truth): {b['side']}; {b['width_spaces']}x{b['height_spaces']} sp; slope~"
                         f"{b['slope_deg_est_(box_height_minus_half_a_space)']} deg; {b['centre_vs_staff']}; local staff lines inside its "
                         f"box {b['own_staff_lines_inside_its_box']}; centre {b['centre_to_nearest_staff_line_spaces']} sp from the "
                         f"nearest line" + (" (ON A LINE)" if b["on_a_staff_line"] else "")
                         + ("; no record stroke overlaps it" if rs is None or rs["iou"] < 0.05 else
                            f"; the record stroke on it ({rs['stroke']}, IoU {rs['iou']}) was refused: {rs['refused_by']}")
                         + (f" [best IoU {rs['iou']}]" if rs and rs["iou"] < 0.05 else ""))
            for f in mb["flags"]:
                L.append(f"    HIS FLAG BOX (hand truth): {f['centre_vs_staff']} {f['page_box']}")
        L.append("")
    path.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
