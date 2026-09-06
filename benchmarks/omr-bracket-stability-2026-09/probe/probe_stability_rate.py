"""How often does bracket-group structure disagree with itself?

Two measures, deliberately different in how much they assume:

WITHIN-PAGE (the strong one, almost confound-free).  Two systems printed on the
SAME page with the SAME staff count are the same printed lineup essentially
always — a page turn does not change which instruments are tacet in the middle
of a page.  So any disagreement between their `group_index` vectors is the
detector disagreeing with itself about ink it read twice.

WITHIN-EDITION (the weak one, an UPPER bound).  Systems of equal staff count
across the pages of one edition are USUALLY the same lineup, but need not be:
a printed score suppresses tacet staves, and two different subsets can happen
to have the same count.  Reported separately and never pooled with the first.

Model-free: `_assign_groups` needs the binary page and the staves only.

Usage:
    probe_stability_rate.py --corpus scan  [--pages-per-edition 20] [--dpi 600]
    probe_stability_rate.py PDF... --pages=0-40
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.preprocessing import render_page          # noqa: E402
from tools.omr.staff_detector import detect_staves       # noqa: E402
from tools.omr.system_grouping import (                  # noqa: E402
    gap_bridging_counts, GROUP_BOUNDARY_RATIO)

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
WORKS = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
             "omr-scan-e2e-2026-09/works.json")


def scan_editions() -> list[tuple[str, Path]]:
    rows = json.loads(WORKS.read_text())["rows"]
    seen: dict[str, Path] = {}
    for r in rows:
        cp = r["edition"]["catalog_path"]
        seen.setdefault(cp, LIB / cp)
    return sorted(seen.items())


def page_systems(pdf: str, page_index: int, dpi: int) -> list[dict]:
    """Per system on the page: staff count, group vector, gap evidence."""
    pi = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(pi)
    staves = sorted(pws.staves, key=lambda s: s.top_y)
    bridging = gap_bridging_counts(pi.binary, staves)
    by_system: dict[int, list[int]] = {}
    for i, s in enumerate(staves):
        by_system.setdefault(s.system_index, []).append(i)
    out = []
    for sys_idx in sorted(by_system):
        members = by_system[sys_idx]
        inner = [bridging[i] for i in members[:-1] if bridging[i] >= 0]
        median = statistics.median(inner) if inner else None
        out.append({
            "system_index": sys_idx,
            "n_staves": len(members),
            "groups": [staves[i].group_index for i in members],
            "n_groups": len({staves[i].group_index for i in members}),
            "inner_bridging": [bridging[i] for i in members[:-1]],
            "median": median,
            "ratios": ([round(bridging[i] / median, 4) if median else None
                        for i in members[:-1]] if median else None),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="*")
    ap.add_argument("--corpus", choices=["scan"], default=None)
    ap.add_argument("--pages", default=None)
    ap.add_argument("--pages-per-edition", type=int, default=24)
    ap.add_argument("--first-page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    targets: list[tuple[str, Path, list[int]]] = []
    if args.corpus == "scan":
        import fitz
        for name, path in scan_editions():
            n = fitz.open(path).page_count
            last = min(n - 1, args.first_page + args.pages_per_edition - 1)
            targets.append((name, path, list(range(args.first_page, last + 1))))
    for p in args.pdfs:
        pages: list[int] = []
        for tok in (args.pages or "0").split(","):
            if "-" in tok:
                a, b = tok.split("-")
                pages.extend(range(int(a), int(b) + 1))
            else:
                pages.append(int(tok))
        targets.append((Path(p).name, Path(p), pages))

    records = []
    t0 = time.time()
    for name, path, pages in targets:
        for p in pages:
            try:
                systems = page_systems(str(path), p, args.dpi)
            except Exception as exc:                      # noqa: BLE001
                print(f"  !! {name} p{p}: {type(exc).__name__}: {exc}")
                continue
            records.append({"edition": name, "page": p, "systems": systems})
            print(f"  {name} p{p}: "
                  + " | ".join(f"{s['n_staves']}st {s['n_groups']}g "
                               f"{''.join(map(str, s['groups']))}"
                               for s in systems), flush=True)
    print(f"\n{len(records)} pages in {time.time() - t0:.0f}s")

    # ── within-page ─────────────────────────────────────────────────────────
    wp_pairs = wp_disagree = 0
    wp_detail = []
    for rec in records:
        by_count: dict[int, list[dict]] = defaultdict(list)
        for s in rec["systems"]:
            by_count[s["n_staves"]].append(s)
        for count, group in by_count.items():
            if count < 3 or len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    wp_pairs += 1
                    if group[i]["groups"] != group[j]["groups"]:
                        wp_disagree += 1
                        wp_detail.append({
                            "edition": rec["edition"], "page": rec["page"],
                            "n_staves": count,
                            "a": group[i], "b": group[j],
                        })

    # ── within-edition, bucketed by staff count ─────────────────────────────
    we = []
    buckets: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for rec in records:
        for s in rec["systems"]:
            if s["n_staves"] >= 3:
                buckets[(rec["edition"], s["n_staves"])].append(
                    {**s, "page": rec["page"]})
    for (edition, count), group in sorted(buckets.items()):
        if len(group) < 3:
            continue
        vecs = Counter(tuple(s["groups"]) for s in group)
        modal, modal_n = vecs.most_common(1)[0]
        we.append({
            "edition": edition, "n_staves": count, "n_systems": len(group),
            "n_distinct_vectors": len(vecs),
            "modal_share": round(modal_n / len(group), 3),
            "modal": list(modal),
            "vectors": {"".join(map(str, k)): v for k, v in vecs.most_common()},
        })

    summary = {
        "within_page": {
            "pairs": wp_pairs, "disagreeing": wp_disagree,
            "rate": round(wp_disagree / wp_pairs, 4) if wp_pairs else None,
        },
        "within_edition": we,
    }
    print("\nWITHIN-PAGE  pairs=%d  disagreeing=%d  rate=%s"
          % (wp_pairs, wp_disagree, summary["within_page"]["rate"]))
    for b in we:
        print(f"WITHIN-EDITION {b['edition'][:48]:48s} {b['n_staves']:2d}st "
              f"n={b['n_systems']:2d} distinct={b['n_distinct_vectors']} "
              f"modal_share={b['modal_share']}")

    Path(args.out).write_text(json.dumps(
        {"summary": summary, "within_page_detail": wp_detail,
         "records": records}, indent=1))


if __name__ == "__main__":
    main()
