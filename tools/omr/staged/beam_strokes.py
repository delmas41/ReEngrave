"""ROADMAP 2.202 -- the shared ink map, STEP 3: a head's beams from the STROKE MAP (flag `OMR_BEAMS_FROM_STROKES`, requires `OMR_STROKE_MAP`).

STAGED ADJUDICATE, PURE: this module imports nothing from the pipeline. `adjudicators/rhythm.py::_beams_from_strokes` is the only caller; it
builds `StrokeView`s from `Q.STROKE` rows and hands them here. Nothing in this file decides a duration: it says what each stroke IS (by
measured shape), which strokes a detector box stands on, and what the strokes at one stem's tip count. The adjudicator turns that into
narrowings and decisions (CLAUDE §3: the answer follows -> decided; it does not -> narrowed with candidates).

THE ROLES (a stroke's role is a function of ITS OWN fields and its neighbours, never of the box that happens to cover it) --

  beam       horizontal, touches >= 2 vertical strokes (stems), thick as a beam         (a beam joins its stems)
  beam_stub  horizontal, touches ONE vertical stroke, thick as a beam                   (Sean 2026-10-09: "a beam must not only
             connect to its note but also to another note" -> counted as a CANDIDATE level, never a decided one)
  span_thin  touches >= 2 vertical strokes but thinner than a beam, or curved           (a slur / tie / hairpin line across stems)
  hook       horizontal or curve, touches ONE vertical stroke, thinner than a beam, short (a flag)
  hook_or_stub  the same, longer than the hook cut but inside its near-miss band        (cannot tell flag from a stub: never decided)
  other      everything else (a vertical, a blob, a lone horizontal, a long one-stem line)

THE CUT-OFFS ARE MEASURED ON THE STROKE FIELDS, NOT TUNED TO A TARGET (benchmarks/shared-ink-map-2026-10/FINDINGS.md 2.202 section 1;
Litolff pages 2 and 4, the 2.198 ON record: 395 horizontal/curve strokes under 373 detector beam boxes, 15 under 39 detector flag boxes; `hook_beam_measure.py`):

  * `BEAM_MIN_THICKNESS_SP` 0.5. The thickness of the 190 horizontal strokes that touch >= 2 stems is two populations with a gap between
    them: 0.06-0.437 (66 strokes: slur, tie and hairpin remnants -- Sean 2026-10-09 "the thickness of a beam is always more than a
    hairpin") and 0.546-1.0 (124 strokes, median 0.653). 0.5 is the engraving convention for a beam's thickness (about half a space) and
    sits in the gap.
  * `HOOK_MAX_SPACES` 1.6. The 12 one-stem strokes under detector FLAG boxes: 10 are near-horizontal, 0.63-1.45 sp long (thickness 0.12-
    0.38); two are slanted curves, 1.93 and 2.69. 1.6 is the longest near-horizontal flag plus 0.15; `HOOK_NEAR_MISS_SPACES` 0.8 widens it
    to 2.4 so a flag that is a little longer (the 1.93 curve) is NARROWED (`hook_or_stub`), not decided; the 2.69 curve is not rescued.
    The one-stem strokes under BEAM boxes overlap the flag population in length (32 of 100 are <= 1.6 sp) and thickness (median 0.31):
    LENGTH AND THICKNESS ALONE DO NOT SEPARATE A HOOK FROM A BEAM STUB. What separates them is the stem, below.
  * a one-stem short stroke is a FLAG only when its stem touches NO beam-role stroke (a stem that carries a spanning beam is a beamed
    stem; a short stroke beside it is a partial-beam stub = a level candidate). That is structural, not a number.

A cut measured on one plate (n = 15 for the hook length) may only NARROW until another publisher confirms it (CLAUDE §4): the margins are
returned with every role so a refusal says how close it came.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

#: A vertical stroke is a STEM only up to this long (staff spaces). Measured on Litolff pp.2-16 (the 2.202 milestone gather): the 4,260 vertical
#: strokes that coincide with a `Q.STEM` (cv_lines) row are 1-8 sp long (only 10 reach 8-9); the 11,457 that coincide with none pile up at 8 and at
#: 12 sp (barlines, system edges, the cell's full height). A hook "on one stem" that is really a stroke leaning on a barline was 118 of the 122
#: Litolff map-hook boxes (`hook_box_funnel.py`): such a vertical is not a stem and counts for nothing here.
STEM_MAX_SPACES = 8.0
#: A beam's thickness, staff spaces. Measured gap between the two thickness populations of the strokes that span >= 2 stems (module doc).
BEAM_MIN_THICKNESS_SP = 0.5
#: 2.202f (Sean's round-3 tile 8, Brahms p12, a beam 0.49 thick): BELOW the cut and down to this, a stroke across >= 2 stems is in the TROUGH
#: between the two populations and thickness cannot tell a beam from a thin span. Measured on the frozen sample, horizontal strokes touching >= 2
#: stems, sixteenths of a space (`thick_census`, FINDINGS 2.202 section 5i): Litolff ... 0.375: 281, 0.4375: 166, 0.5: 143, 0.5625: 188, 0.625: 360
#: (mode); Brahms ... 0.375: 147, 0.4375: 83, 0.5: 80, 0.5625: 154, 0.625: 233 (mode) -- the same trough on both plates. A trough stroke at a stem's tip
#: is `beam_doubt`: never a level, never a refutation (the map abstains there; rule 8).
BEAM_DOUBT_MIN_THICKNESS_SP = 0.4375
#: A flag's hook is at most this long (staff spaces) to be DECIDED a hook; up to `+ HOOK_NEAR_MISS_SPACES` it is `hook_or_stub`.
HOOK_MAX_SPACES = 1.6
HOOK_NEAR_MISS_SPACES = 0.8
#: The window at a stem's tip in which a stroke counts as one of its beam levels / hooks: from this far BEYOND the tip (the beam's outer
#: edge past the stem end) to this far INWARD (level 1 starts at the tip, 2 at ~0.9, 3 ~1.8, 4 ~2.7, each ~0.6 thick;
#: `rhythm.BEAM_STEM_RUNS_PAST_MAX_SPACES` 2.5 + one beam -- derived from the stacking geometry, not fitted).
TIP_OUTWARD_SPACES = 0.5
TIP_INWARD_SPACES = 3.3
#: Two strokes touching one stem whose centres are closer than this (staff spaces) are one level (a stroke cut in two by a crossing).
LEVEL_MIN_SEPARATION_SPACES = 0.4
#: ROADMAP 2.202b. TWO beams are printed one above the other with a gap: beam 0.5 sp + gap 0.25 sp + beam 0.5 sp = 1.25 sp (the engraving convention the
#: tip window above is built on: level pitch ~0.75 sp). A slab that spans the stems and is this thick is TWO levels fused by the scan, not one beam
#: (a single beam is 0.5-0.7 sp; measured, FINDINGS 2.202 section 5c), measured at THE STEM'S OWN x (`local_thickness`). Counted as two only while its outer edge lies AT the tip (within
#: `FUSED_OUTER_EDGE_SPACES`: a "slab" 3 sp inward of the tip is a head cluster, the 2.202 cause 2) and only up to `FUSED_MAX_THICKNESS_SPACES`
#: (three levels fused would be 2.0 sp; nothing between is measured, so a thicker slab is left as the one level it was counted as).
FUSED_DOUBLE_MIN_THICKNESS_SPACES = 1.0
FREE_END_HOOK = True
FUSED_MAX_THICKNESS_SPACES = 1.75
FUSED_LOCAL_MIN_SPACES = 0.8      # 2.202e: the cut on the thickness AT THIS STEM's x (the 12-sample profile is coarse: a second beam that STARTS at this stem reads 0.96; measured gap single 0.31-0.66 | double 0.8-1.6, FINDINGS 5f)
FUSED_OUTER_EDGE_SPACES = 0.6
#: ROADMAP 2.202b. A beam-role stroke that does not TOUCH the head's stem stroke but ends within this many staff spaces of it (box to box: the scan
#: cuts a beam where it meets a stem, or the stem stops short of the beam) is the stem's beam: a beam IS the thing that joins its stems.
JOIN_MAX_GAP_SPACES = 0.5
#: ...and the joining beam's OUTER edge lies within this many staff spaces of the stem's tip (the first level of a beam).
JOIN_OUTER_EDGE_SPACES = 0.6
#: A vertical stroke is THIS stem when it overlaps the stem's x-span (within this slack) and y-range.
STEM_MATCH_X_SLACK_SPACES = 0.35
#: How far (staff spaces) beyond the head's half-width a stem's far end may stand and still be the head's stem (the stem finder's own 0.35).
STEM_HEAD_X_SLACK_SPACES = 0.35
#: How far (staff spaces) past the head's box edge a stem's far end must stand to be the head's stem in that direction.
STEM_PAST_HEAD_MIN_SPACES = 0.0


@dataclass(frozen=True)
class StrokeView:
    """One `Q.STROKE` row as this module reads it (canonical cell px; lengths in staff spaces)."""
    ordinal: int
    kind: str                                    # vertical / horizontal / curve / blob
    box: Tuple[float, float, float, float]       # x, y, w, h
    length: float
    thickness: float
    sagitta: Optional[float]
    angle: float
    touches: Tuple[Tuple[int, float], ...]
    space_px: float                              # canonical px per staff space at the stroke
    row_id: str = ""
    profile: Tuple[int, ...] = ()                # thickness along the stroke's axis, 12 samples, sixteenths of a staff space (empty: not filed)
    ends: Tuple[float, ...] = ()                 # x0, y0, x1, y1: the extreme pixels along the axis (the centre line's two ends; empty: not filed)
    end_steps: Tuple[float, ...] = ()            # 2.318 r3: where the two `ends` stand against the staff, half-spaces from the top line (0) to the bottom line (8), at their own x (empty: not filed)
    cut: str = ""                                # 2.318 r4: the cell-crop edges the ink reaches, letters "tblr" (`Q.STROKE` detail `cut`; "" = none / not filed)
    family: str = ""                             # 2.318 r4: the family of the mark that owns this stroke ("dynamic", "arc", "head" ...; the stroke owner's verdict), "" = unclaimed


def local_thickness(s: StrokeView, x: float) -> float:
    """The stroke's thickness (staff spaces) in the neighbourhood of page-x `x` (canonical cell px): the mean of the three profile samples around it;
    the stroke's own median thickness where no profile was filed or `x` is off the stroke. CLAUDE section 5: measure against the subject LOCALLY."""
    if len(s.profile) < 3 or s.box[2] <= 0 or not (s.box[0] - 0.35 * s.space_px <= x <= s.box[0] + s.box[2] + 0.35 * s.space_px):
        return s.thickness
    n = len(s.profile)
    i = int(round(min(max((x - s.box[0]) / s.box[2], 0.0), 1.0) * (n - 1)))
    lo, hi = max(0, i - 1), min(n, i + 2)
    return sum(s.profile[lo:hi]) / float(hi - lo) / 16.0


def _centre_y(beam: StrokeView, v: StrokeView) -> Optional[float]:
    """The beam's centre line at the vertical `v`'s x (from the stroke's `ends`); `None` without ends or outside the beam's run."""
    if len(beam.ends) < 4:
        return None
    sp = beam.space_px if beam.space_px > 0 else 1.0
    x0, y0, x1, y1 = beam.ends[:4]
    vx = v.box[0] + v.box[2] / 2.0
    if not (min(x0, x1) - 0.35 * sp <= vx <= max(x0, x1) + 0.35 * sp):
        return None
    return y0 if x1 == x0 else y0 + (y1 - y0) * (vx - x0) / (x1 - x0)


def _level_gap(a: StrokeView, b: StrokeView) -> float:
    """Vertical distance (canonical px) between two beam-like strokes: their centre lines at the middle of the x-stretch both run along (`ends`); the boxes'
    centres where either has no line or they share no stretch."""
    if LEVEL_BY_LINE and len(a.ends) >= 4 and len(b.ends) >= 4:
        lo = max(min(a.ends[0], a.ends[2]), min(b.ends[0], b.ends[2]))
        hi = min(max(a.ends[0], a.ends[2]), max(b.ends[0], b.ends[2]))
        if hi > lo:
            xm = (lo + hi) / 2.0

            def y_at(s: StrokeView) -> float:
                x0, y0, x1, y1 = s.ends[:4]
                return y0 if x1 == x0 else y0 + (y1 - y0) * (xm - x0) / (x1 - x0)
            return abs(y_at(a) - y_at(b))
    return abs((a.box[1] + a.box[3] / 2.0) - (b.box[1] + b.box[3] / 2.0))


def face_gap(beam: StrokeView, v: StrokeView) -> Optional[float]:
    """2.202f. Staff spaces of paper between the vertical `v`'s near end and the FACE of `beam` at `v`'s own x (the centre line from the
    stroke's `ends`, +/- half its thickness): >= 0 where `v` stops short of the beam (above or below it), negative where they overlap. `None`
    where the beam has no ends filed or `v`'s x lies outside the beam's run. A box gap cannot say this for a sloped beam: its box is as tall as the slope."""
    yc = _centre_y(beam, v)
    if yc is None:
        return None
    sp = beam.space_px if beam.space_px > 0 else (v.space_px if v.space_px > 0 else 1.0)
    top, bot = yc - beam.thickness * sp / 2.0, yc + beam.thickness * sp / 2.0
    v_top, v_bot = v.box[1], v.box[1] + v.box[3]
    if v_top >= yc:                      # the vertical hangs below the beam: its top end faces the beam's lower face
        return (v_top - bot) / sp
    if v_bot <= yc:                      # it stands above: its lower end faces the upper face
        return (top - v_bot) / sp
    return -1.0                          # it runs through the centre line: crossing, not a stem stopping short


#: 2.202f: how far short of the beam's face a stem may stop and still be the beam's (Sean 2026-10-28: "the beam covers the width of where those
#: notes with stems occur ... they were all 8th notes that belong to that beam even though the ink is broken"). The convention is the COVER;
#: this bound only keeps a stem of another system / voice far below out (an erased line costs 0.12-0.25 sp, two cut lines < 1; Brahms p0 4/9: 0.75).
FACE_JOIN_MAX_SPACES = 1.0


def _face_joined(s: StrokeView, v: StrokeView, by_ord: Optional[Dict[int, StrokeView]] = None) -> bool:
    """`v` stands under `s`'s run and stops short of its face by at most `FACE_JOIN_MAX_SPACES` of PAPER, with no other mark's ink in the
    column between them (a sliver inside the stem's own column is the stem's broken piece: its length is not paper). Sean 2026-10-28 (the beam
    covers its notes' stems); 2.202f round-3 Litolff p2 13/0,1,3 (a beam on the top line, erased loose of 3 of its 4 stems), Brahms p0 4/9 (a
    stem cut at a line: 1.1 sp to the beam's face, 0.5 of it the stem's own piece)."""
    g = face_gap(s, v)
    if g is None or g < -0.05:
        return False
    if by_ord is None or g <= 0:
        return g <= FACE_JOIN_MAX_SPACES
    sp = s.space_px if s.space_px > 0 else 1.0
    cx0, cx1 = v.box[0] - 0.35 * sp, v.box[0] + v.box[2] + 0.35 * sp
    top_end = v.box[1] >= _centre_y(s, v)          # the vertical hangs below the beam: the paper between is above its top
    lo, hi = (v.box[1] - g * sp, v.box[1]) if top_end else (v.box[1] + v.box[3], v.box[1] + v.box[3] + g * sp)
    piece = 0.0                                    # px of the gap the stem's own broken pieces fill
    for o in by_ord.values():
        if o.ordinal in (s.ordinal, v.ordinal) or o.kind == "owned":
            continue
        if o.box[1] + o.box[3] <= lo or o.box[1] >= hi or o.box[0] + o.box[2] <= cx0 or o.box[0] >= cx1:
            continue
        if o.box[0] >= cx0 and o.box[0] + o.box[2] <= cx1:
            piece += min(o.box[1] + o.box[3], hi) - max(o.box[1], lo)     # inside the stem's own column: a broken piece of it
            continue
        return False                               # another mark's ink between the stem and the beam
    return (g * sp - piece) / sp <= FACE_JOIN_MAX_SPACES


#: 2.318 r6: A BEAM ENDS ON ITS OUTER STEMS (Sean 2026-10-09: a beam connects its note to another note; 2026-10-28: "the beam covers the width of where
#: those notes with stems occur ... they were all 8th notes that belong to that beam even though the ink is broken"). The map sometimes ends a beam's
#: stroke a hair short of its FIRST or LAST stem (the corner where they meet goes to neither stroke): Litolff p2 0/8/0, p15 1/8/17, beamed eighths whose
#: first note read "no beam". A stem that stands just past a beam's end, its own end LEVEL with the beam's outer face there, is that beam's outer stem.
#: MEASURED on the tile pages (every beam-shaped stroke end against the nearest stem-length vertical beyond it, level within `END_JOIN_LEVEL_SPACES`, not
#: touching): the paper between is 0.3-0.5 sp for 9 (Litolff 7, Brahms 2: the unjoined outer stems), one at 0.7, 1.0 sp and more for 37 (the next
#: note's stem). The cut is `JOIN_MAX_GAP_SPACES` (0.5, 2.202b's own). Never a stem whose end is not level with the beam, never across more paper.
END_JOIN = True
END_JOIN_LEVEL_SPACES = 0.3


def _end_joined(s: StrokeView, v: StrokeView, end_y: Optional[float] = None) -> bool:
    """The vertical `v` stands just beyond an END of the horizontal stroke `s` (outside its run) with its own end (`end_y`; either end when None)
    level with the beam's outer face at that end."""
    if not END_JOIN or len(s.ends) < 4 or s.kind != "horizontal" or s.thickness < BEAM_MIN_THICKNESS_SP:
        return False
    if v.length < SHORT_STEM_SPACES:
        return False        # a stem, not a head's outline piece (Sean's L10, Litolff p2 0/10/1/5: a 1.9 sp sliver beside a head made its stub "a beam")
    sp = s.space_px if s.space_px > 0 else 1.0
    x0, y0, x1, y1 = s.ends[:4]
    if x0 > x1:
        x0, y0, x1, y1 = x1, y1, x0, y0
    vx0, vx1 = v.box[0], v.box[0] + v.box[2]
    if vx1 <= x0 + 0.1 * sp:
        gap, ey = x0 - vx1, y0
    elif vx0 >= x1 - 0.1 * sp:
        gap, ey = vx0 - x1, y1
    else:
        return False
    if gap > JOIN_MAX_GAP_SPACES * sp:
        return False
    # `ends` are the stroke's extreme PIXELS, somewhere in its band, not its centre line: the band at this end lies within one thickness of `ey`
    # either way and inside the stroke's own extent.
    th = s.thickness * sp
    lvl = END_JOIN_LEVEL_SPACES * sp
    v_top, v_bot = v.box[1], v.box[1] + v.box[3]

    def at_top(y: float) -> bool:        # a stem hanging below the beam ends at the band's TOP face
        return max(ey - th, s.box[1]) - lvl <= y <= ey + lvl

    def at_bottom(y: float) -> bool:     # a stem standing above it ends at the band's BOTTOM face
        return ey - lvl <= y <= min(ey + th, s.box[1] + s.box[3]) + lvl
    if end_y is None:
        return at_top(v_top) or at_bottom(v_bot)
    return (abs(end_y - v_top) < 1.0 and at_top(end_y)) or (abs(end_y - v_bot) < 1.0 and at_bottom(end_y))


#: 2.318 r6: A CLOT AT THE JOIN. Where a beam meets a stem the map sometimes files the meeting itself as a separate small piece of ink (a blob, a
#: short upright bar), so the beam's stroke touches the piece and the piece touches the stem, and neither touches the other (Brahms p17 0/12/3, 0/10/1:
#: the last note of a beamed three read "no beam" and was written a quarter). Ink that runs unbroken from the beam to the stem, through one or two
#: unclaimed pieces no bigger than `CLOT_PIECE_MAX_SPACES` lying inside the beam's own band, joins them (joining goes by ink, Sean 2026-11-18).
#: Never through a claimed stroke (a head, a letter), never through a piece that leaves the beam's band. The size is the hook cut (1.6 sp): the three
#: pieces seen are 1.0 x 1.4, 0.9 x 1.5 and 0.6 x 1.4 sp; a number from one plate, it decides only together with the unbroken contact.
CLOT_JOIN = True
CLOT_PIECE_MAX_SPACES = 1.6
CLOT_BAND_SLACK_SPACES = 0.5
#: 2.318 r6: centre line to centre line, the outer beam of a stack lies at most a beam's thickness plus the space between two beams from the next
#: (0.6 + 0.75; measured 0.85 on Brahms p17 1/10, 0.96 on Sean's B09).
OUTER_LEVEL = True
FOREIGN_LEVEL = True
OUTER_LEVEL_MAX_SPACES = 1.35


def _clot_stems(s: StrokeView, by_ord: Dict[int, StrokeView]) -> List[int]:
    """Ordinals of stem-length verticals the horizontal stroke `s` reaches through one or two small unclaimed pieces lying in its own band."""
    if not CLOT_JOIN or s.kind != "horizontal" or s.thickness < BEAM_MIN_THICKNESS_SP:
        return []
    sp = s.space_px if s.space_px > 0 else 1.0
    y0, y1 = s.box[1] - CLOT_BAND_SLACK_SPACES * sp, s.box[1] + s.box[3] + CLOT_BAND_SLACK_SPACES * sp

    def piece(o: int) -> bool:
        t = by_ord.get(o)
        return (t is not None and t.ordinal != s.ordinal and t.kind in ("blob", "horizontal") and max(t.box[2], t.box[3]) <= CLOT_PIECE_MAX_SPACES * sp
                and t.box[1] >= y0 and t.box[1] + t.box[3] <= y1)

    def stem(o: int) -> bool:
        t = by_ord.get(o)
        return t is not None and t.kind == "vertical" and SHORT_STEM_SPACES <= t.length <= STEM_MAX_SPACES
    direct = {j for j, _c in s.touches}
    out = set()
    for j in direct:
        if not piece(j):
            continue
        for k, _c in by_ord[j].touches:
            if stem(k):
                out.add(k)
            elif piece(k) and k not in direct:
                out.update(m for m, _c2 in by_ord[k].touches if stem(m))
    return sorted(out - direct)


#: 2.319: EVERY BEAM LIES WITHIN ONE BAR (page-facts, Sean 2026-11-04: "Every beam is within a bar"). A stroke whose ink runs out of the bar at BOTH ends
#: (the cell's crop cuts it left and right) crosses the barlines, so it is a staff line or a rule, never a beam -- the neighbour staff's line in the cell's
#: padding, which the erase of THIS staff's lines leaves standing, lies under the flagged eighths of Brahms p25 0/2/1 and stem tips that stop short of
#: it were joined to it by the face rule: four flagged eighths counted as one beam group. Structural. Never a stroke that ends inside the bar at either end.
BEAM_WITHIN_ONE_BAR = True


def role_of(s: StrokeView, by_ord: Dict[int, StrokeView], *, face_join: bool = False, trough: bool = False, one_count: bool = False) -> Dict[str, object]:
    """The role of one stroke and the signed margins that say how close it came. Pure; reads `s` and the kinds of its neighbours.

    2.202f, both OFF by default (only the 2.202 path passes them): `face_join` also counts as this stroke's stems the stem-length verticals that
    stand under its run and stop short of its face (<= `FACE_JOIN_MAX_SPACES`, nothing between) at their own x (a beam lying on a staff line loses its contact with its stems to the
    erase: Litolff p2 13/0,1,3 read 1 stem of 4, so a `beam_stub`); `trough` files a >= 2-stem horizontal stroke in the thickness trough
    (`BEAM_DOUBT_MIN_THICKNESS_SP` .. `BEAM_MIN_THICKNESS_SP`) as `beam_doubt` instead of `span_thin`."""
    if s.kind not in ("horizontal", "curve"):
        return {"role": "other", "why": "kind:" + s.kind}
    if one_count and BEAM_WITHIN_ONE_BAR and "l" in (s.cut or "") and "r" in (s.cut or ""):
        return {"role": "other", "why": "runs_out_of_the_bar"}
    stems = sorted({j for j, _c in s.touches if j in by_ord and by_ord[j].kind == "vertical" and by_ord[j].length <= STEM_MAX_SPACES})
    gap_stems: List[int] = []
    if face_join and s.kind == "horizontal" and stems:
        # only a stroke that already reaches a stem on its own is a beam whose width can own more (2.202f tiles 3, 8: a hairpin under a
        # stem tip touches no stem, and was taken for a broken beam -- FINDINGS 5i)
        gap_stems = sorted(v.ordinal for v in by_ord.values()
                           if v.kind == "vertical" and v.length <= STEM_MAX_SPACES and v.ordinal not in stems and v.ordinal != s.ordinal
                           and (_face_joined(s, v, by_ord) or (one_count and _end_joined(s, v))))
        stems = sorted(stems + gap_stems)
    if one_count and s.kind == "horizontal":
        clot = [o for o in _clot_stems(s, by_ord) if o not in stems]         # 2.318 r6: stems the beam reaches through a clot at the join
        gap_stems = sorted(gap_stems + clot)
        stems = sorted(stems + clot)
    nv = len(stems)
    out: Dict[str, object] = {"stems": nv, "stem_ordinals": stems, "stems_by_face": gap_stems, "thickness": s.thickness, "length": s.length,
                              "thickness_margin": round(s.thickness - BEAM_MIN_THICKNESS_SP, 3),
                              "hook_margin": round(HOOK_MAX_SPACES - s.length, 3)}
    thick = s.thickness >= BEAM_MIN_THICKNESS_SP
    if nv >= 2:
        # "A beam never has an arc" (Sean 2026-10-09): a CURVE-kind stroke across stems is a slur, however thick.
        out["role"] = "beam" if (s.kind == "horizontal" and thick) else (
            "beam_doubt" if (trough and s.kind == "horizontal" and s.thickness >= BEAM_DOUBT_MIN_THICKNESS_SP) else "span_thin")
    elif nv == 1:
        if thick and s.kind == "horizontal":
            out["role"] = "beam_stub"
        elif s.length <= HOOK_MAX_SPACES:
            out["role"] = "hook"
        elif s.length <= HOOK_MAX_SPACES + HOOK_NEAR_MISS_SPACES:
            out["role"] = "hook_or_stub"
        else:
            out["role"] = "other"
            out["why"] = "one_stem_too_long"
    else:
        out["role"] = "other"
        out["why"] = "touches_no_stem"
    return out


def roles(strokes: Sequence[StrokeView], *, face_join: bool = False, trough: bool = False, one_count: bool = False) -> Dict[int, Dict[str, object]]:
    """`one_count` (2.318 r6, only the one beam count passes it): a beam also owns the outer stem a hair past its stroke's end (`_end_joined`)."""
    by_ord = {s.ordinal: s for s in strokes}
    return {s.ordinal: role_of(s, by_ord, face_join=face_join, trough=trough, one_count=one_count) for s in strokes}


def box_support(under: Iterable[int], role_by_ord: Dict[int, Dict[str, object]]) -> Dict[str, object]:
    """What a detector BEAM box stands on, from the roles of the strokes `Q.GLYPH_STROKES` lists for it.

    `support`: `beam` (some stroke under it is beam-shaped), `hook` (no beam, at least one hook), `unsupported` (nothing beam- or
    hook-shaped: empty paper, a stem alone, a thin line, a one-stem stub, an ambiguous hook). `reason` names why, for the record."""
    under = [o for o in under if o in role_by_ord]
    rs = [str(role_by_ord[o]["role"]) for o in under]
    if "beam" in rs:
        return {"support": "beam", "strokes": under}
    if "hook" in rs:
        return {"support": "hook", "strokes": under, "hooks": [o for o in under if role_by_ord[o]["role"] == "hook"]}
    if not under:
        why = "box_on_paper"
    elif all(str(role_by_ord[o].get("why", "")) == "kind:vertical" for o in under):
        why = "box_on_a_stem"
    elif "hook_or_stub" in rs:
        why = "hook_or_stub"
    elif "beam_stub" in rs:
        why = "one_stem_stub"
    elif "span_thin" in rs:
        why = "thin_or_curved_span"
    else:
        why = "no_beam_or_hook_shaped_stroke"
    return {"support": "unsupported", "strokes": under, "reason": why}


def _box_gap(a: Sequence[float], b: Sequence[float]) -> float:
    """Distance between two (x, y, w, h) boxes in their own units; 0 when they overlap or touch."""
    dx = max(0.0, max(a[0], b[0]) - min(a[0] + a[2], b[0] + b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[1] + a[3], b[1] + b[3]))
    return (dx * dx + dy * dy) ** 0.5


def find_stem_stroke(strokes: Sequence[StrokeView], stem_box: Sequence[float]) -> Optional[StrokeView]:
    """The vertical stroke that IS the stem `stem_box` (x, y, w, h, canonical px), or None when the map holds none there (cannot tell)."""
    sx, sy, sw, sh = (float(v) for v in stem_box)
    best, best_ov = None, 0.0
    for s in strokes:
        if s.kind != "vertical" or s.length > STEM_MAX_SPACES:
            continue
        slack = STEM_MATCH_X_SLACK_SPACES * s.space_px
        bx, by, bw, bh = s.box
        if bx > sx + sw + slack or bx + bw < sx - slack:
            continue
        ov = min(by + bh, sy + sh) - max(by, sy)
        if ov > best_ov:
            best, best_ov = s, ov
    return best


BOX_AT_TIP_SHARES_THE_COUNT = True
LEVEL_BY_LINE = True       # 2.318 r5: levels told apart by the strokes' centre lines at the stem, not by their boxes
STACK_FILTER = True
STACK_FIRST_SPACES = 1.0      # the first level's outer edge lies within this of the tip (a sloped beam's box edge is off by <= 0.5)
STACK_GAP_SPACES = 0.75       # the next level starts within this of the previous level's inner edge (pitch 0.75 sp, gap 0.25)


def tip_clean(strokes: Sequence[StrokeView], stem: StrokeView, side: str) -> bool:
    """2.202d: NO stroke other than the stem touches it or lies within 0.5 sp of it (a beam-shaped or contested one; blobs and strokes another mark owns do not count) inside the tip
    window -- Sean's "clean tip" (2026-10-16). Ink of any kind there means the tip is NOT clean."""
    sp = stem.space_px if stem.space_px > 0 else 1.0
    bx, by, bw, bh = stem.box
    tip_y = by if side == "up" else by + bh
    lo, hi = (tip_y - TIP_OUTWARD_SPACES * sp, tip_y + TIP_INWARD_SPACES * sp) if side == "up" else (tip_y - TIP_INWARD_SPACES * sp, tip_y + TIP_OUTWARD_SPACES * sp)
    touching = {j for j, _c in stem.touches}
    for s in strokes:
        if s.ordinal == stem.ordinal or s.kind in ("blob", "owned", "vertical"):
            continue            # a blob is a head / dot / letter, not beam ink; an owned stroke is another mark's (a contested one still blocks)
        if s.box[1] + s.box[3] < lo or s.box[1] > hi:
            continue
        if s.ordinal in touching or _box_gap(s.box, stem.box) <= 0.5 * sp:
            return False
    return True


def _covers_head(s: StrokeView, head_box: Sequence[float]) -> bool:
    """2.202f (Sean's round-3 tile 1, Litolff p6 0/1/10/2): the stroke holds at least half of THIS head's box. A beam lies at the far end of the
    head's stem; a 'level' that holds the head is the head's own ink fused to its neighbours (Litolff merges), never a beam of it."""
    hx, hy, hw, hh = head_box[:4]
    ix = min(s.box[0] + s.box[2], hx + hw) - max(s.box[0], hx)
    iy = min(s.box[1] + s.box[3], hy + hh) - max(s.box[1], hy)
    return ix > 0 and iy > 0 and ix * iy >= 0.5 * hw * hh


def tip_reading(strokes: Sequence[StrokeView], role_by_ord: Dict[int, Dict[str, object]], stem: StrokeView, side: str, *,
                head_box: Optional[Sequence[float]] = None, face_join: bool = False, one_count: bool = False) -> Dict[str, object]:
    """What the strokes touching THIS stem say at its tip. `side` is the stem's direction ("up": the tip is the top).

    `beams`: ordinals of beam-role strokes touching the stem inside the tip window, one per level (strokes whose centres are closer than
    `LEVEL_MIN_SEPARATION_SPACES` are one level); `hooks`: the same for hook-role strokes; `stubs`: beam_stub / hook_or_stub strokes.
    `stem_beamed`: the stem touches ANY beam-role stroke (inside the window or not) -- the structural test that makes a short stroke a
    stub rather than a flag.

    2.202f (only the 2.202 path passes these): `head_box` drops any stroke holding half of this head's box (`_covers_head`); `face_join` joins a
    beam this stem stands under and stops short of (`_face_joined`, Sean 2026-10-28 "the beam covers the width") instead of the outer-edge test;
    `doubt` lists the trough strokes (`beam_doubt`) at the tip -- not levels, but the map cannot say "no beam" while one is there."""
    sp = stem.space_px if stem.space_px > 0 else 1.0
    bx, by, bw, bh = stem.box
    tip_y = by if side == "up" else by + bh
    if side == "up":
        lo, hi = tip_y - TIP_OUTWARD_SPACES * sp, tip_y + TIP_INWARD_SPACES * sp
    else:
        lo, hi = tip_y - TIP_INWARD_SPACES * sp, tip_y + TIP_OUTWARD_SPACES * sp
    by_ord = {s.ordinal: s for s in strokes}
    touching = [by_ord[j] for j, _c in stem.touches if j in by_ord]
    # 2.318 r6: A HEAD STANDS AT ONE END OF ITS STEM AND THE BEAM AT THE OTHER. "A level that holds the head is the head's own ink" (2.202f) is true at
    # the head's end. A box lying at the stem's FAR end, on the beam, is the beam's ink the detector boxed (Litolff p6 1/7/4, p2 0/7/1: a box where the
    # stem meets its beam): it carries the stem's own count like every box on that stem -- round 5 read it "no beam", a quarter among its stem's
    # eighths, and the whole chord left the file. Never at the head's end: there the 2.202f rule stands.
    box_at_tip = bool(one_count and BOX_AT_TIP_SHARES_THE_COUNT and head_box is not None
                      and abs(float(head_box[1]) + float(head_box[3]) / 2.0 - tip_y) <= STACK_FIRST_SPACES * sp)
    stem_beamed = any(role_by_ord.get(s.ordinal, {}).get("role") == "beam" for s in touching)
    found: Dict[str, List[StrokeView]] = {"beam": [], "hook": [], "stub": [], "doubt": []}
    own_head: List[int] = []
    for s in touching:
        r = role_by_ord.get(s.ordinal, {}).get("role")
        key = ("beam" if r == "beam" else "hook" if r == "hook" else "stub" if r in ("beam_stub", "hook_or_stub")
               else "doubt" if r == "beam_doubt" else None)
        if key is None:
            continue
        if head_box is not None and not box_at_tip and _covers_head(s, head_box):
            own_head.append(s.ordinal)
            continue
        y0, y1 = s.box[1], s.box[1] + s.box[3]
        if y1 < lo or y0 > hi:
            continue
        # 2.202e (5b cause 3; tile 2 of 2.202d: a 0.06 sp hairline touching a second stroke): a flag's far end is FREE. A hook that touches any
        # stroke but this stem is the start of a slur / tie, not a flag.
        if key == "hook" and FREE_END_HOOK and any(j != stem.ordinal for j, _c in s.touches):
            continue
        found[key].append(s)
    # 2.202b: a stem with NO beam level at its tip, and a beam-role stroke that comes within JOIN_MAX_GAP_SPACES of it without touching it, whose
    # OUTER edge lies at the tip (the first level: a beam's outer edge is where its stems end) and that is no thicker than one beam: the beam is this
    # stem's. (Measured, FINDINGS 2.202 section 5c: without these three conditions the same rule re-counted head clusters at 18 of 26 heads the readers
    # already agreed on.) Never adds a second level to a stem that already has one.
    joined: List[StrokeView] = []
    if not found["beam"]:
        touched = {s.ordinal for s in touching}
        for s in strokes:
            if s.ordinal in touched or s.ordinal == stem.ordinal or role_by_ord.get(s.ordinal, {}).get("role") != "beam":
                continue
            if s.thickness >= FUSED_DOUBLE_MIN_THICKNESS_SPACES:
                continue
            if head_box is not None and not box_at_tip and _covers_head(s, head_box):
                continue
            if face_join and len(s.ends) >= 4:
                # the beam's face at THIS stem's x, beyond its tip: the stem stands under the beam (Sean 2026-10-28)
                yc = _centre_y(s, stem)
                if yc is not None and ((side == "up" and yc < tip_y) or (side == "down" and yc > tip_y)) and _face_joined(s, stem, by_ord):
                    joined.append(s)
                elif one_count and _end_joined(s, stem, tip_y):
                    joined.append(s)          # 2.318 r6: the beam's outer stem, a hair past the stroke's end
                continue
            if _box_gap(s.box, stem.box) > JOIN_MAX_GAP_SPACES * sp:
                continue
            outer = s.box[1] if side == "up" else s.box[1] + s.box[3]
            if abs(outer - tip_y) > JOIN_OUTER_EDGE_SPACES * sp:
                continue
            joined.append(s)
        found["beam"].extend(joined)
    if one_count:
        touched = {s.ordinal for s in touching}
        if CLOT_JOIN and not found["beam"]:
            # 2.318 r6: the beam reaches this stem through a clot of ink at the join (`_clot_stems`)
            for s in strokes:
                if s.ordinal in touched or s.kind != "horizontal" or role_by_ord.get(s.ordinal, {}).get("role") != "beam":
                    continue
                if head_box is not None and not box_at_tip and _covers_head(s, head_box):
                    continue
                if s.box[1] + s.box[3] < lo or s.box[1] > hi:
                    continue
                if stem.ordinal in _clot_stems(s, by_ord):
                    found["beam"].append(s)
                    joined.append(s)
        if OUTER_LEVEL and found["beam"]:
            # 2.318 r6: EVERY STEM OF A GROUP REACHES THE OUTER BEAM; the extra beams lie inward of it, toward the heads. A beam running over this
            # stem's column one beam-spacing OUTWARD of the beam the stem's ink touches is the group's outer beam, and the stem's ink was cut between
            # the two (Brahms p17 1/10/1, 1/10/2: sixteenths whose stem stroke stops at the inner beam were read one beam). Never a beam farther out
            # than a beam and the space between two (`OUTER_LEVEL_MAX_SPACES`), never one that does not run over the stem.
            sx = bx + bw / 2.0
            base = list(found["beam"])
            have = {b.ordinal for b in base}
            for s in strokes:
                if s.ordinal in touched or s.ordinal in have or s.kind != "horizontal" or role_by_ord.get(s.ordinal, {}).get("role") != "beam":
                    continue
                if not (s.box[0] <= sx <= s.box[0] + s.box[2]):
                    continue
                cy = s.box[1] + s.box[3] / 2.0
                if not ((cy < tip_y) if side == "up" else (cy > tip_y)):
                    continue
                # ...and never a neighbour's: the two beams of one group hang on the same stems -- at least TWO whose ink touches both (a beam joins
                # two stems). The beam of the next staff's group lying just beyond shares none (Litolff p13 1/2/5), or the one stem whose ink
                # happens to run into it (Litolff p4 1/2/13: 2 more eighths read sixteenths with a single shared stem allowed).
                mine = {j for j, _c in s.touches if j in by_ord and by_ord[j].kind == "vertical"}
                if any(LEVEL_MIN_SEPARATION_SPACES * sp <= _level_gap(b, s) <= OUTER_LEVEL_MAX_SPACES * sp
                       and len(mine & {j for j, _c in b.touches}) >= 2 for b in base):
                    found["beam"].append(s)
                    joined.append(s)

    # 2.202c: levels are STACKED from the tip. A stroke that does not start where the previous level ends (its outer edge more than
    # STACK_GAP_SPACES past it; the first: more than STACK_FIRST_SPACES past the tip) is ink of something else lying in the window -- a head
    # of the other voice, a chord cluster -- not a level (FINDINGS 2.202 section 5d; 12 of 15 Litolff p9 narrowed heads, 5b cause 2).
    if STACK_FILTER and found["beam"]:
        def _d(s: StrokeView):       # (outer, inner) edge, spaces INWARD of the tip
            y0, y1 = s.box[1], s.box[1] + s.box[3]
            return ((y0 - tip_y) / sp, (y1 - tip_y) / sp) if side == "up" else ((tip_y - y1) / sp, (tip_y - y0) / sp)
        kept: List[StrokeView] = []
        reach = STACK_FIRST_SPACES
        for s in sorted(found["beam"], key=lambda t: (_d(t)[0], t.ordinal)):
            o_, i_ = _d(s)
            if o_ <= reach:
                kept.append(s)
                reach = max(reach, i_ + STACK_GAP_SPACES)
        found["beam"] = kept

    if one_count and FOREIGN_LEVEL and len(found["beam"]) >= 2:
        # 2.318 r6: A GROUP'S BEAMS HANG ON STEMS THAT COME FROM THE SAME SIDE AS THIS ONE. A beam at this stem's tip whose every other stem stands
        # on the far side of it -- running AWAY from this stem's head -- is the next group's beam, set so close that the two inks touch (Litolff p4
        # 1/2/13: four eighths whose stems end on the beam of the group below were read two beams, sixteenths). Structural; only ever takes a level
        # away where another stands, never the stem's only beam.
        sx = bx + bw / 2.0

        def hangs_away(s: StrokeView) -> bool:
            cy = s.box[1] + s.box[3] / 2.0
            others = [by_ord[j] for j, _c in s.touches if j in by_ord and by_ord[j].kind == "vertical" and by_ord[j].length <= STEM_MAX_SPACES
                      and abs(by_ord[j].box[0] + by_ord[j].box[2] / 2.0 - sx) > ONE_STEM_COLLINEAR_X_SPACES * sp]
            return bool(others) and all(((o.box[1] + o.box[3] / 2.0) < cy) if side == "up" else ((o.box[1] + o.box[3] / 2.0) > cy) for o in others)
        own = [s for s in found["beam"] if not hangs_away(s)]
        if own and len(own) < len(found["beam"]):
            found["beam"] = own

    def levels(group: List[StrokeView]) -> List[int]:
        # Two strokes are one level only where their INK is one band: compare their centre lines along the stretch BOTH run (`_line_gap`), never their
        # boxes' centres (a sloped stroke's box is far taller than its ink: Brahms B09's two beams, 0.96 sp apart along their common run, had boxes 0.39 sp
        # apart) and never at a stroke's end (where the stem's own ink bends the fitted line).
        out: List[StrokeView] = []
        for s in sorted(group, key=lambda t: (t.box[1] + t.box[3] / 2.0, t.ordinal)):
            if out and _level_gap(out[-1], s) < LEVEL_MIN_SEPARATION_SPACES * sp:
                continue
            out.append(s)
        return [t.ordinal for t in out]

    fused: List[int] = []
    beams = levels(found["beam"])
    by_o = {s.ordinal: s for s in found["beam"]}
    doubled: List[int] = []
    for o in beams:
        s = by_o[o]
        outer = s.box[1] if side == "up" else s.box[1] + s.box[3]
        # The slab is double (median over the stroke >= 1.0, Sean's rule) AND double at THIS stem's x: a group whose second beam covers some stems
        # only is ~0.6 sp along one stretch and ~1.25 along the next, and the median alone would double every stem of it (Brahms: 6 heads main read
        # as one level). The median is kept because a short bump of >= 1.0 in a 0.8 beam (a head merged with it: Litolff, 16 heads) is not a slab.
        here = local_thickness(s, bx + bw / 2.0)
        if (s.thickness >= FUSED_DOUBLE_MIN_THICKNESS_SPACES and FUSED_LOCAL_MIN_SPACES <= here < FUSED_MAX_THICKNESS_SPACES
                and s.kind == "horizontal"
                and abs(outer - tip_y) <= FUSED_OUTER_EDGE_SPACES * sp):
            fused.append(o)
        doubled.append(o)
        if o in fused:
            doubled.append(o)           # one slab = two levels: the ordinal is listed once per level

    return {"stem": stem.ordinal, "tip_y": tip_y, "stem_beamed": stem_beamed,
            "beams": doubled, "fused": fused, "joined": sorted(j.ordinal for j in joined), "hooks": levels(found["hook"]), "stubs": levels(found["stub"]),
            "hooks_all": sorted(s.ordinal for s in found["hook"]), "doubt": levels(found["doubt"]), "own_head": sorted(own_head)}


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
# ROADMAP 2.318 r3 (flag `OMR_ONE_BEAM_COUNT`, ON by default since 2026-11-19): THE ONE BEAM COUNT. How many beams stand at a stemmed note's stem, from the stroke map
# (built on the STAFF-ERASED raster, so a staff line is never taken for a beam) and nothing else. STAGED ADJUDICATE, PURE.
#
#   The stem is the vertical stroke whose INK touches the head's ink (Sean 2026-11-18: join by ink, never by box edge, centre or overlap; the
#   detector's box says only WHERE the head's ink is), followed to its FAR end. Every head on that stem gets the stem's one count (page fact:
#   every note on one stem shares one written value). A stem is never chosen by its midpoint against one head's centre (that left the upper
#   head of every chord with no stem: 2.318 FINDINGS, STEM CHOICE 314 Litolff / 307 Brahms).
#   The count is `tip_reading`'s, unchanged. Where it cannot tell it says so with its candidates; it never turns "cannot tell" into "no beam"
#   (rule 8): a stem the map holds no stroke for, a stem that touches a beam it did not count at its tip, a stub or a trough stroke at the tip,
#   and a beam too thick AT THE STEM (the staff line's own thickness taken out) to be one beam all NARROW.
#   FLAGS are another mark: the hooks at the tip are filed beside the count (`hooks`) and decide nothing here.
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
#: 2.318 r6: the longest upright that can be THIS head's stem where its ink touches the head's ink. `STEM_MAX_SPACES` (8.0) was measured for strokes
#: nothing ties to a head ("only 10 of 4,260 stems reach 8-9"; barlines and cell-high strokes pile up at 8 and 12). Two voices' stems drawn in one line
#: through a shared head or chord are one stroke 8.0-8.25 sp long (Litolff p15 0/3/14, p13 1/5/8: five notes the map had "no stem" for): up to 9 sp a
#: stroke whose ink touches the head's ink is its stem; a 12 sp stroke (a barline, the cell's height) never is.
ONE_STEM_MAX_SPACES = 9.0
#: A vertical stroke wider than this has head ink fused to it (Litolff merges): its stem stands at the far end (`stem_strokes.FUSED_MIN_WIDTH_SPACES`).
ONE_FUSED_MIN_WIDTH_SPACES = 0.6
#: Two pieces of one stem cut by a crossing (a beam, a ledger rung): within this of one x-column and this far apart vertically (the numbers
#: `stem_strokes.COLLINEAR_X_SPACES` / `BREAK_MAX_GAP_SPACES` already use, which were not tuned to a count).
ONE_STEM_COLLINEAR_X_SPACES = 0.3
ONE_STEM_BREAK_MAX_GAP_SPACES = 0.6
#: A staff line's own thickness, staff spaces, taken out of a beam's thickness where the beam lies on a line at the stem. MEASURED, NARROWS ONLY:
#: the median of `Q.STAFF_SKEW` thickness over the cells of the 20261117-night records, Litolff 0.254 / Brahms 0.245 (decile 0.21-0.30), one
#: scanner per plate; it only ever moves a note from "decided" to "narrowed" (the beam may be two), never the other way.
STAFF_LINE_THICKNESS_SPACES = 0.25


#: 2.318 r5: a vertical piece shorter than a stem (`SHORT_STEM_SPACES`) that stands within this many staff spaces of the head's own extent is the head's
#: outline (a Litolff head cut in pieces), not a stem: Litolff p2 0/0/9/0/0, a 1.9 sp piece 0.2 sp past the head's foot beside the head's real 4.9 sp stem.
HEAD_OUTLINE_SLACK_SPACES = 0.7


def _outline_slack(s: "StrokeView") -> float:
    return HEAD_OUTLINE_SLACK_SPACES if s.length < SHORT_STEM_SPACES else STEM_MATCH_X_SLACK_SPACES


def _head_ink_ordinals(strokes: Sequence[StrokeView], head_box: Sequence[float]) -> set:
    """Strokes that are THIS head's ink: not a stem-length vertical, with their centre inside the head's box (the box says where to look; the
    ink is what the stem must touch)."""
    hx, hy, hw, hh = head_box[:4]
    out = set()
    for s in strokes:
        if s.kind == "vertical" and s.length <= ONE_STEM_MAX_SPACES:
            sp = s.space_px if s.space_px > 0 else 1.0
            # a vertical piece wholly inside the head's own extent is the head's outline (a stem leaves the head); it is the head's ink
            osl = _outline_slack(s)
            if (s.box[1] >= hy - osl * sp and s.box[1] + s.box[3] <= hy + hh + osl * sp
                    and hx <= s.box[0] + s.box[2] / 2.0 <= hx + hw):
                out.add(s.ordinal)
            continue
        cx, cy = s.box[0] + s.box[2] / 2.0, s.box[1] + s.box[3] / 2.0
        # the head's own ink; or ink that holds the head (a Litolff head merged into a beam: the stroke is the head's ink and the beam's at once)
        if (hx <= cx <= hx + hw and hy <= cy <= hy + hh) or _covers_head(s, head_box):
            out.add(s.ordinal)
    return out


#: How many strokes of the head's own ink (a head the scan or the claim order cut in pieces, a stem's fused foot) the contact may pass through on its
#: way from the head to its stem. Structural: the head, its fused foot, the stem (Litolff p6 0/2/10: head, foot, then the stem's own stroke).
ONE_STEM_REACH_HOPS = 2


def _head_reach(strokes: Sequence[StrokeView], head_box: Sequence[float]) -> set:
    """The ink the head's own ink runs into: the head's strokes (`_head_ink_ordinals`) and, through the stroke map's contact (`touches`: ink within
    2 px), the blobs and claimed strokes touching them, up to `ONE_STEM_REACH_HOPS`. A stem-length vertical is where the road ends, never part of
    it; a beam, a slur, a hairpin (horizontal / curve) is not the head's ink."""
    by = {s.ordinal: s for s in strokes}
    reach = set(_head_ink_ordinals(strokes, head_box))
    frontier = set(reach)
    for _ in range(ONE_STEM_REACH_HOPS):
        nxt = set()
        for o in frontier:
            for j, _c in by[o].touches:
                t = by.get(j)
                if t is None or j in reach or t.kind not in ("blob", "owned", "contested"):
                    continue
                nxt.add(j)
        reach |= nxt
        frontier = nxt
    return reach


def _far_end(v: StrokeView, side: str) -> Tuple[float, float]:
    """(x, y) of the stem's far end for a stem running `side` ("up": the top). A wide (head-fused) stroke's x is that of its far end."""
    bx, by, bw, bh = v.box
    y = by if side == "up" else by + bh
    sp = v.space_px if v.space_px > 0 else 1.0
    if len(v.ends) >= 4 and bw > ONE_FUSED_MIN_WIDTH_SPACES * sp:
        x0, y0, x1, y1 = v.ends[:4]
        return (x0 if (y0 <= y1) == (side == "up") else x1), y
    return bx + bw / 2.0, y


#: 2.318 r4: a stem runs on past a chord's other head: the piece below the head and the piece above it are one stem though the head's ink lies between
#: them (the gap is a head high, not a crossing's hair). A stem that stops at another head and counts a tip there reads the chord's inner end.
CHAIN_THROUGH_HEAD = True
CHAIN_THROUGH_HEAD_MAX_GAP_SPACES = 2.0


def _head_ink_between(strokes: Sequence[StrokeView], x: float, y0: float, y1: float, sp: float) -> bool:
    """A stroke another mark has claimed as a HEAD (or an unclaimed blob) holds the column `x` (within the collinear slack) across at least half of the
    vertical gap between `y0` and `y1`."""
    lo, hi = min(y0, y1), max(y0, y1)
    if hi - lo <= 0:
        return False
    for s in strokes:
        if s.kind == "vertical" or not (s.kind == "blob" or s.family == "head"):
            continue
        if not (s.box[0] - ONE_STEM_COLLINEAR_X_SPACES * sp <= x <= s.box[0] + s.box[2] + ONE_STEM_COLLINEAR_X_SPACES * sp):
            continue
        cover = min(hi, s.box[1] + s.box[3]) - max(lo, s.box[1])
        if cover >= 0.5 * (hi - lo):
            return True
    return False


HEAD_BODY_IS_NOT_A_STEM = True
#: 2.318 r6: the chain's long step through a chord's head (r4) is never taken past the stem's BEAM: where the piece's far end stands in the band
#: of a beam-thick flat stroke its ink touches, only a hair's cut is followed (r3). Round 5 chained a beamed stem through a clot of ink below its beam to a
#: sliver at the cell's edge and read the sliver's bare end (Litolff p4 1/2/14: two beamed eighths written quarters).
CHAIN_STOPS_AT_A_BEAM = True


def _ends_at_a_beam(strokes: Sequence[StrokeView], v: StrokeView, end_y: float) -> bool:
    sp = v.space_px if v.space_px > 0 else 1.0
    touching = {j for j, _c in v.touches}
    for s in strokes:
        # one beam's thickness: a thicker slab across the stems may be a chord's row of heads run together, which a stem does pass (Litolff p9 0/0/1)
        if (s.ordinal in touching and s.kind == "horizontal" and BEAM_MIN_THICKNESS_SP <= s.thickness <= BEAM_ONE_MAX_THICKNESS_SPACES
                and s.length >= BEAM_SHAPE_MIN_LENGTH_SPACES
                and s.box[1] - 0.3 * sp <= end_y <= s.box[1] + s.box[3] + 0.3 * sp):
            return True
    return False


#: 2.319: A LETTER CLAIMS ITS OWN INK, NOT THE STEM ITS BOX COVERS (Sean 2026-11-18: "We use the boxes to identify something, but then claim only the
#: ink"). Litolff prints `ff` hard under a beamed group; the staff erase cut a stem at the bottom line and the letter's box covered the stem's lower piece,
#: so the claim filed that piece as the `ff`'s and the stem stopped short of its beam (Litolff p16 1/7/2, the first of three beamed eighth chords, written a
#: quarter). An upright piece in line with the stem, whose far end runs into a beam and whose ink touches NO ink of the letter that claimed it, is the
#: stem's piece: the chain follows it (a crossing's cut only). Structural, no number. Never a piece that touches the letter's own ink, never one that does not
#: reach a beam, never a piece another kind of mark claimed. The claim itself is left as it is (the stroke owner's business): the stem is READ through it.
STEM_PIECE_A_LETTER_TOOK = True


def _stem_piece_a_letter_took(strokes: Sequence[StrokeView], w: StrokeView, side: str) -> bool:
    if not STEM_PIECE_A_LETTER_TOOK or w.kind not in ("owned", "contested") or w.family not in FUSABLE_FAMILIES:
        return False
    if w.box[3] < 3.0 * w.box[2]:
        return False                    # upright: a stem's piece is several times taller than wide
    by_o = {s.ordinal: s for s in strokes}
    if any((by_o.get(j) is not None and by_o[j].family == w.family) for j, _c in w.touches):
        return False                    # its ink is joined to the letter's: the letter's own ink
    return _ends_at_a_beam(strokes, w, _far_end(w, side)[1])


def _chain(strokes: Sequence[StrokeView], first: StrokeView, side: str) -> StrokeView:
    """Follow the stem to its far end across a crossing that cut it: the next vertical piece in the same x-column, starting where this one ends
    or within `ONE_STEM_BREAK_MAX_GAP_SPACES` of it. One piece: the stroke itself. Several: one stem stroke (union box, union of what touches it)."""
    import dataclasses
    members = [first]
    sp = first.space_px if first.space_px > 0 else 1.0
    while True:
        cur_x, cur_y = _far_end(members[-1], side)
        best = None
        # 2.318 r6: a stem ends at its beam. A hair's cut by the beam itself is still followed (r3); the long step "through a head" (r4) is not taken
        # from a piece that ends in a beam's band: what stands in line beyond is another note's (Litolff p4 1/2/14)
        at_beam = CHAIN_STOPS_AT_A_BEAM and _ends_at_a_beam(strokes, members[-1], cur_y)
        for w in strokes:
            if (w.kind != "vertical" and not _stem_piece_a_letter_took(strokes, w, side)) or w.length > STEM_MAX_SPACES \
                    or any(w.ordinal == m.ordinal for m in members):
                continue
            wx, wy = _far_end(w, side)
            if w.kind != "vertical":
                # a piece a letter's box took is followed only across a crossing's cut, never the long step through a head
                near_ = w.box[1] + w.box[3] if side == "up" else w.box[1]
                if ((cur_y - near_) if side == "up" else (near_ - cur_y)) > ONE_STEM_BREAK_MAX_GAP_SPACES * sp:
                    continue
            if abs(wx - cur_x) > ONE_STEM_COLLINEAR_X_SPACES * sp:
                continue
            near = w.box[1] + w.box[3] if side == "up" else w.box[1]          # the piece's end toward the stem
            gap = (cur_y - near) if side == "up" else (near - cur_y)
            if gap > ONE_STEM_BREAK_MAX_GAP_SPACES * sp and not (CHAIN_THROUGH_HEAD and not at_beam and gap <= CHAIN_THROUGH_HEAD_MAX_GAP_SPACES * sp
                                                                  and _head_ink_between(strokes, cur_x, cur_y, near, sp)):
                continue
            if (wy < cur_y) if side == "up" else (wy > cur_y):                  # it reaches farther than the chain does
                if best is None or ((wy < best[1]) if side == "up" else (wy > best[1])):
                    best = (w, wy)
        if best is None:
            break
        members.append(best[0])
    if len(members) == 1:
        return first
    x0 = min(m.box[0] for m in members)
    y0 = min(m.box[1] for m in members)
    x1 = max(m.box[0] + m.box[2] for m in members)
    y1 = max(m.box[1] + m.box[3] for m in members)
    far = members[-1]
    touches: Dict[int, float] = {}
    for m in members:
        for j, c in m.touches:
            if not any(j == o.ordinal for o in members):
                touches[j] = max(touches.get(j, 0.0), c)
    read_as_stem = {"kind": "vertical", "family": ""} if far.kind != "vertical" and far.family in FUSABLE_FAMILIES else {}
    return dataclasses.replace(far, box=(x0, y0, x1 - x0, y1 - y0), length=(y1 - y0) / sp, touches=tuple(sorted(touches.items())),
                               ends=(), profile=(), **read_as_stem)


#: A stem a scan has parted from its head by a hair of paper (Breitkopf SHATTERS) is still the head's stem: the vertical stands within this many staff
#: spaces of the head's ink, beside it, level with it. The number is `stem_strokes.BRIDGE_MAX_GAP_SPACES` (2.161: the gap measured 0.13-0.27 sp on one
#: plate, plus 0.08), so it NARROWS ONLY until another publisher confirms it (CLAUDE section 4).
ONE_STEM_BRIDGE_MAX_GAP_SPACES = 0.35
BRIDGE = True
#: 2.318 r4: where the direction verdict puts no stem on the ink, the stem that runs the other way by at least this many staff spaces past the head is the
#: head's stem. MEASURED AND REFUSED (off): on the tile pages it moved 15 heads that read one beam like today to "cannot tell" and gave 7 heads that
#: today write no beam a beam, 13 more it read from the other end; a verdict and the ink disagreeing is two readers disagreeing, not an answer (rule 8).
INK_SIDE = False
INK_SIDE_MIN_SPACES = 1.0
#: 2.318 r4: where two stems stand on a head's engraving side, the one whose ink touches the head's ink is its stem.
DIRECT_CONTACT_STEM = True
SHORT_STEM_SPACES = 2.5
#: 2.318 r5: with no direction verdict, a vertical that runs past the head both ways has no tip for THIS head on the ink: silent, not the farther end.
BOTH_WAYS_BOTH = True


#: 2.318 r6: THE FREE END IS THE TIP (a vertical that passes a head both ways, no direction verdict). A stem is attached at its head's side and leaves it
#: toward one end; the other end only just passes the head. MEASURED on the tile pages (20261117-night, every vertical touching a head's ink and passing
#: its box both ways): the SHORTER overshoot is 0.0-0.67 sp for 125 strokes (Litolff 113, Brahms 12: a stem's foot) and 0.9 sp or more for 32 (a chord's
#: stem running on to its next head: a third is a full space away); nothing between 0.67 and 0.9. Real controls: Sean's rhythm-leftovers-2 tile 10
#: (Litolff p2 0/3/1/2, an eighth: a neighbour's stem passing 0.22 sp below the head made "several stems") and Litolff p2 0/5/1/2 (a chord's stem whose
#: far end is the lower head). Never: an end that is the only one, or two ends that both run free, is not chosen by this.
FREE_END_IS_THE_TIP = True
FOOT_MAX_PAST_HEAD_SPACES = 0.75
#: Another head's ink "sits at" a stem's end where it touches the stroke and its extent holds the end, within this (a head is ~1.2 sp tall).
HEAD_AT_END_SLACK_SPACES = 0.3


def _head_ink_at_end(strokes: Sequence[StrokeView], v: StrokeView, side: str, own_ink: set) -> bool:
    """Ink of ANOTHER notehead (a stroke a head has claimed, not this head's own) touches the vertical `v` and holds its `side` end."""
    sp = v.space_px if v.space_px > 0 else 1.0
    y = v.box[1] if side == "up" else v.box[1] + v.box[3]
    touching = {j for j, _c in v.touches}
    for s in strokes:
        if s.ordinal not in touching or s.ordinal in own_ink or s.family != "head":
            continue
        if s.box[1] - HEAD_AT_END_SLACK_SPACES * sp <= y <= s.box[1] + s.box[3] + HEAD_AT_END_SLACK_SPACES * sp:
            return True
    return False


#: 2.318 r6: the same hair of paper END-ON: the stem stands over the head's own ink column and stops just short of it (Brahms p17 0/3/2, 0/3/3: a down
#: stem 0.13 sp below its head). MEASURED on the tile pages, heads with no stem in the map and a stem-length vertical end-on in their column: the paper
#: between is 0.01-0.24 sp for 9 (Brahms five at 0.13, the gap 2.161 measured side-on), 0.37 for one whose stem the map cut at the head's own ledger
#: line, then 0.62, 0.62, 1.15. `ONE_STEM_BRIDGE_MAX_GAP_SPACES` (0.35) is the cut; where the stem's ink touches a ledger line's ink (the rung that
#: cut it: `ONE_STEM_BREAK_MAX_GAP_SPACES`, 0.6, the stem-cut-by-a-crossing number) the cut is that. Never across more paper, never off the column.
END_ON_BRIDGE = True
#: ...and only a stroke long enough to be the free part of a stem: the nine bridged stems are 2.4-4.6 sp long; a 1.6 sp upright over a head between
#: ledger lines was the next chord note's own body (Litolff p15 0/0/5: it made "several stems" of a note written today).
END_ON_MIN_LENGTH_SPACES = 2.0


def _bridged(v: StrokeView, ink_boxes: Sequence[Sequence[float]], head_h: float, cut_by_ledger: bool = False) -> bool:
    sp = v.space_px if v.space_px > 0 else 1.0
    if END_ON_BRIDGE and v.length >= END_ON_MIN_LENGTH_SPACES:
        cx = v.box[0] + v.box[2] / 2.0
        limit = (ONE_STEM_BREAK_MAX_GAP_SPACES if cut_by_ledger else ONE_STEM_BRIDGE_MAX_GAP_SPACES) * sp
        for b in ink_boxes:
            if b[0] <= cx <= b[0] + b[2]:
                gap = max(b[1] - (v.box[1] + v.box[3]), v.box[1] - (b[1] + b[3]))
                if 0.0 <= gap <= limit:
                    return True
    for b in ink_boxes:
        dy = min(v.box[1] + v.box[3], b[1] + b[3]) - max(v.box[1], b[1])
        if dy < 0.4 * min(head_h, b[3]):                       # level with the head's ink (the same share `stem_strokes` asks)
            continue
        gap = max(0.0, max(v.box[0], b[0]) - min(v.box[0] + v.box[2], b[0] + b[2]))
        if gap <= ONE_STEM_BRIDGE_MAX_GAP_SPACES * sp:
            return True
    return False


#: 2.318 r6: THE LAST NOTE BEFORE A BARLINE. Litolff sets the last note of a beamed group so close to the barline that its stem and the barline are one
#: ink; the barline claims first (CLAUDE section 3), so the map files the stem as the barline's and the head had "no stem" (Litolff p2 1/9/7, p3 0/8/0,
#: p6 1/8/8, 1/9/8: beamed eighths that lost their value). A later reader may READ claimed ink, never take it: an upright stroke of a stem's length that
#: a barline has claimed is read as the head's stem where a beam-thick flat stroke touches it -- a barline carries no beam, a stem does. Structural.
#: Never without the beam: a barline's own piece beside a head is not a stem, and the head stays "no stem in the map".
STEM_IN_A_BARLINE = True
#: ...and THE FIRST NOTE AFTER A CLEF, the same way: the clef claims first and took the stem of the note set hard against it (Litolff p15 1/3/18: the
#: first of a beamed row of chords had "no stem", and a box beside it lent it a quarter). The same rule, the same never: only with the beam's witness.
STEM_CLAIMING_FAMILIES = ("barline", "clef")


def _stem_in_a_barline(strokes: Sequence[StrokeView], v: StrokeView) -> bool:
    if not STEM_IN_A_BARLINE or v.kind not in ("owned", "contested") or v.family not in STEM_CLAIMING_FAMILIES or v.length < SHORT_STEM_SPACES:
        return False
    if v.box[3] < 4.0 * v.box[2]:
        return False                    # upright: at least four times as tall as wide
    touching = {j for j, _c in v.touches}
    return any(s.ordinal in touching and s.kind == "horizontal" and s.thickness >= BEAM_MIN_THICKNESS_SP and s.length >= BEAM_SHAPE_MIN_LENGTH_SPACES
               for s in strokes)


def stems_by_ink(strokes: Sequence[StrokeView], head_box: Sequence[float], side: Optional[str] = None) -> Dict[str, object]:
    """The stem(s) of the head at `head_box` (x, y, w, h, canonical px), found by INK: a stem-length vertical stroke that is the head's own ink
    (a Litolff head fused to its stem: the stroke holds the head) or touches a stroke that is (a Breitkopf head and stem apart), whose FAR end lies
    beyond the head's box and whose axis stands beside the head, followed across a crossing to its far end. `side` ("up" / "down") is the stem
    direction the pipeline decided from the whole stem group (`Q.STEM_DIRECTION`; a chord's inner head has a stem both ways, so only that
    verdict says which end is the tip); None where it has none, then the end farther from the head's centre is the tip.

    Returns `{"stems": [(stroke, side)], "why": str}`: one stem; or two, one each way (a unison of two voices); or none, `why` says why
    (`no_vertical_touches_the_head`, `several_stems`). Nothing is invented: a stroke that does not touch the head's ink is never its stem."""
    hx, hy, hw, hh = (float(v) for v in head_box[:4])
    hcx, hcy = hx + hw / 2.0, hy + hh / 2.0
    ink = _head_reach(strokes, head_box)
    ink_boxes = [s.box for s in strokes if s.ordinal in ink]
    ledger_ords = {s.ordinal for s in strokes if s.family == "ledger"}
    found: Dict[str, List[StrokeView]] = {"up": [], "down": []}
    for v in strokes:
        if v.length > ONE_STEM_MAX_SPACES or not (v.kind == "vertical" or _stem_in_a_barline(strokes, v)):
            continue
        if v.length > STEM_MAX_SPACES and not any(j in ink for j, _c in v.touches):
            continue                    # past a stem's usual length only the ink's own contact with the head makes it one (never a bridge)
        sp = v.space_px if v.space_px > 0 else 1.0
        osl = _outline_slack(v)
        # 2.318 r6: ...and a SHORT upright that holds the head is the head's own body, filed upright (Litolff p16 0/0/8, p9 0/0/3: a 1.6 sp stroke 0.7
        # thick), never the head fused to its stem -- that stroke is as long as a stem. Round 5 took the body for a stem and read "no beam" at its end.
        if v.box[1] >= hy - osl * sp and v.box[1] + v.box[3] <= hy + hh + osl * sp and (
                not _covers_head(v, head_box) or (HEAD_BODY_IS_NOT_A_STEM and v.length < SHORT_STEM_SPACES)):
            continue                    # a vertical piece wholly inside the head's own extent is the head's outline, not a stem that leaves it
        if not (_covers_head(v, head_box) or any(j in ink for j, _c in v.touches)
                or (BRIDGE and _bridged(v, ink_boxes, hh, cut_by_ledger=any(j in ledger_ords for j, _c in v.touches)))):
            continue
        dirs = [side] if side in ("up", "down") else ["up", "down"]
        ok = []
        for sd in dirs:
            x, y = _far_end(v, sd)
            if (y < hy - STEM_PAST_HEAD_MIN_SPACES * sp) if sd == "up" else (y > hy + hh + STEM_PAST_HEAD_MIN_SPACES * sp):
                if abs(x - hcx) <= hw / 2.0 + STEM_HEAD_X_SLACK_SPACES * sp:
                    ok.append((sd, abs(y - hcy)))
        if not ok and side in ("up", "down") and INK_SIDE:
            # The direction verdict is contradicted by the ink: the stem reaches a full staff space past the head on the OTHER side and not at all on
            # this one (Litolff p2 0/0/7/1/9: a stem that runs UP from a head the verdict calls "down"). The ink says where the stem ends.
            other = "down" if side == "up" else "up"
            x, y = _far_end(v, other)
            if ((y < hy - INK_SIDE_MIN_SPACES * sp) if other == "up" else (y > hy + hh + INK_SIDE_MIN_SPACES * sp)) \
                    and abs(x - hcx) <= hw / 2.0 + STEM_HEAD_X_SLACK_SPACES * sp:
                ok.append((other, abs(y - hcy)))
        # BOTH_WAYS_BOTH: with no direction verdict and a stroke that runs past the head BOTH ways (a chord's stem through its inner head, or a stem that
        # serves a neighbour's head too: Litolff p2 0/0/5/1/2, where the farther end is the neighbour's), which end is THIS head's tip is not on the ink:
        # both ends are read (two stems, one each way) and the head's count is the lower to the higher -- read where they agree, marked where they differ.
        if len(ok) == 2 and FREE_END_IS_THE_TIP:
            # 2.318 r6. A stem leaves its head toward ONE free end. Of a vertical that passes the head both ways:
            #  (a) the end that barely passes the head is where the stem is ATTACHED (its foot), never a tip (`FOOT_MAX_PAST_HEAD_SPACES`);
            #  (b) the end where ANOTHER notehead's ink sits on the stroke is that head's place on a chord's stem, never a tip.
            # One end left: that is the tip. Both or neither: not told apart here, both are read as before.
            past = {"up": (hy - v.box[1]) / sp, "down": (v.box[1] + v.box[3] - (hy + hh)) / sp}
            free = [t for t in ok if past[t[0]] >= FOOT_MAX_PAST_HEAD_SPACES]
            if len(free) == 1:
                ok = free
            else:
                free = [t for t in ok if not _head_ink_at_end(strokes, v, t[0], ink)]
                if len(free) == 1:
                    ok = free
        if len(ok) == 2 and not BOTH_WAYS_BOTH:
            ok = [max(ok, key=lambda t: t[1])] if ok[0][1] != ok[1][1] else []      # the farther end is the tip (the old rule)
        for sd, _d in ok:
            found[sd].append(v)
    stems: List[Tuple[StrokeView, str]] = []
    for sd in ("up", "down"):
        pieces = found[sd]
        if len(pieces) > 1:
            # pieces of ONE stem (cut by a crossing) are chained to the same far end; two stems on one side are not one stem
            chained = {_chain(strokes, p, sd).ordinal for p in pieces}
            if len(chained) > 1:
                # two stems running one way at one head: the head's own stem is the one on its engraving side (CLAUDE section 5: up -> right,
                # down -> left); the other is its neighbour's. Neither or both on that side: not told apart (rule 8).
                own = [p for p in pieces if ((_far_end(p, sd)[0] >= hcx) if sd == "up" else (_far_end(p, sd)[0] <= hcx))]
                if len({_chain(strokes, p, sd).ordinal for p in own}) != 1 and DIRECT_CONTACT_STEM:
                    # a stem is at least `SHORT_STEM_SPACES` long (a piece shorter than that, standing in the head's own outline, is not one: Litolff p2
                    # 0/0/9/0/0, where a 1.9 sp piece of the head beside the real 4.9 sp stem was taken): where a longer one stands on that side, it is the stem
                    longer = [p for p in own if _chain(strokes, p, sd).length >= SHORT_STEM_SPACES]
                    if longer and len(longer) < len(own):
                        own = longer
                    # still two on that side: the head's stem is the one whose ink TOUCHES the head's own ink; one only bridged across a hair of paper
                    # is its neighbour's (a stem joins the head whose ink it touches, Sean 2026-11-18)
                    direct = [p for p in own if _covers_head(p, head_box) or any(j in ink for j, _c in p.touches)]
                    if direct:
                        own = direct
                if len({_chain(strokes, p, sd).ordinal for p in own}) != 1:
                    return {"stems": [], "why": "several_stems", "side": sd}
                pieces = own
        if pieces:
            nearest = min(pieces, key=lambda p: abs(_far_end(p, sd)[1] - hcy))      # the piece the head stands on; the chain takes it to the tip
            stems.append((_chain(strokes, nearest, sd), sd))
    if not stems:
        return {"stems": [], "why": "no_vertical_touches_the_head"}
    return {"stems": stems, "why": ""}


def _centre_step(s: StrokeView, x: float) -> Optional[float]:
    """The stroke's centre line, in half-spaces from the staff's top line, at page-x `x` (linear between the two filed ends); None if not filed."""
    if len(s.end_steps) < 2 or len(s.ends) < 4:
        return None
    x0, _y0, x1, _y1 = s.ends[:4]
    a, b = s.end_steps[:2]
    if x1 == x0:
        return (a + b) / 2.0
    t = min(max((x - x0) / (x1 - x0), 0.0), 1.0)
    return a + (b - a) * t


def thickness_less_line(s: StrokeView, x: float) -> Tuple[float, float]:
    """`(here, corrected)`: the stroke's thickness at `x` (`local_thickness`) and the same with the staff line's own thickness taken out for
    every staff line the beam's band covers at `x` (a line is at an even half-space step; the map restored the erased line's ink INTO a beam
    that lies on it, so a single beam on a line reads a line's thickness too thick). Without the stroke's steps filed, nothing is taken out."""
    here = local_thickness(s, x)
    c = _centre_step(s, x)
    if c is None:
        return here, here
    lt = STAFF_LINE_THICKNESS_SPACES
    out = 0.0
    for line in (0, 2, 4, 6, 8, -2, 10, -4, 12):
        if abs(c - line) <= here + lt:             # half-spaces: the band's half is `here` spaces = `here` x 2 / 2 steps; the line's half `lt`
            out += lt
    return here, max(here - out, 0.0)


#: Families of mark whose ink may have a beam fused to it: a dynamic or a word (Litolff p13 8/2: a beam on a staff line fused with an `ff`, Sean's tile
#: L11). A page-wide mark claims its ink first and a later reader may mark it but never take it (CLAUDE section 3), so where the stem's end meets such
#: ink the map cannot say "no beam", whatever shape the ink has.
FUSABLE_FAMILIES = ("dynamic", "text", "word")
#: A beam-shaped stroke: flat, as thick as a beam (`BEAM_DOUBT_MIN_THICKNESS_SP` up to what one beam is: `BEAM_ONE_MAX_THICKNESS_SPACES`) and long enough
#: to span two stems. A notehead's ink is thicker (0.85 and up) and shorter, a staff line's remnant thinner.
BEAM_ONE_MAX_THICKNESS_SPACES = 0.8
BEAM_SHAPE_MIN_LENGTH_SPACES = 2.0
BEAM_SHAPE_MAX_ANGLE = 25.0
#: Families whose claim is never a reason: a tremolo slash and a barline are marks the stem carries or stands against; a stem is never "unfinished" at them.
NO_BEAM_HIDING_FAMILIES = ("tremolo", "barline")


#: 2.318 r4: how far inward of the stem's tip a thin line's outer edge may lie and still be where the first beam level would start. A beam's first level
#: lies at the tip (`STACK_FIRST_SPACES` is the stacking rule's own allowance for a sloped beam's box); a line whose edge starts farther in is not the
#: stem's beam, so it cannot hide one.
THIN_LINE_FIRST_LEVEL_SPACES = 0.6


def thin_line_at_tip(strokes: Sequence[StrokeView], role_by_ord: Dict[int, Dict[str, object]], stem: StrokeView, side: str,
                     head_box: Optional[Sequence[float]]) -> List[int]:
    """Ordinals of unclaimed FLAT lines, long enough to span two stems, that the stem's ink touches AT its tip (outer edge from `TIP_OUTWARD_SPACES` beyond
    the tip to `THIN_LINE_FIRST_LEVEL_SPACES` inward) and that are thinner than a beam by the map (`span_thin`: a slur, hairpin or tie line across stems is
    this thin, and so is a beam the scan or the erasure has thinned: Litolff p6 0/0/8/2, a beam 0.38 thick over three stems). Where the tip counts no beam,
    a line like this where a beam's first level would start is why the map cannot say there is none (rule 8). Never over blank paper."""
    sp = stem.space_px if stem.space_px > 0 else 1.0
    bx, by, bw, bh = stem.box
    tip_y = by if side == "up" else by + bh
    touching = {j for j, _c in stem.touches}
    out = []
    for s in strokes:
        if s.ordinal not in touching or s.kind != "horizontal" or role_by_ord.get(s.ordinal, {}).get("role") != "span_thin":
            continue
        if head_box is not None and _covers_head(s, head_box):
            continue
        if s.length < BEAM_SHAPE_MIN_LENGTH_SPACES or abs(s.angle) > BEAM_SHAPE_MAX_ANGLE:
            continue
        outer = s.box[1] if side == "up" else s.box[1] + s.box[3]
        inward = ((outer - tip_y) if side == "up" else (tip_y - outer)) / sp
        if -TIP_OUTWARD_SPACES <= inward <= THIN_LINE_FIRST_LEVEL_SPACES:
            out.append(s.ordinal)
    return sorted(out)


CLAIMED_INK_RUNS_ON = True


def claimed_ink_at_tip(strokes: Sequence[StrokeView], stem: StrokeView, side: str) -> List[int]:
    """Ordinals of strokes ANOTHER mark has claimed that the stem's own INK touches at its end (the first-level zone of its tip: from `TIP_OUTWARD_SPACES`
    beyond to `STACK_FIRST_SPACES` inward) and that a beam could be hiding in: at least a beam's thickness (never ink thinner than the trough, `BEAM_DOUBT_MIN_THICKNESS_SP`: a hairpin is thinner than a beam, Sean 2026-10-09), and either a dynamic's or a word's ink (a beam fused to an `ff`) or ink SHAPED like
    a beam (a beam under a head box or an accidental's or a hairpin's claim: Litolff p2 13/1, the beam of a stem claimed as a head). A claim is a measurement
    of who owns ink, not of its shape, so it does not hide a beam. Never over blank paper: with no such ink touching the end, nothing here."""
    sp = stem.space_px if stem.space_px > 0 else 1.0
    bx, by, bw, bh = stem.box
    tip_y = by if side == "up" else by + bh
    lo, hi = ((tip_y - TIP_OUTWARD_SPACES * sp, tip_y + STACK_FIRST_SPACES * sp) if side == "up"
              else (tip_y - STACK_FIRST_SPACES * sp, tip_y + TIP_OUTWARD_SPACES * sp))
    out = []
    touching = {j for j, _c in stem.touches}
    for s in strokes:
        if s.ordinal == stem.ordinal or s.kind not in ("owned", "contested") or s.family in NO_BEAM_HIDING_FAMILIES:
            continue
        if s.ordinal not in touching:                  # joined by INK: the stem's own ink meets it, never a box edge or a gap
            continue
        if s.box[1] + s.box[3] < lo or s.box[1] > hi:
            continue
        if s.thickness < BEAM_DOUBT_MIN_THICKNESS_SP:
            # 2.318 r6: the letter's claim may have cut the fused beam in pieces: a thin piece at the stem that runs straight on, in the same band, into
            # a beam-thick piece of the SAME mark is that mark's ink at the tip all the same (Litolff p8 1/1/0: a beam under three notes fused with
            # an `ff`; the piece at the first stem is 0.43 thick, the next 0.98 -- three beamed eighths were written quarters).
            if not (CLAIMED_INK_RUNS_ON and s.family in FUSABLE_FAMILIES and any(
                    t.ordinal != stem.ordinal and t.kind in ("owned", "contested") and t.family == s.family
                    and t.thickness >= BEAM_DOUBT_MIN_THICKNESS_SP and not (t.box[1] + t.box[3] < lo or t.box[1] > hi)
                    and t.ordinal in {j for j, _c in s.touches} for t in strokes)):
                continue
        shaped = (s.thickness <= BEAM_ONE_MAX_THICKNESS_SPACES and s.length >= BEAM_SHAPE_MIN_LENGTH_SPACES and abs(s.angle) <= BEAM_SHAPE_MAX_ANGLE)
        if s.family in FUSABLE_FAMILIES or shaped:
            out.append(s.ordinal)
    return sorted(out)


def beam_over_the_column(strokes: Sequence[StrokeView], role_by_ord: Dict[int, Dict[str, object]], head_box: Sequence[float]) -> List[int]:
    """Beam-shaped strokes (a beam, a stub, a trough stroke) that run over the head's own column within a stem's reach of it: where a head has no
    stem at all, these are why the map still cannot say "no beam" (a beam with no stem under it is a stem the scan lost)."""
    hx, hy, hw, hh = head_box[:4]
    hcx = hx + hw / 2.0
    out = []
    for s in strokes:
        if role_by_ord.get(s.ordinal, {}).get("role") not in ("beam", "beam_stub", "beam_doubt") or s.kind != "horizontal":
            continue
        sp = s.space_px if s.space_px > 0 else 1.0
        if s.box[0] <= hcx <= s.box[0] + s.box[2] and (s.box[1] <= hy + hh + STEM_MAX_SPACES * sp and s.box[1] + s.box[3] >= hy - STEM_MAX_SPACES * sp):
            out.append(s.ordinal)
    return sorted(out)


#: 2.318 r4: how much thicker (staff spaces) this stem's stretch of a beam is than the thin part of the same beam (the lower quartile of its profile)
#: before a second beam fused to it cannot be ruled out. Measured on every one-beam note of the tile pages (1,818 notes, both plates): 0.10 or less for
#: 1,462 of them, the tail starts at 0.15; Sean's B09 reads 0.17, his one-beam notes 0.03 or less except two heads fused to the beam. Narrows only.
STEP_AT_STEM_SPACES = 0.15
#: OFF: MEASURED AND REFUSED (2.318 r4): it marks Sean's B09 but also 45 more Litolff and 16 more Brahms notes on the tile pages that carry one beam today
#: (five Brahms crops looked at: four are one thick beam, one a real second beam; agent's look). Kept so the measure can be re-run.
STEP_NARROW = False


def thin_part(s: StrokeView) -> float:
    """The stroke's thin part, staff spaces: the lower quartile of its thickness profile."""
    p = sorted(s.profile)
    return p[len(p) // 4] / 16.0


THIN_LINE_TIP = True


#: 2.318 r4: a stem whose far end is cut by the cell crop (`Q.STROKE` `cut`) has its tip out of sight. MEASURED AND REFUSED (off): no judged note needs it
#: and it marks 21 Litolff and 2 Brahms notes on the tile pages that carry a value today. Kept so the measure can be re-run.
CUT_TIP = False


STUB_STACKS_ON_THE_BEAM = True
#: 2.318 r6: how far ALONG the beam (staff spaces) the nearest double-thick stretch may lie from a stem and still leave "one beam or two" open at that
#: stem. MEASURED on the tile pages, every stem under a stroke that is double over part of its run (Brahms p17, p4: a group whose second beam covers
#: only some notes; the profile has 12 samples, 0.6-1.1 sp apart): the nearest thick sample is 0.05-0.97 sp away for 40 stems -- Sean's four judged
#: sixteenths B01, B04, B06, B10 at 0.50, 0.27, 0.22, 0.45 -- and 3.0-5.8 sp away for 14 (the notes under the single part; 8 of them written eighths
#: today and marked by round 5); nothing between 0.97 and 3.0. The cut stands in the gap, two samples of the coarsest profile from the near side.
THICK_REACH_SPACES = 2.0


def _thick_stretch_distance(s: StrokeView, x: float) -> Optional[float]:
    """Staff spaces along the stroke from page-x `x` to its nearest profile sample as thick as a double beam; None where no sample is (or no
    profile was filed: then nothing is known about where the thick part lies)."""
    n = len(s.profile)
    sp = s.space_px if s.space_px > 0 else 1.0
    if n < 3 or s.box[2] <= 0:
        return None
    best = None
    for i, p in enumerate(s.profile):
        if p / 16.0 >= FUSED_LOCAL_MIN_SPACES:
            d = abs(s.box[0] + s.box[2] * i / (n - 1) - x) / sp
            best = d if best is None or d < best else best
    return best


#: 2.318 r6: A MARK AT A BARE TIP THAT MAY BE A FLAG OR A BROKEN BEAM (rule 8). Round 5 read "no beam" and wrote a plain quarter wherever the tip held only
#: a stroke the map could not call a hook or a beam. Two shapes are not "nothing": (a) a CURVED stroke hanging from the stem, too long for the hook cut
#: (`hook_or_stub`), that touches no letter's ink -- a flag drawn long (Litolff p13 0/1/8: two flagged notes written quarters); (b) a FLAT stroke as
#: thick as a beam whose band starts at the tip and that the map joins to no second stem -- a beam whose other stem is lost in a clot (Brahms p17
#: 0/11/2, 0/12/3: dotted eighths under a beam written dotted quarters). The note is MARKED between its head's value and one level; the flag reader
#: still speaks first. MEASURED on the tile pages: it marks 5 notes round 5 newly wrote plain (all 5 were marked with the flag OFF too) and none that is
#: written with the flag OFF. Never a stroke deeper than the first level (`STUB_FIRST_LEVEL_SPACES`: ledger lines 1.3-3.4 sp in from the tip, 21 notes
#: written quarters today), never one touching a barline (a staff-long remnant, Brahms p15 0/3/6) or -- the curve -- a dynamic's or word's ink.
MARK_AT_BARE_TIP = True
STUB_FIRST_LEVEL_SPACES = 0.6


def _may_be_flag_or_broken_beam(strokes: Sequence[StrokeView], s: StrokeView, tip_y: float, side: str) -> bool:
    sp = s.space_px if s.space_px > 0 else 1.0
    by_o = {t.ordinal: t for t in strokes}
    fams = {by_o[j].family for j, _c in s.touches if j in by_o and by_o[j].kind in ("owned", "contested")}
    if s.kind == "curve":
        return not (fams & set(FUSABLE_FAMILIES))
    if s.kind != "horizontal" or s.thickness < BEAM_MIN_THICKNESS_SP or abs(s.angle) > BEAM_SHAPE_MAX_ANGLE or "barline" in fams:
        return False
    cy = s.box[1] + s.box[3] / 2.0
    inward = ((cy - tip_y) if side == "up" else (tip_y - cy)) / sp
    return -TIP_OUTWARD_SPACES <= inward <= STUB_FIRST_LEVEL_SPACES


#: 2.318 r6: A STEM ENDS AT ITS BEAM. Litolff prints `ff` hard under a beamed group and the scan merges the stem with the letter's own upright, so the
#: map's vertical runs on past the beam and its "tip" is inside the letter, where no beam is (Litolff p13 1/1/8, p2 0/2/5: beamed eighths read "no
#: beam"). Where the stem's ink TOUCHES a beam beyond the head and, past that beam, touches ink a dynamic or a word has claimed, the stem ends at the
#: beam's outer face and the beams are counted from there. Structural, no number. Never where the ink past the stroke touches no letter: a stem that
#: runs on through a ledger line or a row of heads (Litolff p15 0/0/19, quarters above the staff) has not been shown to end there.
STEM_ENDS_AT_ITS_BEAM = True
#: 2.319: ...AND THE LETTER'S INK IS THE LETTER'S WHETHER OR NOT ITS CLAIM HELD. The claim refuses a letter's piece whose ink runs into a note
#: (`letter_ink_runs_into_a_note`) -- here the very stem that runs on into the `ff` -- so past the beam the stem touched only ink nobody claimed and the
#: rule above waited on a claim that never comes (Litolff p16 1/7/2: three beamed eighth chords over an `ff`, the middle one written a quarter). Ink
#: past the beam that runs straight into a dynamic's or a word's claimed ink is that letter's: one step of ink, never more. Never ink that touches no
#: letter (a ledger line, a row of heads past the beam).
LETTER_INK_ONE_STEP = True


def _letter_ink(s: StrokeView, by_o: Dict[int, StrokeView]) -> bool:
    """`s` is a dynamic's or a word's ink: claimed by one, or (2.319) unclaimed ink whose own ink touches a stroke one has claimed."""
    if s.kind in ("owned", "contested"):
        return s.family in FUSABLE_FAMILIES
    if not LETTER_INK_ONE_STEP:
        return False
    return any(t is not None and t.kind in ("owned", "contested") and t.family in FUSABLE_FAMILIES
               for t in (by_o.get(j) for j, _c in s.touches))


def _stem_cut_at_its_beam(strokes: Sequence[StrokeView], role_by_ord: Dict[int, Dict[str, object]], stem: StrokeView, side: str,
                          head_box: Sequence[float]) -> Optional[StrokeView]:
    """The stem shortened to the outer face of the outermost beam its ink touches beyond the head, where past that face it touches a dynamic's or
    a word's ink; None where it does not (module comment above)."""
    import dataclasses
    sp = stem.space_px if stem.space_px > 0 else 1.0
    hy, hh = float(head_box[1]), float(head_box[3])
    bx, by, bw, bh = stem.box
    by_o = {s.ordinal: s for s in strokes}
    touching = [by_o[j] for j, _c in stem.touches if j in by_o]
    best = None
    for s in touching:
        if s.kind != "horizontal" or role_by_ord.get(s.ordinal, {}).get("role") != "beam" or _covers_head(s, head_box):
            continue
        yc = _centre_y(s, stem)
        if yc is None:
            yc = s.box[1] + s.box[3] / 2.0
        if not ((yc < hy) if side == "up" else (yc > hy + hh)):
            continue
        face = (yc - s.thickness * sp / 2.0) if side == "up" else (yc + s.thickness * sp / 2.0)
        if best is None or ((face < best) if side == "up" else (face > best)):
            best = face
    if best is None:
        return None
    if not any(_letter_ink(s, by_o) and ((s.box[1] < best) if side == "up" else (s.box[1] + s.box[3] > best)) for s in touching):
        return None
    y0, y1 = (best, by + bh) if side == "up" else (by, best)
    if y1 - y0 <= 0:
        return None
    # what the ink touches wholly past the beam's face is the letter's side of the join, not the stem's
    keep = tuple((j, c) for j, c in stem.touches
                 if j in by_o and not ((by_o[j].box[1] + by_o[j].box[3] <= best) if side == "up" else (by_o[j].box[1] >= best)))
    return dataclasses.replace(stem, box=(bx, y0, bw, y1 - y0), length=(y1 - y0) / sp, touches=keep)


def beam_count(strokes: Sequence[StrokeView], role_by_ord: Dict[int, Dict[str, object]], head_box: Sequence[float], side: Optional[str],
               finder_stem: bool = True) -> Dict[str, object]:
    """THE ONE BEAM COUNT of the stem(s) of the head at `head_box`. Pure.

    `{"state": "read" | "narrowed" | "silent", "certain", "possible", "why", "stems": [per stem], "side"}`; `silent` has no count (the stem was
    not found in the map; the caller narrows, never reads zero). Per stem: the stroke ordinal, its side, the tip reading, and the causes of any
    narrowing (`stub`, `doubt`, `beamed_stem_uncounted`, `thick_at_stem`). Two stems (one each way, a unison of two voices) are read each on
    its own; the head's count is the lower to the higher (rule 8: never one voice's value for both)."""
    found = stems_by_ink(strokes, head_box, side)
    if not found["stems"]:
        if not finder_stem and found["why"] == "no_vertical_touches_the_head" and not beam_over_the_column(strokes, role_by_ord, head_box):
            # NO stem by either reader (the finder's and the ink's) and no beam over the head's column: a head with no stem carries no beam.
            return {"state": "read", "certain": 0, "possible": 0, "why": "", "stems": [], "side": side, "stemless": True}
        return {"state": "silent", "certain": None, "possible": None, "why": str(found["why"]), "stems": [], "side": side}
    per: List[Dict[str, object]] = []
    by_o = {s.ordinal: s for s in strokes}
    for stem, sd in found["stems"]:
        tip = tip_reading(strokes, role_by_ord, stem, sd, head_box=head_box, face_join=True, one_count=True)
        n = len(tip["beams"])
        causes: List[str] = []
        if n == 0 and STEM_ENDS_AT_ITS_BEAM:
            cut = _stem_cut_at_its_beam(strokes, role_by_ord, stem, sd, head_box)
            if cut is not None:
                stem = cut
                tip = tip_reading(strokes, role_by_ord, stem, sd, head_box=head_box, face_join=True, one_count=True)
                n = len(tip["beams"])
        extra = 0
        # A stub at the tip of a stem that already has a beam is a candidate SECOND level (a partial beam: Sean 2026-10-09, "a beam must not only connect to
        # its note but also to another note"). With no beam at all it is a flag-shaped hook, the flag reader's mark, and cannot make the count unreadable.
        stubs_here = list(tip["stubs"])
        if stubs_here and n >= 1 and STUB_STACKS_ON_THE_BEAM:
            # 2.318 r6: a second beam lies ONE beam-spacing in from the first (`STACK_GAP_SPACES`, the rule the levels themselves are stacked by). A
            # short bar farther in is not a beam: measured on the tile pages, all 19 stubs beside a counted beam stand 2.0-3.1 sp from it (ledger
            # lines 0.19-0.31 thick by the head, an accidental's or a dynamic's ink) -- one stands 1.2 -- and 11 of those notes are written today
            # and were being marked. Never drops a stub that starts where the next level would.
            sp_ = stem.space_px if stem.space_px > 0 else 1.0
            tip_y_ = float(tip["tip_y"])

            def _edges(s: StrokeView) -> Tuple[float, float]:        # (outer, inner) edge, staff spaces inward of the tip
                y0, y1 = s.box[1], s.box[1] + s.box[3]
                return ((y0 - tip_y_) / sp_, (y1 - tip_y_) / sp_) if sd == "up" else ((tip_y_ - y1) / sp_, (tip_y_ - y0) / sp_)
            reach = max(_edges(by_o[o])[1] for o in tip["beams"]) + STACK_GAP_SPACES
            stubs_here = [o for o in stubs_here if _edges(by_o[o])[0] <= reach]
        if stubs_here and n >= 1:
            causes.append("stub")
            extra += len(stubs_here)
        if tip["doubt"]:
            causes.append("doubt")
            extra += len(tip["doubt"])
        if n == 0 and tip["stubs"] and MARK_AT_BARE_TIP and any(_may_be_flag_or_broken_beam(strokes, by_o[o], tip["tip_y"], sd) for o in tip["stubs"]):
            causes.append("mark_at_bare_tip")
            extra += 1
        if n == 0 and not tip["stubs"] and not tip["doubt"] and not tip["hooks"]:
            # Where the tip counts no beam, "none" is only as good as what the map saw at the tip (rule 8): claimed ink the stem's end touches may have a
            # beam in it (`claimed_ink_at_tip`); a stem that runs into the cell crop's edge has its tip out of sight. Neither is "no beam".
            if claimed_ink_at_tip(strokes, stem, sd):
                causes.append("claimed_ink_at_tip")
                extra += 1
            elif THIN_LINE_TIP and thin_line_at_tip(strokes, role_by_ord, stem, sd, head_box):
                causes.append("thin_line_at_tip")
                extra += 1
            elif CUT_TIP and (("t" if sd == "up" else "b") in (stem.cut or "")):
                causes.append("stem_cut_by_cell")
                extra += 1
        sp = stem.space_px if stem.space_px > 0 else 1.0
        bx, _by, bw, _bh = stem.box
        sx = bx + bw / 2.0
        thick = []
        for o in sorted(set(tip["beams"])):
            s = by_o[o]
            if o in tip["fused"] or s.kind != "horizontal":
                continue                                 # already two levels (the tip reading's own fused test) / not a beam shape
            here, corr = thickness_less_line(s, sx)
            # NARROW, never decide (rule 8): the beam may be two beams fused by the scan, and this stem cannot say it is not. (a) the beam is as thick
            # AT THE STEM as the measured double beams (`FUSED_LOCAL_MIN_SPACES`) once a staff line it lies on is taken out; (b) the stroke is double
            # over part of its run (`FUSED_DOUBLE_MIN_THICKNESS_SPACES` on its median) and thin here -- a second beam that STARTS at a later stem
            # reads thin over the first stems (Brahms B01, a wedge). The tip reading's own outer-edge test (a slab 3 sp inward is a head cluster)
            # is what it needs to DECIDE a double; a beam it already counted at this tip needs none to be called possibly double.
            # 2.318 r6, (b) only: ...but a second beam is counted only at the stems it REACHES. Where the stroke's thick stretch (a profile sample as
            # thick as a double beam, `FUSED_LOCAL_MIN_SPACES`) lies more than `THICK_REACH_SPACES` along the beam from this stem, the stem stands
            # under the single part: one beam, read (`_thick_stretch_distance`).
            far = _thick_stretch_distance(s, sx)
            double_elsewhere = s.thickness >= FUSED_DOUBLE_MIN_THICKNESS_SPACES and not (far is not None and far > THICK_REACH_SPACES)
            if (FUSED_LOCAL_MIN_SPACES <= corr < FUSED_MAX_THICKNESS_SPACES) or double_elsewhere:
                thick.append({"stroke": o, "here": round(here, 3), "corrected": round(corr, 3), "median": round(s.thickness, 3)})
            elif STEP_NARROW and len(s.profile) >= 6 and here - thin_part(s) >= STEP_AT_STEM_SPACES:
                # (c) THIS stem's stretch of the beam is thicker than the same beam's thin part, as a second beam that starts here is (Brahms B09: a
                # second beam fused to the first on the bottom line: 0.79 here against 0.62 along the rest of the stroke). Said as a musician reads
                # it: thicker here than the beam is elsewhere. Never decides.
                thick.append({"stroke": o, "here": round(here, 3), "corrected": round(corr, 3), "median": round(s.thickness, 3),
                              "step": round(here - thin_part(s), 3)})
        if thick:
            causes.append("thick_at_stem")
            extra += len(thick)
        per.append({"stem": stem.ordinal, "stem_row": stem.row_id, "side": sd, "certain": n, "possible": n + extra, "causes": causes,
                    "beams": list(tip["beams"]), "hooks": list(tip["hooks"]), "stubs": list(tip["stubs"]), "doubt": list(tip["doubt"]),
                    "stem_beamed": bool(tip["stem_beamed"]), "own_head": list(tip["own_head"]), "thick_at_stem": thick, "tip_y": tip["tip_y"]})
    certain = min(int(p["certain"]) for p in per)
    possible = max(int(p["possible"]) for p in per)
    return {"state": "read" if possible == certain else "narrowed", "certain": certain, "possible": possible, "why": "", "stems": per, "side": side}
