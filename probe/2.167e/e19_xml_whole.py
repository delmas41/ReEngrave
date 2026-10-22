"""2.167e probe 19: WHOLE notes (not rests) in the exported MusicXML of the 2.173 replay (flag ON, so held bars are written red) of the same 20261018-night records.
Prints the count and the glyph ids carried (the exporter writes glyph ids as reengrave:glyph or similar). usage: e19_xml_whole.py FILE.musicxml"""
import re
import sys
import collections

txt = open(sys.argv[1]).read()
notes = re.findall(r"<note\b.*?</note>", txt, flags=re.S)
whole = [n for n in notes if "<rest" not in n and "<type>whole</type>" in n]
print("notes", len(notes), "whole notes (not rests)", len(whole))
ids = collections.Counter()
for n in whole:
    m = re.search(r"glyph/\d+/\d+/\d+/\d+/\d+", n)
    ids[m.group(0) if m else "?"] += 1
print(list(ids)[:5], "with glyph id:", sum(1 for k in ids if k != "?"))
print(sorted(ids)[:200])
