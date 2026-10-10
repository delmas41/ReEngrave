#!/usr/bin/env python3
"""l283_tiles: the blind tiles for Sean -- ROADMAP 2.83, same style as `out/print/2.81-review/`.

QUESTION on every tile: *What is the printed value of the note in the red brackets?* Nothing of ours is drawn but a red corner
bracket on the head. Our reading (BASE and ARM) and every other hidden field is in `manifest.json` only.

THE SAMPLE: heads whose standing ADJUDICATE duration verdict CHANGED between the base and the arm record (`l283_compare.py
--list-changed`), drawn at random per change class so the rare class is not drowned by the common one, plus CONTROLS from
Sean's hand-truth page (Brahms pdf 0) whose answer is in his own boxes: heads his boxes show FLAGGED (the answer is an eighth)
and heads they show BARE (a quarter). The cut, the normalisation (32 px per staff space) and the frame control are
`l281_tiles.cut` / `frame_control`, unchanged: a control that can fail (the same measure on the page shifted 1.6 head widths
must fail on most tiles).

    python3 l283_tiles.py --out DIR --seed 20261010 \
        --brahms-arm A.record.json --brahms-changed ch_b.json --litolff-arm L.record.json --litolff-changed ch_l.json \
        --controls truth_rows_arm.json --n-brahms 6 --n-litolff 4 --n-controls 4
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

from l281_tiles import PDFS, QUESTION, TILE_SP, cut, frame_control  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def head_info(run, key):
    """(page box, staff space in page px, stem page box or None) for one head, off the run's own rows."""
    g = run.glyphs[key]
    cx0, cy0, cx1, cy1 = g.box_canon
    px0, py0, px1, py1 = g.box_page
    ax, ay = (px1 - px0) / (cx1 - cx0), (py1 - py0) / (cy1 - cy0)
    sp_rows = run.obs_at(g.cell_key, Q.CELL_STAFF_SPACE)
    sp = float(sp_rows[-1]["value"]) * ax if sp_rows else 32.0
    stem = None
    hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
    if hs is not None and hs["outcome"] == "decided" and hs.get("value"):
        for o in run.obs_at(g.cell_key, Q.STEM):
            if o["id"] == hs["value"]:
                x, y, w, h = o["value"]
                stem = (px0 + (x - cx0) * ax, py0 + (y - cy0) * ay, px0 + (x + w - cx0) * ax, py0 + (y + h - cy0) * ay)
    return tuple(g.box_page), sp, stem, g.page


def draw(changed, n, rng):
    """n changed heads, spread over the change classes (base label -> arm label) round-robin, at random within each."""
    by = collections.defaultdict(list)
    for c in changed:
        by[(c["base"].split("{")[0] + "->" + c["arm"].split("{")[0])].append(c)
    keys = sorted(by, key=lambda k: -len(by[k]))
    for k in keys:
        by[k].sort(key=lambda c: c["key"])
        rng.shuffle(by[k])
    out = []
    i = 0
    while len(out) < n and any(by.values()):
        k = keys[i % len(keys)]
        if by[k]:
            out.append((k, by[k].pop()))
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--brahms-arm")
    ap.add_argument("--brahms-base")
    ap.add_argument("--brahms-changed")
    ap.add_argument("--litolff-arm")
    ap.add_argument("--litolff-base")
    ap.add_argument("--litolff-changed")
    ap.add_argument("--controls", default=None, help="l283_truth_score --json of base+arm records of Brahms pdf 0-1")
    ap.add_argument("--controls-run", default=None, help="the ARM record those control rows were scored on")
    ap.add_argument("--n-brahms", type=int, default=6)
    ap.add_argument("--n-litolff", type=int, default=4)
    ap.add_argument("--n-controls", type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    from tools.omr.preprocessing import render_page
    runs = {}
    base_runs = {}
    items = []
    for mv, arm, base, ch, n in (("brahms", a.brahms_arm, a.brahms_base, a.brahms_changed, a.n_brahms),
                                 ("litolff", a.litolff_arm, a.litolff_base, a.litolff_changed, a.n_litolff)):
        if not arm or not ch:
            continue
        runs[mv] = RD.load_run(arm)
        base_runs[mv] = RD.load_run(base) if base else None
        changed = [c for c in json.loads(Path(ch).read_text()) if c.get("box_page")]
        if mv == "brahms":
            changed = [c for c in changed if c["page"] != 0]      # page 0 is the hand-truth page: its controls are below
        for k, c in draw(changed, n, rng):
            items.append({"kind": "sample", "mv": mv, "cls": k, "c": c})
    if a.controls:
        rows = json.loads(Path(a.controls).read_text())
        runs["brahms_ctl"] = RD.load_run(a.controls_run)
        flagged = [r for r in rows if r["kind"] == "flag" and r.get("arm_key") and r["arm"][0] in ("right", "narrowed+")]
        bare = [r for r in rows if r["kind"] == "bare" and r.get("arm_key")]
        rng.shuffle(flagged)
        rng.shuffle(bare)
        half = a.n_controls // 2
        for r in flagged[:half]:
            items.append({"kind": "control", "mv": "brahms_ctl", "control": "flagged", "r": r})
        for r in bare[:a.n_controls - half]:
            items.append({"kind": "control", "mv": "brahms_ctl", "control": "bare", "r": r})
    order = list(range(len(items)))
    random.Random(a.seed + 2).shuffle(order)
    rendered = {}

    def page_img(mv, page):
        k = (mv.split("_")[0], page)
        if k not in rendered:
            if len(rendered) > 3:
                rendered.pop(next(iter(rendered)))
            rendered[k] = render_page(PDFS[k[0]], page, dpi=600).rgb
        return rendered[k]
    manifest = {"question": QUESTION, "seed": a.seed,
                "tile_scale": f"{TILE_SP:.0f} px per staff space on every tile (600 dpi page, normalised)", "tiles": []}
    n_s = n_c = 0
    fc_true, fc_wrong = [], []
    for pos in order:
        it = items[pos]
        mv = it["mv"]
        run = runs[mv]
        if it["kind"] == "sample":
            c = it["c"]
            key = c["key"]
            n_s += 1
            tid = f"tile_{n_s:02d}"
            bkey = base_runs[mv]
            hidden = {"key": key, "movement": mv, "pdf_page": c["page"], "change_class": it["cls"],
                      "base_reading": c["base"], "arm_reading": c["arm"], "base_status": c["base_status"],
                      "arm_status": c["arm_status"]}
            g_run = run
        else:
            r = it["r"]
            key = r["arm_key"]
            n_c += 1
            tid = f"control_{n_c}"
            hidden = {"key": key, "movement": "brahms", "pdf_page": 0, "control": it["control"],
                      "truth": {"rule": "Sean's hand-truth boxes (Brahms pdf 0): "
                                        + ("a flag is on this head's stem: an EIGHTH" if it["control"] == "flagged"
                                           else "nothing on its stem: a QUARTER"),
                                "truth_id": r["truth"], "truth_level": r["level"]},
                      "base_reading": str(r["base"]), "arm_reading": str(r["arm"])}
            g_run = run
        box, sp, stem, page = head_info(g_run, key)
        img = page_img(mv, page)
        crop, win = cut(img, box, sp, stem)
        cv2.imwrite(str(out / f"{tid}.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        gray = img.mean(axis=2)
        t, l, r_ = frame_control(gray, box)
        t_w, l_w, r_w = frame_control(gray, box, shift_px=int(1.6 * (box[2] - box[0])))
        fc_true.append((t, l, r_))
        fc_wrong.append((t_w, l_w, r_w))
        manifest["tiles"].append({"id": tid, "file": f"{tid}.png", "question": QUESTION, "kind": it["kind"],
                                  "hidden": hidden, "window_page_px": list(win), "space_px_native": round(sp, 2),
                                  "frame_control": {"inside": round(t, 3), "left": round(l, 3), "right": round(r_, 3)}})
    ok_true = sum(1 for t, l, r_ in fc_true if t is not None and t > (l or 0) and t > (r_ or 0))
    ok_wrong = sum(1 for t, l, r_ in fc_wrong if t is not None and t > (l or 0) and t > (r_ or 0))
    manifest["frame_control"] = {
        "n": len(fc_true), "true_frame_inside_beats_both_neighbours": ok_true,
        "wrong_frame_(page_shifted_1.6_heads)_inside_beats_both": ok_wrong,
        "reading": "the control can fail: it must pass on the true frame and mostly fail on the shifted one"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (out / "answers.template.json").write_text(json.dumps(
        {t["id"]: None for t in sorted(manifest["tiles"], key=lambda t: t["id"])}, indent=1) + "\n")
    (out / "frame_control.txt").write_text(json.dumps(manifest["frame_control"], indent=1) + "\n")
    print("frame control:", manifest["frame_control"])
    print("wrote", len(manifest["tiles"]), "tiles to", out)


if __name__ == "__main__":
    main()
