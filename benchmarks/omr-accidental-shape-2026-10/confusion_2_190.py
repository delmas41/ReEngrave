"""ROADMAP 2.190 cause step: the detector's accidental class pairs on the frozen sample pages (stored GATHER rows of the 20261020-night
record, no merge applied there), merged exactly as 2.186 merges (`one_ink.plan`). Prints pair counts, margins, and single-box class counts.
usage: confusion_2_190.py [--dump FILE]   (STAGED GATHER rows, replay; reads the per-page slices lane_report cut)"""
import collections, json, sys
from tools.omr.staged import lane_report as LR, one_ink as OI

def load(plate):
    s = LR.load_sample()
    pages = set(s["plates"][plate]["pages"])
    d = LR.slice_dir(plate, "20261020-night")
    cells = collections.defaultdict(list)
    for l in open(d / "observations.jsonl"):
        o = json.loads(l)
        if o["quantity"] != "glyph_box" or (o.get("detail") or {}).get("category") != "accidental":
            continue
        cls = o["value"][0]
        if cls.lower().startswith("key"):
            continue
        sub = o["subject"].split("/")
        if int(sub[1]) not in pages:
            continue
        cells[tuple(sub[:-1])].append((cls, *o["value"][1:5], float(o["score"] or 0), o["subject"], o["detail"].get("bbox_page_px")))
    return cells

def main():
    out = {}
    for plate in ("litolff", "brahms"):
        cells = load(plate)
        single = collections.Counter(); pairs = collections.Counter(); margins = collections.defaultdict(list); dump = []
        for key, bx in cells.items():
            p = OI.plan([b[:6] for b in bx])
            absorbed = {j for i in p.values() for j in i["absorbed"]}
            for i, info in p.items():
                for j in info["absorbed"]:
                    k = (bx[i][0], bx[j][0]); pairs[k] += 1
                    margins[k].append(bx[i][5] - bx[j][5])
                dump.append(dict(plate=plate, winner=bx[i][0], wconf=bx[i][5], rivals=[(bx[j][0], bx[j][5]) for j in info["absorbed"]],
                                 margin=info["margin"], subject=bx[i][6], bbox=bx[i][7]))
            for i, b in enumerate(bx):
                if i not in absorbed and i not in p:
                    single[b[0]] += 1
        print("==", plate, "cells with accidentals", len(cells), "merged inks", sum(pairs.values()), "single boxes", sum(single.values()))
        print(" single-box classes:", dict(single))
        for k, n in pairs.most_common():
            m = sorted(margins[k]); q = lambda f: round(m[int(f * (len(m) - 1))], 3)
            print("  winner %-18s over %-18s n=%3d  margin min %.3f p25 %.3f med %.3f p75 %.3f" % (k[0], k[1], n, m[0], q(.25), q(.5), q(.75)))
        out[plate] = dump
    if "--dump" in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index("--dump") + 1], "w"))
main()
