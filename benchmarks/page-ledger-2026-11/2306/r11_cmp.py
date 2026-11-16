"""2306 r11: page stem readings per glyph, r9 gather vs r11 gather on the same pages: transitions by `how`; for heads newly read by contact, their
direction against the OLD cell join's (the r9 OFF replay: a lead, not truth -- Sean's r10 tiles agreed with it 10 of 10) and whether the r9 replay
called the glyph a real head. Usage: r11_cmp.py R9_REC R11_REC RF9PREFIX PAGES"""
import sys, json, re, collections
r9, r11, rf9, pages = sys.argv[1], sys.argv[2], sys.argv[3], {int(x) for x in sys.argv[4].split(",")}


def readings(path):
    txt = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'"subject":"(glyph/([0-9]+)/[0-9/]+)","quantity":"page_stem","value":"obs:[0-9]+","reader":"cv_page_stems","frame":"[^"]*","score":null,"detail":\{"page_stroke":[0-9]+,"direction":"([a-z]+)".{0,300}?"how":"([a-z_]+)"', txt):
        if int(m.group(2)) in pages:
            out[m.group(1)] = ("read", m.group(4), m.group(3))
    for m in re.finditer(r'"subject":"(glyph/([0-9]+)/[0-9/]+)","quantity":"page_stem","reader":"cv_page_stems","frame":"[^"]*","reason":"[a-z_]+","detail":\{"note":"([a-z_]+)"', txt):
        if int(m.group(2)) in pages:
            out[m.group(1)] = ("abstain", m.group(3), None)
    return out


A, B = readings(r9), readings(r11)
O = json.load(open(rf9 + ".off.json"))
L = collections.defaultdict(dict)
for v in O["verdicts"]:
    if v["q"] in ("stem_direction", "notehead_is_not_a_notehead", "glyph_owner"):
        L[v["s"]][v["q"]] = v


def real(g):
    n = L[g].get("notehead_is_not_a_notehead")
    if n and n["o"] == "decided" and n["v"] is True:
        return "refused"
    o = L[g].get("glyph_owner")
    if o and o["o"] == "decided" and isinstance(o["v"], str) and o["v"] != "staff/" + "/".join(g.split("/")[1:4]):
        return "copy"
    return "real"


t = collections.Counter()
for g in set(A) | set(B):
    a, b = A.get(g), B.get(g)
    if (a and a[:2]) != (b and b[:2]):
        t[("%s/%s" % a[:2] if a else "none", "%s/%s" % b[:2] if b else "none")] += 1
print("glyph readings r9 -> r11 that changed:")
for k, n in t.most_common():
    print("  %4d  %s -> %s" % (n, k[0], k[1]))
c = collections.Counter()
for g, b in B.items():
    if b[1] == "contact_with_head_ink":
        od = (L[g].get("stem_direction") or {}).get("v")
        c[(real(g), "agrees with old join" if od == b[2] else ("old join %s" % od))] += 1
print("contact readings:", sum(c.values()))
for k, n in c.most_common():
    print("  %4d  %s" % (n, k))
json.dump({g: [A.get(g), B.get(g), real(g), (L[g].get("stem_direction") or {}).get("v")] for g in B if B[g][1] == "contact_with_head_ink"},
          open(r11 + ".contact.json", "w"))
