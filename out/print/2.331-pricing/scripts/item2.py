"""Item 2: slurs / ties written twice (both end notes shared), by writer, from the probe log and checked on the MusicXML."""
import sys, json, re, collections
probe, xml_path, pages, out = sys.argv[1], sys.argv[2], {int(p) for p in sys.argv[3].split(",")}, sys.argv[4]
L = json.load(open(probe))
pg = lambda g: int(str(g).split("/")[1]) if g else None
sl = [s for s in L["spans"] if s.get("stage") == "final_slur" and pg(s["first"]) in pages]
ti = [s for s in L["spans"] if s.get("stage") == "tie" and pg(s["first"]) in pages]
by = collections.defaultdict(list)
for s in sl:
    by[(s["fid"], s["lid"])].append(s)
dup = {k: v for k, v in by.items() if len(v) > 1}
print("slur spans (final, sample pages):", len(sl), "pairs of ends:", len(by), "pairs written more than once:", len(dup),
      "extra copies:", sum(len(v) - 1 for v in dup.values()))
print("  by writer combination:", collections.Counter(tuple(sorted(x["writer"] for x in v)) for v in dup.values()))
tby = collections.defaultdict(list)
for s in ti:
    tby[(s["fid"], s["lid"])].append(s)
tdup = {k: v for k, v in tby.items() if len(v) > 1}
print("tie spans:", len(ti), "tie pairs more than once:", len(tdup))
both = [k for k in by if k in tby]
print("slur sharing both ends with a tie:", len(both), collections.Counter(by[k][0]["writer"] for k in both))
# the file: per part, slur start/stop by number -> (start rg, stop rg)
xml = open(xml_path).read()
fx = collections.Counter()
ties_x = collections.Counter()
for part in re.findall(r"<part id=.*?</part>", xml, re.S):
    open_ = {}
    for m in re.finditer(r'<note rg="([^"]+)"(.*?)</note>', part, re.S):
        g, body = m.group(1), m.group(2)
        for t, n in re.findall(r'<slur[^>]*type="(start|stop)"[^>]*number="(\d+)"', body) + \
                [(t, n) for n, t in re.findall(r'<slur[^>]*number="(\d+)"[^>]*type="(start|stop)"', body)]:
            if t == "start":
                open_[n] = g
            elif n in open_:
                fx[(open_.pop(n), g)] += 1
        nt = len(re.findall(r'<tied[^>]*type="start"', body))
        if nt:
            ties_x[g] += nt
fx = {k: v for k, v in fx.items() if pg(k[0]) in pages}
print("FILE: slurs", sum(fx.values()), "same two notes more than once:", sum(1 for v in fx.values() if v > 1),
      "| notes with two tie starts:", sum(1 for g, v in ties_x.items() if v > 1 and pg(g) in pages))
rows = []
for k, v in dup.items():
    rows.append(dict(first=v[0]["first"], last=v[0]["last"], writers=[x["writer"] for x in v], kind="slur+slur"))
for k in both:
    rows.append(dict(first=by[k][0]["first"], last=by[k][0]["last"], writers=[by[k][0]["writer"], "record_tie"], kind="slur+tie"))
json.dump(rows, open(out, "w"), indent=1)
