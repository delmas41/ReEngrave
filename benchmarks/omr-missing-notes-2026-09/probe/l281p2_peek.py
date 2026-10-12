#!/usr/bin/env python3
"""l281p2_peek: cut a print crop (clean, a red corner bracket on the head, nothing of ours) for given glyph keys.
An AGENT-READ look, never Sean's judgement. `--ext DIR --tag TAG KEY...`; writes `OUT/<key>.png` (with a 2x
upscale so a phone/contact sheet shows the stem and the tip).

    python3 l281p2_peek.py --ext DIR --tag brank --out OUT --movement brahms glyph/1/0/2/6/3 ...
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402

import l281_tiles as T  # noqa: E402
from l281_population import build  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--movement", default="brahms")
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    d, _pop, _n, _s = build(a.ext, a.tag)
    from tools.omr.preprocessing import render_page
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = {}
    for key in a.keys:
        head = d["obs"]["heads"].get(key)
        if head is None or not head.get("page"):
            print(key, "NO HEAD")
            continue
        page = int(key.split("/")[1])
        if page not in cache:
            cache[page] = render_page(T.PDFS[a.movement], page, dpi=600).rgb
        sp = T.space_px(d, head, key) or 32.0
        stem = T.stem_page_box(d, key, head)
        crop, _win = T.cut(cache[page], list(head["page"]), sp, stem)
        crop = cv2.resize(crop, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
        fn = out / (key.replace("/", "_") + ".png")
        cv2.imwrite(str(fn), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        print("wrote", fn)


if __name__ == "__main__":
    main()
