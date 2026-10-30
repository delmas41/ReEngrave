"""What an arm record (2-page gather, pages 3,4) says at the three places, matched BY BOX (cells are cut fresh).
usage: jm_arm.py ARM.record.json [...]"""
import json
import pathlib
import sys

PL = json.loads((pathlib.Path(__file__).parent / "jm_places.json").read_text())
want = []
for p in PL:
    want.append((p["place"], "subject", p["page"], p["box"]))
    want.append((p["place"], "other", p["page"], p["other_box"]))


def close(a, b):
    return all(abs(x - y) < 3 for x, y in zip(a, b))


for path in sys.argv[1:]:
    d = json.load(open(path))
    rec = d.get("record", d)
    obs, vs, ab = rec["observations"], rec["verdicts"], rec.get("abstentions", [])
    print("=====", path.split("/")[-1])
    boxes = {}
    for o in obs:
        if o["quantity"] == "glyph_box":
            boxes[o["subject"]] = o["detail"]["bbox_page_px"]
    for place, role, pg, box in want:
        subs = [s for s, b in boxes.items() if s.startswith("glyph/%d/" % pg) and close(b, box)]
        for s in subs:
            out = []
            for v in vs:
                if v["subject"] == s and v["quantity"] in ("notehead_is_not_a_notehead", "duration"):
                    out.append((v["quantity"][:9], v["outcome"], v.get("reason"), json.dumps(v.get("value"))[:40]))
            fit = [(o["value"], o["detail"].get("ink")) for o in obs if o["subject"] == s and o["quantity"] == "stacked_head_fit"]
            fab = [(a["reason"], a["detail"].get("margin")) for a in ab if a["subject"] == s and a["quantity"] == "stacked_head_fit"]
            print("place", place, role, s, "fit", fit, "fit_abstain", fab)
            for o_ in out[-4:]:
                print("      ", o_)
        if not subs:
            print("place", place, role, "NO BOX AT", box)
