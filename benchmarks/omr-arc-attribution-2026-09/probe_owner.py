"""For every arc: which staff of its system hugs it best?

An arc is drawn against the run of noteheads it binds — just clear of the head
row, on the side away from the stems. So the staff an arc BELONGS to is the one
whose noteheads it sits closest to, and that question is answerable for staves
that never detected the arc at all: the noteheads have already been arbitrated
across staves by `transcribe._dedupe_cross_staff_detections`, so each staff's
head set is the one the reader would see.

Prints one row per arc with the owning staff's clearance and the best rival's.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.export import _measure_noteheads, _SLUR_ARC_PAD_NOTEHEADS  # noqa: E402
from probe_arc_dy import arcs_of, gap  # noqa: E402


def staff_heads(staff):
    out = []
    for m in staff.get("measures", []):
        out.extend(_measure_noteheads(m))
    return out


def clearance(arc_box, heads):
    """(spaces-free clearance in px, n covered) of an arc against a head set."""
    if not heads:
        return None, 0
    pad = _SLUR_ARC_PAD_NOTEHEADS * (
        sum(h["bbox_page"][2] for h in heads) / len(heads))
    ax, _, aw, _ = arc_box
    cov = [h for h in heads
           if ax - pad <= h["bbox_page"][0] + h["bbox_page"][2] / 2.0 <= ax + aw + pad]
    if not cov:
        return None, 0
    return min(gap(arc_box, h["bbox_page"]) for h in cov), len(cov)


def rows(path):
    res = json.loads(Path(path).read_text())
    out = []
    for page in res["pages"]:
        for sys_i, sys_ in enumerate(page.get("systems", [])):
            staves = sys_.get("staves", [])
            heads = [staff_heads(s) for s in staves]
            sps = []
            for s in staves:
                g = s.get("staff_geometry") or {}
                sps.append(g.get("line_spacing_px"))
            for s_i, st in enumerate(staves):
                sp = sps[s_i]
                if not sp:
                    continue
                for m in st.get("measures", []):
                    for d in arcs_of(m):
                        own, ncov = clearance(d["bbox_page"], heads[s_i])
                        rivals = []
                        for o_i in range(len(staves)):
                            if o_i == s_i or not sps[o_i]:
                                continue
                            g, n = clearance(d["bbox_page"], heads[o_i])
                            if g is not None and n >= 2:
                                rivals.append((g / sps[o_i], o_i, n))
                        rivals.sort()
                        out.append(dict(
                            sysi=sys_i, staff=s_i, m=m.get("measure_index"),
                            cls=d["class"], conf=round(d.get("confidence") or 0, 2),
                            ncov=ncov,
                            own=None if own is None else round(own / sp, 2),
                            best=rivals[0] if rivals else None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--staff", type=int, default=None)
    args = ap.parse_args()
    for r in rows(args.json):
        if args.staff is not None and r["staff"] != args.staff:
            continue
        b = r["best"]
        bs = "-" if b is None else f"st{b[1]} @{b[0]:.2f} (n={b[2]})"
        print(f"sys{r['sysi']} st{r['staff']:2d} m{r['m']:2d} {r['cls']:5s} "
              f"c{r['conf']:<4} cov={r['ncov']:2d} own={r['own']} best_rival={bs}")


if __name__ == "__main__":
    main()
