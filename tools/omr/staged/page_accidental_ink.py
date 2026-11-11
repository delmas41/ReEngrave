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


def read_page(strokes: Sequence[Any], sp: float, heads: Sequence[Head], boxed: Sequence[Sequence[float]], held: Sequence[Sequence[float]],
              reads: Sequence[Sequence[float]] = (), held_ids: Sequence[int] = (),
              header: Sequence[Sequence[float]] = (), held_by: Optional[Dict[int, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
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
    out = fold_twins(out)
    reasons["claimed"] = len(out)
    return out, reasons


def fold_twins(found: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One mark, one claim: two clusters whose ink boxes overlap by at least `OWN_BOX_SHARE` of either are ONE accidental seen from two seeds (the growth stops at a different
    piece depending on which stem it starts from; 2.285 first gather: one Litolff sharp claimed twice). The cluster with more strokes stays (ties: the first). Pure."""
    keep: List[Dict[str, Any]] = []
    for c in sorted(found, key=lambda c: (-len(c["members"]), c["box"])):
        if not any(share_inside(c["box"], k["box"]) >= OWN_BOX_SHARE or share_inside(k["box"], c["box"]) >= OWN_BOX_SHARE for k in keep):
            keep.append(c)
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
    system's left edge is claimed. A clef change (cell > 0) is not one."""
    from .record import Q, Scope
    out: List[Tuple[float, float, float, float]] = []
    for r in log.rows(Q.CLAIMED_AREA, page_sub, scope=Scope.SELF_AND_DESCENDANTS):
        d = r.detail or {}
        v = r.value
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
    found, reasons = read_page(pm.strokes, float(pm.sp), heads, boxed, rects, reads, ids, header_claims(log, sub), earlier_owners(log, sub))
    if not file:
        return found, reasons
    glyphs = file_own_accidentals(log, found, cells, local)
    reasons["row_filed"] = sum(1 for g in glyphs if g)
    for c, g in zip(found, glyphs):
        x0, y0, x1, y1 = c["box"]
        log.observe(sub, Q.CLAIMED_AREA, [x0, y0, x1, y1], reader=READERS.CV_PAGE_ACCIDENTAL_INK, frame=FRAME_PAGE, owner=OWNER, unit=UNIT, standing="READ", source=SOURCE,
                    how="family_reader_on_unboxed_ink", kind=c["type"], candidates=c["candidates"], page_strokes=list(c["members"]), contested=[], area=[x0, y0, x1, y1],
                    owner_row=None, owner_glyph=g, w_sp=c["w_sp"], h_sp=c["h_sp"])
    if progress:
        print("  gather page accidental ink p%s: %d claimed (%s), %d with a position row, %d heads known, refusals %s, %s s"
              % (p, len(found), ", ".join("%s %s" % (k, sum(1 for c in found if c["type"] == k)) for k in ("sharp", "flat", "natural")), reasons["row_filed"],
                 len(heads), {k: v for k, v in reasons.items() if k not in ("claimed", "row_filed")}, round(time.time() - t0, 2)))
    return found, reasons
