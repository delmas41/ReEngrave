"""ROADMAP 2.110 Step A.1 -- LEAKAGE: does any training image share pixels with a TEST cell or a TEST page?  Content, not names.

Training pool: every image of the control mix (v1-v4, v13-v22 distill25 form; 495 unique) + v24 (100) -- the 595
images that either arm of 2.110 or the 2.4b fine-tunes saw.
Test pool: the product-path cells of Brahms 317803 pdf 0 (112) and Litolff 984073 idx 1 (192, of which Sean's 104
TEST cells are the scored ones), plus the 104 TEST PNGs as saved by the labeling round, and the two PAGES themselves.

  1. EXACT: SHA-256 of the decoded pixel array (shape + bytes), train vs every test cell PNG.
  2. NEAR-DUPLICATE: 8x8-block dHash of the whole image (64 bits), Hamming <= 10 (the cell re-cut at a shifted pad
     changes the hash, so this is only a first net).
  3. CROP-OF-THE-PAGE (the one that matters): each training image, rescaled to staff space 25/100 of canonical by
     its own measured space, is template-matched (TM_CCOEFF_NORMED on inverted gray) inside each TEST PAGE rendered at
     600 dpi and scaled to the same staff space. A cell cut from that page - at any pad, any offset - scores ~1.0;
     an unrelated cell scores far lower. Control (must succeed): a cell cut FROM the test page by the product cutter
     and then shifted/cropped must be found at >= 0.9; and a training image pasted in nowhere scores < 0.6.
usage: leakage.py   (writes leakage.json)
"""
import hashlib, json, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path.cwd()))
from shown_space import measure_space

HERE = Path(__file__).parent
E = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")
PAGES = {
    "brahms317803_p0": (E / "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 0),
    "litolff984073_p1": (E / "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 1),
}
SC = 0.25  # work at a quarter of canonical (space 25 px)


def sha(im):
    return hashlib.sha256(str(im.shape).encode() + np.ascontiguousarray(im).tobytes()).hexdigest()


def dhash(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    s = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    return (s[:, 1:] > s[:, :-1]).flatten()


def inv_small(im, space):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    f = 25.0 / space
    out = cv2.resize(255 - g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    return out.astype(np.float32)


def main():
    train = json.load(open(HERE / "train-spaces-control.json"))  # control train + v24, with measured space
    seen = {r["path"] for r in train}
    for l in open("runs/2.110/cat-old/_catalog_val.txt"):  # the val images of the same catalog (also in the mix)
        p = l.strip()
        if p and p not in seen:
            im = cv2.imread(p); m = measure_space(im)
            train.append({"path": p, "h": im.shape[0], "w": im.shape[1], "space": None if m is None else m[0], "comb": None if m is None else m[1], "split": "val"})
    tests = {}
    for tag in PAGES:
        d = Path("runs/2.110/test-cells") / tag
        for m in json.load(open(d / "cells.json")):
            tests[f"{tag}/{m['cell_id']}"] = d / f"{m['cell_id']}.png"
    saved = Path("benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells")
    for p in sorted(saved.glob("*.png")):
        if not p.stem.endswith("_nostaff"):
            tests[f"saved-TEST/{p.stem}"] = p
    out = {"train_images": len(train), "test_cells": len(tests)}
    # 1 exact + 2 near-dup
    th = {k: sha(cv2.imread(str(v))) for k, v in tests.items()}
    tdh = {k: dhash(cv2.imread(str(v))) for k, v in tests.items()}
    tset = {}
    for k, h in th.items():
        tset.setdefault(h, []).append(k)
    exact, near = [], []
    for r in train:
        im = cv2.imread(r["path"])
        h = sha(im)
        if h in tset:
            exact.append((r["path"], tset[h]))
        dh = dhash(im)
        for k, v in tdh.items():
            ham = int((dh != v).sum())
            if ham <= 10:
                near.append((r["path"], k, ham))
    out["exact_pixel_matches"] = exact
    out["near_dhash_le10"] = near
    # reproducibility: saved TEST png vs regenerated product cell, joined on (system, staff, measure)
    same = diff = 0
    sm = {(c["system_index"], c["staff_index"], c["measure_index"]): c["cell_id"]
          for c in json.load(open("benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells.json"))}
    rc = {(c["system_index"], c["staff_index"], c["measure_index"]): c["cell_id"]
          for c in json.load(open("runs/2.110/test-cells/litolff984073_p1/cells.json"))}
    for key, sid in sm.items():
        a = cv2.imread(f"benchmarks/omr-labeling-hollow4-test-litolff-p1-2026-10/cells/{sid}.png")
        b = cv2.imread(f"runs/2.110/test-cells/litolff984073_p1/{rc[key]}.png") if key in rc else None
        if a is not None and b is not None and a.shape == b.shape and (a == b).all():
            same += 1
        else:
            diff += 1
    out["saved_TEST_vs_recut_pixel_identical"] = {"identical": same, "different_or_missing": diff}
    # 3 crop of the page
    from tools.omr.preprocessing import render_page
    res = {}
    for tag, (pdf, pg) in PAGES.items():
        page = render_page(pdf, pg, dpi=600)
        pg_gray = cv2.cvtColor(page.rgb, cv2.COLOR_RGB2GRAY)
        cells = json.load(open(Path("runs/2.110/test-cells") / tag / "cells.json"))
        # page staff space: a cell's page crop is measured by the same comb
        sp = []
        for c in cells[:6]:
            x0, y0, x1, y1 = c["bbox_page_px"]
            m = measure_space(pg_gray[y0:y1, x0:x1])
            if m:
                sp.append(m[0])
        pspace = float(np.median(sp))
        P = cv2.resize(255 - pg_gray, None, fx=25.0 / pspace, fy=25.0 / pspace, interpolation=cv2.INTER_AREA).astype(np.float32)
        # controls: a product cell cut from this very page, then CROPPED (shifted pad) -> must be found
        ctl = []
        for c in cells[:3]:
            im = cv2.imread(str(Path("runs/2.110/test-cells") / tag / f"{c['cell_id']}.png"))
            crop = im[60:-90, 40:-30]
            T = inv_small(crop, measure_space(crop)[0])
            r = cv2.matchTemplate(P, T, cv2.TM_CCOEFF_NORMED)
            ctl.append(round(float(r.max()), 3))
        scores = []
        for r in train:
            im = cv2.imread(r["path"])
            T = inv_small(im, r["space"])
            if r["w"] < 500 or r["space"] is None or T.shape[0] >= P.shape[0] or T.shape[1] >= P.shape[1] or T.std() < 1e-3:
                scores.append((r["path"], None)); continue
            res_ = cv2.matchTemplate(P, T, cv2.TM_CCOEFF_NORMED)
            scores.append((r["path"], round(float(res_.max()), 3)))
        vals = np.array([s for _, s in scores if s is not None])
        res[tag] = {"page_staff_space_px": pspace, "control_cut_from_page_then_cropped_scores": ctl,
                    "n_templates": len(vals), "max": float(vals.max()), "p99": float(np.percentile(vals, 99)),
                    "median": float(np.median(vals)),
                    "n_ge_0.6": int((vals >= 0.6).sum()), "n_ge_0.8": int((vals >= 0.8).sum()),
                    "top5": sorted([s for s in scores if s[1] is not None], key=lambda t: -t[1])[:5]}
        print(tag, json.dumps({k: v for k, v in res[tag].items() if k != "top5"}), flush=True)
        print("   top5", res[tag]["top5"], flush=True)
    out["crop_of_page"] = res
    (HERE / "leakage.json").write_text(json.dumps(out, indent=1))
    print("exact", len(exact), "near", len(near), "saved-vs-recut", out["saved_TEST_vs_recut_pixel_identical"])


if __name__ == "__main__":
    main()
