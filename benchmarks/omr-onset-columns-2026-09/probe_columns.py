"""Do the staves of one system agree where the notes are?

⚠️ MEASURE THE POPULATION BEFORE CHOOSING A CONSTANT. Every constant in this
repo that survived was read off a gap in a measured distribution; every one
that was tuned to a score got refused later. So this asks only what the ink
does, on real pages, before any rule exists.

Reads a committed LEGACY transcription (page pixels are on every detection as
`bbox_page`) because a cloud container has no weights and the staged record
does not yet carry a notehead's page x at all -- which is itself the finding.
"""
import json, sys, statistics as st
from collections import defaultdict

def cells(page):
    for si, sysd in enumerate(page.get("systems", [])):
        yield si, sysd.get("staves", [])

def event_xs(measure, tol_frac=0.6):
    """Within-staff chord grouping, page pixels: the same rule adjudicate_event
    applies in canonical coords."""
    heads = [d for d in measure.get("detections", [])
             if d.get("category") in ("notehead", "rest") and d.get("bbox_page")]
    if not heads:
        return []
    xs = sorted(((d["bbox_page"][0] + d["bbox_page"][2] / 2.0), i, d)
                for i, d in enumerate(heads))
    widths = [d["bbox_page"][2] for _, _, d in xs if d.get("category") == "notehead"]
    tol = (sum(widths) / len(widths) * tol_frac) if widths else 30.0
    groups = []
    for x, _, d in xs:
        if groups and abs(x - groups[-1][-1]) <= tol:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [sum(g) / len(g) for g in groups]

def main(path):
    doc = json.load(open(path))
    print(f"=== {path} ===")
    for pi, page in enumerate(doc.get("pages", [])):
        for si, staves in cells(page):
            # events per (measure_index, staff)
            per_measure = defaultdict(dict)
            staff_y = {}
            for sti, staff in enumerate(staves):
                ys = staff.get("line_ys") or []
                staff_y[sti] = (sum(ys) / len(ys)) if ys else None
                for m in staff.get("measures", []):
                    xs = event_xs(m)
                    if xs:
                        per_measure[m.get("measure_index")][sti] = xs
            if not per_measure:
                continue
            print(f"\n-- page {pi} system {si}: {len(staves)} staves, "
                  f"{len(per_measure)} measures with events --")
            for mi in sorted(per_measure)[:4]:
                by_staff = per_measure[mi]
                allx = sorted(x for xs in by_staff.values() for x in xs)
                if len(by_staff) < 2:
                    continue
                # single-link cluster the pooled xs, then report spread
                clusters, cur = [], [allx[0]]
                for x in allx[1:]:
                    if x - cur[-1] <= 40:      # deliberately loose, just to see
                        cur.append(x)
                    else:
                        clusters.append(cur); cur = [x]
                clusters.append(cur)
                multi = [c for c in clusters if len(c) >= 2]
                spreads = [max(c) - min(c) for c in multi]
                print(f"   m{mi}: staves_with_events={len(by_staff):2d} "
                      f"events={len(allx):3d} clusters={len(clusters):3d} "
                      f"multi={len(multi):3d} "
                      f"spread med={st.median(spreads) if spreads else 0:.1f}px "
                      f"max={max(spreads) if spreads else 0:.1f}px")

if __name__ == "__main__":
    main(sys.argv[1])
