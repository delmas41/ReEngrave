#!/usr/bin/env python3
"""l282_tiles: blind tiles of heads whose ADJUDICATE `Q.DURATION` verdict CHANGED between the 2.74 tree and the
2.82 tree (`l282_diff.py --json`). ROADMAP 2.82. Same style as `out/print/2.81-review/`: a red corner bracket
on the head and nothing of ours; the question on every tile is *what is the printed value of the note in the
red brackets?* Our readings (before and after) and every other hidden field are in `manifest.json` only.

600 dpi page, `preprocessing.render_page` (the raster the gather read), normalised to 32 px per staff space
(`l281_tiles.cut`); the window is 12 spaces wide and 14 tall (a head's stem and its beam fit). The frame
control is `l281_tiles.frame_control`: the head's box darkness must beat the box moved 1.6 head-widths either
way on the true frame, and mostly FAIL when the page raster is shifted (it can fail).

SAMPLE. The changed heads, split by plate; `--n` tiles in all, drawn at random (fixed seed) per stratum
(`--per`), shuffled. Hand-truth heads (Brahms pdf 0) carry Sean's own derived value in the manifest.

    python3 l282_tiles.py --changed-brahms c1.json --changed-litolff c2.json --out DIR [--n 10] [--seed 282]
"""
import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402

from l281_tiles import PDFS, QUESTION, cut, frame_control  # noqa: E402
from tools.omr.staged import readout as RO  # noqa: E402


def space_of(g):
    cx0, cy0, cx1, cy1 = g.box_canon
    px0, py0, px1, py1 = g.box_page
    up = (cx1 - cx0) / float(px1 - px0)
    return 100.0 / up


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed-brahms", required=True, help="comma list of l282_diff.py --json files")
    ap.add_argument("--changed-litolff", required=True, help="comma list ('' for none)")
    ap.add_argument("--arm-brahms", required=True, help="comma list of arm records (the head's own box and scale)")
    ap.add_argument("--arm-litolff", required=True, help="comma list")
    ap.add_argument("--truth", default=None, help="l282_headscore.py --json of the ARM (Brahms pdf 0)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--per-brahms", type=int, default=6)
    ap.add_argument("--seed", type=int, default=282)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    runs = {"brahms": [RO.load_run(p) for p in a.arm_brahms.split(",") if p],
            "litolff": [RO.load_run(p) for p in a.arm_litolff.split(",") if p]}
    truth = {r["key"]: r for r in json.load(open(a.truth))} if a.truth else {}
    def _pool(arg):
        out_ = []
        for f in arg.split(","):
            if f:
                out_ += json.load(open(f))
        return sorted(out_, key=lambda c: c["key"])
    pool = {"brahms": _pool(a.changed_brahms), "litolff": _pool(a.changed_litolff)}
    take = {"brahms": min(a.per_brahms, len(pool["brahms"])), "litolff": 0}
    take["litolff"] = min(a.n - take["brahms"], len(pool["litolff"]))
    take["brahms"] = min(a.n - take["litolff"], len(pool["brahms"]))
    chosen = []
    for mv in ("brahms", "litolff"):
        chosen += [(mv, c) for c in rng.sample(pool[mv], take[mv])]
    rng.shuffle(chosen)
    from tools.omr.preprocessing import render_page
    cache = {}
    manifest = {"question": QUESTION, "seed": a.seed,
                "frame_sizes": {k: len(v) for k, v in pool.items()},
                "tile_scale": "32 px per staff space on every tile (600 dpi page, normalised)",
                "tiles": []}
    fc_t, fc_w = [], []
    for i, (mv, c) in enumerate(chosen, 1):
        g = next(r.glyphs[c["key"]] for r in runs[mv] if c["key"] in r.glyphs)
        page = g.page
        if (mv, page) not in cache:
            if len(cache) > 3:
                cache.pop(next(iter(cache)))
            cache[(mv, page)] = render_page(PDFS[mv], page, dpi=600).rgb
        img = cache[(mv, page)]
        box = list(g.box_page)
        sp = space_of(g)
        crop, win = cut(img, box, sp, None)
        tid = f"tile_{i:02d}"
        cv2.imwrite(str(out / f"{tid}.png"), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        gray = img.mean(axis=2)
        t, l, r = frame_control(gray, box)
        tw, lw, rw = frame_control(gray, box, shift_px=int(1.6 * (box[2] - box[0])))
        fc_t.append((t, l, r))
        fc_w.append((tw, lw, rw))
        hidden = {"key": c["key"], "movement": mv, "pdf_page": page, "before_2_74": c["old"], "after_2_82": c["new"],
                  "head_class": g.cls, "head_box_page_px": [round(v, 1) for v in box]}
        if c["key"] in truth:
            hidden["hand_truth"] = {"written_beats": truth[c["key"]].get("truth_written"),
                                    "levels": truth[c["key"]].get("truth_levels"),
                                    "our_after_judged": truth[c["key"]].get("judge")}
        manifest["tiles"].append({"id": tid, "file": f"{tid}.png", "question": QUESTION, "hidden": hidden,
                                  "window_page_px": list(win), "space_px_native": round(sp, 2),
                                  "frame_control": {"inside": round(t, 3), "left": round(l, 3), "right": round(r, 3)}})
    ok_t = sum(1 for t, l, r in fc_t if t is not None and t > (l or 0) and t > (r or 0))
    ok_w = sum(1 for t, l, r in fc_w if t is not None and t > (l or 0) and t > (r or 0))
    manifest["frame_control"] = {"n": len(fc_t), "true_frame_inside_beats_both_neighbours": ok_t,
                                 "wrong_frame_(page_shifted_1.6_heads)_inside_beats_both": ok_w,
                                 "reading": "the control can fail: it must pass on the true frame and mostly fail on the shifted one"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (out / "answers.template.json").write_text(json.dumps({t["id"]: None for t in manifest["tiles"]}, indent=1) + "\n")
    (out / "frame_control.txt").write_text(json.dumps(manifest["frame_control"], indent=1) + "\n")
    print("frame control:", manifest["frame_control"])
    print("wrote", len(manifest["tiles"]), "tiles to", out)
    for t in manifest["tiles"]:
        h = t["hidden"]
        print(f"  {t['id']} {h['movement']} p{h['pdf_page']} {h['key']}: {h['before_2_74']}  ->  {h['after_2_82']}"
              + (f"   [hand truth: {h['hand_truth']}]" if 'hand_truth' in h else ""))


if __name__ == "__main__":
    main()
