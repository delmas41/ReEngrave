"""ROADMAP 2.307 T1c -- where do the known unboxed heads sit relative to the cell? (measure only)

    python3 benchmarks/page-and-zoom-2026-11/t1c_unboxed.py SLICES_DIR OUT.json

Population (A): every notehead in Sean's Brahms p0 hand labels (`data/hand-truth/pages/imslp317803/0.json`) that NO detector notehead box of
the saved gather overlaps (IoU >= 0.3, or the label's centre inside a head box). Labels were PREFILLED from the cell detector and then
confirmed / fixed / drawn by Sean, so this population is mostly his `drawn` heads; it is reported with origin.
(B): the named single cases -- 2.305 r3 tile 8 (Litolff p5, lower note of the chord whose upper head is `glyph/5/1/1/1/1`) and
2.290 r? tile 3 (Litolff p8 m58 staff 3, lower-left head) -- are printed with the cell geometry next to them for a crop look; their exact
head position is NOT in any record (they were never boxed), so they are leads.

Each head of (A) is placed against the cells of its own staff (the staff whose lines it is nearest): distance in staff spaces from the head
centre to the nearest left/right edge of the cell holding it (a cell edge is a barline or the system's end), to its crop's top/bottom edge,
and whether the centre sits outside the five staff lines (ledger territory = the band a padded neighbour cell also shows).
"""
import json
import sys

LABELS = "data/hand-truth/pages/imslp317803/0.json"


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def main():
    root, outp = sys.argv[1], sys.argv[2]
    lab = json.load(open(LABELS))
    heads = [b for b in lab["boxes"] if b["cls"].startswith("notehead")]
    det, cells, lines = [], {}, {}
    for line in open("%s/brahms/observations.jsonl" % root):
        o = json.loads(line)
        s = o["subject"].split("/")
        if len(s) < 2 or s[1] != "0":
            continue
        if o["quantity"] == "glyph_box" and str(o["value"][0]).lower().startswith("notehead"):
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                det.append((o["subject"], o.get("reader"), pb))
        elif o["quantity"] == "cell_box":
            cells[o["subject"]] = o["value"]
        elif o["quantity"] == "staff_lines":
            lines[o["subject"]] = o["value"]
    out = []
    for h in heads:
        r = h["rect"]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        hit = [d for d in det if iou(r, d[2]) >= 0.3 or (d[2][0] <= cx <= d[2][2] and d[2][1] <= cy <= d[2][3])]
        if any(d[1] == "detector" for d in hit):
            continue
        # own staff: nearest staff by distance from centre to the staff's line span
        best = None
        for sk, ys in lines.items():
            d = 0.0 if ys[0] <= cy <= ys[-1] else min(abs(cy - ys[0]), abs(cy - ys[-1]))
            if best is None or d < best[0]:
                best = (d, sk, ys)
        _, sk, ys = best
        sp = (ys[-1] - ys[0]) / 4.0
        pref = "cell/" + "/".join(sk.split("/")[1:]) + "/"
        mine = [(k, v) for k, v in cells.items() if k.startswith(pref) and v[0] <= cx <= v[2]]
        row = dict(label=h["id"], cls=h["cls"], origin=h["origin"], centre=[round(cx), round(cy)], staff=sk, sp=round(sp, 1),
                   other_reader_box=[d[1] for d in hit])
        if mine:
            k, v = mine[0]
            row.update(cell=k, dx_edge_sp=round(min(cx - v[0], v[2] - cx) / sp, 2), dy_crop_edge_sp=round(min(cy - v[1], v[3] - cy) / sp, 2))
        row["outside_lines_sp"] = round(max(0.0, ys[0] - cy, cy - ys[-1]) / sp, 2)
        within_edge = row.get("dx_edge_sp", 99) <= 1.0
        row["where"] = ("cell edge (<=1 sp of a barline)" if within_edge else
                        "padding band (outside the lines, ledger territory)" if row["outside_lines_sp"] > 0.5 else "open")
        out.append(row)
    for r in out:
        print(r)
    import collections
    print("Brahms p0 labelled heads with no detector head box:", len(out), dict(collections.Counter(r["where"] for r in out)),
          "origins", dict(collections.Counter(r["origin"] for r in out)))
    json.dump(out, open(outp, "w"), indent=1)


if __name__ == "__main__":
    main()
