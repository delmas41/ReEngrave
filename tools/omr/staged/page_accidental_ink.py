"""ROADMAP 2.285 -- AN ACCIDENTAL CLAIMS ITS OWN INK WHERE THE DETECTOR DREW NO ACCIDENTAL BOX (STAGED GATHER; flag `OMR_ACCIDENTAL_OWN_INK`, default ON ("0" turns it off)).

    Sean's tiles 2.280 r2 (b40cca964), 2.279 r3 (b8b1a5ce2), 2.282 (5d882f939); 2.282 FINDINGS (benchmarks/claim-order-accid-stem-2026-11).
    CLAUDE section 3 (claim order: GATHER claims a mark's ink at the coarsest kind it is sure of; a later reader may mark claimed ink, never take it);
    Sean 2026-11-04 "once they're read, the ink is claimed once and ... not read again".

CAUSE (STAGED GATHER). Some printed sharps, flats and naturals get no accidental box from the detector (2.282: the five sharps Sean flagged were each boxed
only as a notehead at 0.25-0.46). Their ink is then a head box's, and its two long verticals are left for the stem reader: a false note and a false stem.
No claim ORDER can fix it (2.282: neither order landed): there is no accidental claim to order. LESSON: before testing an order, check that both
claimants exist at the places that hurt. A mark the detector cannot box must be read by the page pass (the 2.276 tremolo lesson, again).

WHAT. On the PAGE map, after the page-wide claims and before the head claim, ink that no accidental / key box, no earlier page claim and no real head holds
is read ONCE as an accidental by the ONE family reader (`accidental_family.read_type`, via `ink_members_and_extent`, no second shape reader):
  1. SEEDS: every vertical page stroke of an accidental stem's length (`accidental_family.STEM_MIN_SP`..`STEM_MAX_SP`) not held and not a real head's stem.
  2. EXTENT: the seed grown along the strokes it touches inside ONE accidental's size (`ink_members_and_extent`: the same growth the boxed accidentals get).
  3. KIND: `read_type` names flat / natural / sharp from the strokes (stem stagger, bowl). A cluster whose kind it cannot name is COUNTED, not claimed (rule 8).
  4. THE NOTE IT IS BY: a notehead box stands to its right within `HEAD_GAP_MAX_SP` and `HEAD_DY_MAX_SP` (an accidental is printed at the left of its note, a
     chord's stacked one up to three columns out; page-facts). No head beside it, no claim.
A cluster that passes is claimed (`Q.CLAIMED_AREA`, owner `accidental_ink`, unit `page_ink`, standing the family reader's: a natural at its READ margin is
READ, everything else GUESSED with its candidates, nothing is READ by this reader on a flat or a sharp -- `accidental_family.reads`). The claim is a layer of
`claim_order.LAYERS` before the heads: a head box standing on the ink is a LATER box, refused BY the claim through the one generic rule (2.277,
`claimed_by:page_claim`), counted by the consult, never dropped silently.

ROUND 2 (2026-11-10) -- TWO CAUSES, BOTH WIRING (benchmarks/accidental-own-ink-2026-11/FINDINGS.md).
  A. THE READER DID NOT CONSULT WHAT WAS ALREADY READ. (1) A rest the detector boxed is an earlier READ of its ink, and a rest box is not a claim at GATHER (only a whole rest,
     flag OFF), so the ledger rows could not refuse it: two correct quarter rests were read as flats (a stem and a curl) and removed from the file. Rest boxes were consulted
     by a private list here (`rest_box`); RETIRED at the 2.288 landing, the ledger's `claimed_by:rest` does it. (2) The crook `(C)` of a shared-word label (`Hr.` between two staves) is not in its word claim, because the staff's detected x_start (538, the true
     start is ~650) cut the margin strip: the `(` was free ink and read as a sharp. An accidental never stands left of its staff's first clef, and the clef and the leading column
     are claims on the ledger: ink whose centre lies left of one, at its rows, is the margin's (`left_of_the_clef`, `header_claims`).
  B. THE READ ACCIDENTAL HAD NO CONSUMER. Round 1 filed the kind on the claim row and nothing read it; the note beside was exported at the key's pitch, unmarked. Each claimed mark
     now also files the `Q.ACCIDENTAL_STAFF_POSITION` row a boxed accidental gets, from the same function (`gather.file_accidental_position`), on a glyph subject of the cell of
     the note it is by (ordinal `GLYPH_BASE`+n, no box in the cell's detection list, no class of the detector's). `adjudicate_accidental_owner` names the head by its position in
     that cell's own grid, `consequences.apply_printed_accidental` carries it to the bar, EXPORT writes it READ or GUESSED from the family row (`accidental_family.guess_of`: the
     mark has no detector class, so a sharp or flat is never a "lone agreement": GUESSED, blue; a natural at its READ margin is READ). A mark whose cell has no head to own it
     abstains `no_candidate`, counted, never written.

CONVENTION ASSUMED (page-facts "accidental"; accidental_family): an accidental is drawn in its font's shape and stands at the left of the note it alters. WHAT
WOULD FALSIFY IT: a claimed cluster Sean calls a note's stem or head (the control: a down-stem quarter note reads as one stem and a bowl). NOT CONFIRMED beyond
the two plates; the gap and offset cut-offs are measurements on them and only NARROW.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

DERIVED_CHECK = False
ENV = "OMR_ACCIDENTAL_OWN_INK"
OWNER = "accidental_ink"
UNIT = "page_ink"
SOURCE = "page_accidental_ink"
#: the notehead box that is the note an accidental is BY: its left edge stands at most this far right of the cluster's right edge (spaces) -- a chord's third column of
#: accidentals is ~3 sp out -- and its centre at most this far from the accidental's anchor, vertically (a chord's stack runs up to a sixth, ~3 sp)
HEAD_GAP_MAX_SP = 3.6
HEAD_DY_MAX_SP = 3.1
#: a head box overlapped this much by the cluster is the cluster's own box (a sharp boxed as a head), not the note it is by (the register's cover cut)
OWN_BOX_SHARE = 0.5
#: a detector box of an accidental / key class holds a stroke when this share of the stroke's box lies in it (the register's cover cut, `stroke_map.COVER_SHARE_MIN`)
BOXED_SHARE_MIN = 0.5
#: the cluster's ink and a detector accidental / key box overlap by this share of EITHER: the detector boxed this mark (its box may sit off the ink, 2.247 r2)
BOXED_OVERLAP_MIN = 0.25
#: a notehead box at least this confident holds a REAL head: its blob strokes are a head's, never an accidental's bowl. A box under it (the five sharps: 0.25-0.46)
#: holds nothing: the ink may be what the box mislabels. A measurement on two plates (2.282), only narrows.
REAL_HEAD_CONF = 0.5
HEAD_PREFIX = "notehead"
#: glyph ordinals of the accidentals this reader files a row for (ROADMAP 2.285 r2): past `gather._UNBOXED_REST_GLYPH_BASE` (350k) and every other gather base, BELOW
#: `record.STROKE_GLYPH_BASE` (375k: `Log.subjects(Kind.GLYPH)` does not list those) -- a collision would merge a row into another reader's subject
GLYPH_BASE = 360_000
#: what the accidental's family row says of the detector: nothing. The mark has NO detector class, so no class can "agree" with the strokes and make the reading a lone
#: agreement (`accidental_family.guess_of` returns None for that: READ). Flats and sharps are GUESSED, a natural at its READ margin is READ -- the family reader's own bar.
NO_DETECTOR = "page_ink"
#: the detector classes (by lower-case prefix) whose box is an EARLIER mark's read than an accidental in the reading order (2.276 r3): a dynamic letter, a beam, a flag, a clef,
#: a meter digit, a key, a fermata, an ornament.
EARLIER_READ_PREFIXES = ("dynamic", "beam", "flag", "clef", "timesig", "key", "fermata", "ornament", "tremolo", "keyboardpedal", "ottava", "repeat")
# (2.288 landing: the 2.285 r2 private list of detector rest boxes, `REST_PREFIX`, `rest_box`, is RETIRED: a READ rest is a claim on the ledger and `held_by` refuses its ink.)
#: the claims that stand at a system's LEFT EDGE (claim order, plan section 10 step 2): the header column and the clef, as the page-wide pass read them (cell 0 = the system's start).
#: An accidental never stands left of its staff's first clef (page-facts: "Only a clef stands before the key accidentals"), so ink whose centre lies left of such a claim, at its rows,
#: is the margin's -- a label, a crook, a brace. A clef CHANGE mid-system is not here (cell > 0): accidentals stand before it.
HEADER_OWNERS = ("clef", "leading_column")
#: the tallest ink that is ONE accidental, as a share of its glyph's height: Breitkopf prints ~10% larger than the font (`stroke_map`: the first try lost 15 of 21
#: naturals trimming to the font size), plus the register's tolerance. A measurement on two plates; it only narrows.
GLYPH_H_MAX_FRAC = 1.3
#: a solid blob this large and this filled is a head, whatever box stands on it (an accidental's bowl is a ring; page_heads.HEAD_MIN_AREA_SP2 is 0.25)
SOLID_HEAD_AREA_SP2 = 0.9
SOLID_HEAD_FILL = 0.8

# ── accidental-not-head lane (flag `OMR_ACCIDENTAL_FUSED_INK`, default ON): an accidental whose ink the scan has thickened ──────────────────────
#: THE RULE, as a musician says it: an accidental stands just left of the note it alters, about three spaces tall, and has no oval head of its own;
#: ink that is an accidental's is never also a notehead. Two shapes the reader above cannot see on a thick-inked plate (Litolff), both read here:
#:   * A NATURAL WHOSE BARS ARE LOST: its two uprights stand closer together than a notehead is wide, the left one higher and the right one lower
#:     (`accidental_family.read_type` names that stagger). Two stems of notes never stand that close -- a head stands between or beside them. Where
#:     the bars fused into the barline or the staff lines, the two uprights alone name the natural (the never: never two uprights a head's width
#:     apart; never a mirrored pair -- those on these plates were stems, a beam's ends, a flag).
#:   * A SHARP WHOSE BARS ARE BROKEN: two LEVEL uprights, each nearly the sharp's full height, as close as a natural's (Brahms 5/0/13/7: the thin
#:     bars left no stroke joining them). The never: short level pairs (1.6-1.8 sp, 0.2-0.25 apart on Litolff) were a beam's or a head's pieces.
#:   * A SHARP FILLED IN TO ONE BLOCK: the stroke map cuts it into a stack of blobs (as two stacked heads); ink in both its lower-left and its upper-
#:     right corner (its two uprights sticking out, `accidental_shape`), about three spaces tall, no stem in it. A notehead is one space tall; two
#:     heads stacked a third apart are two spaces tall and hang on a stem. Only a SHARP is read this way: the same corner reading names a quarter
#:     rest a "flat" (2.285 r1's failure), so a stack read as a flat or a natural is counted, never claimed (rule 8).
#: Both need a notehead box just right of them at their height (`head_beside`), and neither takes ink an earlier claim holds.
FUSED_ENV = "OMR_ACCIDENTAL_FUSED_INK"
#: the widest a natural's two uprights stand, centre to centre (spaces). Measured, Litolff p2/6/16 (32 staggered pairs by look, 23 naturals at
#: 0.37-0.58); a notehead (~1.2 sp) between two stems puts them at least ~1.1 apart. Between the two, it only narrows.
PAIR_GAP_MAX_SP = 0.7
#: the tallest the two uprights stand together (spaces): the naturals measured 3.59-4.34 (thick ink stretches the font's 2.7).
PAIR_H_MAX_SP = 4.5
#: a pair is an accidental only where BOTH uprights are at least this long (spaces): the 8 level pairs read by look on Litolff p2/6 + Brahms p5, all
#: sharps, measured 2.73-3.43, the 23 naturals 2.6-3.43; the short pairs that were not accidentals 1.59-1.84 (level: a beam's or a head's pieces;
#: Litolff 6/1/8/10 m72: a 1.84-sp upright beside a 2.8 one was the A4 eighth's own down stem beside a flat, and the stems check lost that note).
PAIR_STEM_MIN_SP = 2.2
#: a fused stack's height, as a share of the sharp glyph's (2.79 sp): at least `STACK_H_MIN_FRAC` (a third of two stacked heads is ~2.0 sp; the
#: filled sharps measured 2.65-4.02 sp), at most `STACK_H_MAX_FRAC`; and its width at most `STACK_W_MAX_SP` (the sharps: 1.0-1.94 sp).
STACK_H_MIN_FRAC = 0.85
STACK_H_MAX_FRAC = 1.5
STACK_W_MAX_SP = 2.0
#: a stroke in a fused stack longer than this (spaces) is a stem: a stack hanging on a stem is a chord, never a sharp
STACK_STEM_MIN_SP = 1.5
#: a sharp's uprights stick out past its bars, so at least one END of the filled block is no wider than an upright; two stacked heads end round
#: and wide. The narrower end's width (mean of its two end rows), spaces: the 18 filled Litolff sharps measured 0.13-0.29, the one stacked
#: chord they were confused with (Litolff 6/1/3/9, B-flat3 + E-flat4 beside a natural: the check's only real notes lost) 0.44.
STACK_END_MAX_SP = 0.35
#: ROADMAP 2.352 -- THE RULE, as a musician says it: a sharp is two thin uprights crossed by two slanted bars, so where its uprights stick out past the
#: bars paper shows between them; a solid block with one stub on it is noteheads on a broken stem, not a sharp. NEVER: release a real sharp.
#: The widest paper between two inked parts of one row of the filled block's own ink (spaces), at least this much. Measured on the reader's own mask,
#: both sides, real marks: Litolff p10 glyph/10/1/9/0/5 (Sean 2026-11-25: "a notehead but the stem ink is broken") 0.06 (one pixel); the four sharps this
#: reader claims among 2.347's eleven judged-true cases 0.31-0.32 (five pixels); the other 25 stack claims on Litolff p10/12/13 (unjudged) 0.19-0.39 except
#: three at 0.00-0.06 (Litolff p10 x2, p12 x1: left unclaimed, not looked at by Sean). A cut on ~16 px to the space with five judged marks: it only narrows.
STACK_TIP_GAP_MIN_SP = 0.15


def fused_enabled() -> bool:
    """`OMR_ACCIDENTAL_FUSED_INK` (accidental-not-head lane), default ON (Sean 2026-11-23); "0"/"false"/"no"/"off" turns it off. Needs the 2.285 reader on."""
    return os.environ.get(FUSED_ENV, "").strip().lower() not in ("0", "false", "no", "off")


def enabled() -> bool:
    """`OMR_ACCIDENTAL_OWN_INK` (ROADMAP 2.285), default ON (Sean 2026-11-10; "0"/"false"/"no"/"off" turns it off): the same opt-out as `OMR_PAGE_TREMOLO`.
    It ALSO needs `OMR_PAGE_CLAIM_RESTS` on (ROADMAP 2.288 landing): this reader learns of a rest ONLY through the rest's claim on the ledger (`held_by`, `claimed_by:rest`); with no rest
    claims it would read a quarter rest's stem and curl as a flat (2.285 r1), so it does not run. One mechanism, no private list of rest boxes."""
    from . import page_claim_names as _PCN
    return os.environ.get(ENV, "1").strip().lower() not in ("0", "false", "no", "off") and _PCN.rests_enabled()


def _box(s: Any) -> Tuple[float, float, float, float]:
    x, y, w, h = s.box
    return float(x), float(y), float(x + w), float(y + h)


def share_inside(inner: Sequence[float], outer: Sequence[float]) -> float:
    """The share of `inner` `(x0, y0, x1, y1)` lying inside `outer`. Pure."""
    ix = min(inner[2], outer[2]) - max(inner[0], outer[0])
    iy = min(inner[3], outer[3]) - max(inner[1], outer[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    return ix * iy / max(1e-9, (inner[2] - inner[0]) * (inner[3] - inner[1]))


def bar_joins_stems(members: Sequence[Any], ordinals: Sequence[int]) -> bool:
    """True where a member that is not a vertical stem (a bar: any other kind, the stroke map cuts a thin slanted bar as a horizontal or a blob) touches at least two of
    the member verticals: the two upright stems of a sharp / natural are JOINED by their bars, two bare verticals a chord's stem pair are not. `ordinals`: the page
    ordinal of each member (the `touches` numbering). Pure."""
    from . import accidental_family as AF
    stem_ords = {o for s, o in zip(members, ordinals) if s.kind == "vertical" and AF.STEM_MIN_SP <= float(s.length_sp) <= AF.STEM_MAX_SP}
    for s, o in zip(members, ordinals):
        if o in stem_ords:
            continue
        if sum(1 for j, _c in (getattr(s, "touches", None) or ()) if int(j) in stem_ords) >= 2:
            return True
    return False


def glyph_size_refusal(type_: str, w_sp: float, h_sp: float) -> Optional[str]:
    """None where ink of `w_sp` x `h_sp` (local spaces) has the size of ONE `type_` accidental glyph, else why not: `too_short` / `too_narrow` below the register's lower
    bounds (`stroke_map.accidental_ink_fits`, 2.242 r2), `too_tall` above `GLYPH_H_MAX_FRAC` of the glyph's height (a chord's stem pair stands 3.5 sp; a sharp
    2.8). Pure."""
    from . import accidental_family as AF
    from . import stroke_map as SM
    name = AF.class_of_type(type_)
    size = SM.accidental_size(name)
    if size is None:
        return None
    ok, why = SM.accidental_ink_fits(name, w_sp, h_sp)
    if not ok:
        return why.split(":")[0]
    if h_sp > GLYPH_H_MAX_FRAC * size[1]:
        return "too_tall"
    return None



class Head:
    """A detector notehead box on the page: `box` `(x0, y0, x1, y1)` page px, its `conf`, its `key`."""
    __slots__ = ("box", "conf", "key")

    def __init__(self, box: Sequence[float], conf: float, key: str = ""):
        self.box = tuple(float(v) for v in box)
        self.conf = float(conf or 0.0)
        self.key = key


def real_head_strokes(strokes: Sequence[Any], heads: Sequence[Head], boxed: Sequence[Sequence[float]], sp: float) -> List[int]:
    """The strokes that are a REAL head's ink: a blob a confident notehead box holds (and no accidental / key box holds), or a solid head-sized blob anywhere.
    Their neighbours are never grown into (`ink_members_and_extent`'s `blocked`), so a down-stem note's stem + head can never read as a flat. Pure."""
    out = []
    for i, s in enumerate(strokes):
        if s.kind != "blob":
            continue
        sb = _box(s)
        if any(share_inside(sb, a) >= BOXED_SHARE_MIN for a in boxed):
            continue
        spl = float(getattr(s, "staff_space_local", None) or sp)
        area = float(getattr(s, "area_sp2", 0.0) or 0.0)
        solid = area >= SOLID_HEAD_AREA_SP2 and float(getattr(s, "fill", 0.0) or 0.0) >= SOLID_HEAD_FILL
        if solid or any(h.conf >= REAL_HEAD_CONF and share_inside(sb, h.box) >= BOXED_SHARE_MIN for h in heads):
            out.append(i)
    return out


def held_strokes(strokes: Sequence[Any], held: Sequence[Sequence[float]], boxed: Sequence[Sequence[float]], reads: Sequence[Sequence[float]] = ()) -> set:
    """The strokes that are not this reader's: the centre in an earlier page claim's rectangle (barline, bracket, clef / key / meter, word, dynamic, ...), or at
    least `BOXED_SHARE_MIN` of the stroke's box inside a detector accidental / key box (the detector read it; its reader owns it) or inside an earlier mark's
    detector box (`reads`: a dynamic letter, a beam, a flag, a clef, a meter digit ... the reading order puts them before an accidental, as 2.276 r3). Pure."""
    out = set()
    for i, s in enumerate(strokes):
        sb = _box(s)
        cx, cy = (sb[0] + sb[2]) / 2.0, (sb[1] + sb[3]) / 2.0
        if (any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in held) or any(share_inside(sb, a) >= BOXED_SHARE_MIN for a in boxed)
                or any(share_inside(sb, a) >= BOXED_SHARE_MIN for a in reads)):
            out.add(i)
    return out


def head_beside(box: Sequence[float], anchor_y: float, heads: Sequence[Head], sp: float) -> Optional[Head]:
    """The notehead this cluster is BY: the nearest head box to its right (not the cluster's own box) within `HEAD_GAP_MAX_SP` and `HEAD_DY_MAX_SP` of its
    anchor height, else None. Pure."""
    best = None
    best_gap = None
    for h in heads:
        if share_inside(h.box, box) >= OWN_BOX_SHARE or share_inside(box, h.box) >= OWN_BOX_SHARE:
            continue
        gap = (h.box[0] - box[2]) / sp
        dy = abs((h.box[1] + h.box[3]) / 2.0 - anchor_y) / sp
        if -0.3 <= gap <= HEAD_GAP_MAX_SP and dy <= HEAD_DY_MAX_SP and (best is None or gap < best_gap):
            best, best_gap = h, gap
    return best


def left_of_header(box: Sequence[float], header: Sequence[Sequence[float]]) -> bool:
    """True where the ink's centre lies LEFT of a system-start header claim (`HEADER_OWNERS`) whose rows hold the ink's own: the margin's ink, never an accidental's
    (no accidental stands before its staff's first clef). `header`: the claims' rectangles `(x0, y0, x1, y1)`, page px. Pure."""
    cx, cy = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
    return any(r[1] <= cy <= r[3] and cx < r[0] for r in header)


def _union_box(boxes: Sequence[Sequence[float]]) -> List[float]:
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _cluster(members: Sequence[int], box: Sequence[float], ty: str, t: Dict[str, Any], h: Head, spl: float, how: str) -> Dict[str, Any]:
    """A fused-ink mark: never READ (margin None, so the family row writes it GUESSED, blue): its kind rests on a cut-off measured on one plate."""
    return {"members": sorted(members), "box": [round(v, 1) for v in box], "type": ty, "why": t.get("why"), "margin": None,
            "standing": "GUESSED", "head": list(h.box), "head_conf": h.conf, "head_key": h.key,
            "candidates": [ty], "features": {**{k: v for k, v in t.items() if k not in ("type", "why", "margin")}, "read_margin": t.get("margin")}, "how": how,
            "w_sp": round((box[2] - box[0]) / spl, 2), "h_sp": round((box[3] - box[1]) / spl, 2)}


def _free_of(box: Sequence[float], boxed: Sequence[Sequence[float]], header: Sequence[Sequence[float]]) -> Optional[str]:
    """Why a fused mark at `box` is not this reader's (None = it is): left of the system's first clef, or the detector boxed it."""
    if left_of_header(box, header):
        return "left_of_the_clef"
    if any(share_inside(box, a) >= BOXED_OVERLAP_MIN or share_inside(a, box) >= BOXED_OVERLAP_MIN for a in boxed):
        return "already_boxed"
    return None


def accidental_pairs(strokes: Sequence[Any], sp: float, heads: Sequence[Head], boxed: Sequence[Sequence[float]], taken: set, header: Sequence[Sequence[float]],
                  count: Any) -> List[Dict[str, Any]]:
    """A NATURAL OR SHARP WHOSE BARS ARE LOST (module rule above, `OMR_ACCIDENTAL_FUSED_INK`): two free uprights of an accidental stem's length, centres at
    most `PAIR_GAP_MAX_SP` apart, staggered the natural's way or level (a sharp), both at least `PAIR_STEM_MIN_SP` long -- `read_type` names
    them on the two uprights alone --, together at most `PAIR_H_MAX_SP` tall, a note just right of them. `taken`: stroke ordinals no mark here may use (held, already claimed). Pure."""
    from . import accidental_family as AF
    ups = sorted([i for i, s in enumerate(strokes) if s.kind == "vertical" and AF.STEM_MIN_SP <= float(s.length_sp) <= AF.STEM_MAX_SP and i not in taken],
                 key=lambda i: _box(strokes[i])[0])
    out: List[Dict[str, Any]] = []
    used: set = set()
    for n, a in enumerate(ups):
        if a in used:
            continue
        A = _box(strokes[a])
        spl = float(getattr(strokes[a], "staff_space_local", None) or sp)
        for b in ups[n + 1:]:
            B = _box(strokes[b])
            if B[0] > A[2] + PAIR_GAP_MAX_SP * spl:
                break
            if b in used:
                continue
            dx = abs((A[0] + A[2]) - (B[0] + B[2])) / 2.0 / spl
            if dx > PAIR_GAP_MAX_SP or min(A[3], B[3]) <= max(A[1], B[1]):
                continue
            t = AF.read_type([strokes[a], strokes[b]], [0, 1], spl, [])
            ty = t["type"]
            if min(float(strokes[a].length_sp), float(strokes[b].length_sp)) < PAIR_STEM_MIN_SP:
                continue        # an accidental's uprights are nearly its full height; a short one beside a long one is a note's stem or a flat's bowl side
            if ty not in ("natural", "sharp"):
                continue
            ub = _union_box([A, B])
            if (ub[3] - ub[1]) / spl > PAIR_H_MAX_SP:
                count("fused_pair:too_tall")
                continue
            why = _free_of(ub, boxed, header)
            if why:
                count("fused_pair:" + why)
                continue
            h = head_beside(ub, ub[1] + (ub[3] - ub[1]) * (AF.anchor_fraction(ty) or 0.5), heads, spl)
            if h is None:
                count("fused_pair:no_note_beside")
                continue
            # the accidental's bars are its ink too: every free piece that touches one of the two uprights and lies inside the pair's rows, never a
            # stem-long upright, never a real head's blob (`taken` holds those) -- Brahms 5/0/13/7: the sharp's bar ends left free kept the head box on
            # the sharp from being refused
            bars = [j for u in (a, b) for j, _c in (strokes[u].touches or ()) if 0 <= int(j) < len(strokes) and int(j) not in taken and int(j) not in (a, b)
                    and not (strokes[int(j)].kind == "vertical" and float(strokes[int(j)].length_sp) >= PAIR_STEM_MIN_SP)
                    and _box(strokes[int(j)])[1] >= ub[1] - 0.1 * spl and _box(strokes[int(j)])[3] <= ub[3] + 0.1 * spl
                    and _box(strokes[int(j)])[2] <= ub[2] + 0.6 * spl and _box(strokes[int(j)])[0] >= ub[0] - 0.6 * spl]
            mem = sorted({a, b} | {int(j) for j in bars})
            out.append(_cluster(mem, _union_box([_box(strokes[m]) for m in mem]), ty, t, h, spl, ty + "_pair"))
            used |= set(mem)
            used |= {a, b}
            break
    return out


def stack_corners(masks: Sequence[Any], members: Sequence[int], scale: float) -> Optional[Dict[str, Any]]:
    """`accidental_shape.classify` of the members' own ink (the stroke map's masks: staff lines erased, neighbours not drawn), or None without masks."""
    import numpy as np
    from . import accidental_shape as AS
    if not masks:
        return None
    ms = [masks[m] for m in members if 0 <= m < len(masks)]
    if not ms:
        return None
    x0 = min(int(x) for _m, x, _y in ms)
    y0 = min(int(y) for _m, _x, y in ms)
    x1 = max(int(x) + m.shape[1] for m, x, _y in ms)
    y1 = max(int(y) + m.shape[0] for m, _x, y in ms)
    u = np.zeros((y1 - y0, x1 - x0), bool)
    for m, x, y in ms:
        u[int(y) - y0:int(y) - y0 + m.shape[0], int(x) - x0:int(x) - x0 + m.shape[1]] |= np.asarray(m).astype(bool)
    img = np.where(u, 0, 255).astype(np.uint8)
    meas = AS.measure(img, (0, 0, u.shape[1], u.shape[0]))
    rows = [int(v) for v in u.sum(axis=1) if v > 0]
    k = min(2, len(rows))
    ends = [sum(rows[:k]) / float(k), sum(rows[-k:]) / float(k)] if rows else [0.0, 0.0]
    # the narrower end of the mark, in page px: an upright sticking out of a sharp, or a notehead's rounded end
    return {**AS.classify(meas), "measure": meas, "end_px": round(min(ends) / max(1e-9, float(scale or 1.0)), 2)}


def stack_tip_gap(masks: Sequence[Any], members: Sequence[int], scale: float, spl: float) -> float:
    """ROADMAP 2.352: the widest paper between two inked parts of ONE row of the members' own ink (the stroke map's masks: staff lines erased, neighbours not
    drawn), in staff spaces; 0.0 for a solid block with nothing standing apart from it (no row shows paper between two parts), or without masks. `spl`: page px to
    the space at the mark, `scale`: the masks' reduction of the page. Measures the ink, not its box. Pure."""
    import numpy as np
    ms = [masks[m] for m in members if 0 <= m < len(masks)]
    if not ms:
        return 0.0
    x0 = min(int(x) for _m, x, _y in ms)
    y0 = min(int(y) for _m, _x, y in ms)
    x1 = max(int(x) + m.shape[1] for m, x, _y in ms)
    y1 = max(int(y) + m.shape[0] for m, _x, y in ms)
    u = np.zeros((y1 - y0, x1 - x0), bool)
    for m, x, y in ms:
        u[int(y) - y0:int(y) - y0 + m.shape[0], int(x) - x0:int(x) - x0 + m.shape[1]] |= np.asarray(m).astype(bool)
    d = np.diff(np.pad(u.astype(np.int8), ((0, 0), (1, 1))), axis=1)
    widest = 0
    for r in range(d.shape[0]):
        starts, ends = np.flatnonzero(d[r] == 1), np.flatnonzero(d[r] == -1)
        if len(starts) > 1:
            widest = max(widest, int((starts[1:] - ends[:-1]).max()))
    return float(widest) / max(1e-9, float(scale or 1.0) * float(spl or 1.0))


def sharp_stacks(strokes: Sequence[Any], sp: float, heads: Sequence[Head], boxed: Sequence[Sequence[float]], taken: set, header: Sequence[Sequence[float]],
                 masks: Sequence[Any], scale: float, count: Any) -> List[Dict[str, Any]]:
    """A SHARP FILLED IN TO ONE BLOCK (module rule above, `OMR_ACCIDENTAL_FUSED_INK`): a group of strokes the stroke map cut from ONE fused piece
    (`joined_to`), none of them a stem, a horizontal or a curve, about one sharp tall (`STACK_H_MIN_FRAC`..`STACK_H_MAX_FRAC` of its glyph) and at
    most `STACK_W_MAX_SP` wide, ink in both its lower-left and upper-right corners (`accidental_shape`: a sharp), a note just right of it at its height.
    A stack the corners name anything else is counted (`fused_stack:<shape>`), never claimed. Pure."""
    from . import accidental_family as AF
    from . import stroke_map as SM
    size = SM.accidental_size("accidentalSharp") or (0.996, 2.792)
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for i, s in enumerate(strokes):
        if i in seen or not getattr(s, "joined_to", None):
            continue
        grp, todo = set(), [i]
        while todo:
            j = todo.pop()
            if j in grp or not (0 <= j < len(strokes)):
                continue
            grp.add(j)
            todo.extend(int(k) for k, _w in (strokes[j].joined_to or ()))
        seen |= grp
        mem = sorted(grp)
        if grp & taken:
            continue
        if any(strokes[m].kind in ("horizontal", "curve") or (strokes[m].kind == "vertical" and float(strokes[m].length_sp) >= STACK_STEM_MIN_SP) for m in mem):
            continue
        ub = _union_box([_box(strokes[m]) for m in mem])
        spl = float(getattr(s, "staff_space_local", None) or sp)
        w, hh = (ub[2] - ub[0]) / spl, (ub[3] - ub[1]) / spl
        if not (STACK_H_MIN_FRAC * size[1] <= hh <= STACK_H_MAX_FRAC * size[1]) or w > STACK_W_MAX_SP:
            continue
        why = _free_of(ub, boxed, header)
        if why:
            count("fused_stack:" + why)
            continue
        h = head_beside(ub, ub[1] + (ub[3] - ub[1]) * (AF.anchor_fraction("sharp") or 0.5), heads, spl)
        if h is None:
            count("fused_stack:no_note_beside")
            continue
        c = stack_corners(masks, mem, scale)
        shape = (c or {}).get("shape") or "unread"
        if shape != "sharp":
            count("fused_stack:" + shape)
            continue
        if float(c.get("end_px") or 0.0) / spl > STACK_END_MAX_SP:
            count("fused_stack:rounded_ends")          # no upright sticks out at either end: stacked heads, not a sharp
            continue
        if stack_tip_gap(masks, mem, scale, spl) < STACK_TIP_GAP_MIN_SP:
            # ROADMAP 2.352: a stub on one end passes the thin-end test, but a sharp's two uprights stand APART with paper between them; a solid block with
            # one stub is noteheads on a broken stem (Litolff p10 glyph/10/1/9/0/5, Sean: "a notehead but the stem ink is broken"). Left unclaimed, never re-read.
            count("fused_stack:no_paper_between_uprights")
            continue
        t = {"why": "filled_sharp_corners", "margin": c.get("margin"), "bl": (c.get("measure") or {}).get("bl"), "tr": (c.get("measure") or {}).get("tr")}
        out.append(_cluster(mem, ub, "sharp", t, h, spl, "sharp_stack"))
    return out


def read_page(strokes: Sequence[Any], sp: float, heads: Sequence[Head], boxed: Sequence[Sequence[float]], held: Sequence[Sequence[float]],
              reads: Sequence[Sequence[float]] = (), held_ids: Sequence[int] = (),
              header: Sequence[Sequence[float]] = (), held_by: Optional[Dict[int, str]] = None, *, fused: bool = False,
              masks: Sequence[Any] = (), scale: float = 1.0) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """The finder over every vertical stroke of the page (module doc). Returns the clusters that pass (each `{members, box, type, why, margin, standing, head,
    candidates, fam}`) and the refusal-reason counts. Pure: strokes in, dicts out. `header`: the system-start header claims' rectangles (`left_of_the_clef`).
    `held_by` (ROADMAP 2.288): `{stroke ordinal: owner}` of the ledger's page-stroke claims; where given, a seed stroke the LEDGER holds is counted `claimed_by:<owner>` (the one consult's
    own words) instead of passing silently. A read rest is a ledger claim (2.288); the reader keeps no list of the detector's rest boxes."""
    from . import accidental_family as AF
    blocked = set(real_head_strokes(strokes, heads, boxed, sp))
    held_set = held_strokes(strokes, held, boxed, reads) | {int(i) for i in held_ids}
    reasons: Dict[str, int] = {}
    seen: Dict[frozenset, Dict[str, Any]] = {}
    out: List[Dict[str, Any]] = []

    def count(why: str) -> None:
        reasons[why] = reasons.get(why, 0) + 1

    for i, s in enumerate(strokes):
        if s.kind != "vertical" or not (AF.STEM_MIN_SP <= float(s.length_sp) <= AF.STEM_MAX_SP):
            continue
        if i in held_set or i in blocked:
            if held_by is not None and i in held_by and i not in blocked:
                count("claimed_by:" + held_by[i])
            continue
        spl = float(getattr(s, "staff_space_local", None) or sp)
        ext = AF.ink_members_and_extent(_box(s), strokes, [(i, 1.0)], spl, sorted(blocked | held_set))
        mem = frozenset(ext["members"])
        if not mem or mem in seen:
            continue
        seen[mem] = ext
        ink_box = [float(v) for v in ext["box"]]
        if left_of_header(ink_box, header):
            count("left_of_the_clef")     # the margin's ink (a label's crook, a brace), left of the system's first clef: no accidental stands there
            continue
        t = AF.read_type([strokes[m] for m in sorted(mem)], list(range(len(mem))), spl, [])
        ty = t["type"]
        if ty not in AF.TYPES:
            count("kind_unclear:" + str(t.get("why")))
            continue
        size_why = glyph_size_refusal(ty, (ink_box[2] - ink_box[0]) / spl, (ink_box[3] - ink_box[1]) / spl)
        if size_why:
            count("size:" + size_why)
            continue
        if ty in ("sharp", "natural") and not bar_joins_stems([strokes[m] for m in sorted(mem)], sorted(mem)):
            count("two_stems_no_bar")           # a sharp's / natural's stems are joined by its bars; two bare verticals are a chord's stems
            continue
        if any(share_inside(ink_box, a) >= BOXED_OVERLAP_MIN or share_inside(a, ink_box) >= BOXED_OVERLAP_MIN for a in boxed):
            count("already_boxed")            # the detector read this mark (its box may sit off it, 2.247 r2): the boxed accidental's reader owns it
            continue
        frac = AF.anchor_fraction(ty) or 0.5
        anchor_y = ink_box[1] + (ink_box[3] - ink_box[1]) * frac
        h = head_beside(ink_box, anchor_y, heads, spl)
        if h is None:
            count("no_note_beside")
            continue
        margin = t.get("margin")
        out.append({"members": sorted(mem), "box": [round(v, 1) for v in ink_box], "type": ty, "why": t.get("why"), "margin": margin,
                    "standing": "READ" if AF.reads(margin, ty) else "GUESSED", "head": list(h.box), "head_conf": h.conf, "head_key": h.key,
                    "candidates": [ty], "features": {k: v for k, v in t.items() if k not in ("type", "why", "margin")},
                    "w_sp": round((ink_box[2] - ink_box[0]) / spl, 2), "h_sp": round((ink_box[3] - ink_box[1]) / spl, 2)})
    if fused:
        # accidental-not-head lane: the two thick-ink shapes the stroke reading above cannot see; never ink it or an earlier claim already took
        taken = set(held_set) | {m for c in out for m in c["members"]}
        pairs = accidental_pairs(strokes, sp, heads, boxed, taken | blocked, header, count)       # a real head's blob is never a bar
        out.extend(pairs)
        taken |= {m for c in pairs for m in c["members"]}
        out.extend(sharp_stacks(strokes, sp, heads, boxed, taken, header, masks, scale, count))
        reasons["fused_natural_pair"] = sum(1 for c in pairs if c["how"] == "natural_pair")
        reasons["fused_sharp_pair"] = sum(1 for c in pairs if c["how"] == "sharp_pair")
        reasons["fused_sharp_stack"] = sum(1 for c in out if c.get("how") == "sharp_stack")
    out = fold_twins(out, merge=fused)
    reasons["claimed"] = len(out)
    return out, reasons


def fold_twins(found: Sequence[Dict[str, Any]], merge: bool = False) -> List[Dict[str, Any]]:
    """One mark, one claim: two clusters whose ink boxes overlap by at least `OWN_BOX_SHARE` of either are ONE accidental seen from two seeds (the growth stops at a different
    piece depending on which stem it starts from; 2.285 first gather: one Litolff sharp claimed twice). The cluster with more strokes stays (ties: the first). Pure.
    `merge` (accidental-not-head lane, `OMR_ACCIDENTAL_FUSED_INK`): the kept claim also takes the folded twin's strokes -- ALL the mark's ink is claimed, seen from
    either upright. Without it a sharp's bar ends right of its right upright stayed free (Brahms 5/0/12/7: the head box on the sharp owned them, so the
    claim holding 92% of its ink did not refuse it, and an E-flat3 was written on the sharp)."""
    keep: List[Dict[str, Any]] = []
    for c in sorted(found, key=lambda c: (-len(c["members"]), c["box"])):
        twin = next((k for k in keep if share_inside(c["box"], k["box"]) >= OWN_BOX_SHARE or share_inside(k["box"], c["box"]) >= OWN_BOX_SHARE), None)
        if twin is None:
            keep.append(dict(c) if merge else c)
        elif merge and twin["type"] == c["type"]:
            twin["members"] = sorted(set(twin["members"]) | set(c["members"]))
            twin["box"] = [round(v, 1) for v in _union_box([twin["box"], c["box"]])]
    return sorted(keep, key=lambda c: (c["box"][0], c["box"][1]))


def _detector_reads(cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]]
                    ) -> Tuple[List[Head], List[Tuple[float, float, float, float]], List[Tuple[float, float, float, float]]]:
    """The detector's boxes of the page, page px, twins from two cells folded by identical rounded box: `(noteheads, accidental / key boxes, earlier-mark boxes)`. Rest boxes are not read
    here (2.288 landing): a rest the page reads claims its ink on the ledger."""
    from .record import Subject
    from .gather import _page_box
    cell_by_key = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            cell_by_key[(c.page_index, key[0], key[1], c.measure_index)] = c
    heads: List[Head] = []
    boxed: List[Tuple[float, float, float, float]] = []
    reads: List[Tuple[float, float, float, float]] = []
    seen = set()
    for ck, dets in detections.items():
        sub = Subject.from_key(ck)
        c = cell_by_key.get((sub.page, sub.system, sub.staff, sub.cell))
        if c is None:
            continue
        for d in dets:
            name = str(d.smufl_name)
            low = name.lower()
            pb = _page_box(c, d)
            if pb is None:
                continue
            k = (low,) + tuple(int(round(v / 2.0)) for v in pb)
            if k in seen:
                continue
            seen.add(k)
            if low.startswith(HEAD_PREFIX):
                heads.append(Head(pb, float(getattr(d, "confidence", 0.0) or 0.0), ck))
            elif low.startswith("accidental") or (low.startswith("key") and not low.startswith("keyboard")):
                boxed.append(tuple(float(v) for v in pb))
            elif low.startswith(EARLIER_READ_PREFIXES):
                reads.append(tuple(float(v) for v in pb))
    return heads, boxed, reads


def earlier_claims(log: Any, page_sub: Any) -> Tuple[List[Tuple[float, float, float, float]], List[int]]:
    """What the page-wide claims already on the log hold: `(rectangles, stroke ordinals)`. A `unit: area` READ claim (clef, key, meter, word, barline, bracket, the header
    column) holds the strokes whose centre stands in its rectangle; a claim that names page strokes (an arc, a hairpin, a slash, a page-ink claim) holds those. This
    reader's own rows are not read back (it runs once per page)."""
    from .record import Q, Scope
    rects: List[Tuple[float, float, float, float]] = []
    ids: List[int] = []
    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        if str(d.get("owner") or "") == OWNER:
            continue
        v = r.value
        if d.get("unit") == "area" and d.get("standing", "READ") == "READ" and isinstance(v, (list, tuple)) and len(v) == 4 and all(isinstance(t, (int, float)) for t in v):
            rects.append(tuple(float(t) for t in v))
        for o in d.get("page_strokes") or ():
            if isinstance(o, int):
                ids.append(int(o))
    return rects, ids


def earlier_owners(log: Any, page_sub: Any) -> Dict[int, str]:
    """`{page stroke ordinal: owner}` for the page strokes the ledger's earlier claims name (`earlier_claims`' second answer, with the owner kept so the consult can say
    `claimed_by:<owner>`). The first claim on a stroke keeps it. This reader's own rows are not read back."""
    from .record import Q, Scope
    out: Dict[int, str] = {}
    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        owner = str(d.get("owner") or "")
        if owner == OWNER:
            continue
        for o in d.get("page_strokes") or ():
            if isinstance(o, int):
                out.setdefault(int(o), owner)
    return out


def header_claims(log: Any, page_sub: Any) -> List[Tuple[float, float, float, float]]:
    """The rectangles of the system-start header claims the page-wide pass filed (`HEADER_OWNERS`, READ, `unit: area`, cell 0): the page ledger's own rows, the one place the
    system's left edge is claimed. A clef change is not one -- wherever it stands: ROADMAP 2.324 r8, a clef the page-wide pass read INSIDE the first bar (`change: True`, cell 0;
    four on Litolff) is no start-of-staff clef, and ink left of it is the bar's own."""
    from .record import Q, Scope
    out: List[Tuple[float, float, float, float]] = []
    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        v = r.value
        if d.get("owner") == "clef" and d.get("change"):
            continue
        if (str(d.get("owner") or "") in HEADER_OWNERS and d.get("unit") == "area" and d.get("standing", "READ") == "READ" and d.get("cell") == 0
                and isinstance(v, (list, tuple)) and len(v) == 4 and all(isinstance(t, (int, float)) for t in v)):
            out.append(tuple(float(t) for t in v))
    return out


def cell_of_head(cells: Sequence[Any], local: Dict[int, Tuple[int, int]]) -> Dict[str, Any]:
    """`{cell subject key: cell}` for every cell the page holds (the key a `Head` carries is its detection list's, a cell subject key)."""
    from .record import Subject
    from . import record as R
    out: Dict[str, Any] = {}
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            out[R.cell(c.page_index, key[0], key[1], c.measure_index).to_key()] = c
    return out


def own_accidental_detection(cell: Any, cluster: Dict[str, Any]) -> Optional[Any]:
    """The mark as a `SymbolDetection` of its OWN cell (never put in the cell's detection list: no box, no class of the detector's), carrying the family reading the
    boxed accidentals carry (`d.accidental_family`), so `gather.file_accidental_position` files its `Q.ACCIDENTAL_STAFF_POSITION` row exactly as for a boxed one.
    Canonical cell frame from the page box (the inverse of `gather._page_box`). None where the cell has no page frame."""
    from . import accidental_family as AF
    from ..template_matcher import SymbolDetection
    rect, up = getattr(cell, "bbox_page_px", None), getattr(cell, "upscale_factor", None)
    if not rect or not up:
        return None
    x0, y0, x1, y1 = (float(v) for v in cluster["box"])
    cx0, cy0 = int(round((x0 - rect[0]) * up)), int(round((y0 - rect[1]) * up))
    cw, ch = max(1, int(round((x1 - x0) * up))), max(1, int(round((y1 - y0) * up)))
    ty = cluster["type"]
    d = SymbolDetection(cell=cell, smufl_name=AF.class_of_type(ty), category="accidental", x_canonical=cx0, y_canonical=cy0, width_canonical=cw,
                        height_canonical=ch, confidence=0.0)
    d.accidental_family = {"type": ty, "why": cluster.get("why"), "margin": cluster.get("margin"), "features": dict(cluster.get("features") or {}),
                           "box": [float(cx0), float(cy0), float(cx0 + cw), float(cy0 + ch)], "grown": [], "grown_sp": 0.0, "members": list(cluster["members"]),
                           "detector_class": NO_DETECTOR, "detector_type": None, "candidates": [], "agrees_with_detector": None,
                           "anchor_fraction": AF.anchor_fraction(ty)}
    return d


def file_own_accidentals(log: Any, found: Sequence[Dict[str, Any]], cells: Sequence[Any], local: Dict[int, Tuple[int, int]]) -> List[Optional[str]]:
    """ROADMAP 2.285 r2 (the value existed and nothing read it): each claimed cluster's `Q.ACCIDENTAL_STAFF_POSITION` row, on a glyph subject of the cell of the note it
    is by -- the SAME row, from the SAME function, a detector-boxed accidental gets (`gather.file_accidental_position`). `adjudicate_accidental_owner` then names the
    head by position (local staff grid of that cell), EVALUATE carries the alteration to the bar's later notes, and EXPORT writes READ or GUESSED from the family row.
    Returns each cluster's glyph key (None where no row could be filed: no page frame / no staff grid for the cell)."""
    from .record import Subject
    from . import record as R
    from . import gather as G
    by_cell = cell_of_head(cells, local)
    count: Dict[str, int] = {}
    keys: List[Optional[str]] = []
    for c in found:
        ck = c.get("head_key")
        cell = by_cell.get(ck)
        d = own_accidental_detection(cell, c) if cell is not None else None
        if d is None:
            keys.append(None)
            continue
        sub = Subject.from_key(ck)
        gi = GLYPH_BASE + count.get(ck, 0)
        if G.file_accidental_position(log, cell, sub, gi, d):
            count[ck] = count.get(ck, 0) + 1
            keys.append(R.glyph(sub.page, sub.system, sub.staff, sub.cell, gi).to_key())
        else:
            keys.append(None)
    return keys


def gather_page_accidental_ink(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]], pm: Any, *,
                               file: bool = True, progress: bool = False) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, int]]]:
    """ROADMAP 2.285 (flag `OMR_ACCIDENTAL_OWN_INK`, default ON), STAGED GATHER. Reads the page's unboxed accidental ink once, claims it and (r2) files each claimed mark's
    own `Q.ACCIDENTAL_STAFF_POSITION` row (module doc). `file=False` reads only. Returns `(clusters, reasons)`, or None where the flag is off or there is no page map."""
    if not enabled() or pm is None or not getattr(pm, "strokes", None):
        return None
    from . import record as R
    from .record import Q, READERS
    from .gather import FRAME_PAGE
    t0 = time.time()
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    heads, boxed, reads = _detector_reads(cells, local, detections)
    rects, ids = earlier_claims(log, sub)
    # ROADMAP 2.288: a rest that stands READ is a claim on the ledger (`page_claim_names.gather_page_claim_boxes`, before this reader) and the ledger consult refuses its ink
    # (`claimed_by:rest`); a weak rest box blocks nobody, by rule: only a READ rest claims. `enabled()` already required the rest claims to be on.
    found, reasons = read_page(pm.strokes, float(pm.sp), heads, boxed, rects, reads, ids, header_claims(log, sub), earlier_owners(log, sub),
                               fused=fused_enabled(), masks=getattr(pm, "masks", None) or (), scale=float(getattr(pm, "scale", 1.0) or 1.0))
    if not file:
        return found, reasons
    glyphs = file_own_accidentals(log, found, cells, local)
    reasons["row_filed"] = sum(1 for g in glyphs if g)
    for c, g in zip(found, glyphs):
        x0, y0, x1, y1 = c["box"]
        extra = {"fused": c["how"]} if c.get("how") in ("natural_pair", "sharp_pair", "sharp_stack") else {}      # accidental-not-head lane: which thick-ink shape
        log.observe(sub, Q.CLAIMED_AREA, [x0, y0, x1, y1], reader=READERS.CV_PAGE_ACCIDENTAL_INK, frame=FRAME_PAGE, owner=OWNER, unit=UNIT, standing="READ", source=SOURCE,
                    how="family_reader_on_unboxed_ink", kind=c["type"], candidates=c["candidates"], page_strokes=list(c["members"]), contested=[], area=[x0, y0, x1, y1],
                    owner_row=None, owner_glyph=g, w_sp=c["w_sp"], h_sp=c["h_sp"], **extra)
    if progress:
        print("  gather page accidental ink p%s: %d claimed (%s), %d with a position row, %d heads known, refusals %s, %s s"
              % (p, len(found), ", ".join("%s %s" % (k, sum(1 for c in found if c["type"] == k)) for k in ("sharp", "flat", "natural")), reasons["row_filed"],
                 len(heads), {k: v for k, v in reasons.items() if k not in ("claimed", "row_filed")}, round(time.time() - t0, 2)))
    return found, reasons
