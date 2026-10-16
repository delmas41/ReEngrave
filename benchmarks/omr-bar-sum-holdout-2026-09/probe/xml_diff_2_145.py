"""2.145 -- which MusicXML bars changed between the OFF and ON replays (re-exported systems only).
usage: xml_diff_2_145.py OFF.musicxml ON.musicxml"""
import sys
import xml.etree.ElementTree as ET


def bars(path):
    root = ET.parse(path).getroot()
    out = {}
    for part in root.findall("part"):
        for m in part.findall("measure"):
            seq = []
            for n in m.findall("note"):
                kind = "rest" if n.find("rest") is not None else "note"
                step = n.findtext("pitch/step") or ""
                octv = n.findtext("pitch/octave") or ""
                seq.append((kind, step + octv, n.findtext("duration"), n.findtext("type"),
                            n.find("rest") is not None and n.find("rest").get("measure") == "yes"))
            out[(part.get("id"), m.get("number"))] = seq
    return out


a, b = bars(sys.argv[1]), bars(sys.argv[2])
changed = [k for k in sorted(set(a) | set(b), key=lambda t: (t[0], int(t[1]) if (t[1] or "").isdigit() else 0))
           if a.get(k) != b.get(k)]
print("bars", len(a), len(b), "changed", len(changed))
for k in changed:
    print(k)
    print("   OFF", a.get(k))
    print("   ON ", b.get(k))
