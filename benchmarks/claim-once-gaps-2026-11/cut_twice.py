"""2.322 follow-up: one sheet per plate of 12 places where ink is claimed twice (same ledger canvas as gaps_page.py, read-only).
    OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=. python3 cut_twice.py PLATE PAGES OUTDIR [SEED]
Phase 1 (build_page per page): twice-ink mask + a pair code per pixel -> npz + patch list. Phase 2: seeded draw weighted by patch px, quota 9 same-kind / 3 two-kind,
tiles = PAIR (plain crop | same crop with ONLY claimed-twice ink red), caption = number + the two claimants."""
import collections
import json
import pathlib
import random
import sys

import cv2
import numpy as np

from tools.omr.staged import cell_map as CM
from tools.omr.staged import claim_readout as CR

plate, pages_s, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
seed = int(sys.argv[4]) if len(sys.argv) > 4 else 2322012
pages = [int(p) for p in pages_s.split(",")]
out.mkdir(parents=True, exist_ok=True)
work = out / ("work_%s" % plate)
work.mkdir(exist_ok=True)
WORDS = {"notehead": "head", "ledger_line": "ledger line", "staff_line": "staff line", "key": "key signature", "meter": "time signature", "hairpin": "hairpin",
         "tremolo": "tremolo", "mark": "mark", "word": "word", "other": "other"}
word = lambda k: WORDS.get(k, k)
TWICE = (CR.ST_TWIN, CR.ST_TWIN_VIEWS, CR.ST_TWO_OPEN, CR.ST_TWO_VIEWS, CR.ST_PAGE_NOT_CONSULTED)
patches = []
tot_same = tot_two = 0

if not list(work.glob("p*.npz")):
    SL = CR.RECORDS / "lane-report-slices-20261117-night" / plate
    rows_all = CR.read_rows(SL, pages)
    ed = CR.edition_info(rows_all)
    pdf = CR.LIB / ed["edition_path"]
    for pg in pages:
        canvas, ver, pws, cells = CR.build_page(rows_all, pdf, pg, CM.ROOT_DEFAULT, None, ledger=True)
        st = canvas.state
        twice = canvas.ink & np.isin(st, TWICE)
        pop = canvas.pop
        names = {}
        code = np.zeros(st.shape, np.uint16)
        vals = np.unique(canvas.fam_eff[twice])
        for v in vals:
            ks = [word(k) for k in CR.mask_fine(int(v))]
            name = (ks[0] + " + " + ks[0]) if len(ks) == 1 else (" + ".join(ks[:2]) + (" + more" if len(ks) > 2 else ""))
            names[int(v)] = name
        lab = {n: i + 1 for i, n in enumerate(sorted(set(names.values())))}
        for v, n in names.items():
            code[twice & (canvas.fam_eff == v)] = lab[n]
        two_kind = twice & (pop >= 2)
        np.savez_compressed(work / ("p%d.npz" % pg), ink=canvas.ink, twice=twice, code=code, two=two_kind)
        json.dump({"lab": lab, "sp": float(canvas.sp), "same_px": int((twice & ~two_kind).sum()), "two_px": int(two_kind.sum())}, open(work / ("p%d.json" % pg), "w"))
        print("page", pg, "twice px", int(twice.sum()), flush=True)
        del canvas, pws, cells

pg_meta = {}
for pg in pages:
    z = np.load(work / ("p%d.npz" % pg))
    m = json.load(open(work / ("p%d.json" % pg)))
    pg_meta[pg] = m
    inv = {v: k for k, v in m["lab"].items()}
    tot_same += m["same_px"]
    tot_two += m["two_px"]
    tw, code, two = z["twice"], z["code"], z["two"]
    n, labc, stats, _c = cv2.connectedComponentsWithStats(cv2.dilate(tw.astype(np.uint8), np.ones((3, 3), np.uint8)), connectivity=8)
    for j in range(1, n):
        sel = (labc == j) & tw
        px = int(sel.sum())
        if px < 30:
            continue
        cc = collections.Counter(code[sel].tolist())
        top = cc.most_common(1)[0][0]
        x, y, w, h, _a = stats[j]
        patches.append({"page": pg, "box": [int(x), int(y), int(x + w), int(y + h)], "px": px, "pair": inv.get(top, "?"), "kind": "two" if two[sel].mean() > 0.5 else "same",
                        "sp": m["sp"]})
print(plate, "claimed-twice ink: same kind %d px, two kinds %d px => same %.1f%% / two %.1f%%" % (tot_same, tot_two, 100.0 * tot_same / (tot_same + tot_two), 100.0 * tot_two / (tot_same + tot_two)))
print("patches >= 30 px:", len(patches), " by pair (px):", collections.Counter({k: sum(p["px"] for p in patches if p["pair"] == k) for k in {p["pair"] for p in patches}}).most_common(8))
rng = random.Random(seed)


def draw(pool, k):
    pool = list(pool)
    got = []
    while pool and len(got) < k:
        i = rng.choices(range(len(pool)), weights=[p["px"] for p in pool])[0]
        got.append(pool.pop(i))
    return got


same = [p for p in patches if p["kind"] == "same"]
two = [p for p in patches if p["kind"] == "two"]
pick = draw(same, 9) + draw(two, 3)
rng.shuffle(pick)
TW, TH = 300, 220
tiles = []
key = []
for i, p in enumerate(pick, 1):
    z = np.load(work / ("p%d.npz" % p["page"]))
    ink, tw = z["ink"], z["twice"]
    sp = p["sp"] or 30.0
    x0, y0, x1, y1 = p["box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw = min(max((x1 - x0) / 2 + 8 * sp, 10 * sp), 22 * sp)
    hh = min(max((y1 - y0) / 2 + 8 * sp, 8 * sp), 16 * sp)
    X0, X1 = int(max(0, cx - hw)), int(min(ink.shape[1], cx + hw))
    Y0, Y1 = int(max(0, cy - hh)), int(min(ink.shape[0], cy + hh))
    a = ink[Y0:Y1, X0:X1]
    left = np.full(a.shape + (3,), 255, np.uint8)
    left[a] = (0, 0, 0)
    right = left.copy()
    right[tw[Y0:Y1, X0:X1]] = (0, 0, 230)
    s = min(TW / a.shape[1], TH / a.shape[0])
    both = []
    for im in (left, right):
        r = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        c = np.full((TH, TW, 3), 255, np.uint8)
        c[:r.shape[0], :r.shape[1]] = r
        cv2.rectangle(c, (0, 0), (TW - 1, TH - 1), (170, 170, 170), 1)
        both.append(c)
    pair = np.hstack(both)
    cap = np.full((34, pair.shape[1], 3), 255, np.uint8)
    cv2.putText(cap, "%d  %s" % (i, p["pair"]), (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    tiles.append(np.vstack([pair, cap]))
    key.append({"tile": i, "plate": plate, "page": p["page"], "system_staff": "not kept by the ledger canvas", "page_box": [X0, Y0, X1, Y1], "patch_box": p["box"],
                "claimants": p["pair"], "kind": "two different kinds" if p["kind"] == "two" else "same kind twice", "claimant_box_ids": "not kept by the ledger canvas (kinds only)",
                "patch_px": p["px"]})
rows = []
for r in range(0, len(tiles), 3):
    row = tiles[r:r + 3]
    while len(row) < 3:
        row.append(np.full_like(tiles[0], 255))
    rows.append(np.hstack(row))
cv2.imwrite(str(out / ("sheet_%s.png" % plate)), np.vstack(rows))
json.dump(key, open(out / ("key_%s.json" % plate), "w"), indent=1)
print("pairs drawn:", collections.Counter(k["claimants"] for k in key))
