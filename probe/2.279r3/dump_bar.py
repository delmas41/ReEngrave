import sys, xml.etree.ElementTree as ET
plate, part, num = sys.argv[1:4]
for arm in ("off","on"):
    r=ET.parse("out/lane-report/2.279-r4/work/%s.%s.musicxml"%(plate,arm)).getroot()
    for p in r.iter("part"):
        if p.get("id")!=part: continue
        for m in p.findall("measure"):
            if m.get("number")==num:
                print("=====",arm)
                for el in m:
                    if el.tag=="note":
                        pi=el.find("pitch")
                        print("note",el.get("rg"),el.get("color"),el.findtext("type"),el.findtext("duration"),
                              pi is not None and (pi.findtext("step"),pi.findtext("alter"),pi.findtext("octave")), el.findtext("accidental"),
                              "chord" if el.find("chord") is not None else "", "grace" if el.find("grace") is not None else "")
                    else: print(el.tag,[(c.tag,c.get("color"),(c.text or "")[:30]) for c in el.iter() if c.get("color") or (c.text and c.text.strip())][:2])
