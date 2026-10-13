#!/usr/bin/env python3
"""l281p2_tiles: blind tiles for Sean -- ROADMAP 2.81 PHASE 2.

QUESTION on every tile: *what is the printed value of the note in the red brackets?* (Sean answers
"N. 4/8/16", N = the big number baked into the tile.) The image carries the print, the staff, a big
tile number and the red corner bracket on the head -- nothing of ours. OUR reading (what INFER did,
whether the bar math settled it, the rest) is in `manifest.json` only.

Members come from the ARM record's page 0..1 population (both count-page documents), drawn at random
from three groups, so the page shows what the rule did and what it left alone:

  settled   a member INFER collapsed by the bar's arithmetic (decider `infer:collapse_bare_stem_by_bar`)
  narrowed  a member still NARROWED after INFER, quarter-first ranking held (bare-stem evidence)
  other     a member still NARROWED with the old order (evidence did not hold)

plus CONTROLS from Sean's hand-truth page (Brahms pdf 0) -- the head his boxes show BEAMED and the
head his boxes show BARE -- so a reader who answers the same on both is visible.

Reuses `l281_tiles` for the cut and the frame control (a control that can fail: the head's box
darkness must beat the box moved 1.6 head-widths either way on the true frame, and mostly fail on a
shifted page).

    python3 l281p2_tiles.py --ext DIR --tags bquick_arm,lquick_arm --scored scored.json --out OUT
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

import l281_tiles as T  # noqa: E402
from l281_population import build  # noqa: E402

MV = {"b": "brahms", "l": "litolff"}
QUESTION = "What is the printed value of the note in the red brackets?  (4 = quarter, 8 = eighth, 16 = sixteenth)"


def banner(img, n):
    """A tile image: the crop, a big number top-left, scaled to a phone-readable width."""
    h, w = img.shape[:2]
    f = 640.0 / w
    img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    band = np.full((86, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, str(n), (14, 70), cv2.FONT_HERSHEY_SIMPLEX, 2.6, (0, 0, 0), 7, cv2.LINE_AA)
    cv2.putText(band, "value of the note in the red brackets?", (130, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (60, 60, 60), 2, cv2.LINE_AA)
    out = np.vstack([band, img])
    cv2.rectangle(out, (0, 0), (out.shape[1] - 1, out.shape[0] - 1), (150, 150, 150), 2)
    return out


def group_of(m):
    if m["final_stage"] == "INFER" and str(m.get("final_decider", "")).endswith("collapse_bare_stem_by_bar"):
        return "settled"
    if m["final_outcome"] == "narrowed":
        cands = m["cands"] or []
        if cands and cands[0].get("beam_levels") == 0:
            return "narrowed_quarter_first"
        return "narrowed_old_order"
    return "other_stage_settled"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--tags", required=True, help="b...,l... (b = Brahms, l = Litolff), arm tags in --ext")
    ap.add_argument("--scored", required=True, help="l281_score --json of the Brahms arm (the controls)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--plan", default="settled:5,narrowed_quarter_first:3,narrowed_old_order:2")
    ap.add_argument("--controls", type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    plan = {k: int(v) for k, v in (p.split(":") for p in a.plan.split(","))}

    data, pop = {}, {}
    for tag in a.tags.split(","):
        data[tag], pop[tag], _n, _s = build(a.ext, tag)
    frame = collections.defaultdict(list)
    for tag, members in pop.items():
        mv = MV[tag[0]]
        for m in members:
            # exclude the hand-truth page from the sample frame: it is scored, not sampled
            if mv == "brahms" and m["page"] == 0:
                continue
            if m["page_box"]:
                frame[group_of(m)].append((tag, mv, m))
    sizes = {k: len(v) for k, v in frame.items()}
    print("frame sizes:", sizes)
    chosen = []
    for g, k in plan.items():
        pool = sorted(frame.get(g, []), key=lambda t: t[2]["key"])
        for t in rng.sample(pool, min(k, len(pool))):
            chosen.append(("sample", g) + t)
    scored = json.loads(Path(a.scored).read_text())
    quick_tag = [t for t in data if t[0] == "b"][0]
    for kind, r in T.pick_controls(scored, a.seed, a.controls):
        chosen.append(("control", kind, quick_tag, "brahms", r))
    rng.shuffle(chosen)

    from tools.omr.preprocessing import render_page
    cache = {}

    def page_img(mv, page):
        k = (mv, page)
        if k not in cache:
            cache[k] = render_page(T.PDFS[mv], page, dpi=600).rgb
        return cache[k]

    manifest = {"question": QUESTION, "seed": a.seed, "plan": plan, "frame_sizes": sizes, "tiles": []}
    fc_true, fc_wrong = [], []
    for i, it in enumerate(chosen, start=1):
        kind, grp, tag, mv, m = it
        d = data[tag]
        key = m["key"]
        box = m["page_box"]
        page = m["page"] if kind == "sample" else 0
        head = d["obs"]["heads"][key]
        sp = T.space_px(d, head, key) or 32.0
        stem = T.stem_page_box(d, key, head)
        img = page_img(mv, page)
        crop, win = T.cut(img, box, sp, stem)
        tile = banner(crop, i)
        cv2.imwrite(str(out / f"tile_{i:02d}.png"), cv2.cvtColor(tile, cv2.COLOR_RGB2BGR))
        gray = img.mean(axis=2)
        fc_true.append(T.frame_control(gray, box))
        fc_wrong.append(T.frame_control(gray, box, shift_px=int(1.6 * (box[2] - box[0]))))
        if kind == "sample":
            fv = m["final_value"] if isinstance(m["final_value"], dict) else {}
            hidden = {"group": grp, "key": key, "movement": mv, "pdf_page": page,
                      "our_reading_before_infer": "narrowed " + " | ".join(
                          f"beam_levels={c['beam_levels']} written={c['written']}" for c in (m["cands"] or [])),
                      "final": {"stage": m["final_stage"], "decider": m["final_decider"],
                                "outcome": m["final_outcome"], "beam_levels": fv.get("beam_levels"),
                                "written": fv.get("written")},
                      "tip_status": m["tip"], "stroke_at_tip": m["at_tip"], "dots_read": m["dots"]}
        else:
            hidden = {"control": grp, "key": key, "movement": mv, "pdf_page": 0,
                      "truth": ("Sean's boxes: a beam or flag is on this head's stem (NOT a quarter)"
                                if grp == "beamed" else "Sean's boxes: bare stem, a quarter / dotted quarter"),
                      "truth_levels": m.get("truth_levels")}
        manifest["tiles"].append({"id": f"tile_{i:02d}", "file": f"tile_{i:02d}.png", "kind": kind,
                                  "hidden": hidden, "window_page_px": list(win)})
    ok_t = sum(1 for t, l, r in fc_true if t is not None and t > (l or 0) and t > (r or 0))
    ok_w = sum(1 for t, l, r in fc_wrong if t is not None and t > (l or 0) and t > (r or 0))
    manifest["frame_control"] = {"n": len(fc_true), "true_frame_beats_both_neighbours": ok_t,
                                 "wrong_frame_(shifted_1.6_heads)_beats_both": ok_w}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (out / "answers.template.json").write_text(json.dumps({t["id"]: None for t in manifest["tiles"]}, indent=1) + "\n")
    print("frame control:", manifest["frame_control"])
    print("wrote", len(manifest["tiles"]), "tiles to", out)


if __name__ == "__main__":
    main()
