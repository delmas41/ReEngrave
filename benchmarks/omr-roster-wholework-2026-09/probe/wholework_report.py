"""Whole-document roster report.

Everything here is derived from the run's own JSON — no external truth — so the
two arms are directly comparable and an empty join is impossible to mistake for
a clean result (see the INPUT ASSERTION block, which refuses on zero staves).

Sections
  1. ACQUISITION   which page/system the roster came off, at what cost
  2. SHAPE         reference size vs the largest system in the document.
                   `slots.align` deletes on the reference side only, so a system
                   with MORE staves than the reference loses its TOP staves and
                   every staff below takes the slot of the staff above. The
                   count of `slot is None` staves is that failure, page by page.
  3. IDENTITY      coverage and provenance per page
  4. MOVEMENTS     staff-count runs — an instrumentation change shows as a step
"""
import json
import sys
import collections
from pathlib import Path


def systems(r):
    for page in r.get("pages", []):
        for sy in page.get("systems", []):
            sts = sorted(sy.get("staves", []),
                         key=lambda s: s.get("staff_geometry", {})
                         .get("line_ys_page", [0])[0])
            yield page.get("page_index"), sy.get("system_index"), sts


def main(path):
    r = json.load(open(path))
    ctx = r.get("contextual") or {}
    sysrows = list(systems(r))
    n_staff = sum(len(s) for _, _, s in sysrows)
    print(f"=== {Path(path).name}")
    print(f"INPUT ASSERTION: pages={len(r.get('pages', []))} "
          f"systems={len(sysrows)} staff-records={n_staff}")
    if n_staff == 0:
        print("REFUSING: no staff records")
        return
    print(f"contextual available={ctx.get('available')} reason={ctx.get('reason')!r}")

    # ---- 1. acquisition ----
    ros = ctx.get("roster")
    print()
    print("## 1. ACQUISITION")
    if not ros:
        print("  NO ROSTER")
    else:
        print(f"  acquired from PDF page index {ros['page_index']}, system "
              f"{ros['system_index']}  ({ros['named']}/{ros['n_staves']} named, "
              f"coverage {ros['coverage']})")
        print(f"  pages_searched (free, already in the run) : {ros['pages_searched']}")
        print(f"  pages_opened   (paid, rendered for this)  : {ros['pages_opened']}")
        print(f"  label tiers                               : {ros['label_tiers']}")
        for e in ros["entries"]:
            print(f"     ord {e['ordinal']:3d}  {e['instrument']:24s} <- {e['text']!r}")

    # ---- 2. shape ----
    ref = ctx.get("reference") or []
    sizes = collections.Counter(len(s) for _, _, s in sysrows)
    print()
    print("## 2. SHAPE — reference vs the document")
    print(f"  reference slots : {len(ref)}")
    print(f"  reference names : " +
          ", ".join((s.get('instrument') or '-') for s in ref))
    print(f"  system sizes    : " +
          ", ".join(f"{k}x{v}" for k, v in sorted(sizes.items())))
    over = [(p, s, len(st)) for p, s, st in sysrows if len(st) > len(ref)]
    lost = sum(len(st) - len(ref) for _, _, st in sysrows if len(st) > len(ref))
    print(f"  systems LARGER than the reference: {len(over)} of {len(sysrows)}")
    print(f"  staves that can get no slot at all (top-dropped): {lost}")
    unslotted = [(p, s, sum(1 for x in st if x.get('slot_index') in (None, -1)))
                 for p, s, st in sysrows]
    tot_unslotted = sum(n for _, _, n in unslotted)
    print(f"  staves observed with slot None/-1              : {tot_unslotted}")

    # ---- 3. identity ----
    print()
    print("## 3. IDENTITY per page")
    per = collections.defaultdict(collections.Counter)
    cnt = collections.Counter()
    for p, s, st in sysrows:
        for x in st:
            cnt[p] += 1
            per[p][x.get("instrument_source") or "none"] += 1
    print(f"{'pg':>4} {'staves':>7} {'label':>6} {'roster':>7} {'order':>6} "
          f"{'ambig':>6} {'none':>5} {'cov':>6}")
    for p in sorted(cnt):
        c = per[p]
        n = cnt[p]
        print(f"{p:4} {n:7} {c['label']:6} {c['roster']:7} {c['score_order']:6} "
              f"{c['score_order_ambiguity']:6} {c['none']:5} {(n-c['none'])/n:6.3f}")
    tot = sum(cnt.values())
    allc = collections.Counter()
    for c in per.values():
        allc.update(c)
    print(f"  TOTAL staves {tot}: " +
          ", ".join(f"{k}={v}" for k, v in sorted(allc.items())) +
          f"   coverage={(tot-allc['none'])/tot:.4f}")

    # ---- 4. movements ----
    print()
    print("## 4. STAFF-COUNT PROFILE (an instrumentation change is a step)")
    prof = []
    for p, s, st in sysrows:
        prof.append((p, len(st)))
    line = []
    prev = None
    for p, n in prof:
        line.append(f"{n}" if n == prev else f"|p{p}:{n}")
        prev = n
    print("  " + " ".join(line))

    # ---- 5. slot occupancy per distinct system size ----
    print()
    print("## 5. WHAT EACH SYSTEM SIZE IS NAMED (first system of each size)")
    seen = set()
    for p, s, st in sysrows:
        k = len(st)
        if k in seen:
            continue
        seen.add(k)
        names = [(x.get("instrument") or "-") for x in st]
        srcs = [(x.get("instrument_source") or "-")[:3] for x in st]
        print(f"  size {k:2d} (first at p{p}.s{s}): " + " | ".join(names))
        print(f"                        src: " + " | ".join(srcs))


if __name__ == "__main__":
    for a in sys.argv[1:]:
        main(a)
        print()
