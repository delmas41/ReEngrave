"""2.167d probe 3: per-bar working sheets for MY OWN eyes (scratch, not evidence).
LEFT: the page crop of the bar with 2.5 staff spaces of its neighbours either side; thin GREY frame = the bar crop the detector was given;
boxes: GREEN = notehead/rest boxes the record keeps (numbered), BLUE-GREY = other kept classes (flag, dot, accidental, beam...),
ORANGE dashed = boxes my base re-run found BELOW the 0.25 floor (the record does not keep them); small ruler under the crop in staff spaces from the bar's left edge.
RIGHT: numbered box table (class, conf, fate/verdict) and the exporter's events.
usage: d3_sheet.py lit|bra FROM TO OUTDIR   (indices into the 2.167c sample)"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
SKIP = ("slur", "tie", "arc", "dynamic", "hairpin", "crescendo", "decrescendo", "text", "word", "tempo", "staff", "ledger", "barline", "bracket",
        "brace", "volta", "ending", "fermata", "pedal", "ottava", "trill", "tremolo")


def font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def short(c):
    c = c.replace("noteheadBlackInSpace", "NB").replace("noteheadHalfInSpace", "NH").replace("noteheadWholeInSpace", "NW")
    c = c.replace("noteheadBlackOnLine", "NBl").replace("noteheadHalfOnLine", "NHl").replace("noteheadWholeOnLine", "NWl")
    for a, b in (("rest", "R"), ("flag", "F"), ("augmentationDot", "dot"), ("accidental", "acc")):
        c = c.replace(a, b)
    return c


def main():
    plate, a, b, outdir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    d = ROOT + "/probe/2.167d/data/"
    sample = json.load(open(d + "%s_sample.json" % plate))
    rec = json.load(open(d + "%s_rec.json" % plate))
    rr = json.load(open(d + "%s_rerun.json" % plate))
    held = json.load(open(d + "%s_held_sample.json" % plate))
    doc = fitz.open(PDF[plate])
    os.makedirs(outdir, exist_ok=True)
    fo, fs = font(14), font(11)
    zoom = 3.0 if plate == "lit" else 1.6
    for i in range(a, min(b, len(sample))):
        p, s, st, c = sample[i]
        key = "%d/%d/%d/%d" % (p, s, st, c)
        R = rr[key]
        sp = R["spacing"]
        lines = R["lines"]
        x0, y0, x1, y1 = R["cell"]
        r = (x0 - 2.5 * sp, lines[0] - 4.5 * sp, x1 + 2.5 * sp, lines[0] + 8.5 * sp)
        k = 72 / 600
        pix = doc[p].get_pixmap(matrix=fitz.Matrix(600 / 72 * zoom, 600 / 72 * zoom), clip=fitz.Rect(*[v * k for v in r]))
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        f = im.width / (r[2] - r[0])
        dr = ImageDraw.Draw(im)

        def X(v):
            return (v - r[0]) * f

        def Y(v):
            return (v - r[1]) * f
        dr.rectangle([X(x0), Y(y0), X(x1), Y(y1)], outline=(130, 130, 130), width=1)
        table = []
        nmap = {}
        n = 0
        # record boxes of this cell and the two neighbours
        for dc in (0, -1, 1):
            kk = "%d/%d/%d/%d" % (p, s, st, c + dc)
            for g in rec["cells"].get(kk, {}).get("glyphs", []):
                if not g.get("bbox"):
                    continue
                cls = g["cls"]
                if any(cls.lower().startswith(t) or t in cls.lower() for t in SKIP) and not cls.startswith(("notehead", "rest")):
                    continue
                bb = g["bbox"]
                if bb[2] < r[0] or bb[0] > r[2]:
                    continue
                n += 1
                main = cls.startswith(("notehead", "rest"))
                col = (0, 150, 0) if main else (90, 110, 160)
                if dc != 0:
                    col = (150, 200, 150) if main else (170, 180, 200)
                dr.rectangle([X(bb[0]), Y(bb[1]), X(bb[2]), Y(bb[3])], outline=col, width=1)
                dr.text((X(bb[0]), Y(bb[1]) - 11), str(n), fill=col, font=fs)
                v = {q[0]: q[1:3] for q in g["verdicts"]}
                dv = v.get("duration") or v.get("rest_is_not_a_rest") or v.get("notehead_is_not_a_notehead")
                nn = v.get("notehead_is_not_a_notehead")
                nmap[n] = dict(sub=g["sub"], dc=dc, cls=cls, conf=g["conf"], bbox=bb, low=False)
                table.append((n, dc, "%s %.2f" % (short(cls), g["conf"]), "%s" % (",".join(str(x) for x in dv) if dv else ""),
                              "notnote:" + str(nn[1]) if nn and nn[0] == "decided" and nn[1] not in ("notehead",) else ""))
        for bx in R["variants"]["base"]["boxes"]:
            if 0.05 <= bx[1] < 0.25 and bx[0].startswith(("notehead", "rest", "flag", "augmentationDot")):
                bb = bx[2:6]
                n += 1
                dr.rectangle([X(bb[0]), Y(bb[1]), X(bb[2]), Y(bb[3])], outline=(255, 140, 0), width=1)
                dr.text((X(bb[0]), Y(bb[3]) + 1), "L%d" % n, fill=(255, 140, 0), font=fs)
                nmap[n] = dict(sub=None, dc=0, cls=bx[0], conf=bx[1], bbox=bb, low=True)
                table.append((n, 0, "LOW %s %.2f" % (short(bx[0]), bx[1]), "", ""))
        # ruler
        rh = 16
        ruler = Image.new("RGB", (im.width, rh), "white")
        rd = ImageDraw.Draw(ruler)
        t = 0
        while x0 + t * sp < r[2]:
            xx = X(x0 + t * sp)
            rd.line([xx, 0, xx, 6], fill=(0, 0, 0))
            if t % 2 == 0:
                rd.text((xx + 1, 2), str(t), fill=(0, 0, 0), font=fs)
            t += 1
        t = -1
        while x0 + t * sp > r[0]:
            xx = X(x0 + t * sp)
            rd.line([xx, 0, xx, 6], fill=(0, 0, 0))
            t -= 1
        h = held[key]
        hdr = "#%d p%d s%d staff%d cell%d %s want %.4g q got %s  imgsz(base)=%d  bar %dpx wide = %.1f sp" % (
            i, p, s, st, c, h["name"], h["held"]["want_quarters"], h["held"]["quarters"], R["variants"]["base"]["imgsz"], x1 - x0, (x1 - x0) / sp)
        txt = []
        for (nn_, dc, a_, b_, c_) in table:
            txt.append("%d%s %s %s %s" % (nn_, "" if dc == 0 else (" [prev]" if dc < 0 else " [next]"), a_, b_, c_))
        txt.append("-- exporter events:")
        for j, e in enumerate(h["events"]):
            if e["kind"] == "rest":
                txt.append("e%d rest %s" % (j + 1, e.get("duration_type")))
            else:
                txt.append("e%d chord %s dots%s %s" % (j + 1, e.get("duration_type"), e.get("dots"), "+".join(hh.get("pitch", "?") for hh in e["heads"])))
        for q in h["boxes"]:
            if q["fate"] not in ("written",):
                txt.append("fate %s %s" % (q["fate"], [round(v) for v in (q.get("bbox") or [])]))
        tw = 360
        H = max(im.height + rh, 15 * len(txt) + 30) + 24
        tile = Image.new("RGB", (im.width + tw, H), "white")
        tile.paste(im, (0, 24))
        tile.paste(ruler, (0, 24 + im.height))
        td = ImageDraw.Draw(tile)
        td.text((4, 4), hdr, fill=(0, 0, 0), font=fo)
        for q, t_ in enumerate(txt):
            td.text((im.width + 6, 28 + 15 * q), t_, fill=(0, 0, 0), font=fs)
        tile.save(os.path.join(outdir, "%s_%02d.png" % (plate, i)))
        json.dump(nmap, open(os.path.join(outdir, "%s_%02d.json" % (plate, i)), "w"))
    print("ok")


if __name__ == "__main__":
    main()
