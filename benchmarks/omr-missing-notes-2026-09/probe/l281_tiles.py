#!/usr/bin/env python3
"""l281_tiles: cut the blind tiles for Sean -- ROADMAP 2.81 Phase 1, measure (b).

QUESTION on every tile: *what is the printed value of the note in the red brackets?*
Nothing of ours is drawn but the corner bracket on the head: no box, no stem line, no
candidate. Our reading (and every other hidden field) is in `manifest.json` only.

THE SAMPLE (fixed seed, recorded in the manifest). Frame = the 2.81 population (see
`l281_population.py`) of the two overnight records `*-mvt1-whole-20261010-night`, MINUS Brahms
PDF page 0 (the hand-truth page: it already has an answer, and a tile drawn from it would be a
second reading of the same ink). Two strata, each drawn at random, so the rule's candidate subset
is not diluted by the rest of the population:

  A  the candidate rule's subset: the head's stem is DECIDED, `Q.STEM_TIP_INK` reads the tip
     window clean, and NO `Q.BEAM_STROKE` box (CV or detector, refused or not) stands at the
     stem's tip end (`l281_population.stroke_at_tip`)            -> 14 Brahms + 6 Litolff
  B  every other member of the population (no decided stem, window occupied, a stroke at the
     tip, a hook seen)                                              ->  6 Brahms + 4 Litolff

`--controls N` adds control tiles from the hand-truth page (Brahms p0), named `control_*`, that
Sean has an answer for in his own boxes: heads his boxes show BEAMED (the answer is not a quarter)
and heads his boxes show BARE (the answer is a quarter or dotted quarter). A pipeline that cannot
tell them apart -- or a reader who sees the same on both -- shows up here.

THE CUT. 600 dpi, `preprocessing.render_page` (the deskewed raster GATHER read), normalised so a
staff space is 32 px on every plate (Litolff is ~15 px/space natively). The window is 12 spaces
wide and tall enough to hold the head's whole stem (read off the record's own `Q.STEM` row) and a
space and a half beyond its far end, where a flag or a beam hangs; a head with no stem gets 14
spaces.

FRAME CONTROL (a control that can fail): for every tile the mean darkness inside the head's box is
compared with the same box moved 1.6 head-widths right and left. True must beat both. The same
measure is then run with the page raster SHIFTED 1.6 head-widths (a deliberately wrong frame): it
must fail on most tiles, or the control cannot tell a right frame from a wrong one.

    python3 l281_tiles.py --ext DIR --out OUT_DIR [--seed 20261010] [--controls 4]
"""
import argparse
import collections
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_population import build, standing  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

SEED = 20261010
QUESTION = "What is the printed value of the note in the red brackets?"
PLAN = {"A": {"brahms": 14, "litolff": 6}, "B": {"brahms": 6, "litolff": 4}}
TILE_SP = 32.0          # normalised staff space, px
HALF_W_SP = 6.0         # half window width, spaces
MIN_HALF_H_SP = 7.0
STEM_PAD_SP = 1.6

PDFS = {
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}


def stratum(m):
    if m["tip"] == "clean" and m["at_tip"] is False:
        return "A"
    return "B"


def canon_to_page(head, box):
    """The linear map that the head's own two boxes (canonical `[x, y, w, h]` and page corners)
    define, applied to another canonical `[x, y, w, h]` box. Both axes separately."""
    cx, cy, cw, ch = head["canon"]
    px0, py0, px1, py1 = head["page"]
    ax, ay = (px1 - px0) / float(cw), (py1 - py0) / float(ch)
    x, y, w, h = box
    return [px0 + (x - cx) * ax, py0 + (y - cy) * ay, px0 + (x + w - cx) * ax, py0 + (y + h - cy) * ay]


def space_px(d, head, key):
    cell = "cell/" + "/".join(key.split("/")[1:5])
    sp = d["obs"]["space"].get(cell)
    if not sp:
        return None
    cx, cy, cw, ch = head["canon"]
    px0, py0, px1, py1 = head["page"]
    return float(sp) * (px1 - px0) / float(cw)


def stem_page_box(d, key, head):
    rows = d["ver"]["verdicts"].get(key, [])
    hs = standing(rows, Q.HEAD_STEM, "ADJUDICATE")
    if hs is None or hs["outcome"] != "decided" or not hs.get("value"):
        return None
    cell = "cell/" + "/".join(key.split("/")[1:5])
    box = (d["obs"]["stems"].get(cell) or {}).get(hs["value"])
    if not box:
        return None
    return canon_to_page(head, box)


def window(head_box, sp, stem_box):
    x0, y0, x1, y1 = head_box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    X0, X1 = cx - HALF_W_SP * sp, cx + HALF_W_SP * sp
    if stem_box:
        top = min(y0, stem_box[1]) - STEM_PAD_SP * sp
        bot = max(y1, stem_box[3]) + STEM_PAD_SP * sp
        # keep the head clear of the window's edge and the window at least 9 spaces tall
        mid = (top + bot) / 2.0
        half = max((bot - top) / 2.0, 4.5 * sp)
        Y0, Y1 = mid - half, mid + half
    else:
        Y0, Y1 = cy - 7.0 * sp, cy + 7.0 * sp
    return int(X0), int(Y0), int(X1), int(Y1)


def cut(img, head_box, sp, stem_box, caption=None):
    X0, Y0, X1, Y1 = window(head_box, sp, stem_box)
    H, W = img.shape[:2]
    crop = np.full((Y1 - Y0, X1 - X0, 3), 255, np.uint8)
    xa, ya, xb, yb = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
    if xb > xa and yb > ya:
        crop[ya - Y0:yb - Y0, xa - X0:xb - X0] = img[ya:yb, xa:xb]
    f = TILE_SP / sp
    # the bracket is drawn AFTER normalising, so its stroke is the same on every tile
    crop = cv2.resize(crop, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC if f > 1 else cv2.INTER_AREA)
    bx0, by0 = (head_box[0] - X0) * f, (head_box[1] - Y0) * f
    bx1, by1 = (head_box[2] - X0) * f, (head_box[3] - Y0) * f
    pad, arm, t = 3, 11, 3
    bx0, by0, bx1, by1 = int(bx0 - pad), int(by0 - pad), int(bx1 + pad), int(by1 + pad)
    red = (220, 30, 30)
    for (x, y, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        cv2.line(crop, (x, y), (x + dx * arm, y), red, t)
        cv2.line(crop, (x, y), (x, y + dy * arm), red, t)
    return crop, (X0, Y0, X1, Y1)


def ink_in(gray, box):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    H, W = gray.shape
    x0, x1, y0, y1 = max(0, x0), min(W, x1), max(0, y0), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return None
    return float((255.0 - gray[y0:y1, x0:x1]).mean() / 255.0)


def frame_control(gray, head_box, shift_px=0):
    """(true, left, right) mean darkness: the head's box, and the box moved 1.6 head-widths either way.
    `shift_px` shifts the PAGE under the box (the deliberately wrong frame)."""
    x0, y0, x1, y1 = head_box
    w = x1 - x0
    s = shift_px
    t = ink_in(gray, (x0 + s, y0, x1 + s, y1))
    l = ink_in(gray, (x0 - 1.6 * w + s, y0, x1 - 1.6 * w + s, y1))
    r = ink_in(gray, (x0 + 1.6 * w + s, y0, x1 + 1.6 * w + s, y1))
    return t, l, r


def draw(pop, seed):
    rng = random.Random(seed)
    chosen = []
    sizes = {}
    for mv in ("brahms", "litolff"):
        members = [m for m in pop[mv] if m["page_box"] and not (mv == "brahms" and m["page"] == 0)]
        members.sort(key=lambda m: m["key"])
        for s in ("A", "B"):
            frame = [m for m in members if stratum(m) == s]
            sizes[(mv, s)] = len(frame)
            k = min(PLAN[s][mv], len(frame))
            for m in rng.sample(frame, k):
                chosen.append((mv, s, m))
    rng.shuffle(chosen)
    return chosen, sizes


def pick_controls(scored, seed, n):
    """n control members from the hand-truth page: half judged BARE by his boxes (`right`), half BEAMED
    (`wrong_beam`), at random from the clean-window / no-stroke / no-stem mix the sample itself holds."""
    rng = random.Random(seed + 1)
    bare = sorted([r for r in scored if r["judge"] == "right" and r["key"] != "glyph/0/0/9/2/2"],
                  key=lambda r: r["key"])
    beamed = sorted([r for r in scored if r["judge"] == "wrong_beam"], key=lambda r: r["key"])
    out = []
    for r in rng.sample(beamed, n // 2):
        out.append(("beamed", r))
    for r in rng.sample(bare, n - n // 2):
        out.append(("bare", r))
    rng.shuffle(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--controls", type=int, default=4)
    ap.add_argument("--scored", default=None, help="l281_score.py --json of the quick record (for the controls)")
    ap.add_argument("--tags", default="brahms,litolff")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    data, pop = {}, {}
    for tag in a.tags.split(","):
        data[tag], pop[tag], _n, _sc = build(a.ext, tag)
    chosen, sizes = draw(pop, a.seed)
    print("frame sizes:", {f"{k[0]}/{k[1]}": v for k, v in sizes.items()})
    print("drawn:", collections.Counter((mv, s) for mv, s, _m in chosen))

    from tools.omr.preprocessing import render_page
    rendered = {}

    def page_img(mv, page):
        k = (mv, page)
        if k not in rendered:
            if len(rendered) > 3:
                rendered.pop(next(iter(rendered)))
            rendered[k] = render_page(PDFS[mv], page, dpi=600).rgb
        return rendered[k]

    items = []
    for i, (mv, s, m) in enumerate(chosen):
        items.append({"kind": "sample", "mv": mv, "stratum": s, "m": m, "d": data[mv]})
    if a.controls:
        scored = json.loads(Path(a.scored).read_text())
        quick = data.get("bquick")
        if quick is None:
            data["bquick"], _p, _n, _s = build(a.ext, "bquick")
            quick = data["bquick"]
        for kind, r in pick_controls(scored, a.seed, a.controls):
            items.append({"kind": "control", "mv": "brahms", "control": kind, "r": r, "d": quick})

    order = list(range(len(items)))
    random.Random(a.seed + 2).shuffle(order)
    manifest = {"question": QUESTION, "seed": a.seed, "plan": PLAN,
                "frame_sizes": {f"{k[0]}/{k[1]}": v for k, v in sizes.items()},
                "excluded": "Brahms pdf page 0 (the hand-truth page) from the sample frame",
                "tile_scale": f"{TILE_SP:.0f} px per staff space on every tile (600 dpi page, normalised)",
                "tiles": []}
    fc_true, fc_wrong = [], []
    n_s = n_c = 0
    for pos in order:
        it = items[pos]
        d = it["d"]
        if it["kind"] == "sample":
            m = it["m"]
            key, box, page, mv = m["key"], m["page_box"], m["page"], it["mv"]
            head = d["obs"]["heads"][key]
            sp = space_px(d, head, key)
            stem = stem_page_box(d, key, head)
            n_s += 1
            tid = f"tile_{n_s:02d}"
            hidden = {
                "key": key, "movement": mv, "pdf_page": page, "stratum": it["stratum"],
                "tip_status": m["tip"], "stroke_at_tip": m["at_tip"],
                "our_reading": "narrowed " + " | ".join(
                    f"beam_levels={c['beam_levels']} written={c['written']}" for c in (m["cands"] or [])),
                "dots_read": m["dots"], "ink_refusals": m["ink_why"],
                "later_stages": {"stage": m["final_stage"], "decider": m["final_decider"],
                                 "outcome": m["final_outcome"],
                                 "beam_levels": (m["final_value"] or {}).get("beam_levels")
                                 if isinstance(m["final_value"], dict) else None,
                                 "written": (m["final_value"] or {}).get("written")
                                 if isinstance(m["final_value"], dict) else None},
                "head_class": m["cls"], "head_box_page_px": box,
            }
        else:
            r = it["r"]
            key, box, page, mv = r["key"], r["page_box"], 0, "brahms"
            head = d["obs"]["heads"][key]
            sp = space_px(d, head, key)
            stem = stem_page_box(d, key, head)
            n_c += 1
            tid = f"control_{n_c}"
            hidden = {"key": key, "movement": mv, "pdf_page": 0, "control": it["control"],
                      "truth": {"rule": "Sean's hand-truth boxes (page 0): "
                                        + ("a beam or flag is on this head's stem: NOT a quarter"
                                           if it["control"] == "beamed"
                                           else "no beam or flag on its stem: a quarter / dotted quarter"),
                                "truth_levels": r.get("truth_levels"), "truth_dots": r.get("truth_dots"),
                                "truth_id": r.get("truth_id")},
                      "our_reading": "narrowed (see key)", "head_box_page_px": box}
        sp = sp or 32.0
        img = page_img(mv, page)
        crop, win = cut(img, box, sp, stem)
        cv2.imwrite(str(out / f"{tid}.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        gray = img.mean(axis=2)
        t, l, r_ = frame_control(gray, box)
        t_w, l_w, r_w = frame_control(gray, box, shift_px=int(1.6 * (box[2] - box[0])))
        fc_true.append((t, l, r_))
        fc_wrong.append((t_w, l_w, r_w))
        manifest["tiles"].append({"id": tid, "file": f"{tid}.png", "question": QUESTION,
                                  "kind": it["kind"], "hidden": hidden,
                                  "window_page_px": list(win), "space_px_native": round(sp, 2),
                                  "frame_control": {"inside": round(t, 3), "left": round(l, 3), "right": round(r_, 3)}})
    # frame control summary
    ok_true = sum(1 for t, l, r_ in fc_true if t is not None and t > (l or 0) and t > (r_ or 0))
    ok_wrong = sum(1 for t, l, r_ in fc_wrong if t is not None and t > (l or 0) and t > (r_ or 0))
    manifest["frame_control"] = {
        "n": len(fc_true), "true_frame_inside_beats_both_neighbours": ok_true,
        "wrong_frame_(page_shifted_1.6_heads)_inside_beats_both": ok_wrong,
        "reading": "the control can fail: it must pass on the true frame and mostly fail on the shifted one"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    # the sheet Sean's words go in (one value per tile): the input of `l281_tilescore.py`
    (out / "answers.template.json").write_text(json.dumps(
        {t["id"]: None for t in sorted(manifest["tiles"], key=lambda t: t["id"])}, indent=1) + "\n")
    (out / "frame_control.txt").write_text(json.dumps(manifest["frame_control"], indent=1) + "\n")
    print("frame control:", manifest["frame_control"])
    print("wrote", len(manifest["tiles"]), "tiles to", out)


if __name__ == "__main__":
    main()
