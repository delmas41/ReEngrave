"""ROADMAP 2.290 build -- every note / rest written OFF and not ON (and the reverse), one by one, with the head identity on both arms (READ-ONLY).

    python3 benchmarks/page-heads-ledger-2026-11/lost_notes.py WORKDIR PLATE [--out FILE]

WORKDIR = a `lane_report --from gather` work dir (its `<plate>.<arm>.symbols.json` and `.gathered.record.json`). A host is matched across the arms BY PLACE
(same page and cell, same kind, boxes overlapping); every unmatched one is listed with: its glyph, the box's `Q.MARK_GROUP` OFF and ON (group size, the
other members, ON's `head_how`), and which members of its ON group the ON file wrote (a member written instead at the same place is a twin written ONCE).
"""
import argparse
import json
import pathlib


def load_groups(rec):
    d = json.loads(pathlib.Path(rec).read_text())
    obs = d.get("record", d)["observations"]
    g, det, box = {}, {}, {}
    for o in obs:
        if o.get("quantity") == "mark_group":
            g[o["subject"]] = o["value"]
            det[o["subject"]] = o.get("detail") or {}
        elif o.get("quantity") == "glyph_box":
            box[o["subject"]] = (o.get("detail") or {}).get("bbox_page_px")
    mem = {}
    for k, v in g.items():
        mem.setdefault(v, []).append(k)
    return g, det, mem, box


def ov(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def cell_of(rg):
    return "/".join(str(rg).split("/")[1:5]) if rg else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("plate")
    ap.add_argument("--out")
    a = ap.parse_args()
    w = pathlib.Path(a.work)
    sym = {arm: json.loads((w / ("%s.%s.symbols.json" % (a.plate, arm))).read_text()) for arm in ("off", "on")}
    grp = {arm: load_groups(w / ("%s.%s.gathered.record.json" % (a.plate, arm))) for arm in ("off", "on")}
    hosts = {arm: [h for h in sym[arm]["hosts"] if h["kind"] in ("note", "rest")] for arm in ("off", "on")}
    written_on = {h.get("rg") for h in hosts["on"]}
    written_off = {h.get("rg") for h in hosts["off"]}
    lines = []
    for side, src, dst in (("LOST (OFF, not ON)", "off", "on"), ("GAINED (ON, not OFF)", "on", "off")):
        used = set()
        for h in hosts[src]:
            m = None
            for i, x in enumerate(hosts[dst]):
                if i in used or x["kind"] != h["kind"] or x["page"] != h["page"] or cell_of(x.get("rg")) != cell_of(h.get("rg")):
                    continue
                if h.get("box") and x.get("box") and ov(h["box"], x["box"]) and x.get("pitch") == h.get("pitch"):
                    m = i
                    break
            if m is not None:
                used.add(m)
                continue
            rg = h.get("rg")
            gO, dO, mO, _ = grp["off"]
            gN, dN, mN, _ = grp["on"]
            offm = mO.get(gO.get(rg), [])
            onm = mN.get(gN.get(rg), [])
            lines.append("%s  %s p%s m%s %s %s %s  box %s\n    OFF group %d %s (written OFF: %s)\n    ON  group %d %s how %s (written ON: %s)" % (
                side, a.plate, h["page"], h["measure"], h["kind"], h.get("type"), h.get("pitch"), [round(v) for v in h.get("box") or []],
                len(offm), [k for k in offm if k != rg], [k for k in offm if k in written_off],
                len(onm), [k for k in onm if k != rg], (dN.get(rg) or {}).get("head_how"), [k for k in onm if k in written_on]))
            lines[-1] = ("%s  glyph %s\n" % (lines[-1].split("\n")[0], rg)) + "\n".join(lines[-1].split("\n")[1:])
    print("\n".join(lines))
    if a.out:
        pathlib.Path(a.out).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
