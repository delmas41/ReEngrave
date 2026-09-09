"""Is the alignment signal real, or is it DENSITY?

⚠️ The pooled figure said 89% of events sit within 0.25 staff spaces of an
event in another staff. The null control said a reshuffle scores 75%. So the
question is not "do events align" -- on a bar holding 160 events across 1200
px they cannot help it -- but WHERE, if anywhere, the alignment carries
information the density does not already supply.

Stratified by how crowded the bar actually is: events per staff-space of bar
width, pooled across every staff of the system.
"""
import json, sys, statistics as st, random
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from probe_nn import events_of, spacing_of

def rows(paths, seed=20260909):
    rng = random.Random(seed)
    out = []
    for path in paths:
        doc = json.load(open(path))
        for pi, page in enumerate(doc.get("pages", [])):
            for si, sysd in enumerate(page.get("systems", [])):
                staves = sysd.get("staves", [])
                if len(staves) < 2:
                    continue
                sp = [v for v in (spacing_of(s) for s in staves) if v]
                if not sp:
                    continue
                sp_med = st.median(sp)
                per_measure = defaultdict(dict)
                for sti, staff in enumerate(staves):
                    for m in staff.get("measures", []):
                        ev = events_of(m)
                        if ev:
                            per_measure[m.get("measure_index")][sti] = ev
                for mi, by_staff in per_measure.items():
                    if len(by_staff) < 2:
                        continue
                    lo = min(x for xs in by_staff.values() for x in xs)
                    hi = max(x for xs in by_staff.values() for x in xs)
                    width_sp = (hi - lo) / sp_med
                    n = sum(len(v) for v in by_staff.values())
                    if width_sp < 1:
                        continue
                    dens = n / width_sp          # events per staff space
                    shuf = {s: [rng.uniform(lo, hi) for _ in xs]
                            for s, xs in by_staff.items()}
                    r, u = [], []
                    for sti, xs in by_staff.items():
                        o_r = [x for o, ox in by_staff.items() if o != sti for x in ox]
                        o_u = [x for o, ox in shuf.items() if o != sti for x in ox]
                        if not o_r:
                            continue
                        r += [min(abs(x - o) for o in o_r) / sp_med for x in xs]
                        u += [min(abs(x - o) for o in o_u) / sp_med for x in shuf[sti]]
                    if r and u:
                        out.append((dens, r, u))
    return out

def main(paths):
    data = rows(paths)
    print(f"bars measured: {len(data)}")
    bands = [(0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 99)]
    print(f"\n{'events/space':>14} {'bars':>5} {'REAL<=0.1':>10} {'NULL<=0.1':>10} {'ratio':>7}"
          f" {'REAL med':>9} {'NULL med':>9}")
    for lo, hi in bands:
        sel = [d for d in data if lo <= d[0] < hi]
        if not sel:
            continue
        R = [v for _, r, _ in sel for v in r]
        U = [v for _, _, u in sel for v in u]
        rr = sum(1 for v in R if v <= 0.1) / len(R)
        uu = sum(1 for v in U if v <= 0.1) / len(U)
        print(f"{lo:>6.1f}-{hi:<7.1f}{len(sel):>5} {rr:>10.3f} {uu:>10.3f}"
              f" {rr/uu if uu else float('inf'):>7.2f} {st.median(R):>9.3f} {st.median(U):>9.3f}")

if __name__ == "__main__":
    main(sys.argv[1:])
