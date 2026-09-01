"""How much of the fused-cluster branch is a LOSS, and how much is the locator
doing its job?

`probe_clef_rejection.py` says 52.9% of orchestral header cells die on "cluster
too big" — by a wide margin the largest branch. That number is easy to read as
"half the coverage is stuck behind one bug", and it is not, because it is a
share of ALL header cells and most orchestral staves are treble or bass. A G
clef is about seven staff spaces tall; refusing it is the branch working.

So this asks the only question that matters before touching it: of the staves
that actually CARRY a C clef, how many are lost there? It reads the hand-read
orchestral pages — the ones with a clef per staff — and cross-tabulates the
branch each staff dies on against whether that staff is really a C clef.

    python3 benchmarks/omr-clef-geometry/probe_cluster_too_big.py
    python3 benchmarks/omr-clef-geometry/probe_cluster_too_big.py --per-staff

Orchestral pages only. A keyboard page is skipped even where the ground truth
has one, because this reader is for conductor's scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.clef_locator import locate_clef  # noqa: E402
from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines,
    extract_measures,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402

C_CLEFS = {"soprano", "mezzosoprano", "alto", "tenor", "baritone"}
# Keyboard pages in the shared ground truth, skipped on purpose.
SKIP_IDS = {"wtc-p17"}


def orchestral_pages() -> list[dict]:
    """Every hand-read page carrying one clef per staff, from wherever it
    lives. Each returns as {id, pdf, page_index, dpi, clefs}."""
    out: list[dict] = []

    shared = REPO / "benchmarks" / "omr-key-signature" / "ground_truth.json"
    if shared.exists():
        for page in json.loads(shared.read_text()).get("pages", []):
            if page["id"] in SKIP_IDS or not all("clef" in s for s in page["staves"]):
                continue
            out.append({"id": page["id"], "pdf": page["pdf"],
                        "page_index": page["page_index"], "dpi": page.get("dpi", 300),
                        "clefs": [s["clef"] for s in page["staves"]]})

    join = (REPO / "benchmarks" / "omr-part-staff-join-2026-08"
            / "ground-truth-beet5-p48.json")
    if join.exists():
        g = json.loads(join.read_text())
        if all("clef" in s for s in g["slots"]):
            out.append({"id": g["id"], "pdf": g["pdf"], "page_index": g["page_index"],
                        "dpi": g.get("dpi", 300),
                        "clefs": [s["clef"] for s in g["slots"]]})

    mahler = HERE / "ground-truth-mahler5-p72.json"
    if mahler.exists():
        g = json.loads(mahler.read_text())
        out.append({"id": g["id"], "pdf": g["pdf"], "page_index": g["page_index"],
                    "dpi": g.get("dpi", 300),
                    "clefs": [s["clef"] for s in g["staves"]]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--per-staff", action="store_true")
    args = ap.parse_args()

    # branch -> {"C": n, "not C": n}
    table: dict[str, Counter] = defaultdict(Counter)
    lost: list[tuple[str, int, str, float, float]] = []
    n_pages = 0
    for page in orchestral_pages():
        pdf = Path(page["pdf"]).expanduser()
        if not pdf.is_absolute():
            pdf = REPO / page["pdf"]
        if not pdf.exists():
            print(f"  {page['id']}: skipped, no PDF at {pdf}")
            continue
        rendered = render_page(pdf, page["page_index"], dpi=page["dpi"])
        pws = detect_barlines(detect_staves(rendered))
        remove_staff_lines(resegment_fused_measures(pws, extract_measures(pws)))
        cells = header_cells_for_page(pws)
        n_pages += 1
        by_system: dict[int, list] = defaultdict(list)
        for staff in sorted(pws.staves, key=lambda s: s.top_y):
            by_system[staff.system_index].append(staff)
        for staves in by_system.values():
            for ordinal, staff in enumerate(staves):
                if ordinal >= len(page["clefs"]):
                    continue
                truth = page["clefs"][ordinal]
                cell = cells.get(staff.staff_index)
                if cell is None:
                    continue
                trace: dict = {}
                found = locate_clef(cell, trace=trace)
                branch = ("located" if found is not None
                          else trace.get("reason", "unknown"))
                group = "C" if truth in C_CLEFS else "not C"
                table[branch][group] += 1
                if branch == "too_big" and group == "C":
                    lost.append((page["id"], staff.staff_index, truth,
                                 trace.get("w_spaces", 0.0),
                                 trace.get("h_spaces", 0.0)))
                if args.per_staff:
                    print(f"    {page['id']:<12} s{staff.staff_index:<3} "
                          f"truth={truth:<8} {branch}")

    print(f"\n{n_pages} hand-read orchestral pages, one clef per staff\n")
    print(f"  {'branch':<28} {'C clef':>7} {'not a C clef':>13}")
    total_c = sum(c["C"] for c in table.values())
    for branch, counts in sorted(table.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {branch:<28} {counts['C']:>7} {counts['not C']:>13}")
    print(f"  {'TOTAL':<28} {total_c:>7} "
          f"{sum(c['not C'] for c in table.values()):>13}")

    if lost:
        print(f"\n  C clefs lost to the fused cluster ({len(lost)} of {total_c}):")
        for page_id, staff_index, truth, w, h in lost:
            print(f"    {page_id:<12} s{staff_index:<3} {truth:<8} "
                  f"cluster {w:.2f} x {h:.2f} spaces")
        hs = [h for *_x, h in lost]
        print(f"    heights: median {np.median(hs):.2f}  range "
              f"[{min(hs):.2f}, {max(hs):.2f}]")
    else:
        print("\n  NO C clef is lost to the fused cluster on these pages.")
    print("\nRead the two columns together. A branch that turns away non-C staves "
          "is\nthe locator working; only the left column is a cost.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
