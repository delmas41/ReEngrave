"""STRUCTURAL: can a measure cell EVER contain two staves' outer lines?

The cell reaches 4.0 staff spaces beyond each outer line
(`measure_extractor.PAD_ABOVE_STAFF_LINES`), measured independently in the
arm as the `too TALL` bucket's median end offsets (-4.00 / +4.00). So the
question is whether the NEXT staff's top line is ever within 4.0 spaces of
this staff's bottom line. Read off the two shared records' own
`Q.STAFF_LINES`. No re-cut, no detector.
"""
import sys, collections, statistics
sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-ledger-extrapolation-2026-09")
from recordstream import stream_array

PAD = 4.0
for rec, label in (("library/_shared-records/beethoven5-p1-p4.record.json", "Litolff"),
                   ("library/_shared-records/brahms1-breitkopf-p0-p3.record.json", "Breitkopf")):
    lines, sp = {}, {}
    for o in stream_array(rec, "observations"):
        q = o.get("quantity")
        if q == "staff_lines" and isinstance(o.get("value"), list):
            lines[o["subject"]] = sorted(float(x) for x in o["value"])
        elif q == "staff_spacing":
            try: sp[o["subject"]] = float(o["value"])
            except Exception: pass
    by_page = collections.defaultdict(list)
    for k, v in lines.items():
        by_page[k.split("/")[1]].append((min(v), max(v), sp.get(k)))
    gaps, reachable = [], 0
    for pg, st in by_page.items():
        st.sort()
        for i in range(len(st) - 1):
            bot, nxt, s = st[i][1], st[i + 1][0], st[i][2]
            if not s: continue
            g = (nxt - bot) / s
            gaps.append(g)
            if g <= PAD: reachable += 1
    print(f"{label}: {len(gaps)} adjacent staff pairs; "
          f"gap in staff spaces min {min(gaps):.2f} "
          f"median {statistics.median(gaps):.2f} max {max(gaps):.2f}")
    print(f"  pairs where the NEXT staff's top line is within the cell's "
          f"{PAD}-space reach: {reachable} of {len(gaps)}")
