"""2306 r9: the `no_stroke` page-stem abstentions of real heads the cell join still stems -- split by what the page reader saw beside the head:
a vertical held by another mark's claim (`held`: which owner), verticals near but not at the engraving side (`near`), or nothing. Usage: nostroke9.py REC RFPREFIX"""
import sys, json, re, collections
rec, pre = sys.argv[1], sys.argv[2]
txt = open(rec, encoding="utf-8").read()
det = {}
for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","reader":"cv_page_stems","frame":"[^"]*","reason":"[a-z_]+","detail":', txt):
    s = txt[m.end():m.end() + 4000]
    depth = 0
    for i, ch in enumerate(s):
        depth += ch == "{"
        depth -= ch == "}"
        if depth == 0:
            break
    det[m.group(1)] = json.loads(s[:i + 1])
read = set(m.group(1) for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","value":"obs:', txt))
del txt
B = json.load(open(pre + ".on.json"))
last = collections.defaultdict(dict)
for v in B["verdicts"]:
    if v["q"] in ("notehead_is_not_a_notehead", "glyph_owner", "head_stem"):
        last[v["s"]][v["q"]] = v


def real(g):
    n = last[g].get("notehead_is_not_a_notehead")
    if n and n["o"] == "decided" and n["v"] is True:
        return False
    o = last[g].get("glyph_owner")
    if o and o["o"] == "decided" and isinstance(o["v"], str) and o["v"] != "staff/" + "/".join(g.split("/")[1:4]):
        return False
    return "head_stem" in last[g]


c = collections.Counter()
ex = collections.defaultdict(list)
for g, d in det.items():
    if g in read or not real(g) or last[g]["head_stem"]["o"] != "decided" or d.get("note") != "no_stroke":
        continue
    held = d.get("held") or []
    owners = sorted({str(h[1]) if isinstance(h, (list, tuple)) and len(h) > 1 else str(h.get("owner") if isinstance(h, dict) else h) for h in held})
    if held:
        k = "a vertical there is held by another claim: " + ",".join(owners)
    elif d.get("candidates"):
        k = "candidates refused"
    elif d.get("near"):
        k = "verticals near, none at the head's engraving side"
    else:
        k = "no vertical near at all"
    c[k] += 1
    ex[k].append(g)
for k, n in c.most_common():
    print("%4d  %s   e.g. %s" % (n, k, ex[k][:3]))
