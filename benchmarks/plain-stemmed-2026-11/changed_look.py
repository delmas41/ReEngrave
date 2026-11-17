"""ROADMAP 2.314 -- our own look (rule 7) at EVERY note the flag newly writes (OFF refused, ON written): is it a note? numbered, 12 to a sheet.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/plain-stemmed-2026-11 python3 benchmarks/plain-stemmed-2026-11/changed_look.py SCRATCH OUTDIR
"""
import json
import sys
from pathlib import Path

from beam_crops import render, sheet

S, OUT = sys.argv[1], Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
items = []
for plate, tag in (("litolff", "lit"), ("brahms", "bra")):
    f0 = json.load(open(f"{S}/p314/x/{tag}.f0.json"))
    f1 = json.load(open(f"{S}/p314/x/{tag}.f1.json"))
    pop = json.load(open(f"{S}/p314/pop.json"))[plate]
    extra = json.load(open(f"{S}/2311/{tag}-a.extra.json"))
    for r in sorted(pop, key=lambda r: r["it"]["key"]):
        k = r["it"]["key"]
        if not f0["glyphs"][k]["fate"].startswith("written") and f1["glyphs"][k]["fate"].startswith("written"):
            items.append((plate, dict(r["it"], plate=plate), extra))
json.dump([(p, i["key"]) for p, i, _ in items], open(OUT / "order.json", "w"))
for s in range(0, len(items), 12):
    imgs, labs = [], []
    for n, (p, it, extra) in enumerate(items[s:s + 12], s + 1):
        crop, _ = render(it, extra, 560)
        imgs.append(crop)
        labs.append("%d %s p%d %s" % (n, p[:3], it["page"], it["key"]))
    sheet(imgs, OUT / ("changed_%d.png" % (s // 12 + 1)), 3, labs)
print(len(items))
