import json
import collections
from load import *  # noqa

C = json.load(open("census.json"))
rec = record("on")
gb = {}
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/"):
        b = o["detail"]["bbox_page_px"]
        gb[o["subject"]] = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
tally = collections.Counter()
rows = []
for c in C:
    e = c["bind"][0] if c["bind"] else None
    st = None
    if e is None:
        st = "no_entry"
    elif e["status"] == "written":
        a, b = e["start"], e["stop"]
        el = (gb[a][0] - c["x0"]) / SP if a in gb else None
        er = (gb[b][0] - c["x1"]) / SP if b in gb else None
        ok = el is not None and er is not None and abs(el) <= REACH and abs(er) <= REACH
        st = "written_ends_right" if ok else "written_ends_wrong"
        c["bind_err"] = (None if el is None else round(el, 1), None if er is None else round(er, 1))
        c["bind_kind_ok"] = e["kind"] == c["kind"]
    else:
        st = "abstained:" + str(e["why"])
    c["bind_state"] = st
    tally[(st, c["file_off"], c["file_on"])] += 1
for k, v in sorted(tally.items(), key=lambda t: str(t)):
    print(v, k)
json.dump(C, open("census2.json", "w"), indent=1, default=str)
