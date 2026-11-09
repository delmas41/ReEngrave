"""ROADMAP 2.277 -- CLAIMED INK IS FINAL (flag `OMR_CLAIM_FINAL`, default OFF). PATH: STAGED ADJUDICATE; this module is PURE (plain numbers in, plain
numbers out; it names no quantity and files no row). `adjudicators/stroke_owner.py` calls `held_boxes` / `marks` once per cell and records the
result on the cell's `Q.STROKE_OWNER` verdict (`detail.claim_final`); `adjudicators/notehead_precision.py` and `adjudicators/family_precision.py`
(the rest) read it through `adjudicators/claim_final.py` and refuse BY THE CLAIM.

THE RULE (Sean 2026-11-08: "make sure once ink is claimed that it can not be counted again or reboxed. This is a big deal - essential to our
process. It won't add notes but it will be a more realistic picture of what we are reading"; north star: all ink is accounted for one time;
CLAUDE section 3: a later reader may MARK claimed ink, never TAKE it).

  A detector box (a head, a rest, an accidental ...) is a HYPOTHESIS over the page strokes under it. The stroke owner (2.205) already settles,
  once per stroke, who owns it, in claim order. Two measurements follow from that ownership and nothing else:

    HELD   the share of the box's OWN ink (over the strokes under it: stroke ink x the share of the stroke inside the box) that the stroke owner
           gave to a claim of ANOTHER kind that stands before the per-cell marks (every area / page claim the cell holds -- barline, bracket, word,
           clef, key, meter, the header column, an arc's or a hairpin's traced ink, and whatever a later lane files, e.g. a tremolo slash --
           plus a found whole rest). Not box overlap: a stroke counts only where the owner DECIDED it (a contested stroke is no witness, rule 8).
    MARK   the head boxes whose head-owned strokes overlap are ONE mark (a copy by position: two boxes on one head's ink). `marks()` names each
           box's mark; a mark is counted once, whatever the box count (the detector draws, the record keeps every box, the picture counts ink).

A box HELD at least `CUT` of its own ink is refused BY THAT CLAIM (`claimed_by:<kind>`), so the claim is the first cause and never a shape rule
(`too_narrow`, `clipped_fragment`). A box that owns its blob and merely touches a claim (a head beside a barline or under a slur) is HELD by a
small share and is left alone. CUT = 0.5 is the register's one cut (`claims.INSIDE_SHARE_MIN`); a CUT is a measurement and this one only NARROWS
until a second publisher confirms it (CLAUDE section 4): the boxes between `NEAR_MIN` and `CUT` are recorded with their share, so a near miss is
a blind tile and not a silence.

CONVENTION ASSUMED: a box that is mostly another mark's claimed ink is not a mark of its own kind (claim order, plan section 9). WHAT WOULD FALSIFY
IT: a print-confirmed head under a refusal `claimed_by:barline|arc|hairpin|page_claim` (Sean's blind tiles `out/print/2.277/`). NOT CONFIRMED yet.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ENV = "OMR_CLAIM_FINAL"

#: the share of a box's own ink a claim of another kind must hold for the claim to refuse it (the register's cut, `claims.INSIDE_SHARE_MIN`)
CUT = 0.5
#: boxes held at least this much are RECORDED (a refusal says how close it came: near misses become tiles)
NEAR_MIN = 0.25
#: the per-cell families a box can be of whose ink an earlier claim may hold. Consumers (stem, beam, flag) read what no claim took; they are
#: never boxes of a mark here.
BOX_FAMILIES = ("head", "ledger", "accidental", "rest", "whole_rest", "dot", "mark", "dynamic", "text")
#: families the register consult (`claimed_by.consult`) already refuses by its own, stricter tests (it has the stem exceptions of 2.176 / 2.177 /
#: 2.208 / 2.221 and a NARROW path); this mechanism leaves them to it and takes every other claim kind
CONSULTED_ELSEWHERE = frozenset({"clef", "meter", "key_signature", "leading_column", "word", "bracket"})
#: claims that only MARK, never refuse a box here (Sean's manager 2026-11-08, after the 2.277 crops): the arc and hairpin TRACES took real heads' ink where a
#: slur touches a head (Litolff tiles 1, 5, 6, 7: held 0.53-0.83 by the arc trace, real notes), so refusing by them would lose notes. That is itself a claim-order
#: violation of the arc claim (it took head ink); it belongs to the arc lanes (2.273, 2.274). Recorded in `held`, never refused.
MARK_ONLY = frozenset({"arc_trace", "arc", "hairpin_trace", "hairpin"})


def enabled() -> bool:
    """`OMR_CLAIM_FINAL`, default OFF; only an explicit 1/true/yes/on enables."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


# ── the measurement, pure ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def held_share(strokes: Iterable[Tuple[int, float, float, str, Optional[str]]], own_family: str,
               claim_families: Iterable[str]) -> Tuple[float, Dict[str, Tuple[float, List[int]]]]:
    """`(total ink, {claim family: (ink held, [stroke ordinals])})` of ONE box.

    `strokes`: `(ordinal, share of the stroke inside the box, the stroke's ink, owner state, owner family)` for every stroke with any ink inside
    the box (covered and partial). Ink is the stroke's own ink times the share inside the box, in whatever unit the caller uses for all strokes.
    A stroke counts as held only where the owner DECIDED it (state decided or merged) for a claim family other than the box's own."""
    fams = frozenset(claim_families)
    total = 0.0
    by: Dict[str, Tuple[float, List[int]]] = {}
    for o, share, ink, state, fam in strokes:
        if ink is None or ink <= 0 or share <= 0:
            continue
        w = float(ink) * float(share)
        total += w
        if state in ("decided", "merged") and fam in fams and fam != own_family:
            ink0, ords = by.get(fam, (0.0, []))
            by[fam] = (ink0 + w, ords + [int(o)])
    return total, by


def dominant(total: float, by: Dict[str, Tuple[float, List[int]]]) -> Optional[Tuple[str, float, List[int]]]:
    """The claim family holding the most of the box's ink, with its share, or None. Ties break by family name (deterministic)."""
    if total <= 0 or not by:
        return None
    fam = sorted(by, key=lambda f: (-by[f][0], f))[0]
    return fam, by[fam][0] / total, sorted(by[fam][1])


def held_boxes(boxes: Iterable[Tuple[str, str, Iterable[Tuple[int, float, float, str, Optional[str]]]]],
               claim_families: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """`{box key: {"by", "share", "ink", "strokes", "also"}}` for every box held at least `NEAR_MIN` by ONE claim family. `boxes`: `(key, family,
    strokes)`. `also` lists the other families that hold some of it (a box on a barline and a bracket)."""
    fams = frozenset(claim_families)
    out: Dict[str, Dict[str, Any]] = {}
    for key, family, strokes in boxes:
        if family not in BOX_FAMILIES:
            continue
        total, by = held_share(strokes, family, fams)
        top = dominant(total, by)
        if top is None or top[1] < NEAR_MIN:
            continue
        f, share, ords = top
        out[key] = {"by": f, "share": round(share, 3), "ink": round(total, 1), "strokes": ords,
                    "also": sorted(x for x in by if x != f)}
    return out


# ── copies by position: ONE mark per head's ink ───────────────────────────────────────────────────────────────────────────────────────────
def marks(owned_by_head: Iterable[Sequence[str]]) -> Dict[str, str]:
    """`{box key: mark id}` for every head box that shares a head-owned stroke with another box. `owned_by_head`: for each stroke a HEAD owns, the
    claim keys that own it (a MERGED stroke lists several boxes). Union-find; the mark id is the smallest key of the group (deterministic). A box
    alone on its ink is not listed: it is its own mark."""
    parent: Dict[str, str] = {}

    def find(a: str) -> str:
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for keys in owned_by_head:
        ks = [str(k) for k in keys]
        for k in ks:
            find(k)
        for k in ks[1:]:
            ra, rb = find(ks[0]), find(k)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    groups: Dict[str, List[str]] = {}
    for k in list(parent):
        groups.setdefault(find(k), []).append(k)
    return {k: root for root, ks in groups.items() if len(ks) > 1 for k in ks}


# ── what a decider is told ────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def refusal_kind(by: str) -> str:
    """The `<kind>` of `claimed_by:<kind>` for the claim family `by`. The deciders hold a fixed vocabulary of literals (the vocabulary check reads them): `barline`;
    any other family is the generic `page_claim`, so a claim layer a later lane files (a tremolo slash) is consumed with no code here."""
    return "barline" if by == "barline" else "page_claim"


# ── the derived check (CLAUDE rule 7: it must be able to fail) ─────────────────────────────────────────────────────────────────────────────
#: the precision deciders that refuse a head / a rest, and the file each lives in (relative to `staged/`)
CONSUMER_DECIDERS = {"notehead": "adjudicators/notehead_precision.py", "rest": "adjudicators/family_precision.py"}
_OWNER_TOKENS = {"OWNER_METER": "meter", "OWNER_KEY": "key_signature", "OWNER_CLEF": "clef", "OWNER_BRACKET": "bracket", "OWNER_WORD": "word",
                 "OWNER_COLUMN": "leading_column"}


def static_wiring(staged_dir: Optional[Any] = None) -> List[Dict[str, str]]:
    """Every (claim family, deciding reader) pair where a claim the register files is neither consulted by `claimed_by.consult` nor refused by the generic consult
    in this reader, as `{claim, reader, why}`. Reads SOURCE TEXT under `staged_dir` (default: this tree), so it can be pointed at another tree -- a `git archive` of
    main -- and must FIND the barline / arc / hairpin cases there. A family that `MARK_ONLY` keeps from refusing is a finding too, with its reason: marked, by
    decision, not consulted."""
    import pathlib
    import re
    root = pathlib.Path(staged_dir) if staged_dir else pathlib.Path(__file__).resolve().parent
    so = (root / "stroke_owner.py").read_text()
    m = re.search(r"TIERS[^=]*=\s*\(\s*\(([^)]*)\)", so)
    filed = [x.strip().strip("\"'") for x in re.sub(r"#[^\n]*", "", m.group(1) if m else "").split(",") if x.strip().strip("\"'")]
    cb = (root / "adjudicators" / "claimed_by.py").read_text()
    mo = re.search(r"_ORDER\s*=\s*\(([^)]*)\)", cb)
    consulted = {_OWNER_TOKENS[t.strip().split(".")[-1]] for t in (mo.group(1) if mo else "").split(",") if t.strip().split(".")[-1] in _OWNER_TOKENS}
    mark_only: set = set()
    cf = root / "claim_final.py"
    if cf.exists():
        mm = re.search(r"MARK_ONLY\s*=\s*frozenset\(\{([^}]*)\}\)", cf.read_text())
        mark_only = {x.strip().strip("\"'") for x in (mm.group(1) if mm else "").split(",") if x.strip()}
    generic = {rd: "_claim_final.finding(" in (root / rel).read_text() for rd, rel in CONSUMER_DECIDERS.items()}
    out: List[Dict[str, str]] = []
    for fam in filed:
        if fam in consulted:
            continue
        for rd in CONSUMER_DECIDERS:
            if not generic[rd]:
                out.append({"claim": fam, "reader": rd, "why": "filed and owned, no reader consults it (marks only)"})
            elif fam in mark_only:
                out.append({"claim": fam, "reader": rd, "why": "consulted generically but MARK_ONLY by decision (the claim over-reaches onto head ink)"})
    return out


def survivors(boxes: Iterable[Tuple[str, str, Iterable[Tuple[int, float, float, str, Optional[str]]], bool]],
              claim_families: Iterable[str], cut: float = CUT) -> List[Dict[str, Any]]:
    """The record-level check: boxes (`key, family, strokes, refused`) that are NOT refused although at least `cut` of their own ink is held by a claim that is not
    consulted elsewhere and not MARK_ONLY. Zero on a tree where claimed ink is final; the census cases on a tree where it is not."""
    out = []
    for key, family, strokes, refused in boxes:
        if refused or family not in BOX_FAMILIES:
            continue
        total, by = held_share(strokes, family, claim_families)
        top = dominant(total, {f: v for f, v in by.items() if f not in CONSULTED_ELSEWHERE and f not in MARK_ONLY})
        if top is not None and top[1] >= cut:
            out.append({"box": key, "family": family, "by": top[0], "share": round(top[1], 3)})
    return out


def double_marks(marks_of: Dict[str, str], written: Iterable[str]) -> List[Tuple[str, List[str]]]:
    """Marks (copies by position) with more than one box WRITTEN: one head's ink counted twice in the file."""
    g: Dict[str, List[str]] = {}
    for k in written:
        if k in marks_of:
            g.setdefault(marks_of[k], []).append(k)
    return sorted((m, ks) for m, ks in g.items() if len(ks) > 1)


def distinct_heads(head_boxes: Iterable[str], marks_of: Dict[str, str]) -> int:
    """Heads counted by distinct ink: a box in a mark counts as its mark, once."""
    return len({marks_of.get(k, k) for k in head_boxes})


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="2.277 derived check: python3 -m tools.omr.staged.claim_final static [--root DIR]")
    ap.add_argument("what", choices=["static"])
    ap.add_argument("--root", default=None, help="a staged/ directory (e.g. a `git archive` of main)")
    a = ap.parse_args()
    f = static_wiring(a.root)
    print(json.dumps(f, indent=1))
    print("open: %d" % len(f))
