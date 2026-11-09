"""2.280 micro test (PRE-REGISTERED in benchmarks/omr-unwritten-notes-2026-10/FINDINGS.md; bars in probe/2.280-micro/RULES.md).
Offline GATHER-side prototype, nothing in tools/, no flag, no export. STAGED ruler `gather.measure_head_stem` (2.58d), head-anchored.

Arm A = the shipped ruler on the raw page raster (the 2.280 p18 numbers must reproduce).
Arm B = the same ruler on UNCLAIMED ink (ink minus the claimed areas the record holds) + the chord-through rule:
        a `both` answer is a chord stem when the through-run ends in another KEPT head's box at exactly one end (the stem always ends at a
        head, 2.179), a barline / unreadable when it ends in none or in both; abstain on `none`, on two disagreeing columns.
Arm C = arm B with the engraving side flipped (up -> left edge, down -> right edge): the side control.

usage: m1_prototype.py plate OUT.json
"""
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.pipeline import prepare_pages                      # noqa: E402
from tools.omr.staged import gather as G                                  # noqa: E402
from tools.omr.staged.geometry import stem_touches_head                  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
GLOBAL_SP = {"litolff": 15.75, "brahms": 27.3}      # what 2.280 p18 used
import os
SL = os.environ["R2_REC"].rstrip("/") + "/"
POPD = os.environ["R2_POP"].rstrip("/") + "/"
CLAIM_OWNERS = {"barline", "clef", "key_signature", "meter", "leading_column", "bracket", "word"}
MASK_FAMILIES = {"accidental", "clef", "meter", "text", "dynamic", "rest", "whole_rest"}   # page_mark families whose glyph box is someone's ink
plate, out_path = sys.argv[1], sys.argv[2]
PDF = PDFS[plate]

pop = json.load(open(POPD + "pop_%s.json" % plate))
labels = json.load(open("out/2.280/labels_%s.json" % plate))
popby = {r["sub"]: r for r in pop}
oldpop = json.load(open("out/2.280/pop_%s.json" % plate))     # r2: the SAME seeded populations as the 2.280 micro test (subjects from the 20261104 record)
NOTE_LABELS = {"H", "D", "S"}
NOT_NOTE_LABELS = {"R", "N"}

# ---- the record: claims, cells, stems (streamed; nothing else is loaded) -------------------------------------------------
cellbox, glyph, family, claims, stems = {}, {}, {}, [], collections.defaultdict(list)
for line in open(SL + plate + "/observations.jsonl"):
    if '"claimed_area"' in line:
        o = json.loads(line)
        d = o["detail"]
        if o["quantity"] == "claimed_area" and d.get("unit") == "area" and d.get("owner") in CLAIM_OWNERS:
            claims.append(dict(owner=d["owner"], standing=d.get("standing"), source=d.get("source"), box=o["value"], subject=o["subject"]))
    elif '"cell_box"' in line or '"glyph_box"' in line or '"page_mark"' in line or '"quantity": "stem"' in line:
        o = json.loads(line)
        q = o["quantity"]
        if q == "cell_box":
            cellbox[o["subject"]] = o["value"]
        elif q == "glyph_box" and o["detail"].get("bbox_page_px"):
            glyph[o["subject"]] = dict(canon=o["value"], page=o["detail"]["bbox_page_px"], cat=o["detail"].get("category"))
        elif q == "page_mark":
            family[o["subject"]] = o["detail"].get("family")
        elif q == "stem":
            stems[o["subject"]].append(o["value"])
print(plate, "claims", len(claims), collections.Counter(c["owner"] for c in claims), flush=True)


def page_of_claim(c):
    s = c["subject"].split("/")
    return int(s[1])


claims_by_page = collections.defaultdict(list)
for c in claims:
    claims_by_page[page_of_claim(c)].append(c)

HE = lambda r: tuple(r["page_box"])      # noqa: E731  (x0, y0, x1, y1)


def local_sp(r):
    pb = r["page_box"]
    scale = r["box"][2] / max(1e-6, (pb[2] - pb[0]))        # canonical px per page px
    return r["sp"] / scale, scale


def page_stem_boxes(r):
    """The record's stem rows of this head's cell, in page px (x0, y0, x1, y1)."""
    cb = cellbox.get(r["cell"])
    _, scale = local_sp(r)
    out = []
    for (x, y, w, h) in stems.get(r["cell"], []):
        out.append((cb[0] + x / scale, cb[1] + y / scale, cb[0] + (x + w) / scale, cb[1] + (y + h) / scale))
    return out


# ---- the ruler, with a mask and a side switch (a literal copy of gather.measure_head_stem + the run's x and far end) ----------
def ruler(ink, box, sp, flip=False):
    x0, y0, x1, y1 = (float(v) for v in box)
    hh = y1 - y0
    res = dict(sp=sp)
    if sp <= 0 or hh <= 0:
        return dict(res, direction="none", best={}, through={})
    win = max(2, int(round(G.HEAD_STEM_WINDOW_SPACES * sp)))
    gap = max(1, int(round(G.HEAD_STEM_GAP_SPACES * sp)))
    mx = int(round(G.HEAD_STEM_MAX_RUN_SPACES * sp))
    ys_dn = int(round(y1 - 0.25 * hh))
    ys_up = int(round(y0 + 0.25 * hh))
    lo_out = G.HEAD_STEM_SLIDE_OUT_SPACES * sp
    lo_in = G.HEAD_STEM_SLIDE_IN_SPACES * sp
    best, through = {}, {}
    for side in ("down", "up"):
        left_edge = (side == "down") != bool(flip)       # engraving side: down -> left, up -> right (flip swaps)
        ext_best, tip_best, clip_best, xs_best = -1e9, None, False, None
        if left_edge:
            starts = range(int(round(x0 - lo_out)), int(round(x0 + lo_in)) + 1)
        else:
            starts = range(int(round(x1 - lo_in)) - win, int(round(x1 + lo_out)) - win + 1)
        for xs in starts:
            if side == "down":
                tip, clip = G._stem_run(ink, xs, xs + win, ys_dn, 1, gap, mx)
                ext = tip - y1
            else:
                tip, clip = G._stem_run(ink, xs, xs + win, ys_up, -1, gap, mx)
                ext = y0 - tip
            if ext > ext_best:
                ext_best, tip_best, clip_best, xs_best = ext, tip, clip, xs
        best[side] = dict(ext=ext_best / sp, tip=tip_best, xs=xs_best, win=win)
        if ext_best / sp >= G.HEAD_STEM_MIN_EXT_SPACES and xs_best is not None:
            if side == "down":
                t2, _c = G._stem_run(ink, xs_best, xs_best + win, ys_up, -1, gap, mx)
                through[side] = dict(ok=(y0 - t2) / sp >= G.HEAD_STEM_MIN_EXT_SPACES, other_tip=t2)
            else:
                t2, _c = G._stem_run(ink, xs_best, xs_best + win, ys_dn, 1, gap, mx)
                through[side] = dict(ok=(t2 - y1) / sp >= G.HEAD_STEM_MIN_EXT_SPACES, other_tip=t2)
    d_ok = best["down"]["ext"] >= G.HEAD_STEM_MIN_EXT_SPACES
    u_ok = best["up"]["ext"] >= G.HEAD_STEM_MIN_EXT_SPACES
    direction = ("both" if (d_ok and u_ok) or any(v["ok"] for v in through.values())
                 else "down" if d_ok else "up" if u_ok else "none")
    return dict(res, direction=direction, best=best, through=through, d_ok=d_ok, u_ok=u_ok,
                ys_up=ys_up, ys_dn=ys_dn)


def ink_width_at(ink, xs, win, y, sp):
    """Horizontal extent of the inked segment through columns [xs, xs+win) at row y (capped at 0.6 sp each side)."""
    h, w = ink.shape
    y = min(max(0, y), h - 1)
    lo, hi = xs, xs + win
    cap = int(round(0.6 * sp))
    while lo > xs - cap and lo > 0 and ink[y, lo - 1]:
        lo -= 1
    while hi < xs + win + cap and hi < w and ink[y, hi]:
        hi += 1
    return lo, hi


def armB(ink, r, other_heads, sp, flip=False):
    """What the prototype files for head r: dict(status, direction, box(page px), why)."""
    box = HE(r)
    rr = ruler(ink, box, sp, flip=flip)
    d = rr["direction"]
    y0, y1 = box[1], box[3]
    hc = (y0 + y1) / 2.0
    if d == "none":
        return dict(status="abstain", why="ruler_none", ruler=d)
    if d in ("up", "down"):
        b = rr["best"][d]
        mid = int(round((b["tip"] + (rr["ys_up"] if d == "up" else rr["ys_dn"])) / 2.0))
        lo, hi = ink_width_at(ink, b["xs"], b["win"], mid, sp)
        ty0, ty1 = (b["tip"], hc) if d == "up" else (hc, b["tip"])
        return dict(status="filed", direction=d, kind="single", box=[lo, ty0, hi, ty1], ruler=d, ext=round(b["ext"], 2))
    # both: a through-run (the same column running past the head both ways) or two columns
    cands = []
    for side, t in rr["through"].items():
        if not t["ok"]:
            continue
        b = rr["best"][side]
        top = min(b["tip"], t["other_tip"])
        bot = max(b["tip"], t["other_tip"])
        cands.append((side, b["xs"], b["win"], top, bot))
    if not cands:
        return dict(status="abstain", why="both_two_columns", ruler=d)
    # if both sides gave a through-run on different columns, they must agree on direction or we abstain
    outs = []
    for side, xs, win, top, bot in cands:
        sx0, sx1 = xs - 0.6 * sp, xs + win + 0.6 * sp
        at_top = at_bot = 0
        for o in other_heads:
            ob = o["page_box"]
            if ob[2] < sx0 or ob[0] > sx1:
                continue
            oc = (ob[1] + ob[3]) / 2.0
            if abs(oc - top) <= 1.0 * sp and oc <= (top + bot) / 2.0:
                at_top += 1
            elif abs(oc - bot) <= 1.0 * sp and oc > (top + bot) / 2.0:
                at_bot += 1
        if at_top and not at_bot:
            outs.append(("down", xs, win, top, bot, at_top, at_bot))
        elif at_bot and not at_top:
            outs.append(("up", xs, win, top, bot, at_top, at_bot))
        else:
            outs.append((None, xs, win, top, bot, at_top, at_bot))
    dirs = {o[0] for o in outs}
    if len(dirs) != 1 or None in dirs:
        return dict(status="abstain", why="both_no_head_at_one_end" if all(o[0] is None for o in outs) else "both_sides_disagree",
                    ruler=d, ends=[(o[5], o[6]) for o in outs])
    dd, xs, win, top, bot, at_top, at_bot = outs[0]
    mid = int(round((top + bot) / 2.0))
    lo, hi = ink_width_at(ink, xs, win, mid, sp)
    return dict(status="filed", direction=dd, kind="chord", box=[lo, top, hi, bot], ruler="both", ends=[at_top, at_bot])


# ---- populations --------------------------------------------------------------------------------------------------------
note_subs = [s for s, l in labels.items() if l in NOTE_LABELS]
notnote_subs = [s for s, l in labels.items() if l in NOT_NOTE_LABELS]
dec_subs = [r["sub"] for r in oldpop if r["n_stem"] == 0 and r["dur"] == "decided"]
rng = random.Random(280)
with_row = sorted([r["sub"] for r in oldpop if r["n_stem"] >= 1])
agree_subs = rng.sample(with_row, 100)
want = {}
for grp, subs in (("real51", note_subs), ("notnote30", notnote_subs), ("decided299", dec_subs), ("agree200", agree_subs)):
    for s in subs:
        want.setdefault(s, []).append(grp)
print(plate, {g: sum(1 for v in want.values() if g in v) for g in ("real51", "notnote30", "decided299", "agree200")}, flush=True)

GONE = sorted(s for s in want if s not in popby)      # r2: subjects that are no longer a KEPT head in the re-adjudicated record
print(plate, "no longer a kept head:", {g: sum(1 for s in GONE if g in want[s]) for g in ("real51", "notnote30", "decided299", "agree200")}, flush=True)
json.dump({s: want[s] for s in GONE}, open(out_path + ".gone.json", "w"))
for s in GONE:
    del want[s]
by_page = collections.defaultdict(list)
for s in want:
    by_page[popby[s]["page"]].append(s)
heads_by_page = collections.defaultdict(list)
for r in pop:
    if r["page_box"]:
        heads_by_page[r["page"]].append(r)

results = {}
ctl = collections.Counter()
for pg in sorted(by_page):
    (pws, _cells), = prepare_pages(PDF, [pg])
    rgb = pws.page.rgb
    gray = rgb if rgb.ndim == 2 else rgb[..., :3].mean(axis=2)
    raw = gray < 128
    # the claims the record holds for this page: area claims + the glyph boxes of non-head families
    mask = np.zeros(raw.shape, dtype=bool)
    H, W = raw.shape
    n_claim = 0
    for c in claims_by_page.get(pg, []):
        x0, y0, x1, y1 = c["box"]
        mask[max(0, int(y0)):min(H, int(y1) + 1), max(0, int(x0)):min(W, int(x1) + 1)] = True
        n_claim += 1
    n_glyph = 0
    for sub, g in glyph.items():
        if not sub.startswith("glyph/%d/" % pg):
            continue
        if family.get(sub) in MASK_FAMILIES or g["cat"] in ("accidental", "clef"):
            x0, y0, x1, y1 = g["page"]
            mask[max(0, int(y0)):min(H, int(y1) + 1), max(0, int(x0)):min(W, int(x1) + 1)] = True
            n_glyph += 1
    unclaimed = raw & ~mask
    print("p%d claims %d glyph-claims %d masked-ink-share %.4f" % (pg, n_claim, n_glyph, float((raw & mask).sum()) / max(1, raw.sum())), flush=True)
    heads = heads_by_page[pg]
    for s in by_page[pg]:
        r = popby[s]
        spl, scale = local_sp(r)
        others = [h for h in heads if h["sub"] != s]
        # arm A, as 2.280 p18 ran it (global sp, raw raster) and the shipped function itself
        a_ship = G.measure_head_stem(raw, HE(r), GLOBAL_SP[plate])
        a_loc = G.measure_head_stem(raw, HE(r), spl)
        mine = ruler(raw, HE(r), spl)
        ctl["copy_equals_shipped" if mine["direction"] == a_loc["direction"] else "copy_differs"] += 1
        # the record's own stem rows touching this head, in page px
        st = page_stem_boxes(r)
        res = dict(groups=want[s], label=labels.get(s), page=pg, sp=spl, page_box=r["page_box"], dur=r["dur"], n_stem=r["n_stem"],
                   A_ship=a_ship["direction"], A_local=a_loc["direction"],
                   B=armB(unclaimed, r, others, spl), B_noclaims=armB(raw, r, others, spl),
                   C_flip=armB(unclaimed, r, others, spl, flip=True),
                   row_boxes=[list(b) for b in st if not (b[2] < r["page_box"][0] - 1 or b[0] > r["page_box"][2] + 1 or b[3] < r["page_box"][1] - 1 or b[1] > r["page_box"][3] + 1)])
        results[s] = res
    json.dump(dict(results=results, control=dict(ctl)), open(out_path, "w"))
print("control", dict(ctl))
json.dump(dict(results=results, control=dict(ctl)), open(out_path, "w"))
