"""lane-farhead-2-9 (2026-10-07): ONE sheet, ONE column, 1400 px wide, caption text 20 px. Tiles 2 and 9 of Sean's `farhead_5_6.png` first
(Flute p18 `18/1/0/5/21`; Horn p18 `18/0/5/4/6`), then 10 seeded Brahms/Litolff heads that `look_where_it_must_be` RESCUES (abstain -> answer
because the hidden ledger's jut was found). Each tile: the page at the gather's frame (600 dpi, x2), the filed staff's five lines (azure, 1 px,
drawn ON the ink), the neighbouring staves (named), the head's box (magenta), the row the hidden ledger must be on (orange line, labelled), the jut ink
found (green circles), for tile 9 the accent that was counted as a ledger (red box), the instrument names, the answer in WORDS before and after, and
every drawn line checked against the pixel rows (printed; flagged if off by more than 4 px).

  python3 farhead_2_9_sheet.py <x7 brahms> <x7 litolff> <census brahms.json> <census litolff.json> <names brahms> <names litolff> <out.png> [--seed N]
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import farhead_5_6_diag as D
import farhead_5_6_sheet as FS
import night_1007_sheet as NS
import overnight_1004_report as R
from tools.omr.annotate import far_head_owner as FO, ledger_grid as lg

W, SC, FONT_PX = 1400, 2, 20
AZURE, MAGENTA, ORANGE, GREEN, RED, GREY = (255, 150, 0), (255, 0, 255), (0, 140, 255), (0, 170, 0), (0, 0, 255), (90, 90, 90)
FIRST = [("brahms", "glyph/18/1/0/5/21"), ("brahms", "glyph/18/0/5/4/6")]
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", FONT_PX)
FONTB = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", FONT_PX)
REASON = {"no_line_at_the_note_box": "no answer: it found no line at the note",
          "count_does_not_fit": "no answer: the ledgers it counted do not fit together"}


def words(pos, reason):
    if pos is not None:
        return NS.words_pos(pos)
    for k, v in REASON.items():
        if reason.startswith(k):
            return v
    return "no answer (" + reason[:60] + ")"


def wrap(draw, text, font, width):
    out, line = [], ""
    for w in text.split(" "):
        t = (line + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            line = t
        else:
            out.append(line)
            line = w
    return out + [line]


_WARM = set()


def read_pair(rep, data, s):
    """the page's shape context is pooled from the page's other far heads (the census reads every head in page order, so it is
    warm by the time it reaches this one): warm it the same way, with the page's first far head, before the first read."""
    key = (id(rep), R.page_of(s))
    if key not in _WARM:
        _WARM.add(key)
        first = sorted((x for x, g in data["glyphs"].items() if R.page_of(x) == key[1] and R.is_far(g) and "box" in g and ("fh" in g or "fh_abs" in g)),
                       key=lambda x: tuple(int(v) for v in x.split("/")[1:]))
        for x in first[:1]:
            D.read_one(rep, data, x)
    res = {}
    for on in (False, True):
        D.FH.READER_KEYWORDS["look_where_it_must_be"] = on
        g, r, cap, gl, ctx = D.read_one(rep, data, s)
        res[on] = (r["pos"], r["reason"], (r.get("detail") or {}).get("note_first") or {}, cap)
    D.FH.READER_KEYWORDS["look_where_it_must_be"] = True
    return g, res, gl, ctx


def neighbours(data, s):
    """staff keys of the same page+system whose lines fall in view (filled by the caller)."""
    _, p, sy, sk = ("staff/" + "/".join(s.split("/")[1:4])).split("/")
    return [(k, v) for k, v in data["staff_lines"].items() if k.startswith("staff/%s/%s/" % (p, sy))]


def tile(which, s, rep, data, names, tag, kind):
    g, res, gl, ctx = read_pair(rep, data, s)
    page = R.page_of(s)
    gray = rep.gray_of(page)
    box = g["box"]
    sp = res[True][3]["sp"] if res[True][3] else 27.0
    sign = res[True][3].get("sign", -1.0)
    x0, y0, x1, y1 = box
    top, bot = min(gl), max(gl)
    cx = (x0 + x1) / 2
    X0, X1 = int(cx - W / SC / 2), int(cx + W / SC / 2)
    if y1 < top:
        Y0, Y1 = int(y0 - 3.0 * sp), int(bot + 1.0 * sp)
    else:
        Y0, Y1 = int(top - 1.0 * sp), int(y1 + 3.0 * sp)
    Y0, Y1 = max(0, Y0), min(gray.shape[0], Y1)
    crop = cv2.cvtColor(gray[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
    crop = cv2.resize(crop, None, fx=SC, fy=SC, interpolation=cv2.INTER_NEAREST)
    P = lambda x, y: (int(round((x - X0) * SC)), int(round((y - Y0) * SC + SC / 2)))
    for yy in gl:
        cv2.line(crop, P(X0, yy), P(X1, yy), AZURE, 1)
    cv2.rectangle(crop, P(x0, y0), P(x1, y1), MAGENTA, 2)
    pil_notes = []                                      # (x, y, text, colour) drawn with PIL afterwards
    nf_on, nf_off = res[True][2], res[False][2]
    look = nf_on.get("hidden_ledger_look") or {}
    chk = []
    if look:
        ye = look["expected"]["y"]
        cv2.line(crop, P(x0 - 0.9 * sp, ye), P(x1 + 0.9 * sp, ye), ORANGE, 2)
        pil_notes.append((int((x1 + 0.95 * sp - X0) * SC), int((ye - Y0) * SC) - 12, "row the ledger must be on", ORANGE))
        for side in ("left", "right"):
            j = look.get(side) or {}
            if j.get("ok"):
                xm, ym = (j["x_from"] + j["x_to"]) / 2.0, j["y"]
                cv2.circle(crop, P(xm, ym), int(0.55 * sp * SC), GREEN, 3)
        got = look.get("y")
        if got is not None:
            chk.append("expected row %.1f, jut ink centre %.1f (%.1f px apart), jut found on %d side(s)" % (ye, got, abs(got - ye), look.get("sides", 0)))
    # tile 9: the accent that was counted as a ledger
    own_words = None
    if kind == "artic":
        ab = [b for (_s, c, b) in rep.boxes_by_page[page] if lg.is_articulation_class(c) and b[0] < x1 + 3 * sp and b[2] > x0 - 3 * sp
              and (min(y0, y1) - 3 * sp) < b[1] < (max(y0, y1) + 3 * sp + 40)]
        for b in ab:
            cv2.rectangle(crop, P(b[0], b[1]), P(b[2], b[3]), RED, 3)
        for yb in nf_off.get("between") or []:
            cv2.line(crop, P(x0 - 0.9 * sp, yb), P(x1 + 0.9 * sp, yb), ORANGE, 2)
            pil_notes.append((int((x0 - 0.9 * sp - X0) * SC), int((yb - Y0) * SC) - 12, "the rung counted as ledger 1", ORANGE))
        # the staff on the other side of the head: read the head toward it
        nb = [(k, v) for k, v in neighbours(data, s) if k != "staff/" + "/".join(s.split("/")[1:4])]
        cand = {}
        filed = "staff/" + "/".join(s.split("/")[1:4])
        cand[filed] = FO.read_toward(ctx, s, box, g.get("cls"), data["staff_lines"][filed])
        ks = sorted(nb, key=lambda kv: abs((min(kv[1]) + max(kv[1])) / 2 - (y0 + y1) / 2))
        if ks:
            other = ks[0][0]
            cand[other] = FO.read_toward(ctx, s, box, g.get("cls"), data["staff_lines"][other])
            ow, word = FO.decide(cand)
            own_words = ("read toward %s: %s;  toward %s: %s;  so the owner by its ledgers is %s" % (
                names.get(filed) or "?", words(cand[filed]["pos"], cand[filed]["reason"]), names.get(other) or "?",
                words(cand[other]["pos"], cand[other]["reason"]), (names.get(ow) or ow) if ow else "undecided (%s)" % word))
    # every staff in view named at the left
    for k, v in neighbours(data, s):
        mid = (min(v) + max(v)) / 2
        if Y0 - 2 * sp < mid < Y1 + 2 * sp:
            lab = (names.get(k) or "staff with no name read") + ("   <- the staff the head is filed on" if k == "staff/" + "/".join(s.split("/")[1:4]) else "")
            pil_notes.append((6, int((mid - Y0) * SC) - 11, lab, (0, 0, 0)))
    # lines vs pixel rows
    offs = [FS.row_check(gray, yy, box, sp) for yy in gl]
    chk.append("5 drawn staff lines vs pixel rows: " + ",".join("-" if o is None else "%.0f" % o for o in offs) + " px (- = no flank ink to measure)")
    bad = [o for o in offs if o is not None and abs(o) > 4]
    if bad:
        chk.append("OFF by more than 4 px: " + str(bad))
    img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(img, "RGBA")
    for (x, y, t, col) in pil_notes:
        tw = d.textlength(t, font=FONT)
        d.rectangle((x - 2, y - 1, x + tw + 4, y + FONT_PX + 3), fill=(255, 255, 255, 215))
        d.text((x, y), t, font=FONT, fill=(col[2], col[1], col[0]))
    head = "TILE %s   %s   %s   (page %d, system %d, staff %d from the top)" % (tag, "Brahms" if which == "brahms" else "Beethoven 5 (Litolff)", s, page, int(s.split("/")[2]) + 1, int(s.split("/")[3]) + 1)
    filed = "staff/" + "/".join(s.split("/")[1:4])
    lines = [(head, FONTB, (0, 0, 0)),
             ("Filed on: " + (names.get(filed) or "a staff with no name read"), FONT, (0, 0, 0)),
             ("BEFORE: " + words(res[False][0], res[False][1]), FONT, (200, 0, 0)),
             ("AFTER: " + words(res[True][0], res[True][1]) + ("   (" + own_words + ")" if own_words else ""), FONT, (0, 130, 0))]
    lines += [("Lines checked: " + c, FONT, (70, 70, 70)) for c in chk]
    lines.append(("azure = the bar's five staff lines;  magenta box = the note;  orange = the row a ledger must be on;  green circles = the ledger's thin flat end found jutting out;  red box = an accent", FONT, (90, 90, 90)))
    m = Image.new("RGB", (W, 10), "white")
    dm = ImageDraw.Draw(m)
    rows = []
    for t, f, c in lines:
        for ln in wrap(dm, t, f, W - 12):
            rows.append((ln, f, c))
    pad = (FONT_PX + 6) * len(rows) + 10
    out = Image.new("RGB", (W, pad + img.height), "white")
    do = ImageDraw.Draw(out)
    for i, (t, f, c) in enumerate(rows):
        do.text((6, 4 + i * (FONT_PX + 6)), t, font=f, fill=c)
    out.paste(img.crop((0, 0, W, img.height)), (0, pad))
    return out, dict(subject=s, doc=which, before=res[False][:2], after=res[True][:2], look=json.loads(json.dumps(look, default=str)) if look else None,
                     staff_offsets=offs, checks=chk, own=own_words)


def main(xb, xl, cb, cl, nb, nl, out_png, seed=20261007):
    D_ = {"brahms": D.load(xb, "brahms1-breitkopf"), "litolff": D.load(xl, "beethoven5-litolff")}
    names = {"brahms": json.loads(Path(nb).read_text()), "litolff": json.loads(Path(nl).read_text())}
    cen = {"brahms": json.loads(Path(cb).read_text()), "litolff": json.loads(Path(cl).read_text())}
    resc = [(w, s) for w in ("brahms", "litolff") for s in cen[w]["rescued"]
            if cen[w]["res"][s].get("how") == "hidden_ledger_jut_looked_for" and (w, s) not in FIRST]
    lostp = [(w, s) for w in ("brahms", "litolff") for s in cen[w]["lost"]]
    rng = random.Random(seed)
    refus = rng.sample(lostp, min(10 - len(resc), len(lostp)))
    plan = [(FIRST[0], "look", " (Sean's tile 2)"), (FIRST[1], "artic", " (Sean's tile 9)")]
    plan += [(p, "look", " (rescued: hidden ledger found by its jut)") for p in resc]
    plan += [(p, "artic", " (seeded: a mark's stroke no longer counted as a ledger)") for p in refus]
    tiles, report = [], []
    for i, ((w, s), kind, tag) in enumerate(plan, 1):
        data, rep = D_[w]
        img, rp = tile(w, s, rep, data, names[w], str(i) + tag, kind)
        tiles.append(img)
        report.append(rp)
        print(i, w, s, rp["before"], "->", rp["after"], rp["checks"][:1], flush=True)
    H = sum(t.height + 14 for t in tiles)
    sheet = Image.new("RGB", (W, H), (235, 235, 235))
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y))
        y += t.height + 14
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    Path(out_png).with_suffix(".json").write_text(json.dumps(report, default=str))
    print("wrote", out_png, sheet.size, "rescues", len(resc), "refusal pool", len(lostp))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(*a[:7], seed=int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007)
