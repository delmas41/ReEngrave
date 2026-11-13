"""2.302 -- replay `gather.gather_key_object` (the production function, unchanged) on a page rebuilt from the master cell map, with the
detector's boxes read back from a saved slice (extract.py). No detector, no OCR: seconds per page. GATHER-only; nothing downstream.

    PYTHONPATH=. python3 benchmarks/key-object-counts-flats-2026-11/replay.py PLATE EX.json OUT.json PAGE [PAGE...]

Run it with the flag OFF and ON (env) and compare OUT files (compare.py). OUT: {"p/s/li": {"N", "own", "pieces": [...read_pieces...], "area", ...}}.
Control (rule 7): with the flag OFF the replay must reproduce the SAVED row (extract.py `saved`) -- `--control` prints the differences."""
import json
import os
import sys

from tools.omr.staged import cell_map as CM
from tools.omr.staged import gather as G
from tools.omr.staged import lane_report as LR
from tools.omr.staged import claims as CL
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS


class _Det:
    def __init__(self, name, box):
        self.smufl_name = name
        self.pbox = tuple(box)


def main():
    args = sys.argv[1:]
    control = False
    if args and args[0] == "--control":
        control, args = True, args[1:]
    plate, exp, outp = args[0], args[1], args[2]
    pages = [int(p) for p in args[3:]]
    ex = json.load(open(exp))
    G._page_box = lambda cell, det: det.pbox            # the boxes are already page px
    pdf = LR.LIB / LR.PLATES[plate]["pdf"]
    out = {}
    for pws, cells in CM.load_prepared(pdf, pages, root=LR.CELL_MAP_ROOT):
        p = pws.page.page_index if hasattr(pws.page, "page_index") else None
        local = G._system_local(pws.staves)
        log = Log()
        dets = {}
        for c in cells:
            if c.measure_index != 0:
                continue
            s, li = local[c.staff_index]
            row = ex.get("%d/%d/%d" % (p, s, li)) or {"dets": [], "meter_left": None}
            dets[R.cell(p, s, li, 0).to_key()] = [_Det(d["name"], d["box"]) for d in row["dets"]]
            if row.get("meter_left") is not None:
                log.observe(R.staff(p, s, li), Q.CLAIMED_AREA, [row["meter_left"], 0.0, row["meter_left"] + 1.0, 1.0], reader=READERS.CV_KEY_OBJECT,
                            frame="cell:0", cell=0, owner=CL.OWNER_METER, unit="area", standing="READ", source="replay")
        G.gather_key_object(log, pws, cells, local, dets)
        for (s, li) in sorted({v for v in local.values()}):
            key = "%d/%d/%d" % (p, s, li)
            rows = [r for r in log.rows(Q.CLAIMED_AREA, R.staff(p, s, li)) if (r.detail or {}).get("source") == "system_key_object"]
            if not rows:
                continue
            ko = rows[0].detail["key_object"]
            out[key] = {"N": ko["system_count"], "own": ko["own_slots"], "placed": ko["placed_slots"], "more": ko["more_than_system"],
                        "clef": ko["clef_measured"], "pieces": ko["read_pieces"], "space": rows[0].detail.get("space_page_px"),
                        "areas": [(r.value, r.detail.get("part"), r.detail.get("standing")) for r in rows],
                        "counts": ko["system_counts"]}
    json.dump(out, open(outp, "w"))
    print(len(out), "staves", "flag OMR_KEY_OBJECT_COUNTS_FLATS=%s" % os.environ.get("OMR_KEY_OBJECT_COUNTS_FLATS"))
    if control:
        bad = 0
        for key, v in out.items():
            sv = ex.get(key, {}).get("saved") or []
            if not sv:
                continue
            ko = sv[0]["ko"]
            a = [(q["cx"], q["step"], q["shape"]) for q in ko["read_pieces"]]
            b = [(q["cx"], q["step"], q["shape"]) for q in v["pieces"]]
            if a != b or ko["system_count"] != v["N"]:
                bad += 1
                print("DIFF", key, "saved N", ko["system_count"], "own", ko["own_slots"], "replay N", v["N"], "own", v["own"])
        print("control: %d of %d differ from the saved rows" % (bad, len(out)))


if __name__ == "__main__":
    main()
