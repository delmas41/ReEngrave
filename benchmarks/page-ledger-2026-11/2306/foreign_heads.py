"""2306 r12: boxes whose head-ink reading (Q.HEAD_INK, GATHER) says another mark's box stands on their ink (`holds_another_marks_ink`) -- how
many, how many have a page stem, how many the file writes as notes (ON replay). Usage: foreign_heads.py REC RFPREFIX"""
import sys, json, re, collections
rec, pre = sys.argv[1], sys.argv[2]
txt = open(rec, encoding="utf-8").read()
fg = set(m.group(1) for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"head_ink","reader":"[a-z_]+","frame":"[^"]*","reason":"[a-z_]+","detail":\{[^}]*"not_one_head":"holds_another_marks_ink"', txt))
stem = set(m.group(1) for m in re.finditer(r'"subject":"(glyph/[0-9/]+)","quantity":"page_stem","value"', txt))
del txt
B = json.load(open(pre + ".on.json"))
w = {h["rg"] for h in B["hosts"] if h.get("rg") and h.get("kind") == "note"}
print("boxes another mark's box stands on:", len(fg), "| with a page stem:", len(fg & stem), "| written as notes ON:", len(fg & w))
print("examples written:", sorted(fg & w)[:8])
