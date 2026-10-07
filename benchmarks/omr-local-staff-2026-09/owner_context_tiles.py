"""night 2026-10-07: the two OWNER tiles of `out/print/night_1007_sample.png` (1 Litolff p10, 5 Brahms p7) redrawn WITH
CONTEXT for Sean ("without context I have no idea what is which system"): the whole bar, ALL staves of the system, each
named at the left (instrument from the record's own verdict, else "staff N, unnamed"), five lines per staff, the head
circled + arrowed, the FILED staff outlined blue, the NEW owner outlined green.  Reads two small JSONs written by
`ext.py` (one load_record per record) and renders from the gather-frame page.  Every drawn line is re-measured against
the page's pixel rows and the offset printed.

  python3 owner_context_tiles.py <lit.json> <brh.json>
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from frame import render_page_matching_gather
from tools.library.score_library import library_root  # noqa

OUT = HERE.parents[1] / "out/print/owner_context_tiles_1_5.png"
LIB = library_root()
PDF = {"lit": LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brh": LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
FONT = "/System/Library/Fonts/Helvetica.ttc"
BLUE, GREEN, ORANGE, LINE = (0, 90, 255), (0, 160, 0), (255, 120, 0), (200, 60, 60)
MAXH = 1750


def font(n):
    return ImageFont.truetype(FONT, n)


def staff_name(k, st):
    iv = st.get("instrument_v") or {}
    ml = [m["value"] for m in st.get("margin_label", [])]
    if iv.get("outcome") == "decided" and iv.get("value"):
        nm = iv["value"]["name"]
        if nm == "Violin" and ml:
            nm = f"Violin ({ml[0]})"
        return f"staff {k + 1}: {nm}"
    return f"staff {k + 1}, unnamed" + (f" (margin: \"{ml[0]}\")" if ml else "")


def bars_near(gray, staves, cx, y0, y1):
    """x of barlines: columns dark through >=60% of the rows inside the staff bodies of >=60% of the staves."""
    hit = np.ones(gray.shape[1], bool)
    frac = np.zeros(gray.shape[1])
    for ys in staves:
        top, bot = ys[0], ys[-1]
        seg = gray[int(top) + 2:int(bot) - 1, :] < 110
        frac += (seg.mean(axis=0) >= 0.9)
    cols = np.where(frac >= 0.6 * len(staves))[0]
    groups, cur = [], [cols[0]]
    for c in cols[1:]:
        if c <= cur[-1] + 3:
            cur.append(c)
        else:
            groups.append(cur); cur = [c]
    groups.append(cur)
    xs = [float(np.mean(g)) for g in groups]
    left = max([x for x in xs if x < cx - 5], default=None)
    right = min([x for x in xs if x > cx + 5], default=None)
    return left, right, xs


def tile(key, d, subject, tag):
    N = d["new"]
    _, page, sysi, staff, _, _ = subject.split("/")
    page = int(page)
    pi = render_page_matching_gather(PDF[key], page, 600)
    gray = cv2.cvtColor(np.asarray(pi.rgb), cv2.COLOR_RGB2GRAY) if np.asarray(pi.rgb).ndim == 3 else np.asarray(pi.rgb)
    st = N["staves"]
    keys = sorted(st, key=lambda s: int(s.split("/")[-1]))
    lines = {int(k.split("/")[-1]): st[k]["staff_lines"][0]["value"] for k in keys}
    box = [o for o in N["obs"] if o["q"] == "glyph_box"][0]["detail"]["bbox_page_px"]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    sp = np.median([(l[-1] - l[0]) / 4 for l in lines.values()])
    bl, br, allx = bars_near(gray, list(lines.values()), cx, 0, 0)
    print(tag, "barlines near head:", bl, br, "head x", round(cx), "spacing", round(sp, 1))
    if bl is None or br is None:
        bl, br = cx - 8 * sp, cx + 8 * sp
    filed, new = int(staff), int(N["verdicts"]["glyph_owner"]["value"].split("/")[-1])
    x0, x1 = int(bl - 0.6 * sp), int(br + 0.6 * sp)
    y0, y1 = int(lines[0][0] - 2.5 * sp), int(lines[max(lines)][-1] + 2.5 * sp)
    crop = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    scale = min(MAXH / crop.shape[0], 1.6)
    big = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    # pixel-row check of each drawn line (columns clear of the head, inside the bar)
    checks = []
    thr = 120
    for k, ls in lines.items():
        for y in ls:
            offs = []
            for (a, b) in ((bl + 2 * sp, cx - 1.5 * sp), (cx + 1.5 * sp, br - 2 * sp)):
                a, b = int(a), int(b)
                if b <= a:
                    continue
                rows = [r for r in range(int(y) - 7, int(y) + 8) if (gray[r, a:b] < thr).mean() >= 0.5]
                if rows:
                    offs.append(min((r - y for r in rows), key=abs))
            checks.append((k, round(float(y), 1), None if not offs else round(float(np.mean(offs)), 1)))
    # LOCAL snap (CLAUDE.md: measure against the staff locally): draw each line at the ink row measured beside the head
    snapped = {}
    for (k, y, o) in checks:
        snapped.setdefault(k, []).append(y + (o if o is not None else 0.0))
    lines_rec = lines
    resid = []
    for k, ys in snapped.items():
        for y in ys:
            wins = [(int(a), int(b)) for a, b in ((bl + 2 * sp, cx - 1.5 * sp), (cx + 1.5 * sp, br - 2 * sp)) if b > a]
            rr = [r for r in range(int(round(y)) - 3, int(round(y)) + 4) if any((gray[r, a:b] < thr).mean() >= 0.5 for a, b in wins)]
            resid.append(min((r - y for r in rr), key=abs) if rr else None)
    print(tag, "after local snap: drawn lines with no ink row within 3px:", sum(r is None for r in resid),
          "max |residual| %.1f px" % max([abs(r) for r in resid if r is not None] or [0]))
    lines = {k: v for k, v in snapped.items()}
    bad = [c for c in checks if c[2] is None or abs(c[2]) > 2]
    print(tag, "line check: %d lines, max |offset| %.1f px, off>2px or no ink: %s" % (
        len(checks), max([abs(c[2]) for c in checks if c[2] is not None] or [0]), bad))
    # canvas
    G = int(330 * 1.0)
    cap_h = 330
    W = max(G + big.shape[1] + 20, 700)
    H = big.shape[0] + cap_h
    im = Image.new("RGB", (W, H), "white")
    im.paste(Image.fromarray(cv2.cvtColor(big, cv2.COLOR_BGR2RGB)), (G, 0))
    dr = ImageDraw.Draw(im)
    fx = lambda x: G + (x - x0) * scale
    fy = lambda y: (y - y0) * scale
    for k, ls in lines.items():
        for y in ls:
            dr.line([(G, fy(y)), (G + big.shape[1], fy(y))], fill=LINE, width=1)
        col = BLUE if k == filed else GREEN if k == new else None
        label = staff_name(k, st["staff/%s/%s/%d" % (page, sysi, k)])
        ty = fy((ls[0] + ls[-1]) / 2) - 8
        dr.text((6, ty), label[:34], fill=(0, 0, 0) if col is None else col, font=font(15))
        if col:
            dr.rectangle([G + 1, fy(ls[0] - 0.9 * sp), G + big.shape[1] - 2, fy(ls[-1] + 0.9 * sp)], outline=col, width=4)
            dr.text((6, ty + 18), "FILED here" if col == BLUE else "NEW owner", fill=col, font=font(15))
    # head circle + arrow
    r = max(18, 0.9 * sp * scale)
    hx, hy = fx(cx), fy(cy)
    dr.ellipse([hx - r, hy - r, hx + r, hy + r], outline=ORANGE, width=3)
    ax, ay = hx + r + 70, hy - r - 50
    dr.line([(ax, ay), (hx + r * 0.72, hy - r * 0.72)], fill=ORANGE, width=4)
    tip = (hx + r * 0.72, hy - r * 0.72)
    dr.polygon([tip, (tip[0] + 18, tip[1] - 4), (tip[0] + 4, tip[1] - 18)], fill=ORANGE)
    dr.text((ax + 4, ay - 18), "the note", fill=ORANGE, font=font(17))
    for x in (bl, br):
        pass
    return im, dict(checks=checks, filed=filed, new=new, cap_y=big.shape[0], name_new=staff_name(new, st["staff/%s/%s/%d" % (page, sysi, new)]),
                    name_filed=staff_name(filed, st["staff/%s/%s/%d" % (page, sysi, filed)]), crop=(x0, y0, x1, y1), scale=scale, head=(cx, cy), sp=sp,
                    gray=gray)


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


def main(lit, brh):
    L = json.loads(Path(lit).read_text()); B = json.loads(Path(brh).read_text())
    t1, m1 = tile("lit", L, "glyph/10/1/8/9/6", "T1 Litolff p10")
    t5, m5 = tile("brh", B, "glyph/7/0/6/5/13", "T5 Brahms p7")
    caps = {
        1: ("TILE 1  (Beethoven 5, Litolff, PDF page 10, system 2). This note was found in the strip of %s. The new rule says it belongs to %s "
            "because the very same mark was also found in that staff's own strip, where the ledger lines name it as that staff's note, and the rule gives "
            "both copies to that staff. The old run gave no owner." % (m1["name_filed"], m1["name_new"])),
        5: ("TILE 5  (Brahms 1, Breitkopf, PDF page 7, system 1). This note was found in the strip of %s. The new rule says it belongs to %s "
            "because the very same mark was also found in that staff's own strip, where the ledger lines name it as that staff's note, and the rule gives "
            "both copies to that staff. The old run gave no owner." % (m5["name_filed"], m5["name_new"])),
    }
    tiles = []
    for im, m, n in ((t1, m1, 1), (t5, m5, 5)):
        W = im.size[0]
        dr = ImageDraw.Draw(im)
        f = font(17)
        lines = wrap(caps[n], f, W - 20, dr)
        y = m["cap_y"] + 8
        for ln in lines:
            dr.text((10, y), ln, fill=(0, 0, 0), font=f)
            y += 22
        # key
        dr.rectangle([10, y + 6, 30, y + 22], outline=BLUE, width=4); dr.text((38, y + 5), "staff it was filed on", fill=BLUE, font=font(16))
        dr.rectangle([240, y + 6, 260, y + 22], outline=GREEN, width=4); dr.text((268, y + 5), "staff the new rule picks", fill=GREEN, font=font(16))
        dr.ellipse([500, y + 4, 520, y + 24], outline=ORANGE, width=3); dr.text((528, y + 5), "the note", fill=ORANGE, font=font(16))
        tiles.append(im)
    # zoom insets are saved separately for the report check, not on the sheet
    Wt = sum(t.size[0] for t in tiles) + 30
    Ht = max(t.size[1] for t in tiles)
    sheet = Image.new("RGB", (Wt, Ht), "white")
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0)); x += t.size[0] + 30
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print("saved", OUT, sheet.size)
    for tag, m in (("T1", m1), ("T5", m5)):
        x0, y0, x1, y1 = m["crop"]
        cx, cy = m["head"]; sp = m["sp"]
        z = m["gray"][int(cy - 4 * sp):int(cy + 4 * sp), int(cx - 5 * sp):int(cx + 5 * sp)]
        Image.fromarray(z).resize((z.shape[1] * 3, z.shape[0] * 3), Image.NEAREST).save(
            Path("/private/tmp/claude-501/s") / f"zoom_{tag}.png")


if __name__ == "__main__":
    main(*sys.argv[1:3])
