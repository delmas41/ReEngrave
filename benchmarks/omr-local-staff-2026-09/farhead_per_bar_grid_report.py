"""lane-farhead-per-bar-grid (2026-10-06): the report on `farhead_per_bar_grid_oos.py scan` output -- population changes, Sean's 44 confirmed
tiles, tile 6, and the ONE sheet of 12 seeded changes (before = red dashed, after = blue, both staves, box orange; answer/owner
in words), with every drawn line re-measured against the page's pixel rows.

  python3 farhead_per_bar_grid_report.py <litolff.json> <brahms.json> [--sheet out.png] [--seed 20261006]
"""
from __future__ import annotations

import collections, json, random, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
import farhead_note_first_oos as O
import truth_set_2_44c as ts
from frame import render_page_matching_gather

ROOT = HERE.parents[1]
DOC = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
ORD = {1: "1st", 2: "2nd", 3: "3rd"}
NIGHT_TILES = [("litolff", "glyph/12/1/0/0/7"), ("brahms", "glyph/9/1/2/3/2"), ("litolff", "glyph/16/0/0/8/1"),
               ("brahms", "glyph/6/0/7/6/5"), ("brahms", "glyph/2/0/3/2/1"), ("litolff", "glyph/16/0/0/0/2"),
               ("brahms", "glyph/5/0/3/3/3"), ("litolff", "glyph/14/1/0/7/3"), ("brahms", "glyph/13/0/9/0/4"),
               ("brahms", "glyph/3/1/3/7/9"), ("litolff", "glyph/7/0/7/15/4"), ("litolff", "glyph/5/0/5/9/0")]
NIGHT_CONFIRMED = [1, 2, 3, 4, 5, 7, 8, 11, 12]
IMPLAUSIBLE_SP = 0.35


def ordinal(n):
    return ORD.get(n, f"{n}th")


def words_pos(p):
    if p is None:
        return "no answer (abstained)"
    p = int(p)
    if p < 0:
        if p == -1:
            return "in the first space above the staff"
        return (f"on the {ordinal(-p // 2)} ledger above" if p % 2 == 0
                else f"in the space above the {ordinal((-p - 1) // 2)} ledger")
    if p > 8:
        if p == 9:
            return "in the first space below the staff"
        return (f"on the {ordinal((p - 8) // 2)} ledger below" if p % 2 == 0
                else f"in the space below the {ordinal((p - 9) // 2)} ledger")
    return ("on staff line %d" % (p // 2 + 1)) if p % 2 == 0 else ("in staff space %d" % (p // 2 + 1))


def load(paths):
    heads = {}
    for which, p in zip(("litolff", "brahms"), paths):
        d = json.loads(Path(p).read_text())
        for s, r in d["heads"].items():
            r["which"] = which
            r["subject"] = s
            heads[(which, s)] = r
    return heads


def pos(r, arm):
    return None if r.get(arm) is None else r[arm]["read"]["pos"]


def owner(r, arm):
    return None if r.get(arm) is None else r[arm]["owner"]["owner"]


def implausible(read):
    """A DECIDED answer whose note line stands more than IMPLAUSIBLE_SP clear of the box the reader used (Sean 2026-10-05: the
    line is through the box or on its staff-side edge; there cannot be a line far from the note)."""
    if read["pos"] is None or read["line_y"] is None or not read["box_used"] or not read["lines"]:
        return False
    sp = (max(read["lines"]) - min(read["lines"])) / 4.0
    y0, y1 = read["box_used"][1], read["box_used"][3]
    d = max(y0 - read["line_y"], read["line_y"] - y1, 0.0)
    return d > IMPLAUSIBLE_SP * sp


def population(heads):
    out = {}
    for which in ("litolff", "brahms"):
        hs = {s: r for s, r in heads.items() if r["which"] == which and r.get("old") and r.get("new")}
        c = collections.Counter()
        for s, r in hs.items():
            a, b = pos(r, "old"), pos(r, "new")
            c["n"] += 1
            if a is None and b is None:
                c["both_abstain"] += 1
            elif a is None:
                c["abstain_to_decided"] += 1
            elif b is None:
                c["decided_to_abstain"] += 1
            elif a != b:
                c["position_changed"] += 1
            else:
                c["same_position"] += 1
            oa, ob = owner(r, "old"), owner(r, "new")
            if oa != ob:
                c["owner_changed"] += 1
                key = "owner_none_to_staff" if oa is None else ("owner_staff_to_none" if ob is None else "owner_staff_to_other")
                c[key] += 1
            wa, wb = r["old"]["owner"]["word"], r["new"]["owner"]["word"]
            c[f"word_old_{wa}"] += 1
            c[f"word_new_{wb}"] += 1
            c["implausible_old"] += implausible(r["old"]["read"])
            c["implausible_new"] += implausible(r["new"]["read"])
            c["decided_old"] += a is not None
            c["decided_new"] += b is not None
            c["box_detector_old"] += r["old"]["read"]["box_source"] == "detector"
            c["box_detector_new"] += r["new"]["read"]["box_source"] == "detector"
            c["changed_any"] += (a != b) or (oa != ob)
            if r["recorded"] is not None:
                c["recorded_n"] += 1
                c["old_eq_recorded"] += a == r["recorded"]
                c["new_eq_recorded"] += b == r["recorded"]
        out[which] = c
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the 44 confirmed tiles
# ---------------------------------------------------------------------------------------------------------------------
def confirmed_tiles(heads):
    tiles = []
    # note_first_sample 1-11 (seeded 20261005, the two oos jsons in this order; tile 12 = glyph/5/0/6/3/2 is the check)
    pool = []
    for which in ("litolff", "brahms"):
        for r in json.loads((HERE / f"farhead_note_first_oos_{which}.json").read_text()):
            if r["new"]["pos"] is not None and r["new"]["line_y"] is not None:
                r["doc"] = which
                pool.append(r)
    pick = random.Random(20261005).sample(pool, 12)
    assert pick[11]["subject"] == "glyph/5/0/6/3/2", pick[11]["subject"]
    for i, r in enumerate(pick[:11], 1):
        tiles.append((f"note_first {i}", (r["doc"], r["subject"]), r["new"]["pos"]))
    for i in NIGHT_CONFIRMED:
        k = NIGHT_TILES[i - 1]
        tiles.append((f"night {i}", k, heads[k]["recorded"] if k in heads else None))
    for r in json.loads((ROOT / "out/print/ledgers/edge_vs_through_flips.json").read_text()):
        tiles.append((f"edge_flip {r['n']}", (r["which"], r["subject"]), r["rule"]["pos"]))
    return tiles


def tile_table(heads):
    rows, broken = [], []
    for name, k, ans in confirmed_tiles(heads):
        r = heads.get(k)
        if r is None or not r.get("old") or not r.get("new"):
            rows.append((name, k, ans, None, None, "NOT READ"))
            continue
        a, b = pos(r, "old"), pos(r, "new")
        if b == ans:
            flag = "keeps" if a == ans else "keeps (today's reader without this change differed)"
        elif a == b:
            flag = "NOT MINE: today's reader already differs from the confirmed answer"
        elif a == ans:
            flag = "BROKEN by this change"
            broken.append((name, k, ans, a, b, r["new"]["read"]["reason"]))
        else:
            flag = "differs from confirmed, and from today's reader"
        rows.append((name, k, ans, a, b, flag))
    return rows, broken


# ---------------------------------------------------------------------------------------------------------------------
# the sheet
# ---------------------------------------------------------------------------------------------------------------------
SC = 2
RED, BLUE, ORANGE = (40, 40, 230), (230, 90, 20), (0, 140, 255)


def dashed(img, y, x_end, colour, dash=10, gap=7, th=1):
    x = 0
    while x < x_end:
        cv2.line(img, (x, y), (min(x + dash, x_end), y), colour, th)
        x += dash + gap


def ink_row(gray, y, sp, cols, thr):
    """Centre of the ink run nearest y within +-0.55 sp (rows whose ink fraction in `cols` >= 0.6), or None."""
    lo, hi = max(0, int(y - 0.55 * sp)), min(gray.shape[0], int(y + 0.55 * sp) + 1)
    frac = []
    for a, b in cols:
        a, b = max(0, int(a)), min(gray.shape[1], int(b))
        if b > a:
            frac.append((gray[lo:hi, a:b] <= thr).mean(axis=1))
    if not frac:
        return None
    f = np.mean(frac, axis=0)
    rows = [lo + i for i, v in enumerate(f) if v >= 0.6]
    if not rows:
        return None
    runs, cur = [], [rows[0]]
    for r in rows[1:]:
        if r == cur[-1] + 1:
            cur.append(r)
        else:
            runs.append(cur); cur = [r]
    runs.append(cur)
    best = min(runs, key=lambda c: abs(np.mean(c) - y))
    return float(np.mean(best))


def measure(gray, lines, box, thr):
    sp = (max(lines) - min(lines)) / 4.0
    cols = [(box[0] - 2.5 * sp, box[0] - 0.4 * sp), (box[2] + 0.4 * sp, box[2] + 2.5 * sp)]
    out = []
    for y in lines:
        c = ink_row(gray, y, sp, cols, thr)
        out.append(None if c is None else c - y)
    return out


def own_word(r, arm, own_key):
    o = r[arm]["owner"]
    w = o["word"]
    nb = o["neighbour"]
    if o["owner"] is None:
        return {"both_fit": "nobody: both staves fit", "neither_fits": "nobody: neither staff fits",
                "unread": "nobody: a staff could not be read"}.get(w, "nobody (" + w + ")")
    if o["owner"] == own_key:
        return "its own staff"
    cy = (r["new"]["read"]["box_used"] or r["old"]["read"]["box_used"] or [0, 0, 0, 0])
    lines = o["cands"][nb]["lines"]
    own_lines = o["cands"][own_key]["lines"]
    return "the staff below" if min(lines) > max(own_lines) else "the staff above"


def build_sheet(heads, picks, out, grays):
    cells, allm = [], {"old": [], "new": []}
    for no, (s, r) in enumerate(picks, 1):
        own_key = "staff/" + "/".join(s.split("/")[1:4])
        box = (r["new"]["read"]["box_used"] or r["old"]["read"]["box_used"])
        gray = grays[(r["which"], r["page"])]
        thr = min(int(np.percentile(gray[int(box[1]) - 200:int(box[3]) + 200, int(box[0]) - 200:int(box[2]) + 200], 25) + 40), 140)
        arms = {a: r[a]["owner"]["cands"] for a in ("old", "new")}
        ys = [y for a in arms for c in arms[a].values() for y in c["lines"]] + [box[1], box[3]]
        sp = (max(arms["new"][own_key]["lines"]) - min(arms["new"][own_key]["lines"])) / 4.0
        cx = (box[0] + box[2]) / 2.0
        xa, xb = int(cx - 3.0 * sp), int(cx + 3.0 * sp)
        ya, yb = int(min(ys) - 1.0 * sp), int(max(ys) + 1.0 * sp)
        crop = cv2.cvtColor(gray[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
        crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
        for arm, colour in (("old", RED), ("new", BLUE)):
            for k, c in arms[arm].items():
                m = measure(gray, c["lines"], box, thr)
                allm[arm] += [x for x in m if x is not None]
                allm[arm + "_none"] = allm.get(arm + "_none", 0) + sum(x is None for x in m)
                for y in c["lines"]:
                    yy = int(round((y - ya) * SC))
                    if arm == "old":
                        dashed(crop, yy, crop.shape[1], colour)
                    else:
                        cv2.line(crop, (0, yy), (crop.shape[1] - 1, yy), colour, 1)
        cv2.rectangle(crop, (int((box[0] - xa) * SC), int((box[1] - ya) * SC)),
                      (int((box[2] - xa) * SC), int((box[3] - ya) * SC)), ORANGE, 2)
        W, H = max(crop.shape[1], 400), crop.shape[0]
        cap = np.full((H + 92, W, 3), 255, np.uint8)
        cap[:H, :crop.shape[1]] = crop
        a_, b_ = r["old"]["read"], r["new"]["read"]
        short = s.replace("glyph/", "")
        put = lambda t, y, col=(0, 0, 0), sz=0.42: cv2.putText(cap, t, (6, H + y), cv2.FONT_HERSHEY_SIMPLEX, sz, col, 1)
        put(f"{no}  {r['which'][:4]} {short}", 16, sz=0.5)
        put("answer before: " + words_pos(a_["pos"]), 34, RED)
        put("answer after:  " + words_pos(b_["pos"]), 50, BLUE)
        put("owner before: " + own_word(r, "old", own_key), 68, RED)
        put("owner after:  " + own_word(r, "new", own_key), 84, BLUE)
        cells.append(cap)
    cols = 4
    rowsimg = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        w = max(c.shape[1] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, w - c.shape[1] + 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < cols:
            grp.append(np.full((h, w + 8, 3), 255, np.uint8))
        rowsimg.append(np.hstack(grp))
    w = max(r.shape[1] for r in rowsimg)
    img = np.vstack([np.pad(r, ((6, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rowsimg])
    legend = np.full((34, img.shape[1], 3), 255, np.uint8)
    cv2.putText(legend, "orange box = the head   red dashed = the five lines BEFORE (raw staff-wide, both staves)   "
                "blue = the five lines AFTER (per-bar grid, both staves)", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    cv2.imwrite(out, np.vstack([legend, img]))
    return allm


def stat(v):
    if not v:
        return "n=0"
    a = np.abs(np.array(v))
    return f"n={len(a)} median {np.median(a):.2f} px, p90 {np.percentile(a, 90):.2f} px, max {a.max():.2f} px"


if __name__ == "__main__":
    heads = load(sys.argv[1:3])
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 20261006
    pop = population(heads)
    for which, c in pop.items():
        print("==", which, dict(c))
    rows, broken = tile_table(heads)
    print("== 44 confirmed tiles:", len(rows), "| changed:", len(broken), "| not read:", sum(r[5] == "NOT READ" for r in rows))
    for r in rows:
        print("  ", r)
    for b in broken:
        print("  BROKEN", b)
    t6 = heads.get(("litolff", "glyph/16/0/0/0/2"))
    if t6:
        print("== tile 6 glyph/16/0/0/0/2 (night)")
        for arm in ("old", "new"):
            rd, ow = t6[arm]["read"], t6[arm]["owner"]
            print("  ", arm, "reads", words_pos(rd["pos"]), rd["pos"], rd["reason"][:70], "| owner", ow["owner"], ow["word"],
                  {k: (v["fits"], v["pos"], v["reason"][:40]) for k, v in ow["cands"].items()})
    if "--sheet" in sys.argv:
        changed = [(r["subject"], r) for k, r in heads.items() if r.get("old") and r.get("new")
                   and (r["new"]["read"]["box_used"] or r["old"]["read"]["box_used"])
                   and (pos(r, "old") != pos(r, "new") or owner(r, "old") != owner(r, "new"))]
        rng = random.Random(seed)
        picks = []
        for which in ("litolff", "brahms"):
            pool = sorted([x for x in changed if x[1]["which"] == which])
            picks += rng.sample(pool, min(6, len(pool)))
        grays = {}
        for s, r in picks:
            k = (r["which"], r["page"])
            if k not in grays:
                cfg = ts.DOCS[DOC[r["which"]]]
                grays[k] = cv2.cvtColor(render_page_matching_gather(cfg["pdf"], r["page"], 600).rgb, cv2.COLOR_RGB2GRAY)
        allm = build_sheet(heads, picks, sys.argv[sys.argv.index("--sheet") + 1], grays)
        print("== drawn-line re-measure (offset from the page's pixel rows within +-0.55 sp of the line, flank columns beside the head)")
        print("  before (red):", stat(allm["old"]), "| no ink to measure:", allm.get("old_none"))
        print("  after (blue):", stat(allm["new"]), "| no ink to measure:", allm.get("new_none"))
        for i, (s, r) in enumerate(picks, 1):
            print("  tile", i, s, "pos", pos(r, "old"), "->", pos(r, "new"), "owner", owner(r, "old"), "->", owner(r, "new"))
