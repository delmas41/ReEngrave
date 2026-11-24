"""ROADMAP 2.251 -- every clef on the page, read page-wide by its SHAPE, and the clef in force at each head (Sean 2026-11-01 "Build both").

PATH: STAGED. Step 1 (flag `OMR_CLEF_PAGEWIDE`, default ON) is a GATHER reader on the page-wide pass: it looks over every staff of
the page for clef-shaped, clef-sized ink -- header clefs and clefs inside a system alike -- and CLAIMS that ink at kind `clef` in the
claimed-area register (`claims.py`, owner `clef`, standing READ, source `clef_pagewide`), so the head / rest consult refuses a box on it
(later readers may mark claimed ink, never take it; CLAUDE §3). Step 2 (flag `OMR_CLEF_CARRY`, default OFF) is EVALUATE: `restate_pitch`
pitches each head from the clef printed LAST before it on its staff (`clef_in_force`).

CONVENTION ASSUMED: a clef change is a clef glyph on ONE staff, at or just before a barline or before the first note it governs, often
smaller than the header clef; it holds on that staff until the next printed clef, and a new system reprints the clef in force in its
header. WHAT WOULD FALSIFY IT: a cautionary clef at a system's end that governs nothing, or a change that applies to several staves.
NOT CONFIRMED by Sean beyond "Build both" (DECISIONS 2026-11-01); benchmarks/clef-change-2026-11/FINDINGS.md.

Two witnesses, never the detector's word alone (2.144 / 2.181: false `clef*` boxes stood over real eighths and rests):
* a C clef: the THICK BAR -- a run of columns >= `C_BAR_MIN_WIDTH_SPACES` wide, each holding one unbroken vertical ink run of at least
  `C_BAR_MIN_RUN_SPACES` that stops within `C_BAR_REACH_SPACES` of the staff (a barline runs on to the next staff, a stem is one or two px
  wide), and the BOWLS -- ink right of the bar in both its upper and lower half, roughly mirror images about the bar's middle. The
  middle of the clef measured from its top and bottom edges names the line (ROADMAP 2.324 r10, `c_outside_edges` / `name_c_bar`;
  `clef_geometry.resolve_clef`, the header readers' own snap). Litolff's C clefs inside a system are never boxed as clefs,
  so this test needs no box; a `clefC*` box is one more witness.
* an F clef: a clef-sized `clefF` box (the detector) AND its two dots straddling the line it names (`clef_locator._has_f_clef_dots`, the
  header locator's own veto), the box's top near the top line. The line comes from the dot pair; a pair that names no allowed line
  (`KINDS_READ`) is no witness, so an F clef is either claimed with its kind READ or not claimed (the detector's NARROWED claim stands).
* a G clef: a clef-sized `clefG` box reaching past the staff both above and below (a G clef's curl and tail).
A C clef whose kind cannot be read (no allowed line within the snap) is still CLAIMED -- its bar and bowls are the shape -- and filed
with `kind: None`; step 2 marks the notes after it unread, never pitched from the header clef (rule 8).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ENV = "OMR_CLEF_PAGEWIDE"
ENV_CARRY = "OMR_CLEF_CARRY"
SOURCE = "clef_pagewide"

#: the named line is searched this close to the bar's middle (under half a space: never a neighbouring line)
C_AXIS_SHIFT_SPACES = 0.45
#: the C clef's thick bar: this wide (staff spaces; a barline is ~0.3, a stem ~0.1; Litolff's small C clef bar measures 0.7-0.8)
C_BAR_MIN_WIDTH_SPACES = 0.45
C_BAR_MAX_WIDTH_SPACES = 1.3
#: ROADMAP 2.324 r2 (page-wide clef reader): a bar under `C_BAR_MIN_WIDTH_SPACES` is still a C clef's thick bar where a thin upright
#: line stands just right of it (within this gap, staff spaces), the thin line is a printed line (at least `C_THIN_MIN_SPACES` wide, never
#: a one-pixel sliver) and the bar is at least this many times as wide as that line. Measured on the frozen sample pages (the bars this
#: test admits, 16 pages): Breitkopf header C clefs 0.434/0.124, 0.438/0.156, 0.436/0.182, 0.44/0.183, 0.436/0.145 (2.4-3.5x); on the
#: other side a mid-staff G clef beside a barline, Litolff p8 (0.254/0.127, 2.0x, its bowls passed: the ratio is what refuses it), and
#: stems beside slivers (0.07-0.25 sp beside 0.036-0.07). The bowls still decide (never a C clef from a bar alone).
C_THIN_GAP_SPACES = 0.6
C_THIN_MIN_SPACES = 0.1
C_BAR_THICK_RATIO = 2.2
#: ROADMAP 2.324 r11 (Sean 2026-11-23 on Brahms p3 s1 staff 11: "The first tile is all alto clef"; p17 s1 staff 3: "The second tile
#: starts in tenor"): A C CLEF'S TWO BARS STAND SIDE BY SIDE AND RUN THE SAME HEIGHT -- the clef's own height, the thick one on the left.
#: Never a pair whose two strokes run different heights (a clef's spine beside a barline), never a thick bar as thin as a barline.
#: Where the thin bar beside it runs the same height, the thick bar needs only be clearly the thicker (`C_PAIR_THICK_RATIO`) and thicker
#: than any barline (`C_PAIR_MIN_WIDTH_SPACES`); a scan nick in the thick bar's edge column shortens its measured width and the
#: 2.2x ratio above alone refused three real Breitkopf C clefs. MEASURED (lane-2.324-r11, page binaries, the bars' own columns):
#: reading side -- Brahms p3 s1 st11 alto 0.396 beside 0.216 (1.83x), p10 s1 st11 alto 0.404/0.183 (2.2x, on the cut), p17 s1 st3
#: tenor 0.436/0.218 (2.0x), the two bars' tops and bottoms within 0.06 space; refusing side -- Litolff p8's mid-staff G clef beside a
#: barline (0.254/0.127, its two strokes 3.24 and 4.29 spaces tall: not one height, and under the width), barlines 0.06-0.25, stems
#: 0.04-0.25. Both cuts are numbers from two plates; the bowls still decide (never a C clef from its bars alone).
C_PAIR_THICK_RATIO = 1.5
C_PAIR_MIN_WIDTH_SPACES = 0.35
#: ... "the same height": the two bars' tops, and their bottoms, within this (staff spaces)
C_PAIR_EDGE_SPACES = 0.25
#: r11: the F clef's never "no F clef on a C clef's bars" looks for the bars this far left of the F place (staff spaces). Brahms p3 s1
#: staff 11: the ink piece the F test was handed began at the C clef's THIN bar, and half a space left of it held only part of the thick
#: bar (0.32 space): the pair went unseen and the C clef's upper bowl passed as the two dots. A whole C clef's bars and gap are under one
#: space wide (0.4 + 0.3 + 0.22 measured); before r11 this was half a space.
F_NEVER_C_REACH_SPACES = 1.0
#: ... each column holding one unbroken ink run this long (the small C clef spans 3.6-3.7 sp, a full one ~4.3)
C_BAR_MIN_RUN_SPACES = 3.0
#: ... that starts and ends within this of the staff's top / bottom line (a barline or a bracket runs on to the next staff)
C_BAR_REACH_SPACES = 1.3
#: the glyph ends at the first gap this wide (staff spaces) right of the bar (between the thick and thin bars stands at most ~0.3)
C_GLYPH_GAP_SPACES = 0.35
#: ROADMAP 2.324 r8: ... and before the first column whose unbroken ink runs on more than this past the bar's top or bottom (a stem, a
#: barline touching the bowls: Brahms p4 s1 staff 3). The clef's own ink stays within its bar's height; the margin is a cut on two plates
C_OWN_PAST_SPACES = 0.5
#: the bowls: ink right of the bar within this reach (staff spaces from the bar's right edge) ...
C_BOWL_REACH_SPACES = 2.2
#: ... in BOTH halves (above and below the bar's middle) at least this share of the half's area (a repeat sign's dots are far below it)
C_BOWL_MIN_FILL = 0.3
#: ... and the two halves mirror images: |upper - lower| / max at most this
C_BOWL_MAX_ASYMMETRY = 0.5
#: ROADMAP 2.324 r10 (Sean 2026-11-22, two small Litolff C clefs: "They all look like tenor clefs"; "Needs to be read - never assumed"):
#: "The best bet at determining what clef it is is measuring the middle of the clef and aligning it with a staff line"; "Mesure from
#: the outside to get the midddle"): A C CLEF NAMES THE STAFF LINE THROUGH THE MIDDLE OF THE CLEF, MEASURED FROM ITS TOP AND BOTTOM
#: EDGES (`c_outside_edges`) -- never from the instrument or another clef on the staff, never where its ink balances. The clef's own
#: piece is the thick bar and the ink joined to it in the clef's columns, staff lines passing through it set aside; it reaches at most
#: `C_OUTSIDE_REACH_SPACES` past the bar's own top and bottom (on the 61 C clefs of the frozen sample, Litolff and Breitkopf: at 0.3
#: every middle lands nearest the line the clef is read on, within 0.32 of it and 0.70 or more from the next; at 1.0 a stem, slur or
#: line below joins in and 4 are named wrong). The middle names alto or tenor (`name_c_bar`).
C_OUTSIDE_REACH_SPACES = 0.3
#: a middle ABOVE the tenor line or BELOW the alto line has no second C line on that side, so the nearer one names it -- while it is
#: nearer that line than the next staff line out (under half a space; at half a space it sits as near the fifth or second line, not a
#: C clef read on an instrumental staff). Measured on the 61: up to 0.41 above the tenor line (Litolff p4 s1 st3 bar 3, Sean: tenor),
#: 0.20 below the alto line
C_OUTER_REACH_SPACES = 0.5
#: the clef's columns end this far (staff spaces) short of another mark's stroke standing within `C_STROKE_REACH_SPACES` right of the
#: glyph (a barline's ragged edge touches the bowls: Litolff p11 s0 staff 2 bar 15), a stroke being a column whose unbroken ink runs on
#: more than `C_STROKE_PAST_SPACES` past the bar's top or bottom
C_STROKE_TRIM_SPACES = 0.15
C_STROKE_REACH_SPACES = 0.3
C_STROKE_PAST_SPACES = 0.3
#: a G clef box reaches past the staff by this much above and below
G_REACH_SPACES = 0.6
#: a bar candidate is a G clef's spine where ink stands in BOTH bands this far past the staff (staff spaces, from .. to) beside it
G_PAST_SPACES = (1.4, 2.2)
G_PAST_MIN_FILL = 0.05
#: ... or the G clef's tail: ink in the band this far below the bottom line (from .. to, staff spaces), beside the spine, at least
#: this share (measured on Litolff pp. 2-16: header G clefs 0.42-0.56; every C clef, header or inside a system, at most 0.15)
G_TAIL_SPACES = (0.6, 1.6)
G_TAIL_MIN_FILL = 0.3
#: an F clef box's top stands this close to the top line
F_TOP_REACH_SPACES = 1.0
#: staff-line rows are cleared within this of each line (staff spaces) where a row's ink runs across this share of the window
LINE_HALF_SPACES = 0.3
#: ... and for the C clef's bowls, every row this close to the line measured at the clef (the bowls' fills were set with it)
BOWL_LINE_HALF_SPACES = 0.08
LINE_ROW_MIN_FILL = 0.5
#: the local line search: rows within this of the nominal line, over this many columns left of the clef
LOCAL_LINE_REACH_SPACES = 0.6
LOCAL_LINE_WINDOW_SPACES = 4.0
#: the lines a clef may name and be READ (a convention prior on these plates: the bass F clef, the alto and tenor C clefs); a clef
#: whose line comes out anywhere else is claimed but its kind UNREAD -- never a rare clef from a measurement near a cut
KINDS_READ = {"F": (4,), "C": (3, 4)}
#: a column of the dot window holding an unbroken raw ink run this long (staff spaces) is a stem / barline: cleared before the dots
DOT_STROKE_CLEAR_SPACES = 1.8
#: the F body: pieces starting at most this far (staff spaces) left of its largest piece
F_BODY_LEFT_REACH_SPACES = 0.6
#: a dot candidate whose centre column holds an unbroken ink run this long (staff spaces, lines included) is a stroke's piece
DOT_NOT_A_STROKE_SPACES = 1.5
#: a clef starting within this many staff spaces of the staff's first cell's left edge is the system's header clef
HEADER_WINDOW_SPACES = 6.0


def enabled() -> bool:
    """`OMR_CLEF_PAGEWIDE` (ROADMAP 2.251 step 1), default ON (Sean 2026-11-02 "Land"); an explicit 0/false/no/off disables."""
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off")


def carry_enabled() -> bool:
    """`OMR_CLEF_CARRY` (ROADMAP 2.251 step 2; Sean 2026-11-02 "Land now"), default ON; an explicit 0/false/no/off disables. Reads step 1's rows."""
    return os.environ.get(ENV_CARRY, "").strip().lower() not in ("0", "false", "no", "off")


ENV_STRONG_STOP = "OMR_CLEF_CARRY_STRONG_STOP"
#: the `why` of a candidate that is a detector `clef*` box too small to be a clef-sized claim and NOTHING else (no body template score, no
#: clef-sized box failing a later shape test): `gather` files it for a clef the detector boxed small (Litolff Vc bar 411).
WEAK_CANDIDATE_WHY = "clef_box_not_clef_sized"


def strong_stop_enabled() -> bool:
    """`OMR_CLEF_CARRY_STRONG_STOP`, default ON, deny-list (ROADMAP 2.261 fix 3): only a candidate with a SHAPE witness stops a carried clef; a small
    detector `clef*` box with no shape witness is counted (its abstention row stays) and never a stop.

    CAUSE (Litolff p6 sys1 staff3, p14 sys0 staff10; 27 notes unpitched, `clef_in_force`): `clef_in_force` stopped the carry at ANY candidate
    after a change of another kind than the header's. 33 of the 80 Litolff candidates are `clef_box_not_clef_sized` -- a 1.2-1.5 sp
    `clefG`/`clefF` box (an eighth rest, a head) at confidence 0.5-0.8 and no witness of shape -- and where one stood after a read bass clef
    the whole staff to its right was blanked. Sean's 11-02 stop rulings (bar 111, Vc bar 346) were F clefs seen by the body template
    (`body_score` 0.69-0.73): they keep stopping. LESSON: a stop is a refusal to pitch; it needs the evidence a read would need, or a doubt
    about one bar becomes silence for a staff (CLAUDE rule 8).
    CONVENTION ASSUMED: a detector clef box under clef size with no body score is not a clef printed there. WHAT WOULD FALSIFY IT: a real
    return clef boxed small and read by nothing else, whose notes the flag then pitches from the clef before it. NOT CONFIRMED."""
    return os.environ.get(ENV_STRONG_STOP, "").strip().lower() not in ("0", "false", "no", "off")


#: ROADMAP 2.324 (landed ON 2026-11-21, Sean 2026-11-19 "It should only be read once at a page level"): this page-wide pass reads EVERY clef
#: on the page -- the start-of-staff clef too, not only changes -- each owned by the staff whose lines it sits on and claimed once; it is the
#: only clef reader (no flag: the per-cell readers and the register's clef claims are retired).
#: ROADMAP 2.324: the lines a HEADER G clef may name and be READ (the treble clef); anywhere else it is claimed, kind UNREAD
G_LINES_READ = (2,)
#: ROADMAP 2.324: a clef box is THIS staff's only where its middle stands within this many staff spaces of this staff's own lines,
#: measured at the box (a measure cell is the staff plus four spaces of air, so a neighbour's clef shows in it: FINDINGS 2.324, 7 of 29
#: clef marks on Brahms p12 were claimed on the wrong staff). A G clef's middle stands inside the staff, an F clef's on its upper half.
OWN_STAFF_REACH_SPACES = 1.0
#: ROADMAP 2.324: a header G clef's second witness -- its own ink past the staff on BOTH sides, inside the box's columns: the loop above
#: the top line and the tail below the bottom line (bands from .. to, staff spaces past the line), each at least this share of the band
G_BOX_ABOVE_SPACES = (0.4, 1.4)
G_BOX_BELOW_SPACES = (0.4, 1.4)
G_BOX_PAST_MIN_FILL = 0.08


def cell_lines_page(cell: Any) -> Optional[List[float]]:
    """ROADMAP 2.324 r3: the five staff lines of ONE measure cell in page px -- the bar's own lines, as the cell was cut with them
    (`measure_extractor` traces each cell's grid on its own columns: `OMR_CELL_LINE_TRACE` / `OMR_CELL_LINE_FIND`). None where the cell
    has no five-line grid. CLAUDE §5: measure against the staff locally, at the subject's own bar's lines, never a staff-wide value."""
    ys = list(getattr(cell, "staff_line_ys_canonical", None) or ())
    bb = getattr(cell, "bbox_page_px", None)
    up = getattr(cell, "upscale_factor", None)
    if len(ys) != 5 or not bb or not up:
        return None
    return [float(bb[1]) + float(y) / float(up) for y in ys]


def on_this_staff(box: Sequence[float], lines: Sequence[float], sp: float) -> bool:
    """Whether a clef box's middle stands on THIS staff (`OWN_STAFF_REACH_SPACES`), against the staff's lines measured at the box."""
    cy = (float(box[1]) + float(box[3])) / 2.0
    return float(lines[0]) - OWN_STAFF_REACH_SPACES * sp <= cy <= float(lines[-1]) + OWN_STAFF_REACH_SPACES * sp


def g_witness(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float) -> Dict[str, Any]:
    """A header G clef's second witness (ROADMAP 2.324): the clef's own INK runs past the staff on both sides, in the box's columns --
    the loop above the top line, the tail below the bottom line (`G_BOX_*`). Measures both fills; {passed, why, above_fill, below_fill}.

    The box says WHERE to look (its columns), never what the mark is: round 3 dropped round 2's test that the BOX itself reaches past
    the staff (`G_REACH_SPACES`). `lines` must be the staff's lines measured AT the clef (the header cell's own traced lines, then
    `local_lines`): round 3's cause -- on Litolff's first systems the staff-wide lines stand up to 1.1 spaces above the printed lines
    at the header, so the band "above the staff" fell on blank paper above the clef and the clef was refused."""
    H, W = ink.shape
    top, bot = float(lines[0]), float(lines[-1])
    x0, x1 = max(0, int(box[0])), min(W, int(round(box[2])))
    out: Dict[str, Any] = {"above_fill": None, "below_fill": None}
    if x1 - x0 < 2:
        return dict(out, passed=False, why="g_box_too_narrow")
    a = ink[max(0, int(top - G_BOX_ABOVE_SPACES[1] * sp)):max(0, int(top - G_BOX_ABOVE_SPACES[0] * sp)), x0:x1]
    b = ink[min(H, int(bot + G_BOX_BELOW_SPACES[0] * sp)):min(H, int(bot + G_BOX_BELOW_SPACES[1] * sp)), x0:x1]
    fa = round(float(a.mean()), 3) if a.size else 0.0
    fb = round(float(b.mean()), 3) if b.size else 0.0
    out.update(above_fill=fa, below_fill=fb)
    if fa < G_BOX_PAST_MIN_FILL or fb < G_BOX_PAST_MIN_FILL:
        return dict(out, passed=False, why="g_no_ink_past_the_staff")
    return dict(out, passed=True, why=None)


def read_header_g(name: str, box: Sequence[float], ink: np.ndarray, lines: Sequence[float], sp: float) -> Dict[str, Any]:
    """`read_box` for a clef-sized `clefG` box in a system's HEADER window (ROADMAP 2.324): the box AND its ink past the staff
    (`g_witness`). The kind is the plain treble clef where the class names it (`clef_geometry.clef_name_from_class`: the G family's
    line is not measured by geometry, the same as every header reader today); any other G class (an octave G) is claimed with kind
    None (UNREAD), never a rare clef."""
    from ..clef_geometry import clef_name_from_class
    w = g_witness(ink, box, lines, sp)
    out: Dict[str, Any] = {"family": "G", "cls": str(name), "kind": None, "line": None, "residual": None,
                           "g_fill": {"above": w["above_fill"], "below": w["below_fill"]}}
    if not w["passed"]:
        return dict(out, passed=False, why=w["why"])
    nm = clef_name_from_class(str(name))
    if nm != "treble":
        return dict(out, passed=True, why=None)
    return dict(out, passed=True, why=None, kind=nm, line=G_LINES_READ[0])


#: ROADMAP 2.324 r2: an F clef's dots stand in the two spaces either side of its line (line 4: the second line from the top), just right of
#: its body. Looked at as INK AT THOSE TWO PLACES, not as two separate components (Litolff merges: the dots touch the key flats beside them).
#: The dot is looked for in a square this wide (staff spaces) centred half a space above and below the line ...
F_DOT_SQUARE_SPACES = 0.3
#: ... at the same x, anywhere from this far left of the box's right edge to this far right of it (staff spaces) ...
F_DOT_SEARCH_SPACES = (-0.4, 1.3)
#: ... each square at least this share ink, the staff lines and long upright strokes cleared (`_dot_mask`). Measured (2x2 pages, the
#: smaller of the two fills): the four Litolff header bass clefs the dot-PAIR test missed 0.80-1.0, every header bass clef 0.74-1.0 but
#: one (0.38, read by the pair test); on the other side a header C clef's bowls 0.47-0.64, a header G clef 0.0-0.48
F_DOT_MIN_FILL = 0.7
#: round 3: the dot's square may stand anywhere in this middle part of its space (shares of the gap between the two lines, measured)
F_DOT_SPACE_MIDDLE = (0.25, 0.75)


def f_dot_places(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float) -> Dict[str, Any]:
    """ROADMAP 2.324 r2 (a musician's look at an F clef's dots): dot ink at BOTH places -- half a space above and half a space below the
    clef's line 4, at one x just right of its body -- whatever that ink touches. {passed, x, upper, lower}: the best x (both fills' smaller
    one largest) and its two fills. NEVER an F clef with no ink at either place: both fills must reach `F_DOT_MIN_FILL`."""
    H, W = ink.shape
    ll = [float(v) for v in lines]
    line4 = ll[1]
    half = max(1, int(round(F_DOT_SQUARE_SPACES * sp / 2.0)))
    xa = max(0, int(float(box[2]) + F_DOT_SEARCH_SPACES[0] * sp) - half)
    xb = min(W, int(float(box[2]) + F_DOT_SEARCH_SPACES[1] * sp) + half + 1)
    ya, yb = max(0, int(ll[0] - sp)), min(H, int(ll[2] + sp))
    out: Dict[str, Any] = {"passed": False, "x": None, "upper": 0.0, "lower": 0.0}
    if xb - xa < 2 * half + 1 or yb - ya < 3:
        return out
    m = _dot_mask(ink, ya, yb, xa, xb, ll, sp).astype(bool)
    # round 3 (Litolff p6 s1 staff 10, p8 s0 staff 8: thick lines, a warped scan): the dot stands IN THE SPACE, not at a point half a
    # space from the line -- each square's centre may sit anywhere in the middle half of its own space, between the lines measured here
    def _rows(lo: float, hi: float) -> List[int]:
        g = hi - lo
        return sorted({int(round(v)) - ya for v in np.arange(lo + F_DOT_SPACE_MIDDLE[0] * g, lo + F_DOT_SPACE_MIDDLE[1] * g + 0.5, 1.0)})
    yus, yls = _rows(ll[0], ll[1]), _rows(ll[1], ll[2])
    best = None
    for cx in range(half, m.shape[1] - half):
        fu = max(float(m[max(0, y - half):y + half + 1, cx - half:cx + half + 1].mean()) for y in yus)
        fl = max(float(m[max(0, y - half):y + half + 1, cx - half:cx + half + 1].mean()) for y in yls)
        if best is None or min(fu, fl) > min(best[1], best[2]):
            best = (xa + cx, fu, fl)
    if best is None:
        return out
    return {"passed": min(best[1], best[2]) >= F_DOT_MIN_FILL, "x": float(best[0]), "upper": round(best[1], 3), "lower": round(best[2], 3)}


#: ROADMAP 2.324 r4: an F clef's body (its ball and curve, `f_body`) starts AT the top line -- its ink top within this many staff spaces
#: of the top line measured at the clef. MEASURED on the frozen sample's clef-sized `clefF` boxes inside a system, against the bar's own
#: lines: every real F clef 0.09-0.38 (16 Litolff and Brahms changes, Sean's labelled Brahms p0 staff 12 bar 5 among them); every box
#: that is not a clef (our look: an 'sf', a half note, a flag, two rests, a flag on Brahms, a half note by a barline) 0.72 or more from
#: it, above or below. A cut on two plates (CLAUDE §4).
F_BODY_TOP_SPACES = 0.55
#: ... and a mid-line F clef is READ (written plain) only with room on both of its cuts: the smaller dot fill at least this (the cut is
#: `F_DOT_MIN_FILL`) and the body top within this of the top line. Between the cut and this margin it NARROWS (a strong candidate:
#: the clef in force stops there, its notes go unread) -- never written plain on a reading that rests on a number from two plates.
F_DOT_PLAIN_FILL = 0.8
F_BODY_TOP_PLAIN_SPACES = 0.45


#: the `read_mid_f` refusals that say the ink is NOT an F clef (its body is not an F clef's, or it is a G's or a C's ink): such a box is
#: no clef-shaped candidate -- a carried clef never stops at it (Brahms p25 s0 staff 3: a half note by the barline under a `clefF` box
#: stopped the bass clef read just before it, and bars 1-9 went unread)
MID_F_NOT_A_CLEF = ("f_body_not_at_the_top_line", "f_box_ink_past_the_staff_like_a_g", "g_over_a_notehead",
                    "f_box_on_a_c_bar", "f_no_body_ink")

#: ROADMAP 2.324 r8 (CLAUDE rule 8; Sean 2026-11-20, his r5 tiles 1 and 10 "refused OUTRIGHT"): every refusal that says the ink is NOT a
#: clef on this staff -- the mark breaks a never of its clef's shape, or stands on another staff. Nothing downstream sees it: no carry
#: candidate, no NARROWED claim. Every OTHER refusal is a POSSIBLE clef (one witness seen, the other missing or near its cut): the clef in
#: force stops there (`clef_in_force`) and its ink is claimed NARROWED. The ink evidence that separates them:
#:   * G: a treble clef always runs past the staff above AND below and curls round line 2 (`read_g`). No ink past the staff, or a
#:     notehead's own ink on the glyph (Sean's r5 tiles 1 and 10), is no clef. No curl seen where the INK is the only witness is no clef
#:     (Sean's spiral ruling); no curl seen where the detector's G box says treble and the ink runs past the staff both sides is two
#:     witnesses disagreeing -- CANNOT TELL (r8b, rule 8): a possible, STRONG clef (`G_BOX_NO_CURL`); 13 of the sample's 221 printed
#:     start-of-staff trebles show no curl once their lines are cleared (Litolff p6 s0 staff 1);
#:   * F: the body starts at the top line and is no G's or C's ink (`read_mid_f`'s nevers: not a clef); body seen but a dot missing,
#:     or both seen near their cuts, is a possible clef (Litolff p10 s0 staff 3 and p4 s1 staff 3: real bass clefs whose dots fuse);
#:   * C: a thick bar with bowls both sides; a bar too wide (a beam end, a time signature's figure) or with no bowls is not a clef; bowls
#:     seen but not mirrored is a possible clef;
#:   * a box whose ink stands on another staff belongs to that staff (`on_this_staff`), never this one.
NOT_A_CLEF = MID_F_NOT_A_CLEF + ("box_on_another_staff", "g_no_ink", "g_box_too_narrow", "g_no_ink_past_the_staff",
                                 "g_no_curl_round_line_2", "bar_too_wide", "no_bowls")
#: r8b: the refusal of a mid-line detector `clefG` box whose ink runs past the staff both sides with no curl seen -- a POSSIBLE clef
G_BOX_NO_CURL = "g_box_says_g_no_curl_seen"


def read_mid_f(name: str, box: Sequence[float], ink: np.ndarray, lines: Sequence[float], sp: float, *,
               dots_beside_core: bool = False) -> Dict[str, Any]:
    """ROADMAP 2.324 r4 (Sean 2026-11-20 "Teach it"): an F clef printed INSIDE a line, read on the page-wide pass by its own ink like
    the clef at the start of the staff. `lines`: the staff's lines at the clef, from its own bar's traced grid. The box says where to
    look; the ink says what it is:
      * its BODY starts at the top line (`F_BODY_TOP_SPACES`) -- never from the box's top edge (round 2's `F_TOP_REACH_SPACES` test);
      * dot ink at BOTH places, one in each space either side of line 4 (`f_dot_places`, whatever the dots touch: here they touch the
        clef's own curve, a stem or a barline, so the dot PAIR test of 2.251 found no separate pair -- the round-4 cause);
      * never a G clef's ink (`g_witness`: past the staff above AND below) and never on a C clef's thick bar (`c_bars`).
    NEVER over a notehead, an accidental or a rest that merely has ink at the dot places: their body does not start at the top line,
    or no dot ink stands in one of the two spaces. {passed, plain, why, kind, line, body_top, dots}."""
    out: Dict[str, Any] = {"family": "F", "cls": str(name), "kind": None, "line": None, "residual": None, "plain": False}
    body = f_body(ink, box, lines, sp, wide=True)
    if body is None:
        return dict(out, passed=False, why="f_no_body_ink")
    btop = (float(body[1]) - float(lines[0])) / sp
    out.update(body=body, body_top=round(btop, 3))
    if abs(btop) > F_BODY_TOP_SPACES:
        return dict(out, passed=False, why="f_body_not_at_the_top_line")
    if g_witness(ink, box, lines, sp)["passed"]:
        return dict(out, passed=False, why="f_box_ink_past_the_staff_like_a_g")
    if any(b["why"] not in ("bar_too_thin", "bar_too_wide", "g_clef_shape")
           for b in c_bars(ink, lines, sp, float(box[0]) - F_NEVER_C_REACH_SPACES * sp, float(box[2]))):
        return dict(out, passed=False, why="f_box_on_a_c_bar")
    right = float(box[2])
    if dots_beside_core:
        # round 5: a place found by ink (no box) may run on over the key accidentals: the dots are looked for beside the body's core
        core = f_body(ink, box, lines, sp, wide=True, core=True)
        right = float(core[2]) if core else float(body[2])
    fp = f_dot_places(ink, [box[0], box[1], right, box[3]], lines, sp)
    out["dots"] = {"upper": fp["upper"], "lower": fp["lower"], "x": fp["x"]}
    if not fp["passed"]:
        # round 5: no dot ink in one of the two spaces is no F clef (Litolff's quarter rest; and Litolff p10 s0 staff 3, whose lower dot
        # goes with a thick line -- its header clef is already bass, so nothing is lost there). Round 4's body-bottom never and its
        # shape-only narrowing are gone: both rested on where the line clearing cut the clef's tail (header F tails reach the bottom line)
        return dict(out, passed=False, why="f_no_dot_ink_in_both_spaces")
    if fp["x"] is not None:
        out["dots_right"] = float(fp["x"]) + 0.3 * sp
    plain = min(fp["upper"], fp["lower"]) >= F_DOT_PLAIN_FILL and abs(btop) <= F_BODY_TOP_PLAIN_SPACES
    return dict(out, passed=True, plain=bool(plain), why=None, kind="bass", line=4, witness="f_dot_places")


#: ROADMAP 2.324 r6 (Sean "Do what ever it takes"): a treble clef is one stroke that curls round the second line, and its own upright
#: stroke runs down through the curl -- so the paper inside the curl is cut in two: paper the glyph's own ink encloses, on BOTH sides of
#: that stroke, each across line 2. Round 5 counted a hole's SIZE, and the hollow heads of a half-note chord enclose holes too (Sean's r5
#: tile 10): a hole is not a curl. The curl is counted as the enclosed paper regions that cross line 2's neighbourhood (within
#: `G_CURL_BAND_SPACES` of it) side by side, separated by ink, each at least `G_CURL_MIN_SPACES2`; a curl needs `G_CURL_MIN_REGIONS`.
#: MEASURED (the bridged glyph of each place, the cell's own lines): start-of-staff treble clefs of the frozen sample 208 of 221 have 2
#: or more (13 have 0-1: read there by their box), bass 0 of 98; Sean's judged mid-line tiles: treble (tile 5) 3, half-note chord
#: (tile 10) 1, stem (tile 1) 0; the 788 hollow heads of the nine touched pages looked at as a clef's place: 2 reach 2 with ink past
#: the staff (one is the treble clef of Litolff p6 s1 staff 0 itself, one an 'ff' under a ledger note). C clefs' bowls reach 2 too --
#: the C clef's own bar is read first. The band and the area are cuts on two plates; the count of 2 is the shape.
G_CURL_BAND_SPACES = 0.3
G_CURL_MIN_SPACES2 = 0.05
G_CURL_MIN_REGIONS = 2


def _bridge_line_rows(ink: np.ndarray, sub: np.ndarray, y0: int, y1: int, x0: int, x1: int, lines: Sequence[float], sp: float) -> np.ndarray:
    """ROADMAP 2.324 r7b: put back, in each band of cleared staff-line rows, the page's ink in the columns where the mark's own (line-
    cleared) ink touches the band from just above or just below -- a stroke crossing the line is one stroke again; a line by itself
    and two marks that only come near each other stay apart."""
    out = sub.copy()
    rows = sorted(set(y for y in line_rows(ink, lines, sp, x0, x1) if y0 <= y < y1))
    bands, cur = [], []
    for y in rows:
        if cur and y != cur[-1] + 1:
            bands.append(cur)
            cur = []
        cur.append(y)
    if cur:
        bands.append(cur)
    for band in bands:
        a, b = band[0] - y0, band[-1] - y0
        above = sub[a - 1] if a - 1 >= 0 else np.zeros(sub.shape[1], dtype=sub.dtype)
        below = sub[b + 1] if b + 1 < sub.shape[0] else np.zeros(sub.shape[1], dtype=sub.dtype)
        cols = (above > 0) | (below > 0)
        for r in range(a, b + 1):
            out[r, cols] = ink[y0 + r, x0:x1][cols].astype(out.dtype)
    return out


def glyph_piece(ink: np.ndarray, place: Sequence[float], lines: Sequence[float], sp: float) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.324 r5: the largest piece of ink in `place` (page px), the staff lines cleared where they run (`line_rows`, judged on
    a wide strip) and bridged back across them (a vertical close one cleared band tall) -- the glyph as its own ink, joined by ink,
    never by a box. {box, piece} or None. The SHAPE is measured on this piece; what the clef CLAIMS is `own_ink_box` (round 7b)."""
    import cv2
    H, W = ink.shape
    x0, y0, x1, y1 = max(0, int(round(place[0]))), max(0, int(round(place[1]))), min(W, int(round(place[2]))), min(H, int(round(place[3])))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    half = max(1, int(round(LINE_HALF_SPACES * sp)))
    sub = _mask_wide_lines(ink, y0, y1, x0, x1, lines, sp, strokes=False)
    m = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 2 * half + 1)))
    n, lab, st, _c = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 1:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = (int(v) for v in st[i, :4])
    return {"box": [float(x0 + x), float(y0 + y), float(x0 + x + w), float(y0 + y + h)], "piece": lab[y:y + h, x:x + w] == i}


def own_ink_box(ink: np.ndarray, pc: Dict[str, Any], lines: Sequence[float], sp: float) -> List[float]:
    """ROADMAP 2.324 r7b (Sean: the clef claims only its own ink): the box of the clef's OWN ink inside its measured piece -- the pieces
    of ink, joined across the staff lines only (`_bridge_line_rows`), that lie in the piece and stand on the staff (meet the rows from the
    top line to the bottom line). A word or mark over or under the staff that the measuring close joined to the clef (Brahms p14 s1
    staff 9: "div." over the treble clef) stands off the staff and is never claimed. Falls back to the piece's box where nothing is
    found. Measures.

    Round 8 (Litolff p8 s0 staff 6: the start-of-staff treble clef touches the system's barline and claimed it): a barline standing at
    the glyph's left edge (`barline_left_of`, the same test the no-box header reader cuts its place with) is never the clef's -- the
    claim starts right of it."""
    import cv2
    gb = pc["box"]
    x0, y0, x1, y1 = int(gb[0]), int(gb[1]), int(round(gb[2])), int(round(gb[3]))
    sub = _mask_wide_lines(ink, y0, y1, x0, x1, lines, sp, strokes=False)
    m = _bridge_line_rows(ink, sub, y0, y1, x0, x1, lines, sp)
    piece = pc["piece"][: m.shape[0], : m.shape[1]]
    m = (m.astype(bool) & piece).astype(np.uint8)
    bl = barline_left_of(ink, lines, sp, float(gb[0]) - 0.5 * sp, float(gb[0]) + 0.8 * sp)
    if bl is not None and bl + 1 - x0 < m.shape[1]:
        m[:, : max(0, bl + 1 - x0)] = 0
    n, lab, st, _c = cv2.connectedComponentsWithStats(m, connectivity=8)
    top, bot = int(round(float(lines[0]))) - y0, int(round(float(lines[-1]))) - y0
    keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_TOP] <= bot and st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] >= top]
    if not keep:
        return [float(v) for v in gb]
    return [float(x0 + min(st[i, 0] for i in keep)), float(y0 + min(st[i, 1] for i in keep)),
            float(x0 + max(st[i, 0] + st[i, 2] for i in keep)), float(y0 + max(st[i, 1] + st[i, 3] for i in keep))]


def curl_round_line2(pc: Dict[str, Any], lines: Sequence[float], sp: float) -> int:
    """ROADMAP 2.324 r6: how many separate paper regions enclosed by the glyph's own ink lie across line 2 (from the bottom), side by
    side -- the treble clef's curl cut by its own upright stroke (`G_CURL_*`). Measures."""
    import cv2
    cs, hier = cv2.findContours(pc["piece"].astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return 0
    y0, l2 = pc["box"][1], float(lines[3])
    cross = []
    for c, hh in zip(cs, hier[0]):
        if hh[3] < 0:
            continue
        x, y, w, h = cv2.boundingRect(c)
        if cv2.contourArea(c) / (sp * sp) < G_CURL_MIN_SPACES2:
            continue
        if y0 + y <= l2 + G_CURL_BAND_SPACES * sp and y0 + y + h >= l2 - G_CURL_BAND_SPACES * sp:
            cross.append((x, x + w))
    n, right = 0, -1e9
    for x, x1 in sorted(cross):
        if x >= right:
            n += 1
            right = x1
    return n


#: ROADMAP 2.324 r5b: how far a clef's ink reaches past the staff (staff spaces, above the top line / below the bottom line). Ink joined
#: to a clef beyond this (a barline, a brace, a dynamic) is never the clef's: the claim stops here where no stroke boundary separates it.
#: MEASURED on the frozen sample's start-of-staff clefs: treble reach above 1.14-2.51, below 1.44-2.51; a bass clef's body and dots stand
#: on the staff (its tail at most at the bottom line).
CLEF_REACH_SPACES = {"G": (2.7, 2.7), "F": (0.5, 0.6), "C": (0.6, 0.6)}
#: ... a notehead's own ink inside a G clef's glyph: at least this share of the head box's ink on the glyph's ink (Sean's r5 tiles 1 and
#: 10: a stem and a half-note chord, each with the detector's notehead boxes on the ink, under a `clefG` box). MEASURED: no `clefG` box
#: of the frozen sample's 242 start-of-staff ones holds a notehead box; both of Sean's non-clefs do.
G_HEAD_INK_SHARE = 0.5


def within_reach(box: Sequence[float], family: str, lines: Sequence[float], sp: float) -> List[float]:
    """ROADMAP 2.324 r5b: a clef's area cut to what a clef of `family` can reach past the staff (`CLEF_REACH_SPACES`)."""
    up, down = CLEF_REACH_SPACES.get(family, (2.7, 2.7))
    return [float(box[0]), max(float(box[1]), float(lines[0]) - up * sp), float(box[2]), min(float(box[3]), float(lines[-1]) + down * sp)]


def heads_in_glyph(ink: np.ndarray, pc: Dict[str, Any], heads: Sequence[Sequence[float]], lines: Sequence[float],
                   sp: float) -> List[float]:
    """For each notehead box (page px) meeting the glyph: the share of the box's ink JOINED to the glyph's ink (one piece of ink, the
    staff lines cleared and bridged as `glyph_piece` does) -- a head on the clef's own stroke, joined by ink, never by box overlap. Measures."""
    import cv2
    gb = pc["box"]
    out = []
    H, W = ink.shape
    for h in heads:
        if h[2] <= gb[0] or h[0] >= gb[2] or h[3] <= gb[1] or h[1] >= gb[3]:
            continue
        x0, y0 = max(0, int(min(gb[0], h[0]))), max(0, int(min(gb[1], h[1])))
        x1, y1 = min(W, int(round(max(gb[2], h[2])))), min(H, int(round(max(gb[3], h[3]))))
        half = max(1, int(round(LINE_HALF_SPACES * sp)))
        sub = _mask_wide_lines(ink, y0, y1, x0, x1, lines, sp, strokes=False)
        m = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 2 * half + 1)))
        n, lab = cv2.connectedComponents(m, connectivity=8)
        gy0, gx0 = int(gb[1]) - y0, int(gb[0]) - x0
        gl = lab[gy0:gy0 + pc["piece"].shape[0], gx0:gx0 + pc["piece"].shape[1]]
        gl = gl[: pc["piece"].shape[0], : pc["piece"].shape[1]]
        vals = gl[pc["piece"][: gl.shape[0], : gl.shape[1]] & (gl > 0)]
        if vals.size == 0:
            continue
        g_id = int(np.bincount(vals).argmax())
        hy0, hx0 = int(h[1]) - y0, int(h[0]) - x0
        hl = lab[max(0, hy0):int(round(h[3])) - y0, max(0, hx0):int(round(h[2])) - x0]
        hi = ink[max(0, int(h[1])):int(round(h[3])), max(0, int(h[0])):int(round(h[2]))][: hl.shape[0], : hl.shape[1]]
        tot = float(hi.sum())
        if tot <= 0:
            continue
        out.append(round(float((hi & (hl == g_id)).sum()) / tot, 3))
    return out


def read_g(ink: np.ndarray, place: Sequence[float], lines: Sequence[float], sp: float, *, box_witness: bool,
           heads: Sequence[Sequence[float]] = ()) -> Dict[str, Any]:
    """ROADMAP 2.324 r5/r6: the ONE G-clef test, wherever the clef stands. A musician: a treble clef is one stroke that curls round
    the second line; the curl is its spiral; the stroke runs past the staff above and below. The glyph is its own ink in `place`
    (`glyph_piece`); its ink runs past the staff on BOTH sides (`g_witness`, on the glyph's own columns) -- required -- and the CURL round
    line 2 (`curl_round_line2`: the curl's paper on both sides of the stroke through it). NEVER over blank paper (no ink, no read), never
    over a stem (no curl: Sean's r5 tile 1), never over a notehead (a half-note chord's hollow heads are one ring each, not a curl cut by
    a stroke: tile 10) -- the curl refuses those by itself; a notehead's ink joined to the glyph (`heads`, the detector's head boxes as
    where to look) is kept as a second witness. Where no curl is seen, a detector `clefG` box (`box_witness`) still reads at the START of
    a staff (13 of the sample's 221 printed treble clefs show no curl once their lines are cleared) and only NARROWS inside a line.
    {passed, why, kind, line, box, curl, witness}."""
    out: Dict[str, Any] = {"family": "G", "cls": "clefG", "kind": None, "line": None, "residual": None}
    pc = glyph_piece(ink, place, lines, sp)
    if pc is None:
        return dict(out, passed=False, why="g_no_ink")
    gw = g_witness(ink, pc["box"], lines, sp)
    curl = curl_round_line2(pc, lines, sp)
    hin = heads_in_glyph(ink, pc, heads, lines, sp)
    out.update(box=pc["box"], curl=curl, g_fill={"above": gw["above_fill"], "below": gw["below_fill"]}, heads_on_ink=hin)
    if any(v >= G_HEAD_INK_SHARE for v in hin):
        # round 5b: never a G clef over a notehead (Sean's r5 tile 1 "just a stem", tile 10 "2 half notes in a chord")
        return dict(out, passed=False, why="g_over_a_notehead")         # a second witness (r5b); the curl refuses Sean's tiles alone
    if not gw["passed"]:
        return dict(out, passed=False, why=gw["why"])
    if curl < G_CURL_MIN_REGIONS and not box_witness:
        return dict(out, passed=False, why="g_no_curl_round_line_2")
    # r7b: what the clef claims is its own ink on the staff, never a word the measuring close joined to it
    return dict(out, passed=True, why=None, kind="treble", line=G_LINES_READ[0], box=within_reach(own_ink_box(ink, pc, lines, sp), "G", lines, sp),
                witness="g_curl" if curl >= G_CURL_MIN_REGIONS else "detector_box")


def read_header_ink(ink: np.ndarray, place: Sequence[float], lines: Sequence[float], sp: float) -> Dict[str, Any]:
    """ROADMAP 2.324 r5 (Sean 2026-11-20: "every note on the page is dependent on the clefs being correct"): the clef at the start of a
    staff the detector drew NO box on, read from its own ink in its place -- the system's clef column (only a clef stands before the
    key). C by its thick bar and bowls (`c_bars`), G (`read_g`, no box witness), F (`read_mid_f`, dots beside the body's core); nothing
    where no shape reads -- the staff's clef is then carried from its other systems and counted. {passed, plain, family, kind, line, box}.

    Round 5b (Sean's r5 tiles 2, 3, 6: the claim ran down the system's barline): the place starts just right of the system's barline
    standing at its left edge (`barline_left_of`: a stroke running on past the staff further than a clef reaches -- ink at or left of it
    is never the clef's), and a read clef's area is kept inside what a clef can reach (`CLEF_REACH_SPACES`), never more."""
    bl = barline_left_of(ink, lines, sp, float(place[0]) - 0.5 * sp, float(place[0]) + 0.8 * sp)
    if bl is not None and bl + 1 < float(place[2]):
        place = [float(bl + 1), place[1], place[2], place[3]]
    cs = [c for c in c_bars(ink, lines, sp, place[0], place[2]) if c["passed"]]
    if cs:
        nm, ln, res = name_c_bar(cs[0], lines)
        return {"passed": True, "plain": nm is not None, "family": "C", "kind": nm, "line": ln, "residual": res,
                "box": c_area(cs[0], sp), "witness": "c_bar_and_bowls"}
    g = read_g(ink, place, lines, sp, box_witness=False)
    if g["passed"]:
        return dict(g, plain=True, box=within_reach(g["box"], "G", lines, sp))
    pc = glyph_piece(ink, place, lines, sp)
    if pc is None:
        return {"passed": False, "why": "no_ink_in_the_clef_place", "family": None}
    f = read_mid_f("clefF", pc["box"], ink, lines, sp, dots_beside_core=True)
    if f["passed"]:
        box = within_reach(pc["box"], "F", lines, sp)
        return dict(f, box=box, body=[f["body"][0], max(f["body"][1], box[1]), f["body"][2], min(f["body"][3], box[3])])
    return {"passed": False, "why": "no_clef_shape:" + str(g.get("why")) + "/" + str(f.get("why")), "family": None}


def header_reads(rows: Sequence[Any]) -> List[Any]:
    """ROADMAP 2.324: the HEADER clef reads of one staff (`Q.CLAIMED_AREA`, source `clef_pagewide`, `change: False`), left to right."""
    out = [r for r in rows if (getattr(r, "detail", None) or {}).get("source") == SOURCE
           and (r.detail or {}).get("change") is False and isinstance(r.value, (list, tuple)) and len(r.value) == 4]
    return sorted(out, key=lambda r: float(r.value[0]))


def is_weak_candidate(row: Any) -> bool:
    """A candidate with no shape witness: only the detector's small `clef*` box (`WEAK_CANDIDATE_WHY`), no body score, not strong."""
    d = getattr(row, "detail", None) or {}
    return d.get("why") == WEAK_CANDIDATE_WHY and d.get("body_score") is None and not d.get("strong")


def _ink(binary: Any) -> Optional[np.ndarray]:
    if binary is None or getattr(binary, "ndim", 0) != 2:
        return None
    return np.asarray(binary) == 0


def _longest_run(col: np.ndarray) -> Tuple[int, int]:
    """(length, start) of the longest run of True in a 1-D array."""
    if not col.any():
        return 0, 0
    d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    i = int(np.argmax(ends - starts))
    return int(ends[i] - starts[i]), int(starts[i])


#: ROADMAP 2.324 r3: a column whose unbroken ink runs this far past the staff on BOTH sides together (staff spaces, beyond its four)
#: is a barline or a bracket's line -- longer than any clef's bar may run (`C_BAR_REACH_SPACES` either side) -- never a clef's ink
BARLINE_PAST_STAFF_SPACES = 2 * C_BAR_REACH_SPACES


def barline_left_of(ink: np.ndarray, lines: Sequence[float], sp: float, xa: int, xb: int) -> Optional[int]:
    """The rightmost column in [xa, xb) holding an unbroken ink run longer than the staff plus `BARLINE_PAST_STAFF_SPACES` within the
    window three spaces either side of the staff (a barline or bracket line running on to the next staff), or None. Measures."""
    H, W = ink.shape
    top, bot = float(lines[0]), float(lines[-1])
    ya, yb = max(0, int(top - 3 * sp)), min(H, int(bot + 3 * sp) + 1)
    lim = (bot - top) + BARLINE_PAST_STAFF_SPACES * sp
    got = None
    for x in range(max(0, int(xa)), min(W, int(xb))):
        if _longest_run(ink[ya:yb, x])[0] > lim:
            got = x
    return got


def _without_lines(sub: np.ndarray, line_rows: Sequence[int], half: int, *, full_rows_only: bool = False) -> np.ndarray:
    """A copy of `sub` with the staff lines cleared (a line is no part of a glyph): every row within `half` px of each line, or with
    `full_rows_only` (the F clef's dots: the line is as thick as the print made it) only those rows whose ink runs across at least
    `LINE_ROW_MIN_FILL` of the window -- so a dot beside a line keeps its own rows."""
    out = sub.copy()
    if out.size == 0:
        return out
    for y in line_rows:
        for yy in range(max(0, y - half), min(out.shape[0], y + half + 1)):
            if not full_rows_only or out[yy].mean() >= LINE_ROW_MIN_FILL:
                out[yy, :] = False
    return out


def _runs_past(col: np.ndarray, top: float, bot: float, margin: float) -> bool:
    """Whether an unbroken run of ink in `col` that meets the rows [top, bot] starts above `top - margin` or ends below `bot + margin`."""
    if not col.any():
        return False
    d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
    for s, e in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        if e > top and s < bot and (s < top - margin or e > bot + margin):
            return True
    return False


#: r11: the staff lines are cut, outside the bar's own columns, this far either side of each line (staff spaces) before the ink past the
#: staff is traced back to the bar -- a line joins every mark it passes, so it never makes another mark's ink this clef's
G_OWN_LINE_HALF_SPACES = 0.15


def _own_past_ink(ink: np.ndarray, lines: Sequence[float], sp: float, ya: int, yb: int, xa: int, xb: int,
                  bar_x0: int, bar_x1: int) -> np.ndarray:
    """ROADMAP 2.324 r11 (Litolff p13 s0 staff 9: an alto clef refused as a treble clef's spine because the treble clef of the staff
    ABOVE hung its tail into the band above, and the system's thin barline line ran through the band below): A TREBLE CLEF'S CURL AND
    TAIL ARE ITS OWN STROKE, running on from its spine past the staff. The ink of rows ya..yb, columns xa..xb that is joined
    (8-neighbour) to the bar's columns `bar_x0..bar_x1` -- the staff lines cut outside those columns (`G_OWN_LINE_HALF_SPACES`), so a
    line passing joins nothing. NEVER another staff's clef or a barline standing apart from the bar. Measures; decides nothing."""
    from scipy import ndimage as ndi
    win = ink[ya:yb, xa:xb].copy()
    if win.size == 0:
        return win
    half = max(1, int(round(G_OWN_LINE_HALF_SPACES * sp)))
    keep = np.zeros(win.shape[1], dtype=bool)
    keep[max(0, bar_x0 - xa):max(0, bar_x1 - xa)] = True
    for L in lines:
        r = int(round(float(L))) - ya
        for yy in range(max(0, r - half), min(win.shape[0], r + half + 1)):
            win[yy, ~keep] = False
    lab, _ = ndi.label(win, structure=np.ones((3, 3), dtype=bool))
    ids = np.unique(lab[:, keep])
    ids = ids[ids > 0]
    return np.isin(lab, ids) if ids.size else np.zeros_like(win)


def c_bars(ink: np.ndarray, lines: Sequence[float], sp: float, x0: int, x1: int) -> List[Dict[str, Any]]:
    """Every C-clef thick bar on one staff between page columns x0..x1 (see the module doc), with its bowls measured. Measures;
    decides nothing beyond the shape test each candidate passed or failed (`passed`, `why`)."""
    H, W = ink.shape
    top, bot = float(lines[0]), float(lines[4])
    ya, yb = max(0, int(top - 3 * sp)), min(H, int(bot + 3 * sp) + 1)
    x0, x1 = max(0, int(x0)), min(W, int(x1))
    if x1 - x0 < 3 or yb - ya < 5:
        return []
    band = ink[ya:yb, x0:x1]
    ok = np.zeros(x1 - x0, dtype=bool)
    runs: List[Tuple[int, int]] = []
    for j in range(x1 - x0):
        n, s = _longest_run(band[:, j])
        runs.append((n, s))
        if n >= C_BAR_MIN_RUN_SPACES * sp:
            y_s, y_e = ya + s, ya + s + n
            if y_s >= top - C_BAR_REACH_SPACES * sp and y_e <= bot + C_BAR_REACH_SPACES * sp:
                ok[j] = True
    out: List[Dict[str, Any]] = []
    j = 0
    while j < len(ok):
        if not ok[j]:
            j += 1
            continue
        k = j
        while k < len(ok) and ok[k]:
            k += 1
        w = (k - j) / sp
        tops = [ya + runs[c][1] for c in range(j, k)]
        bots = [ya + runs[c][1] + runs[c][0] for c in range(j, k)]
        y_top, y_bot = float(np.median(tops)), float(np.median(bots))
        cand: Dict[str, Any] = {"x0": x0 + j, "x1": x0 + k, "y0": round(y_top, 1), "y1": round(y_bot, 1),
                                "bar_width_spaces": round(w, 3), "bar_run_spaces": round((y_bot - y_top) / sp, 3)}
        why = None
        thin_beside = None
        if w < C_BAR_MIN_WIDTH_SPACES:
            # 2.324 r2: the bar is thick COMPARED WITH THE THIN LINE BESIDE IT (the C clef's own thin bar, just right of it), not with a
            # figure from one plate -- Breitkopf's C clef bar is 0.43 sp, under Litolff's 0.45 cut, and still ~3x its thin companion
            m = k
            while m < len(ok) and not ok[m] and (m - k) <= C_THIN_GAP_SPACES * sp:
                m += 1
            if m < len(ok) and ok[m] and (m - k) <= C_THIN_GAP_SPACES * sp:
                e = m
                while e < len(ok) and ok[e]:
                    e += 1
                thin_beside = (e - m) / sp
                cand["thin_beside_spaces"] = round(thin_beside, 3)
                # r11: does the thin bar run the same height as this one (the C clef's bar pair)?
                t_top = float(np.median([ya + runs[c][1] for c in range(m, e)]))
                t_bot = float(np.median([ya + runs[c][1] + runs[c][0] for c in range(m, e)]))
                cand["thin_beside_edges_spaces"] = [round((t_top - y_top) / sp, 3), round((t_bot - y_bot) / sp, 3)]
        same_height = (thin_beside is not None and "thin_beside_edges_spaces" in cand
                       and max(abs(v) for v in cand["thin_beside_edges_spaces"]) <= C_PAIR_EDGE_SPACES)
        pair = (same_height and thin_beside >= C_THIN_MIN_SPACES and w >= C_PAIR_MIN_WIDTH_SPACES
                and w >= C_PAIR_THICK_RATIO * thin_beside)
        if pair and w < C_BAR_MIN_WIDTH_SPACES:
            cand["bar_pair"] = True
        if w < C_BAR_MIN_WIDTH_SPACES and not pair and not (thin_beside is not None and thin_beside >= C_THIN_MIN_SPACES
                                                            and w >= C_BAR_THICK_RATIO * thin_beside):
            why = "bar_too_thin"
        elif w > C_BAR_MAX_WIDTH_SPACES:
            why = "bar_too_wide"
        else:
            mid = (y_top + y_bot) / 2.0
            ll = local_lines(ink, lines, sp, x0 + j)
            cand["lines_local"] = [round(v, 1) for v in ll]
            bx0, bx1 = x0 + k, min(W, x0 + k + int(round(C_BOWL_REACH_SPACES * sp)))
            yt, ym, yb2 = int(round(y_top)), int(round(mid)), int(round(y_bot))
            half = max(1, int(round(BOWL_LINE_HALF_SPACES * sp)))
            region = _without_lines(ink[yt:yb2, bx0:bx1], [int(round(l)) - yt for l in ll], half)
            up, lo = region[: ym - yt], region[ym - yt:]
            fu = float(up.mean()) if up.size else 0.0
            fl = float(lo.mean()) if lo.size else 0.0
            asym = abs(fu - fl) / max(fu, fl, 1e-6)
            cand.update(bowl_fill_upper=round(fu, 3), bowl_fill_lower=round(fl, 3), bowl_asymmetry=round(asym, 3),
                        middle_y=round(mid, 1))
            # a G clef's spine passes the bar test too; its curl / tail stand past the staff, where a C clef has no ink
            gx0, gx1 = max(0, x0 + j - int(round(0.5 * sp))), min(W, x0 + k + int(round(0.8 * sp)))
            tx0, tx1 = max(0, x0 + j - int(round(1.0 * sp))), min(W, x0 + k + int(round(1.2 * sp)))
            # round 3 (Litolff p8 s0 staff 7: an alto clef refused as G-shaped): ink at or left of a BARLINE standing just left of the
            # bar is the barline's, never this clef's curl or tail -- a column there whose unbroken ink runs on past the staff further
            # than any clef reaches (`barline_left_of`) closes the window on that side
            bl = barline_left_of(ink, lines, sp, tx0, x0 + j)
            if bl is not None:
                gx0, tx0 = max(gx0, bl + 1), max(tx0, bl + 1)
                cand["barline_left_x"] = int(bl)
            ua, ub = max(0, int(top - G_PAST_SPACES[1] * sp)), max(0, int(top - G_PAST_SPACES[0] * sp))
            la, lb = min(H, int(bot + G_PAST_SPACES[0] * sp)), min(H, int(bot + G_PAST_SPACES[1] * sp))
            if gx1 > gx0 and lb > ua:
                own = _own_past_ink(ink, ll, sp, ua, lb, gx0, gx1, x0 + j, x0 + k)
                g_up, g_lo = own[ua - ua:ub - ua], own[la - ua:lb - ua]
            else:
                g_up, g_lo = ink[ua:ub, gx0:gx1], ink[la:lb, gx0:gx1]
            g_shape = bool(g_up.size and g_up.mean() >= G_PAST_MIN_FILL) and bool(g_lo.size and g_lo.mean() >= G_PAST_MIN_FILL)
            # round 2 (Sean's tile 5: a header G clef claimed as a C clef): the spine of a small G clef stays inside the staff and its
            # curl and tail miss the far bands above; its TAIL below the bottom line beside the spine does not
            tail = ink[min(H, int(ll[4] + G_TAIL_SPACES[0] * sp)):min(H, int(ll[4] + G_TAIL_SPACES[1] * sp)), tx0:tx1]
            cand["g_tail_fill"] = round(float(tail.mean()), 3) if tail.size else 0.0
            g_shape = g_shape or cand["g_tail_fill"] >= G_TAIL_MIN_FILL
            rows_ink = np.flatnonzero(region.any(axis=1))
            # the named line is the axis the WHOLE glyph (bar and bowls, lines cleared) balances about -- the header C-clef
            # locator's own measure (`clef_locator._refine_symmetry_axis`), searched within `C_AXIS_SHIFT_SPACES` of the bar's middle
            from ..clef_locator import _refine_symmetry_axis
            gx_0 = x0 + k     # the bowls only: the bar may run on into a stem or beam that touches it, the bowls do not
            glyph = _without_lines(ink[yt:yb2, gx_0:bx1], [int(round(l)) - yt for l in ll], half).astype(np.uint8)
            if glyph.size:
                axis, sym = _refine_symmetry_axis(glyph, (0, 0, glyph.shape[1], glyph.shape[0]), C_AXIS_SHIFT_SPACES * sp)
                cand["middle_y"] = round(float(yt + axis), 1)
                cand["symmetry"] = round(float(sym), 3)
            cand["g_shape"] = g_shape
            if g_shape:
                why = "g_clef_shape"
            elif min(fu, fl) < C_BOWL_MIN_FILL:
                why = "no_bowls"
            elif asym > C_BOWL_MAX_ASYMMETRY:
                why = "bowls_not_mirrored"
            elif rows_ink.size == 0:
                why = "no_bowls"
            else:
                # the glyph's right edge: walk right from the bar through the columns holding bowl ink, stopping at the first gap
                # wider than `C_GLYPH_GAP_SPACES` (round 2: a claim takes the clef's own ink, never a rest or note beside it)
                # r8 (Brahms p4 s1 staff 3: the claim ran on into the stem of the note touching the bowls): the clef's ink stays within
                # its bar's height -- a column whose ink, unbroken from the clef's rows, runs on past the bar's top or bottom
                # (`C_OWN_PAST_SPACES`) is another mark's stroke (a stem, a barline), and the clef's ink ends before it
                has = region.any(axis=0)
                past = np.zeros(region.shape[1], dtype=bool)
                for c in range(region.shape[1]):
                    if bx0 - x0 + c < band.shape[1]:
                        past[c] = _runs_past(band[:, bx0 - x0 + c], y_top - ya, y_bot - ya, C_OWN_PAST_SPACES * sp)
                gap, last, lim = 0, -1, int(round(C_GLYPH_GAP_SPACES * sp))
                for c in range(region.shape[1]):
                    if past[c] and last >= 0:
                        cand["stroke_right_x"] = int(bx0 + c)     # the other mark's first column: the claim stops short of it
                        break
                    if has[c]:
                        last, gap = c, 0
                    else:
                        gap += 1
                        if gap > lim:
                            break
                cand["x_right"] = int(bx0 + last + 1)
                # r10: the clef's outer edges (Sean: "Mesure from the outside to get the midddle"), on the lines at the clef
                top_e, bot_e = c_outside_edges(ink, cand, ll, sp)
                if top_e is not None:
                    cand.update(outside_top=int(top_e), outside_bottom=int(bot_e), outside_middle=round((top_e + bot_e) / 2.0, 1))
        cand["passed"] = why is None
        cand["why"] = why
        out.append(cand)
        j = k
    return out


def c_outside_edges(ink: np.ndarray, cand: Dict[str, Any], lines: Sequence[float], sp: float) -> Tuple[Optional[int], Optional[int]]:
    """ROADMAP 2.324 r10: the top and bottom rows (both inclusive, page px) of the C clef's own ink -- its outer edges (Sean: "Mesure
    from the outside to get the midddle"); (None, None) where no ink joins the bar. The clef's own piece: in the clef's columns (the
    thick bar's left edge to the glyph's right edge, stopped short of another mark's stroke, `C_STROKE_TRIM_SPACES`), every unbroken
    column run of ink within `C_OUTSIDE_REACH_SPACES` of the bar's top and bottom except a run that is only a staff line passing (as
    thick as the lines measured beside the clef, centred on one of `lines`), joined (8-neighbour) to the thick bar or the thin bar
    beside it. A rest or note left of the bar is outside the columns; a stem or barline touching the bowls ends the columns; a line
    the clef's own stroke runs into is part of that stroke. Measures; decides nothing."""
    from scipy import ndimage as ndi
    H, W = ink.shape
    x0, x1 = int(cand["x0"]), int(cand["x1"])
    xr = int(cand.get("x_right", cand["x1"] + 2.0 * sp))
    ya, yb = int(cand["y0"]), int(cand["y1"])
    for x in range(x0 + int(0.5 * sp), min(W, xr + int(round(C_STROKE_REACH_SPACES * sp)))):
        if _runs_past(ink[:, x], ya, yb, C_STROKE_PAST_SPACES * sp):
            xr = min(xr, x - int(np.ceil(C_STROKE_TRIM_SPACES * sp)))     # another mark's stroke: the clef ends before its edge
            break
    if xr - x0 < 2:
        return None, None
    ll = [float(v) for v in lines]
    th: List[int] = []
    for x in list(range(max(0, x0 - int(sp)), x0)) + list(range(min(W, xr + 2), min(W, xr + 2 + int(sp)))):
        for s, e in _ink_runs(ink[:, x]):
            if e - s <= 0.5 * sp and any(abs((s + e - 1) / 2.0 - L) <= 0.25 * sp for L in ll):
                th.append(e - s)
    thick = float(np.median(th)) if th else max(2.0, 0.25 * sp)
    Y0 = max(0, int(cand["y0"] - C_OUTSIDE_REACH_SPACES * sp))
    Y1 = min(H, int(cand["y1"] + C_OUTSIDE_REACH_SPACES * sp) + 1)
    if Y1 - Y0 < 2:
        return None, None
    own = np.zeros((Y1 - Y0, xr - x0), dtype=bool)
    for j, x in enumerate(range(x0, xr)):
        for s, e in _ink_runs(ink[Y0:Y1, x]):
            mid = (s + e - 1) / 2.0 + Y0
            if (e - s) <= thick + 1 and any(abs(mid - L) <= 0.5 * thick + 1 for L in ll):
                continue                                                    # only a staff line passing through
            own[s:e, j] = True
    lab, _n = ndi.label(own, structure=np.ones((3, 3), dtype=int))
    ids = set(np.unique(lab[:, : max(1, min(own.shape[1], x1 - x0 + int(round(C_THIN_GAP_SPACES * sp))))]).tolist()) - {0}
    if not ids:
        return None, None
    rows = np.flatnonzero(np.isin(lab, list(ids)).any(axis=1))
    return int(Y0 + rows[0]), int(Y0 + rows[-1])


def _ink_runs(col: np.ndarray) -> List[Tuple[int, int]]:
    """The unbroken ink runs of one column: [(start, end_exclusive)]."""
    d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def name_c_bar(cand: Dict[str, Any], lines: Sequence[float]) -> Tuple[Optional[str], Optional[int], Optional[float]]:
    """ROADMAP 2.324 r10 (Sean 2026-11-22: "As far as I know the c clefs are only alto and tenor ... we just need to figure out which
    it is closest to. To me this one looks like a tenor clef that was just printed a bit off"): A C CLEF ON AN INSTRUMENTAL STAFF IS
    ALTO OR TENOR -- WHICHEVER OF THE THIRD AND FOURTH LINES ITS MIDDLE (MEASURED FROM ITS TOP AND BOTTOM EDGES, `c_outside_edges`) IS
    NEARER. Never named where its middle sits between those two lines and is not clearly nearer one (more than the header readers'
    snap, 0.35 space, from both: a possible clef, UNREAD); never past `C_OUTER_REACH_SPACES` outside them; never from the instrument or
    another clef; never from where its ink balances (a candidate with no outside edges is UNREAD). (name, line, residual)."""
    ll = [float(v) for v in (cand.get("lines_local") or lines)]
    if cand.get("outside_middle") is None or len(ll) < 5:
        return None, None, None
    m = float(cand["outside_middle"])
    sp = (ll[4] - ll[0]) / 4.0
    if sp <= 0:
        return None, None, None
    tenor_y, alto_y = ll[1], ll[2]                      # the fourth and third lines (lines run top to bottom)
    dt, da = abs(m - tenor_y) / sp, abs(m - alto_y) / sp
    if tenor_y <= m <= alto_y:
        # between the two lines a C clef uses: the nearer only where it is clearly nearer (the header readers' own snap)
        from ..clef_geometry import DEFAULT_CONFIG
        if min(dt, da) > DEFAULT_CONFIG.max_residual:
            return None, None, round(min(dt, da), 3)
        return ("tenor", 4, round(dt, 3)) if dt <= da else ("alto", 3, round(da, 3))
    if m < tenor_y:                                     # above the tenor line: no second C line on that side
        return ("tenor", 4, round(dt, 3)) if dt < C_OUTER_REACH_SPACES else (None, None, round(dt, 3))
    return ("alto", 3, round(da, 3)) if da < C_OUTER_REACH_SPACES else (None, None, round(da, 3))


def c_area(cand: Dict[str, Any], sp: float) -> List[float]:
    """The page-px area a passing C bar candidate claims: from just left of its thick bar to the glyph's own right edge (`x_right`,
    the contiguous bowl ink), and the clef's height about its named line. ONE formula for the claim and for any tile drawn of it."""
    mid = float(cand.get("middle_y", (cand["y0"] + cand["y1"]) / 2.0))
    right = float(cand.get("x_right", cand["x1"] + 2.0 * sp)) + 0.1 * sp
    if cand.get("stroke_right_x") is not None:
        right = min(right, float(cand["stroke_right_x"]))   # r8: never into the stroke the bowls touch (a stem)
    return [float(cand["x0"]) - 0.15 * sp, min(float(cand["y0"]), mid - 2.0 * sp) - 0.3 * sp,
            right, max(float(cand["y1"]), mid + 2.0 * sp) + 0.3 * sp]


def local_lines(ink: np.ndarray, lines: Sequence[float], sp: float, x: float) -> List[float]:
    """The five staff lines measured AT x (CLAUDE §5: never a staff-wide value; a scanned staff tilts and ~1 px decides a line): the
    one vertical shift, within `LOCAL_LINE_REACH_SPACES`, that puts the most ink under all five nominal lines together over the
    `LOCAL_LINE_WINDOW_SPACES` of columns either side of x (one shift for five lines: a note or a stem beside one line cannot pull it)."""
    H, W = ink.shape
    xa, xb = max(0, int(x - LOCAL_LINE_WINDOW_SPACES * sp)), min(W, int(x + LOCAL_LINE_WINDOW_SPACES * sp))
    reach = int(round(LOCAL_LINE_REACH_SPACES * sp))
    if xb - xa < 3:
        return [float(v) for v in lines]
    best, best_d = -1.0, 0
    for dy in range(-reach, reach + 1):
        tot = 0.0
        for y in lines:
            yy = int(round(y)) + dy
            if 0 <= yy < H:
                tot += float(ink[yy, xa:xb].mean())
        if tot > best + 1e-9 or (abs(tot - best) <= 1e-9 and abs(dy) < abs(best_d)):
            best, best_d = tot, dy
    return [float(v) + best_d for v in lines]


def name_c(mid_y: float, lines: Sequence[float]) -> Tuple[Optional[str], Optional[int], Optional[float]]:
    """The C clef's name from its middle (the header readers' own snap, `clef_geometry.resolve_clef`): (name, line, residual) or
    (None, None, residual) where it lands on no line a C clef uses."""
    from ..clef_geometry import resolve_clef
    r = resolve_clef("cClef", anchor_y=float(mid_y), staff_line_ys=[float(v) for v in lines])
    if r is None or r.line is None or r.line not in KINDS_READ["C"]:
        return None, None, (round(float(r.residual), 3) if r is not None and r.residual is not None else None)
    return r.name, r.line, (round(float(r.residual), 3) if r.residual is not None else None)


def _dot_mask(ink: np.ndarray, y0: int, y1: int, x0: int, x1: int, lines: Sequence[float], sp: float) -> np.ndarray:
    """The window's ink as the dot readers see it: the staff lines cleared (rows a line runs across, as thick as the print made it),
    and every column holding an unbroken RAW ink run of `DOT_STROKE_CLEAR_SPACES` or more cleared too -- a stem or barline that the
    dots touch (Brahms p5 s1 staff 3: thick lines and a stem fuse the lower dot) is no part of a dot, and an F clef's own body never
    runs that far down one column."""
    half = max(1, int(round(LINE_HALF_SPACES * sp)))
    sub = _without_lines(ink[y0:y1, x0:x1], [int(round(l)) - y0 for l in lines], half, full_rows_only=True)
    for j in range(sub.shape[1]):
        if _longest_run(ink[y0:y1, x0 + j])[0] >= DOT_STROKE_CLEAR_SPACES * sp:
            sub[:, j] = False
    return sub.astype(np.uint8)


def f_dots(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float) -> bool:
    """The F clef's two dots right of its body (`clef_locator._has_f_clef_dots`, the header locator's own veto) on the page ink with
    the staff lines cleared."""
    from ..clef_locator import DEFAULT_LOCATOR_CONFIG, _has_f_clef_dots
    H, W = ink.shape
    x0, y0 = max(0, int(box[0] - sp)), max(0, int(box[1] - sp))
    x1, y1 = min(W, int(box[2] + 2 * sp)), min(H, int(box[3] + sp))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return False
    sub = _dot_mask(ink, y0, y1, x0, x1, lines, sp)
    bb = (int(box[0]) - x0, int(box[1]) - y0, int(box[2] - box[0]), int(box[3] - box[1]))
    try:
        return bool(_has_f_clef_dots(sub, bb, float(sp), DEFAULT_LOCATOR_CONFIG))
    except Exception:                                   # noqa: BLE001 -- a reader that cannot run is no witness
        return False


#: the right edge (page px) of the dot pair the last `f_line` call read -- the F claim's own right edge
F_LAST_DOTS: Dict[str, float] = {}


def f_line(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float) -> Tuple[Optional[str], Optional[int], Optional[float]]:
    """The F clef's name from its DOTS: they straddle the line the clef names (`clef_locator._has_f_clef_dots`' own reason), so the
    midpoint of the dot pair right of the body's middle (sizes and spacing from the header locator's config) snaps to that line
    (`clef_geometry._snap_to_staff_line`). (None, None, residual) where no pair or no F line fits."""
    import cv2
    from ..clef_geometry import CLEF_BY_FAMILY_LINE, DEFAULT_CONFIG, _snap_to_staff_line
    from ..clef_locator import DEFAULT_LOCATOR_CONFIG as C
    H, W = ink.shape
    x0, y0 = max(0, int((box[0] + box[2]) / 2.0)), max(0, int(box[1] - sp))
    x1, y1 = min(W, int(box[2] + C.dot_search_right_spaces * sp)), min(H, int(box[3] + sp))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None, None, None
    sub = _dot_mask(ink, y0, y1, x0, x1, lines, sp)
    n, _lab, st, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
    dots = []
    for i in range(1, n):
        bw, bh = st[i, cv2.CC_STAT_WIDTH] / sp, st[i, cv2.CC_STAT_HEIGHT] / sp
        if C.dot_min_size_spaces <= bw <= C.dot_max_size_spaces and C.dot_min_size_spaces <= bh <= C.dot_clear_max_height_spaces:
            cx = x0 + st[i, cv2.CC_STAT_LEFT] + bw * sp / 2.0
            # a piece of a stem or barline the line clearing cut is no dot: its column runs on through the lines in the raw ink
            if _longest_run(ink[y0:y1, int(cx)])[0] >= DOT_NOT_A_STROKE_SPACES * sp:
                continue
            dots.append((cx, y0 + st[i, cv2.CC_STAT_TOP] + bh * sp / 2.0, x0 + st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH]))
    best = None
    for a in range(len(dots)):
        for b in range(a + 1, len(dots)):
            dx, dy = abs(dots[a][0] - dots[b][0]) / sp, abs(dots[a][1] - dots[b][1]) / sp
            if dx <= C.dot_max_dx_spaces and C.dot_min_dy_spaces <= dy <= C.dot_max_dy_spaces:
                # the dots stand at the body's right edge: the pair nearest the box's right edge (a key flat's or a note's pieces stand
                # further right; round 2: on Brahms headers the rightmost pair was a key flat's bowl)
                cand = (round(abs((dots[a][0] + dots[b][0]) / 2.0 - float(box[2])) / sp, 1), abs(dy - 1.0),
                        (dots[a][1] + dots[b][1]) / 2.0,
                        max(dots[a][2], dots[b][2]))
                if best is None or cand < best:
                    best = cand
    if best is None:
        return None, None, None
    F_LAST_DOTS["right"] = float(best[3])
    snapped = _snap_to_staff_line(best[2], [float(v) for v in lines])
    if snapped is None:
        return None, None, None
    line, residual = snapped
    name = CLEF_BY_FAMILY_LINE["F"].get(line) if line in KINDS_READ["F"] else None
    if name is None or residual > DEFAULT_CONFIG.max_residual:
        return None, None, round(float(residual), 3)
    return name, line, round(float(residual), 3)


#: ROADMAP 2.324 r5: the staff lines are found as the rows the line's ink runs along over a WIDE strip -- this far left of the place
#: and this far right of it (staff spaces) -- so a glyph that fills its own box's rows (an F clef's ball on its line) is never taken
#: for a line, however narrow the place looked at
LINE_STRIP_SPACES = (3.0, 8.0)


def line_rows(ink: np.ndarray, lines: Sequence[float], sp: float, x0: float, x1: float) -> List[int]:
    """ROADMAP 2.324 r5: the page rows that ARE staff line near [x0, x1]: within `LINE_HALF_SPACES` of a line, ink across at least
    `LINE_ROW_MIN_FILL` of the wide strip `LINE_STRIP_SPACES` around the place. Measures."""
    H, W = ink.shape
    xa, xb = max(0, int(x0 - LINE_STRIP_SPACES[0] * sp)), min(W, int(x1 + LINE_STRIP_SPACES[1] * sp))
    half = max(1, int(round(LINE_HALF_SPACES * sp)))
    out = []
    for v in lines:
        for y in range(int(round(v)) - half, int(round(v)) + half + 1):
            if 0 <= y < H and xb > xa and float(ink[y, xa:xb].mean()) >= LINE_ROW_MIN_FILL:
                out.append(y)
    return out


def _mask_wide_lines(ink: np.ndarray, y0: int, y1: int, x0: int, x1: int, lines: Sequence[float], sp: float, *,
                     strokes: bool = True) -> np.ndarray:
    """The window's ink with the staff-line rows (`line_rows`, judged on a wide strip) cleared, and (`strokes`) the long upright
    strokes too -- a stem or barline beside an F clef's body; never for a G clef, whose spine is one."""
    sub = ink[y0:y1, x0:x1].copy()
    for y in line_rows(ink, lines, sp, x0, x1):
        if y0 <= y < y1:
            sub[y - y0, :] = False
    for j in range(sub.shape[1] if strokes else 0):
        if _longest_run(ink[y0:y1, x0 + j])[0] >= DOT_STROKE_CLEAR_SPACES * sp:
            sub[:, j] = False
    return sub.astype(np.uint8)


def f_body(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float, *, wide: bool = False,
           core: bool = False) -> Optional[List[float]]:
    """The F clef's BODY inside its detector box (page px [x0, y0, x1, y1]): the largest piece of the box's ink with the staff lines
    and the long strokes cleared (`_dot_mask`). Round 2 (Sean's r1 tile 10, Litolff p16): the detector's `clefF` box also held the
    quarter rest standing just left of the clef, so the claim is cut to the clef's own ink, never the box. `wide` (ROADMAP 2.324 r5,
    `read_mid_f` only): the lines are judged on a wide strip (`_mask_wide_lines`), so a narrow place keeps the ball's rows."""
    import cv2
    H, W = ink.shape
    x0, y0, x1, y1 = max(0, int(box[0])), max(0, int(box[1])), min(W, int(round(box[2]))), min(H, int(round(box[3])))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    sub = _mask_wide_lines(ink, y0, y1, x0, x1, lines, sp) if wide else _dot_mask(ink, y0, y1, x0, x1, lines, sp)
    n, _lab, st, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
    if n <= 1:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    # the line clearing cuts the body into pieces: the body is the largest piece and every sizeable piece starting no further left
    # than `F_BODY_LEFT_REACH_SPACES` before it (a rest or note standing left of the clef starts further left)
    lo = st[i, cv2.CC_STAT_LEFT] - F_BODY_LEFT_REACH_SPACES * sp
    keep = [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 0.15 * st[i, cv2.CC_STAT_AREA] and st[j, cv2.CC_STAT_LEFT] >= lo]
    if core:
        # round 5 (a place found by ink, no box): the body's CORE is the largest piece and what stands under or left of it -- never the
        # dots or key accidentals to its right (Litolff prints them touching)
        rx = st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH]
        keep = [j for j in keep if st[j, cv2.CC_STAT_LEFT] < rx]
    return [float(x0 + min(st[j, cv2.CC_STAT_LEFT] for j in keep)), float(y0 + min(st[j, cv2.CC_STAT_TOP] for j in keep)),
            float(x0 + max(st[j, cv2.CC_STAT_LEFT] + st[j, cv2.CC_STAT_WIDTH] for j in keep)),
            float(y0 + max(st[j, cv2.CC_STAT_TOP] + st[j, cv2.CC_STAT_HEIGHT] for j in keep))]


def f_claim_area(got: Dict[str, Any], box: Sequence[float], sp: float) -> List[float]:
    """The page-px area a passing F clef claims: its body's left edge (else the box's) to its dots' right edge, the box's height.
    ONE formula for the claim and for any tile drawn of it."""
    body = got.get("body")
    left = float(body[0]) - 0.1 * sp if body else float(box[0])
    right = max(float(body[2]) if body else float(box[2]), float(got.get("dots_right") or 0.0)) + 0.05 * sp
    return [max(float(box[0]), left), float(box[1]), right, float(box[3])]


def read_box(name: str, box: Sequence[float], ink: np.ndarray, lines: Sequence[float], sp: float, *,
             header: bool = False) -> Dict[str, Any]:
    """The second witness for a clef-sized detector `clef*` box: {passed, why, kind, family, line, residual}. `header` (ROADMAP 2.324
    r2, the page-wide clef reader, always now): a box in its system's header window, where an F clef whose dot PAIR is not found is read
    by the ink at its two dot places (`f_dot_places`)."""
    from ..clef_geometry import clef_family, resolve_clef
    fam = clef_family(name)
    top, bot = float(lines[0]), float(lines[4])
    out: Dict[str, Any] = {"family": fam, "cls": str(name), "kind": None, "line": None, "residual": None}
    if fam == "F":
        if abs(float(box[1]) - top) > F_TOP_REACH_SPACES * sp:
            return dict(out, passed=False, why="f_top_off_the_top_line")
        if header and g_witness(ink, box, lines, sp)["passed"]:
            # 2.324 r3: an F clef stays on the staff; ink running past it both above AND below in the box's columns is a G clef's loop
            # and tail -- never an F clef, whatever ink stands at the dot places (on the frozen sample a G clef's ink fills them 0.84)
            return dict(out, passed=False, why="f_box_ink_past_the_staff_like_a_g")
        if header and any(b["why"] not in ("bar_too_thin", "bar_too_wide", "g_clef_shape")
                          for b in c_bars(ink, lines, sp, float(box[0]) - F_NEVER_C_REACH_SPACES * sp, float(box[2]))):
            # 2.324 r3: an F clef has no thick bar; where a C clef's bar (thick beside its thin line, the staff's height) stands in the
            # box, the ink is a C clef whatever fills the dot places (a C clef's bowls fill them 0.88-1.0 on the frozen sample)
            return dict(out, passed=False, why="f_box_on_a_c_bar")
        # round 2: the witness is the DOT PAIR that straddles the F line (`f_line`, the header locator's dot sizes and spacing), read on
        # the window with lines AND the strokes the dots touch cleared; the locator's own whole-glyph test (`_has_f_clef_dots`) is
        # kept as the first chance but no longer required -- on Breitkopf's thick lines it fails real clefs (Sean r1 tile 11)
        dots_ok = f_dots(ink, box, lines, sp)
        F_LAST_DOTS.clear()
        nm, ln, res = f_line(ink, box, lines, sp)
        out["dots_right"] = F_LAST_DOTS.get("right")
        out["body"] = f_body(ink, box, lines, sp)
        out["locator_dots"] = bool(dots_ok)
        if nm is None and header:
            # 2.324 r2: Litolff merges -- the dots touch the key flats, so no separate pair is seen; a musician sees dot ink at the two
            # places either side of line 4 just right of the body, whatever it touches
            fp = f_dot_places(ink, box, lines, sp)
            out["dot_places"] = {"upper": fp["upper"], "lower": fp["lower"], "x": fp["x"]}
            if fp["passed"]:
                if fp["x"] is not None:
                    out["dots_right"] = float(fp["x"]) + 0.3 * sp
                return dict(out, passed=True, why=None, kind="bass", line=4, residual=None, witness="f_dot_places")
        if nm is None and not dots_ok and "right" not in F_LAST_DOTS:
            return dict(out, passed=False, why="f_no_dots")
        if nm is None:
            # the dot PAIR must straddle the F line: dots that name no allowed line are no second witness (a false `clefF` box over
            # a half note and a barline passed the looser dot test on Brahms p25) -- the box alone never claims
            return dict(out, passed=False, why="f_dots_name_no_line", residual=res)
        return dict(out, passed=True, why=None, kind=nm, line=ln, residual=res)
    elif fam == "G":
        # no second witness for a G clef inside a system is built (none is printed on the two plates; 2.144's false `clefG` boxes over
        # real eighths are the risk): the box alone never claims (the register's NARROWED claim stands)
        if not (float(box[1]) <= top - G_REACH_SPACES * sp and float(box[3]) >= bot + G_REACH_SPACES * sp):
            return dict(out, passed=False, why="g_not_past_the_staff")
        return dict(out, passed=False, why="g_no_second_witness")
    elif fam == "C":
        bars = [b for b in c_bars(ink, lines, sp, box[0] - 0.5 * sp, box[2]) if b["passed"]]
        if not bars:
            return dict(out, passed=False, why="c_no_bar_and_bowls")
        nm, ln, res = name_c_bar(dict(bars[0], lines_local=None), lines)
        return dict(out, passed=True, why=None, kind=nm, line=ln, residual=res)
    else:
        return dict(out, passed=False, why="not_a_pitched_clef")
    r = resolve_clef(name, y_top=float(box[1]), height=float(box[3] - box[1]), staff_line_ys=[float(v) for v in lines])
    if r is None or r.line is None:
        return dict(out, passed=True, why=None, residual=(round(float(r.residual), 3) if r is not None and r.residual is not None else None))
    return dict(out, passed=True, why=None, kind=r.name, line=r.line, residual=(round(float(r.residual), 3) if r.residual is not None else None))


# --------------------------------------------------------------------------------------------------------------------------------------
# 2.251 carry: an F clef with NO detector box (Litolff bars 38 / 111 / 115, Brahms bass clefs whose box failed its dots)
# --------------------------------------------------------------------------------------------------------------------------------------
#: the dot-pair scan runs in windows this wide (staff spaces), overlapping by `F_SCAN_OVERLAP_SPACES`, each with its own local lines
F_SCAN_WINDOW_SPACES = 8.0
F_SCAN_OVERLAP_SPACES = 3.0


#: a no-box dot may be this wide (staff spaces; the header locator allows 0.75): the body's tip touches the upper dot (Litolff bar 38,
#: 0.76 sp fused) -- the body template is the second witness that keeps a looser dot honest
NOBOX_DOT_MAX_WIDTH_SPACES = 0.9
#: a horizontal ink run this long (staff spaces) is a staff line or a beam, never part of a dot
DOT_LINE_RUN_SPACES = 1.2


def _dot_mask_runs(ink: np.ndarray, y0: int, y1: int, x0: int, x1: int, sp: float) -> np.ndarray:
    """The window's ink as the no-box dot reader sees it: every HORIZONTAL run of `DOT_LINE_RUN_SPACES` or more cleared (a staff line,
    however it tilts, or a beam) and every column holding an unbroken vertical run of `DOT_STROKE_CLEAR_SPACES` or more cleared (a
    stem, a barline). Unlike `_dot_mask` it does not depend on where the window starts (the row-share line test did: Litolff bar 38's
    dots were seen from 5 of 22 window starts)."""
    import cv2
    sub = ink[y0:y1, x0:x1].astype(np.uint8)
    if sub.size == 0:
        return sub
    k = max(3, int(round(DOT_LINE_RUN_SPACES * sp)))
    lines_only = cv2.morphologyEx(sub, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1)))
    out = sub & (1 - lines_only)
    kv = max(3, int(round(DOT_STROKE_CLEAR_SPACES * sp)))
    strokes = cv2.morphologyEx(ink[y0:y1, x0:x1].astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, kv)))
    cols = strokes.any(axis=0)
    out[:, cols] = 0
    return out


def f_dot_pairs(ink: np.ndarray, lines: Sequence[float], sp: float, x0: float, x1: float) -> List[Dict[str, Any]]:
    """Every dot PAIR on one staff between page columns x0..x1 that straddles the F line (line 4 from the bottom: the second line from
    the top) -- the F clef's dots by the header locator's own sizes and spacing (`clef_locator.DEFAULT_LOCATOR_CONFIG`), read on the ink
    with the staff lines and long strokes cleared (`_dot_mask`), the lines measured locally per window. Measures; decides nothing.
    Each: {x_left, x_right, y_mid, residual, dots}."""
    import cv2
    from ..clef_geometry import DEFAULT_CONFIG, _snap_to_staff_line
    from ..clef_locator import DEFAULT_LOCATOR_CONFIG as C
    H, W = ink.shape
    out: List[Dict[str, Any]] = []
    step = max(1, int(round((F_SCAN_WINDOW_SPACES - F_SCAN_OVERLAP_SPACES) * sp)))
    xa = max(0, int(x0))                                   # never a negative column (it would read the far right of the page)
    while xa < int(x1):
        xb = min(W, int(xa + F_SCAN_WINDOW_SPACES * sp))
        ll = local_lines(ink, lines, sp, (xa + xb) / 2.0)
        y0, y1 = max(0, int(ll[1] - 1.4 * sp)), min(H, int(ll[1] + 1.4 * sp))
        sub = _dot_mask_runs(ink, y0, y1, xa, xb, sp)
        n, _lab, st, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
        dots = []
        for i in range(1, n):
            bw, bh = st[i, cv2.CC_STAT_WIDTH] / sp, st[i, cv2.CC_STAT_HEIGHT] / sp
            if not (C.dot_min_size_spaces <= bw <= NOBOX_DOT_MAX_WIDTH_SPACES and C.dot_min_size_spaces <= bh <= C.dot_clear_max_height_spaces):
                continue
            cx = xa + st[i, cv2.CC_STAT_LEFT] + bw * sp / 2.0
            if _longest_run(ink[y0:y1, int(cx)])[0] >= DOT_NOT_A_STROKE_SPACES * sp:
                continue
            dots.append((cx, y0 + st[i, cv2.CC_STAT_TOP] + bh * sp / 2.0, xa + st[i, cv2.CC_STAT_LEFT],
                         xa + st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH]))
        for a in range(len(dots)):
            for b in range(a + 1, len(dots)):
                up, lo = (dots[a], dots[b]) if dots[a][1] < dots[b][1] else (dots[b], dots[a])
                dx, dy = abs(up[0] - lo[0]) / sp, (lo[1] - up[1]) / sp
                if not (dx <= C.dot_max_dx_spaces and C.dot_min_dy_spaces <= dy <= C.dot_max_dy_spaces):
                    continue
                if not (up[1] < ll[1] < lo[1]):
                    continue                                   # the pair straddles the line, one dot either side
                mid = (up[1] + lo[1]) / 2.0
                snapped = _snap_to_staff_line(mid, ll)
                if snapped is None or snapped[0] != 4 or snapped[1] > DEFAULT_CONFIG.max_residual:
                    continue
                xl, xr = min(up[2], lo[2]), max(up[3], lo[3])
                if any(abs(p["x_left"] - xl) < 0.3 * sp and abs(p["y_mid"] - mid) < 0.3 * sp for p in out):
                    continue                                   # the same pair seen from two overlapping windows
                out.append({"x_left": float(xl), "x_right": float(xr), "y_mid": float(mid), "residual": float(snapped[1]),
                            "dots": [[round(float(v), 1) for v in up], [round(float(v), 1) for v in lo]], "lines_local": ll})
        if xb >= int(x1):
            break
        xa += step
    out.sort(key=lambda p: p["x_left"])
    return out


def f_template(ink: np.ndarray, lines: Sequence[float], sp: float, body: Sequence[float], dots_left: float) -> Optional[Dict[str, Any]]:
    """The F body of a READ F clef (`f_body`, page px) as a template: its ink with the staff lines cleared, cut to the body, and where it
    stands against its own dots (the body's right edge to the dots' left edge) and its own F line, in staff spaces."""
    ll = local_lines(ink, lines, sp, body[0])
    x0, y0, x1, y1 = int(body[0]), int(body[1]), int(round(body[2])), int(round(body[3]))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    half = max(1, int(round(BOWL_LINE_HALF_SPACES * sp)))
    m = _without_lines(ink[y0:y1, x0:x1], [int(round(l)) - y0 for l in ll], half)
    return {"mask": m, "sp": float(sp), "dx_to_dots": (float(dots_left) - float(body[2])) / sp, "dy_line": (float(body[1]) - ll[1]) / sp}


#: the template is tried at these sizes (a change is often printed smaller than the header's clef) ...
F_TEMPLATE_SCALES = (0.8, 0.9, 1.0)
#: ... and shifted this far (staff spaces) each way from where its own dots put it
F_TEMPLATE_SHIFT_SPACES = 0.35


def f_body_match(ink: np.ndarray, sp: float, pair: Dict[str, Any], templates: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The second witness for a dot pair with no box: the plate's OWN F body (a read F clef of the same page, `f_template`) laid left of
    the pair where its own dots put it, at the best size and shift. `cover`: the share of the template's ink the page has there; `extra`:
    the share of the page's ink in the template's box that the template does not explain (a stem or head through it). Measures."""
    import cv2
    ll = pair["lines_local"]
    half = max(1, int(round(BOWL_LINE_HALF_SPACES * sp)))
    best = {"cover": 0.0, "extra": 1.0, "score": 0.0}
    H, W = ink.shape
    shift = int(round(F_TEMPLATE_SHIFT_SPACES * sp))
    for t in templates:
        for s in F_TEMPLATE_SCALES:
            k = s * sp / t["sp"]
            th, tw = max(3, int(round(t["mask"].shape[0] * k))), max(3, int(round(t["mask"].shape[1] * k)))
            tm = cv2.resize(t["mask"].astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST).astype(bool)
            if tm.sum() == 0:
                continue
            bx1 = pair["x_left"] - t["dx_to_dots"] * s * sp
            by0 = ll[1] + t["dy_line"] * s * sp
            for dy in range(-shift, shift + 1, max(1, shift // 3)):
                for dx in range(-shift, shift + 1, max(1, shift // 3)):
                    x0, y0 = int(round(bx1 - tw + dx)), int(round(by0 + dy))
                    if x0 < 0 or y0 < 0 or x0 + tw > W or y0 + th > H:
                        continue
                    im = _without_lines(ink[y0:y0 + th, x0:x0 + tw], [int(round(l)) - y0 for l in ll], half)
                    inter = float((tm & im).sum())
                    cover = inter / float(tm.sum())
                    extra = float((im & ~tm).sum()) / max(1.0, float(im.sum()))
                    score = cover - extra
                    if score > best["score"]:
                        best = {"cover": round(cover, 3), "extra": round(extra, 3), "score": round(score, 3), "scale": s,
                                "box": [x0, y0, x0 + tw, y0 + th]}
    return best


def f_body_scan(ink: np.ndarray, lines: Sequence[float], sp: float, x0: float, x1: float,
                templates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The page's own F body slid along one staff between page columns x0..x1 with NO dot witness (ROADMAP 2.251 carry round 2,
    Litolff bar 111: the dots are fused with the heads beside them, so no pair is seen). At each step (twice the template's own shift,
    so the shifts tile the staff) the best `f_body_match`; local maxima only. ONE witness: it may make a clef-shaped CANDIDATE that stops
    a carry (the heads after it go unread, never wrong), never a READ clef. Each: {x (the body's left edge, page px), match}."""
    if not templates:
        return []
    step = max(2, int(round(2 * F_TEMPLATE_SHIFT_SPACES * sp)))
    raw = []
    x = float(x0)
    while x < float(x1):
        ll = local_lines(ink, lines, sp, x)
        m = f_body_match(ink, sp, {"x_left": x, "lines_local": ll}, templates)
        if "box" in m:
            raw.append({"x": float(m["box"][0]), "match": m})
        x += step
    out = []
    for i, r in enumerate(raw):
        lo = raw[i - 1]["match"]["score"] if i > 0 else -1.0
        hi = raw[i + 1]["match"]["score"] if i + 1 < len(raw) else -1.0
        if r["match"]["score"] >= lo and r["match"]["score"] >= hi:
            out.append(r)
    return out


def f_body_shape(ink: np.ndarray, lines: Sequence[float], sp: float, pair: Dict[str, Any],
                 templates: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """Exploration wrapper: `f_body_match` against `templates`."""
    return f_body_match(ink, sp, pair, templates)


#: the no-box F clef is READ (kind bass, claimed) at this body score (cover - extra) and above. MEASURED on Litolff pp. 1-16 (1472 dot
#: pairs; every non-clef pair <= 0.61, the 2.251 count's no-box bass clefs 0.83 (bar 38), 0.75 (Vc bar 411)); Brahms pp. 1,3,4,5 every
#: non-clef pair <= 0.42. A CUT-OFF on two plates (CLAUDE §4: a measurement, not a convention) -- Sean's tiles judge it.
#: 2026-11-02 (Sean "Do it"): lowered 0.70 -> 0.65. Litolff non-clef dots+body max 0.61, real-clef min 0.68; the only new reads are Vc bar
#: 346 (0.69, Sean confirmed) and bar 115 (0.68); Brahms nothing reaches 0.50. Body-only (`f_body_scan`) stays a candidate.
F_TEMPLATE_READ_SCORE = 0.65
#: ... and at this score and above (but below READ) it is a CLEF-SHAPED CANDIDATE: claimed nothing, but a carried clef stops there
#: (Litolff bars 115 0.66 and 111 0.55: real bass clefs with a head / stem through the body)
F_TEMPLATE_CANDIDATE_SCORE = 0.50
#: ... and at this score (dot pair AND body, below READ) a STRONG candidate: it stops the header's clef too, unless that is an F clef.
#: Round 2: Sean's carry tile 11 (Vc bar 346, 0.69) is a real F clef; every non-clef dot pair on Litolff pp. 1-16 scored <= 0.61.
#: Since READ was lowered to 0.65 (2026-11-02) this tier is EMPTY at these cut-offs (STRONG == READ, so a pair at >= STRONG is already
#: READ and `strong` is never set); kept so a later change to READ revives it without a rewrite
F_TEMPLATE_STRONG_SCORE = 0.65
#: the F body slid with NO dot witness (`f_body_scan`) makes a candidate at this score (one witness: a candidate, never READ).
#: MEASURED on Litolff pp. 1-16, the staves holding a claimed change, right of it: every place with no clef <= 0.55; the real F clefs
#: 0.68 (bar 115) - 1.0, bar 111 (dots fused with the heads beside them) 0.73
F_BODY_SCAN_CANDIDATE_SCORE = 0.60
#: a `clef*` box too small for a clef-sized claim, at this detector score and above, is still a clef-shaped CANDIDATE (b)
SMALL_CLEF_BOX_MIN_SCORE = 0.5
#: an F clef's body and dots span at most this far (staff spaces) left of its dots' left edge
F_BODY_MAX_REACH_SPACES = 2.6
#: a dot's width (staff spaces): the template's dots start this far left of the dot pair's right edge `f_line` reports
F_DOT_WIDTH_SPACES = 0.45


def f_templates(ink: np.ndarray, staves: Sequence[Tuple[Sequence[float], float, Sequence[Sequence[float]]]]) -> List[Dict[str, Any]]:
    """The page's own F bodies: every clef-sized `clefF` box (per staff: lines, staff space, the boxes) whose dots read an F line
    (`read_box` passes), its body cut at its dots -- the template the no-box reader lays over a dot pair."""
    out: List[Dict[str, Any]] = []
    for lines, sp, boxes in staves:
        for pb in boxes:
            ll = local_lines(ink, lines, sp, pb[0])
            got = read_box("clefF", pb, ink, ll, sp)
            if not got.get("passed") or not got.get("body") or not got.get("dots_right"):
                continue
            dl = float(got["dots_right"]) - F_DOT_WIDTH_SPACES * sp
            body = list(got["body"])
            body[2] = min(float(body[2]), dl - 1.0)
            if body[2] - body[0] < sp:
                continue
            t = f_template(ink, lines, sp, body, dl)
            if t is not None:
                out.append(t)
    return out


def nobox_area(body_box: Sequence[float], pair: Dict[str, Any], left: float, sp: float) -> List[float]:
    """The page-px area a no-box F clef claims: the matched BODY's own box (from `left`) and its dot pair -- nothing more. A READ claim
    takes ink, so it may never take a real head's (round 3, the coordinator on Sean's carry r2 tile 2). Round 2 padded it a space left
    and to the clef's full height to take bar 38's 0.42 head box on the clef's blob; the same pad would take an eighth printed just before
    a clef (Litolff bar 111). Removed: bar 38's head box is again a head, and the witness counts it as one."""
    return [float(left) - 0.05 * sp, float(min(body_box[1], pair["dots"][0][1] - 0.4 * sp)), float(pair["x_right"]) + 0.05 * sp,
            float(max(body_box[3], pair["dots"][1][1] + 0.4 * sp))]


def f_nobox(ink: np.ndarray, lines: Sequence[float], sp: float, x0: float, x1: float,
            templates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every F clef with no detector box between page columns x0..x1 on one staff: a dot pair straddling the F line (`f_dot_pairs`,
    witness 1) AND the page's own F body where those dots put it (`f_body_match`, witness 2). Each: {pair, match, read (score >=
    `F_TEMPLATE_READ_SCORE`), candidate (score >= `F_TEMPLATE_CANDIDATE_SCORE`), area}. Two witnesses, never one; nothing without a
    template (a page with no read F clef reads none)."""
    if not templates:
        return []
    out = []
    for p in f_dot_pairs(ink, lines, sp, x0, x1):
        m = f_body_match(ink, sp, p, templates)
        if m.get("score", 0.0) < F_TEMPLATE_CANDIDATE_SCORE or "box" not in m:
            continue
        b = m["box"]
        # the clef's left edge: the matched body's, but never further left of its dots than a body is wide (a template laid over a C
        # clef standing just before it -- Litolff bar 110/111 -- must not put this clef before that one)
        left = max(float(b[0]), float(p["x_left"]) - F_BODY_MAX_REACH_SPACES * sp)
        area = nobox_area(b, p, left, sp)
        out.append({"pair": p, "match": m, "read": m["score"] >= F_TEMPLATE_READ_SCORE, "area": area})
    return out


# --------------------------------------------------------------------------------------------------------------------------------------
# Step 2: the clef in force at a head
# --------------------------------------------------------------------------------------------------------------------------------------
def changes_of(rows: Sequence[Any]) -> List[Tuple[float, Optional[str], Any]]:
    """The clefs printed INSIDE a staff (not its header), as (left x page px, kind or None, row), left to right, from step 1's
    `Q.CLAIMED_AREA` rows (source `clef_pagewide`, `change: True`)."""
    out = []
    for r in rows:
        d = getattr(r, "detail", None) or {}
        if d.get("source") != SOURCE or not d.get("change"):
            continue
        v = r.value
        if not (isinstance(v, (list, tuple)) and len(v) == 4):
            continue
        # a change governs from its LEFT edge. (Tried 2026-11-02: from its right edge, so a false head box on the clef's own ink -- Litolff
        # bar 38 -- is not pitched from it; but a C claim's area runs on into the heads it touches, and 12 heads right after a C clef
        # went right -> wrong on the frozen sample. Reverted; the false head is an ink-claim question, not the carry's.)
        out.append((float(v[0]), d.get("kind"), r))
    out.sort(key=lambda t: t[0])
    return out


def candidates_of(refusals: Sequence[Any]) -> List[Tuple[float, None, Any]]:
    """The CLEF-SHAPED CANDIDATES inside a staff that were not claimed with a read kind (step 1's abstentions, source `clef_pagewide`,
    `candidate: True`): (left x page px, None, row), left to right. ROADMAP 2.251 carry (b): a carried clef stops at one."""
    out = []
    for r in refusals:
        d = getattr(r, "detail", None) or {}
        if d.get("source") != SOURCE or not d.get("candidate") or d.get("x_page") is None:
            continue
        out.append((float(d["x_page"]), None, r))
    out.sort(key=lambda t: t[0])
    return out


def clef_in_force(head_x: float, changes: Sequence[Tuple[float, Optional[str], Any]],
                  candidates: Sequence[Tuple[float, None, Any]] = (), header: Optional[str] = None
                  ) -> Optional[Tuple[Optional[str], Any]]:
    """The clef printed LAST before `head_x` on the staff: (kind or None for unread, row) of the last change whose left edge is left of
    the head, or None where no change stands before it (the header clef governs).

    ROADMAP 2.251 carry (b) (CLAUDE rule 8, §4): a clef-shaped CANDIDATE (`candidates_of`: ink that may be a clef, not read) standing
    after a change whose kind differs from the header clef `header` and before the head STOPS the carry -- the head is unread (None,
    the candidate's row), never carried past ink that might be the return. A candidate where the header's own kind is in force (no
    change yet, or a return to it) changes nothing: the clef the head is pitched from is then the one the no-carry reading uses too."""
    got = None
    weak_off = strong_stop_enabled()
    events = sorted([(x, 0, k, r) for x, k, r in changes] + [(x, 1, None, r) for x, _k, r in candidates], key=lambda t: (t[0], t[1]))
    for x, is_cand, kind, r in events:
        if x >= head_x:
            break
        if is_cand:
            if weak_off and is_weak_candidate(r):
                continue                                   # ROADMAP 2.261 fix 3: counted (its abstention row), never a stop
            if got is not None and got[0] is not None and got[0] != header:
                got = (None, r)
            elif _strong_f(r) or _strong_g(r):
                # round 2 (Sean's carry tile 11, Vc bar 346: a real F clef at body 0.69, below READ): an F clef seen by BOTH witnesses
                # but below the read score stops whatever clef is in force -- the header's too -- unless that clef is itself an F clef
                # (then the candidate changes nothing). It NARROWS (the heads go unread, red), it never decides bass. ROADMAP 2.324 r8b:
                # the same for a mid-line G box with ink past the staff and no curl seen (`G_BOX_NO_CURL`), unless a G clef is in force
                in_force = got[0] if got is not None else header
                same = F_KINDS if _strong_f(r) else G_KINDS
                if in_force is None or in_force not in same:
                    got = (None, r)
            continue
        got = (kind, r)
    return got


#: the F-family clef names (`clef_geometry.CLEF_BY_FAMILY_LINE["F"]`)
F_KINDS = ("bass", "varbaritone", "subbass")


def _strong_f(row: Any) -> bool:
    d = getattr(row, "detail", None) or {}
    return bool(d.get("strong")) and d.get("family") == "F"


#: the G-family clef names
G_KINDS = ("treble", "french", "treble8vb", "treble8va")


def _strong_g(row: Any) -> bool:
    d = getattr(row, "detail", None) or {}
    return bool(d.get("strong")) and d.get("family") == "G"


def any_strong(candidates: Sequence[Tuple[float, None, Any]]) -> bool:
    """Whether a staff's candidates include a possible clef strong enough to stop the header's clef too (`_strong_f`, `_strong_g`)."""
    return any(_strong_f(r) or _strong_g(r) for _x, _k, r in candidates)
