#!/usr/bin/env python3
"""l288_tiles: the blind tiles for Sean -- ROADMAP 2.88 (`out/print/2.88-review/`).

Phone-sized (~385 px wide: 12 staff spaces at 32 px), a header strip with the tile NUMBER in large type and the question
*Value of the note in the red brackets?*, the printed staff left as printed, a red corner bracket on the head. NOTHING of ours is on a
tile: our readings (base, arm, the reasons, the ink windows) are in `manifest.json` only; `answers.template.json` is a blank form.

THE SAMPLE: heads the arm DECIDED a half that base left narrowed (the restored population, `l288_compare --json`), at random with the
pages spread, the 2.83 tiles Sean already judged excluded; plus named heads and CONTROLS:
   brahms11_fragment  Brahms pdf 11 `glyph/11/1/10/3/10`: 2.83's first tile 6, the head the old clean-tip window made a WRONG half
   known_half         Litolff pdf 10 `glyph/10/1/4/8/7`: Sean's 2.83 fix tile 6 (a half): the restore must reach it
   controls           heads of Sean's own earlier tiles that must NOT become halves (a bare dotted quarter, an eighth)

    python3 l288_tiles.py --out DIR --changed changed_litolff.json --arm-litolff A.json [--arm-brahms11 B11.json] --brahms-p0 arm_brahms.json
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_tiles import PDFS, TILE_SP, cut, frame_control  # noqa: E402
from l283_tiles import head_info  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402

QUESTION = "Value of the note in the red brackets?"
JUDGED = [REPO / "out" / "print" / d / "manifest.json" for d in ("2.81-review", "2.83-review", "2.83-fix-review")]
HDR = 56


def judged_keys():
    ks = set()
    for p in JUDGED:
        m = json.loads(p.read_text())
        for t in (m["tiles"] if isinstance(m, dict) else m):
            k = (t.get("hidden") or {}).get("key")
            if k:
                ks.add(k)
    return ks


def with_header(crop, n):
    h, w = crop.shape[:2]
    out = np.full((h + HDR, w, 3), 255, np.uint8)
    out[HDR:] = crop
    cv2.putText(out, str(n), (10, HDR - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.9, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(out, QUESTION, (88, HDR - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.line(out, (0, HDR - 1), (w, HDR - 1), (200, 200, 200), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--changed", required=True, help="l288_compare --json over the Litolff set")
    ap.add_argument("--arm-litolff", nargs="+", required=True)
    ap.add_argument("--arm-brahms11", default=None)
    ap.add_argument("--brahms-p0", default=None, help="arm record holding Brahms pdf 0 (controls)")
    ap.add_argument("--n-sample", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20261011)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    excl = judged_keys()
    changed = [c for c in json.loads(Path(a.changed).read_text()) if c["arm"].startswith("decided:hollow_head_bare_stem") and c["key"] not in excl
               and c.get("box_page") and c["status"] != "refused"]
    changed.sort(key=lambda c: c["key"])
    rng.shuffle(changed)
    by_page, picked = {}, []
    for c in changed:
        by_page.setdefault(c["page"], []).append(c)
    pages = sorted(by_page)
    i = 0
    while len(picked) < a.n_sample and any(by_page.values()):
        p = pages[i % len(pages)]
        if by_page[p]:
            picked.append(by_page[p].pop())
        i += 1
    print("restored pool", len(changed), "drawn", len(picked))
    runs = {}
    for p in a.arm_litolff:
        run = RD.load_run(p)
        runs[p] = run
    def litolff_run(key):
        for run in runs.values():
            if key in run.glyphs:
                return run
        return None
    items = []
    for c in picked:
        items.append({"kind": "restored", "key": c["key"], "mv": "litolff", "run": litolff_run(c["key"]), "extra": {"base": c["base"], "arm": c["arm"]}})
    items.append({"kind": "known_half", "key": "glyph/10/1/4/8/7", "mv": "litolff", "run": litolff_run("glyph/10/1/4/8/7"),
                  "extra": {"truth": "Sean 2.83 fix tile 6: half"}})
    if a.arm_brahms11:
        items.append({"kind": "brahms11_fragment", "key": "glyph/11/1/10/3/10", "mv": "brahms", "run": RD.load_run(a.arm_brahms11),
                      "extra": {"truth": "Sean 2.83 tile 6: dotted quarter; the box is not a head (refused)"}})
    if a.brahms_p0:
        r0 = RD.load_run(a.brahms_p0)
        items.append({"kind": "control_bare", "key": "glyph/0/0/11/3/12", "mv": "brahms", "run": r0, "extra": {"truth": "Sean: dotted quarter"}})
        items.append({"kind": "control_flag", "key": "glyph/0/0/9/4/4", "mv": "brahms", "run": r0, "extra": {"truth": "Sean: eighth"}})
    order = list(range(len(items)))
    random.Random(a.seed + 2).shuffle(order)
    from tools.omr.preprocessing import render_page
    cache = {}
    manifest = {"question": QUESTION, "seed": a.seed, "excluded": "every head on Sean's 2.81 / 2.83 / 2.83-fix tiles except the named ones",
                "tile_scale": f"{TILE_SP:.0f} px per staff space", "tiles": []}
    fcs = []
    for n, pos in enumerate(order, 1):
        it = items[pos]
        run = it["run"]
        if run is None or it["key"] not in run.glyphs:
            print("MISSING", it["key"])
            continue
        box, sp, stem, page = head_info(run, it["key"])
        k = (it["mv"], page)
        if k not in cache:
            if len(cache) > 3:
                cache.pop(next(iter(cache)))
            cache[k] = render_page(PDFS[it["mv"]], page, dpi=600).rgb
        img = cache[k]
        crop, win = cut(img, box, sp, stem)
        cv2.imwrite(str(out / f"tile_{n:02d}.png"), cv2.cvtColor(with_header(crop, n), cv2.COLOR_RGB2BGR))
        gray = img.mean(axis=2)
        t, l, r = frame_control(gray, box)
        tw, lw, rw = frame_control(gray, box, shift_px=int(1.6 * (box[2] - box[0])))
        fcs.append(((t, l, r), (tw, lw, rw)))
        g = run.glyphs[it["key"]]
        manifest["tiles"].append({"n": n, "id": f"tile_{n:02d}", "file": f"tile_{n:02d}.png", "question": QUESTION, "kind": it["kind"],
                                  "hidden": {"key": it["key"], "movement": it["mv"], "pdf_page": g.page, **it["extra"]},
                                  "window_page_px": list(win), "frame_control": {"inside": round(t, 3), "left": round(l, 3), "right": round(r, 3)}})
    ok = lambda f: sum(1 for t, l, r in f if t is not None and t > (l or 0) and t > (r or 0))
    manifest["frame_control"] = {"n": len(fcs), "true_frame_inside_beats_both": ok([f[0] for f in fcs]),
                                 "shifted_frame_inside_beats_both": ok([f[1] for f in fcs]),
                                 "reading": "must pass on the true frame and mostly fail on the shifted one"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    (out / "answers.template.json").write_text(json.dumps({t["id"]: None for t in manifest["tiles"]}, indent=1) + "\n")
    (out / "frame_control.txt").write_text(json.dumps(manifest["frame_control"], indent=1) + "\n")
    print("frame control:", manifest["frame_control"])
    print("wrote", len(manifest["tiles"]), "tiles to", out)


if __name__ == "__main__":
    main()
