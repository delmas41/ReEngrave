"""2306 r9: real heads with no page stem (the retire blocker). From the gather: every glyph's Q.PAGE_STEM abstention and its `how`; from the ON replay
(pre-retire): which heads are REAL heads of their own staff (not refused as non-notes, not a copy whose decided owner is another staff, no page stem
reading) and whether the cell join still stemmed them (those are the stems retire takes away). Usage: nostem9.py REC.json RFPREFIX"""
import sys, json, re, collections
rec, pre = sys.argv[1], sys.argv[2]
txt = open(rec, encoding="utf-8").read()
ab = {}
for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","reader":"cv_page_stems","frame":"[^"]*","reason":"([a-z_]+)","detail":\{"note":"([a-z_]+)"', txt):
    ab[m.group(1)] = m.group(3)
read = set(m.group(1) for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","value":"obs:', txt))
del txt
B = json.load(open(pre + ".on.json"))
last = collections.defaultdict(dict)
for v in B["verdicts"]:
    if v["q"] in ("notehead_is_not_a_notehead", "glyph_owner", "head_stem"):
        last[v["s"]][v["q"]] = v
written = {h["rg"] for h in B["hosts"] if h.get("rg") and h.get("kind") == "note"}


def real(g):
    n = last[g].get("notehead_is_not_a_notehead")
    if n and n["o"] == "decided" and n["v"] is True:
        return False
    o = last[g].get("glyph_owner")
    if o and o["o"] == "decided" and isinstance(o["v"], str) and o["v"] != "staff/" + "/".join(g.split("/")[1:4]):
        return False
    return "head_stem" in last[g]


heads = [g for g in last if real(g)]
nostem = [g for g in heads if g not in read]
by = collections.Counter(ab.get(g, "no page reading at all") for g in nostem)
cell = [g for g in nostem if (last[g]["head_stem"]["o"] == "decided")]
byc = collections.Counter(ab.get(g, "no page reading at all") for g in cell)
print("real heads %d | with a page stem %d | with NO page stem %d" % (len(heads), len(heads) - len(nostem), len(nostem)))
for k, n in by.most_common():
    print("   %4d  %s" % (n, k))
print("of those, stemmed today by the cell join (what retire takes away): %d; written ON: %d" % (len(cell), sum(1 for g in cell if g in written)))
for k, n in byc.most_common():
    print("   %4d  %s" % (n, k))
