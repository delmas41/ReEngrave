"""ROADMAP 2.205 -- the shared ink map, STEP 5 (moved forward): ONE OWNER PER STROKE (flag `OMR_STROKE_OWNER`, default ON since 2026-10-26, needs
`OMR_STROKE_MAP` in the gather). STAGED ADJUDICATE, PURE: this module imports nothing from the pipeline. `adjudicators/stroke_owner.py`
(`adjudicate_stroke_owner`) is its stage: it hands in the cell's strokes (`Q.STROKE`), the detector boxes with the strokes each stands on
(`Q.GLYPH_STROKES`) and the register's area claims (`Q.CLAIMED_AREA`), and records what `own_strokes` returns, one verdict per stroke.

THE CAUSE (benchmarks/shared-ink-map-2026-10/FINDINGS.md, 2.205 section): the stroke map measures every piece of ink, but nothing said whose
it was, so the first two consumers (2.202 beams, 2.204 stems) read a sharp's crossbar, a notehead fused to its ledger and a slur's thin start
as beams and flags. A stroke's ROLE (beam, hook, stem) describes ANY dark stroke of that shape; who OWNS it has to be settled first.

THE ORDER OF CLAIMANTS (Sean 2026-10-25, "ownership before consumers"; the reading order of 2026-10-16, notehead first) --

  tier 0  the register's AREA claims (clef, key signature, meter, the header column; `Q.CLAIMED_AREA`, unit `area`): a convention says
          nothing else is printed there, so a stroke whose centre stands in one is that claim's (no shape test: the area IS the evidence)
  tier 1  noteheads, and ledger lines (the ledger names the owner, page-facts section 3): their blob strokes
  tier 2  accidentals (one family, `accidental*` and `key*`, Sean 2026-10-22)
  tier 3  arcs (slur, tie) and hairpins
  tier 4  dynamics, text, articulations, ornaments, dots
  tier 5  rests
  then    stems, beams, flags (2.202, 2.204) read only the strokes NO tier claimed: they are consumers, never claimants

A stroke's claimants are the boxes of those families that hold at least `COVER_SHARE_MIN` of its ink (`Q.GLYPH_STROKES`, the register's one
cut), the area claims its centre stands in, and ATTACHED strokes (below). Then, once per stroke:

  no claimant                 -> UNCLAIMED: the consumers read it
  an area claim               -> DECIDED, the area's owner (tier 0)
  one family whose shape fits -> DECIDED, that family (several boxes of it: MERGED, 2.186's rule -- the family is decided; WHICH box is
                                 2.186's question and is never answered here)
  claimants, none fits        -> REFUSED CLAIMS, the stroke left to the consumers: a box standing on ink that is not its shape (a block rest's
                                 box on a stem, a dynamic's box over a beam) owns nothing; the box-side rules read the refusal (this is where
                                 the old pair rules land, `box_verdict`)
  two families fit            -> the stroke's own shape decides when it CLEARLY fits exactly one (`clear` vs `could`; the measured fields
                                 are named in `why`); else CONTESTED: abstained, both candidates kept in claim order, counted, and no
                                 consumer may use it as a witness (rule 8: a contested stroke never becomes "no beam" or "no stem")

So the claim order decides two things only: the area claims stand first, and the consumers stand last. Between the box tiers it is the order
the candidates are LISTED in (an INFER collapse, later, may choose only among them); it never picks a winner (no confidence branch across
families -- plan section 4). One more place it acts: a stroke a head owns is never an accidental's ATTACHED stroke (2.201's `blocked`).

ATTACHED STROKES. A stroke only partly inside a mark's box (at least `ATTACH_SHARE_MIN`) that touches at least `ATTACH_MIN_TOUCHES` strokes
the mark already owns joins the mark: a sharp's crossbar that runs on into the note's stem ties the sharp's two stems together, so it is the
sharp's. Structural (what the stroke connects), not a number on the stroke -- and only a stroke the mark's shape admits (`shape_fit` not
`no`): a stem touching both halves of a head the staff-line erase split is still the note's stem.

THE SHAPES (`shape_fit`). A convention prior per family on the stroke's own fields, in staff spaces; none tuned to a count. `clear` = the
family's printed shape; `could` = a piece the family can leave on these plates (Litolff merges, Breitkopf shatters); `no` = never that
family's. The sizes are engraving sizes (a notehead ~1.3 x 1.0; a ledger ~2 long and as thin as a staff line; an accidental's stem at most
3.7 -- 2.201's measured STEM_MAX_SP; a beam at least 0.5 thick -- 2.202's measured BEAM_MIN_THICKNESS_SP; a quarter rest ~3 tall -- 2.71).
CONVENTION ASSUMED; WHAT WOULD FALSIFY IT: a plate whose heads, accidentals or rests are printed outside these sizes (then the family's
strokes fall to `no` and the consumers read them: the counts in the lane report show it). NOT CONFIRMED by Sean: nothing here READs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

ENV = "OMR_STROKE_OWNER"

#: A box COVERS a stroke when at least this share of the stroke's ink lies inside it (`stroke_map.COVER_SHARE_MIN`, the register's cut).
COVER_SHARE_MIN = 0.5
#: A stroke partly inside a mark's box (at least this share) that touches >= `ATTACH_MIN_TOUCHES` strokes the mark owns joins the mark.
ATTACH_SHARE_MIN = 0.15
ATTACH_MIN_TOUCHES = 2

#: the claimant tiers, in convention order (module doc). Consumers are not here.
TIERS: Tuple[Tuple[str, ...], ...] = (
    ("clef", "meter", "key_signature", "leading_column"),
    ("head", "ledger"),
    ("accidental",),
    ("arc", "hairpin"),
    ("dynamic", "mark", "dot", "text"),
    ("rest",),
)
CONSUMERS = ("stem", "beam", "flag")
AREA_OWNERS = TIERS[0]
STATES = ("unclaimed", "decided", "merged", "refused_claims", "contested")


def family_of(cls: str, category: Optional[str] = None) -> Optional[str]:
    """The ownership family of a detector class (SMuFL names). None = not a mark (the staff, a brace): never a claimant."""
    lc = str(cls or "").lower()
    if lc.startswith("notehead"):
        return "head"
    if lc.startswith("ledger"):
        return "ledger"
    if lc.startswith("accidental") or lc in ("keyflat", "keynatural", "keysharp"):
        return "accidental"
    if lc in ("slur", "tie"):
        return "arc"
    if "hairpin" in lc:
        return "hairpin"
    if lc.startswith("dynamic"):
        return "dynamic"
    if lc.startswith("rest"):
        return "rest"
    if lc.startswith("clef"):
        return "clef"
    if lc.startswith("timesig"):
        return "meter"
    if lc.startswith("flag"):
        return "flag"
    if lc == "beam":
        return "beam"
    if lc == "stem":
        return "stem"
    if lc in ("augmentationdot", "repeatdot"):
        return "dot"
    if lc.startswith(("tuplet", "segno", "coda", "fingering")):
        return "text"
    if lc in ("staff", "brace", "bracket") or lc.startswith("barline"):
        return None
    if (category or "") == "ornament" or lc.startswith(("artic", "fermata", "ornament", "keyboard", "strings", "caesura", "arpeggiato")):
        return "mark"
    return None


@dataclass(frozen=True)
class Ink:
    """One stroke as ownership reads it: the `Q.STROKE` row's fields (lengths in staff spaces, box in canonical cell px)."""
    ordinal: int
    kind: str                                     # vertical / horizontal / curve / blob
    box: Tuple[float, float, float, float]        # x, y, w, h
    length: float
    thickness: float
    area: float
    space_px: float
    touches: Tuple[Tuple[int, float], ...] = ()
    row_id: str = ""
    angle: float = 0.0                            # principal axis, degrees (0 horizontal, 90 vertical)

    @property
    def w_sp(self) -> float:
        return self.box[2] / self.space_px if self.space_px > 0 else 0.0

    @property
    def h_sp(self) -> float:
        return self.box[3] / self.space_px if self.space_px > 0 else 0.0


@dataclass(frozen=True)
class Claim:
    """A claimant: a detector box (`key` = its glyph subject key, `cls` its class) with the strokes it covers / partly covers, or a register
    area claim (`area` True; `covers` = the strokes whose centre stands in it)."""
    key: str
    family: str
    cls: str = ""
    covers: Tuple[int, ...] = ()
    partial: Tuple[Tuple[int, float], ...] = ()
    row_id: str = ""
    area: bool = False


# ── the shapes ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
HEAD_MAX_W_SP = 3.0          # a head 1.3 wide; fused to its ledger (~2.2) it is still the head's blob
HEAD_MAX_H_SP = 1.6
HEAD_MIN_AREA_SP2 = 0.25     # a filled head ~1.0 sp^2; a hollow head's ring ~0.5
HEAD_CLUSTER_MAX_H_SP = 3.4  # up to three heads of a chord stacked a step apart (~1 sp each, overlapping)
LEDGER_MAX_THICK_SP = 0.35   # a ledger is as thin as a staff line (~0.12-0.2); a beam is >= 0.5 (2.202)
LEDGER_MAX_LEN_SP = 3.5
ACC_STEM_MAX_SP = 3.7        # 2.201 STEM_MAX_SP
ACC_BAR_MAX_LEN_SP = 1.8     # a sharp's crossbar / a natural's square side ~1.0-1.3
ACC_BLOB_MAX_W_SP = 1.4
ACC_BLOB_MAX_H_SP = 2.2
ARC_MAX_THICK_SP = 0.5       # 2.202: an arc / hairpin remnant is 0.06-0.44, a beam >= 0.55
LETTER_MAX_LEN_SP = 3.0      # a dynamic letter's longest stroke
MARK_MAX_AREA_SP2 = 0.8      # a dot, a staccato, a fermata's dot
MARK_MAX_LEN_SP = 2.5        # a fermata's arc, a tenuto
#: a rest's longest stroke. 2.71's measured cut between a plain rest (2.8-3.1 sp) and a slashed stem boxed as a rest (4.5):
#: `family_precision.REST_SLASHED_MIN_HEIGHT_SPACES`. Measured 2.205 (owner_shape_sizes.py): the verticals under KEPT quarter / eighth rests
#: reach 3.44 (Litolff p95) / 3.0 (Brahms p95) -- an earlier 3.4 here refused 31 of them.
REST_MAX_LEN_SP = 3.8
REST_BLOCK_MAX_W_SP = 1.6    # a whole / half rest block ~1.1 x 0.5
#: ... a block is half a space thick nominally; MEASURED 2.205 (owner_shape_sizes.py, the blobs under KEPT whole / half rest boxes): median
#: 0.76, p95 0.88 sp on both plates (the convention's 0.75 refused 455 / 170 of them); a filled head's blob is 1.24-1.32 at the median.
#: 1.0 sits in that gap. A cut measured on our two plates: it only refuses a CLAIM (the box verdict is recorded, nothing acts on it).
BLOCK_MAX_H_SP = 1.0
#: a tremolo slash: a thick diagonal (Sean 2026-10-15) crossing a stem -- thickness at least a beam's minus its spread, 15-60 degrees
SLASH_MIN_THICK_SP = 0.35
#: ... and a LINE, not an oval: length / thickness at least this (a tilted head oval is ~1.5; a slash 1.5 x 0.45 is 3.3). Measured 2.205:
#: without it, real chord heads beside their stem were read as slashes (56 / 204 head-box strokes on the two plates)
SLASH_MIN_ASPECT = 2.5
SLASH_MIN_ANGLE = 15.0
SLASH_MAX_ANGLE = 60.0
#: the block rests (2.33b): their printed shape has NO vertical stroke, so a vertical under a whole / half rest box is never the rest's
BLOCK_RESTS = ("restwhole", "resthalf", "resthbar")


def shape_fit(family: str, s: Ink, cls: str = "", *, crosses_a_stem: bool = False, touches_a_head: bool = False,
              touches_a_note: bool = False, acc_bar_clear_of_note: bool = False) -> Tuple[str, str]:
    """`("clear" | "could" | "no", why)`: does stroke `s` fit the printed shape of `family` (`cls` refines rests)? The `why` names the fields.

    `crosses_a_stem`: the stroke touches a vertical stroke that runs on past both its sides (a slash across a stem, not a head beside it);
    `touches_a_head`: the stroke touches a stroke an EARLIER tier gave to a head (the claim order: a rest never touches a note -- 2.150b,
    `rest_stroke_into_a_head`; 2.33c, `rest_has_a_stem`); `touches_a_note`: it touches a head's stroke or a vertical stroke that touches one
    (the note's stem) -- a dynamic letter / text is printed clear of the notes (CONVENTION ASSUMED, 2.205 milestone: a Litolff flag boxed
    `dynamicF` took the flag from its eighth; WHAT WOULD FALSIFY IT: a letter printed touching a stem -- then the stroke is the consumers'
    as it is today, never invented into a flag by this rule)."""
    k, L, t, a, w, h = s.kind, s.length, s.thickness, s.area, s.w_sp, s.h_sp
    dims = "kind=%s len=%.2f thick=%.2f area=%.2f w=%.2f h=%.2f" % (k, L, t, a, w, h)
    if family in AREA_OWNERS:
        return "clear", "area:" + dims
    if family == "head":
        if (crosses_a_stem and k != "vertical" and t >= SLASH_MIN_THICK_SP and SLASH_MIN_ANGLE <= abs(s.angle) <= SLASH_MAX_ANGLE
                and t > 0 and L / t >= SLASH_MIN_ASPECT):
            # Sean 2026-10-15: "never oval - always thick diagonal lines" crossing one stem (page-facts section 1): never a head
            return "no", "tremolo_slash_across_a_stem:" + dims
        if k == "blob" and w <= HEAD_MAX_W_SP and h <= HEAD_MAX_H_SP:
            return ("clear" if a >= HEAD_MIN_AREA_SP2 else "could"), "head_blob:" + dims
        if k == "horizontal" and w <= HEAD_MAX_W_SP and h <= HEAD_MAX_H_SP:
            # a filled head's lens the horizontal opening kept (thick), or a ledger rung through the head (thin)
            return ("clear" if t > LEDGER_MAX_THICK_SP else "could"), ("head_lens:" if t > LEDGER_MAX_THICK_SP else "rung_in_head:") + dims
        if k in ("blob", "horizontal") and w <= HEAD_MAX_W_SP and h <= HEAD_CLUSTER_MAX_H_SP:
            # two or three heads of a chord fused into one piece (a second, a cluster -- 2.202 tile 5, 1.16 sp thick): head ink, but
            # which head is not this question
            return "could", "head_cluster:" + dims
        if k == "curve" and L <= 2.0:
            return "could", "head_outline_piece:" + dims
        return "no", "not_a_head_piece:" + dims
    if family == "ledger":
        if k == "horizontal" and t <= LEDGER_MAX_THICK_SP and L <= LEDGER_MAX_LEN_SP:
            return "clear", "ledger_rung:" + dims
        if k == "blob" and w <= HEAD_MAX_W_SP and h <= HEAD_MAX_H_SP:
            return "could", "rung_fused_to_head:" + dims
        return "no", "not_a_rung:" + dims
    if family == "accidental":
        if k == "vertical":
            return ("clear", "acc_stem:" + dims) if L <= ACC_STEM_MAX_SP else ("no", "longer_than_an_acc_stem:" + dims)
        if k == "horizontal":
            # 2.202f (Sean's round-3 tile 5, Litolff p6 1/8/10/5: a blotted beam boxed `accidentalSharp` at 0.48 took the 3.6-sp beam as its
            # "bar" and the eighth lost its beam): an accidental is printed CLEAR of its note, to the left of the head. A bar longer than an
            # accidental's that also runs into a note (its head or its stem) is the note's ink, never the accidental's.
            # Acts only with `acc_bar_clear_of_note` (the 2.202 path, `OMR_BEAMS_FROM_STROKES`: it lands with the beam reader it serves).
            if acc_bar_clear_of_note and L > ACC_BAR_MAX_LEN_SP and touches_a_note:
                return "no", "acc_bar_runs_into_a_note:" + dims
            return ("clear" if L <= ACC_BAR_MAX_LEN_SP else "could"), "acc_bar:" + dims
        if k == "blob":
            return ("clear" if w <= ACC_BLOB_MAX_W_SP and h <= ACC_BLOB_MAX_H_SP else "could"), "acc_body:" + dims
        return ("could" if L <= 2.0 else "no"), "acc_curve:" + dims
    if family in ("arc", "hairpin"):
        if k == "curve":
            return "clear", "arc_curve:" + dims
        if k == "horizontal" and t < ARC_MAX_THICK_SP:
            return "clear", "thin_line:" + dims
        # an arc's box is mostly paper over other marks (plan section 2.3): it claims only its own line, never a blob it passes over
        return "no", "not_an_arc_piece:" + dims
    if family in ("dynamic", "text"):
        if touches_a_note:
            return "no", "letter_ink_runs_into_a_note:" + dims
        if L > LETTER_MAX_LEN_SP and k != "blob":
            return "no", "longer_than_a_letter:" + dims
        return ("clear" if k in ("blob", "curve") else "could"), "letter_piece:" + dims
    if family in ("mark", "dot"):
        if k == "blob" and a <= MARK_MAX_AREA_SP2:
            return "clear", "small_mark:" + dims
        if k in ("curve", "horizontal") and L <= MARK_MAX_LEN_SP and t < ARC_MAX_THICK_SP:
            return "could", "mark_line:" + dims
        return "no", "not_a_small_mark:" + dims
    if family == "rest":
        block = str(cls or "").lower() in BLOCK_RESTS
        if touches_a_head:
            return "no", "rest_ink_runs_into_a_head:" + dims
        if block:
            # a whole / half rest is one block, half a space thick, hanging from / sitting on ONE line (2.33a: a box spanning a whole space
            # is a notehead's shape); it has no vertical stroke (2.33b/c)
            if k == "vertical":
                return "no", "block_rest_has_no_vertical:" + dims
            if k in ("blob", "horizontal") and h <= BLOCK_MAX_H_SP and w <= REST_BLOCK_MAX_W_SP:
                return "clear", "rest_block:" + dims
            return "no", "not_a_rest_block:" + dims
        if k == "vertical":
            if block:
                return "no", "block_rest_has_no_vertical:" + dims
            # a quarter / eighth rest's own slanted stroke reads as a short vertical (2.33b: 6 of 8 "rest has a stem" were real rests)
            return ("could", "rest_stroke:" + dims) if L <= REST_MAX_LEN_SP else ("no", "longer_than_a_rest:" + dims)
        if k == "blob":
            return ("clear", "rest_body:" + dims) if h <= REST_MAX_LEN_SP else ("no", "taller_than_a_rest:" + dims)
        if k == "horizontal":
            if t >= ARC_MAX_THICK_SP and L > REST_BLOCK_MAX_W_SP:
                return "no", "a_beam_not_a_rest_block:" + dims
            return "could", "rest_block:" + dims
        return ("could" if L <= REST_MAX_LEN_SP else "no"), "rest_curve:" + dims
    return "no", "not_a_claimant:" + family


# ── the decision, pure ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Ownership:
    """One stroke's owner, as `own_strokes` decides it."""
    ordinal: int
    state: str                                    # one of STATES
    family: Optional[str] = None                  # the owner family (decided / merged)
    owners: Tuple[str, ...] = ()                  # the claim keys of that family
    candidates: Tuple[Dict[str, object], ...] = ()   # every claimant, in claim order: key, family, cls, fit, why, how, row
    by: str = ""                                  # single / area / shape / attach / ""
    row_ids: Tuple[str, ...] = ()                 # the claim rows the verdict used

    @property
    def claimed(self) -> bool:
        """A consumer must NOT read this stroke: a mark owns it, or it is contested. A refused claim leaves it to the consumers."""
        return self.state in ("decided", "merged", "contested")


def _crosses_a_stem(s: Ink, by_ord: Dict[int, Ink]) -> bool:
    """`s` touches a vertical stroke that runs on at least a quarter space past BOTH its top and its bottom, and stands in its MIDDLE (at
    least a quarter space in from both its ends): a slash ACROSS a stem, never a head standing BESIDE one."""
    if s.kind == "vertical" or s.space_px <= 0:
        return False
    q = 0.25 * s.space_px
    x0, x1 = s.box[0], s.box[0] + s.box[2]
    y0, y1 = s.box[1], s.box[1] + s.box[3]
    for j, _c in s.touches:
        v = by_ord.get(j)
        if v is None or v.kind != "vertical":
            continue
        vx = v.box[0] + v.box[2] / 2.0
        if v.box[1] <= y0 - q and v.box[1] + v.box[3] >= y1 + q and x0 + q <= vx <= x1 - q:
            return True
    return False


def _settle(o: int, cand: Dict[int, List[Dict[str, object]]], tier_index: Dict[str, int]) -> Ownership:
    """One stroke's ownership from its candidates (already in claim order). See the module doc for the table."""
    cs = cand[o]
    if not cs:
        return Ownership(o, "unclaimed")
    rows = tuple(dict.fromkeys(str(c["row"]) for c in cs if c["row"]))
    first = cs[0]
    if first["how"] == "area" and tier_index[str(first["family"])] == 0:
        return Ownership(o, "decided", str(first["family"]), (str(first["key"]),), tuple(cs), "area", rows)
    fits = [c for c in cs if c["fit"] != "no"]
    if not fits:
        return Ownership(o, "refused_claims", candidates=tuple(cs), by="shape", row_ids=rows)
    fams = list(dict.fromkeys(str(c["family"]) for c in fits))
    pick = fams[0] if len(fams) == 1 else None
    if pick is None:
        clear = list(dict.fromkeys(str(c["family"]) for c in fits if c["fit"] == "clear"))
        pick = clear[0] if len(clear) == 1 else None
    if pick is None:
        return Ownership(o, "contested", candidates=tuple(cs), row_ids=rows)
    keys = tuple(dict.fromkeys(str(c["key"]) for c in fits if c["family"] == pick))
    how = "single" if len(cs) == 1 else "shape"
    return Ownership(o, "merged" if len(keys) > 1 else "decided", pick, keys, tuple(cs), how, rows)


def own_strokes(strokes: Sequence[Ink], claims: Sequence[Claim], tiers: Sequence[Sequence[str]] = TIERS, *,
                acc_bar_clear_of_note: bool = False) -> Dict[int, Ownership]:
    """`{ordinal: Ownership}` for every stroke of one cell. `claims` = the cell's detector boxes (any family: consumers and non-marks are
    dropped here) and its area claims. `tiers` is the claim order -- a parameter only so a control can break it. Deterministic."""
    by_ord = {s.ordinal: s for s in strokes}
    tier_index = {f: i for i, t in enumerate(tiers) for f in t}
    live = sorted((c for c in claims if c.family in tier_index), key=lambda c: (tier_index[c.family], c.key))
    crossing = {o for o in by_ord if _crosses_a_stem(by_ord[o], by_ord)}
    # the claim order acts here: a later tier sees what the EARLIER tiers' boxes own (a head's strokes, for the rest rule)
    head_tier = tier_index.get("head")
    cand: Dict[int, List[Dict[str, object]]] = {o: [] for o in by_ord}
    head_owned: set = set()
    note_ink: set = set()
    done_tier = -1
    for c in live:
        ti = tier_index[c.family]
        if ti > done_tier:
            if head_tier is not None and head_tier < ti and not head_owned:
                head_owned = {o for o in by_ord if _settle(o, cand, tier_index).family == "head"}
                note_ink = head_owned | {o for o, v in by_ord.items() if v.kind == "vertical" and any(j in head_owned for j, _c in v.touches)}
            done_tier = ti
        for o in c.covers:
            if o in by_ord:
                s_ = by_ord[o]
                touches_head = any(j in head_owned for j, _ct in s_.touches)
                touches_note = o in note_ink or any(j in note_ink for j, _ct in s_.touches)
                fit, why = ("clear", "area") if c.area else shape_fit(c.family, s_, c.cls, crosses_a_stem=o in crossing,
                                                                        touches_a_head=touches_head, touches_a_note=touches_note,
                                                                        acc_bar_clear_of_note=acc_bar_clear_of_note)
                cand[o].append({"key": c.key, "family": c.family, "cls": c.cls, "fit": fit, "why": why,
                                "how": "area" if c.area else "cover", "row": c.row_id})

    out: Dict[int, Ownership] = {o: _settle(o, cand, tier_index) for o in by_ord}

    # ATTACHED (module doc): one pass, in claim order, so it is deterministic. A stroke a HEAD owns is never attached to another mark.
    for c in live:
        if c.area:
            continue
        owned = {o for o, w in out.items() if c.key in w.owners}
        if len(owned) < ATTACH_MIN_TOUCHES:
            continue
        for o, share in c.partial:
            w = out.get(o)
            if w is None or w.claimed or share < ATTACH_SHARE_MIN:
                continue
            s = by_ord[o]
            n = sum(1 for j, _ct in s.touches if j in owned)
            if n < ATTACH_MIN_TOUCHES:
                continue
            fit, why = shape_fit(c.family, s, c.cls)
            if fit == "no":
                # a stroke the family can never be does not join it by touching it: a STEM touching the two halves of a head the staff-line
                # erase split is the note's stem, not the head's ink (measured 2.205: without this, 647 / 143 finder stems went to heads)
                continue
            entry = {"key": c.key, "family": c.family, "cls": c.cls, "fit": fit, "why": "attached:%d_owned:%s" % (n, why),
                     "how": "attach", "row": c.row_id, "share": share}
            out[o] = Ownership(o, "decided", c.family, (c.key,), tuple(list(w.candidates) + [entry]), "attach",
                               tuple(dict.fromkeys(list(w.row_ids) + [c.row_id])))
    return out


#: a box-level verdict (`box_verdict`): the stroke kinds a family's mark always stands BESIDE and never owns -- a head's / an accidental's /
#: a ledger's neighbouring stem. Such a stroke, left unclaimed, is no evidence against the box (it is the note's stem, read by 2.204).
NEUTRAL_KINDS = {"head": ("vertical",), "ledger": ("vertical",), "accidental": ("vertical",), "dynamic": ("vertical",)}


def box_verdict(claim: Claim, owned: Dict[int, Ownership], by_ord: Dict[int, Ink]) -> Dict[str, object]:
    """What ownership says about ONE claimant box as a mark (the box-side of the old pair rules):

      `owns`       it owns at least one stroke (decided or merged): the mark stands on its own ink
      `contested`  it owns nothing and at least one of its strokes is contested: NARROWED (cannot tell which mark the ink is)
      `refused`    it owns nothing: every stroke it COVERS is another family's, or a shape it can
                   never be -- a box on another mark's ink, or on ink that is not its shape
      `no_ink`     it stands on no stroke at all, or only on strokes its family stands BESIDE (`NEUTRAL_KINDS`): ownership cannot tell
    with `lost`: [(ordinal, state, owner family, why)] for the strokes it does not own."""
    # only the strokes the box COVERS speak: a stroke partly inside it (a neighbour's ledger rung, a beam it overlaps) is its margin
    # (measured 2.205: counting partial strokes refused 127 / 343 heads main kept, on a neighbouring rung or letter)
    touched = list(dict.fromkeys(claim.covers))
    lost: List[Tuple[int, str, Optional[str], str]] = []
    contested = False
    for o in touched:
        w = owned.get(o)
        if w is None:
            continue
        if claim.key in w.owners:
            return {"verdict": "owns", "lost": []}
        s = by_ord.get(o)
        if w.state in ("unclaimed", "refused_claims") and s is not None and s.kind in NEUTRAL_KINDS.get(claim.family, ()):
            continue
        contested = contested or w.state == "contested"
        why = next((str(c["why"]).split(":")[0] for c in w.candidates if c["key"] == claim.key), "")
        lost.append((o, w.state, w.family, why))
    if not lost:
        return {"verdict": "no_ink", "lost": []}
    return {"verdict": "contested" if contested else "refused", "lost": lost}


def census(owned: Dict[int, Ownership]) -> Dict[str, int]:
    """Counts by state, and owned strokes by family."""
    out: Dict[str, int] = {}
    for w in owned.values():
        out[w.state] = out.get(w.state, 0) + 1
        if w.family:
            out["family:" + w.family] = out.get("family:" + w.family, 0) + 1
    return out


def unclaimed(owned: Dict[int, Ownership]) -> set:
    """The ordinals a consumer (stems, beams, flags) may read."""
    return {o for o, w in owned.items() if not w.claimed}
