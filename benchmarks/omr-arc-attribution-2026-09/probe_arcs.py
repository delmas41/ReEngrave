"""Inventory every arc detection per staff: how many noteheads it covers in its
OWN staff, and whether the same ink appears as an arc in a NEIGHBOURING staff.

Run from the repo root:

    python3 benchmarks/omr-arc-attribution-2026-09/probe_arcs.py <work>.omr.json
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.export import _measure_noteheads, _SLUR_ARC_PAD_NOTEHEADS  # noqa: E402


def arcs_of(measure, cls=("slur", "tie")):
    return [d for d in measure.get("detections", [])
            if d.get("category") == "structural" and d.get("class") in cls
            and len(d.get("bbox_page") or ()) == 4]


def covered(measure, arc):
    heads = _measure_noteheads(measure)
    if not heads:
        return []
    pad = _SLUR_ARC_PAD_NOTEHEADS * (
        sum(h["bbox_page"][2] for h in heads) / len(heads))
    ax, _, aw, _ = arc["bbox_page"]
    out = []
    for h in heads:
        b = h["bbox_page"]
        xc = b[0] + b[2] / 2.0
        if ax - pad <= xc <= ax + aw + pad:
            out.append(h)
    return out


def ov1(a0, a1, b0, b1):
    lo, hi = max(a0, b0), min(a1, b1)
    return max(0.0, hi - lo) / max(1e-9, min(a1 - a0, b1 - b0))


def iou1d(a, b):
    return (ov1(a[0], a[0] + a[2], b[0], b[0] + b[2]),
            ov1(a[1], a[1] + a[3], b[1], b[1] + b[3]))


def collect(res):
    rows = []
    for page in res["pages"]:
        for sys_i, sys_ in enumerate(page.get("systems", [])):
            staves = sys_.get("staves", [])
            per_staff = []
            for st in staves:
                a = []
                for m in st.get("measures", []):
                    for d in arcs_of(m):
                        a.append((m, d))
                per_staff.append(a)
            for s_i, st in enumerate(staves):
                name = st.get("part_name") or st.get("slot_label") or f"s{s_i}"
                for m, d in per_staff[s_i]:
                    cov = covered(m, d)
                    dups = []
                    for o_i, other in enumerate(per_staff):
                        if o_i == s_i:
                            continue
                        for om, od in other:
                            ox, oy = iou1d(d["bbox_page"], od["bbox_page"])
                            if ox >= 0.7 and oy >= 0.7:
                                dups.append((o_i, len(covered(om, od)), od["class"]))
                    rows.append(dict(page=page.get("page_index"), sysi=sys_i,
                                     staff=s_i, name=name,
                                     m=m.get("measure_index"), cls=d["class"],
                                     conf=round(d.get("confidence", 0) or 0, 2),
                                     bbox=[int(v) for v in d["bbox_page"]],
                                     ncov=len(cov), dups=dups))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--staff-filter", default=None)
    ap.add_argument("--only-suspect", action="store_true")
    args = ap.parse_args()
    rows = collect(json.loads(Path(args.json).read_text()))
    for r in rows:
        if args.staff_filter and args.staff_filter.lower() not in str(r["name"]).lower():
            continue
        if args.only_suspect and r["ncov"] >= 2 and not r["dups"]:
            continue
        print(f"p{r['page']} sys{r['sysi']} st{r['staff']:2d} {str(r['name'])[:22]:22s} "
              f"m{r['m']:2d} {r['cls']:5s} c{r['conf']} cov={r['ncov']} "
              f"bbox={r['bbox']} dups={r['dups']}")
    print(f"\nTOTAL arcs {len(rows)}; zero-coverage "
          f"{sum(1 for r in rows if r['ncov'] == 0)}; "
          f"with cross-staff dup {sum(1 for r in rows if r['dups'])}")


if __name__ == "__main__":
    main()
