"""2.247 step 1b: every accidental WRITTEN in an arm's exported file, joined to the accidental box it came from (the family row of the
nearest accidental-family box left of the note in its own cell, at its height), so we can say WHO named the kind: the strokes (2.201, a clear
type) or the detector class (strokes unclear). usage: written_join.py GATHERED.record.json SYMBOLS.json OUT.json"""
import collections
import json
import sys

ALT = {"flat": "flat", "natural": "natural", "sharp": "sharp", "flat-flat": "flat", "double-sharp": "sharp", "sharp-sharp": "sharp"}


def main(rec_path, sym_path, out_path):
    rec = json.load(open(rec_path))
    rec = rec.get("record", rec)
    sym = json.load(open(sym_path))
    boxes, fams = {}, {}
    for r in rec["observations"]:
        q = r["quantity"]
        if q == "glyph_box":
            n = str(r["value"][0])
            if n.startswith("accidental") or n.startswith("key"):
                boxes[r["subject"]] = (n, (r.get("detail") or {}).get("bbox_page_px"))
        elif q == "accidental_staff_position":
            fams[r["subject"]] = r.get("detail") or {}
    rows, tally = [], collections.Counter()
    for h in sym["hosts"]:
        if h.get("kind") != "note" or not (h.get("sub") or {}).get("accidental") or not h.get("box"):
            continue
        written = ALT.get(h["sub"]["accidental"][0], h["sub"]["accidental"][0])
        cell = "/".join(h["rg"].split("/")[1:5])
        hb = h["box"]
        best = None
        for s, (cls, pb) in boxes.items():
            if "/".join(s.split("/")[1:5]) != cell or not pb or s not in fams:
                continue
            gap = hb[0] - pb[2]
            if -4 <= gap <= 80 and pb[3] > hb[1] - 20 and pb[1] < hb[3] + 20:
                if best is None or gap < best[0]:
                    best = (gap, s, cls, pb)
        if best is None:
            tally[("no_box_found", written)] += 1
            rows.append({"note": h["rg"], "page": h["page"], "written": written, "blue": h["blue"], "box": None})
            continue
        _g, s, cls, pb = best
        fam = fams[s].get("family") or {}
        t = fam.get("type")
        source = "strokes" if t in ("flat", "natural", "sharp") else ("class(strokes:%s)" % t if fam else "class(no family)")
        det = fam.get("detector_type") or cls
        tally[(source, "class=" + str(det), "written=" + written)] += 1
        rows.append({"note": h["rg"], "page": h["page"], "pitch": h["pitch"], "written": written, "blue": h["blue"], "acc": s, "cls": cls,
                     "page_box": pb, "family_type": t, "why": fam.get("why"), "detector_type": fam.get("detector_type"),
                     "features": fam.get("features"), "source": source})
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("  ", k, v)
    json.dump(rows, open(out_path, "w"), indent=0)


if __name__ == "__main__":
    main(*sys.argv[1:])
