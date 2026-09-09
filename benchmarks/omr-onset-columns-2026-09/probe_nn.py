"""How far is a staff's event from the nearest event in ANOTHER staff?

⚠️ THE QUESTION IS THE SHAPE OF THE DISTRIBUTION, NOT A THRESHOLD. If
simultaneity is real and readable, this is bimodal: a tight population near
zero (the same instant, printed in a column) and a loose one at musical
distances. If it is unimodal there is no column to read and the idea is dead.

Distances are in STAFF SPACES, never pixels: spacing varies by page, staff and
scan, and a constant in pixels would be a constant about one document.
"""
import json, sys, statistics as st
from collections import defaultdict

TOL_FRAC = 0.6   # within-staff chord grouping, as adjudicate_event uses

def spacing_of(staff):
    """⚠️ `staff_geometry.line_spacing_px` is the PAGE-frame spacing. The
    per-measure `staff_line_ys_canonical` is the cell's rescaled grid and
    would give a different unit per cell -- the same frame trap this whole
    investigation is about."""
    g = staff.get("staff_geometry") or {}
    sp = g.get("line_spacing_px")
    if sp:
        return float(sp)
    ys = g.get("line_ys_page") or []
    if len(ys) >= 2:
        return (ys[-1] - ys[0]) / (len(ys) - 1)
    # ⚠️ Older transcriptions carry no `staff_geometry`. The page spacing is
    # still recoverable: a cell's canonical grid divided by its own
    # `upscale_factor` IS the page spacing, because that factor is exactly the
    # canonical<-page scale. Derived rather than defaulted, so a file without
    # either still abstains instead of contributing a wrong unit.
    for m in staff.get("measures", []):
        cys, up = m.get("staff_line_ys_canonical"), m.get("upscale_factor")
        if cys and len(cys) >= 2 and up:
            return ((cys[-1] - cys[0]) / (len(cys) - 1)) / float(up)
    return None

def events_of(measure):
    dets = [d for d in measure.get("detections", [])
            if d.get("category") in ("notehead", "rest") and d.get("bbox_page")]
    if not dets:
        return []
    xs = sorted(((d["bbox_page"][0] + d["bbox_page"][2] / 2.0), i, d)
                for i, d in enumerate(dets))
    widths = [d["bbox_page"][2] for _, _, d in xs if d.get("category") == "notehead"]
    tol = (sum(widths) / len(widths) * TOL_FRAC) if widths else 30.0
    groups = []
    for x, _, d in xs:
        if groups and abs(x - groups[-1][-1]) <= tol:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [sum(g) / len(g) for g in groups]

def main(paths):
    near, far = [], []
    n_pairs = n_sys = 0
    for path in paths:
        doc = json.load(open(path))
        for page in doc.get("pages", []):
            for sysd in page.get("systems", []):
                staves = sysd.get("staves", [])
                if len(staves) < 2:
                    continue
                n_sys += 1
                sp = [spacing_of(s) for s in staves]
                sp_med = st.median([v for v in sp if v]) if any(sp) else None
                if not sp_med:
                    continue
                per_measure = defaultdict(dict)
                for sti, staff in enumerate(staves):
                    for m in staff.get("measures", []):
                        ev = events_of(m)
                        if ev:
                            per_measure[m.get("measure_index")][sti] = ev
                for mi, by_staff in per_measure.items():
                    if len(by_staff) < 2:
                        continue
                    for sti, xs in by_staff.items():
                        others = [x for o, oxs in by_staff.items() if o != sti
                                  for x in oxs]
                        if not others:
                            continue
                        for x in xs:
                            d = min(abs(x - o) for o in others) / sp_med
                            n_pairs += 1
                            (near if d <= 3.0 else far).append(d)
    allv = sorted(near + far)
    print(f"systems={n_sys}  events={n_pairs}")
    print("\n=== nearest event in ANOTHER staff, in staff spaces ===")
    for q in (0.10, 0.25, 0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99):
        print(f"  p{int(q*100):02d} = {allv[int(q*(len(allv)-1))]:6.3f}")
    print(f"  max  = {allv[-1]:.3f}")
    # where is the emptiest interval in 0..3 spaces? (the gap, if there is one)
    band = [v for v in allv if v <= 3.0]
    best, edges = 0.0, None
    for i in range(len(band) - 1):
        g = band[i+1] - band[i]
        if g > best:
            best, edges = g, (band[i], band[i+1])
    print(f"\n  widest empty interval below 3 spaces: {best:.3f} spaces "
          f"between {edges[0]:.3f} and {edges[1]:.3f}" if edges else "")
    for t in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
        print(f"  share within {t:>4} spaces: {sum(1 for v in allv if v <= t)/len(allv):.3f}")

if __name__ == "__main__":
    main(sys.argv[1:])


def null_control(paths, seed=20260909):
    """⚠️ THE NUMBER ABOVE IS MEANINGLESS WITHOUT THIS.

    With 14 staves pooled, the nearest event in *some* other staff is close by
    DENSITY alone -- a bar holding 160 events over 1200 px has one every 7 px
    whatever the music does. So the same statistic is recomputed against
    x positions RESHUFFLED uniformly inside each staff's own bar span: the
    count, the bar and the range are preserved and only the alignment is
    destroyed. If real and null agree, there is no column to read.
    """
    import random
    rng = random.Random(seed)
    real, null = [], []
    for path in paths:
        doc = json.load(open(path))
        for page in doc.get("pages", []):
            for sysd in page.get("systems", []):
                staves = sysd.get("staves", [])
                if len(staves) < 2:
                    continue
                sp = [spacing_of(s) for s in staves]
                sp = [v for v in sp if v]
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
                    if hi - lo < 1:
                        continue
                    shuf = {s: [rng.uniform(lo, hi) for _ in xs]
                            for s, xs in by_staff.items()}
                    for sti, xs in by_staff.items():
                        o_real = [x for o, ox in by_staff.items() if o != sti for x in ox]
                        o_null = [x for o, ox in shuf.items() if o != sti for x in ox]
                        if not o_real:
                            continue
                        for x in xs:
                            real.append(min(abs(x - o) for o in o_real) / sp_med)
                        for x in shuf[sti]:
                            null.append(min(abs(x - o) for o in o_null) / sp_med)
    real.sort(); null.sort()
    print("\n=== NULL CONTROL: x reshuffled inside each staff's own bar span ===")
    print(f"{'':22}{'REAL':>10}{'NULL':>10}")
    for t in (0.10, 0.25, 0.50, 1.00):
        r = sum(1 for v in real if v <= t) / len(real)
        n = sum(1 for v in null if v <= t) / len(null)
        print(f"  share within {t:<5}     {r:>9.3f}{n:>10.3f}   ratio {r/n if n else float('inf'):.2f}x")
    print(f"  median                {st.median(real):>9.3f}{st.median(null):>10.3f}")

if __name__ == "__main__":
    null_control(sys.argv[1:])
