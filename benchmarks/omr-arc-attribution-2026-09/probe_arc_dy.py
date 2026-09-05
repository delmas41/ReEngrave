"""How far is an arc from the noteheads it claims to bind?

An arc binds a run of noteheads and is drawn just outside them — a slur sits
about a staff space clear of the head row on the side away from the stems. An
arc that landed in a staff's cell because the PADDING reached the neighbouring
staff's ink is far from every notehead in this staff, in the direction of the
staff it really belongs to.

Emits one row per arc: the signed vertical gap, in staff spaces, from the arc's
box to the nearest notehead it covers in x.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.omr.export import _measure_noteheads, _SLUR_ARC_PAD_NOTEHEADS  # noqa: E402


def arcs_of(measure):
    return [d for d in measure.get("detections", [])
            if d.get("category") == "structural"
            and d.get("class") in ("slur", "tie")
            and len(d.get("bbox_page") or ()) == 4]


def covered(measure, arc):
    heads = _measure_noteheads(measure)
    if not heads:
        return []
    pad = _SLUR_ARC_PAD_NOTEHEADS * (
        sum(h["bbox_page"][2] for h in heads) / len(heads))
    ax, _, aw, _ = arc["bbox_page"]
    return [h for h in heads
            if ax - pad <= h["bbox_page"][0] + h["bbox_page"][2] / 2.0 <= ax + aw + pad]


def gap(arc_box, head_box):
    """Vertical clearance between two boxes in px; 0 when they overlap."""
    a0, a1 = arc_box[1], arc_box[1] + arc_box[3]
    h0, h1 = head_box[1], head_box[1] + head_box[3]
    if a1 < h0:
        return h0 - a1
    if h1 < a0:
        return a0 - h1
    return 0.0


def rows_for(path):
    res = json.loads(Path(path).read_text())
    out = []
    for page in res["pages"]:
        for sys_i, sys_ in enumerate(page.get("systems", [])):
            for s_i, st in enumerate(sys_.get("staves", [])):
                geom = st.get("staff_geometry") or {}
                sp = geom.get("line_spacing_px")
                lines = geom.get("line_ys_page")
                if not sp or not lines:
                    continue
                top, bot = float(min(lines)), float(max(lines))
                for m in st.get("measures", []):
                    for d in arcs_of(m):
                        cov = covered(m, d)
                        if not cov:
                            g = None
                        else:
                            g = min(gap(d["bbox_page"], h["bbox_page"]) for h in cov) / sp
                        ay = d["bbox_page"][1] + d["bbox_page"][3] / 2.0
                        # signed distance from the staff band, in spaces
                        if ay < top:
                            band = (ay - top) / sp
                        elif ay > bot:
                            band = (ay - bot) / sp
                        else:
                            band = 0.0
                        out.append(dict(sysi=sys_i, staff=s_i,
                                        m=m.get("measure_index"),
                                        cls=d["class"],
                                        conf=round(d.get("confidence") or 0, 2),
                                        ncov=len(cov),
                                        dy=None if g is None else round(g, 2),
                                        band=round(band, 2)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--staff", type=int, default=None)
    args = ap.parse_args()
    for r in rows_for(args.json):
        if args.staff is not None and r["staff"] != args.staff:
            continue
        print(f"sys{r['sysi']} st{r['staff']:2d} m{r['m']:2d} {r['cls']:5s} "
              f"c{r['conf']:<4} cov={r['ncov']:2d} dy={r['dy']} band={r['band']}")


if __name__ == "__main__":
    main()
