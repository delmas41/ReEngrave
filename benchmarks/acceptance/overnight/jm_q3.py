"""Scratch: from the two page slices, per place: stems, the other box's verdicts, and for the 6 gone tiles the
box at BASE and what sits at that page position in TAG. usage: jm_q3.py"""
import json
import sys

S = "/private/tmp/claude-501/s/slices/%s/litolff/%s.jsonl"


def load(arm, kind):
    return [json.loads(l) for l in open(S % (arm, kind))]


def vq(rows, sub, qs=("notehead_is_not_a_notehead", "duration", "rest_is_not_a_rest", "unboxed_ink_is_a_rest")):
    out = {}
    for v in rows:
        if v.get("subject") == sub and v.get("quantity") in qs:
            out.setdefault(v["quantity"], []).append(v)
    for q, vs in out.items():
        sup = {x["supersedes"] for x in vs if x.get("supersedes")}
        live = [x for x in vs if x["id"] not in sup] or vs
        v = live[-1]
        yield q, v["outcome"], json.dumps(v.get("value"))[:80], v.get("reason")


def box(obs, sub):
    for o in obs:
        if o["subject"] == sub and o["quantity"] == "glyph_box":
            return o["value"][0], o["detail"]["bbox_page_px"]


places = [("glyph/3/1/2/15/", ["0", "2"]), ("glyph/3/0/4/3/", ["12", "13"]), ("glyph/4/0/7/7/", ["10", "2"])]
for arm in ("base", "tag"):
    obs, ver = load(arm, "observations"), load(arm, "verdicts")
    print("=====", arm)
    for pre, idx in places:
        for i in idx:
            s = pre + i
            print(s, box(obs, s))
            for r in vq(ver, s):
                print("    ", r)
        cell = pre
        for o in obs:
            if o["subject"].startswith(pre) and o["quantity"] == "stem":
                print("   STEM", o["id"], o["subject"], json.dumps(o["value"])[:100], o.get("reader"))
        # stem rows may be filed on cell subject
    stems = [o for o in obs if o["quantity"] == "stem"]
    print("n stem rows on pages", len(stems), "sample subject", stems[0]["subject"] if stems else None)
