"""ROADMAP 2.274 step 1 -- ARCS READ FROM THE PAGE'S INK, ONE RUN EACH, FILED AND NOT YET READ (STAGED GATHER; decides nothing).

    flag `OMR_PAGE_ARCS`, default OFF (allow-list). Files `Q.PAGE_ARC` rows only; NOTHING READS THEM. The exported file is byte-identical with it ON.

WHY (docs/plan-2026-11-06-page-ink-arcs.md). On STAGED an arc's identity is a detector box, and the detector runs per cell, barline to barline, so everything
after it inherits the cut. page-facts (2026-10-30): "a detector box in a cell is only a witness to it, never the mark". This reader starts from the INK.

WHAT IT READS. The page raster the page map is built on (`page_strokes.Assembly.canvas`: each staff's own erased band + the page raster outside, the tilted
barline columns carved) -- the staff lines and barlines are claimed first. CLAIM ORDER (CLAUDE §3): what claims before an arc or is not arc ink is blanked --
the page claims of brackets / clef / key / meter / leading column / words (`Q.CLAIMED_AREA` AREAS, which take the ink COMPONENTS wholly inside them, as
`stroke_owner._areas` does, never the rectangle) and every compact detector mark (heads, ledgers, rests, accidentals, flags, dots, dynamics, fermatas,
articulations ...: their box). Beam and hairpin boxes are NOT blanked as rectangles (a false `beam` box over a slur took half of one). Then:
  1. THIN COLUMN RUNS at ~16 px/sp: a vertical ink run taller than `RUN_MAX_SP` (a stem, a head, a beam end-on) is not arc ink and is a HOLE;
  2. TRACK left to right on each track's own recent slope, bridging a hole up to `GAP_SP` (a carved rule, a blanked stem or head) -- so a run CROSSES a
     barline, a stem and a head without being cut; one column run feeds one track;
  3. SPLIT a track at a bridged hole where its slope turns from one sign to the other (a V at a claimed head: two arcs meeting);
  4. KEEP a track that is long enough, thin, inked over most of its span, smooth (off its own running mean), bowed ONE way, not a stub on a staff-line row,
     and not (longer than 4 sp AND straighter than 0.1 sp: a hairpin leg, a beam or a line).
It reads NO cell and needs no detector pass. Cost: about a second a page.

WHAT IT FILES (`Q.PAGE_ARC`, one row per run, on the page's subject). `value` = `run` (read from the ink alone) | `seeded` (no run existed under a
DETECTOR arc box that a bounded local read of its ink found: the box SEEDED it, so it is not ink-first; counted apart) | `census` (one per page: counts,
seconds, peak memory). `detail`: `ordinal`, `bbox_page_px`, `points` (page px, about one per quarter space), `width_spaces`, `sagitta_spaces` (signed:
positive = the middle is LOWER than the chord), `thickness_spaces`, `ends` ([[x, y, tangent_deg], [x, y, tangent_deg]],
left then right), `witnesses` (glyph keys of the detector slur/tie boxes it overlaps, a witness only), `staff` ([system, staff]).
A detector arc box no run witnesses is a `Q.PAGE_ARC` row of value `box_without_run` (its glyph key, box, and `seeded` outcome) so both counts are in the record.

CONVENTIONS ASSUMED / WHAT WOULD FALSIFY / NOT CONFIRMED: the run parameters were tuned four times on Brahms p0 (in-sample) and are NOT confirmed beyond it;
step 1 measures them on other pages (benchmarks/omr-arc-binding-2026-10/page-ink-2026-11/step1/FINDINGS-step1.md). They are lengths in staff spaces
(a convention of the print, not a number fitted to a plate) except the cut-offs named below, which are measurements. Sean's tiles are the judge.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_PAGE_ARCS"

TARGET_SP_PX = 16.0
RUN_MAX_SP = 0.62         # a column run thicker than this is not arc ink (arc middles ~0.15-0.35 sp; a steep arc end is cut off here)
TOL_SP = 0.30             # how far from the predicted centre the next run may lie
GAP_SP = 1.25             # the widest hole a track bridges (a carved rule ~0.2 sp, a blanked stem ~0.3 sp, a head box ~1.3 sp)
SLOPE_SP = 1.5            # the stretch of its own recent points a track predicts from
MIN_WIDTH_SP = 1.4
CROSS_CLASSES = ("dynamic", "fermata", "ornament", "trill", "ottava", "pedal", "tremolo", "articulation", "tuplet")     # compact marks an arc may touch without ending there
EXT_ALL = 1               # the extension runs through every claim (a head too): an arc's end is carried on to the note it stops at
EXT_MIN_SP = 1.0         # a run shorter than this is not extended
EXT_TOL_SP = 0.2          # the extension takes ink this close to the end's tangent
EXT_FIT_SP = 4.0          # the extension follows the quadratic fitted to this much of the run's end
EXT_THICK = 1.5           # ... no thicker than this many times the run's own median thickness (+1 px)
EXT_MAX_SP = 4.0          # ... for at most this long a stretch
LINE_GAP_SP = 0.25        # the widest erased staff-line band an arc's two halves are joined across
CLAIM_GAP_SP = 6.0        # the longest stretch a track waits inside a blanked region (a dynamic, a word, a head cluster) on its own slope
CLAIM_TOL_PER_SP = 0.05   # the tolerance for the ink that comes out grows this much per space of blanked stretch crossed
MIN_OWN_INKED = 0.45      # inked columns that are the run's own (not counted as claimed by another mark) / span
MIN_INKED = 0.6           # inked columns / span
MAX_CHORD_DEG = 40.0
JAG_SHORT_SP = 0.035      # a run under two smoothing windows is measured against its own quadratic, which a clean arc follows to 0.01-0.025 and a head's rim or a letter does not (0.04-0.065, develop pages)
SHORT_RUN_SP = 4.0
SHORT_THICK_SP = 0.5      # a short run this thick at its middle is a head's base or a beam stub (develop pages: 1 under a detector arc box, 14 under none)
JAG_SP = 0.08             # rms off the 1-sp running mean
HOLE_MIN_SP = 0.1         # a gap between two inked columns at least this wide is a bridged hole
HOLE_PAD_SP = 0.3         # the jag is not measured this close to a hole
CUSP_SP = 0.75            # the stretch each side of a hole the slope is read over
CUSP_GAP_SP = 0.3         # a bridged hole at least this wide (a blanked head is ~1.2 sp)
HUG_SP = 0.3             # a run's body this close to a compact claimed mark's box is its rim
FLAT_MAX_SP = 4.0          # a run this narrow ...
FLAT_SAG_SP = 0.12         # ... that bows less than this is a ledger line / head base / beam stub
HEADER_OWNERS = ("leading_column", "bracket", "clef", "key_signature", "meter")   # claimed before an arc: no arc lies along them
DOT_MIN_SP = 0.2
DOT_MAX_SP = 0.75
FERMATA_MAX_SP = 4.5      # a fermata's hump is at most this wide
HUG_SHARE = 0.5          # (share of the body)
CORNER_TURN = 0.35        # the change of slope that makes a corner where two touching arcs meet
BOW_SP = 4.0              # the stretch each side of a hole the pieces' own bow is read over
CUSP_SLOPE = 0.15         # both sides at least this steep, opposite signs
LINE_STUB_SP = 0.14       # a run whose centre sits this close to a staff line row over most of its length is the eraser's leftover
STRAIGHT_SAG_SP = 0.10    # a run straighter than this ...
MIN_THICK_SP = 0.10       # median thickness under this is a staff line's residue (a staff line is ~0.1 sp)
STRAIGHT_REL = 0.02       # a run whose bow is under this share of its width is a line: a slur's bow grows with its length (measured: lines 0.005, the flattest tie 0.05)
STRAIGHT_LONG_REL = 0.047  # a run over STRAIGHT_MAX_SP whose bow is under this share of its width is a line (round-1 measurement on 5 pages: 12 lines at 0.023-0.045, the flattest real arc 0.050; confirmed on 4 fresh pages)
STRAIGHT_MAX_SP = 4.0     # ... and longer than this is a line, not an arc
WITNESS_SHARE = 0.5       # a detector arc box witnesses a run when the run covers this share of the box's width inside the box (grown 0.5 sp)
POINT_STEP_SP = 0.25      # one filed point per this many staff spaces
LINE_WIN_SP = 2.0         # r3: the line's own thickness is the median over this much each side (never above LINE_THICK_CAP x its page median)
LINE_THICK_CAP = 1.25
LINE_EXCESS_SP = 0.12     # r3: a raw run on a staff line at least this much thicker than the line's own thickness there is an arc on the line
ARC_NOMINAL_SP = 0.25     # r3: an arc's depth when it leaves the line on one side only (the rest lies in the line)
LINK = 1                  # r3: join fragments of one arc that a joint curve fit and the raw ink under the gap explain
LINK_GAP_SP = 6.0         # the widest gap two fragments are joined across
LINK_MIN_SP = 0.6         # the shortest fragment that is joined
LINK_RES_SP = 0.08        # rms of the joint fit over both fragments
LINK_DEV_SP = 0.25        # the largest deviation of either fragment's points from the joint fit
LINK_SUPPORT = 0.7        # the share of the gap's columns that carry raw ink within LINK_SUP_SP of the fit
LINK_SUP_SP = 0.3
LINK_YNEAR_SP = 2.5       # fragments whose facing ends lie further apart than this are not tried
THICK_PASS = 1            # r3: a heavy slur's middle (thicker than RUN_MAX_SP) is read as a thick run, never a hole
THICK_MAX_SP = 1.3        # ... up to this thick (a head is as tall, and no wider than ~1.3 sp: a thick track must be longer than THICK_MIN_SP)
THICK_MIN_SP = 3.0
THICK_SHARE = 0.25        # ... and at least this share of its columns thicker than RUN_MAX_SP
LEDGER_THIN = 0           # r3: a ledger box does not claim a column whose ink is much thicker than the box
LEDGER_THIN_PX = 3
TRIM_LINE = 0             # r3: an arc's end that runs along a staff line row is the line's, not the arc's
TRIM_MIN_SP = 1.0
LINE_RESIDUE = 1          # r3: ink wholly inside a staff line's own band is the line's
ARC_IN_WORD = 1           # r3: an arc-shaped component inside a word's rectangle is not the word's
ARC_COMP_MIN_SP = 3.0
RAGGED_TRIM = 1           # r3: cut the junction points off an arc fused with a stem / flag / beam, and judge what is left
RAGGED_DEV_SP = 0.2
HEADER_INK = 1            # r3: a run hugs a header claim by the claimed INK, not the claim's rectangle
HUG_EXEMPT = ("accidental",)   # r3: an arc passes over the top of a tall accidental's box; a sharp has no rim an arc could be mistaken for
LINK_PLAIN_GAP_SP = 1.3   # a gap this short needs only the raw ink under it (a carved rule, a stem); a longer one must lie in what claims / hides ink
LINK_EXPL_SHARE = 0.8
LINK_QUAD_SP = 8.0        # the joint fit is a quadratic up to this wide, a quartic beyond
LINK_BOW_REL = 0.03       # the joint curve's bow, as a share of its width, at least (the flattest real tie measured 0.05, lines 0.005)
TAPER_SLUR = 1            # r4: a long flat slur is a lens: thinner at both ends than in the middle. A run over STRAIGHT_MAX_SP that bows at least STRAIGHT_REL of its width and tapers is an arc, not a line
TAPER_MID_MAX_SP = 0.5    # ... whose middle is no thicker than this (a beam is ~0.6-0.9 sp, a staff line ~0.1; develop pages: real flat slurs 0.25-0.5)
TAPER_END_RATIO = 0.9     # ... and whose end thickness (mean of the outer 12% each side) is at most this share of the mean of the middle 30% (develop pages: 31 of 41 refused-straight real slurs; 5 of 127 non-arc B runs after the thickness limit)
FIT_MAX_SP = 5.0          # ... on a run no wider than this (a longer run that joins an arc to a head or a stem is judged by its jag; 2 real arcs were lost to this on long runs)
FIT_RMS_SP = 0.12         # r4: a run that stays further than this (rms) off its own smooth fit (quadratic, quartic over 8 sp) is a zig-zag through letters, not an arc ("piu f" read as a run)
GLYPH_COMP = 1            # r4: a small ink component that no detector mark overlaps and that is not one thin bowed stroke is a glyph (a digit, a letter, a rehearsal frame): page marks claim before an arc
GLYPH_MAX_W_SP = 5.5
GLYPH_MAX_H_SP = 4.5
GLYPH_MIN_H_SP = 0.9      # shorter than this it can be a tie's piece or a dash
ERASED_EXT = 0            # r4 EXPERIMENT, OFF (tried and removed, see FINDINGS r4; delete when the round closes): an arc's thin tail can lie INSIDE a staff line's erased band (Sean's tiles 6 and 11 of round 3: the tail left of the line was cut off); the end extension may cross an erased band of up to this many spaces and take the ink that comes out on the end's own curve
ERASED_GAP_SP = 2.5
ERASED_TOL_SP = 0.35
ERASED_FIT_SP = 1.5
ERASED_MIN_SLOPE = 0.1
WIDE_BOX = 1              # r4: a detector box of a class that is one note-space wide (accidental, head, dot, flag) that is wider than WIDE_BOX_SP is not that mark (round-2 tile 9: a 4-space "accidentalFlat" box lay over a slur and blanked it): it blanks nothing
WIDE_BOX_SP = 2.5
WIDE_BOX_CLASSES = ("accidental", "notehead", "augmentationDot", "flag")
WEDGE = 1                # r4: a hairpin's leg is thick at one end and a point at the other; a slur is thin at BOTH ends. An ink-only run whose thickness at its two ends differs by more than this ratio is a wedge
WEDGE_RATIO = 1.8
BEAM_RAW = 1              # r4: a run that lies on RAW ink (nothing erased or blanked) taller than BEAM_RAW_SP in at least BEAM_RAW_SHARE of its points and that does not thin toward its ends (end / middle >= BEAM_RAW_ENDS) is a beam's edge piece: the beam owns that ink
BEAM_RAW_SP = 0.45        # (develop pages, 5 pages: 16 of 109 NEW runs and 0 of 553 witnessed runs)
BEAM_RAW_SHARE = 0.9
BEAM_RAW_ENDS = 0.85
BEAM_STEM_NEAR_SP = 0.8   # (a stem within this of the run's end)
BEAM_STEM_SP = 2.0        # ... and standing on stems: raw ink at least this tall at both ends of the run
BEAM_LIKE_SP = 0.5        # r3: a run this thick at its middle that does not taper (end / middle thickness above BEAM_TAPER) is a beam
BEAM_TAPER = 0.75
LINE_WAIT = 0             # r3 experiment: a track waits through a line band
LINE_PAD_SP = 0.1         # r3: a line's band for the wait-through

NOT_ARC_SKIP = ("staff", "slur", "tie", "brace", "bracket", "barline", "arpeggiato", "systemicBarline")
CLAIM_OWNERS = ("meter", "clef", "key_signature", "leading_column", "word", "bracket")


def enabled() -> bool:
    """`OMR_PAGE_ARCS` (ROADMAP 2.274 step 1), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    if os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on"):
        return True
    from . import page_arc_bind as _pab
    return _pab.write_enabled()          # step 2 (`OMR_PAGE_ARC_WRITE`) reads these rows: it turns the reader on


# ───────────────────────────── 1. the rows the reader needs (any source) ─────────────────────────────

def _cls_of(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value.replace("'", '"'))
        except ValueError:
            return value
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return str(value)


def inputs_from_rows(rows: Sequence[Tuple[str, str, Any, Dict[str, Any]]]
                     ) -> Tuple[List[Tuple[str, List[float]]], List[Tuple[str, List[float]]], List[Dict[str, Any]]]:
    """`(blank_boxes, claim_areas, arc_boxes)` from `(quantity, subject, value, detail)` rows of ONE page: `blank_boxes` = `(class, [x0, y0, x1, y1])` of every
    detector box that is neither an arc nor a staff / brace / barline box nor a long stroke (beam / hairpin); `claim_areas` = `(owner, rect)` of the page
    claims that are not the arc's own; `arc_boxes` = the detector's slur / tie boxes `{subject, cls, box}`."""
    boxes: List[Tuple[str, List[float]]] = []
    areas: List[Tuple[str, List[float]]] = []
    arc_boxes: List[Dict[str, Any]] = []
    for q, subject, value, det in rows:
        det = det or {}
        if q == "glyph_box":
            cls = _cls_of(value)
            bb = det.get("bbox_page_px")
            if not bb:
                continue
            if cls in ("slur", "tie"):
                arc_boxes.append(dict(subject=subject, cls=cls, box=[float(v) for v in bb]))
            elif "airpin" in cls:
                areas.append(("hairpin", [float(v) for v in bb]))      # a hairpin claims before an arc: its ink COMPONENTS inside the box, never the rectangle
            elif cls.startswith("beam"):
                continue          # claimed AFTER arcs (CLAUDE §3); a false beam box over a slur took half of one (r3: a beam box is no veto either: 22 real slurs on Brahms p22 lie under one)
            elif not any(cls.startswith(k) for k in NOT_ARC_SKIP):
                boxes.append((cls, [float(v) for v in bb]))
        elif q == "claimed_area" and det.get("owner") in CLAIM_OWNERS and det.get("unit") == "area":
            v = value
            if isinstance(v, str):
                v = json.loads(v)
            areas.append((det["owner"], [float(t) for t in v]))
        elif q == "claimed_area" and det.get("owner") == "hairpin" and det.get("bbox_page_px"):
            areas.append(("hairpin", [float(t) for t in det["bbox_page_px"]]))
    return boxes, areas, arc_boxes


# ───────────────────────────── 2. the run reader (pure; page raster in, runs out) ─────────────────────────────

def _column_runs(ink: np.ndarray, max_run: int, line_rows: Optional[np.ndarray] = None, line_gap: int = 0) -> List[List[Tuple[int, int]]]:
    """Per column: the (top, bottom) ink runs no taller than `max_run`. Two runs of one column that the page's own staff-line eraser parted (the gap lies
    wholly on a staff-line row, at most `line_gap` rows) are ONE run: a line crossing an arc is a crossing, not an end (ROADMAP 2.274 r2)."""
    H, W = ink.shape
    pad = np.zeros((H + 2, W), np.int8)
    pad[1:-1] = ink
    d = np.diff(pad, axis=0)
    out = []
    for x in range(W):
        starts = np.flatnonzero(d[:, x] == 1)
        ends = np.flatnonzero(d[:, x] == -1)
        runs = [(int(a), int(b)) for a, b in zip(starts, ends)]
        if line_rows is not None and len(runs) > 1:
            merged = [runs[0]]
            for a, b in runs[1:]:
                pa, pb = merged[-1]
                if 0 < a - pb <= line_gap and line_rows[pb:a].all():
                    merged[-1] = (pa, b)
                else:
                    merged.append((a, b))
            runs = merged
        out.append([(a, b) for a, b in runs if b - a <= max_run])
    return out


def _track(runs: List[List[Tuple[int, int]]], sp: float, W: int, blank: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
    """Tracks left to right. A track whose predicted path (its own recent slope) runs INTO a blanked region (a mark that claims before an arc: a dynamic, a
    word, a head, a flag, whatever box the detector drew) waits there up to `CLAIM_GAP_SP` and takes the first ink that comes out on its own slope: a claimed
    mark claims its own ink pixels, so the arc continues through it (ROADMAP 2.274 r2; the rectangle used to cut it). The columns it waited in are counted
    (`claimed`) so that a stretch another mark holds is not read as a run with no ink."""
    tol, gap, look = TOL_SP * sp, int(round(GAP_SP * sp)), SLOPE_SP * sp
    cgap = int(round(CLAIM_GAP_SP * sp))
    rad = max(1, int(round(0.15 * sp)))
    H = blank.shape[0] if blank is not None else 0
    active: List[Dict[str, Any]] = []
    done: List[Dict[str, Any]] = []
    for x in range(W):
        cand = [((a + b - 1) / 2.0, b - a) for a, b in runs[x]]
        preds = []
        for t in active:
            pts = t["pts"]
            lx, ly = pts[-1][0], pts[-1][1]
            k = len(pts) - 1
            while k > 0 and lx - pts[k - 1][0] <= look:
                k -= 1
            slope = (ly - pts[k][1]) / float(lx - pts[k][0]) if lx - pts[k][0] >= 3 else 0.0
            preds.append(ly + slope * (x - lx))
        pairs = []
        for ti, py in enumerate(preds):
            lx = active[ti]["pts"][-1][0]
            tol_t = tol + (CLAIM_TOL_PER_SP * (x - lx) / sp if x - lx > gap else 0.0) * sp
            for ci, (cy, th) in enumerate(cand):
                dy = abs(cy - py)
                if dy <= tol_t + 0.5 * th:
                    pairs.append((dy, ti, ci))
        pairs.sort()
        used_t, used_c = set(), set()
        for dy, ti, ci in pairs:
            if ti in used_t or ci in used_c:
                continue
            used_t.add(ti)
            used_c.add(ci)
            t = active[ti]
            if t.get("wait"):
                t.setdefault("gaps", []).append((t["pts"][-1][0], x))
                t["wait"] = 0
            t["pts"].append((x, cand[ci][0], cand[ci][1]))
        nxt = []
        for ti, t in enumerate(active):
            if ti in used_t:
                nxt.append(t)
                continue
            lx = t["pts"][-1][0]
            in_blank = False
            if blank is not None and x - lx <= cgap:
                yy = int(round(preds[ti]))
                in_blank = 0 <= yy < H and bool(blank[max(0, yy - rad):min(H, yy + rad + 1), x].any())
            if in_blank:
                t["wait"] = t.get("wait", 0) + 1
            if x - lx <= gap or in_blank:
                nxt.append(t)
            else:
                done.append(t)
        for ci, (cy, th) in enumerate(cand):
            if ci not in used_c:
                nxt.append(dict(pts=[(x, cy, th)]))
        active = nxt
    return done + active


def _extend_through_claims(t: Dict[str, Any], raw_cols: List[List[Tuple[int, int]]], blank: np.ndarray, sp: float, erased: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """An arc that touches a mark that claims before it (a dynamic's foot, a word, a head) has its ink inside that mark's blanked area, where no track can
    start. A run's own ink continues there on its own slope: from each end, follow the thin ink of the RAW page (claims not blanked) that lies on the
    end's tangent, as long as the path runs inside blanked area and the ink is no thicker than the run's own. A claimed mark claims its own pixels, not
    the arc's (ROADMAP 2.274 r2; Sean's claim order: a later reader marks claimed ink, never takes it -- and never loses its own to a claim by contact)."""
    p = list(t["pts"])
    if len(p) < 6 or (p[-1][0] - p[0][0]) < EXT_MIN_SP * sp:
        return t
    W = len(raw_cols)
    H = blank.shape[0]
    tol, gap, rad = EXT_TOL_SP * sp, int(round(GAP_SP * sp)), max(1, int(round(0.15 * sp)))
    max_th = EXT_THICK * float(np.median([q[2] for q in p])) + 1.0
    limit = int(round(EXT_MAX_SP * sp))
    fit_w = EXT_FIT_SP * sp
    out = {"left": [], "right": []}
    egaps: List[Tuple[int, int]] = []
    for side, step in (("left", -1), ("right", 1)):
        seq = p if step == 1 else p[::-1]
        ex = np.array([q[0] for q in seq if abs(q[0] - seq[-1][0]) <= fit_w], float)
        ey = np.array([q[1] for q in seq if abs(q[0] - seq[-1][0]) <= fit_w], float)
        if len(ex) < 6:
            continue
        coef = np.polyfit(ex, ey, 2)        # the run's own curve over its last stretch: the extension may not wander off it (a dynamic's strokes lie close by)
        lx = seq[-1][0]
        new = []
        x = lx + step
        x0 = lx
        broken = False
        unexpl = 0
        blank_seen = False
        lin = None
        if erased is not None and ERASED_EXT:
            sel = [(q[0], q[1]) for q in seq if abs(q[0] - seq[-1][0]) <= ERASED_FIT_SP * sp]
            if len(sel) >= 4:
                lin = np.polyfit([a for a, _b in sel], [b for _a, b in sel], 1)
                if abs(float(lin[0])) < ERASED_MIN_SLOPE:
                    lin = None          # a flat end runs along the line it would cross: nothing to tell it from the line (and a beam's flat edge reached the next beam)
        while 0 <= x < W and abs(x - x0) <= limit:
            py = float(np.polyval(coef, x))
            yy = int(round(py))
            if not (0 <= yy < H):
                break
            in_blank = bool(blank[max(0, yy - rad):min(H, yy + rad + 1), x].any())
            on_tangent = False
            if lin is not None and not broken and not blank_seen:
                ty = int(round(float(np.polyval(lin, x))))
                on_tangent = 0 <= ty < H and not bool(blank[max(0, ty - rad):min(H, ty + rad + 1), x].any())      # the tangent's own path is open: the erased path reads it, the quadratic (which can curl into a neighbour's blanked area) is not asked
            if in_blank and not on_tangent:
                blank_seen = True
                best = None
                for (ra, rb) in raw_cols[x]:
                    cy, th = (ra + rb - 1) / 2.0, rb - ra
                    if th <= max_th and abs(cy - py) <= tol + 0.5 * th and (best is None or abs(cy - py) < abs(best[0] - py)):
                        best = (cy, th)
                if best is not None:
                    if abs(x - lx) > 1:
                        egaps.append((min(lx, x), max(lx, x)))      # columns skipped inside the claimed area are the other mark's, not a lack of ink
                    new.append((x, best[0], best[1]))
                    lx = x
                    blank_seen = False
            elif lin is not None and not (broken and False):
                ly_ = float(np.polyval(lin, x))          # the tail leaves on the end's own tangent (a line, never a quadratic carried 2 sp out)
                yl = int(round(ly_))
                r2 = max(rad, int(round(0.3 * sp)))
                expl = 0 <= yl < H and bool(erased[max(0, yl - r2):min(H, yl + r2 + 1), x].any())
                best = None
                for (ra, rb) in raw_cols[x]:
                    cy, th = (ra + rb - 1) / 2.0, rb - ra
                    if th <= max_th * 1.6 and abs(cy - ly_) <= ERASED_TOL_SP * sp + 0.5 * th and not bool(blank[max(0, int(cy) - rad):min(H, int(cy) + rad + 1), x].any()) \
                            and (best is None or abs(cy - ly_) < abs(best[0] - ly_)):
                        best = (cy, th)
                if best is not None and not broken:
                    if abs(x - lx) > 1:
                        egaps.append((min(lx, x), max(lx, x)))
                    new.append((x, best[0], best[1]))
                    lx = x
                    blank_seen = False
                elif best is None and not expl:
                    unexpl += 1
                    if unexpl > 0.4 * sp:
                        broken = True          # neither ink nor an erased band on the tangent for 0.4 sp: nothing hides the tail here
                if best is not None or expl:
                    unexpl = 0
            if abs(x - lx) > (int(round(ERASED_GAP_SP * sp)) if (lin is not None and not broken and not blank_seen) else gap):
                break
            x += step
        out[side] = new
    if not out["left"] and not out["right"]:
        return t
    return dict(pts=out["left"][::-1] + p + out["right"], gaps=list(t.get("gaps", [])) + egaps)


def _split_at_cusps(t: Dict[str, Any], sp: float) -> List[Dict[str, Any]]:
    """Two arcs that meet at a note chain into one track: across the blanked head between them (a bridged HOLE) or, where their ends touch, at a CORNER.
    An arc turns smoothly through ONE apex, with the turn in the sense of its own bow; where two arcs meet the pieces bow one way and the join turns the
    other way, in a V. Split there: at a bridged hole of at least `CUSP_GAP_SP`, or at a corner (a change of slope of at least `CORNER_TURN` between the
    space before and the space after) -- where the slope either side has opposite signs, each at least `CUSP_SLOPE` steep, and both pieces (each long
    enough to tell) bow against the turn. A piece too short to tell its bow is never cut."""
    p = t["pts"]
    if len(p) < 8:
        return [t]
    x = np.array([q[0] for q in p], float)
    y = np.array([q[1] for q in p], float)
    w = CUSP_SP * sp
    wb = BOW_SP * sp
    n = len(p)

    def turn_at(i: int, xl: float, xr: float) -> Optional[float]:
        lo = int(np.searchsorted(x, xl - w))
        hi = int(np.searchsorted(x, xr + w, side="right"))
        if i - lo < 3 or hi - i < 3:
            return None
        sl = np.polyfit(x[lo:i], y[lo:i], 1)[0]
        sr = np.polyfit(x[i:hi], y[i:hi], 1)[0]
        if sl * sr >= 0 or min(abs(sl), abs(sr)) < CUSP_SLOPE:
            return None
        lo2 = int(np.searchsorted(x, xl - wb))
        hi2 = int(np.searchsorted(x, xr + wb, side="right"))
        if i - lo2 < 8 or hi2 - i < 8:
            return None
        bl = np.polyfit(x[lo2:i], y[lo2:i], 2)[0]
        br = np.polyfit(x[i:hi2], y[i:hi2], 2)[0]
        turn = sr - sl
        if np.sign(bl) == np.sign(br) and np.sign(turn) != np.sign(bl):
            return float(abs(turn))
        return None

    holes = {i for i in range(1, n) if x[i] - x[i - 1] >= CUSP_GAP_SP * sp}
    cand: List[Tuple[int, float]] = []
    for i in sorted(holes):
        tn = turn_at(i, x[i - 1], x[i])
        if tn is not None:
            cand.append((i, 1e9))
    if n >= 16 and x[-1] - x[0] >= 2.5 * sp:
        run: List[Tuple[int, float]] = []
        for i in range(4, n - 3):
            if i in holes or (x[i] - x[i - 1]) >= CUSP_GAP_SP * sp:
                continue
            tn = turn_at(i, x[i], x[i])
            if tn is not None and tn >= CORNER_TURN:
                if run and i - run[-1][0] > 2:
                    cand.append(max(run, key=lambda c: c[1]))
                    run = []
                run.append((i, tn))
        if run:
            cand.append(max(run, key=lambda c: c[1]))
    cuts = sorted({c for c, _ in cand})
    if not cuts:
        return [t]
    out, a = [], 0
    gaps = t.get("gaps", [])
    for c in cuts + [n]:
        x0, x1 = p[a][0], p[c - 1][0]
        out.append(dict(pts=p[a:c], gaps=[g for g in gaps if g[0] >= x0 and g[1] <= x1]))
        a = c
    return out


def _link_fragments(tracks: List[Dict[str, Any]], sp: float, raw_b: np.ndarray, expl: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
    """ROADMAP 2.274 r3, THE ARC IS ONE INK RUN (Sean's process): fragments the tracker left where the arc touches other ink -- a staff line the eraser took a
    band out of, a carved barline, a stem or a head, a thick apex -- are joined when ONE smooth curve explains both (the joint quadratic, quartic over 8 sp,
    off by no more than `LINK_RES_SP` rms and `LINK_DEV_SP` at any point), the curve at the join is where the two ends face each other, and the RAW ink
    (nothing erased) lies along that curve under the gap in at least `LINK_SUPPORT` of its columns. Two arcs that meet at a note do not fit one curve (a V);
    two ties in a chain bow separately. Greedy by the smallest residual; a joined track can be joined again. Returns the joined tracks only (the fragments stay
    in the caller's list; it drops what a joined run covers). A joined track carries the gap in `gaps`, which the judge counts as explained, not missing."""
    frag = []
    for t in tracks:
        p = t["pts"]
        if len(p) >= 3 and (p[-1][0] - p[0][0]) >= LINK_MIN_SP * sp:
            frag.append(dict(t, _x=np.array([q[0] for q in p], float), _y=np.array([q[1] for q in p], float)))
    if len(frag) < 2:
        return []
    import heapq
    H, W = raw_b.shape
    gap_max, ynear = LINK_GAP_SP * sp, LINK_YNEAR_SP * sp
    r_sup = max(1, int(round(LINK_SUP_SP * sp)))

    def score(a: Dict[str, Any], b: Dict[str, Any]) -> Optional[float]:
        gx = b["_x"][0] - a["_x"][-1]
        if gx > gap_max or gx < -2 or abs(b["_y"][0] - a["_y"][-1]) > ynear:
            return None
        x = np.concatenate([a["_x"], b["_x"]])
        y = np.concatenate([a["_y"], b["_y"]])
        deg = 2 if (x.max() - x.min()) <= LINK_QUAD_SP * sp else 4
        if len(x) < deg + 3:
            return None
        c = np.polyfit(x, y, deg)
        res = y - np.polyval(c, x)
        rms = float(np.sqrt(np.mean(res ** 2)))
        if rms > LINK_RES_SP * sp or float(np.abs(res).max()) > LINK_DEV_SP * sp:
            return None
        xa, xb = float(x.min()), float(x.max())
        bow = abs(float(np.polyval(c, (xa + xb) / 2.0)) - (float(np.polyval(c, xa)) + float(np.polyval(c, xb))) / 2.0)
        if bow < LINK_BOW_REL * (xb - xa):
            return None          # two straight pieces on one line (a beam between its stems, a staff line) are one straight line, not an arc
        if gx > 2:
            gxs = np.arange(int(a["_x"][-1]) + 1, int(b["_x"][0]))
            gy = np.round(np.polyval(c, gxs)).astype(int)
            ok = 0
            for xx, yy in zip(gxs, gy):
                if 0 <= yy < H and 0 <= xx < W and raw_b[max(0, yy - r_sup):min(H, yy + r_sup + 1), xx].any():
                    ok += 1
            if ok < LINK_SUPPORT * len(gxs):
                return None
            if expl is not None and gx > LINK_PLAIN_GAP_SP * sp:
                # a long gap is the arc passing THROUGH something that claims or hides ink (a claimed mark, a staff line's band); a gap over open page or over
                # other ink (a beam, a stem) is not the same arc (runs fused with a beam or run on to the next group were the fakes of the first build)
                ex = sum(1 for xx, yy in zip(gxs, gy) if 0 <= yy < H and 0 <= xx < W and expl[max(0, yy - r_sup):min(H, yy + r_sup + 1), xx].any())
                if ex < LINK_EXPL_SHARE * len(gxs):
                    return None
        return max(0.0, gx) / sp + rms / sp      # the nearest fragment first (a joint fit with a far piece can have a smaller residual), then the better fit

    heap: List[Tuple[float, int, int]] = []
    order = sorted(range(len(frag)), key=lambda i: frag[i]["_x"][0])
    xs0 = [frag[i]["_x"][0] for i in order]
    import bisect
    for ai, i in enumerate(order):
        lim = bisect.bisect_right(xs0, frag[i]["_x"][-1] + gap_max)
        for j in order[ai + 1:lim]:
            sc = score(frag[i], frag[j])
            if sc is not None:
                heapq.heappush(heap, (sc, i, j))
    dead = set()
    made: List[Dict[str, Any]] = []
    while heap and len(made) < 4 * len(frag):
        _r, i, j = heapq.heappop(heap)
        if i in dead or j in dead:
            continue
        a, b = frag[i], frag[j]
        gaps = list(a.get("gaps", [])) + list(b.get("gaps", []))
        if b["_x"][0] - a["_x"][-1] > 2:
            gaps.append((int(a["_x"][-1]), int(b["_x"][0])))
        pts = list(a["pts"]) + list(b["pts"])
        m = dict(pts=pts, gaps=gaps, linked=True, _x=np.array([q[0] for q in pts], float), _y=np.array([q[1] for q in pts], float))
        dead.add(i)
        dead.add(j)
        k = len(frag)
        frag.append(m)
        made.append(m)
        for o in range(k):
            if o in dead:
                continue
            f = frag[o]
            if f["_x"][-1] <= m["_x"][0] + 2:
                sc = score(f, m)
                if sc is not None:
                    heapq.heappush(heap, (sc, o, k))
            if f["_x"][0] >= m["_x"][-1] - 2:
                sc = score(m, f)
                if sc is not None:
                    heapq.heappush(heap, (sc, k, o))
    return [dict(pts=m["pts"], gaps=m["gaps"], linked=True) for m in made]


def _trim_line_ends(t: Dict[str, Any], lines: np.ndarray, sp: float, ledgers: Sequence[Sequence[float]] = ()) -> Dict[str, Any]:
    """An arc that ends at a staff line chains with the line's own ink: the track runs on along the row (ROADMAP 2.274 r3: a bowl hanging from a line is read
    with two bows). A stretch of at least `TRIM_MIN_SP` at an end whose centre stays within `LINE_STUB_SP` of one staff-line row is the line's; it is cut off."""
    p = t["pts"]
    if len(p) < 8 or (len(lines) == 0 and not len(ledgers)):
        return t
    ys = np.array([q[1] for q in p], float)
    xs = np.array([q[0] for q in p], float)
    on = np.min(np.abs(ys[:, None] - lines[None, :]), axis=1) < LINE_STUB_SP * sp if len(lines) else np.zeros(len(p), bool)
    for (lx0, ly0, lx1, ly1) in ledgers:        # a ledger line claims first too: its own stretch of row (page boxes, reduced)
        on |= (xs >= lx0 - 2) & (xs <= lx1 + 2) & (ys >= ly0 - LINE_STUB_SP * sp) & (ys <= ly1 + LINE_STUB_SP * sp)
    a, b = 0, len(p)
    i = 0
    while i < len(p) and on[i]:
        i += 1
    if i > 0 and xs[i - 1] - xs[0] >= TRIM_MIN_SP * sp:
        a = i
    j = len(p)
    while j > a and on[j - 1]:
        j -= 1
    if j < len(p) and xs[-1] - xs[j] >= TRIM_MIN_SP * sp:
        b = j
    if a == 0 and b == len(p):
        return t
    return dict(t, pts=p[a:b], gaps=[g for g in t.get("gaps", []) if g[0] >= xs[a] and g[1] <= xs[b - 1]]) if b - a >= 3 else t


def _trim_ragged_ends(t: Dict[str, Any], sp: float) -> Optional[Dict[str, Any]]:
    """An arc that is fused with a stem, a flag or a beam at an end has a few junction points that lie off its own curve (ROADMAP 2.274 r3: refused "rough" or
    "two bows" where it merges). The curve is the quadratic of the MIDDLE of the track; the end points that stand off it by more than `RAGGED_DEV_SP` (running
    in from the end, no further) are the junction's and are cut. None when nothing is cut or too little is left."""
    p = t["pts"]
    if len(p) < 10:
        return None
    x = np.array([q[0] for q in p], float)
    y = np.array([q[1] for q in p], float)
    f = (x - x[0]) / max(1.0, x[-1] - x[0])
    mid = (f >= 0.2) & (f <= 0.8)
    if mid.sum() < 6:
        return None
    c = np.polyfit(x[mid], y[mid], 2)
    off = np.abs(y - np.polyval(c, x)) > RAGGED_DEV_SP * sp
    a, b = 0, len(p)
    while a < len(p) // 3 and off[a]:
        a += 1
    while b > a + 3 and b > 2 * len(p) // 3 and off[b - 1]:
        b -= 1
    if a == 0 and b == len(p):
        return None
    if x[b - 1] - x[a] < MIN_WIDTH_SP * sp:
        return None
    return dict(t, pts=p[a:b], gaps=[g for g in t.get("gaps", []) if g[0] >= x[a] and g[1] <= x[b - 1]])


def _judge(t: Dict[str, Any], sp: float, lines: np.ndarray, *, min_width_sp: float = MIN_WIDTH_SP, allow_on_line: bool = False
           ) -> Tuple[str, Optional[Dict[str, Any]]]:
    p = np.array(t["pts"], float)
    x, y, th = p[:, 0], p[:, 1], p[:, 2]
    width = x[-1] - x[0] + 1
    if width < min_width_sp * sp:
        return "short", None
    own = len(np.unique(x))
    claimed = float(sum(g1 - g0 for g0, g1 in t.get("gaps", []) if g0 >= x[0] and g1 <= x[-1]))
    inked = (own + claimed) / width
    if inked < MIN_INKED or own / width < MIN_OWN_INKED:
        return "sparse", None
    if np.median(th) < MIN_THICK_SP * sp:
        return "thin", None            # one reduced pixel of ink: the staff line's own residue, never a slur (a slur's body is thicker than a staff line)
    k = max(3, int(round(sp)))
    ys_ = np.convolve(y, np.ones(k) / k, mode="same")
    if len(ys_) != len(y):       # a track shorter than the window: nothing to smooth
        ys_ = y.copy()
    inner = slice(k, len(y) - k) if len(y) > 2 * k + 2 else slice(0, len(y))
    if len(y) <= 2 * k + 2 and len(y) >= 6:
        # a run shorter than two smoothing windows has no interior: the zero-padded running mean is wrong at both ends (it made every short, clean tie "rough"),
        # so its roughness is the scatter off its own smooth (quadratic) curve
        ys_ = np.polyval(np.polyfit(x, y, 2), x)
    # a bridged hole (a stem, a head, a carved rule the arc crosses) is not the arc's own ink: the columns beside it carry the stem's flank, so the jag is
    # measured away from every hole (`HOLE_PAD_SP` each side), never across one
    near_hole = np.zeros(len(x), bool)
    for i in np.flatnonzero(np.diff(x) > HOLE_MIN_SP * sp):
        near_hole |= (x >= x[i] - HOLE_PAD_SP * sp) & (x <= x[i + 1] + HOLE_PAD_SP * sp)
    keep = ~near_hole
    keep[:inner.start] = False
    keep[inner.stop:] = False
    if int(keep.sum()) < 8:
        keep = np.zeros(len(x), bool)
        keep[inner] = True
    resid = float(np.sqrt(np.mean((ys_[keep] - y[keep]) ** 2)))
    short_run = len(y) <= 2 * k + 2 and len(y) >= 6
    if resid > (JAG_SHORT_SP if short_run else JAG_SP) * sp:
        return "rough", None
    deg = 4 if width > 8 * sp else 2
    c = np.polyfit(x, y, deg)
    fit = np.polyval(c, x)
    chord = np.degrees(np.arctan2(abs(fit[-1] - fit[0]), width))
    if chord > MAX_CHORD_DEG:
        return "steep", None
    if FIT_RMS_SP and width <= FIT_MAX_SP * sp and float(np.sqrt(np.mean((y - fit) ** 2))) > FIT_RMS_SP * sp:
        return "bad_fit", None
    line_y = fit[0] + (fit[-1] - fit[0]) * (x - x[0]) / max(1.0, x[-1] - x[0])
    dev = fit - line_y
    sag = float(dev[np.argmax(np.abs(dev))])
    if len(lines) and not allow_on_line:
        dist = np.min(np.abs(y[:, None] - lines[None, :]), axis=1)
        if np.mean(dist < LINE_STUB_SP * sp) > 0.7:
            return "on_a_line", None
    if abs(sag) < STRAIGHT_REL * width:
        return "straight", None
    if width > STRAIGHT_MAX_SP * sp and abs(sag) < STRAIGHT_LONG_REL * width:
        # r4: a long flat slur bows 2-4.7% of its width but is a LENS (thin at both ends); a line or a beam keeps its thickness
        if not (TAPER_SLUR and _is_lens(x, th, width, sp)):
            return "straight", None
    if abs(sag) >= STRAIGHT_SAG_SP * sp:
        inn = np.abs(dev) > 0.03 * sp
        if inn.sum() >= 5 and np.mean(np.sign(dev[inn]) == np.sign(sag)) < 0.85:
            return "two_bows", None
    q = np.argsort(x)
    xs_, ths_ = x[q], th[q]
    if width <= SHORT_RUN_SP * sp and float(np.median(ths_[(xs_ - xs_[0] >= 0.3 * (xs_[-1] - xs_[0])) & (xs_ - xs_[0] <= 0.7 * (xs_[-1] - xs_[0]))] if np.any((xs_ - xs_[0] >= 0.3 * (xs_[-1] - xs_[0])) & (xs_ - xs_[0] <= 0.7 * (xs_[-1] - xs_[0]))) else np.median(ths_))) >= SHORT_THICK_SP * sp:
        return "thick", None
    f = (xs_ - xs_[0]) / max(1.0, xs_[-1] - xs_[0])
    mid_th = float(np.median(ths_[(f >= 0.3) & (f <= 0.7)])) if np.any((f >= 0.3) & (f <= 0.7)) else float(np.median(ths_))
    end_l = float(np.median(ths_[f <= 0.2])) if np.any(f <= 0.2) else mid_th
    end_r = float(np.median(ths_[f >= 0.8])) if np.any(f >= 0.8) else mid_th
    return "arc", dict(width_sp=round(width / sp, 2), sagitta_sp=round(sag / sp, 3), thick_sp=round(float(np.median(th)) / sp, 3),
                       resid_sp=round(resid / sp, 3), inked=round(inked, 2), chord_deg=round(float(chord), 1),
                       mid_th_sp=round(mid_th / sp, 3), taper=round(min(end_l, end_r) / max(mid_th, 1e-6), 2))


def _is_lens(x: np.ndarray, th: np.ndarray, width: float, sp: float) -> bool:
    """ROADMAP 2.274 r4: a slur is thin at both ends and thickest in the middle, even when it is shallow; a beam, a staff line and a hairpin leg keep their
    thickness. True when the middle's mean thickness is that of a slur (no more than `TAPER_MID_MAX_SP`) and both ends are thinner than it by `TAPER_END_RATIO`
    (the two ends' mean against the middle's)."""
    f = (x - x[0]) / max(1.0, width)
    mid = (f >= 0.35) & (f <= 0.65)
    ends = (f <= 0.12) | (f >= 0.88)
    if mid.sum() < 3 or ends.sum() < 4:
        return False
    tm, te = float(np.mean(th[mid])), float(np.mean(th[ends]))
    return tm <= TAPER_MID_MAX_SP * sp and te <= TAPER_END_RATIO * tm


def _is_wedge(t: Dict[str, Any], sp: float) -> bool:
    """ROADMAP 2.274 r4: thick at one end and thin at the other (a hairpin's leg, a flag's stroke), not thin at both ends like a slur. Mean thickness of the outer
    quarters; the thick end must be a stroke (at least 3 reduced px) so a one-pixel difference is not a wedge."""
    p = np.array(t["pts"], float)
    x, th = p[:, 0], p[:, 2]
    if len(x) < 8:
        return False
    f = (x - x[0]) / max(1.0, x[-1] - x[0])
    a, b = float(np.mean(th[f <= 0.25])), float(np.mean(th[f >= 0.75]))
    hi, lo = max(a, b), max(min(a, b), 1.0)
    return hi >= 3.0 and hi / lo >= WEDGE_RATIO


def _raw_beam_like(t: Dict[str, Any], raw_b: np.ndarray, sp: float, need_stems: bool = True) -> bool:
    """ROADMAP 2.274 r4, CLAIM ORDER (CLAUDE §3, Sean: "a beam is thick, straight, and joined to two or more stems"): a beam is claimed before an arc, and the
    linker / the thick pass built runs out of beams' edge pieces (9 of the 12 fakes of round 3). A run's body that lies on RAW ink (the unerased, unblanked
    raster, reduced) taller than `BEAM_RAW_SP` in nearly all its points, with a raw thickness that does not fall toward the ends, is on a beam's ink. A slur's
    raw ink is its own run (thin) or tapers; a heavy slur's middle is tall but its ends are not."""
    pts = t["pts"]
    if len(pts) < 8:
        return False
    H, W = raw_b.shape
    th = []
    for q in pts:
        xi, yi = int(round(q[0])), int(round(q[1]))
        if not (0 <= xi < W and 0 <= yi < H):
            th.append(np.nan)
            continue
        if not raw_b[yi, xi]:
            for d in (1, -1, 2, -2, 3, -3):
                if 0 <= yi + d < H and raw_b[yi + d, xi]:
                    yi += d
                    break
            else:
                th.append(np.nan)
                continue
        a = yi
        while a > 0 and raw_b[a - 1, xi]:
            a -= 1
        b = yi
        while b < H - 1 and raw_b[b + 1, xi]:
            b += 1
        th.append(b - a + 1)
    th = np.array(th, float)
    ok = np.isfinite(th)
    if ok.sum() < 8:
        return False
    x = np.array([q[0] for q in pts], float)
    f = (x - x[0]) / max(1.0, x[-1] - x[0])
    if float(np.mean(th[ok] > BEAM_RAW_SP * sp)) < BEAM_RAW_SHARE:
        return False
    mid, ends = th[(f >= 0.3) & (f <= 0.7) & ok], th[((f <= 0.12) | (f >= 0.88)) & ok]
    if len(mid) < 3 or len(ends) < 3:
        return False
    if float(np.median(ends)) < BEAM_RAW_ENDS * float(np.median(mid)):
        return False
    # a beam stands on its stems: raw ink at least BEAM_STEM_SP long rises or hangs at BOTH ends (a heavy slur's lens-middle has none: round-3 tile 6)
    def stem_at(q) -> bool:
        xc, yc = int(round(q[0])), int(round(q[1]))
        for xi in range(max(0, xc - int(BEAM_STEM_NEAR_SP * sp)), min(W, xc + int(BEAM_STEM_NEAR_SP * sp) + 1)):
            if not (0 <= yc < H) or not raw_b[yc, xi]:
                continue
            a = yc
            while a > 0 and raw_b[a - 1, xi]:
                a -= 1
            b = yc
            while b < H - 1 and raw_b[b + 1, xi]:
                b += 1
            if b - a + 1 >= BEAM_STEM_SP * sp:
                return True
        return False
    return (not need_stems) or (stem_at(pts[0]) and stem_at(pts[-1]))


def hugs_a_claimed_mark(pts: np.ndarray, boxes: Sequence[Tuple[str, Sequence[float]]], areas: Sequence[Tuple[str, Sequence[float]]], sp_page: float,
                        header_ink: Optional[np.ndarray] = None) -> Optional[str]:
    """CLAIM ORDER (CLAUDE §3): a run whose body (the middle of it, page px) lies along a mark that claims before an arc is that mark's own rim, not an arc: the
    foot of a head, an accidental, a dot, a rest, a ledger line (`HUG_SP` of its box) (a word's rectangle is no test: an arc passes over a "cresc."). The ends of an
    arc touch a head and a dynamic is crossed, so the ends are not looked at and dynamics are not counted. Returns the reason or None."""
    if len(pts) < 4:
        return None
    x0, x1 = pts[0, 0], pts[-1, 0]
    mid = pts[(pts[:, 0] >= x0 + 0.2 * (x1 - x0)) & (pts[:, 0] <= x1 - 0.2 * (x1 - x0))]
    if len(mid) < 2:
        mid = pts
    for name, rects, g in (("claimed_mark", [b for c, b in boxes if not c.startswith(CROSS_CLASSES + HUG_EXEMPT)], HUG_SP),
                           ("claimed_header", [a for o, a in areas if o in HEADER_OWNERS], HUG_SP)):
        g *= sp_page
        if name == "claimed_header" and header_ink is not None:
            # r3: the header's own INK (the components its areas claim), not its rectangle: a tie that starts after the key signature lies inside the
            # key's rectangle and is not along any of its strokes
            Hh, Ww = header_ink.shape
            gi = int(np.ceil(g))
            near = 0
            for x, y in mid[:, :2]:
                xi, yi = int(round(x)), int(round(y))
                if header_ink[max(0, yi - gi):min(Hh, yi + gi + 1), max(0, xi - gi):min(Ww, xi + gi + 1)].any():
                    near += 1
            if near / float(len(mid)) >= HUG_SHARE:
                return name
            continue
        inside = np.zeros(len(mid), bool)
        for (a0, b0, a1, b1) in rects:
            if a1 < mid[:, 0].min() - g or a0 > mid[:, 0].max() + g:
                continue
            inside |= (mid[:, 0] >= a0 - g) & (mid[:, 0] <= a1 + g) & (mid[:, 1] >= b0 - g) & (mid[:, 1] <= b1 + g)
        if inside.mean() >= HUG_SHARE:
            return name
    return None


def page_dots(ink: np.ndarray, sp_page: float) -> np.ndarray:
    """Centres (x, y, page px) of the small round ink blobs of the page (a dot: 0.2 - 0.75 space across, filling most of its box): what a fermata's hump sits
    over, what a staccato or a dotted note carries."""
    import cv2
    n, lab, st, cen = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    w, h, a = st[:, 2], st[:, 3], st[:, 4]
    ok = (w >= DOT_MIN_SP * sp_page) & (w <= DOT_MAX_SP * sp_page) & (h >= DOT_MIN_SP * sp_page) & (h <= DOT_MAX_SP * sp_page) & (a >= 0.5 * w * h)
    ok[0] = False
    return cen[ok]


def is_a_fermata(pts: np.ndarray, dots: np.ndarray, sag_sp: float, width_sp: float, sp_page: float) -> bool:
    """A short hump (bow up) with a dot under its middle is a fermata, a mark that claims before an arc (page-facts: a fermata is a mark, not an arc)."""
    if sag_sp >= 0 or width_sp > FERMATA_MAX_SP or len(dots) == 0:
        return False
    x0, x1 = pts[0, 0], pts[-1, 0]
    mx, w = (x0 + x1) / 2.0, x1 - x0
    top = float(pts[:, 1].min())
    sel = dots[(np.abs(dots[:, 0] - mx) <= 0.2 * w) & (dots[:, 1] >= top + 0.2 * sp_page) & (dots[:, 1] <= top + 1.8 * sp_page)]
    return len(sel) > 0


def short_and_flat(sag_sp: float, width_sp: float) -> bool:
    """A run no wider than `FLAT_MAX_SP` that bows less than `FLAT_SAG_SP` is a ledger line, a head's base or a beam's stub, never a tie. Measured on the five
    develop pages: 2 such runs lie under a detector arc box and 28 under none (a tie bows; and a mark that is not an arc is not boxed as one)."""
    return width_sp <= FLAT_MAX_SP and abs(sag_sp) < FLAT_SAG_SP


def _line_rows(line_ys: Sequence[float], scale: float, H: int) -> np.ndarray:
    """The rows (reduced px) a staff line, and so its erased band, occupies."""
    rows = np.zeros(H, bool)
    for y in line_ys:
        c = int(round(y * scale))
        rows[max(0, c - 1):min(H, c + 2)] = True
    return rows


def _is_arc_component(lab: np.ndarray, i: int, x0: int, y0: int, w: int, h: int, sp: float) -> bool:
    """One thin bowed run: nearly every column holds ONE stroke no thicker than an arc column (`RUN_MAX_SP`), the strokes' centres follow a smooth quadratic, and
    the bow is not a line's. Letters, a dash line, a stem or a head are none of these."""
    m = lab[y0:y0 + h, x0:x0 + w] == i
    cen, th = [], []
    multi = 0
    for x in range(w):
        col = np.flatnonzero(m[:, x])
        if len(col) == 0:
            continue
        runs = 1 + int(np.count_nonzero(np.diff(col) > 1))
        if runs > 1:
            multi += 1
            continue
        cen.append((x, (col[0] + col[-1]) / 2.0))
        th.append(len(col))
    if len(cen) < 0.9 * w or multi > 0.04 * w or float(np.median(th)) > RUN_MAX_SP * sp or max(th) > 1.4 * RUN_MAX_SP * sp:
        return False
    cx = np.array([c[0] for c in cen], float)
    cy = np.array([c[1] for c in cen], float)
    c2 = np.polyfit(cx, cy, 2)
    if float(np.sqrt(np.mean((np.polyval(c2, cx) - cy) ** 2))) > 0.12 * sp:
        return False
    return True          # a straight stroke this long is no letter either; the judge refuses a line, a piece of an arc is nearly one

def _has_hole(m: np.ndarray, sp: float) -> bool:
    """The component mask encloses background (a ring: 0, 6, 8, 9, O, D, a boxed rehearsal letter) of at least a fifth of a space across."""
    import cv2
    pad = np.pad(~m, 1, constant_values=True).astype(np.uint8)
    n, lab, st, _c = cv2.connectedComponentsWithStats(pad, connectivity=4)
    outer = lab[0, 0]
    for i in range(1, n):
        if i != outer and st[i, 2] >= 0.2 * sp and st[i, 3] >= 0.2 * sp:
            return True
    return False


def blank_mask(ink: np.ndarray, boxes: Sequence[Tuple[str, Sequence[float]]], areas: Sequence[Tuple[str, Sequence[float]]], sp_page: Optional[float] = None, glyphs: bool = True) -> np.ndarray:
    """What claims first or is not arc ink: the compact detector boxes' rectangles, and the ink COMPONENTS wholly inside a page claim's area (+1 px)."""
    import cv2
    H, W = ink.shape
    blank = np.zeros_like(ink)
    for _cls, (x0, y0, x1, y1) in boxes:
        if WIDE_BOX and sp_page and _cls.startswith(WIDE_BOX_CLASSES) and (x1 - x0) > WIDE_BOX_SP * sp_page:
            continue          # r4: not a mark of that class (a flat is one space wide): the detector boxed an arc
        ya, yb, xa, xb = max(0, int(y0) - 1), min(H, int(np.ceil(y1)) + 1), max(0, int(x0) - 1), min(W, int(np.ceil(x1)) + 1)
        if LEDGER_THIN and _cls.startswith("ledger"):
            # a ledger line is a thin level stroke: where the ink through the box is much thicker than the box is tall, something else lies there (the top of
            # a heavy slur the detector boxed as a ledger line, 2.274 r3), and that column is not claimed
            for x in range(xa, xb):
                col = ink[:, x]
                top = ya
                while top > 0 and col[top - 1]:
                    top -= 1
                bot = yb
                while bot < H and col[bot]:
                    bot += 1
                if bot - top > (yb - ya) + LEDGER_THIN_PX and col[ya:yb].any():
                    continue
                blank[ya:yb, x] = True
            continue
        blank[ya:yb, xa:xb] = True
    glyphs = bool(glyphs and GLYPH_COMP and sp_page)
    if areas or glyphs:
        n, lab, st, _c = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        take = np.zeros(n, bool)
        bx, by, bw, bh = st[:, 0], st[:, 1], st[:, 2], st[:, 3]
        if glyphs:
            cand = np.flatnonzero((bw <= GLYPH_MAX_W_SP * sp_page) & (bh <= GLYPH_MAX_H_SP * sp_page) & (bh >= GLYPH_MIN_H_SP * sp_page) & (bw >= 0.5 * sp_page))
            cand = cand[cand > 0]
            if len(cand) and boxes:
                bxs = np.array([[b[0], b[1], b[2], b[3]] for _c2, b in boxes], float)
            else:
                bxs = np.zeros((0, 4))
            for i in cand:
                if len(bxs) and np.any((bxs[:, 0] <= bx[i] + bw[i]) & (bxs[:, 2] >= bx[i]) & (bxs[:, 1] <= by[i] + bh[i]) & (bxs[:, 3] >= by[i])):
                    continue          # a detector mark lies on it: a note, an accidental, a rest ... never a glyph
                if _is_arc_component(lab, int(i), int(bx[i]), int(by[i]), int(bw[i]), int(bh[i]), sp_page):
                    continue
                if not _has_hole(lab[by[i]:by[i] + bh[i], bx[i]:bx[i] + bw[i]] == i, sp_page):
                    continue          # a slur's piece with a hook, a tie, a dash has no ring; a digit, an O, a rehearsal frame has
                take[i] = True
        union = np.zeros(ink.shape, bool)
        hdr = np.zeros(n, bool)
        for _own, (x0, y0, x1, y1) in areas:
            inside = (bx >= x0 - 1) & (by >= y0 - 1) & (bx + bw <= x1 + 1) & (by + bh <= y1 + 1)
            take |= inside
            if _own != "word":
                hdr |= inside          # a bracket, clef, key signature, meter, leading column, hairpin: their strokes are never an arc
            union[max(0, int(y0) - 1):min(H, int(np.ceil(y1)) + 1), max(0, int(x0) - 1):min(W, int(np.ceil(x1)) + 1)] = True
        # a label whose letters straddle two claimed areas (a staff name stacked over its crook) is wholly inside their UNION
        tot = np.bincount(lab.ravel(), minlength=n)
        ins = np.bincount(lab[union & ink].ravel(), minlength=n)
        take |= (ins >= 0.98 * np.maximum(tot, 1))
        take[0] = False
        if ARC_IN_WORD and sp_page:
            # a word's rectangle can run over an arc (a long "cresc. - - -" line); the arc, cut at a barline, is a component wholly inside it. A component that is
            # ONE thin bowed run (every column one stroke, no taller than an arc, wide for a letter) is an arc, not a letter: not taken (2.274 r3)
            for i in np.flatnonzero(take & ~hdr & (bw >= ARC_COMP_MIN_SP * sp_page)):
                if _is_arc_component(lab, int(i), int(bx[i]), int(by[i]), int(bw[i]), int(bh[i]), sp_page):
                    take[i] = False
        blank |= take[lab]
    return blank


def line_model(raw_ink: np.ndarray, line_ys: Sequence[float], sp: float, scale: float) -> List[Dict[str, Any]]:
    """ROADMAP 2.274 r3, the staff lines' OWN local geometry on the UNERASED raster (reduced frame): per line, `c` (the line's centre at every column, from the
    page's own local staff reader `stroke_map.LocalStaff`, so a tilted or wavy staff is measured where the arc is, never with a staff-wide value) and `t` (the
    line's own thickness at every column: the run thickness on the raw raster, medianed over +-`LINE_WIN_SP` and never above `LINE_THICK_CAP` times the line's
    own median, so an arc lying on the line does not become part of it). The lines are taken in staves of five, as the page's staves are. [] when the lines
    are not whole staves."""
    from .stroke_map import LocalStaff
    ys = sorted(float(y) * scale for y in line_ys)
    if not ys or len(ys) % 5:
        return []
    H, W = raw_ink.shape
    out: List[Dict[str, Any]] = []
    win = max(3, int(round(LINE_WIN_SP * sp)))
    ink = raw_ink > 0.5
    for s in range(0, len(ys), 5):
        grp = ys[s:s + 5]
        ya = max(0, int(grp[0] - 3 * sp))
        yb = min(H, int(grp[-1] + 3 * sp) + 1)
        ls = LocalStaff(raw_ink[ya:yb], [y - ya for y in grp], sp)
        xs = np.arange(W)
        for i in range(5):
            cen = np.array([ls.lines_at(float(x))[i] + ya for x in range(0, W, 4)])
            c = np.interp(xs, np.arange(0, W, 4), cen)
            r0 = np.clip(np.round(c).astype(int), 0, H - 1)
            # the ink row nearest the centre (within 2 px), then the run's extent up and down
            r = r0.copy()
            for d in (1, -1, 2, -2):
                miss = ~ink[r, xs]
                r[miss] = np.clip(r0[miss] + d, 0, H - 1)
            have = ink[r, xs]
            top = r.copy()
            bot = r.copy()
            lim = int(1.5 * sp)
            alive_u = have.copy()
            alive_d = have.copy()
            for k in range(1, lim + 1):
                yu = np.clip(r - k, 0, H - 1)
                yd = np.clip(r + k, 0, H - 1)
                alive_u &= ink[yu, xs]
                alive_d &= ink[yd, xs]
                top[alive_u] = yu[alive_u]
                bot[alive_d] = yd[alive_d]
            t = (bot - top + 1).astype(float)
            t[~have] = np.nan
            tmed = float(np.nanmedian(t)) if np.isfinite(t).any() else 2.0
            tl = np.full(W, tmed)
            tt = np.where(np.isfinite(t), np.minimum(t, LINE_THICK_CAP * tmed), np.nan)
            for x in range(0, W, 2):
                seg = tt[max(0, x - win):x + win + 1]
                seg = seg[np.isfinite(seg)]
                if len(seg) >= 3:
                    tl[x:x + 2] = float(np.median(seg))
            out.append(dict(c=c, t=tl, tmed=tmed, have=have, top=top, bot=bot))
    return out


def line_arc_ink(small_raw: np.ndarray, model: Sequence[Dict[str, Any]], sp: float, cols: List[List[Tuple[int, int]]], blank_s: Optional[np.ndarray],
                 max_run: int) -> np.ndarray:
    """What lies ON a staff line is read on the unerased raster (ROADMAP 2.274 r3; lane brief 1, Sean's process: an arc is the ink that leaves the line's own band
    or is thicker than the line's own local thickness at that x). In each column where the raw run through a line is thicker than that line's own thickness
    here by at least `LINE_EXCESS_SP` (and no taller than an arc column, and not claimed), the eraser may have taken part of an arc with the line: the column's
    runs under the raw run are replaced by the arc's own rows -- the whole raw run when it leaves the line on BOTH sides, else the side it leaves on, one
    nominal arc thickness deep (the rest lies in the line). Returns the boolean mask of the line bands (rows of each line's own band, with `LINE_PAD_SP`),
    where a track may wait on its own slope through the stretch where the arc lies wholly in the line and nothing shows."""
    H, W = small_raw.shape
    band = np.zeros((H, W), bool)
    xs = np.arange(W)
    pad = max(1, int(round(LINE_PAD_SP * sp)))
    nom = max(2, int(round(ARC_NOMINAL_SP * sp)))
    emin = max(2.0, LINE_EXCESS_SP * sp)
    for m in model:
        c, tl = m["c"], m["t"]
        for x in range(W):
            if not m["have"][x]:
                continue
            lo, hi = int(round(c[x] - tl[x] / 2.0)) - pad, int(round(c[x] + tl[x] / 2.0)) + pad
            band[max(0, lo):min(H, hi + 1), x] = True
        if LINE_RESIDUE:
            # the eraser can leave a staff line standing in a stretch (its band is a few px off): ink wholly inside the line's own band is the line's, and a
            # track that chains with it makes a bowl hanging from the line read as a straight run along it
            for x in range(W):
                if m["have"][x] and cols[x]:
                    lo, hi = int(round(c[x] - tl[x] / 2.0)) - 1, int(round(c[x] + tl[x] / 2.0)) + 1
                    cols[x] = [(p, q) for (p, q) in cols[x] if not (p >= lo and q - 1 <= hi)]
        top, bot = m["top"], m["bot"]
        t = (bot - top + 1).astype(float)
        la, lb = c - tl / 2.0, c + tl / 2.0
        et, eb = la - top, bot - lb
        ok = m["have"] & (t - tl >= emin) & (t <= max_run)
        for x in np.flatnonzero(ok):
            a, b = int(top[x]), int(bot[x])
            if blank_s is not None and blank_s[a:b + 1, x].any():
                continue
            if et[x] >= 1.0 and eb[x] >= 1.0:
                A, B = a, b
            elif et[x] >= eb[x]:
                A, B = a, min(b, a + max(nom, int(round(et[x]))))
            else:
                A, B = max(a, b - max(nom, int(round(eb[x])))), b
            keep = [(p, q) for (p, q) in cols[x] if q < a - 1 or p > b + 1]
            keep.append((A, B + 1))
            cols[x] = sorted(keep)
    return band


def read_runs(canvas: np.ndarray, sp_page: float, line_ys: Sequence[float], boxes: Sequence[Tuple[str, Sequence[float]]],
              areas: Sequence[Tuple[str, Sequence[float]]], *, blank: Optional[np.ndarray] = None, keep_rejected: bool = False, extend: bool = True,
              raw: Optional[np.ndarray] = None, arc_boxes: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """The runs of the page ink (module doc). `canvas`: 0 = ink, page px. Returns `{runs, why, tracks, scale, sp, blanked}`; each run has `pts` (page px,
    ~one per 2 reduced px), `box`, `width_sp`, `sagitta_sp`, `thick_sp`, `resid_sp`, `inked`, `chord_deg`, `half` (half its thickness, page px)."""
    import cv2
    ink = canvas == 0
    if blank is None:
        blank = blank_mask(ink, boxes, areas, sp_page)
    ink2 = ink & ~blank
    scale = min(1.0, TARGET_SP_PX / sp_page)
    small = cv2.resize(ink2.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96 if scale < 1 else ink2
    sp = sp_page * scale
    line_rows = _line_rows(line_ys, scale, small.shape[0])
    cols = _column_runs(small.astype(np.int8), int(round(RUN_MAX_SP * sp)), line_rows, int(np.ceil(LINE_GAP_SP * sp)))
    blank_s = cv2.resize(blank.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 32 if scale < 1 else blank
    band_s = None
    if raw is not None and line_ys:
        raw_f = cv2.resize((raw == 0).astype(np.float32), None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else (raw == 0).astype(np.float32)
        model = line_model(raw_f, line_ys, sp, scale)
        if model:
            band_s = line_arc_ink(raw_f > 0.5, model, sp, cols, blank_s, int(round(RUN_MAX_SP * sp)))
    # a track may wait out, and an arc be carried on through, only what a WORD or a dynamic claims (the marks an arc passes THROUGH); a head, an accidental,
    # a rest, a flag is where an arc ENDS, and a track that waited across heads linked their edges into fake runs
    cross = blank_mask(ink, [(c, b) for c, b in boxes if c.startswith(CROSS_CLASSES)], areas, sp_page, glyphs=False)
    cross_s = cv2.resize(cross.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 32 if scale < 1 else cross
    tracks = _track(cols, sp, small.shape[1], cross_s if (band_s is None or not LINE_WAIT) else (cross_s | band_s))
    lines = np.array(sorted(y * scale for y in line_ys))
    tracks = [q for t in tracks for q in _split_at_cusps(t, sp)]
    if THICK_PASS and raw is not None:
        cols_t = _column_runs(small.astype(np.int8), int(round(THICK_MAX_SP * sp)), line_rows, int(np.ceil(LINE_GAP_SP * sp)))
        extra = []
        for t in _track(cols_t, sp, small.shape[1], cross_s):
            for q in _split_at_cusps(t, sp):
                pp = q["pts"]
                if len(pp) < 8 or (pp[-1][0] - pp[0][0]) < THICK_MIN_SP * sp:
                    continue
                if np.mean([c[2] > RUN_MAX_SP * sp for c in pp]) >= THICK_SHARE:
                    extra.append(dict(q, linked=True, thick=True))
        tracks = extra + tracks
    n_linked = 0
    raw_b = None
    if raw is not None:
        raw_b = cv2.resize((raw == 0).astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96 if scale < 1 else (raw == 0)
    if raw is not None and LINK:
        joined = _link_fragments(tracks, sp, raw_b, (blank_s | band_s) if band_s is not None else blank_s)
        n_linked = len(joined)
        tracks = joined + tracks
    dots = page_dots(ink, sp_page)
    raw_cols = None
    erased_s = None
    if extend:
        small_raw = cv2.resize(ink.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96 if scale < 1 else ink
        raw_cols = _column_runs(small_raw.astype(np.int8), int(round(RUN_MAX_SP * sp)), line_rows, int(np.ceil(LINE_GAP_SP * sp)))
        if raw_b is not None and ERASED_EXT:
            erased_s = raw_b & ~(small_raw > 0)          # what the staff-line eraser and the barline carve took out of the page's ink
    header_ink = blank_mask(ink, [], [(o, a) for o, a in areas if o in HEADER_OWNERS], sp_page, glyphs=False) if (HEADER_INK and areas) else None
    ledgers_s = [[b[0] * scale, b[1] * scale, b[2] * scale, b[3] * scale] for c, b in boxes if c.startswith("ledger")]
    why: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    rejected_tracks: List[Dict[str, Any]] = []
    acc: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for t in tracks:
        if len(t["pts"]) < 3:
            why["tiny"] = why.get("tiny", 0) + 1
            continue
        if TRIM_LINE and raw is not None:
            t = _trim_line_ends(t, lines, sp, ledgers_s)
        v, info = _judge(t, sp, lines)
        if v in ("rough", "two_bows", "steep", "straight", "sparse", "bad_fit") and RAGGED_TRIM and raw is not None:
            t2 = _trim_ragged_ends(t, sp)
            if t2 is not None:
                v2, info2 = _judge(t2, sp, lines)
                if v2 == "arc":
                    t, v, info = dict(t2, ragged=True), v2, info2
        if v == "arc" and info["mid_th_sp"] >= BEAM_LIKE_SP and info["taper"] > BEAM_TAPER:
            v = "beam_like"          # a thick run that does not thin toward its ends is a beam, not the heavy middle of a slur (r3: thick pass + linking built beam runs)
        if v == "arc" and BEAM_RAW and raw_b is not None and _raw_beam_like(t, raw_b, sp):
            v = "beam_raw"           # r4: on a beam's raw ink (tall, uniform): the beam owns it
        why[v] = why.get(v, 0) + 1
        if v != "arc":
            if keep_rejected and v != "short":
                q = np.array(t["pts"], float)
                rejected.append(dict(why=v, x0=float(q[0, 0] / scale), x1=float(q[-1, 0] / scale), y=float(np.median(q[:, 1]) / scale),
                                     thick_sp=round(float(np.median(q[:, 2]) / sp), 2), n=len(q)))
                rejected_tracks.append(dict(why=v, pts=[[float(a / scale), float(b / scale)] for a, b, _c in q]))
            continue
        hug = hugs_a_claimed_mark(np.array(t["pts"], float) / scale, boxes, areas, sp_page, header_ink)
        if not hug and short_and_flat(info["sagitta_sp"], info["width_sp"]):
            hug = "short_flat"
        if not hug and is_a_fermata(np.array(t["pts"], float)[:, :2] / scale, dots, info["sagitta_sp"], info["width_sp"], sp_page):
            hug = "fermata"
        if hug:
            why[hug] = why.get(hug, 0) + 1
            why["arc"] = why.get("arc", 1) - 1
            if keep_rejected:
                rejected_tracks.append(dict(why=hug, pts=[[float(a / scale), float(b / scale)] for a, b, _c in t["pts"]]))
            continue
        acc.append((t, info))
    # a joined run replaces the fragments it covers (an accepted fragment inside an accepted joined run is that run's own part)
    joined_acc = [(t, info) for t, info in acc if t.get("linked")]
    if joined_acc:
        keep = []
        for t, info in acc:
            if not t.get("linked"):
                px = np.array([q[0] for q in t["pts"]], float)
                py = np.array([q[1] for q in t["pts"]], float)
                inside = False
                for jt, _ji in joined_acc:
                    jx = np.array([q[0] for q in jt["pts"]], float)
                    jy = np.array([q[1] for q in jt["pts"]], float)
                    sel = (px >= jx[0] - 2) & (px <= jx[-1] + 2)
                    if sel.mean() >= 0.8 and float(np.median(np.abs(np.interp(px[sel], jx, jy) - py[sel]))) <= 0.6 * sp:
                        inside = True
                        break
                if inside:
                    why["covered_by_joined"] = why.get("covered_by_joined", 0) + 1
                    continue
            keep.append((t, info))
        acc = keep
    for t, info in acc:
        if BEAM_RAW and raw_b is not None and arc_boxes is not None:
            # r4, count evidence by source: a run no detector arc box witnesses stands on its ink alone, so it meets the stricter standard (tall, uniform raw ink is a
            # beam's edge even with no stems seen at its ends); a witnessed run (0 fakes in 20, rounds 3 and 4) keeps the stems-at-both-ends test above
            pg = np.array(t["pts"], float)[:, :2] / scale
            if not any(witness_share(pg, b["box"], sp_page) >= WITNESS_SHARE for b in arc_boxes):
                if _raw_beam_like(t, raw_b, sp, need_stems=False):
                    why["beam_raw_new"] = why.get("beam_raw_new", 0) + 1
                    why["arc"] = why.get("arc", 1) - 1
                    continue
                if WEDGE and _is_wedge(t, sp):
                    why["wedge_new"] = why.get("wedge_new", 0) + 1
                    why["arc"] = why.get("arc", 1) - 1
                    continue
        core = [[t["pts"][0][0], t["pts"][0][1]], [t["pts"][-1][0], t["pts"][-1][1]]]          # step 2: where the arc's OWN ink stops, before the extension carries it on
        if raw_cols is not None:
            # the core was judged on its own ink; only an accepted arc is carried on through the marks that claim before it, so an extension can never
            # make a run fail (a tail into a head used to turn a clean arc "steep")
            t = _extend_through_claims(t, raw_cols, blank_s if EXT_ALL else cross_s, sp, erased_s)
            info = dict(info, width_sp=round((t["pts"][-1][0] - t["pts"][0][0] + 1) / sp, 2))
        info = dict(info, src=("thick" if t.get("thick") else "linked" if t.get("linked") else "ragged" if t.get("ragged") else "plain"), core=core)
        out.append(_run_row(t, info, scale, len(out)))
    why['joined_tracks'] = n_linked
    return dict(runs=out, why=why, tracks=len(tracks), scale=scale, sp=sp, blanked=int(blank.sum()), rejected=rejected,
                rejected_tracks=rejected_tracks if keep_rejected else [], all_tracks=tracks if keep_rejected else [], blank_mask=blank if keep_rejected else None)


def _run_row(t: Dict[str, Any], info: Dict[str, Any], scale: float, ordinal: int) -> Dict[str, Any]:
    p = np.array(t["pts"], float)
    pts = [[round(px / scale, 1), round(py / scale, 1)] for px, py, _ in p[::max(1, int(2 * scale))]]
    pts.append([round(p[-1, 0] / scale, 1), round(p[-1, 1] / scale, 1)])
    xs, ys = p[:, 0] / scale, p[:, 1] / scale
    half = float(p[:, 2].max() / scale / 2)
    info = dict(info)
    if info.get("core"):
        info["core_ends"] = [[round(c[0] / scale, 1), round(c[1] / scale, 1)] for c in info.pop("core")]
    info.update(id=ordinal, pts=pts, half=round(half, 1), box=[float(xs.min()), float(ys.min() - half), float(xs.max()), float(ys.max() + half)])
    return info


# ───────────────────────────── 3. witnesses, ends, the detector boxes no run answers ─────────────────────────────

def thin_points(pts: Sequence[Sequence[float]], sp_page: float) -> List[List[float]]:
    """About one point per `POINT_STEP_SP` along x, always keeping the two ends."""
    step = POINT_STEP_SP * sp_page
    out = [list(pts[0])]
    for p in pts[1:-1]:
        if p[0] - out[-1][0] >= step:
            out.append(list(p))
    out.append(list(pts[-1]))
    return out


def ends_of(pts: Sequence[Sequence[float]], sp_page: float) -> List[List[float]]:
    """`[[x, y, tangent_deg], [x, y, tangent_deg]]`, left then right; the tangent is the slope over the last space of the run (positive = running DOWN the page)."""
    a = np.array(pts, float)
    out = []
    for end, sel in ((a[0], a[:, 0] <= a[0, 0] + sp_page), (a[-1], a[:, 0] >= a[-1, 0] - sp_page)):
        s = a[sel]
        sl = float(np.polyfit(s[:, 0], s[:, 1], 1)[0]) if len(s) >= 3 and np.ptp(s[:, 0]) > 1 else 0.0
        out.append([round(float(end[0]), 1), round(float(end[1]), 1), round(float(np.degrees(np.arctan(sl))), 1)])
    return out


def witness_share(pts: np.ndarray, box: Sequence[float], sp_page: float) -> float:
    """The share of the detector box's width that the run covers INSIDE the box grown by half a space (a witness test, not a verdict)."""
    g = 0.5 * sp_page
    x0, y0, x1, y1 = box
    if x1 <= x0:
        return 0.0
    sel = pts[(pts[:, 0] >= x0 - g) & (pts[:, 0] <= x1 + g) & (pts[:, 1] >= y0 - g) & (pts[:, 1] <= y1 + g)]
    if len(sel) < 2:
        return 0.0
    return float(min(sel[:, 0].max(), x1) - max(sel[:, 0].min(), x0)) / (x1 - x0)


def witnesses_of(runs: Sequence[Dict[str, Any]], arc_boxes: Sequence[Dict[str, Any]], sp_page: float
                 ) -> Tuple[Dict[int, List[str]], List[Dict[str, Any]]]:
    """`({run id: [witness subjects]}, [arc boxes no run witnesses])`."""
    by_run: Dict[int, List[str]] = {r["id"]: [] for r in runs}
    pts = {r["id"]: np.array(r["pts"], float) for r in runs}
    alone = []
    for b in arc_boxes:
        hit = False
        for r in runs:
            bb = r["box"]
            g = sp_page
            if bb[2] < b["box"][0] - g or bb[0] > b["box"][2] + g or bb[3] < b["box"][1] - g or bb[1] > b["box"][3] + g:
                continue
            if witness_share(pts[r["id"]], b["box"], sp_page) >= WITNESS_SHARE:
                by_run[r["id"]].append(b["subject"])
                hit = True
        if not hit:
            alone.append(b)
    return by_run, alone


def seed_read(canvas: np.ndarray, sp_page: float, line_ys: Sequence[float], box: Sequence[float], blank: np.ndarray) -> Optional[Dict[str, Any]]:
    """A BOUNDED local read under a detector arc box no run answers (the plan's §3.3 seeded witness): the same tracker on the box grown by `SEED_PAD_SP`,
    with the short-run floor lowered to a tie's and a staff-line row allowed. Returns the run that spans most of the box, or None. Marked `seeded`: the
    box chose where to look, so it is not an ink-first run and is counted apart."""
    import cv2
    H, W = canvas.shape
    pad = SEED_PAD_SP * sp_page
    x0, y0, x1, y1 = max(0, int(box[0] - pad)), max(0, int(box[1] - pad)), min(W, int(box[2] + pad)), min(H, int(box[3] + pad))
    if x1 - x0 < 8 or y1 - y0 < 4:
        return None
    sub = (canvas[y0:y1, x0:x1] == 0) & ~blank[y0:y1, x0:x1]
    scale = min(1.0, TARGET_SP_PX / sp_page)
    small = cv2.resize(sub.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96 if scale < 1 else sub
    sp = sp_page * scale
    line_rows = _line_rows([y - y0 for y in line_ys], scale, small.shape[0])
    cols = _column_runs(small.astype(np.int8), int(round(RUN_MAX_SP * sp)), line_rows, int(np.ceil(LINE_GAP_SP * sp)))
    tracks = [q for t in _track(cols, sp, small.shape[1]) for q in _split_at_cusps(t, sp)]
    lines = np.array(sorted((y - y0) * scale for y in line_ys))
    best, best_w = None, 0.0
    for t in tracks:
        if len(t["pts"]) < 3:
            continue
        v, info = _judge(t, sp, lines, min_width_sp=SEED_MIN_WIDTH_SP, allow_on_line=True)
        if v != "arc":
            continue
        w = (t["pts"][-1][0] - t["pts"][0][0]) / scale
        if w > best_w:
            best, best_w = (t, info), w
    if best is None or best_w < 0.6 * (box[2] - box[0]):
        return None
    t, info = best
    t = dict(pts=[(px + x0 * scale, py + y0 * scale, th) for px, py, th in t["pts"]])
    return _run_row(t, info, scale, -1)


SEED_PAD_SP = 0.5
SEED_MIN_WIDTH_SP = 0.9


# ───────────────────────────── 4. file it ─────────────────────────────

def gather_page_arcs(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], page_map: Any, *, progress: bool = False
                     ) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.274 step 1 (flag `OMR_PAGE_ARCS`, default OFF), STAGED GATHER: `Q.PAGE_ARC` (module doc). AFTER the page-wide claims (words, clef / key /
    meter, brackets), the page claim names and the page heads, and after the page beams: the last page-wide reader of ink. Reads rows and the page map's
    canvas; files rows only; decides nothing, claims nothing."""
    if not enabled():
        return None
    from . import record as R
    from .record import Q, READERS, ABSTAIN, Scope
    from .gather import FRAME_PAGE
    from . import run_meter
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    asm = getattr(page_map, "assembly", None)
    canvas = getattr(asm, "canvas", None)
    if page_map is None or canvas is None:
        log.abstain(sub, Q.PAGE_ARC, reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, reason=ABSTAIN.NO_MASK, note="no page stroke map")
        return None
    t0 = time.time()
    rows = []
    for r in log.rows(Q.GLYPH_BOX, sub, scope=Scope.SELF_AND_DESCENDANTS):
        rows.append(("glyph_box", r.subject.to_key() if hasattr(r.subject, "to_key") else str(r.subject), r.value, r.detail))
    for r in log.rows(Q.CLAIMED_AREA, sub, scope=Scope.SELF_AND_DESCENDANTS):
        rows.append(("claimed_area", "", r.value, r.detail))
    boxes, areas, arc_boxes = inputs_from_rows(rows)
    sp_page = float(page_map.sp)
    line_ys = [float(y) for s in pws.staves for y in s.line_ys]
    res = read_runs(canvas, sp_page, line_ys, boxes, areas, raw=getattr(getattr(pws, "page", None), "binary", None), arc_boxes=arc_boxes)
    runs = res["runs"]
    by_run, alone = witnesses_of(runs, arc_boxes, sp_page)
    t_runs = time.time()
    # staff of a run: the staff whose lines are nearest its middle
    staves = list(pws.staves)

    def staff_of(y: float) -> List[int]:
        best = min(staves, key=lambda s: abs((s.line_ys[0] + s.line_ys[-1]) / 2.0 - y))
        return [local.get(best.staff_index, (0, 0))[0], local.get(best.staff_index, (0, 0))[1]]
    n = 0
    for r in runs:
        pts = np.array(r["pts"], float)
        thin = thin_points(r["pts"], sp_page)
        mid_y = float(np.median(pts[:, 1]))
        log.observe(sub, Q.PAGE_ARC, "run", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, ordinal=n, bbox_page_px=[round(v, 1) for v in r["box"]],
                    points=thin, width_spaces=r["width_sp"], sagitta_spaces=r["sagitta_sp"], thickness_spaces=r["thick_sp"], ends=ends_of(r["pts"], sp_page),
                    witnesses=by_run[r["id"]], staff=staff_of(mid_y), space_page_px=round(sp_page, 3), core_ends=r.get("core_ends"))
        n += 1
    blank = None
    n_seeded = 0
    if alone:
        ink = canvas == 0
        blank = blank_mask(ink, boxes, areas, sp_page)
    for b in alone:
        s = seed_read(canvas, sp_page, line_ys, b["box"], blank)
        if s is not None:
            n_seeded += 1
            log.observe(sub, Q.PAGE_ARC, "seeded", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, ordinal=n, bbox_page_px=[round(v, 1) for v in s["box"]],
                        points=thin_points(s["pts"], sp_page), width_spaces=s["width_sp"], sagitta_spaces=s["sagitta_sp"], thickness_spaces=s["thick_sp"],
                        ends=ends_of(s["pts"], sp_page),
                        witnesses=[b["subject"]], staff=staff_of(float(np.median(np.array(s["pts"])[:, 1]))))
            n += 1
        else:
            log.observe(sub, Q.PAGE_ARC, "box_without_run", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, ordinal=n, bbox_page_px=[round(v, 1) for v in b["box"]],
                        witnesses=[b["subject"]])
            n += 1
    census = dict(runs=len(runs), seeded=n_seeded, boxes_without_run=len(alone) - n_seeded, arc_boxes=len(arc_boxes),
                  runs_with_witness=sum(1 for v in by_run.values() if v), runs_without_witness=sum(1 for v in by_run.values() if not v),
                  tracks=res["tracks"], rejected=res["why"], blanked_px=res["blanked"], seconds=round(time.time() - t0, 2),
                  seconds_runs=round(t_runs - t0, 2), peak_rss_gb=round(run_meter.peak_rss_bytes() / 1e9, 2))
    log.observe(sub, Q.PAGE_ARC, "census", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, **census)
    if progress:
        print("  gather page arcs p%s: %s" % (p, census))
    return census


def rows_of(rec: Any, page: Optional[int] = None) -> List[Any]:
    """The record's own `Q.PAGE_ARC` rows (empty when the gather ran with the flag OFF), of `page` when given. The measurement readout reads the record
    through this (benchmarks/omr-arc-binding-2026-10/page-ink-2026-11/step1); no stage reads it in step 1."""
    from .record import Q
    out = []
    for o in rec.obs_of(Q.PAGE_ARC):
        sub = str(getattr(o, "subject", "") or "")
        if page is None or sub == "page/%d" % page or sub.startswith("page/%d/" % page):
            out.append(o)
    return out

