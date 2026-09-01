"""Why does the F-clef dot veto not fire on the bass clefs that survive?

Every false positive this layer has left is a real clef misread on the staff —
19 bass and 2 treble across both sweep corpora — so `_has_f_clef_dots` is the
single remaining cause, and it has already cost two sessions by being reasoned
about rather than measured. Twice the recorded diagnosis was wrong: first "the
dots merge into the clef's body" (they did not; the veto was handed the wrong
pixels), then "loosen the height bound" (measured, and it costs 27 real clefs to
save 3).

So this reports what is actually in the search window. For every candidate it
re-runs the veto's own component pass with instrumentation and prints, per
connected component, its size and position in staff spaces and which test
turned it away; then, per candidate, the pair that came CLOSEST to passing and
the constraint that blocked it.

    python3 benchmarks/omr-clef-geometry/probe_f_clef_dots.py
    python3 benchmarks/omr-clef-geometry/probe_f_clef_dots.py --per-staff

Run over BOTH populations, always. A loosening that admits the bass clefs is
worth nothing if the real C clefs have components that would pass it too, and
the real C clefs are the reason every previous loosening was refused. The
summary prints them side by side for exactly that reason.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.clef_locator import (  # noqa: E402
    DEFAULT_LOCATOR_CONFIG,
    _analysis_scale,
    _ink_mask,
    locate_clef,
)
from tools.omr.header_ink import staff_metrics  # noqa: E402
from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines,
    extract_measures,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402

DEFAULT_SPECS = ("beethoven5-clef-sweep.json", "mahler5-clef-sweep.json")


def components(mask, bbox, spacing, config):
    """Every component in the veto's own search window, measured in staff
    spaces, with the first test it fails."""
    x, y, w, h = bbox
    right = min(mask.shape[1],
                x + w + int(round(config.dot_search_right_spaces * spacing)))
    sub = mask[y:y + h, x:right]
    if sub.size == 0:
        return []
    n, _l, stats, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
    out = []
    for i in range(1, n):
        bw = stats[i, cv2.CC_STAT_WIDTH] / spacing
        bh = stats[i, cv2.CC_STAT_HEIGHT] / spacing
        aspect = bw / max(bh, 1e-6)
        cx = stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH] / 2.0
        cy = stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2.0
        # Both readings the veto applies, so this reports what ships rather
        # than the strict half of it — see `_has_f_clef_dots`.
        strict = (config.dot_min_size_spaces <= bh <= config.dot_max_height_spaces
                  and config.dot_min_aspect <= aspect <= config.dot_max_aspect
                  and cx / w >= config.dot_right_fraction)
        clear = (config.dot_min_size_spaces <= bh <= config.dot_clear_max_height_spaces
                 and config.dot_clear_min_aspect <= aspect <= config.dot_clear_max_aspect
                 and cx / w >= config.dot_clear_right_fraction)
        fail = None
        if not (config.dot_min_size_spaces <= bw <= config.dot_max_size_spaces):
            fail = "width"
        elif strict or clear:
            fail = None
        elif bh > config.dot_clear_max_height_spaces:
            fail = "height"
        elif not (config.dot_clear_min_aspect <= aspect <= config.dot_clear_max_aspect):
            fail = "aspect"
        elif cx / w < config.dot_clear_right_fraction:
            # Inside the body, where only the strict shape bounds apply — and
            # they are strict for a reason: a C clef's own stroke fragments
            # live here. See `dot_clear_right_fraction`.
            fail = "inside-the-body"
        else:
            fail = "shape"
        out.append({"w": bw, "h": bh, "aspect": aspect, "cx": cx, "cy": cy,
                    "right_frac": cx / w, "fail": fail,
                    "tier": "strict" if strict else "clear" if clear else None})
    return out


def closest_pair(comps, spacing, config):
    """The pair that comes nearest to being an F clef's dots, and what blocks
    it. Only pairs whose members are individually plausible in WIDTH and
    position are considered — a pair test on arbitrary ink says nothing."""
    cands = [c for c in comps
             if config.dot_min_size_spaces <= c["w"] <= config.dot_max_size_spaces
             and c["right_frac"] >= config.dot_right_fraction]
    best = None
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            a, b = cands[i], cands[j]
            dx = abs(a["cx"] - b["cx"]) / spacing
            dy = abs(a["cy"] - b["cy"]) / spacing
            blocked = []
            if dx > config.dot_max_dx_spaces:
                blocked.append("dx")
            if not (config.dot_min_dy_spaces <= dy <= config.dot_max_dy_spaces):
                blocked.append("dy")
            for c, tag in ((a, "a"), (b, "b")):
                if c["fail"] is not None:
                    blocked.append(f"{c['fail']}({tag})")
            score = len(blocked)
            row = {"dx": dx, "dy": dy, "a": a, "b": b, "blocked": blocked}
            if best is None or score < len(best["blocked"]):
                best = row
    return best


def run(spec_path: Path, dpi: int, per_staff: bool) -> dict:
    spec = json.loads(spec_path.read_text())
    pdf = Path(spec["pdf"]).expanduser()
    if not pdf.is_absolute():
        pdf = REPO / spec["pdf"]
    print(f"\n{spec_path.name} — {spec['source']}")
    if not pdf.exists():
        print(f"  skipped, no score at {pdf}")
        return {}
    by_page: dict[int, list[dict]] = {}
    for r in spec["staves"]:
        by_page.setdefault(r["page"], []).append(r)

    config = DEFAULT_LOCATOR_CONFIG
    tally: dict[str, Counter] = {"misread": Counter(), "real": Counter()}
    heights: dict[str, list[float]] = {"misread": [], "real": []}
    for page_index in sorted(by_page):
        page = render_page(pdf, page_index, dpi=dpi)
        pws = detect_barlines(detect_staves(page))
        remove_staff_lines(resegment_fused_measures(pws, extract_measures(pws)))
        cells = header_cells_for_page(pws)
        for r in by_page[page_index]:
            cell = cells.get(r["staff"])
            if cell is None:
                continue
            found = locate_clef(cell, config=config)
            if found is None:
                continue          # already declined; the veto is not the issue
            m = staff_metrics(cell)
            if m is None:
                continue
            spacing_cell = m[0]
            mask = _ink_mask(cell, spacing_cell, config)
            if mask is None:
                continue
            scale = _analysis_scale(spacing_cell, config)
            spacing = spacing_cell * scale
            bbox = tuple(int(round(v * scale)) for v in found.bbox)
            comps = components(mask, bbox, spacing, config)
            best = closest_pair(comps, spacing, config)
            group = "real" if r["c_clef"] else "misread"
            key = ("no pair of dot-width components in the right half"
                   if best is None else
                   "PASSES (should have been vetoed)" if not best["blocked"]
                   else " + ".join(sorted(set(b.split("(")[0]
                                             for b in best["blocked"]))))
            tally[group][key] += 1
            if best is not None:
                for c in (best["a"], best["b"]):
                    heights[group].append(c["h"])
            if per_staff and group == "misread":
                print(f"    p{page_index:>3} s{r['staff']:<3} {r['note'][:34]:<34} "
                      f"-> {key}")
                if best is not None:
                    for tag, c in (("a", best["a"]), ("b", best["b"])):
                        print(f"        {tag}: w={c['w']:.2f} h={c['h']:.2f} "
                              f"aspect={c['aspect']:.2f} right={c['right_frac']:.2f} "
                              f"fail={c['fail']}")
                    print(f"        dx={best['dx']:.2f} dy={best['dy']:.2f}")
    for group in ("misread", "real"):
        n = sum(tally[group].values())
        print(f"  {group} candidates that survive the veto: {n}")
        for key, count in tally[group].most_common():
            print(f"    {count:>3}  {key}")
        v = sorted(heights[group])
        if v:
            print(f"    near-pair component heights: median {np.median(v):.2f} "
                  f"range [{v[0]:.2f}, {v[-1]:.2f}]  (limit "
                  f"{DEFAULT_LOCATOR_CONFIG.dot_max_height_spaces})")
    return tally


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--spec", type=Path, action="append")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--per-staff", action="store_true")
    args = ap.parse_args()
    for spec in (args.spec or [HERE / n for n in DEFAULT_SPECS]):
        run(spec, args.dpi, args.per_staff)
    print("\nA loosening is only available where the misread population has a "
          "property the\nreal one does not. Read both columns, on both editions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
