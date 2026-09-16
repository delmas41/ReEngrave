"""How FAR a declared meter travels: measures GOVERNED, not declarations."""
import collections, sys, xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
gov = collections.Counter()
parts_with = collections.defaultdict(set)
for part in root.findall("part"):
    pid = part.get("id")
    cur = None
    for meas in part.findall("measure"):
        t = meas.find("./attributes/time")
        if t is not None:
            n, b = t.findtext("beats"), t.findtext("beat-type")
            if n and b:
                cur = "%s/%s" % (n, b)
        gov[cur] += 1
        if cur:
            parts_with[cur].add(pid)
n = sum(gov.values())
print("MEASURES GOVERNED by each declared meter (of %d):" % n)
for k, v in gov.most_common():
    print("   %-10s %5d  (%5.1f%%)   in %d parts"
          % (k or "(none)", v, 100.0 * v / n, len(parts_with.get(k, ()))))
