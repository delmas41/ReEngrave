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


def role_of(s: StrokeView, by_ord: Dict[int, StrokeView], *, face_join: bool = False, trough: bool = False) -> Dict[str, object]:
    """The role of one stroke and the signed margins that say how close it came. Pure; reads `s` and the kinds of its neighbours.

    2.202f, both OFF by default (only the 2.202 path passes them): `face_join` also counts as this stroke's stems the stem-length verticals that
    stand under its run and stop short of its face (<= `FACE_JOIN_MAX_SPACES`, nothing between) at their own x (a beam lying on a staff line loses its contact with its stems to the
    erase: Litolff p2 13/0,1,3 read 1 stem of 4, so a `beam_stub`); `trough` files a >= 2-stem horizontal stroke in the thickness trough
    (`BEAM_DOUBT_MIN_THICKNESS_SP` .. `BEAM_MIN_THICKNESS_SP`) as `beam_doubt` instead of `span_thin`."""
    if s.kind not in ("horizontal", "curve"):
        return {"role": "other", "why": "kind:" + s.kind}
    stems = sorted({j for j, _c in s.touches if j in by_ord and by_ord[j].kind == "vertical" and by_ord[j].length <= STEM_MAX_SPACES})
    gap_stems: List[int] = []
    if face_join and s.kind == "horizontal" and stems:
        # only a stroke that already reaches a stem on its own is a beam whose width can own more (2.202f tiles 3, 8: a hairpin under a
        # stem tip touches no stem, and was taken for a broken beam -- FINDINGS 5i)
        gap_stems = sorted(v.ordinal for v in by_ord.values()
                           if v.kind == "vertical" and v.length <= STEM_MAX_SPACES and v.ordinal not in stems and v.ordinal != s.ordinal
                           and _face_joined(s, v, by_ord))
        stems = sorted(stems + gap_stems)
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


def roles(strokes: Sequence[StrokeView], *, face_join: bool = False, trough: bool = False) -> Dict[int, Dict[str, object]]:
    by_ord = {s.ordinal: s for s in strokes}
    return {s.ordinal: role_of(s, by_ord, face_join=face_join, trough=trough) for s in strokes}


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
                head_box: Optional[Sequence[float]] = None, face_join: bool = False) -> Dict[str, object]:
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
    stem_beamed = any(role_by_ord.get(s.ordinal, {}).get("role") == "beam" for s in touching)
    found: Dict[str, List[StrokeView]] = {"beam": [], "hook": [], "stub": [], "doubt": []}
    own_head: List[int] = []
    for s in touching:
        r = role_by_ord.get(s.ordinal, {}).get("role")
        key = ("beam" if r == "beam" else "hook" if r == "hook" else "stub" if r in ("beam_stub", "hook_or_stub")
               else "doubt" if r == "beam_doubt" else None)
        if key is None:
            continue
        if head_box is not None and _covers_head(s, head_box):
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
            if head_box is not None and _covers_head(s, head_box):
                continue
            if face_join and len(s.ends) >= 4:
                # the beam's face at THIS stem's x, beyond its tip: the stem stands under the beam (Sean 2026-10-28)
                yc = _centre_y(s, stem)
                if yc is not None and ((side == "up" and yc < tip_y) or (side == "down" and yc > tip_y)) and _face_joined(s, stem, by_ord):
                    joined.append(s)
                continue
            if _box_gap(s.box, stem.box) > JOIN_MAX_GAP_SPACES * sp:
                continue
            outer = s.box[1] if side == "up" else s.box[1] + s.box[3]
            if abs(outer - tip_y) > JOIN_OUTER_EDGE_SPACES * sp:
                continue
            joined.append(s)
        found["beam"].extend(joined)

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

    def levels(group: List[StrokeView]) -> List[int]:
        out: List[Tuple[float, int]] = []
        for s in sorted(group, key=lambda t: (t.box[1] + t.box[3] / 2.0, t.ordinal)):
            c = s.box[1] + s.box[3] / 2.0
            if out and abs(c - out[-1][0]) < LEVEL_MIN_SEPARATION_SPACES * sp:
                continue
            out.append((c, s.ordinal))
        return [o for _c, o in out]

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
