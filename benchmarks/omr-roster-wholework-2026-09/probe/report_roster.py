"""Read a whole-work transcription and report the roster's behaviour.

Answers, per run:
  1. acquisition — which page, which system, coverage, what it named
  2. identity per staff across the document — provenance mix by page
  3. staff-count profile per page (the instrumentation-change signal)
"""
import json
import sys
import collections
from pathlib import Path


def load(p):
    return json.load(open(p))


def staves_of(page):
    for sysm in page.get("systems", []):
        for st in sysm.get("staves", []):
            yield sysm, st


def main(path):
    r = load(path)
    ctx = r.get("contextual") or {}
    ros = ctx.get("roster")
    print(f"### {Path(path).name}")
    print(f"pages transcribed: {len(r.get('pages', []))}")
    print(f"contextual reason: {ctx.get('reason')!r}")
    print()
    print("## 1. ACQUISITION")
    if not ros:
        print("  NO ROSTER ACQUIRED")
    else:
        print(f"  page_index      : {ros['page_index']}")
        print(f"  system_index    : {ros['system_index']}")
        print(f"  n_staves        : {ros['n_staves']}")
        print(f"  named           : {ros['named']}  coverage={ros['coverage']}")
        print(f"  pages_searched  : {ros['pages_searched']}")
        print(f"  pages_opened    : {ros['pages_opened']}")
        print(f"  label tiers     : {ros['label_tiers']}")
        for e in ros["entries"]:
            print(f"    {e['ordinal']:3d}  {e['instrument']:22s} <- {e['text']!r} ({e['confidence']})")
    print()

    print("## 2. SLOT IDENTITY (document-level)")
    slots = ctx.get("slots") or ctx.get("reference") or []
    src = ctx.get("instrument_source") or {}
    if isinstance(slots, list) and slots:
        print(f"  reference slots: {len(slots)}")
    for k in sorted(ctx):
        if k in ("roster", "slots", "reference"):
            continue
        v = ctx[k]
        if isinstance(v, (int, float, str, bool)) or v is None:
            print(f"  {k}: {v}")
    print()

    print("## 3. PER-PAGE STAFF PROFILE + IDENTITY PROVENANCE")
    hdr = f"{'pg':>4} {'sys':>4} {'staves':>7} {'named':>6} " \
          f"{'label':>6} {'roster':>7} {'order':>6} {'none':>5}  instruments"
    print(hdr)
    rows = []
    for page in r.get("pages", []):
        pi = page.get("page_index")
        for sysm in page.get("systems", []):
            sts = sysm.get("staves", [])
            prov = collections.Counter()
            names = []
            for st in sts:
                s = st.get("instrument_source")
                prov[s if s else "none"] += 1
                names.append(st.get("instrument") or "?")
            rows.append((pi, sysm.get("system_index"), len(sts), prov, names))
    for pi, si, n, prov, names in rows:
        named = n - prov["none"]
        print(f"{pi:4} {si:4} {n:7} {named:6} {prov['label']:6} {prov['roster']:7} "
              f"{prov['score_order'] + prov['score_order_ambiguity']:6} {prov['none']:5}  "
              + ",".join(names))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
        print()
