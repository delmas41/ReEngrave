"""ROADMAP 2.58 A/B sheet: up to 12 changed decisions, rests first.  STAGED, GATHER+ADJUDICATE.

  python3 benchmarks/gather-order-ab-2026-10/ab_sheet.py OUTDIR [--seed 20261007]

Reads OUTDIR/<tag>.{base,arm}.json.  A changed decision = a bar that holds an
`empty_bar_rest_search` row in ARM and none in BASE (the rescued bars), plus any
glyph pair `readout.diff_runs` reports as changed.  Each tile: the bar cut from
the gather-frame page (600 dpi, `frame.render_page_matching_gather`), the staff
named from the record's own `instrument` verdict, the mark boxed ORANGE, before
and after in words.  1 px lines: magenta = the staff's top and bottom line from the
record, grey = the bar's own cell edges; each is re-measured against the ink rows
and the result printed.  NOT a judgement of who is right.
"""
from __future__ import annotations
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "benchmarks/omr-local-staff-2026-09"))
import cv2
import numpy as np
from tools.omr.staged import readout as RD
from tools.omr.staged.record import Q
from frame import render_page_matching_gather

R0 = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")
PDFS = {"lit": R0 / "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "bra": R0 / "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
NAMES = {"lit": "Beethoven 5, Litolff", "bra": "Brahms 1, Breitkopf"}
MAGENTA, ORANGE, GREY, BLACK = (255, 0, 255), (0, 140, 255), (110, 110, 110), (0, 0, 0)
SC = 2
_IMG = {}


def gray(doc, page):
    if (doc, page) not in _IMG:
        _IMG[(doc, page)] = cv2.cvtColor(render_page_matching_gather(PDFS[doc], page, 600).rgb, cv2.COLOR_RGB2GRAY)
    return _IMG[(doc, page)]


def staff_name(run, skey):
    v = run.standing(skey, Q.INSTRUMENT, "ADJUDICATE")
    if v and v["outcome"] == "decided" and isinstance(v.get("value"), dict):
        return v["value"].get("name") or "staff with no name read"
    return "staff with no name read"


def ink_row(g, y, x0, x1, thr):
    """centre of the darkest-run row nearest y (within 6 px) across x0..x1; offset, or (None, None)."""
    rows = [r for r in range(int(y) - 8, int(y) + 9) if 0 <= r < g.shape[0] and (g[r, x0:x1] <= thr).mean() >= 0.5]
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
    return float(np.mean(best)) - y


def rest_tile(tag, doc, base, arm, cell):
    page, system, staff, c = [int(v) for v in cell.split("/")[1:5]]
    skey = f"staff/{page}/{system}/{staff}"
    cb = next(o["value"] for o in arm.observations if o["subject"] == cell and o["quantity"] == Q.CELL_BOX)
    lines = next(o["value"] for o in arm.observations if o["subject"] == skey and o["quantity"] == Q.STAFF_LINES)
    sp = (lines[4] - lines[0]) / 4.0
    heads = [g for k, g in arm.glyphs.items() if k.startswith(f"glyph/{page}/{system}/{staff}/{c}/")
             and any(o["reader"] == "yolo_rescue_lowconf" for o in arm.obs_at(k, Q.GLYPH_BOX))]
    row = next(o for o in arm.observations if o["subject"] == cell and o["quantity"] == Q.EMPTY_BAR_REST_SEARCH)
    det = row.get("detail") or {}
    v_arm = arm.standing(cell, Q.EMPTY_BAR_WHOLE_REST, "ADJUDICATE")
    v_base = base.standing(cell, Q.EMPTY_BAR_WHOLE_REST, "ADJUDICATE")
    g = gray(doc, page)
    xa, xb = max(0, int(cb[0] - 0.5 * sp)), int(cb[2] + 0.5 * sp)
    ya, yb = max(0, int(lines[0] - 3.5 * sp)), int(lines[4] + 3.5 * sp)
    crop = cv2.cvtColor(g[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(g[ya:yb, xa:xb], 25) + 40), 140)
    checks = []
    w = cb[2] - cb[0]
    cols = lambda f0, f1: (int(cb[0] + f0 * w), int(cb[0] + f1 * w))
    for name, y in (("staff top line", lines[0]), ("staff bottom line", lines[4])):
        # LOCAL line (CLAUDE.md s10): the ink row found at two stretches of THIS bar, away from the heads and the
        # barlines; drawn as the straight line between them; then re-measured at a THIRD stretch it was not fitted on.
        o1, o2 = (ink_row(g, y, *cols(*f), thr) for f in ((0.45, 0.55), (0.80, 0.90)))
        if o1 is None or o2 is None:
            checks.append((cell, name, None)); continue
        x1, x2 = (cb[0] + 0.5 * w), (cb[0] + 0.85 * w)
        y1, y2 = y + o1, y + o2
        slope = (y2 - y1) / (x2 - x1)
        ya_, yb_ = y1 + slope * (cb[0] - x1), y1 + slope * (cb[2] - x1)
        cv2.line(crop, (int((cb[0] - xa) * SC), int(round((ya_ - ya) * SC)) + SC // 2),
                 (int((cb[2] - xa) * SC), int(round((yb_ - ya) * SC)) + SC // 2), MAGENTA, 1)
        ym = y1 + slope * (cb[0] + 0.65 * w - x1)
        o3 = ink_row(g, ym, *cols(0.62, 0.68), thr)
        checks.append((cell, name, None if o3 is None else round(abs(o3), 1)))
        # the control: the SAME re-measure on a line drawn 4 px off must read ~4 px off (value printed is the offset, expect 3-5) (a control that can fail)
        o4 = ink_row(g, ym + 4, *cols(0.62, 0.68), thr)
        checks.append((cell, name + " [control: 4 px off]", None if o4 is None else round(abs(o4), 1)))
    for x in (cb[0], cb[2]):
        xx = int(round((x - xa) * SC))
        cv2.line(crop, (xx, 0), (xx, crop.shape[0] - 1), GREY, 1)
    for h in heads:
        b = h.box_page
        cv2.rectangle(crop, (int((b[0] - xa) * SC), int((b[1] - ya) * SC)), (int((b[2] - xa) * SC), int((b[3] - ya) * SC)), ORANGE, 1)
    nm = staff_name(arm, skey)
    why = {"not_rest_shaped_or_positioned": "no mark in it shaped and placed like a whole rest",
           }.get(det.get("reason"), str(det.get("reason")))
    caps = [
        ("BEFORE (BASE, parent commit): the rescue ran first and found " + str(len(heads)) + " note head(s) in this bar, so the "
         "middle-of-the-bar whole-rest search never looked here; the record holds no search row for it. "
         "Whole-rest decision: " + ("none filed." if v_base is None else v_base["outcome"] + ".")),
        ("AFTER (ARM, 2.58): the whole-rest search ran first, looked in the middle of the bar and found nothing (" + why + "); "
         "then the same rescue found the same " + str(len(heads)) + " head(s). Whole-rest decision: "
         + (v_arm["outcome"] + (", reason " + str(v_arm.get("reason")) if v_arm else "") if v_arm else "none filed") + ". Notes unchanged."),
    ]
    head = f"{NAMES[doc]}, pdf page {page}  |  {nm}  |  system {system + 1}, staff {staff + 1}, bar {c + 1}"
    return dict(kind="rest", img=crop, head=head, caps=caps, checks=checks, cell=cell, tag=tag, doc=doc,
                sub="whole-rest search now ran before the rescue", nheads=len(heads))


def wrap(text, px, scale=0.46):
    words, out, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0] > px - 12 and cur:
            out.append(cur); cur = w
        else:
            cur = t
    if cur:
        out.append(cur)
    return out


def main(outdir, seed, dest):
    out = Path(outdir)
    tiles, other = [], []
    allrest = []
    for pb in sorted(out.glob("*.base.json")):
        tag = pb.name.split(".")[0]
        if tag.endswith("B") or not (out / f"{tag}.arm.json").exists():
            continue
        doc = "lit" if tag.startswith("lit") else "bra"
        base, arm = RD.load_run(str(pb)), RD.load_run(str(out / f"{tag}.arm.json"))
        rb = {o["subject"] for o in base.observations if o["quantity"] == Q.EMPTY_BAR_REST_SEARCH}
        new = sorted({o["subject"] for o in arm.observations if o["quantity"] == Q.EMPTY_BAR_REST_SEARCH} - rb)
        allrest += [(tag, doc, base, arm, c) for c in new]
        d = RD.diff_runs(base, arm)
        for cp in d["changed_pairs"]:
            other.append((tag, cp))
    print("rest-search rows only in ARM:", len(allrest), "| other changed glyph pairs:", len(other))
    rng = random.Random(seed)
    # spread: take round-robin over tags
    by_tag = collections.defaultdict(list)
    for t in allrest:
        by_tag[t[0]].append(t)
    for v in by_tag.values():
        rng.shuffle(v)
    picks = []
    while len(picks) < 12 and any(by_tag.values()):
        for tg in sorted(by_tag):
            if by_tag[tg] and len(picks) < 12:
                picks.append(by_tag[tg].pop())
    for tag, doc, base, arm, c in picks:
        tiles.append(rest_tile(tag, doc, base, arm, c))
    if not tiles:
        print("no tiles"); return
    W = max(t["img"].shape[1] for t in tiles)
    cells = []
    for i, t in enumerate(tiles, 1):
        hl = wrap(f"{i}. {t['head']}", W, 0.5)
        cl = [l for cap in t["caps"] for l in wrap(cap, W)]
        hh, chh = 8 + 20 * len(hl), 12 + 18 * len(cl)
        H = t["img"].shape[0]
        c = np.full((hh + H + chh, W, 3), 255, np.uint8)
        for j, l in enumerate(hl):
            cv2.putText(c, l, (4, 18 + 20 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLACK, 1, cv2.LINE_AA)
        c[hh:hh + H, :t["img"].shape[1]] = t["img"]
        for j, l in enumerate(cl):
            cv2.putText(c, l, (6, hh + H + 18 + 18 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.46, BLACK, 1, cv2.LINE_AA)
        cv2.rectangle(c, (0, 0), (W - 1, c.shape[0] - 1), (190, 190, 190), 1)
        cells.append(c)
    cols = 2
    rows = []
    for k in range(0, len(cells), cols):
        grp = cells[k:k + cols]
        h = max(c.shape[0] for c in grp)
        grp = [np.pad(c, ((0, h - c.shape[0]), (4, 4), (0, 0)), constant_values=255) for c in grp]
        while len(grp) < cols:
            grp.append(np.full((h, W + 8, 3), 255, np.uint8))
        rows.append(np.hstack(grp))
    w = max(r.shape[1] for r in rows)
    body = np.vstack([np.pad(r, ((6, 6), (0, w - r.shape[1]), (0, 0)), constant_values=255) for r in rows])
    legend = np.full((110, body.shape[1], 3), 255, np.uint8)
    for j, txt in enumerate((
            f"ROADMAP 2.58 GATHER-order A/B, GATHER+ADJUDICATE only. {len(allrest)} bars changed in ALL runs; a seeded {len(tiles)} shown. NOT judged -- Sean decides.",
            "ORANGE box = the rescued note head(s) in the bar.  MAGENTA line = the staff's top and bottom line (record geometry); GREY = the bar's left/right cell edge.",
            "Every coloured line is 1 px at the page's own coordinates; its offset from the nearest ink row (px) is printed on stdout.")):
        cv2.putText(legend, txt, (8, 24 + 28 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLACK, 1, cv2.LINE_AA)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), np.vstack([legend, body]))
    allc = [c for t in tiles for c in t["checks"]]
    print("line checks (offset px to nearest ink row; None = no ink beside it):")
    for c in allc:
        print("  ", c)
    print("tiles:", [(t["tag"], t["cell"], t["nheads"]) for t in tiles])
    print("wrote", dest)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007,
         a[a.index("--dest") + 1] if "--dest" in a else str(ROOT / "out/print/ab_2.58_gather_order.png"))
