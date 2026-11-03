"""2.251 carry (c): every <clef> the exported MusicXML writes after a part's first measure, and every red "clef?" bar, per part and
measure number -- to set against the clefs printed inside a system (where a written clef must stand) and the claims.

python3 work-2.251/xml_clefs.py FILE.musicxml
"""
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
names = {sp.get("id"): (sp.findtext("part-name") or "").strip() for sp in root.iter("score-part")}
for part in root.iter("part"):
    out, red, first = [], [], True
    for m in part.iter("measure"):
        for att in m.findall("attributes"):
            for c in att.findall("clef"):
                if not first:
                    out.append((m.get("number"), c.findtext("sign") + (c.findtext("line") or "")))
            first = False
        for w in m.iter("words"):
            if (w.text or "").strip() == "clef?":
                red.append(m.get("number"))
    if out or red:
        print(part.get("id"), names.get(part.get("id"), "")[:16], "clefs:", out, "| red clef?:", red)
