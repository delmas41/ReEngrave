"""Hairpins, read by classical CV in the band below each staff.

THE DETECTOR DOES NOT SEE THEM ON SCANS. Over eleven scanned pages with
hand-verified windows it finds **1 hairpin against 99** the truth carries, while
a 600 dpi crop shows them plainly — straight arms, connected apex, sitting in the
gap under the staff. A hairpin is a thin diagonal line, which is the shape
Phase 4f moved stems and beams out of the detector for, on the stated grounds
that YOLO bounding boxes are structurally bad at thin lines. Hairpins are the
member of that family that was left behind.

⚠️ **SEARCHED IN THE BAND, IN PAGE PIXELS, PER STAFF — not per measure cell**,
which is where every other detector here works. Two reasons, both measured:

  * a hairpin SPANS measures, and a per-cell reader sees fragments — which is
    what makes a cell-based export emit one crescendo as two;
  * the band belongs to exactly ONE staff, so attribution is right by
    construction. The detector's own hairpins have to be rescued afterwards by a
    dedup veto: 3 of Mahler 5's 4 are filed under staff 18 while standing in
    staff 17's band.

THREE TESTS, and each was measured alone before being combined
(`benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md`):

  1. **per-column open extent** — one stroke gives its own thickness at every
     column however much it curves; two arms give the distance between them.
     ⚠️ ALONE IT IS USELESS: 302 of 312 band components clear it.
  2. **outline straightness** — a hairpin's arms are straight, a slur is one
     curved stroke so neither of its outlines fits a line.
  3. **isolation** — *a beam is always attached to something, its stems; a
     hairpin is attached to nothing.* Measured on the whole page, not the band:
     component growth is 1.0x at p50 and **3248x** at p75, with nothing between.
     ⚠️ It must be the WHOLE page — the band crop cuts a beam off from its stems
     and makes it look as isolated as a hairpin.

⚠️ **Fill ratio was tried and does NOT reject the beams** (p10 0.375, median
0.437): a long shallow hairpin is dense, because its bbox height is the *opening*
and its arms run a few pixels apart along most of the length.

Gate, constants set on one page then run unchanged across eleven: **59 of 99
hairpins against the detector's 1, and zero false positives on five of the six
pages that carry none.**
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import cv2
import numpy as np

#: The band a hairpin is printed in, in staff spaces below the bottom staff
#: line. ⚠️ Measured, not assumed: every hairpin in the engraved page truth sits
#: below a staff and none inside one (8 of 8), and the dynamic-letter population
#: sharing this band runs +0.0 to +5.6 spaces.
BAND_TOP_SPACES = 0.3
BAND_BOTTOM_SPACES = 6.0

#: The two arms must open by at least this much somewhere — a stroke never does.
MIN_OPEN_SPACES = 0.5
#: ...and both outlines must fit a straight line this closely.
MAX_OUTLINE_RMS_SPACES = 0.10
#: A component whose full-page extent is more than this multiple of its own is
#: attached to something. The population is 1.0x against 3248x; any value in
#: that gap gives the same answer.
MAX_COMPONENT_GROWTH = 2.0

MIN_WIDTH_SPACES = 0.8
MAX_WIDTH_SPACES = 30.0

#: Detections whose BOX is mostly paper. Blanking them erases whatever stands
#: under them — in this band, the hairpins themselves. Same rule and the same
#: trap as `direction_text.BandConfig.max_blank_width_spaces`.
SPAN_CLASSES = frozenset({"slur", "tie", "beam", "staff", "ledgerLine"})
MAX_BLANK_WIDTH_SPACES = 3.0


@dataclass(frozen=True)
class Hairpin:
    """One hairpin in PAGE pixels, with the staff it was found under."""

    staff_index: int
    kind: str            # "crescendo" | "diminuendo"
    x: int
    y: int
    width: int
    height: int
    open_spaces: float
    outline_rms_spaces: float


def _outlines(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs, tops, bots = [], [], []
    for x in range(mask.shape[1]):
        rows = np.flatnonzero(mask[:, x])
        if rows.size:
            xs.append(x)
            tops.append(rows[0])
            bots.append(rows[-1])
    return np.asarray(xs, float), np.asarray(tops, float), np.asarray(bots, float)


def measure_component(mask: np.ndarray, spacing: float) -> dict[str, float] | None:
    """The three shape numbers for one candidate, or None if unmeasurable."""
    xs, tops, bots = _outlines(mask)
    if xs.size < 6:
        return None
    extent = bots - tops + 1
    lo = float(np.percentile(extent, 10))
    hi = float(np.percentile(extent, 90))
    rms = 0.0
    for ys in (tops, bots):
        a, b = np.polyfit(xs, ys, 1)
        rms = max(rms, float(np.sqrt(((ys - (a * xs + b)) ** 2).mean())))
    # Which end is the apex: crescendo opens to the RIGHT.
    n = max(1, xs.size // 4)
    left, right = float(extent[:n].mean()), float(extent[-n:].mean())
    return {
        "open_spaces": hi / spacing,
        "closed_spaces": lo / spacing,
        "outline_rms_spaces": rms / spacing,
        "kind": "crescendo" if right > left else "diminuendo",
    }


def _band_bounds(staves: list[dict], i: int) -> tuple[int, int]:
    s = staves[i]
    sp = s["spacing"]
    top = int(s["bottom"] + BAND_TOP_SPACES * sp)
    floor = s["bottom"] + BAND_BOTTOM_SPACES * sp
    if i + 1 < len(staves):
        floor = min(floor, staves[i + 1]["top"] - 0.3 * sp)
    return top, int(floor)


def detect_hairpins(
    page_ink: np.ndarray,
    staves: list[dict],
    blanked_ink: np.ndarray | None = None,
) -> list[Hairpin]:
    """Find the hairpins on one page.

    `page_ink` is the RAW binary page — needed whole, because isolation is a
    property of a component's full extent. `blanked_ink` is the same page with
    the point detections erased; pass None to search the raw ink.

    `staves` is `[{"index", "top", "bottom", "spacing"}, ...]` top to bottom.
    """
    if not staves:
        return []
    search = page_ink if blanked_ink is None else blanked_ink
    _n, full_lab, full_stats, _c = cv2.connectedComponentsWithStats(page_ink, 8)

    out: list[Hairpin] = []
    order = sorted(range(len(staves)), key=lambda i: staves[i]["bottom"])
    ordered = [staves[i] for i in order]
    for i, s in enumerate(ordered):
        sp = float(s["spacing"])
        top, bot = _band_bounds(ordered, i)
        if bot - top < 4 or sp <= 0:
            continue
        band = search[top:bot, :]
        n, lab, stats, _c2 = cv2.connectedComponentsWithStats(band, 8)
        for k in range(1, n):
            x, y, w, h, _area = stats[k]
            if not (MIN_WIDTH_SPACES * sp <= w <= MAX_WIDTH_SPACES * sp):
                continue
            m = measure_component(((lab[y:y + h, x:x + w] == k).astype(np.uint8)) * 255, sp)
            if m is None:
                continue
            if m["open_spaces"] < MIN_OPEN_SPACES:
                continue
            if m["outline_rms_spaces"] > MAX_OUTLINE_RMS_SPACES:
                continue
            if not _is_isolated(full_lab, full_stats, x, top + y, w, h):
                continue
            out.append(Hairpin(
                staff_index=int(s["index"]), kind=str(m["kind"]),
                x=int(x), y=int(top + y), width=int(w), height=int(h),
                open_spaces=float(m["open_spaces"]),
                outline_rms_spaces=float(m["outline_rms_spaces"]),
            ))
    return out


def _is_isolated(full_lab, full_stats, x: int, y: int, w: int, h: int) -> bool:
    """Is this candidate's FULL-PAGE component only itself?

    ⚠️ A beam is always connected to something — its stems — and a hairpin is
    connected to nothing. Measured on the whole page rather than the band,
    because the band crop severs a beam from its stems and makes it look as
    isolated as a hairpin.
    """
    label = 0
    for yy in range(y, min(y + h, full_lab.shape[0])):
        for xx in range(x, min(x + w, full_lab.shape[1]), 3):
            if full_lab[yy, xx]:
                label = int(full_lab[yy, xx])
                break
        if label:
            break
    if not label:
        return False
    _x, _y, cw, ch, _a = full_stats[label]
    return (cw * ch) / max(1.0, float(w * h)) < MAX_COMPONENT_GROWTH


def blank_point_detections(
    ink: np.ndarray, boxes: Iterable[tuple[float, float, float, float, str]],
    spacing: float,
) -> np.ndarray:
    """Erase the detections, but NOT the spans.

    ⚠️ A slur, tie or beam box is mostly the PAPER its arc crosses, so blanking
    it erases whatever stands under it — in this band, exactly the hairpins.
    `direction_text` documents the same rule and avoids the same trap.
    """
    out = ink.copy()
    for x, y, w, h, cls in boxes:
        if cls in SPAN_CLASSES or w > MAX_BLANK_WIDTH_SPACES * spacing:
            continue
        out[max(0, int(y)):int(y + h) + 1, max(0, int(x)):int(x + w) + 1] = 0
    return out


def staves_from_result(result: dict[str, Any], page_index: int = 0) -> list[dict]:
    """`staves` in this module's shape, from a transcription result."""
    out = []
    for system in result["pages"][page_index].get("systems", []):
        for staff in system.get("staves", []):
            g = staff.get("staff_geometry") or {}
            ys = g.get("line_ys_page") or []
            if len(ys) >= 5 and g.get("line_spacing_px"):
                out.append({"index": staff.get("staff_index"),
                            "top": float(min(ys)), "bottom": float(max(ys)),
                            "spacing": float(g["line_spacing_px"])})
    return sorted(out, key=lambda s: s["bottom"])
