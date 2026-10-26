"""2.201: Sean's answered accidental tiles, OFF vs ON arm of a lane report (the written <accidental> of the note each tile is about).
usage: before_after.py WORK_DIR [OUT.json]   (WORK_DIR = out/lane-report/2.201/work, holding <plate>.<off|on>.symbols.json)
Tiles on pages outside the report's counted pages are listed as `not counted`. Tile box = the NOTE (2.186b, 2.190, 2.193, 2.199b) or the ACCIDENTAL (2.203)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import truth_tiles as TT

NORM = {"sharp": "sharp", "flat": "flat", "natural": "natural", "double-sharp": "sharp", "flat-flat": "flat", "sharp-sharp": "sharp"}


def host_for(hosts, page, box, accidental_box, unit):
    bx0, by0, bx1, by1 = box
    cand = []
    for h in hosts:
        if h["kind"] != "note" or h["page"] != page or not h.get("box"):
            continue
        hb = h["box"]
        if accidental_box:       # the note to the RIGHT of the accidental, at its height
            gap = hb[0] - bx1
            if -0.5 * unit <= gap <= 3.0 * unit and hb[3] > by0 - unit and hb[1] < by1 + unit:
                cand.append((abs(gap) + abs((hb[1] + hb[3]) / 2 - (by0 + by1) / 2) / 4.0, h))
        else:
            iw, ih = min(bx1, hb[2]) - max(bx0, hb[0]), min(by1, hb[3]) - max(by0, hb[1])
            if iw > 0 and ih > 0:
                cand.append((-iw * ih, h))
    return min(cand, key=lambda t: t[0])[1] if cand else None


def acc_of(h):
    if h is None:
        return "no note written"
    a = (h.get("sub") or {}).get("accidental") or []
    return NORM.get(a[0], a[0]) if a else "none"


if __name__ == "__main__":
    work = sys.argv[1]
    arms = {}
    for plate in ("litolff", "brahms"):
        for arm in ("off", "on"):
            p = os.path.join(work, "%s.%s.symbols.json" % (plate, arm))
            if os.path.exists(p):
                arms[(plate, arm)] = json.load(open(p))
    out, tally = [], {"off": 0, "on": 0, "n": 0}
    unit = {"litolff": 15.75, "brahms": 32.0}
    for t in TT.load():
        a = {k: arms.get((t["plate"], k)) for k in ("off", "on")}
        if not a["off"] or not a["on"]:
            continue
        counted = any(h["page"] == t["page"] for h in a["off"]["hosts"])
        row = dict(set=t["set"], tile=t["tile"], plate=t["plate"], page=t["page"], sean=t["sean"])
        if not counted:
            row.update(off="not counted", on="not counted")
        else:
            acc_box = t["set"] == "2.203"
            for k in ("off", "on"):
                h = host_for(a[k]["hosts"], t["page"], t["box"], acc_box, unit[t["plate"]])
                row[k] = acc_of(h)
                row[k + "_blue"] = bool(h and h.get("blue"))
            tally["n"] += 1
            for k in ("off", "on"):
                tally[k] += int(row[k] == t["sean"])
        out.append(row)
    for r in out:
        print("%-6s %-3s %-2s p%-2s sean=%-8s OFF=%-9s ON=%-9s%s" % (r["set"], r["tile"], r["plate"][0], r["page"], r["sean"], r["off"], r["on"],
              "  (ON blue)" if r.get("on_blue") else ""))
    print("counted tiles", tally["n"], "right OFF", tally["off"], "right ON", tally["on"])
    if len(sys.argv) > 2:
        json.dump(dict(rows=out, tally=tally), open(sys.argv[2], "w"), indent=1)
