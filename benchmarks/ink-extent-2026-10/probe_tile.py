"""2.248 r2: the raw ink around one head -- per-row ink run spans in a window, the detector box, the grown extent, and the
far-head / ledger rows the record holds for it.  usage: probe_tile.py PLATE RECORD GLYPH"""
import json
import pathlib
import sys

from tools.omr.staged import cell_map as CM
from tools.omr.staged import head_extent

PDF = {"litolff": "library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
UNIT = {"litolff": 15.75, "brahms": 32.0}


def main(plate, path, g):
    rec = json.load(open(path))
    rec = rec.get("record", rec)
    for k in ("observations", "abstentions", "verdicts"):
        for r in rec.get(k, ()):
            if r.get("subject") == g and r.get("quantity") in ("glyph_box", "notehead_staff_position", "far_head_ledger_position",
                                                               "far_head_owner_ledger", "notehead_position", "head_ink", "pitch"):
                print(k[:3], r["quantity"], r.get("value"), r.get("outcome", ""), r.get("reason", ""),
                      json.dumps(r.get("detail") or {})[:300])
    box = [o["detail"]["bbox_page_px"] for o in rec["observations"] if o["subject"] == g and o["quantity"] == "glyph_box"][0]
    page = int(g.split("/")[1])
    (pws, _c), = CM.load_prepared(pathlib.Path(PDF[plate]), [page], root=CM.ROOT_DEFAULT)
    b = pws.page.binary
    got = head_extent.ink_extent(b, box, UNIT[plate])
    print("box", [round(v, 1) for v in box], "extent", got)
    x0, x1 = int(box[0] - 1.0 * UNIT[plate]), int(box[2] + 1.0 * UNIT[plate])
    for y in range(int(box[1] - 0.8 * UNIT[plate]), int(box[3] + 0.8 * UNIT[plate])):
        row = "".join("#" if b[y, x] == 0 else "." for x in range(x0, x1))
        mark = "B" if box[1] <= y <= box[3] else " "
        print("%5d %s %s" % (y, mark, row))
    print("cols", x0, "..", x1, "box x", round(box[0]), round(box[2]))


if __name__ == "__main__":
    main(*sys.argv[1:])
