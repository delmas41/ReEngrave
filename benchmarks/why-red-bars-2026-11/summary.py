"""2.291: bars the export did not write plain, by status / rule reason / meter source / unread-glyph reasons. usage: summary.py BARS.json [label]"""
import collections
import json
import sys

bars = json.load(open(sys.argv[1]))
print("==", sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
red = [b for b in bars if b["red"]]
par = [b for b in bars if b["status"] == "partial"]
print("red bars", len(red), "notes", sum(b["red"]["noteheads_and_rests"] for b in red), "(blue inside:", sum(b["red"]["guessed"] for b in red), ")")
print("  deciding rule (_partial_bar_plan why):", dict(collections.Counter(b["why"] for b in red)))
print("  meter source:", dict(collections.Counter((b.get("meter") or {}).get("reason") for b in red)))
print("  red bars naming any unread glyph:", sum(1 for b in red if b["unread_glyphs"]), "; reasons:", dict(collections.Counter(r for b in red for r in (b["unread_glyphs"] or []))))
print("partial bars", len(par), "rows in gap", sum(b["rows_in_gap"] or 0 for b in par), "; unread-glyph reasons:", dict(collections.Counter(r for b in par for r in b["unread_glyphs"])))
print("  partial bars with notes in the gap:", [("/".join(map(str, b["key"])), b["rows_in_gap"]) for b in par if b["rows_in_gap"]])
