"""IS THE OPENING'S 1-PIXEL KERNEL THE FRAGMENTER? A prototype, not a patch.

`rejection_census.py` attributes all 793 missing stems, and the reasons sum:
too WIDE 237, too SHORT 199, NO component 167, pair rule 73, cell EDGE 70,
too TALL 47.

SHORT + NONE = 366 (46%) is fragmentation, and `erasure_arm.py` already
refuted the obvious cause -- reading the ORIGINAL raster recovers fewer, so
removing the staff lines is not what breaks them.

What remains is the opening itself. Its structuring element is
`(1, kernel_h)`: **one pixel wide**, demanding an unbroken vertical run 1.6
staff spaces tall IN A SINGLE COLUMN. A scanned plate bows 8-17 page px
across a staff (`OMR_CELL_LINE_TRACE`'s own measurement), so a stem leans, its
ink walks across columns, and no single column carries the whole run. That
story predicts the erasure arm's negative: the lean is on the original too.

THE TEST IS A ONE-OPERATION PROTOTYPE. Dilate the ink horizontally before the
opening, so a column "sees" its neighbours and a leaning stroke stays whole,
then run the shipped chain unchanged. If SHORT and NONE collapse, the kernel
width is the fragmenter.

⚠️ IT IS NOT A PROPOSED FIX. A horizontal dilation also fattens every other
vertical -- barlines, beams' edges, the sides of noteheads -- so it BUYS
recall and PAYS in width, which is already the largest rejection bucket. Both
are counted. A real repair would slant the kernel or track the stroke, not
smear the page.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-ledger-extrapolation-2026-09"))
from recordstream import stream_array  # noqa: E402


def overlaps(a, b) -> bool:
    ax0, ay0, aw, ah = a
    bx0, by0, bw, bh = b
    return (min(ax0 + aw, bx0 + bw) - max(ax0, bx0) > 0
            and min(ay0 + ah, by0 + bh) - max(ay0, by0) > 0)


def run_chain(cell, ld, dilate_w: int):
    """The SHIPPED chain, with an optional horizontal pre-dilation.

    Every constant is the shipped one; `dilate_w` is the only change, and at
    1 this is `detect_stems(drop_accidental_pairs=False)` exactly -- asserted
    by the caller against the real function.
    """
    src = (cell.image_no_staff
           if getattr(cell, "image_no_staff", None) is not None else cell.image)
    if src is None or src.size == 0:
        return [], collections.Counter()
    sp = ld._staff_line_spacing(cell)
    if sp <= 1.0:
        return [], collections.Counter()
    cell_w = cell.width
    edge = max(int(round(sp * 0.8)), 12)
    ink = ld._binary_ink(src)
    if dilate_w > 1:
        ink = cv2.dilate(ink, cv2.getStructuringElement(
            cv2.MORPH_RECT, (dilate_w, 1)))
    kh = max(3, int(round(sp * 2.0 * ld.STEM_KERNEL_MARGIN)))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                              cv2.getStructuringElement(cv2.MORPH_RECT, (1, kh)))
    num, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    min_h, max_h = int(round(sp * 2.0)), int(round(sp * ld.STEM_MAX_HEIGHT_LINES))
    # ⚠️ the width cap must widen WITH the dilation or the prototype simply
    # re-fails everything it just joined; +dilate_w px is the minimum honest
    # allowance and is stated rather than tuned.
    max_w = max(3, int(round(sp * 0.6))) + (dilate_w - 1)
    out, why = [], collections.Counter()
    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if h < min_h:
            why["too SHORT"] += 1
        elif h > max_h:
            why["too TALL"] += 1
        elif w > max_w:
            why["too WIDE"] += 1
        elif x < edge or x + w > cell_w - edge:
            why["CELL EDGE"] += 1
        elif area < max(4, sp * 0.5):
            why["AREA"] += 1
        elif h / max(1, w) < 3.0:
            why["ASPECT"] += 1
        else:
            out.append((float(x), float(y), float(w), float(h)))
    return out, why


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()

    from tools.omr.staged.pipeline import prepare_pages
    from tools.omr.staged.gather import _system_local
    from tools.omr import line_detection as ld

    heads, accid = {}, collections.defaultdict(list)
    for o in stream_array(a.record, "observations"):
        if o.get("quantity") != "glyph_box":
            continue
        v = o.get("value")
        if not (isinstance(v, list) and len(v) == 5):
            continue
        name, box = str(v[0]), tuple(float(x) for x in v[1:])
        if name.startswith("notehead"):
            heads[o["subject"]] = box
        elif name.startswith("accidental") or name.startswith("key"):
            p = o["subject"].split("/")
            accid["cell/" + "/".join(p[1:5])].append(box)
    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))
    missing = {s for s, r in verdict.items() if r == "no_stem" and s in heads}
    print(f"{a.label}: {len(missing)} heads abstain `no_stem`")

    pages = [int(x) for x in a.pages.split(",")]
    t0 = time.time()
    prepared = list(zip(prepare_pages(a.pdf, pages, dpi=600), pages))
    print(f"re-cut in {time.time() - t0:.0f}s")

    WIDTHS = (1, 2, 3, 5)
    store = {w: {} for w in WIDTHS}
    whys = {w: collections.Counter() for w in WIDTHS}
    drift = 0
    for (pws, cells), pg in prepared:
        local = _system_local(pws.staves)
        for c in cells:
            key = local.get(c.staff_index)
            if key is None:
                continue
            ck = f"cell/{pg}/{key[0]}/{key[1]}/{c.measure_index}"
            for w in WIDTHS:
                got, why = run_chain(c, ld, w)
                store[w][ck] = got
                whys[w] += why
            real = sorted((float(d.x_canonical), float(d.y_canonical),
                           float(d.width_canonical), float(d.height_canonical))
                          for d in ld.detect_stems(c, drop_accidental_pairs=False))
            if sorted(store[1][ck]) != real:
                drift += 1
    print(f"cells: {len(store[1])}   FAITHFULNESS drift at width 1: {drift}")
    if drift:
        print("DEAD: the replication is not the shipped chain", file=sys.stderr)
        return 2

    print(f"\n{'pre-dilation':<14} {'strokes':>8} {'recovers':>9} {'of 793':>8} "
          f"{'SHORT':>7} {'NONE-ish':>9} {'WIDE':>7} {'on accid':>9}")
    out = {"label": a.label, "no_stem": len(missing), "arms": {}}
    base = store[1]
    for w in WIDTHS:
        s = store[w]
        rec = 0
        for sub in missing:
            p = sub.split("/")
            ck = "cell/" + "/".join(p[1:5])
            if ck in s and any(overlaps(heads[sub], st) for st in s[ck]):
                rec += 1
        onacc = 0
        for ck, sts in s.items():
            for st in sts:
                if st in base.get(ck, []):
                    continue
                if any(overlaps(st, ac) for ac in accid.get(ck, [])):
                    onacc += 1
        tot = sum(len(v) for v in s.values())
        out["arms"][f"dilate {w}px"] = {
            "strokes": tot, "recovered": rec,
            "rejections": dict(whys[w]), "new_on_accidental": onacc}
        print(f"{w:>2}px{'':<10} {tot:>8} {rec:>9} {rec/len(missing):>7.1%} "
              f"{whys[w]['too SHORT']:>7} {'-':>9} {whys[w]['too WIDE']:>7} "
              f"{onacc:>9}")

    print("\n== the rejection census, per arm (all components, not per head)")
    keys = ["too SHORT", "too TALL", "too WIDE", "CELL EDGE", "AREA", "ASPECT"]
    print(f"{'reason':<12} " + "".join(f"{f'{w}px':>10}" for w in WIDTHS))
    for k in keys:
        print(f"{k:<12} " + "".join(f"{whys[w][k]:>10}" for w in WIDTHS))
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
