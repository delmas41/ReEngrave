"""Per-staff identity audit of a whole-work transcription.

The load-bearing check needs NO image and no truth file: on the page the
roster was READ from, each staff's own raw margin text is in the JSON beside
the instrument the layer assigned it.  If the text says `Corni` and the
assignment says `Trumpet`, the ordinal join slipped — and it slipped on the
one page where the evidence is strongest.

Usage:  audit_identity.py OUT.json [--pages 1,2,3]
"""
import json
import sys
import collections
from pathlib import Path

from tools.omr.instruments import lookup


def rows(r):
    for page in r.get("pages", []):
        pi = page.get("page_index")
        for sysm in page.get("systems", []):
            si = sysm.get("system_index")
            sts = sorted(sysm.get("staves", []),
                         key=lambda s: s.get("staff_geometry", {})
                         .get("line_ys_page", [0])[0])
            for ordinal, st in enumerate(sts):
                yield pi, si, ordinal, st


def canon(text):
    """What the lexicon makes of a raw margin string, or None."""
    if not text:
        return None
    m = lookup(text)
    return m.instrument.name if m else None


def main(path):
    r = json.load(open(path))
    ctx = r.get("contextual") or {}
    ros = ctx.get("roster")
    print(f"=== {Path(path).name}")
    n_pages = len(r.get("pages", []))
    allrows = list(rows(r))
    print(f"INPUT ASSERTION: pages={n_pages} systems="
          f"{len({(a,b) for a,b,_,_ in allrows})} staff-records={len(allrows)}")
    if not allrows:
        print("REFUSING: no staff records — nothing to audit")
        return
    if ros:
        print(f"roster: page {ros['page_index']} system {ros['system_index']} "
              f"{ros['named']}/{ros['n_staves']} pages_searched={ros['pages_searched']} "
              f"pages_opened={ros['pages_opened']}")
    else:
        print("roster: NONE")

    # ---- check A: staff's OWN label vs assigned instrument ----
    print()
    print("## A. self-contradiction (staff carries a label that disagrees)")
    bad = 0
    seen = 0
    for pi, si, ordinal, st in allrows:
        raw = st.get("instrument_label")
        got = st.get("instrument")
        c = canon(raw)
        if c is None or got is None:
            continue
        seen += 1
        if c != got:
            bad += 1
            print(f"  p{pi} s{si} ord{ordinal:3d}  label={raw!r:28s} "
                  f"lexicon={c:16s} assigned={got:16s} src={st.get('instrument_source')}")
    print(f"  checked {seen} labelled staves, {bad} disagree")

    # ---- check B: provenance + coverage by page ----
    print()
    print("## B. coverage and provenance by page")
    per_page = collections.defaultdict(collections.Counter)
    staves_pp = collections.Counter()
    for pi, si, ordinal, st in allrows:
        staves_pp[pi] += 1
        per_page[pi][st.get("instrument_source") or "none"] += 1
    print(f"{'pg':>4} {'staves':>7} {'label':>6} {'roster':>7} {'order':>6} "
          f"{'ambig':>6} {'none':>5} {'cov':>6}")
    for pi in sorted(staves_pp):
        c = per_page[pi]
        n = staves_pp[pi]
        named = n - c["none"]
        print(f"{pi:4} {n:7} {c['label']:6} {c['roster']:7} {c['score_order']:6} "
              f"{c['score_order_ambiguity']:6} {c['none']:5} {named/n:6.3f}")

    # ---- check C: staff-count profile (instrumentation changes) ----
    print()
    print("## C. per-system staff counts (an instrumentation change shows here)")
    prof = [(pi, si, sum(1 for a, b, _, _ in allrows if a == pi and b == si))
            for pi, si in sorted({(a, b) for a, b, _, _ in allrows})]
    print("  " + " ".join(f"{pi}.{si}:{n}" for pi, si, n in prof))

    # ---- check D: the assigned name-set per page ----
    print()
    print("## D. assigned instrument sequence per page (top to bottom)")
    for pi in sorted(staves_pp):
        for si in sorted({b for a, b, _, _ in allrows if a == pi}):
            names = [st.get("instrument") or "-"
                     for a, b, _, st in allrows if a == pi and b == si]
            labs = [st.get("instrument_label") or ""
                    for a, b, _, st in allrows if a == pi and b == si]
            print(f"  p{pi}.s{si} ({len(names)}): " + " | ".join(names))
            if any(labs):
                print(f"        labels: " + " | ".join(l or "·" for l in labs))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
        print()
