"""2.305 r10 -- IS THE PAGE READER'S INK RUN CUT WHERE AN ARC CROSSES A BARLINE? For every arc crossing a barline -- Brahms p0: Sean's confirmed page-pass
arc labels whose box spans a barline column; Litolff p13 (no labels): two detector arc boxes of one staff meeting at a barline column (one ends, the other
starts within 0.5 sp of it) -- the record's `Q.PAGE_ARC` runs there: WHOLE (one run's points on both sides of the barline), CUT (runs on each side, none on
both), ONE SIDE ONLY, or NONE; and for WHOLE, what the binding did with that run. Reads only.

    python3 barline_cut.py CANVAS_DIR PLATE PAGE RECORD.json [LABELS.json]
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402


def main():
    cdir, plate, page, rec_path = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    labels = sys.argv[5] if len(sys.argv) > 5 else None
    pj = json.load(open(os.path.join(cdir, "%s-p%d.page.json" % (plate, page))))
    sp = float(pj["sp"])
    bars = [b["box"] for b in pj["barlines"]]
    rec = load_record(rec_path)["record"]
    runs = [o for o in rec["observations"] if o["quantity"] == "page_arc" and o.get("value") in ("run", "seeded")]
    st = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "page_arc_binding":
            for x in (v.get("detail") or {}).get("runs") or ():
                st[x["row"]] = x
    crossings = []          # (label, x_bar, y0, y1)
    if labels:
        for a in json.load(open(labels))["labels"]:
            if a["kind"] != "arc" or a["state"] != "confirmed":
                continue
            r = a["shape"]["rect"]
            for b in bars:
                xb = (b[0] + b[2]) / 2.0
                if r[0] + 0.5 * sp < xb < r[2] - 0.5 * sp and b[1] <= r[3] and b[3] >= r[1]:
                    crossings.append((a["id"], xb, r[1], r[3]))
    else:
        ab = [(o["subject"], (o.get("detail") or {}).get("bbox_page_px")) for o in rec["observations"] if o["quantity"] == "arc_box"]
        ab = [(s, b) for s, b in ab if b and s.startswith("glyph/%d/" % page)]
        seen = set()
        for b in bars:
            xb = (b[0] + b[2]) / 2.0
            for s1, b1 in ab:
                if abs(b1[2] - xb) > 0.5 * sp:
                    continue
                for s2, b2 in ab:
                    if s2 == s1 or abs(b2[0] - xb) > 0.5 * sp or s1.split("/")[3] != s2.split("/")[3]:
                        continue
                    if min(b1[3], b2[3]) - max(b1[1], b2[1]) < -0.5 * sp:
                        continue
                    k = (s1.split("/")[3], round(xb), round((b1[1] + b2[1]) / 2 / sp))
                    if k in seen:
                        continue
                    seen.add(k)
                    crossings.append(("%s|%s" % (s1, s2), xb, min(b1[1], b2[1]), max(b1[3], b2[3])))
    tally = {}
    for name, xb, y0, y1 in crossings:
        left, right, both = [], [], []
        for o in runs:
            pts = [p for p in (o.get("detail") or {}).get("points") or () if y0 - 0.5 * sp <= p[1] <= y1 + 0.5 * sp]
            if not pts:
                continue
            l = any(xb - 2 * sp <= p[0] < xb - 0.3 * sp for p in pts)
            r_ = any(xb + 0.3 * sp < p[0] <= xb + 2 * sp for p in pts)
            if l and r_:
                both.append(o["id"])
            elif l:
                left.append(o["id"])
            elif r_:
                right.append(o["id"])
        if both:
            what = "WHOLE"
            x = st.get(both[0], {})
            what2 = "%s:%s" % (x.get("status"), x.get("why") or x.get("kind"))
        elif left and right:
            what, what2 = "CUT", ""
        elif left or right:
            what, what2 = "ONE_SIDE", ""
        else:
            what, what2 = "NONE", ""
        tally[what] = tally.get(what, 0) + 1
        print("%-50s x %5d  %-8s %s %s" % (name[:50], xb, what, what2, both or (left + right)))
    print(plate, page, "crossings", len(crossings), tally)


if __name__ == "__main__":
    main()
