"""2.305 r9, MY look only (leads, never findings): a crop of Brahms p0 with every page-ink arc run drawn (blue polyline, row id at its start;
abstained runs dashed-orange), his confirmed arcs (green rect, id), and the notes named on the command line (red box).

    python3 look.py RECORD.json OUT.png x0 y0 x1 y1 [glyph ...]
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

BRA = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
ARCS = "/Users/seanjohnson/Desktop/ReEngrave/out/print-from-worktrees/2.287-r1/0.pagepass.sean-snapshot2.json"


def main():
    rec_p, out = sys.argv[1], sys.argv[2]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7])
    keys = sys.argv[7:]
    res = load_record(rec_p)
    rec = res.get("record", res)
    obs = rec["observations"]
    status = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "page_arc_binding":
            for r in (v.get("detail") or {}).get("runs") or ():
                status.setdefault(r["row"], []).append(r["status"])
    im = Image.fromarray(render_page(BRA, 0, dpi=600).rgb).convert("RGB")
    dr = ImageDraw.Draw(im)
    for o in obs:
        if o.get("quantity") == "page_arc" and o.get("value") == "run":
            pts = (o.get("detail") or {}).get("points") or []
            if not pts or o["subject"].split("/")[1] != "0":
                continue
            st = status.get(o.get("id"), ["?"])
            col = (0, 90, 255) if "written" in st else (255, 140, 0)
            dr.line([(float(p[0]), float(p[1])) for p in pts], fill=col, width=3)
            dr.text((float(pts[0][0]), float(pts[0][1]) - 14), "%s %s" % (o.get("id", "")[-4:], ",".join(st)[:9]), fill=col)
    for o in obs:
        if o.get("quantity") == "glyph_box" and o["subject"] in keys:
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b:
                dr.rectangle(b[:4], outline=(220, 0, 0), width=3)
                dr.text((b[0], b[3] + 2), o["subject"].split("/", 3)[3], fill=(220, 0, 0))
    for a in json.load(open(ARCS))["labels"]:
        if a["kind"] == "arc" and a["state"] == "confirmed":
            r = a["shape"]["rect"]
            dr.rectangle(r, outline=(0, 170, 0), width=2)
            dr.text((r[0], r[1] - 12), "%s %s" % (a["id"], a.get("sub")), fill=(0, 140, 0))
    im.crop((x0, y0, x1, y1)).save(out)


if __name__ == "__main__":
    main()
