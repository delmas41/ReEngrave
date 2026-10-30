import json
S = "/private/tmp/claude-501/s/slices/%s/litolff/%s.jsonl"
subs = ["glyph/16/1/9/7/4", "glyph/16/1/1/2/5", "glyph/13/1/2/9/1", "glyph/13/1/2/9/2", "glyph/13/1/8/13/5", "glyph/13/1/8/11/6"]
Q = ("notehead_is_not_a_notehead", "duration", "rest_is_not_a_rest", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest")
D = {}
for arm in ("base", "tag"):
    obs = [json.loads(l) for l in open(S % (arm, "observations"))]
    ver = [json.loads(l) for l in open(S % (arm, "verdicts"))]
    boxes = {}
    for o in obs:
        if o["quantity"] == "glyph_box":
            boxes[o["subject"]] = (o["value"][0], o["detail"]["bbox_page_px"])
    live = {}
    for v in ver:
        if v["quantity"] in Q:
            live.setdefault((v["subject"], v["quantity"]), []).append(v)
    D[arm] = (boxes, live)


def stand(live, s):
    out = []
    for (sub, q), vs in live.items():
        if sub == s:
            sup = {x["supersedes"] for x in vs if x.get("supersedes")}
            l = [x for x in vs if x["id"] not in sup] or vs
            v = l[-1]
            out.append((q[:12], v["outcome"], v.get("reason"), json.dumps(v.get("value"))[:50]))
    return out


for s in subs:
    bb = D["base"][0].get(s)
    print("#####", s, "BASE box", bb)
    for x in stand(D["base"][1], s):
        print("   BASE", x)
    tb = D["tag"][0].get(s)
    print("   TAG same key box:", tb, stand(D["tag"][1], s))
    if bb:
        cx, cy = (bb[1][0] + bb[1][2]) / 2, (bb[1][1] + bb[1][3]) / 2
        for k, (cl, b) in D["tag"][0].items():
            pass
        for k, (cl, b) in D["tag"][0].items():
            if k.startswith("glyph/%s/" % s.split("/")[1]):
                tx, ty = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                if abs(tx - cx) < 15 and abs(ty - cy) < 15:
                    print("   TAG at that place:", k, cl, [round(v) for v in b], stand(D["tag"][1], k))
