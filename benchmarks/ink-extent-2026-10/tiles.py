"""2.248 tiles for Sean, drawn from the NEW extent (the head's own ink grown from the detector box): one staff a tile, one thin
orange box, key.json BESIDE tiles/ (cutter: benchmarks/page-ledger-2026-10/s4/tiles.py `cut`).

    PYTHONPATH=. python3 benchmarks/ink-extent-2026-10/tiles.py OUT_DIR ON_L.record.json ON_B.record.json

Tiles: Sean's 'box too small' places (the 2.240 s4 / rules heads) drawn from the extent grown from the SAME detector box, then
places where the ON arm moved a written head's position (`from_head_ink`), drawn from that extent; 12 in all, plates mixed."""
import importlib.util
import json
import pathlib
import random
import sys

from tools.omr.staged import cell_map as CM
from tools.omr.staged import head_extent

HERE = pathlib.Path(__file__).resolve().parent
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": str(LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
       "brahms": str(LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
UNIT = {"litolff": 15.75, "brahms": 32.0}
#: Sean's places (2.240 s4 tiles 1, 6; rules tiles 3, 6, 7), all on the gathered pages L 6,10 / B 0,5; staff = the one he named.
SEAN = [("litolff", "glyph/6/1/2/9/7", "staff/6/1/3", "2.240-s4 tile 1"),
        ("brahms", "glyph/5/1/10/5/8", "staff/5/1/9", "2.240-s4 tile 6"),
        ("litolff", "glyph/6/1/0/11/7", "staff/6/1/1", "2.240-s4-rules tile 3"),
        ("litolff", "glyph/10/1/8/7/11", "staff/10/1/7", "2.240-s4-rules tile 6"),
        ("brahms", "glyph/0/0/11/3/21", "staff/0/0/12", "2.240-s4-rules tile 7")]
README = ("# One plain question\n\nEach picture is a piece of a score page with ONE thin orange box on it and nothing else drawn. "
          "The box only says where to look.\n\n**For every tile:** what is the ink in the box, and does the box hold the whole "
          "mark? If it is a note, which line or space of the full five-line staff is it on?\n\nAnswer by tile number.\n")


def load(path):
    rec = json.load(open(path))
    return rec.get("record", rec)


def main(out_dir, on_l, on_b):
    spec = importlib.util.spec_from_file_location("s4tiles", str(HERE.parent / "page-ledger-2026-10" / "s4" / "tiles.py"))
    s4 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s4)
    s4.README = README
    items = []
    pages_bin = {}

    def binary(plate, page):
        k = (plate, page)
        if k not in pages_bin:
            (pws, _cells), = CM.load_prepared(pathlib.Path(PDF[plate]), [page], root=CM.ROOT_DEFAULT)
            pages_bin[k] = pws.page.binary
        return pages_bin[k]

    recs = {"litolff": load(on_l), "brahms": load(on_b)}
    boxes = {p: {o["subject"]: o["detail"]["bbox_page_px"] for o in r["observations"]
                 if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")} for p, r in recs.items()}
    for plate, g, staff, why in SEAN:
        b = boxes[plate].get(g)
        if not b:
            print("missing", g)
            continue
        page = int(g.split("/")[1])
        got = head_extent.ink_extent(binary(plate, page), b, UNIT[plate])
        ext = got["extent"] or b
        items.append(dict(plate=plate, pdf=PDF[plate], page=page, glyph=g, box=ext, staff=staff, kind="sean_place", was=why,
                          detector_box=b, extent_why=got["why"]))
    moved = []
    for plate, r in recs.items():
        refused = {v["subject"] for v in r["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead"
                   and v["outcome"] == "decided" and v.get("value") is True}
        owner = {v["subject"]: v.get("value") for v in r["verdicts"] if v["quantity"] == "glyph_owner"}
        for o in r["observations"]:
            d = o.get("detail") or {}
            if o["quantity"] != "notehead_staff_position" or "from_head_ink" not in d or o["subject"] in refused:
                continue
            g = o["subject"]
            st = owner.get(g) or "staff/" + "/".join(g.split("/")[1:4])
            moved.append(dict(plate=plate, pdf=PDF[plate], page=int(g.split("/")[1]), glyph=g, box=d["from_head_ink"], staff=st,
                              kind="position_moved", detector_box=boxes[plate].get(g),
                              off_position=d["detector_position_float"], on_position=o["value"]))
    random.Random(2248).shuffle(moved)
    lit = [m for m in moved if m["plate"] == "litolff"]
    bra = [m for m in moved if m["plate"] == "brahms"]
    pick = (lit[:4] + bra[:3])[:7] if len(lit) >= 4 and len(bra) >= 3 else moved[:7]
    items += pick
    items = items[:12]
    random.Random(48).shuffle(items)
    s4.cut(items, out_dir)
    print("tiles:", len(items), "moved places available L %d B %d" % (len(lit), len(bra)))


if __name__ == "__main__":
    main(*sys.argv[1:])
