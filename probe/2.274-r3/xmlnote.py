"""python3 xmlnote.py ARM KEY [KEY..]: the <note> elements stamped rg=KEY and their <notations> (slur/tied), with the voice and measure"""
import sys
import xml.etree.ElementTree as ET
from load import *  # noqa

arm = sys.argv[1]
root = ET.fromstring((WORK / ("%s.musicxml" % arm)).read_text())
want = set(sys.argv[2:])
for part in root.iter("part"):
    for m in part.findall("measure"):
        for el in m.findall("note"):
            if el.get("rg") in want:
                nt = el.find("notations")
                sl = [] if nt is None else [(s.tag, s.get("type"), s.get("number")) for s in nt if s.tag in ("slur", "tied")]
                print(part.get("id"), "m", m.get("number"), el.get("rg"), "voice", el.findtext("voice"), "chord" if el.find("chord") is not None else "", "pitch", (el.findtext("pitch/step") or "") + (el.findtext("pitch/octave") or ""), sl)
