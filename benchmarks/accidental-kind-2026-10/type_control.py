"""2.247: the 2.201 per-box TYPE control -- every accidental-family box's stroke type in the OFF and ON gathered records of a lane report,
every change listed (subject, detector class, OFF type/why -> ON type/why, features). usage: type_control.py WORK_DIR [OUT.json]"""
import collections
import json
import sys


def fams(path):
    rec = json.load(open(path))
    rec = rec.get("record", rec)
    out, pbox = {}, {}
    for r in rec["observations"]:
        if r["quantity"] == "glyph_box":
            pbox[r["subject"]] = (r.get("detail") or {}).get("bbox_page_px")
        elif r["quantity"] == "accidental_staff_position":
            d = r.get("detail") or {}
            out[r["subject"]] = dict(family=d.get("family") or {}, alteration=d.get("alteration"), cls=d.get("detector_class"))
    for s in out:
        out[s]["page_box"] = pbox.get(s)
    return out


def main(work, out_path=None):
    changes = []
    for plate in ("litolff", "brahms"):
        off, on = fams(f"{work}/{plate}.off.gathered.record.json"), fams(f"{work}/{plate}.on.gathered.record.json")
        tally = collections.Counter()
        for s in sorted(set(off) | set(on)):
            a, b = off.get(s), on.get(s)
            if a is None or b is None:
                tally["only_one_arm"] += 1
                continue
            ta, tb = a["family"].get("type"), b["family"].get("type")
            if (ta, a["alteration"]) == (tb, b["alteration"]):
                tally["same"] += 1
                continue
            k = (a["family"].get("detector_type"), ta, tb, b["family"].get("why"))
            tally[k] += 1
            changes.append(dict(plate=plate, subject=s, cls=a["cls"], off=ta, off_why=a["family"].get("why"), on=tb, on_why=b["family"].get("why"),
                                alt_off=a["alteration"], alt_on=b["alteration"], features_on=b["family"].get("features"), margin_on=b["family"].get("margin"),
                                page=int(s.split("/")[1]), page_box=b["page_box"]))
        print(plate, "boxes", len(on))
        for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
            print("   ", k, v)
    for c in changes:
        print("  ", c["plate"], c["subject"], c["cls"], c["off"], "->", c["on"], c["on_why"], "alt", c["alt_off"], "->", c["alt_on"], c["features_on"])
    if out_path:
        json.dump(changes, open(out_path, "w"), indent=0)


if __name__ == "__main__":
    main(*sys.argv[1:])
