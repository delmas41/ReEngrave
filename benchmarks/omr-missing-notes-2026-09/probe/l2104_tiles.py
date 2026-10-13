#!/usr/bin/env python3
"""l2104_tiles: the blind tiles for Sean -- ROADMAP 2.104 (flags read under a covering detector box).

QUESTION on every tile: *What is the printed value of the note in the red brackets?*  Big tile number top-left, nothing of ours drawn.
Roles, readings and every hidden field are in `manifest.json` only.  Same cut and frame control as `l281_tiles` / `l283_tiles2`.

    python3 l2104_tiles.py --out DIR --spec SPEC.json --seed 20261013
SPEC.json: [{"mv": "brahms|litolff|schumann", "record": ARM_RECORD, "key": "glyph/p/s/st/c/g", "role": "...", "hidden": {...}}, ...]
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

from l281_tiles import PDFS, QUESTION, TILE_SP, cut, frame_control  # noqa: E402
from l283_tiles import head_info  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402

PDFS = dict(PDFS)
PDFS["schumann"] = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/schumann/symphony-2-op61/"
                    "schumann--symphony-2-op61--peters-1887--imslp514290.pdf")
PDFS["dvorak"] = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/dvorak/symphony-8-op88/"
                  "dvorak--symphony-8-op88--novello-1892--imslp405841.pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--seed", type=int, default=20261013)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads(Path(a.spec).read_text())
    random.Random(a.seed).shuffle(spec)
    from tools.omr.preprocessing import render_page
    runs, rendered = {}, {}
    man = {"question": QUESTION, "seed": a.seed,
           "tile_scale": f"{TILE_SP:.0f} px per staff space on every tile (600 dpi page, normalised)", "tiles": []}
    fct, fcw = [], []
    for n, it in enumerate(spec, 1):
        rec = it["record"]
        if rec not in runs:
            runs[rec] = RD.load_run(rec)
        run = runs[rec]
        box, sp, stem, page = head_info(run, it["key"])
        k = (it["mv"], page)
        if k not in rendered:
            if len(rendered) > 3:
                rendered.pop(next(iter(rendered)))
            rendered[k] = render_page(PDFS[it["mv"]], page, dpi=600).rgb
        img = rendered[k]
        crop, win = cut(img, box, sp, stem)
        # a big number in its own white strip above the music (phone-sized, never over the ink)
        strip = 54
        canvas = 255 * (crop[:1].repeat(strip, axis=0) * 0 + 1)
        cv2.putText(canvas, str(n), (10, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 4)
        tile = cv2.vconcat([canvas.astype(crop.dtype), crop])
        tid = f"tile_{n:02d}"
        cv2.imwrite(str(out / f"{tid}.png"), cv2.cvtColor(tile, cv2.COLOR_RGB2BGR))
        gray = img.mean(axis=2)
        t, l, r = frame_control(gray, box)
        tw, lw, rw = frame_control(gray, box, shift_px=int(1.6 * (box[2] - box[0])))
        fct.append((t, l, r))
        fcw.append((tw, lw, rw))
        man["tiles"].append({"n": n, "file": f"{tid}.png", "question": QUESTION, "movement": it["mv"], "pdf_page": page,
                             "key": it["key"], "role": it["role"], "hidden": it.get("hidden", {}),
                             "window_page_px": list(win), "space_px_native": round(sp, 2),
                             "frame_control": {"inside": round(t, 3), "left": round(l, 3), "right": round(r, 3)}})
    ok = lambda rows: sum(1 for t, l, r in rows if t is not None and t > (l or 0) and t > (r or 0))  # noqa: E731
    man["frame_control"] = {"n": len(fct), "true_frame_inside_beats_both_neighbours": ok(fct),
                            "wrong_frame_(page_shifted_1.6_heads)_inside_beats_both": ok(fcw),
                            "reading": "the control can fail: it must pass on the true frame and mostly fail on the shifted one"}
    (out / "manifest.json").write_text(json.dumps(man, indent=1, default=str))
    (out / "answers.template.json").write_text(json.dumps({f"tile_{i:02d}": None for i in range(1, len(spec) + 1)}, indent=1) + "\n")
    print(man["frame_control"], "wrote", len(spec), "tiles to", out)


if __name__ == "__main__":
    main()
