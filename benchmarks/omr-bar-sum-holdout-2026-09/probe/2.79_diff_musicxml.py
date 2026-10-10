"""Per-part, per-measure diff of two MusicXML files from the same record shape.

Prints every (part, measure) whose serialized XML differs, with a one-line
before/after summary (rests/notes/durations/time)."""
import sys
import xml.etree.ElementTree as ET


def measures(path):
    root = ET.parse(path).getroot()
    names = {sp.get("id"): (sp.findtext("part-name") or "") for sp in root.iter("score-part")}
    out = {}
    for part in root.findall("part"):
        pid = part.get("id")
        for m in part.findall("measure"):
            out[(pid, int(m.get("number")))] = (names.get(pid, ""), m)
    return out


def summary(m):
    ev = []
    for e in m:
        if e.tag == "note":
            d = e.findtext("duration")
            r = e.find("rest")
            if r is not None:
                ev.append("R%s%s" % (d, "[M]" if r.get("measure") == "yes" else ""))
            elif e.find("chord") is None:
                ev.append("n%s" % d)
        elif e.tag == "attributes" and e.find("time") is not None:
            ev.append("T%s/%s" % (e.find("time").findtext("beats"), e.find("time").findtext("beat-type")))
    return " ".join(ev)


a = measures(sys.argv[1])
b = measures(sys.argv[2])
changed = []
for k in sorted(set(a) | set(b)):
    if k not in a or k not in b:
        changed.append((k, "only in %s" % ("after" if k in b else "before"), ""))
        continue
    sa = ET.tostring(a[k][1])
    sb = ET.tostring(b[k][1])
    if sa != sb:
        changed.append((k, summary(a[k][1]), summary(b[k][1])))
print("measures before:", len(a), "after:", len(b), "changed:", len(changed))
for (pid, n), x, y in changed:
    print("%s bar %d (%s): %s  ->  %s" % (pid, n, a.get((pid, n), b.get((pid, n)))[0][:14], x, y))
