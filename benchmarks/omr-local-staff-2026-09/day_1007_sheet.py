"""day 2026-10-07: ONE set of sheets for Sean, 12 seeded tiles on pages the rules were NOT written on (Litolff pp.4-16,
Brahms pp.2-26), NEW (`...20261007-day`) vs BASE (`...20261007-night`), GATHER+ADJUDICATE verdicts only.

Mix (the biggest kinds of change, 2-3 each): 3 arcs refused as a staff line, 3 dots (unread -> lengthening, lengthening ->
staccato, dot's owner moved), 2 far heads (BASE gave up -> answered; answered -> NEW gave up), 2 owner changes, 2 other (a
meter worked out from the bars, a bar's voices).  Each tile is ONE COLUMN, 1400 px wide: a header, the WHOLE SYSTEM with the
staff names at the left (the subject boxed), then a BASE panel and a NEW panel (zoomed, same window), each with its words.
Text is >= 20 px.  Every drawn line is 1 px and is re-measured against the pixel rows of the page (offset printed).
Images are cut between tiles so none is taller than 6000 px: out/print/day_1007_sample_1.png, _2.png, ...

  python3 day_1007_sheet.py <scratch dir with x/*.json> [--seed 20261007]
"""
from __future__ import annotations
import collections, json, os, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import day_1007_report as DR
import night_1007_sheet as S
import farhead_note_first_sheet as NF
import overnight_1004_report as R
import truth_set_2_44c as ts
from frame import render_page_matching_gather

OUTDIR = HERE.parents[1] / "out/print"
NEWTAG, BASETAG = "20261007-day", "20261007-night"
PAGES = S.PAGES
SHORT = S.SHORT
NAME = {"beethoven5-litolff": "Beethoven 5, Litolff", "brahms1-breitkopf": "Brahms 1, Breitkopf"}
W, LABW = 1400, 270
OVW = W - LABW
MAGENTA, LIME, RED, AZURE, ORANGE = (255, 0, 255), (0, 190, 0), (0, 0, 255), (255, 150, 0), (0, 140, 255)   # BGR
FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
F = ImageFont.truetype(FONT_PATH, 21)
FB = ImageFont.truetype(FONT_PATH, 22, index=1)
FS = ImageFont.truetype(FONT_PATH, 19)
C_NEW, C_BASE, C_GREY = (190, 0, 0), (0, 90, 200), (90, 90, 90)
MAXH = 6000
_STATE = S._STATE
_GRAY = {}
CHECKS = []


def gray_of(doc, page):
    if (doc, page) not in _GRAY:
        _GRAY[(doc, page)] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[doc]["pdf"], page, 600).rgb, cv2.COLOR_RGB2GRAY)
    return _GRAY[(doc, page)]


# ---------------------------------------------------------------- words
def inst_name(D, key):
    v = DR.vget(D, "instrument", key)
    if v and v[0] == "decided":
        j = DR.jl(v[1])
        if isinstance(j, dict) and j.get("name"):
            return j["name"]
    return None


def staff_label(D, key):
    if not key:
        return "no staff"
    _, p, s, k = key.split("/")
    nm = inst_name(D, key)
    return f"staff {int(k) + 1} from the top" + (f" ({nm})" if nm else " (no name read)")


def dur_words(x):
    if not x or x[0] != "decided":
        return "no length decided" if not x else f"length not decided ({x[2]})"
    j = DR.jl(x[1])
    if not isinstance(j, dict):
        return str(x[1])
    wr = {4.0: "whole", 2.0: "half", 1.0: "quarter", 0.5: "eighth", 0.25: "sixteenth", 0.125: "32nd"}.get(j.get("written"), f"{j.get('written')}-beat")
    d = j.get("dots", 0)
    return f"{j.get('beats')} beats ({'dotted ' if d else ''}{wr}{' rest' if j.get('is_rest') else ''})"


def wrap(text, font, width):
    out, line = [], ""
    for w_ in text.split():
        t = (line + " " + w_).strip()
        if font.getlength(t) <= width:
            line = t
        else:
            out.append(line)
            line = w_
    if line:
        out.append(line)
    return out


def text_block(lines_colored, width=W - 24, pad=8):
    """lines_colored = [(text, colour, font)] -> RGB PIL image of wrapped lines."""
    rows = []
    for txt, col, font in lines_colored:
        for ln in wrap(txt, font, width):
            rows.append((ln, col, font))
    h = sum(int(f.size * 1.3) for _, _, f in rows) + 2 * pad
    im = Image.new("RGB", (W, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    y = pad
    for ln, col, f in rows:
        d.text((12, y), ln, fill=col, font=f)
        y += int(f.size * 1.3)
    return im


# ---------------------------------------------------------------- geometry
def box_of(D, s):
    if "_bx" not in D:
        D["_bx"] = {s_: (c, b) for s_, c, b in D["boxes"]}
    return D["_bx"].get(s)


def system_staves(D, page, sy):
    ks = sorted((k for k in D["staff_lines"] if k.startswith(f"staff/{page}/{sy}/")), key=lambda k: int(k.split("/")[3]))
    return ks


def sp_of(D, key):
    ys = D["staff_lines"][key]
    return (max(ys) - min(ys)) / 4.0


def overview(doc, D, page, sy, subject_box, marks, tags, gray):
    """Whole system, scaled to OVW wide, staff names at the left. marks: [(box, BGR colour)] boxed; tags {staff key: [(text, rgb)]}."""
    ks = system_staves(D, page, sy)
    pre = f"glyph/{page}/{sy}/"
    xs0, xs1 = [], []
    for s, c, b in D["boxes"]:
        if s.startswith(pre):
            xs0.append(b[0]); xs1.append(b[2])
    x0, x1 = int(min(xs0)) - 12, int(max(xs1)) + 12
    sp0 = sp_of(D, ks[0])
    y0 = int(min(D["staff_lines"][ks[0]]) - 3.2 * sp0)
    y1 = int(max(D["staff_lines"][ks[-1]]) + 3.2 * sp_of(D, ks[-1]))
    for b, _ in marks:
        y0, y1 = min(y0, int(b[1] - 20)), max(y1, int(b[3] + 20))
    y0, x0 = max(0, y0), max(0, x0)
    crop = gray[y0:y1, x0:x1]
    sc = OVW / float(x1 - x0)
    im = cv2.resize(crop, (OVW, max(1, int(round((y1 - y0) * sc)))), interpolation=cv2.INTER_AREA)
    im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    for b, col in marks:
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        hx, hy = max(22, (b[2] - b[0]) * sc / 2 + 10), max(22, (b[3] - b[1]) * sc / 2 + 10)
        px, py = (cx - x0) * sc, (cy - y0) * sc
        cv2.rectangle(im, (int(px - hx), int(py - hy)), (int(px + hx), int(py + hy)), col, 3)
    pil = Image.new("RGB", (W, im.shape[0]), (255, 255, 255))
    pil.paste(Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)), (LABW, 0))
    d = ImageDraw.Draw(pil)
    for k in ks:
        ys = D["staff_lines"][k]
        yc = ((min(ys) + max(ys)) / 2.0 - y0) * sc
        nm = inst_name(D, k) or "(no name read)"
        label = f"{int(k.split('/')[3]) + 1}. {nm}"
        d.text((8, yc - 11), label[:24], fill=(0, 0, 0), font=FS)
        for j, (t, col) in enumerate(tags.get(k, [])):
            d.text((8 + 150 + j * 0, yc - 11 + 0), "", fill=col, font=FS)
        tx = 8
        if tags.get(k):
            d.text((8, yc + 6), "  ".join(t for t, _ in tags[k]), fill=tags[k][0][1], font=FS)
    d.line([(LABW - 4, 0), (LABW - 4, pil.size[1])], fill=(200, 200, 200), width=1)
    return pil


def zoom(gray, region, draws, checks_cols=None, tile_no=0, panel=""):
    """region (x0,y0,x1,y1) page px; draws = [("box", box, BGR, label) | ("hline", y, BGR, label)]; scale chosen so it fits W."""
    x0, y0, x1, y1 = [int(v) for v in region]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(gray.shape[1], x1), min(gray.shape[0], y1)
    sc = min(3.0, W / float(x1 - x0))
    crop = cv2.cvtColor(gray[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
    im = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    thr = min(int(np.percentile(gray[y0:y1, x0:x1], 25) + 40), 140)
    out = []
    for d in draws:
        if d[0] == "box":
            b, col = d[1], d[2]
            cv2.rectangle(im, (int((b[0] - x0) * sc), int((b[1] - y0) * sc)), (int((b[2] - x0) * sc), int((b[3] - y0) * sc)), col, 1)
        elif d[0] == "hline":
            y, col, label, mx0, mx1 = d[1], d[2], d[3], d[4], d[5]
            yy = int(round((y - y0) * sc)) + int(sc) // 2
            cv2.line(im, (0, yy), (im.shape[1] - 1, yy), col, 1)
            peaks = [NF.remeasure(gray, y, *cols, thr) for cols in ((int(mx0 - 40), int(mx0 - 4)), (int(mx1 + 4), int(mx1 + 40)))]
            peaks = [p for p in peaks if p[0] is not None]
            off = min((abs(p[1]) for p in peaks), default=None)
            CHECKS.append((tile_no, panel, label, round(float(y), 1), None if off is None else round(off, 1)))
    pil = Image.new("RGB", (W, im.shape[0]), (255, 255, 255))
    pil.paste(Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)), (0, 0))
    return pil


def region_for(boxes, ys=(), pad_x=140, pad_y=60, min_w=470, max_h=760):
    x0 = min(b[0] for b in boxes) - pad_x
    x1 = max(b[2] for b in boxes) + pad_x
    y0 = min([b[1] for b in boxes] + list(ys)) - pad_y
    y1 = max([b[3] for b in boxes] + list(ys)) + pad_y
    if x1 - x0 < min_w:
        c = (x0 + x1) / 2.0
        x0, x1 = c - min_w / 2.0, c + min_w / 2.0
    if y1 - y0 > max_h:
        cy = (boxes[0][1] + boxes[0][3]) / 2.0
        y0, y1 = cy - max_h / 2.0, cy + max_h / 2.0
    return (x0, y0, x1, y1)


# ---------------------------------------------------------------- pools
def pools(doc, N, B, rn, rb):
    P = collections.defaultdict(list)
    pages = PAGES[doc]
    bx = {s: (c, b) for s, c, b in N["boxes"]}
    an, ab = N["allv"], B["allv"]

    def pg(s):
        return int(s.split("/")[1])
    for k, v in an.items():
        q, s = k.split("|", 1)
        b = ab.get(k)
        if b is None or b == v:
            continue
        if q == "arc_is_not_an_arc" and v[0] == "decided" and v[1] == "true" and pg(s) in pages and s in bx:
            P["arc"].append(dict(doc=doc, subject=s, page=pg(s), box=bx[s][1], cls=bx[s][0]))
        elif q == "dot_role" and pg(s) in pages and s in bx:
            if b[0] == "abstained" and v[0] == "decided" and DR.jl(v[1]) == "augmentation":
                P["dot_aug"].append(dict(doc=doc, subject=s, page=pg(s), box=bx[s][1], cls=bx[s][0], b=b, n=v))
            elif b[0] == "decided" and v[0] == "decided" and DR.jl(b[1]) == "augmentation" and DR.jl(v[1]) == "staccato":
                P["dot_stac"].append(dict(doc=doc, subject=s, page=pg(s), box=bx[s][1], cls=bx[s][0], b=b, n=v))
        elif q == "glyph_owner" and pg(s) in pages and s in bx and bx[s][0].startswith("notehead") and v[0] == "decided":
            if b[0] == "decided" and DR.jl(b[1]) != DR.jl(v[1]):
                P["owner"].append(dict(doc=doc, subject=s, page=pg(s), box=bx[s][1], cls=bx[s][0], b=b, n=v, kind="other"))
            elif b[0] != "decided":
                P["owner"].append(dict(doc=doc, subject=s, page=pg(s), box=bx[s][1], cls=bx[s][0], b=b, n=v, kind="gaveup"))
        elif q == "meter" and b[0] == "abstained" and v[0] == "decided" and pg(s.replace("system/", "x/")) in pages:
            P["meter"].append(dict(doc=doc, subject=s, page=int(s.split("/")[1]), b=b, n=v))
        elif q == "voices" and pg(s.replace("cell/", "x/")) in pages:
            P["voices"].append(dict(doc=doc, subject=s, page=int(s.split("/")[1]), b=b, n=v))
    # a dot tile must show a note whose length changed with the dot's role
    for kk in ("dot_aug", "dot_stac"):
        keep = []
        for r in P[kk]:
            nt = nearest_note_left(N, r["subject"], r["box"])
            if nt and DR.vget(N, "duration", nt[0]) != DR.vget(B, "duration", nt[0]):
                keep.append(r)
        P[kk] = keep
    # dot owners: dot-class boxes whose glyph_owner decided differently
    for k, v in an.items():
        q, s = k.split("|", 1)
        if q == "glyph_owner" and s in bx and "ugmentationDot" in bx[s][0] and pg(s) in pages:
            b = ab.get(k)
            if b and v[0] == "decided" and (b[0], b[1]) != (v[0], v[1]):
                P["dot_owner"].append(dict(doc=doc, subject=s, page=pg(s), box=bx[s][1], cls=bx[s][0], b=b, n=v))
    # far heads (the night sheet's pools, tags swapped by hand: it reads rn/rb itself)
    FP = S.pools(doc, N, B, rn, rb)
    for r in FP["newly"]:
        P["far_new"].append(r)
    # far heads NEW gave up on (BASE decided), with BASE's replay lines
    far_n = S.R6far(N)
    for s, g in N["glyphs"].items():
        bg = B["glyphs"].get(s)
        if not bg or "box" not in g or R.page_of(s) not in pages:
            continue
        if (g.get("np") or {}).get("outcome") == "abstained" and (bg.get("np") or {}).get("outcome") == "decided" and R.is_far(bg):
            m = rb.get(s)
            if m and m.get("repro") and m.get("edge_y") is not None and m.get("line_y") is not None and m.get("between") is not None:
                P["far_lost"].append(dict(doc=doc, subject=s, page=R.page_of(s), box=g["box"], base_pos=int(round(float(bg["np"]["value"]))),
                                          new_reason=(g.get("fh_abs") or {}).get("ledger_reason") or (g.get("np") or {}).get("reason"),
                                          base=m))
    return P


def nearest_note_left(N, dot_subject, dot_box):
    pre = "/".join(dot_subject.split("/")[:5]) + "/"
    best, bd = None, 1e9
    cy = (dot_box[1] + dot_box[3]) / 2.0
    key = "staff/" + "/".join(dot_subject.split("/")[1:4])
    sp = sp_of(N, key) if key in N["staff_lines"] else 20.0
    for s, c, b in N["boxes"]:
        if not s.startswith(pre) or not c.startswith("notehead") or s == dot_subject:
            continue
        gap = dot_box[0] - b[2]
        if -0.3 * sp <= gap <= 2.5 * sp and abs((b[1] + b[3]) / 2.0 - cy) < 1.6 * sp and gap < bd:
            best, bd = (s, b), gap
    return best


# ---------------------------------------------------------------- tiles
def tile_image(no, header, ov, panels):
    parts = [text_block([(header, (0, 0, 0), FB)]), ov]
    for words, col, img in panels:
        parts.append(text_block([(words, col, F)]))
        parts.append(img)
    h = sum(p.size[1] for p in parts)
    im = Image.new("RGB", (W, h), (255, 255, 255))
    y = 0
    for p in parts:
        im.paste(p, (0, y))
        y += p.size[1]
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W - 1, h - 1], outline=(120, 120, 120), width=2)
    return im


def build(no, kind, r, N, B, rn, rb):
    doc, page, s = r["doc"], r["page"], r["subject"]
    gray = gray_of(doc, page)
    _STATE["N"] = {doc: N}
    parts = s.split("/")
    sy = int(parts[2])
    filing = "staff/" + "/".join(parts[1:4])
    where = f"{NAME[doc]}, PDF page index {page}, system {sy + 1} (subject {s})"
    tags = {}
    marks = []
    panels = []
    if kind == "arc":
        box = r["box"]
        sp = sp_of(N, filing) if filing in N["staff_lines"] else 20.0
        ownb = DR.vget(B, "arc_owner", s)
        akind = DR.vget(B, "arc_kind", s)
        tpb, tpn = DR.vget(B, "tie_pair", s), DR.vget(N, "tie_pair", s)
        okey = DR.jl(ownb[1]) if ownb and ownb[0] == "decided" else None
        if okey:
            tags[okey] = [("BASE owner", C_BASE)]
        marks = [(box, ORANGE)]
        gn, sn = S.grids(doc, page, "new")
        cx = (box[0] + box[2]) / 2.0
        lines = []
        for st in sn:
            ln = S.seg_lines(sn, st["key"], cx)
            for y in (ln or []):
                if box[1] - 0.5 * sp <= y <= box[3] + 0.5 * sp:
                    lines.append(y)
        reg = region_for([box], ys=lines, pad_x=60, pad_y=1.8 * sp, min_w=520, max_h=500)
        w_sp = (box[2] - box[0]) / sp
        kindw = DR.jl(akind[1]) if akind and akind[0] == "decided" else "slur or tie"
        base_w = f"BASE: this box ({w_sp:.0f} staff spaces wide, {(box[3] - box[1]) / sp:.1f} tall) was kept as {'a ' + str(kindw) if kindw else 'an arc'}, owned by {staff_label(B, okey)}. Tie pairing: {tpb[0] if tpb else 'none'}" + (f" ({tpb[2]})" if tpb else "") + "."
        new_w = (f"NEW: refused, because the ink in the box is a straight staff line, not a curve (a staff line runs through it and nearly every column holds only line). It is no longer an arc, so it cannot tie or slur anything. Tie pairing: {tpn[0] if tpn else 'none'}" + (f" ({tpn[2]})" if tpn else "") + ".")
        pb = zoom(gray, reg, [("box", box, ORANGE, "")], tile_no=no, panel="BASE")
        pn = zoom(gray, reg, [("box", box, ORANGE, "")] + [("hline", y, MAGENTA, "staff line through the box", box[0], box[2]) for y in lines], tile_no=no, panel="NEW")
        panels = [(base_w, C_BASE, pb), (new_w + (" Magenta line = the staff line that runs through the box." if lines else ""), C_NEW, pn)]
        label = "ARC: a staff line, no longer an arc"
        words_b, words_n = base_w, new_w
    elif kind in ("dot_aug", "dot_stac"):
        box = r["box"]
        nt = nearest_note_left(N, s, box)
        sp = sp_of(N, filing) if filing in N["staff_lines"] else 20.0
        boxes = [box] + ([nt[1]] if nt else [])
        marks = [(box, ORANGE)]
        reg = region_for(boxes, pad_x=3 * sp, pad_y=2.5 * sp, min_w=470, max_h=420)
        bn = [("box", box, ORANGE, "")]
        bb = list(bn)
        if nt:
            bn.append(("box", nt[1], (0, 190, 0), ""))
            bb.append(("box", nt[1], (0, 190, 0), ""))
        dn, dbs = (DR.vget(N, "duration", nt[0]), DR.vget(B, "duration", nt[0])) if nt else (None, None)
        if kind == "dot_aug":
            wb = "BASE: cannot tell what this dot is ('could lengthen a note or be a staccato dot'), so it says nothing."
            wn = "NEW: a lengthening dot: it sits right of a note head and level with it, so the note is longer."
        else:
            wb = "BASE: read as a lengthening dot (right of a head, level with it), making the note longer."
            wn = "NEW: read as a staccato dot (centred on the head's column, above or below it), so the note is not lengthened."
        if nt:
            wb += f" The note to its left (green box): {dur_words(dbs)}."
            wn += f" The same note: {dur_words(dn)}."
        panels = [(wb + " Orange = the dot.", C_BASE, zoom(gray, reg, bb, tile_no=no, panel="BASE")),
                  (wn, C_NEW, zoom(gray, reg, bn, tile_no=no, panel="NEW"))]
        label = "DOT: " + ("unread -> lengthening" if kind == "dot_aug" else "lengthening -> staccato")
        words_b, words_n = wb, wn
        if nt:
            marks.append((nt[1], (0, 190, 0)))
    elif kind == "dot_owner":
        box = r["box"]
        sp = sp_of(N, filing) if filing in N["staff_lines"] else 20.0
        bo, no_ = DR.jl(r["b"][1]), DR.jl(r["n"][1])
        tags[no_] = [("NEW owner", C_NEW)]
        if bo:
            tags.setdefault(bo, []).append(("BASE owner", C_BASE))
        nt = nearest_note_left(N, s, box)
        boxes = [box] + ([nt[1]] if nt else [])
        marks = [(box, ORANGE)]
        reg = region_for(boxes, pad_x=3 * sp, pad_y=3 * sp, min_w=470, max_h=520)
        d_ = [("box", box, ORANGE, "")] + ([("box", nt[1], (0, 190, 0), "")] if nt else [])
        wb = f"BASE: this dot (orange) belongs to {staff_label(B, bo)}. The dot is filed under {staff_label(B, filing)}."
        wn = f"NEW: it belongs to {staff_label(N, no_)}" + (", the staff of the note it follows (green box)." if nt else ".")
        panels = [(wb, C_BASE, zoom(gray, reg, d_, tile_no=no, panel="BASE")), (wn, C_NEW, zoom(gray, reg, d_, tile_no=no, panel="NEW"))]
        label = "DOT: whose it is"
        words_b, words_n = wb, wn
    elif kind in ("far_new", "far_lost"):
        box = r["box"]
        if kind == "far_new":
            nf = r["new"]
            nb = r.get("base_rep")
            base_txt = "BASE: gave up, no position (" + str(r.get("base_reason"))[:70] + ")."
            new_txt = "NEW: " + S.words_pos(r["new_pos"]) + "."
        else:
            nb = r["base"]
            nf = None
            base_txt = "BASE: " + S.words_pos(r["base_pos"]) + "."
            new_txt = "NEW: gave up, no position (" + str(r["new_reason"])[:70] + ")."
        ref = nf or nb
        sp = (max(ref["lines"]) - min(ref["lines"])) / 4.0
        box_used = ref.get("box_used") or box
        marks = [(box, ORANGE)]

        def lines_of(m, newside):
            L = []
            if not m or m.get("edge_y") is None:
                return L
            L.append((m["edge_y"], MAGENTA, "staff edge"))
            L += [(b_, (0, 190, 0), f"ledger {i + 1}") for i, b_ in enumerate(m.get("between") or [])]
            if m.get("line_y") is not None:
                L.append((m["line_y"], RED if newside else AZURE, "note line"))
            return L
        Ln, Lb = lines_of(nf, True), lines_of(nb, False)
        ys = [y for y, *_ in Ln + Lb]
        reg = region_for([box_used], ys=ys, pad_x=3.4 * sp, pad_y=1.3 * sp, min_w=480, max_h=700)
        mk = lambda L, b_: [("box", b_, ORANGE, "")] + [("hline", y, c, lab, box_used[0], box_used[2]) for y, c, lab in L]
        panels = [(base_txt + (" Lines drawn: BASE's own." if Lb else ""), C_BASE, zoom(gray, reg, mk(Lb, box_used), tile_no=no, panel="BASE")),
                  (new_txt + (" Lines drawn: magenta = the staff edge, green = each ledger line counted out, red = the line the note is on." if Ln else ""), C_NEW,
                   zoom(gray, reg, mk(Ln, box_used), tile_no=no, panel="NEW"))]
        label = "FAR HEAD: " + ("BASE gave up, NEW answers" if kind == "far_new" else "BASE answered, NEW gives up")
        words_b, words_n = base_txt, new_txt
    elif kind == "owner":
        box = r["box"]
        bo = DR.jl(r["b"][1]) if r["b"][0] == "decided" else None
        no_ = DR.jl(r["n"][1])
        gn, sn = S.grids(doc, page, "new")
        cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
        tags[no_] = [("NEW owner", C_NEW)]
        if bo:
            tags.setdefault(bo, []).append(("BASE owner", C_BASE))
        marks = [(box, ORANGE)]
        sp = sp_of(N, filing) if filing in N["staff_lines"] else 20.0

        def near(key):
            ln = S.seg_lines(sn, key, cx) if key else None
            return min(ln, key=lambda y: abs(y - cy)) if ln else None
        yn, yb = near(no_), near(bo)
        reg = region_for([box], ys=[y for y in (yn, yb) if y], pad_x=3.4 * sp, pad_y=1.5 * sp, min_w=480, max_h=700)
        wb = ("BASE: belongs to " + staff_label(B, bo) if bo else "BASE: no answer (gave up on whose note it is)") + f". The note is filed under {staff_label(B, filing)}."
        wn = f"NEW: belongs to {staff_label(N, no_)}" + (" (the one it is filed under)" if no_ == filing else " (NOT the one it is filed under)") + f"; decided by: {r['n'][2]}."
        mkl = lambda y, c: [("box", box, ORANGE, "")] + ([("hline", y, c, "nearest line of the owner staff", box[0], box[2])] if y else [])
        panels = [(wb + (" Azure line = that staff's line nearest the note." if yb else ""), C_BASE, zoom(gray, reg, mkl(yb, AZURE), tile_no=no, panel="BASE")),
                  (wn + " Magenta line = that staff's line nearest the note.", C_NEW, zoom(gray, reg, mkl(yn, MAGENTA), tile_no=no, panel="NEW"))]
        label = "OWNER: " + ("moved to another staff" if r["kind"] == "other" else "BASE gave up, NEW decides")
        words_b, words_n = wb, wn
    elif kind == "meter":
        bv, nv = r["b"], r["n"]
        j = DR.jl(nv[1])
        raw = j.get("raw") if isinstance(j, dict) else str(j)
        ks = system_staves(N, page, sy)
        k0 = ks[0]
        xs = [b[0] for s_, c, b in N["boxes"] if s_.startswith(f"glyph/{page}/{sy}/{k0.split('/')[3]}/")]
        bx0 = [b for s_, c, b in N["boxes"] if s_.startswith(f"glyph/{page}/{sy}/{k0.split('/')[3]}/") and s_.split("/")[4] in ("0", "1")]
        sp = sp_of(N, k0)
        reg = region_for(bx0, ys=N["staff_lines"][k0], pad_x=20, pad_y=2 * sp, min_w=1000, max_h=500)
        wb = f"BASE: cannot tell this system's meter (the printed digits looked like a change but were misread: '{bv[2]}'), so no bar in it is checked against a meter."
        wn = f"NEW: {raw}, worked out from how long the bars add up (reason: {nv[2]}). The dotted notes are now counted as dotted, so the bars now add up to {raw}."
        z = zoom(gray, reg, [], tile_no=no, panel="both")
        panels = [(wb, C_BASE, z), (wn + " (Same window for both: the start of the top staff.)", C_NEW, z)]
        label = "METER: worked out from the bars"
        words_b, words_n = wb, wn
    else:   # voices
        bv, nv = r["b"], r["n"]
        _, p_, sy_, k_, c_ = s.split("/")
        pre = f"glyph/{p_}/{sy_}/{k_}/{c_}/"
        bxs = [b for s_, c, b in N["boxes"] if s_.startswith(pre) and not c.startswith(("staff", "ledger"))]
        key = f"staff/{p_}/{sy_}/{k_}"
        sp = sp_of(N, key)
        reg = region_for(bxs or [[0, 0, 100, 100]], ys=N["staff_lines"][key], pad_x=30, pad_y=2 * sp, min_w=700, max_h=520)
        filing = key
        marks = [(bxs[0], ORANGE)] if bxs else []
        for b_ in bxs[1:]:
            marks.append((b_, ORANGE))

        def vw(v):
            if v[0] == "decided":
                j = DR.jl(v[1])
                return f"{j.get('n_voices', '?')} voice, the note lengths add up to the bar" if isinstance(j, dict) else "decided"
            return "no way to split the bar into voices that adds up (" + str(v[2]) + ")"
        wb, wn = "BASE: " + vw(bv) + ".", "NEW: " + vw(nv) + "."
        z = zoom(gray, reg, [], tile_no=no, panel="both")
        panels = [(wb, C_BASE, z), (wn + " (Same window for both: the whole bar, " + staff_label(N, key) + ".)", C_NEW, z)]
        label = "VOICES: one bar's note lengths"
        words_b, words_n = wb, wn
        box = bxs[0] if bxs else None
    ov = overview(doc, N, page, sy, None, marks, tags, gray)
    head = f"{no}.  {label}   |   {where}"
    img = tile_image(no, head, ov, panels)
    info = dict(n=no, kind=kind, label=label, doc=doc, page=page, subject=s, base=words_b, new=words_n)
    return img, info


def pick(rng, pool, used, n=1):
    out = []
    pool = list(pool)
    rng.shuffle(pool)
    for r in pool:
        key = (r["doc"], r["page"], r["subject"].split("/")[2] if r["subject"].count("/") >= 2 else "")
        if key in used:
            continue
        out.append(r)
        used.add(key)
        if len(out) == n:
            break
    return out


def main(d, seed):
    d = Path(d)
    rng = random.Random(seed)
    data = {}
    DOCS = [x for x in os.environ.get("DAY_DOCS", "").split(",") if x] or list(PAGES)
    for doc in DOCS:
        N = json.loads((d / "x" / f"{doc}-{NEWTAG}.json").read_text())
        B = json.loads((d / "x" / f"{doc}-{BASETAG}.json").read_text())
        rn = json.loads((d / "x" / f"rep_new_{SHORT[doc]}.json").read_text())["heads"]
        rb = json.loads((d / "x" / f"rep_base_{SHORT[doc]}.json").read_text())["heads"]
        data[doc] = (N, B, rn, rb)
        _STATE.setdefault("N", {})[doc] = N
    P = {}
    for doc in DOCS:
        p = pools(doc, *data[doc])
        for k, v in p.items():
            P.setdefault(k, []).extend(v)
        print(doc, {k: len(v) for k, v in p.items()})
    used = set()
    plan = [("arc", 3), ("dot_aug", 1), ("dot_stac", 1), ("dot_owner", 1), ("far_new", 2), ("far_lost", 1), ("owner", 2), ("meter", 1), ("voices", 1)]
    picks = []
    for kind, n in plan:
        pool = P.get(kind, [])
        if kind == "arc":      # 2 Brahms, 1 Litolff (population is 94% Brahms)
            picks += [(kind, r) for r in pick(rng, [r for r in pool if r["doc"].startswith("brahms")], used, 2)]
            picks += [(kind, r) for r in pick(rng, [r for r in pool if r["doc"].startswith("beethoven")], used, 1)]
        elif kind == "owner":  # one moved, one gave-up -> decided
            picks += [(kind, r) for r in pick(rng, [r for r in pool if r["kind"] == "other"], used, 1)]
            got = pick(rng, [r for r in pool if r["kind"] == "gaveup"], used, 1) or pick(rng, [r for r in pool if r["kind"] == "other"], used, 1)
            picks += [(kind, r) for r in got]
        else:
            picks += [(kind, r) for r in pick(rng, pool, used, n)]
    print("pools:", {k: len(v) for k, v in P.items()}, "picked", len(picks), [k for k, _ in picks])
    rng.shuffle(picks)
    tiles, infos = [], []
    for i, (kind, r) in enumerate(picks, 1):
        N, B, rn, rb = data[r["doc"]]
        img, info = build(i, kind, r, N, B, rn, rb)
        tiles.append(img)
        infos.append(info)
        print(i, kind, r["doc"][:6], r["subject"], img.size, flush=True)
    # legend + cut into images <= MAXH
    legend = text_block([("How to read: each tile is ONE staff-line-level question. The top picture is the whole system with the staff names at the left; the "
                          "subject is boxed. Below it, BASE (blue words) and NEW (red words) are shown at the same window. ORANGE = the subject; green box = the note a dot "
                          "follows; magenta / green / red / azure 1-pixel lines are described under each picture. Neither side is claimed right: you decide.", (0, 0, 0), F)])
    sheets, cur, h = [], [legend], legend.size[1]
    for t in tiles:
        if h + t.size[1] + 14 > MAXH and len(cur) > 1:
            sheets.append(cur)
            cur, h = [legend], legend.size[1]
        cur.append(t)
        h += t.size[1] + 14
    sheets.append(cur)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for old in OUTDIR.glob("day_1007_sample_*.png"):
        old.unlink()
    for j, parts in enumerate(sheets, 1):
        H = sum(p.size[1] + 14 for p in parts)
        im = Image.new("RGB", (W, H), (255, 255, 255))
        y = 0
        for p in parts:
            im.paste(p, (0, y))
            y += p.size[1] + 14
        fn = OUTDIR / f"day_1007_sample_{j}.png"
        im.save(fn)
        print("wrote", fn, im.size)
    (OUTDIR / "day_1007_sample.json").write_text(json.dumps(infos, indent=1, default=str))
    new_c = [c for c in CHECKS if c[1] != "BASE"]
    bad = [c for c in new_c if c[4] is not None and c[4] > 2.0]
    hid = [c for c in new_c if c[4] is None]
    print(f"drawn lines {len(CHECKS)}: NEW/shared {len(new_c)}: within 2 px of an ink row {len(new_c) - len(bad) - len(hid)}, off by more than 2 px {len(bad)} {bad}, "
          f"no ink beside the box to measure {len(hid)} {hid}")
    print("BASE lines:", [c for c in CHECKS if c[1] == "BASE"])


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--seed") + 1]) if "--seed" in a else 20261007)
