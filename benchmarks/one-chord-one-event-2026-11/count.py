"""2.300 step 1 count: from dump_events.py output, the bars where two note events stand at (nearly) one onset on one
stream and removing the double count would make the bar sum to its meter.
    python3 benchmarks/one-chord-one-event-2026-11/count.py EV.json [--list]
GEOMETRY (an agent's look is not evidence; this only lists leads): two NOTE events A,B adjacent in x, same stream (or no
voice split), centre distance dx <= DXW head widths and vertical gap of their nearest heads <= DYH head heights
(a second: dx ~ 1 width, nearest heads ~ 1 height apart; a stack: dx ~ 0).
EXPLAINS: red bar, sum(counted) - d == want for d in {A.beats, B.beats} (one event kept, the other's time removed).
"""
import collections
import json
import sys
KINDS = collections.defaultdict(collections.Counter)
SHARED = []

DXW = 1.35
DYC = 1.15   # centre-to-centre vertical offset, in head heights (a second is ~0.5-1.0)


def box(h):
    x, y, w, hh = h["bbox"]
    return x, y, w, hh


def pair_geom(a, b):
    """(dx in head widths, dy in head heights, stems compatible) for the closest head pair, or None."""
    best = None
    for p in [h for h in a["heads"] if h.get("bbox")]:
        for q in [h for h in b["heads"] if h.get("bbox")]:
            px, py, pw, ph = box(p)
            qx, qy, qw, qh = box(q)
            w = (pw + qw) / 2.0
            h = (ph + qh) / 2.0
            dx = abs((px + pw / 2.0) - (qx + qw / 2.0)) / w
            dy = abs((py + ph / 2.0) - (qy + qh / 2.0)) / h
            ok = (not p.get("stem")) or (not q.get("stem")) or p["stem"] == q["stem"]
            shared = bool(p.get("stem_id")) and p.get("stem_id") == q.get("stem_id")
            kind = ("same_stem_id" if shared else "partner_no_stem" if bool(p.get("stem")) != bool(q.get("stem")) else
                    "neither_has_stem" if not p.get("stem") else "both_stem_" + ("same" if p["stem"] == q["stem"] else "opposite"))
            if best is None or (dx + dy) < (best[0] + best[1]):
                best = (dx, dy, ok, kind)
    return best


def pairs(bar):
    evs = [(i, e) for i, e in enumerate(bar["events"]) if e["kind"] == "chord" and e["heads"]]
    streams = bar["streams"]
    out = []
    # a stem is ONE event: any two heads in different events that share a stem id, wherever they stand
    for x in range(len(evs)):
        for y in range(x + 1, len(evs)):
            ids = {h.get("stem_id") for h in evs[x][1]["heads"] if h.get("stem_id")} & \
                  {h.get("stem_id") for h in evs[y][1]["heads"] if h.get("stem_id")}
            if ids:
                SHARED.append((bar["key"], evs[x][0], evs[y][0]))
    for (i, a), (j, b) in zip(evs, evs[1:]):
        if streams:
            sa = {k for k, s in enumerate(streams) if i in s}
            sb = {k for k, s in enumerate(streams) if j in s}
            if not (sa & sb):
                continue
        g = pair_geom(a, b)
        if g and 0.6 <= g[0] <= DXW and 0.3 <= g[1] <= 0.8 and g[2]:
            out.append((i, j, g))
    return out


def main():
    d = json.load(open(sys.argv[1]))
    n = {"bars": 0, "red": 0, "red_pairs": 0, "explained": 0, "clean_pairs": 0, "partial_pairs": 0}
    notes_red = notes_expl = notes_all = 0
    rows = []
    for bar in d["bars"]:
        n["bars"] += 1
        nh = sum(len(e["heads"]) for e in bar["events"])
        notes_all += nh
        ps = pairs(bar)
        if bar["red"]:
            n["red"] += 1
            notes_red += nh
        for i, j, g in ps:
            KINDS["red" if bar["red"] else "partial" if bar["partial"] else "clean"][g[3]] += 1
        if bar["red"] and ps:
            n["red_pairs"] += 1
            rr = [x for x in d["red_bars"] if (x["page"], x["system"], x["staff"], x["cell"]) == tuple(bar["key"])][0]
            want = rr["want_quarters"]
            counted = rr["counted_quarters"]
            tot = sum(counted) if len(counted) == 1 else None
            ex = False
            if tot is not None:
                for i, j, g in ps:
                    for k in (i, j):
                        if abs(tot - bar["events"][k]["beats"] - want) < 1e-6:
                            ex = True
            if ex:
                n["explained"] += 1
                notes_expl += nh
            rows.append((bar["key"], want, counted, ex, [(i, j, [round(v, 2) if isinstance(v, float) else v for v in g]) for i, j, g in ps]))
        elif bar["partial"] and ps:
            n["partial_pairs"] += 1
        elif not bar["red"] and not bar["partial"] and ps:
            n["clean_pairs"] += 1
    print(sys.argv[1].split("/")[-1], n, "notes: all", notes_all, "in red bars", notes_red, "in explained bars", notes_expl)
    print({k: dict(v) for k, v in KINDS.items()})
    redk = {tuple(r_["page"] if False else r_[k] for k in ("page", "system", "staff", "cell")): r_ for r_ in d["red_bars"]}
    byk = {tuple(b["key"]): b for b in d["bars"]}
    tally = collections.Counter()
    notes_sh = collections.Counter()
    seenk = set()
    for k, i, j in SHARED:
        k = tuple(k)
        b = byk[k]
        st = "red" if b["red"] else "partial" if b["partial"] else "clean"
        tally[st + "_pairs"] += 1
        if k not in seenk:
            seenk.add(k)
            tally[st + "_bars"] += 1
            notes_sh[st] += sum(len(e["heads"]) for e in b["events"])
            if st == "red":
                rr = redk[k]
                tot = sum(rr["counted_quarters"]) if len(rr["counted_quarters"]) == 1 else None
                if tot is not None and any(abs(tot - b["events"][m]["beats"] - rr["want_quarters"]) < 1e-6 for kk, ii, jj in SHARED if tuple(kk) == k for m in (ii, jj)):
                    tally["red_bars_explained_by_merging"] += 1
    print("heads on ONE stem id but in DIFFERENT events:", len(SHARED), "pairs;", dict(tally), "notes in those bars", dict(notes_sh))
    if "--list" in sys.argv:
        for r in rows:
            print(r)


main()
