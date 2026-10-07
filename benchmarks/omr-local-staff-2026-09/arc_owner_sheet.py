"""lane-arc-owner-regression: ONE sheet of arc-owner tiles for Sean.  Each tile = the arc's bar, the staves around it (all named at the
left, the two staves in question outlined), the ARC in orange, the heads at its two ENDS circled, and the owner in WORDS:
10-06 (BASE), 10-07 (NEW), and the CURRENT code.  Every drawn staff line is re-measured against the page's pixel rows (local snap)
and the worst offset printed.  GATHER+ADJUDICATE only.

  python3 arc_owner_sheet.py <brh_new.pkl> <brh_base.pkl> <out.png> <arc subject> [<arc subject> ...]
Reads `out/arc_owner_regression.json` for the current-code answer of each arc.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arc_owner_replay as R
from frame import render_page_matching_gather
from tools.library.score_library import library_root

PDF = library_root() / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
FONT = "/System/Library/Fonts/Helvetica.ttc"
ORANGE, BLUE, GREEN, RED, GREY, LINE = (255, 120, 0), (0, 90, 255), (0, 150, 0), (220, 0, 0), (110, 110, 110), (200, 60, 60)
NAME_W, TILE_W, SC = 215, 500, 0.65
LABEL = {"glyph/5/0/6/5/11": "TILE 8 on Sean's sheet", "glyph/5/0/1/5/1": "TILE 7 on Sean's sheet"}
NOTE = {"glyph/5/0/6/5/11": "NOT FIXED by the arc rule: the two end heads are owned by DIFFERENT staves (left one: Horn, right one: the unnamed staff, by the ledger reader). Both sit at the same height just under the Horn's bottom line, so the right one is the ownership fault."}
_pages = {}


def font(n):
    return ImageFont.truetype(FONT, n)


def gray(page):
    if page not in _pages:
        _pages[page] = cv2.cvtColor(np.asarray(render_page_matching_gather(PDF, page, 600).rgb), cv2.COLOR_RGB2GRAY)
    return _pages[page]


def wrap(text, f, width, dr):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if dr.textlength(t, font=f) <= width:
            cur = t
        else:
            out.append(cur); cur = w
    out.append(cur)
    return out


class Data:
    def __init__(self, new_pkl):
        d = R.load(new_pkl)
        self.lines, self.name, self.spacing, self.arcbox, self.heads, self.own = {}, {}, {}, {}, {}, {}
        for o in d["obs"]:
            q, s = o["quantity"], o["subject"]
            if q == "staff_lines":
                self.lines[s] = [float(y) for y in o["value"]]
            elif q == "staff_spacing":
                self.spacing[s] = float(o["value"])
            elif q == "arc_box":
                self.arcbox[s] = o["detail"]["bbox_page_px"]
            elif q == "glyph_box":
                self.heads.setdefault(tuple(s.split("/")[1:3]), []).append((s, o["detail"]["bbox_page_px"]))
        for v in d["verdicts"]:
            if v["quantity"] == "instrument" and v["outcome"] == "decided" and v.get("value"):
                self.name[v["subject"]] = v["value"]["name"] if isinstance(v["value"], dict) else str(v["value"])
            elif v["quantity"] == "glyph_owner" and v["outcome"] == "decided":
                self.own[v["subject"]] = v["value"]

    def label(self, key):
        _, p, s, k = key.split("/")
        return f"{self.name.get(key) or 'the unnamed staff'} (system {int(s) + 1}, staff {int(k) + 1} from the top)"

    def end_heads(self, arc):
        """(left, right) end head subjects, by the same test the decision makes."""
        from tools.omr.staged.adjudicators.notehead_precision import TOO_NARROW_MIN_SPACES
        ab = self.arcbox[arc]
        sysk = tuple(arc.split("/")[1:3])
        hs = self.heads[sysk]
        mean_w = sum(b[2] - b[0] for _s, b in hs) / len(hs)
        pad = 0.25 * mean_w
        near = []
        for s, b in hs:
            ow = self.own.get(s) or "staff/" + "/".join(s.split("/")[1:4])
            sp = self.spacing.get(ow)
            cx = (b[0] + b[2]) / 2
            if not sp or (b[2] - b[0]) < TOO_NARROW_MIN_SPACES * sp or not (ab[0] - pad <= cx <= ab[2] + pad):
                continue
            gap = max(ab[1] - b[3], b[1] - ab[3], 0.0)
            if gap / sp <= 0.75:
                near.append((cx, s, b))
        if not near:
            return []
        lo, hi = min(c for c, _, _ in near), max(c for c, _, _ in near)
        return [(s, b) for c, s, b in near if c <= lo + 0.5 * mean_w or c >= hi - 0.5 * mean_w]


def tile(D, arc, n, base_owner, new_owner, now_owner, now_reason, kind):
    _, page, sysi, filed, _, _ = arc.split("/")
    page = int(page)
    G = gray(page)
    ab = D.arcbox[arc]
    keys = sorted((k for k in D.lines if k.startswith(f"staff/{page}/{sysi}/")), key=lambda k: int(k.split("/")[-1]))
    role = {}
    for tag, key in (("base", base_owner), ("new", new_owner), ("now", now_owner)):
        role.setdefault(key, []).append(tag)
    inq = sorted({int(k.split("/")[-1]) for k in list(role) + [f"staff/{page}/{sysi}/{filed}"]})
    lo, hi = max(0, min(inq) - 1), min(len(keys) - 1, max(inq) + 1)
    show = keys[lo:hi + 1]
    sp = float(np.median([D.spacing.get(k, 28.0) for k in show]))
    x0, x1 = int(ab[0] - 1.2 * sp), int(ab[2] + 1.2 * sp)
    y0, y1 = int(D.lines[show[0]][0] - 2.2 * sp), int(D.lines[show[-1]][-1] + 2.2 * sp)
    crop = cv2.cvtColor(G[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    scale = min(SC, TILE_W / crop.shape[1])
    big = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    # local snap of each staff line to the ink row beside the notes (page pixel rows) and the residual
    resid, snapped = [], {}
    for k in show:
        ys = []
        for y in D.lines[k]:
            rows = [r for r in range(int(y) - 6, int(y) + 7) if (G[r, x0 + 4:x1 - 4] < 120).mean() >= 0.5]
            if rows:
                best = min(rows, key=lambda r: abs(r - y)); ys.append(float(best)); resid.append(best - y)
            else:
                ys.append(float(y)); resid.append(None)
        snapped[k] = ys
    maxoff = max([abs(r) for r in resid if r is not None] or [0.0])
    noink = sum(r is None for r in resid)
    cap_h = 250
    W = NAME_W + TILE_W + 8
    H = big.shape[0] + cap_h
    im = Image.new("RGB", (W, H), "white")
    im.paste(Image.fromarray(cv2.cvtColor(big, cv2.COLOR_BGR2RGB)), (NAME_W, 0))
    dr = ImageDraw.Draw(im)
    fx = lambda x: NAME_W + (x - x0) * scale
    fy = lambda y: (y - y0) * scale
    cols = {"base": BLUE, "new": RED, "now": GREEN}
    for k in show:
        for y in snapped[k]:
            dr.line([(NAME_W, fy(y)), (NAME_W + big.shape[1], fy(y))], fill=LINE, width=1)
        mid = fy((snapped[k][0] + snapped[k][-1]) / 2)
        num = int(k.split("/")[-1]) + 1
        dr.text((6, mid - 9), f"{D.name.get(k) or 'unnamed'} (staff {num})", fill=(0, 0, 0), font=font(14))
        for j, tag in enumerate(role.get(k, [])):
            top, bot = fy(snapped[k][0] - 0.9 * sp), fy(snapped[k][-1] + 0.9 * sp)
            dr.rectangle([NAME_W + 1 + 4 * j, top + 4 * j, NAME_W + big.shape[1] - 2 - 4 * j, bot - 4 * j], outline=cols[tag], width=2)
        if k == f"staff/{page}/{sysi}/{filed}":
            dr.text((6, mid + 8), "arc was cut from here", fill=GREY, font=font(12))
    dr.rectangle([fx(ab[0]), fy(ab[1]), fx(ab[2]), fy(ab[3])], outline=ORANGE, width=3)
    for s, b in D.end_heads(arc):
        cx, cy = fx((b[0] + b[2]) / 2), fy((b[1] + b[3]) / 2)
        r = max(14, 0.8 * sp * scale)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(160, 0, 200), width=3)
    f = font(15)
    txt = (f"{LABEL.get(arc, 'Tile ' + str(n))}  (Brahms 1, PDF page {page}, system {int(sysi) + 1}; this is a {kind}).  10-06 gave it to {D.label(base_owner)}.  "
           f"10-07 gives it to {D.label(new_owner)}.  The code now gives it to {D.label(now_owner)} ({now_reason}).")
    y = big.shape[0] + 6
    for ln in wrap(txt, f, W - 16, dr):
        dr.text((8, y), ln, fill=(0, 0, 0), font=f); y += 19
    if arc in NOTE:
        for ln in wrap(NOTE[arc], f, W - 16, dr):
            dr.text((8, y), ln, fill=(160, 0, 0), font=f); y += 19
    dr.text((8, y + 2), "Orange box = the arc. Purple circles = the heads at its two ends. Outlines: blue = 10-06 owner, red = 10-07 owner, green = now.", fill=(60, 60, 60), font=font(12))
    dr.text((8, y + 20), f"Staff lines drawn on the ink rows: {len(resid)} lines checked, worst offset {maxoff:.1f} px, {noink} with no ink to check.", fill=(60, 60, 60), font=font(12))
    return im, dict(arc=arc, lines_checked=len(resid), worst_offset_px=round(maxoff, 1), no_ink=noink)


def main(new_pkl, base_pkl, out, *arcs):
    D = Data(new_pkl)
    reg = json.loads((HERE / "out/arc_owner_regression.json").read_text())
    pool = {r["arc"]: r for r in reg["seventeen"]}
    for c in reg["brahms"]["changed"]:       # arcs 10-06 and 10-07 agreed on that the current code now moves
        pool.setdefault(c["arc"], dict(arc=c["arc"], base=c["record"][0], record_new=c["record"][0], fixed=c["now"][0], reason=c["now"][1]))
    now_reason = {}
    nv = {v["subject"]: v for v in R.load(new_pkl)["verdicts"] if v["quantity"] == "arc_owner"}
    kinds = {v["subject"]: (v["value"] if isinstance(v["value"], str) else "arc") for v in R.load(new_pkl)["verdicts"] if v["quantity"] == "arc_kind"}
    ims, meta = [], []
    for i, a in enumerate(arcs, 1):
        r = pool[a]
        im, m = tile(D, a, i, r["base"], r["record_new"], r["fixed"], r["reason"], kinds.get(a, "arc"))
        ims.append(im); meta.append(m)
    cols = 4
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    Wt = max(t.size[0] for t in ims) * cols + 10 * (cols - 1)
    Ht = sum(max(t.size[1] for t in row) for row in rows) + 10 * (len(rows) - 1)
    sheet = Image.new("RGB", (Wt, Ht), "white")
    y = 0
    for row in rows:
        x = 0
        for t in row:
            sheet.paste(t, (x, y)); x += max(q.size[0] for q in ims) + 10
        y += max(t.size[1] for t in row) + 10
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("saved", out, sheet.size)
    print(json.dumps(meta))


if __name__ == "__main__":
    main(*sys.argv[1:5], *sys.argv[5:])
