"""Can classical CV find hairpins in the band below a staff, on a real scan?

The detector reads **1 hairpin against 198 `<wedge>` of truth** over 11 scanned
pages, while a 300 dpi crop shows them plainly. A hairpin is a thin diagonal
line, which is the shape Phase 4f moved stems and beams to classical CV for.
This asks whether the CV is actually available before anyone writes the reader —
`docs/scope-cv-hairpin-detection-2026-09-04.md` §6.

⚠️ THE QUESTION IS NOT "is there ink there", IT IS "does anything SEPARATE a
hairpin from a slur". The band below a staff is full of arcs reaching down from
the notes above, plus words (`pizz.`, `espr.`, `arco`). Fill ratio cannot do it —
`direction_text` already uses that to tell text from curves, and a hairpin is as
sparse as a slur.

THE PROPOSED DISCRIMINATOR, and what this measures: take each candidate's
PER-COLUMN VERTICAL EXTENT, `h(x) = max_y(x) - min_y(x)`.

    a slur or tie   one stroke, so h(x) is the STROKE THICKNESS at every x,
                    small and flat, however far the arc travels
    a hairpin       two arms with air between them, so h(x) runs from ~0 at
                    the apex to the full opening at the other end

So `max h` in staff spaces should separate them outright, with no reference to
angle, length or curvature — none of which are stable across engravers.

    python3 benchmarks/omr-hairpin-cv-2026-09/probe_band_ink.py \\
        --pdf <scan.pdf> --page N --transcription read.json --out-dir out/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

#: The band a dynamic or hairpin is printed in, in staff spaces below the
#: staff's bottom line. Measured: every hairpin in the engraved page truth sits
#: below a staff and none inside one (8 of 8), and the dynamic-letter population
#: sharing this band runs +0.0 to +5.6 spaces with a 2.5-space empty gap under
#: it (`benchmarks/omr-dynamics-band-2026-09`).
BAND_TOP_SPACES = 0.3
BAND_BOTTOM_SPACES = 6.0

#: A component narrower than this is a speck; wider than this is a rule or a
#: merged run. A hairpin on the Brahms strip is a few staff spaces wide.
MIN_WIDTH_SPACES = 0.8
MAX_WIDTH_SPACES = 30.0

#: Detections whose BOX is mostly paper. Blanking them erases whatever stands
#: under them — in this band, the hairpins. Same rule as
#: `direction_text.BandConfig.max_blank_width_spaces`, and the same trap.
_SPAN_CLASSES = frozenset({"slur", "tie", "beam", "staff", "ledgerLine"})
MAX_BLANK_WIDTH_SPACES = 3.0


def staves_of(result: dict[str, Any], page_index: int = 0) -> list[dict]:
    out = []
    for system in result["pages"][page_index].get("systems", []):
        for staff in system.get("staves", []):
            g = staff.get("staff_geometry") or {}
            ys = g.get("line_ys_page") or []
            if len(ys) >= 5 and g.get("line_spacing_px"):
                out.append({"index": staff.get("staff_index"),
                            "bottom": float(max(ys)), "top": float(min(ys)),
                            "spacing": float(g["line_spacing_px"]),
                            "x0": float(g.get("x_start") or 0),
                            "x1": float(g.get("x_end") or 0),
                            "staff": staff})
    return sorted(out, key=lambda s: s["bottom"])


def detection_boxes(result: dict[str, Any], page_index: int = 0) -> list[tuple]:
    """Every detection as a page-pixel box — what the band reader must ignore."""
    out = []
    for system in result["pages"][page_index].get("systems", []):
        for staff in system.get("staves", []):
            for meas in staff.get("measures", []):
                box = meas.get("bbox_page_px") or [0, 0, 0, 0]
                up = float(meas.get("upscale_factor") or 1.0) or 1.0
                for det in meas.get("detections", []):
                    b = det.get("bbox")
                    if not b or len(b) != 4:
                        continue
                    out.append((float(box[0]) + b[0] / up,
                                float(box[1]) + b[1] / up,
                                b[2] / up, b[3] / up,
                                det.get("class") or ""))
    return out


def column_extent_profile(mask: np.ndarray) -> np.ndarray:
    """`h(x)` — the vertical extent of ink in each column, in pixels.

    This is the whole discriminator. A single stroke gives its own thickness at
    every column however much it curves; two arms with air between them give the
    distance between the arms.
    """
    out = np.zeros(mask.shape[1], dtype=np.float32)
    for x in range(mask.shape[1]):
        rows = np.flatnonzero(mask[:, x])
        if rows.size:
            out[x] = rows[-1] - rows[0] + 1
    return out


def boundary_straightness(mask: np.ndarray, spacing: float) -> dict[str, float]:
    """How well the component's top and bottom outlines fit STRAIGHT LINES.

    ⚠️ THE HALF THE FIRST CUT LEFT OUT, and the open-extent test alone is
    refuted without it: on one scanned page 302 of 312 band components clear an
    open extent of 0.4 staff spaces, against roughly 68 hairpins on the page.
    Extent says a component is TALL somewhere; it does not say it is a WEDGE.

    A hairpin is two STRAIGHT arms. A slur is one curved stroke, so both its
    outlines are arcs and neither fits a line. That is the difference this
    measures, and it needs no reference to angle or length — which vary with
    the engraver and would not survive a second publisher.
    """
    xs, tops, bots = [], [], []
    for x in range(mask.shape[1]):
        rows = np.flatnonzero(mask[:, x])
        if rows.size:
            xs.append(x); tops.append(rows[0]); bots.append(rows[-1])
    if len(xs) < 6:
        return {}
    x = np.asarray(xs, float)
    out = {}
    for name, ys in (("top", np.asarray(tops, float)),
                     ("bot", np.asarray(bots, float))):
        a, b = np.polyfit(x, ys, 1)
        resid = ys - (a * x + b)
        out[f"{name}_rms_sp"] = float(np.sqrt((resid ** 2).mean()) / spacing)
        out[f"{name}_slope"] = float(a)
    out["straight_rms_sp"] = max(out["top_rms_sp"], out["bot_rms_sp"])
    # Arms converge: the two outlines have DIFFERENT slopes. A stroke's two
    # outlines are parallel, whatever it does.
    out["converge"] = abs(out["top_slope"] - out["bot_slope"])
    return out


def describe(mask: np.ndarray, spacing: float) -> dict[str, float]:
    h = column_extent_profile(mask)
    live = h[h > 0]
    if live.size < 3:
        return {}
    # The apex end and the open end, robust to a few stray pixels.
    lo = float(np.percentile(live, 10))
    hi = float(np.percentile(live, 90))
    return {
        "width_sp": mask.shape[1] / spacing,
        "height_sp": mask.shape[0] / spacing,
        "open_sp": hi / spacing,          # extent at the open end
        "closed_sp": lo / spacing,        # extent at the apex end
        "opening_sp": (hi - lo) / spacing,
        "fill": float(mask.sum() / 255.0) / max(1.0, mask.size),
        **boundary_straightness(mask, spacing),
    }


def probe(pdf: Path, page_index: int, result: dict, out_dir: Path,
          dpi: int, result_page: int = 0) -> dict:
    import fitz  # type: ignore

    page = fitz.open(pdf)[page_index]
    pm = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if pm.n >= 3 else img[:, :, 0]
    ink = (gray < 180).astype(np.uint8) * 255

    # Erase the detections: "find the hairpin" becomes "find the ink".
    #
    # ⚠️ BUT NOT THE SPANS, and this was a real bug in the first cut of this
    # probe. A slur, tie or beam box is mostly the PAPER its arc crosses, so
    # blanking it wholesale erases whatever else stands under it — which in this
    # band is exactly the hairpins we are looking for. `direction_text`
    # documents the same rule and avoids the same trap
    # (`max_blank_width_spaces`): "a SPAN wider than a glyph can be, whose box
    # is mostly the paper its arc crosses".
    spacings = [s["spacing"] for s in staves_of(result, result_page)]
    sp_med = sorted(spacings)[len(spacings) // 2] if spacings else 1.0
    for x, y, w, h, cls in detection_boxes(result, result_page):
        if cls in _SPAN_CLASSES or w > MAX_BLANK_WIDTH_SPACES * sp_med:
            continue
        x0, y0 = max(0, int(x)), max(0, int(y))
        ink[y0:int(y + h) + 1, x0:int(x + w) + 1] = 0

    staves = staves_of(result, result_page)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, s in enumerate(staves):
        sp = s["spacing"]
        top = int(s["bottom"] + BAND_TOP_SPACES * sp)
        floor = s["bottom"] + BAND_BOTTOM_SPACES * sp
        if i + 1 < len(staves):
            floor = min(floor, staves[i + 1]["top"] - 0.3 * sp)
        bot = int(floor)
        if bot - top < 4:
            continue
        band = ink[top:bot, :]
        n, labels, stats, _ = cv2.connectedComponentsWithStats(band, 8)
        for lab in range(1, n):
            x, y, w, h, area = stats[lab]
            if not (MIN_WIDTH_SPACES * sp <= w <= MAX_WIDTH_SPACES * sp):
                continue
            comp = ((labels[y:y + h, x:x + w] == lab).astype(np.uint8)) * 255
            d = describe(comp, sp)
            if not d:
                continue
            d.update({"staff": s["index"], "x": int(x), "y": int(top + y),
                      "w": int(w), "h": int(h), "area": int(area)})
            rows.append(d)
    return {"pdf": str(pdf), "page": page_index, "dpi": dpi,
            "n_staves": len(staves), "components": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--transcription", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--result-page", type=int, default=0,
                    help="page index INSIDE the transcription, which holds only "
                         "the pages it was asked for — not the PDF page number")
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    res = json.loads(args.transcription.read_text())
    out = probe(args.pdf, args.page, res, args.out_dir, args.dpi,
                result_page=args.result_page)
    rows = out["components"]
    print(f"{out['n_staves']} staves, {len(rows)} band components "
          f"(detections already erased)")

    if rows:
        opens = sorted(r["open_sp"] for r in rows)
        print("\nper-column OPEN extent, in staff spaces — the discriminator:")
        for q in (10, 25, 50, 75, 90, 95, 99):
            print(f"   p{q:<3d} {opens[min(len(opens) - 1, q * len(opens) // 100)]:.2f}")
        for thr in (0.4, 0.5, 0.6, 0.8, 1.0):
            n = sum(1 for r in rows if r["open_sp"] >= thr)
            print(f"   components with open extent >= {thr:.1f} sp: {n}")

        have = [r for r in rows if "straight_rms_sp" in r]
        print(f"\nSTRAIGHTNESS of the outlines ({len(have)} measurable), "
              "rms of a line fit in staff spaces:")
        sr = sorted(r["straight_rms_sp"] for r in have)
        for q in (10, 25, 50, 75, 90):
            print(f"   p{q:<3d} {sr[min(len(sr) - 1, q * len(sr) // 100)]:.3f}")
        print("\nBOTH TESTS — open extent >= 0.5 sp AND outlines straight:")
        for rms in (0.05, 0.08, 0.10, 0.15, 0.20):
            n = sum(1 for r in have
                    if r["open_sp"] >= 0.5 and r["straight_rms_sp"] <= rms)
            print(f"   straight within {rms:.2f} sp: {n:4d} candidates")
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
