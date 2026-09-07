"""Bracket READING against the barline-stop INFERENCE, on the same systems.

Both produce a set of boundary gaps within a system.  This runs them side by
side and reports, per publisher:

  * the reader's verdict distribution (reach)
  * where they agree, and where each asserts a boundary the other does not
  * the reader's WITHIN-PAGE self-consistency, the same measure
    `benchmarks/omr-bracket-stability-2026-09` used on the incumbent

The incumbent arm runs under both `OMR_BRACKET_COLUMNS` settings, since the
repair landed today and the flag is default-OFF.

    probe_vs_incumbent.py --corpus scan --pages-per-edition 12 --out out/vs.json
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

from tools.omr.preprocessing import render_page              # noqa: E402
from tools.omr.staff_detector import detect_staves           # noqa: E402
from tools.omr.bracket_reader import read_brackets           # noqa: E402
from tools.omr import system_grouping as sg                  # noqa: E402

LIB = Path("/Users/seanjohnson/Desktop/ReEngrave/library")
WORKS = Path("/Users/seanjohnson/Desktop/ReEngrave/benchmarks/"
             "omr-scan-e2e-2026-09/works.json")


def scan_editions() -> list[tuple[str, Path]]:
    rows = json.loads(WORKS.read_text())["rows"]
    seen: dict[str, Path] = {}
    for r in rows:
        cp = r["edition"]["catalog_path"]
        seen.setdefault(cp.split("/")[1], LIB / cp)
    return sorted(seen.items())


def incumbent_boundaries(binary, members, use_columns: bool) -> list[int]:
    """The gaps `_assign_groups` would split at, for ONE system.

    Reimplemented over this system's own staves rather than calling
    `_assign_groups` (which needs the page's global gap indexing) — same
    arithmetic, same constants, read from the module so it cannot drift.
    """
    if len(members) < 3:
        return []
    runs = sg.gap_crossing_runs(binary, members)
    spacing = statistics.median([s.line_spacing_px for s in members]) or 1.0
    if use_columns:
        evidence = sg.systemic_column_counts(runs, spacing)
    else:
        evidence = [-1 if r is None else sum(w for _c, w in r) for r in runs]
    inner = [e for e in evidence if e >= 0]
    if not inner:
        return []
    if use_columns and statistics.median(inner) < sg.BRACKET_COLUMN_MIN_EVIDENCE:
        return []
    thr = statistics.median(inner) * sg.GROUP_BOUNDARY_RATIO
    return [i for i, e in enumerate(evidence) if 0 <= e < thr]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", choices=["scan"], default="scan")
    ap.add_argument("--pages-per-edition", type=int, default=12)
    ap.add_argument("--first-page", type=int, default=2)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--min-staves", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for tag, pdf in scan_editions():
        for pg in range(args.first_page,
                        args.first_page + args.pages_per_edition):
            t0 = time.time()
            try:
                pi = render_page(str(pdf), pg, dpi=args.dpi)
                staves = sorted(detect_staves(pi).staves, key=lambda s: s.top_y)
            except Exception as exc:                          # noqa: BLE001
                print(f"{tag} p{pg}: FAILED {type(exc).__name__}: {exc}",
                      flush=True)
                continue
            by_sys: dict[int, list] = {}
            for s in staves:
                by_sys.setdefault(s.system_index, []).append(s)
            for si in sorted(by_sys):
                members = by_sys[si]
                if len(members) < args.min_staves:
                    continue
                r = read_brackets(pi.binary, members)
                rows.append({
                    "tag": tag, "page": pg, "system": si,
                    "n_staves": len(members),
                    "verdict": r["verdict"],
                    "blocks": r["blocks"],
                    "bracket_boundaries": r["boundaries"],
                    "bracket_interior": r["interior"],
                    "incumbent_px": incumbent_boundaries(pi.binary, members, False),
                    "incumbent_cols": incumbent_boundaries(pi.binary, members, True),
                })
                b = rows[-1]
                print(f"{tag} p{pg} s{si} n={len(members):2d} "
                      f"{r['verdict']:<13} bracket={b['bracket_boundaries']} "
                      f"px={b['incumbent_px']} cols={b['incumbent_cols']}",
                      flush=True)
            print(f"  [{tag} p{pg} {time.time()-t0:.1f}s]", flush=True)

    Path(args.out).write_text(json.dumps(rows, indent=1))

    # ── summary ──
    per: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        per[r["tag"]].append(r)
    print("\n== verdict distribution (reach) ==")
    print(f"{'publisher':<12} {'systems':>8} {'partial':>8} {'spanning':>9} "
          f"{'no_rule':>8}")
    for pub in sorted(per) + ["TOTAL"]:
        rs = rows if pub == "TOTAL" else per[pub]
        c = Counter(r["verdict"] for r in rs)
        print(f"{pub:<12} {len(rs):>8} {c['partial']:>8} "
              f"{c['spanning_only']:>9} {c['no_rule']:>8}")

    print("\n== agreement on systems where the bracket STATES blocks ==")
    print(f"{'publisher':<12} {'sys':>4} {'both':>6} {'brkt only':>10} "
          f"{'inc only':>9}   (incumbent = OMR_BRACKET_COLUMNS on)")
    for pub in sorted(per) + ["TOTAL"]:
        rs = [r for r in (rows if pub == "TOTAL" else per[pub])
              if r["verdict"] == "partial"]
        both = bonly = ionly = 0
        for r in rs:
            b, i = set(r["bracket_boundaries"]), set(r["incumbent_cols"])
            both += len(b & i)
            bonly += len(b - i)
            ionly += len(i - b)
        print(f"{pub:<12} {len(rs):>4} {both:>6} {bonly:>10} {ionly:>9}")

    print("\n== within-page self-consistency of the bracket reading ==")
    print("(two systems on one page with the same staff count are the same "
          "printed lineup)")
    pairs = agree = 0
    per_pub: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    bykey: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        bykey[(r["tag"], r["page"], r["n_staves"])].append(r)
    for key, group in bykey.items():
        if len(group) < 2:
            continue
        for a, b in zip(group, group[1:]):
            pairs += 1
            per_pub[key[0]][0] += 1
            ok = (a["verdict"] == b["verdict"]
                  and a["bracket_boundaries"] == b["bracket_boundaries"])
            agree += ok
            per_pub[key[0]][1] += ok
    for pub in sorted(per_pub):
        n, ok = per_pub[pub]
        print(f"  {pub:<11} {ok}/{n}" + (f"  {ok/n:.3f}" if n else ""))
    if pairs:
        print(f"  {'TOTAL':<11} {agree}/{pairs}  {agree/pairs:.3f}"
              f"   (disagreement rate {1 - agree/pairs:.3f})")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
