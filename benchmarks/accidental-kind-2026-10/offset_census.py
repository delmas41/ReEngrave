"""2.247 r2: how far the detector's accidental box sits off the mark's own ink (the r2 ink-grown extent, `box_offset_sp`), by plate and by
where the box stands (above / in / below the staff, from its centre's staff position). Reads ON-arm gathered records (OMR_ACCIDENTAL_KIND=1).
usage: offset_census.py PLATE=RECORD.json [PLATE=RECORD.json ...]"""
import collections
import json
import sys


def main(*args):
    for a in args:
        plate, path = a.split("=", 1)
        rec = json.load(open(path))
        rec = rec.get("record", rec)
        tab = collections.defaultdict(collections.Counter)
        for r in rec["observations"]:
            if r["quantity"] != "accidental_staff_position":
                continue
            d = r.get("detail") or {}
            fam = d.get("family") or {}
            off = (fam.get("features") or {}).get("box_offset_sp")
            if not off:
                tab["no ink"]["n"] += 1
                continue
            cp = d.get("box_centre_position")
            where = "above" if cp is not None and cp < -1 else ("below" if cp is not None and cp > 9 else "in")
            t = tab[where]
            t["n"] += 1
            worst = max(abs(off["top"]), abs(off["bottom"]))
            t["ink beyond box >=0.5sp (top or bottom)"] += worst >= 0.5
            t["ink beyond box >=1sp"] += worst >= 1.0
            t["box above its ink (top and bottom both higher by >=0.25)"] += off["top"] >= 0.25 and off["bottom"] >= 0.25
            t["box below its ink"] += off["top"] <= -0.25 and off["bottom"] <= -0.25
        print(plate)
        for k, v in tab.items():
            print("   %-6s %s" % (k, dict(v)))


if __name__ == "__main__":
    main(*sys.argv[1:])
