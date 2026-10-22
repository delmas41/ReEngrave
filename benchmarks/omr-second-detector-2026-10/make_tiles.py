"""ROADMAP 2.114 blind tiles for Sean: `out/print/2.114-second-detector/`.

One question per tile, *Hollow or black? (or: not a note)* (or: not a note). Phone-sized (12 staff spaces x 32 px = 384 px wide),
a big tile NUMBER, the print as printed and ONE red corner bracket on the subject box. NOTHING of ours is on a tile: no class, no verdict, no
colour of ours; what each detector called it and how the rule settled it is in manifest.json only (read it after he answers).

Subjects (cap 20, deterministic): the ON record's disagreements -- production's BLACK head under a second-detector HOLLOW box, and a hollow box
where production boxed NOTHING -- spread over both pages and over the settlements (READ hollow / NARROWED / black stands / settled by an older
rule / second-only narrowed / second-only refused), plus 2 CONTROLS of known answer (a head both detectors call hollow that Sean's truth
confirms; a black head Sean's truth confirms) so a careless reading shows.

usage: make_tiles.py score.json rec-lit-on.json rec-bra-on.json OUTDIR
"""
import collections
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402

CAP = 20
HDR = 56
QUESTION = "Hollow or black? (or: not a note)"
LIT = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRA = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
PAGES = {"litolff": (LIT, 1), "brahms": (BRA, 0)}


def staff_space_page(run, g):
    """Staff space in PAGE pixels: the cell's canonical space scaled by the glyph's own page/canonical box ratio."""
    sp = [o for o in run.observations if o["quantity"] == "cell_staff_space" and o["subject"] == g.cell_key]
    if not sp or g.box_page is None or g.box_canon is None:
        return None
    wc = g.box_canon[2] - g.box_canon[0]
    wp = g.box_page[2] - g.box_page[0]
    return float(sp[-1]["value"]) * (wp / wc) if wc > 0 else None


def pick(rows, n):
    """n rows spread evenly by position (page y, then x)."""
    rows = sorted(rows, key=lambda r: (r["y"], r["x"]))
    if len(rows) <= n:
        return rows
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)]


def main():
    score_p, lit_p, bra_p, out = sys.argv[1:5]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    runs = {"litolff": RO.load_run(lit_p), "brahms": RO.load_run(bra_p)}
    score = json.loads(Path(score_p).read_text())["arms"]["on"]
    rows = []
    for d in score["touched"]:
        if d["relation"] == "agrees":
            continue
        run = runs[d["doc"]]
        g = run.glyphs[d["key"]]
        if g.box_page is None:
            continue
        sp = staff_space_page(run, g)
        if not sp:
            continue
        rows.append({**d, "x": (g.box_page[0] + g.box_page[2]) / 2, "y": g.box_page[1], "rect": list(g.box_page), "sp": sp,
                     "group": f"{d['relation']} / {d['settled']}"})
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["doc"], r["group"])].append(r)
    keys = sorted(groups)
    n_ctrl = 2
    budget = CAP - n_ctrl
    per = max(1, budget // max(1, len(keys)))
    chosen = []
    for k in keys:
        chosen += pick(groups[k], per)
    # top up round-robin to the cap, biggest groups first
    rest = [r for k in sorted(keys, key=lambda k: -len(groups[k])) for r in groups[k] if r not in chosen]
    i = 0
    while len(chosen) < budget and i < len(rest):
        chosen.append(rest[i])
        i += 1
    chosen = chosen[:budget]
    # controls of known answer from the AGREE rows (hollow both) and a plain black production head from the hand truth
    ctrl = []
    agrees = [d for d in score["touched"] if d["relation"] == "agrees" and d["truth"] == "truth hollow head" and d["doc"] == "brahms"]
    if not agrees:
        agrees = [d for d in score["touched"] if d["relation"] == "agrees" and d["truth"] == "truth hollow head"]
    if agrees:
        d = agrees[len(agrees) // 2]
        run = runs[d["doc"]]
        g = run.glyphs[d["key"]]
        ctrl.append({**d, "x": 0, "y": 0, "rect": list(g.box_page), "sp": staff_space_page(run, g), "group": "CONTROL hollow (both detectors, truth hollow)",
                     "expected": "hollow"})
    from tools.omr.hand_truth import score as SC
    from tools.omr.hand_truth import store as ST
    page = ST.load(Path("data/hand-truth/pages/imslp317803/0.json"))
    run = runs["brahms"]
    blacks = [b for b in page.boxes if b.cls.startswith("noteheadBlack")]
    glyphs = [g for g in run.glyphs.values() if g.box_page is not None and (g.cls or "").startswith("noteheadBlack")
              and "second_hollow" not in {o["quantity"] for _, k, o in run.rows_at(g.key) if k == "observation"}]
    for b in blacks[len(blacks) // 3::max(1, len(blacks) // 3)]:
        gm = [g for g in glyphs if abs((g.box_page[0] + g.box_page[2]) / 2 - (b.rect[0] + b.rect[2]) / 2) < 6
              and abs((g.box_page[1] + g.box_page[3]) / 2 - (b.rect[1] + b.rect[3]) / 2) < 6 and staff_space_page(run, g)]
        if gm:
            g = gm[0]
            ctrl.append({"doc": "brahms", "key": g.key, "relation": "control", "settled": "-", "reason": "-", "truth": "truth BLACK head",
                         "x": 0, "y": 0, "rect": list(g.box_page), "sp": staff_space_page(run, g), "group": "CONTROL black (truth black, never touched)",
                         "expected": "black"})
            break
    items = chosen + ctrl[:n_ctrl]
    random.Random(20261013).shuffle(items)
    imgs = {}
    tiles = []
    for n, it in enumerate(items, 1):
        pdf, idx = PAGES[it["doc"]]
        if it["doc"] not in imgs:
            imgs[it["doc"]] = render_page(Path(pdf), idx, dpi=600).rgb
        img = imgs[it["doc"]]
        x0, y0, x1, y1 = it["rect"]
        sp = it["sp"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        half_w, half_h = 6 * sp, 6.5 * sp
        ax0, ay0 = int(max(0, cx - half_w)), int(max(0, cy - half_h))
        ax1, ay1 = int(min(img.shape[1], cx + half_w)), int(min(img.shape[0], cy + half_h))
        crop = img[ay0:ay1, ax0:ax1].copy()
        s = 32.0 / sp
        crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        bx0, by0, bx1, by1 = [int(round(v * s)) for v in (x0 - ax0, y0 - ay0, x1 - ax0, y1 - ay0)]
        L = 10
        for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            cv2.line(crop, (px, py), (px + dx * L, py), (220, 30, 30), 2)
            cv2.line(crop, (px, py), (px, py + dy * L), (220, 30, 30), 2)
        h, w = crop.shape[:2]
        canvas = np.full((h + HDR, max(w, 384), 3), 255, np.uint8)
        canvas[HDR:, :w] = crop
        cv2.putText(canvas, str(n), (10, HDR - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.9, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(canvas, QUESTION, (70 if n < 10 else 110, HDR - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (60, 60, 60), 1, cv2.LINE_AA)
        cv2.line(canvas, (0, HDR - 1), (canvas.shape[1], HDR - 1), (200, 200, 200), 1)
        f = out / f"tile_{n:02d}.png"
        cv2.imwrite(str(f), cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR))
        tiles.append({"n": n, "file": f.name, "question": QUESTION, "hidden": {k: it[k] for k in it if k not in ("x", "y", "sp")},
                      "page_box_600dpi": [round(v) for v in it["rect"]], "dpi": 600})
    (out / "manifest.json").write_text(json.dumps({"question": QUESTION, "tile_scale": "32 px per staff space", "tiles": tiles}, indent=1))
    (out / "answers.template.json").write_text(json.dumps({f"tile_{t['n']:02d}": None for t in tiles}, indent=1))
    print(f"{len(tiles)} tiles -> {out}; groups: {collections.Counter(t['hidden']['group'] for t in tiles)}")


main()
