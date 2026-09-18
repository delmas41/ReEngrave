"""WHICH BARLINES RUN A SYSTEM'S FULL HEIGHT? Measured off the raster.

Sean, 2026-09-17: *"A barline goes all the way through a system at the
beginning and end of the system but not necessarily in the other bars in the
system."*

CLAUDE.md:4897 says, as the justification for a LIVE rule: *"A barline runs a
system's full height and the bracket encloses exactly it, so a column inked
through the whole gap VETOES a gap-based break."* The bracket half is already
recorded as an error in
`benchmarks/omr-system-grouping-2026-09/research/publisher-conventions.md`.
This asks whether the BARLINE half survives, because the veto rests on it.

THE CONVENTION AS SEAN STATES IT, in the form a reader can test: a barline's
height is a function of WHERE IN THE SYSTEM IT STANDS. The systemic barline
at the left edge joins every staff; interior barlines are continuous within an
instrument FAMILY and broken between families (MOLA: *"barlines continuous
within each family of instruments"*); the final barline closes the system.

METHOD. For each system take the inter-staff GAPS — between one staff's
bottom printed line and the next staff's top printed line. A barline candidate
is an x-column carrying ink through the body of at least half the staves. For
each candidate count how many of the system's gaps it crosses. Then split the
candidates by position: FIRST (leftmost), LAST (rightmost), INTERIOR.

⚠️ THE CONTROL. The staff BODIES are where every barline must be inked, so a
column that does not cross the staves is not a barline and is dropped before
anything is counted. And the probe prints, for every system, how many
candidates it found: a system yielding none is reported, not silently skipped.
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

import fitz
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "benchmarks"
                       / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402

DPI, INK = 600, 128
BODY_FRAC = 0.75     # ink must fill this much of a staff's own height
GAP_FRAC = 0.75      # and this much of a gap, to count as crossing it
# ⚠️ A BARLINE INKS EVERY STAFF BODY. This is the convention doing the
# filtering, and it is what separates a barline from a column of aligned
# stems: an interior barline is drawn in EVERY instrument family, so it
# crosses all five lines of all staves and skips only the gaps BETWEEN
# families. A stem column in a rhythm-unison tutti inks some staves and not
# others. A first cut required only half the bodies and reported 18-33
# "barlines" on systems that print at most nine bars -- the interior
# population was mostly stems, which biases the crossing rate DOWNWARD, i.e.
# toward the conclusion. Tightened to every staff.
ALL_BODIES = 1.00


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    staves: dict[tuple, list] = {}
    for o in stream_array(a.record, "observations"):
        if o.get("quantity") != "staff_lines" or not isinstance(o.get("value"), list):
            continue
        p = o["subject"].split("/")
        if len(p) != 4:
            continue
        staves[(int(p[1]), int(p[2]), int(p[3]))] = sorted(
            float(x) for x in o["value"])
    systems: dict[tuple, list] = collections.defaultdict(list)
    for (pg, sy, st), L in staves.items():
        systems[(pg, sy)].append((st, L))
    print(f"{a.label}: {len(staves)} staves in {len(systems)} systems")

    doc = fitz.open(a.pdf)
    pages: dict[int, np.ndarray] = {}
    rows = []
    for (pg, sy), members in sorted(systems.items()):
        members.sort(key=lambda m: m[1][0])
        if len(members) < 3:
            continue                      # a gap table needs several staves
        if pg not in pages:
            pm = doc[pg].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
            pages[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        img = pages[pg]
        bodies = [(L[0], L[4]) for _, L in members]
        gaps = [(bodies[i][1], bodies[i + 1][0])
                for i in range(len(bodies) - 1)]
        gaps = [(t, b) for t, b in gaps if b - t > 2]
        if not gaps:
            continue
        top, bot = bodies[0][0], bodies[-1][1]
        dark = img[int(top):int(bot) + 1, :] < INK
        # a candidate must ink the BODY of at least half the staves
        ok = np.ones(img.shape[1], dtype=bool)
        hit = np.zeros(img.shape[1], dtype=int)
        for t, b in bodies:
            col = dark[int(t - top):int(b - top) + 1, :].mean(axis=0)
            hit += (col >= BODY_FRAC)
        cand = np.where(hit >= int(len(bodies) * ALL_BODIES))[0]
        if cand.size == 0:
            print(f"   page {pg} system {sy}: NO barline candidate "
                  f"({len(members)} staves)")
            continue
        # group adjacent columns into one barline
        groups, run = [], [cand[0]]
        for x in cand[1:]:
            if x - run[-1] <= 3:
                run.append(x)
            else:
                groups.append(run)
                run = [x]
        groups.append(run)
        xs = [int(statistics.fmean(g)) for g in groups]
        crossed = []
        for x in xs:
            n = 0
            for t, b in gaps:
                seg = dark[int(t - top):int(b - top) + 1,
                           max(0, x - 1):x + 2]
                if seg.size and seg.mean(axis=1).mean() >= GAP_FRAC:
                    n += 1
            crossed.append(n)
        for i, (x, n) in enumerate(zip(xs, crossed)):
            where = ("FIRST" if i == 0 else
                     "LAST" if i == len(xs) - 1 else "interior")
            rows.append({"page": pg, "system": sy, "where": where,
                         "x": x, "gaps_crossed": n, "gaps": len(gaps)})
        print(f"   page {pg} system {sy}: {len(members)} staves, "
              f"{len(gaps)} gaps, {len(xs)} barlines, crossings {crossed}")

    if not rows:
        print("DEAD: no barline found anywhere", file=sys.stderr)
        return 2

    print(f"\n== does a barline cross EVERY inter-staff gap of its system?")
    print(f"{'position':<10} {'n':>5} {'crosses ALL':>12} {'crosses NONE':>13} "
          f"{'median share':>13}")
    out = {"label": a.label, "barlines": len(rows), "by_position": {}}
    for where in ("FIRST", "interior", "LAST"):
        v = [r for r in rows if r["where"] == where]
        if not v:
            continue
        allg = sum(1 for r in v if r["gaps_crossed"] == r["gaps"])
        none = sum(1 for r in v if r["gaps_crossed"] == 0)
        share = statistics.median(r["gaps_crossed"] / r["gaps"] for r in v)
        out["by_position"][where] = {"n": len(v), "crosses_all": allg,
                                     "crosses_none": none,
                                     "median_share": round(share, 3)}
        print(f"{where:<10} {len(v):>5} {allg:>7} {allg/len(v):>5.0%} "
              f"{none:>8} {none/len(v):>5.0%} {share:>13.2f}")
    Path(a.json).write_text(json.dumps({**out, "rows": rows}, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
