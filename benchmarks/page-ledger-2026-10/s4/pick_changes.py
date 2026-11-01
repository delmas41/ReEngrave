"""2.240 step 3: 12 blind tiles on places the FILE changed (a head whose owner moved; an arc whose staff moved) plus tile 8's place.
Each tile draws the staff the ON file writes the mark on.

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-10/s4/pick_changes.py OUT_ITEMS.json litolff:OFF.json:ON.json brahms:OFF.json:ON.json
"""
import collections
import json
import pathlib
import random
import sys

from tools.omr.staged.judged import iter_array

LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": str(LIB / "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
       "brahms": str(LIB / "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
TILE8 = dict(plate="litolff", page=4, kind="owner", glyph="glyph/4/1/1/3/5", box=[971.2875, 2404.145, 995.8575, 2425.7225],
             staff="staff/4/1/2", why="s3 tile 8's place: Sean 'belongs to the staff below'; step 3 now decides staff/4/1/2 (ledger_and_stem)")


def load(path):
    vs, boxes, spans = {}, {}, {}
    for v in iter_array(pathlib.Path(path), "verdicts"):
        if v.get("quantity") in ("glyph_owner", "arc_owner"):
            vs[(v["quantity"], v["subject"])] = v
    for o in iter_array(pathlib.Path(path), "observations"):
        if o.get("quantity") == "glyph_box":
            boxes[o["subject"]] = (o.get("detail") or {}).get("bbox_page_px")
        elif o.get("quantity") == "page_span" and o.get("value") == "arc":
            for p in (o.get("detail") or {}).get("pieces") or []:
                spans[p] = o
    return vs, boxes, spans


def main():
    out = sys.argv[1]
    heads, arcs = [], []
    for spec in sys.argv[2:]:
        plate, off, on = spec.split(":")
        voff, _b, _s = load(off)
        von, boxes, spans = load(on)
        seen_span = set()
        for k, v in von.items():
            o = voff.get(k)
            if not o or (o.get("value") == v.get("value")) or v.get("outcome") != "decided":
                continue
            q, s = k
            pg = int(s.split("/")[1])
            if q == "glyph_owner" and v.get("reason") == "page_owner" and boxes.get(s):
                heads.append(dict(plate=plate, pdf=PDF[plate], page=pg, kind="head_owner_moved", glyph=s, box=boxes[s], staff=v["value"],
                                  off_owner=o.get("value"), off_reason=o.get("reason"), on_reason=(v.get("detail") or {}).get("page_owner")))
            elif q == "arc_owner" and v.get("reason") == "page_span_owner" and s in spans:
                sp = spans[s]
                if sp["subject"] in seen_span:
                    continue
                seen_span.add(sp["subject"])
                d = sp.get("detail") or {}
                arcs.append(dict(plate=plate, pdf=PDF[plate], page=pg, kind="arc_staff_moved", glyph=s, span=sp["subject"], box=d.get("box"),
                                 staff=v["value"], off_owner=o.get("value"), off_reason=o.get("reason"),
                                 span_owner_reason=(d.get("owner") or {}).get("reason")))
    # one tile per place (a mark's two copies are one place)
    def uniq(xs):
        seen, res = set(), []
        for x in xs:
            k = (x["plate"], x["page"], round(x["box"][0] / 10), round(x["box"][1] / 10))
            if k not in seen:
                seen.add(k)
                res.append(x)
        return res
    heads, arcs = uniq(heads), uniq(arcs)
    print("head places moved %s; arc places moved %s" % (dict(collections.Counter(h["plate"] for h in heads)),
                                                        dict(collections.Counter(a["plate"] for a in arcs))))
    rng = random.Random(22404)
    pick = []
    for pool, n in ((heads, 6), (arcs, 5)):
        by = collections.defaultdict(list)
        for x in pool:
            by[x["plate"]].append(x)
        for v in by.values():
            rng.shuffle(v)
        got = []
        while len(got) < n and any(by.values()):
            for p in sorted(by):
                if by[p] and len(got) < n:
                    got.append(by[p].pop())
        pick += got
    t8 = dict(TILE8, pdf=PDF["litolff"])
    pick.append(t8)
    rng.shuffle(pick)
    pathlib.Path(out).write_text(json.dumps(pick, indent=1))
    pathlib.Path(out).with_name("pool_changes.json").write_text(json.dumps({"heads": heads, "arcs": arcs}, indent=1))
    print("picked", len(pick), dict(collections.Counter((x["kind"], x["plate"]) for x in pick)))


if __name__ == "__main__":
    main()
