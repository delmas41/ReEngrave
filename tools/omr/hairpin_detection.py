"""Hairpins, read by classical CV in the band below each staff.

THE DETECTOR BARELY SEES THEM ON SCANS. Over eleven scanned pages with
hand-verified windows it finds **1 hairpin against 99** the truth carries — and
over the widened twenty-row gate, **3 against 192** — while
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

⚠️ **THAT GATE WAS RE-RUN BEFORE THE CALL SITE WAS ADDED (2026-09-07) AND IT
REPRODUCES** — a measurement for code nothing imports is exactly the kind this
repo has been bitten by, so it was not taken on trust.
`benchmarks/omr-hairpin-cv-2026-09/probe/reproduce_gate.py`, over the same
eleven rows on the current `graft09` fixtures, truth 99 hairpins:

    ink recipe                           found   FPs on the 6 blank pages
    gray < 180, fresh 600 dpi render        62   3, silent on 5 of 6
    PageImage.binary (Sauvola, deskewed)    57   2, silent on 5 of 6

Same categorical result on both, and the same weak row (Mahler 5 p3, 2 against
17). ⚠️ **The near-miss needs no excuse: 59 lies BETWEEN the two arms measured
here.** 57 and 62 are the same code on the same pages differing only in how the
page was binarized, so the original figure is inside the spread the ink recipe
alone produces. An earlier draft reached for changed weights to explain a gap
that is not outside the noise.

**The pipeline reads the second recipe**, because `PageImage.binary` is already
rendered, already deskewed, and already the frame every `bbox_page_px` on the
page dict is in. It yields five fewer and invents one fewer; on a metric that
charges an invented direction exactly what it charges a missed one, that trade
is close to neutral and the shared frame is not.
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

#: A page whose "ink" exceeds this after inversion was handed the wrong
#: polarity. Not a tuned number — a printed orchestral page is a few percent
#: ink, and the ceiling only has to sit below "most of the page".
_INK_FRACTION_CEILING = 0.5

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


# ---------------------------------------------------------------------------
# Wiring: hairpins found on the page, attached to the cells that carry them
# ---------------------------------------------------------------------------

#: What a CV hairpin is called downstream. The same two classes the detector
#: uses, so the exporter needs no new case — `export.measure_wedges` already
#: reads them.
CLASS_FOR_KIND = {
    "crescendo": "dynamicCrescendoHairpin",
    "diminuendo": "dynamicDiminuendoHairpin",
}

#: A CV reading is not a probability, and pretending otherwise would let a
#: confidence filter somewhere downstream silently drop it. Stated once, high
#: enough to survive every threshold in the pipeline, and flagged as synthetic
#: by `detector: "cv"` on the detection itself.
CV_CONFIDENCE = 0.99


def _measure_for(staff: dict[str, Any], page_x: float) -> dict[str, Any] | None:
    """The measure of this staff whose x-range contains `page_x`.

    ⚠️ `bbox_page_px` is `(x0, y0, x1, y1)` — CORNERS, not `(x, y, w, h)`
    (`types.MeasureCell`, and every consumer in `transcribe` takes the width as
    `[2] - [0]`). This read it as a width and tested `x0 <= x <= x0 + x1`, which
    inflates every measure's right edge past the page and hands the hairpin to
    the first measure in iteration order rather than the containing one.
    Measured over the eleven scored scan pages: **41 of 59 hairpins landed in
    the wrong measure**, and on Dvorak 9 p5 all four went to m2 — a bar that
    genuinely rests — when they belong in m6 and m7, which carry 5 and 9
    noteheads.

    That is where FINDINGS.md's "the residue is the same bug a fourth time"
    came from: half of the eight hairpins that never became wedges were not lost
    by the export at all, they were filed under a resting bar by this line. The
    fixture that should have caught it could not — it put the first measure at
    x0 = 0, where `x0 + x1 == x1` and the two conventions agree.
    """
    best = None
    for meas in staff.get("measures", []):
        box = meas.get("bbox_page_px") or [0, 0, 0, 0]
        if box[0] <= page_x <= box[2]:
            return meas
        if best is None or abs(box[0] - page_x) < abs(
                (best.get("bbox_page_px") or [0])[0] - page_x):
            best = meas
    return best


def attach_to_page(page: dict[str, Any], page_ink: np.ndarray,
                   blanked_ink: np.ndarray | None = None) -> int:
    """Find the hairpins on one built page dict and add them as detections.

    Returns how many were added. A hairpin already read by the detector at the
    same place is not added twice.

    ⚠️ The hairpin is attributed to the staff whose BAND it stands in, which is
    the whole point of searching per staff — `_dedupe_cross_staff_detections`
    never sees a contest to resolve. On the engraved corpus that arbitration has
    to rescue 3 of Mahler 5's 4 hairpins from the staff below their own.
    """
    staves_meta = []
    by_index: dict[int, dict[str, Any]] = {}
    for system in page.get("systems", []):
        for staff in system.get("staves", []):
            g = staff.get("staff_geometry") or {}
            ys = g.get("line_ys_page") or []
            if len(ys) >= 5 and g.get("line_spacing_px"):
                staves_meta.append({"index": staff.get("staff_index"),
                                    "top": float(min(ys)), "bottom": float(max(ys)),
                                    "spacing": float(g["line_spacing_px"])})
                by_index[staff.get("staff_index")] = staff
    if not staves_meta:
        return 0

    added = 0
    for hp in detect_hairpins(page_ink, staves_meta, blanked_ink):
        staff = by_index.get(hp.staff_index)
        if staff is None:
            continue
        meas = _measure_for(staff, hp.x)
        if meas is None:
            continue
        box = meas.get("bbox_page_px") or [0, 0, 0, 0]
        up = float(meas.get("upscale_factor") or 1.0) or 1.0
        cls = CLASS_FOR_KIND[hp.kind]
        # Already read by the detector here? Do not double it.
        if any((d.get("class") or "") == cls
               and abs((d.get("bbox_page") or [1e9])[0] - hp.x) < hp.width
               for d in meas.get("detections", [])):
            continue
        meas.setdefault("detections", []).append({
            "class": cls,
            "category": "dynamic",
            "bbox": [int(round((hp.x - box[0]) * up)),
                     int(round((hp.y - box[1]) * up)),
                     int(round(hp.width * up)), int(round(hp.height * up))],
            "bbox_page": [hp.x, hp.y, hp.width, hp.height],
            "confidence": CV_CONFIDENCE,
            "pitch": None,
            "detector": "cv",
        })
        meas["n_detections"] = len(meas["detections"])
        added += 1
    return added


def _detection_boxes(page: dict[str, Any]) -> list[tuple[float, float, float, float, str]]:
    """Every detection on a built page dict, as a PAGE-pixel box.

    ⚠️ A DETECTION's `bbox` is canonical-cell `[x, y, w, h]` and its cell's
    `bbox_page_px` is `(x0, y0, x1, y1)` — CORNERS. Only the corner ORIGIN is
    used here, which is the half both conventions agree on; `_measure_for`
    documents what reading the far corner as a width cost.
    """
    out: list[tuple[float, float, float, float, str]] = []
    for system in page.get("systems", []):
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
                                b[2] / up, b[3] / up, det.get("class") or ""))
    return out


def read_hairpins_for_page(page: dict[str, Any], page_binary: np.ndarray) -> int:
    """The whole rung, on one built page dict: blank, search, attach.

    ⚠️ `page_binary` is the pipeline's own `types.PageImage.binary` — **0 = ink,
    255 = paper** — and the inversion to this module's ink-non-zero convention
    happens HERE rather than at the call site. Both polarities live in this
    repo, and getting one wrong does not crash: it searches the PAPER, finds
    nothing, and reports a clean zero. A silent null is the one result this
    project treats as worse than a loud failure, so the polarity is asserted
    (`_INK_FRACTION_CEILING`) instead of trusted.

    The image is the WHOLE page — not a band, not a cell, and not the
    staff-line-erased variant the other CV rungs take. All three are deliberate
    and each is measured:

      * whole page, because ISOLATION is a property of a component's full
        extent and a crop severs a beam from the stems that betray it;
      * staff lines INTACT — and this one is an exception to the rule the rest
        of the CV rungs follow, so it is argued rather than asserted.
        `remove_staff_lines` erases per CELL because for `line_detection` and
        `staff_header` the lines are NOISE. Here they are SIGNAL: they are a
        large part of what makes an attached component big, which is the whole
        content of the isolation test. Two reasons, both narrower than the
        first draft of this docstring claimed:

          1. **Calibration.** The 1.0x-against-3248x growth gap, and
             `MAX_COMPONENT_GROWTH` read off it, were measured on lines-intact
             ink. A constant keeps its meaning on the substrate it was fitted
             to and loses it on any other, whether or not the other still
             works.
          2. **Erased ink is unpredictable in exactly the way this gate is
             sensitive to.** Measured elsewhere in this repo, erasing staff
             lines before YOLO took `beam` detections 46 -> 105 on staff-line
             RESIDUE. A gate keyed on connectivity is precisely what residue
             perturbs — it manufactures the bridges the test reads.

        ⚠️ **What is NOT claimed: that erasure breaks the test.** An earlier
        draft here said the constant "no longer separates anything", and that
        overclaims. Measured on a synthetic page (a beam with two stems
        crossing a staff, an isolated hairpin below, this module's own
        `_is_isolated` arithmetic): erasure cuts the beam's growth from
        **130.7x to 13.75x** — a 9.5x collapse of the margin that still leaves
        it far above the 2.0 threshold, because the STEMS alone keep the beam
        attached. So the direction is real and the categorical claim is not
        demonstrated. ⚠️ That case is n=1 and hand-built, so it does not show
        erasure is SAFE either: **nobody has run the erased arm on a real
        page.** `probe/reproduce_gate.py` compares two ink RECIPES and both are
        lines-intact.

    Returns how many hairpins were added as detections.

    ⚠️ **A hairpin added here is not a `<wedge>` exported.** Measured end to end
    over the eleven scan rows, 2026-09-07: 56 added, 112 wedge tags exported —
    but one of those 55 pairs is DEGENERATE, a crescendo and its stop emitted
    back to back with no note between them, on Mahler 5 p3. That is export-side
    (an eventless bar taking the directions-only path while the anchor pair
    lands in the next bar), not this module's, and it is recorded here because
    this is where anyone reading a wedge count will start.
    """
    spacings = sorted(s["spacing"] for s in _staff_meta(page))
    if not spacings:
        return 0
    page_ink = (page_binary == 0).astype(np.uint8) * 255
    ink_fraction = float(np.count_nonzero(page_ink)) / max(1, page_ink.size)
    if ink_fraction > _INK_FRACTION_CEILING:
        raise ValueError(
            f"page_binary looks inverted: {ink_fraction:.2f} of the page is ink "
            f"after 0=ink inversion. Pass `PageImage.binary` (0=ink), not an "
            f"ink-non-zero mask. The densest page measured here is far under "
            f"{_INK_FRACTION_CEILING}.")
    sp_med = spacings[len(spacings) // 2]
    blanked = blank_point_detections(page_ink, _detection_boxes(page), sp_med)
    return attach_to_page(page, page_ink, blanked)


def _staff_meta(page: dict[str, Any]) -> list[dict[str, Any]]:
    """`{"index", "top", "bottom", "spacing"}` per staff of a built page dict."""
    out = []
    for system in page.get("systems", []):
        for staff in system.get("staves", []):
            g = staff.get("staff_geometry") or {}
            ys = g.get("line_ys_page") or []
            if len(ys) >= 5 and g.get("line_spacing_px"):
                out.append({"index": staff.get("staff_index"),
                            "top": float(min(ys)), "bottom": float(max(ys)),
                            "spacing": float(g["line_spacing_px"])})
    return sorted(out, key=lambda s: s["bottom"])
