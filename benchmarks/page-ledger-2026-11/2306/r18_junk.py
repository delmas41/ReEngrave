"""2.306 r18 item 2: notes the OFF arm WRITES on heads the page stem reader read and could stand on NO stem (Q.PAGE_STEM refused: no stroke,
two candidates, read both ways; two voices and no-cell excluded). From one ON gather (its page-stem rows) and the OFF arm's per-glyph export
fates (r16_readjudicate.py). Usage: r18_junk.py GATHERED_ON.record.json FATES.pkl PAGES -> counts by refusal and a list."""
import sys, json, pickle, collections

recp, fp, pages = sys.argv[1], sys.argv[2], {int(p) for p in sys.argv[3].split(",")}
rec = json.load(open(recp)); rec = rec.get("record", rec)
ref = {}
for a in rec.get("abstentions", []):
    if a["quantity"] == "page_stem" and int(a["subject"].split("/")[1]) in pages:
        d = a.get("detail") or {}
        if d.get("how") != "two_voices" and d.get("note") != "no_cell":
            ref[a["subject"]] = d.get("how")
del rec
F = pickle.load(open(fp, "rb"))
c = collections.Counter(); ex = collections.defaultdict(list)
for k, how in ref.items():
    off, on = F["off"].get(k), F["on"].get(k)
    if off in ("written", "written_relocated"):
        c[(how, on)] += 1
        ex[(how, on)].append(k)
print("written OFF on a head the page reader stands on no stem:", sum(c.values()))
for k, n in c.most_common():
    print("%4d %-28s ON fate: %-28s %s" % (n, k[0], k[1], " ".join(ex[k][:5])))
json.dump({"%s|%s" % k: v for k, v in ex.items()}, open(fp.replace(".fates.pkl", ".junk.json"), "w"))
