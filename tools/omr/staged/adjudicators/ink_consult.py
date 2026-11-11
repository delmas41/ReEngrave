"""ROADMAP 2.284 r5 -- THE ONE CONSULT: every box family asks the page ledger's one owner per page stroke, through this module, once
(flag `OMR_PAGE_LEDGER_OWNS`, default OFF; with it OFF nothing here is called and the three old mechanisms run unchanged). STAGED ADJUDICATE.

    Sean 2026-11-09 ("Fix 2"): "the page ledger owns the ink, one owner per page stroke, one consult for every box family". Sean 2026-11-10: "The
    issue is not what is built but what still needs to be built." CLAUDE section 3 (claim order): a later reader may MARK claimed ink, never TAKE it.
    The 2.205 claim tiers (`stroke_owner.TIERS`) name what is earlier.

THE CAUSE IT ANSWERS (2.283 audit, rows 10-11). Three consults (`claimed_by.consult`, `claim_final.finding`, `stroke_owner.box_says`) each covered
some families: heads, rests, accidentals, ledgers and arpeggiatos asked; dynamics, flags, articulations, tuplet and key markers, arcs and dots asked
nothing, so a dynamic, a flag or a tuplet box standing on ink an earlier mark had claimed was read again.

WHAT. The cell's `Q.STROKE_OWNER` verdict -- whose ownership, with the flag ON, is the page ledger's ONE settle per page stroke (`page_ledger`) --
carries `detail.ink_consult`: for EVERY box of the cell, whatever its family, how much of its own ink (stroke ink x the share of the stroke inside
the box) the ledger gave to a claim of an EARLIER tier than the box's own (`stroke_owner.TIERS`; an area / layer claim is tier 0; the consumers
stem / beam / flag stand after every tier), which claim, and whether the box owns a stroke of its own (`held_by_earlier`, pure). `consult` reads that
entry for one box and returns ONE answer, `Consult`:

  register  the claimed-area register's own rule table for its six owners (clef, meter, key signature, header column, word, bracket: the stem
            exceptions of 2.176 / 2.177 / 2.208 / 2.221 and the key tail) -- `claimed_by.consult`, run here, for the families it has rules for
            (head, rest, and the key run for marks); the register is a rule table INSIDE this consult, not a second consult;
  ledger    the page ledger's finding: the box is held at least `claim_final.CUT` of its own ink by an earlier claim and owns none of its own
            strokes -> refused BY THAT CLAIM (`claimed_by:barline`, `claimed_by:page_claim`, `claimed_by:earlier_mark`); the register's owners are
            left to `register` for the families it covers, and the hairpin trace only MARKS (`claim_final.mark_only`, the manager's 2.277 ruling);
  shape     the 2.238 owner-shape answer (`stroke_owner.box_says`: owns / refused / contested / silent), the old pair rules' evidence the owner holds.

`first()` is the refusal in claim order (register, then ledger), for the families whose deciders have no shape rules of their own.

CONVENTION ASSUMED: a box whose own ink is mostly an earlier mark's claimed ink, and which owns none of its own, is not a mark of its own kind
(claim order, plan 2026-10-28 section 9). WHAT WOULD FALSIFY IT: a print-confirmed dynamic / flag / articulation / tuplet numeral refused
`claimed_by:*` under the flag (r5 tiles). NOT CONFIRMED by Sean.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

from ..record import Kind, Q

#: the decider of each box family that must consult, and the file it lives in (relative to `staged/`). `unconsulted()` reads the SOURCE: a family
#: whose decider never calls this module's `consult` (or, for the stroke consumers, `stroke_owner.masked`) is a family that reads claimed ink again.
FAMILY_DECIDERS: Dict[str, Tuple[str, str]] = {
    "head": ("adjudicators/notehead_precision.py", "adjudicate_notehead_is_not_a_notehead"),
    "ledger": ("adjudicators/family_precision.py", "adjudicate_ledger_is_not_a_ledger"),
    "accidental": ("adjudicators/family_precision.py", "adjudicate_accidental_is_not_an_accidental"),
    "rest": ("adjudicators/family_precision.py", "adjudicate_rest_is_not_a_rest"),
    "arpeggiato": ("adjudicators/family_precision.py", "adjudicate_arpeggiato_is_not_an_arpeggiato"),
    "arc": ("adjudicators/family_precision.py", "adjudicate_arc_is_not_an_arc"),
    "dynamic": ("adjudicators/family_precision.py", "adjudicate_dynamic_is_not_a_dynamic"),
    "articulation": ("adjudicators/family_precision.py", "adjudicate_articulation_is_not_an_articulation"),
    "flag": ("adjudicators/family_precision.py", "adjudicate_flag_is_not_a_flag"),
    "tuplet": ("adjudicators/family_precision.py", "adjudicate_tuplet_marker_is_not_a_marker"),
    "dot": ("adjudicators/rhythm.py", "adjudicate_dot_role"),
    # the stroke CONSUMERS read the owner per stroke (`stroke_owner.masked`: an owned / contested stroke is never a stem or a beam)
    "stem": ("adjudicators/rhythm.py", "_stem_views"),
    "beam": ("adjudicators/rhythm.py", "_stroke_views"),
}
#: NOT a consulting family: the key-signature marker (`adjudicate_keysig_marker_is_not_a_marker`) runs BEFORE the stroke owner in `adjudicate.ORDER` (its
#: consumer, the header's key reader, is earlier still), and its ink IS the key run's tier-0 claim -- a key marker is the claimant, not a later reader.
#: The inventory guard (`test_staged_out_of_pipeline_producer`) refused the r5 first wiring: it would always read None.
EXEMPT = {"keysig_marker": "runs before the stroke owner (adjudicate.ORDER); its ink is the key run's own tier-0 claim"}
#: the consumers' consult is the per-stroke mask, not a box consult
CONSUMER_CALL = "_owner_mask("
#: a decider is ON the one consult when its body calls `consult` here, or a family_precision helper that does (`_ink_consult_refusal`, `_ledger_finding`)
BOX_CALLS = ("_ink_consult.consult(", "_ink_consult_refusal(", "_ledger_finding(")

#: refusal kinds a decider is told (a fixed vocabulary of literals: the vocabulary check reads them)
KINDS = ("barline", "page_claim", "earlier_mark")


def enabled() -> bool:
    from .. import page_ledger as _PL
    return _PL.enabled()


# ── the measurement, pure ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def tier_of(family: str, tiers: Sequence[Sequence[str]], area_families: Iterable[str] = ()) -> int:
    """A family's claim tier: an area / layer claim is 0; a family in no tier (the consumers stem / beam / flag) stands after every tier."""
    if family in set(area_families):
        return 0
    for i, t in enumerate(tiers):
        if family in t:
            return i
    return len(tiers)


def held_by_earlier(boxes: Iterable[Tuple[str, str, Iterable[Tuple[int, float, float, str, Optional[str], Sequence[str]]]]],
                    tiers: Sequence[Sequence[str]], area_families: Iterable[str] = (), near_min: float = 0.25) -> Dict[str, Dict[str, Any]]:
    """PURE. `{box key: {"by", "share", "ink", "strokes", "owns", "tier", "by_tier", "area"}}` for every box held at least `near_min` of its own ink by ONE claim
    family of an EARLIER tier than the box's own, and every box that owns nothing (share 0 entries are not filed). `boxes`: `(key, family, strokes)`, each
    stroke `(ordinal, share inside the box, ink, owner state, owner family, owner keys)`. A stroke counts as held only where the owner DECIDED it (decided /
    merged) for an earlier family other than the box's own (a contested stroke is no witness, rule 8). `owns`: the box is among the owners of a decided /
    merged stroke of its own family."""
    areas = frozenset(area_families)
    out: Dict[str, Dict[str, Any]] = {}
    for key, family, strokes in boxes:
        t_own = tier_of(family, tiers, areas)
        total = 0.0
        by: Dict[str, Tuple[float, List[int]]] = {}
        owns = False
        for o, share, ink, state, fam, owners in strokes:
            if ink is None or ink <= 0 or share <= 0:
                continue
            w = float(ink) * float(share)
            total += w
            if state not in ("decided", "merged") or not fam:
                continue
            if fam == family:
                owns = owns or key in set(owners or ())
                continue
            if tier_of(fam, tiers, areas) < t_own:
                ink0, ords = by.get(fam, (0.0, []))
                by[fam] = (ink0 + w, ords + [int(o)])
        if total <= 0 or not by:
            continue
        f = sorted(by, key=lambda x: (-by[x][0], x))[0]
        share = by[f][0] / total
        if share < near_min:
            continue
        out[key] = {"by": f, "share": round(share, 3), "ink": round(total, 1), "strokes": sorted(by[f][1]), "owns": owns, "tier": t_own,
                    "by_tier": tier_of(f, tiers, areas), "area": f in areas, "also": sorted(x for x in by if x != f)}
    return out


def refusal_kind(by: str, area: bool) -> str:
    """`claimed_by:<kind>`: the barline by name; any other area / layer claim is `page_claim` (a layer a later lane files is consumed with no code
    here); a claim by an earlier box family (a head, an accidental, a whole rest) is `earlier_mark`."""
    if by == "barline":
        return "barline"
    return "page_claim" if area else "earlier_mark"


# ── what a decider is told ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
class Consult(NamedTuple):
    register: Any            # `claimed_by.Finding` or None
    ledger: Any              # `adjudicators.claim_final.Finding` or None (the page ledger's refusal)
    shape: Tuple[str, Any, str]   # `stroke_owner.box_says` triple
    entry: Optional[Dict[str, Any]]   # the box's `detail.ink_consult` entry (None: not held)
    verdict_id: str

    def first(self) -> Any:
        """The refusal in claim order (register, then the page ledger), or None."""
        if self.register is not None and getattr(self.register, "refuse", False):
            return self.register
        return self.ledger


def owner_verdict(ev: Any) -> Any:
    """The cell's `Q.STROKE_OWNER` verdict, READ through the deciding module's own Evidence (its `wants` entry is live)."""
    cell = ev.subject.at(Kind.CELL)
    return ev.verdict(Q.STROKE_OWNER, subject=cell) if cell is not None else None


#: the families whose decider applies the register's own rule table (`claimed_by.consult`). The register's six owners (`claim_final.CONSULTED_ELSEWHERE`)
#: are judged by that table ONLY, for every family (a key accidental held by the key run is the key's ink, not a refusal; the 2.277 split, kept)
REGISTER_FAMILIES = ("head", "rest")
#: a SPANNER's detector box is a rectangle over other marks' ink by design (a slur box over its notes, a tuplet bracket over its group): "most of the box's
#: ink is another mark's" is no test of it. Its consult is recorded (`entry`), never a refusal; the arc's own unit is its traced ink (`arc_claim`, 2.284b).
SPANNER_FAMILIES = ("arc",)
#: the claims that REFUSE through the ledger: every area / page / layer claim (barline, an arc's or a hairpin's traced ink, a tremolo slash, the register's
#: owners for the families it has no table for) and a whole rest READ by its block (2.230: it claims before the heads). A claim by an earlier per-cell BOX
#: family (a head, an accidental) is RECORDED (`entry`, a tile), never a refusal: box-against-box is the owner's shape rules' question, and r5's first try
#: refused a real quarter rest a misdrawn head box had "decided" (Litolff glyph/2/0/8/2/4: the 2.205 tiers put rests last, so a head box's could-fit on a
#: rest's strokes wins them). Measured, not assumed: r5 re-adjudication, 3 written rests lost, 18 arpeggiatos refused by heads / accidentals.
#: ROADMAP 2.290 step 4 (flag `OMR_PAGE_HEAD_LEDGER`): a stroke the ledger gave to a PAGE HEAD's claim (its oval's own page strokes, read once on the page;
#: `page_heads.file_one_claims`) is held by this owner name, at the head tier -- unlike a per-cell head BOX, it is final: a later box mostly on it and owning
#: none of its own ink is refused `claimed_by:earlier_mark` (by `page_head`). Never present with the flag OFF.
PAGE_HEAD_OWNER = "page_head"
FINAL_BOX_CLAIMS = ("whole_rest", PAGE_HEAD_OWNER)
SPANNER_CLASSES = ("tupletBracket", "tupleBracket", "slur", "tie")


def consult(ev: Any, box_row: Any, family: str, *, head: bool = False, tail_reads: Any = None, verdict: Any = None,
            box_key: Optional[str] = None) -> Consult:
    """The ONE consult for one box (module doc). `family`: the asking decider's family (FAMILY_DECIDERS); `box_row`: its `Q.GLYPH_BOX` row (None
    for a decider that has none); `verdict`: the cell's `Q.STROKE_OWNER` verdict if the decider read it already. Call only with the flag ON."""
    from . import claimed_by as _CB
    from . import claim_final as _ACF
    from . import stroke_owner as _SOA
    from .. import claim_final as CF
    key = box_key or ev.subject.to_key()
    v = verdict if verdict is not None else owner_verdict(ev)
    vid = str(getattr(v, "id", "") or "")
    reg = None
    if family in REGISTER_FAMILIES and box_row is not None and _CB.enabled():
        reg = _CB.consult(ev, box_row, head=head, tail_reads=tail_reads)
    e = (((getattr(v, "detail", None) or {}).get("ink_consult") or {}).get("held") or {}).get(key)
    led = None
    cls = str((box_row.value[0] if box_row is not None and isinstance(box_row.value, (list, tuple)) and box_row.value else "") or "")
    if e and float(e["share"]) >= CF.CUT and not e.get("owns") and e["by"] not in CF.mark_only() and (e.get("area") or e["by"] in FINAL_BOX_CLAIMS) \
            and e["by"] not in CF.CONSULTED_ELSEWHERE and family not in SPANNER_FAMILIES and cls not in SPANNER_CLASSES:
        kind = refusal_kind(e["by"], bool(e.get("area")))
        detail = {"ink_consult": {"by": e["by"], "share": e["share"], "cut": CF.CUT, "strokes": e["strokes"], "also": e.get("also") or [],
                                  "tier": e.get("tier"), "by_tier": e.get("by_tier"), "verdict": vid},
                  # the 2.277 key, so every reader of `claim_final` detail reads the ledger's refusal the same way
                  "claim_final": {"by": e["by"], "share": e["share"], "cut": CF.CUT, "strokes": e["strokes"], "also": e.get("also") or [],
                                  "verdict": vid, "via": "ink_consult"}}
        used = tuple(x for x in ((box_row.id if box_row is not None else None), vid) if x)
        led = _ACF.Finding(kind, e["by"], float(e["share"]), used, detail)
    shape = _SOA.box_says(ev, key, v) if family in ("head", "rest", "accidental") else ("silent", None, vid)
    return Consult(reg, led, shape, e, vid)


# ── the derived check (CLAUDE rule 7: it must be able to fail) ─────────────────────────────────────────────────────────────────────────────
def _function_source(text: str, name: str) -> str:
    import re
    m = re.search(r"^def %s\(.*?(?=^def |^@decision|\Z)" % re.escape(name), text, re.S | re.M)
    return m.group(0) if m else ""


def unconsulted(staged_dir: Optional[Any] = None) -> List[Dict[str, str]]:
    """Every box family (FAMILY_DECIDERS) whose decider consults NO claim, as `{family, decider, why}`. Reads SOURCE text under `staged_dir` (default:
    this tree), so it can be pointed at a `git archive` of main (the BEFORE count). A decider consults when its body calls this module's `consult`, the
    old `claimed_by.consult` / `claim_final.finding` / `stroke_owner.box_says`, or (stems, beams) `stroke_owner.masked`."""
    import pathlib
    root = pathlib.Path(staged_dir) if staged_dir else pathlib.Path(__file__).resolve().parent.parent
    old = ("_claimed_by.consult(", "_claim_final.finding(", "_stroke_owner.box_says(", "_key_slot_refusal(", "_dot_ink_owned_elsewhere(")
    out: List[Dict[str, str]] = []
    for fam, (rel, fn) in FAMILY_DECIDERS.items():
        p = root / rel
        body = _function_source(p.read_text(), fn) if p.exists() else ""
        if not body:
            out.append({"family": fam, "decider": fn, "why": "decider not found"})
            continue
        if fam in ("stem", "beam"):
            if CONSUMER_CALL not in body:
                out.append({"family": fam, "decider": fn, "why": "reads strokes with no owner mask"})
            continue
        if any(c in body for c in BOX_CALLS):
            continue
        hits = [c for c in old if c in body]
        if not hits:
            out.append({"family": fam, "decider": fn, "why": "consults no claim"})
        elif hits == ["_key_slot_refusal("]:
            out.append({"family": fam, "decider": fn, "why": "consults the key run only (no other claim)"})
    return out


def not_on_the_one_consult(staged_dir: Optional[Any] = None) -> List[str]:
    """The box families whose decider does not call `consult` here (the old mechanisms or nothing): 0 is the target under the flag."""
    import pathlib
    root = pathlib.Path(staged_dir) if staged_dir else pathlib.Path(__file__).resolve().parent.parent
    out = []
    for fam, (rel, fn) in FAMILY_DECIDERS.items():
        p = root / rel
        body = _function_source(p.read_text(), fn) if p.exists() else ""
        calls = (CONSUMER_CALL,) if fam in ("stem", "beam") else BOX_CALLS
        if not any(c in body for c in calls):
            out.append(fam)
    return out


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="2.284 r5 derived check: python3 -m tools.omr.staged.adjudicators.ink_consult [--root DIR]")
    ap.add_argument("--root", default=None, help="a staged/ directory (e.g. a `git archive` of main)")
    a = ap.parse_args()
    f = unconsulted(a.root)
    print(json.dumps(f, indent=1))
    print("unconsulted families: %d; not on the one consult: %s" % (len(f), not_on_the_one_consult(a.root)))
