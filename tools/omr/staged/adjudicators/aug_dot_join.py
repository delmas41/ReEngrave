"""ROADMAP 2.127 -- a dot that was SEEN beside a note must not leave that note
written plain and unmarked (STAGED ADJUDICATE, `OMR_AUG_DOT_JOIN`, default ON).

WHAT THE BRAHMS RECORD SAID, AND WHAT IT WAS. `augmentation_decided_but_
unattached` counted 1,108 dots DECIDED augmentation that reach no duration, and
2.124 guessed "~390 of them beside a decided note: dotted notes written
undotted". `benchmarks/omr-aug-dots-2026-10/FINDINGS.md` takes the 1,108 apart:
555 name a ghost head another staff owns, 377 are the same physical dot a head
already carries from its OWN cell, 149 sit beside a note whose duration is not
decided (so the note is not written), and **16** sit beside a note whose
duration IS decided with no dot -- 8 of those a flag's curl boxed as a dot
(Brahms `1/0/5/1/14`, the neighbouring staff's flag tip in this strip's pad).
The second population is the dot the role decision never placed
(`dot_role_ambiguous`, ~65 beside a decided-plain head): 4 of Sean's 7 such
dots on page 0 of Brahms 317803 are dotted halves and quarters written plain.

THE RULE (CLAUDE.md §4, rule 8). A decided plain duration beside dot ink that
was SEEN and never placed is not "plain", it is "cannot tell". This module
does NOT lengthen the note: a flag's curl, a staccato of the next staff and a
real dot are one box to the geometry (the box sits level with the head in all
three), so lengthening would let a guess in. It NARROWS the note to
{as read, dotted} -- the reader's own two candidates, equal support, the order
claims nothing -- and INFER's existing bar collapse may then choose and label
it blue. A dot whose centre lies inside a DETECTED flag box is the flag's own
tip and narrows nothing.

CONNECT, NEVER GUESS: it reads the dot's DECIDED role (`Q.DOT_ROLE`) and the
head's live `Q.DURATION` and supersedes the latter with a narrowed verdict.
"""
from __future__ import annotations

import os
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .. import record as R
from ..record import Kind, Outcome, Q, Scope

AUG_DOT_JOIN_ENV = "OMR_AUG_DOT_JOIN"


def aug_dot_join_enabled() -> bool:
    """DEFAULT ON (Sean, 2026-10-14: "Yes"): an explicit `0`/`false`/`no`/`off`
    turns it off."""
    return os.environ.get(AUG_DOT_JOIN_ENV, "").strip().lower() not in (
        "0", "false", "no", "off")


#: A dot with no decided role counts as "beside" a head when its left edge is
#: no more than this far right of the head's right edge, and no more than
#: `UNRESOLVED_MAX_DY_SPACES` above or below its centre. CONVENTION ASSUMED /
#: WHAT WOULD FALSIFY IT / NOT CONFIRMED: measured over Brahms
#: `overnight-20261013-night` (the role window itself is gap <= ~0.7 sp,
#: 0.75 above / 0.25 below; the 596 refused dots lie mostly in -0.75..-0.25
#: and 0.75..1.0, the two near-misses on Sean's page 0), so the window here
#: only has to include them. A cut-off is a measurement: Sean's tiles decide.
UNRESOLVED_MAX_GAP_SPACES = 1.2
UNRESOLVED_MIN_GAP_SPACES = -0.1
UNRESOLVED_MAX_DY_SPACES = 1.3

#: The role decision's own staccato window (`rhythm.STACCATO_*`), in spaces.
STACCATO_CENTRED_MAX_SPACES = 0.5
STACCATO_OFFSET_MIN_SPACES = 0.75
STACCATO_MAX_GAP_SPACES = 2.0

#: A dot's page box centre inside a flag glyph's page box is the flag's tip.
FLAG_CLASS_PREFIX = "flag"

NARROWED_REASON = "dot_seen_beside_a_plain_note"


def _box(log: R.Log, sub: R.Subject):
    """`(class, value, page bbox)` of a glyph's last `Q.GLYPH_BOX` row."""
    rows = log.rows(Q.GLYPH_BOX, sub)
    if not rows:
        return None
    r = rows[-1]
    v = r.value
    bb = (r.detail or {}).get("bbox_page_px")
    if not isinstance(v, (list, tuple)) or len(v) < 5 or not bb or len(bb) != 4:
        return None
    return str(v[0]), v, tuple(float(x) for x in bb), r


def _undotted_narrowing(v: Optional[R.Verdict]) -> bool:
    """A NARROWED note none of whose candidates carries a dot (Brahms
    `0/0/11/0/4`, `0/0/11/0/9`: candidates {eighth, quarter}, and INFER chose
    the plain quarter where Sean reads a DOTTED quarter)."""
    return (v is not None and v.outcome is Outcome.NARROWED
            and bool(v.candidates)
            and all(isinstance(c.value, dict) and not c.value.get("is_rest")
                    and c.value.get("dots") == 0 for c in v.candidates))


def _plain_note(v: Optional[R.Verdict]) -> bool:
    return (v is not None and v.outcome is Outcome.DECIDED
            and isinstance(v.value, dict) and not v.value.get("is_rest")
            and v.value.get("dots") == 0)


def _dotted_candidate(value: Dict[str, Any]) -> Dict[str, Any]:
    """The same note with one dot: every length scaled by 1.5."""
    out = dict(value)
    out["dots"] = 1
    for k in ("beats", "written"):
        if isinstance(value.get(k), (int, float)):
            out[k] = value[k] * 1.5
    return out


def reconcile_unjoined_dots(log: R.Log) -> Dict[str, int]:
    """Narrow every decided-plain note that has a dot seen beside it.

    Run after `Q.DURATION`. `{}` when `OMR_AUG_DOT_JOIN` is switched off. Returns the
    census (also what the tests read): `narrowed_decided_dot_named_this_head`,
    `narrowed_unplaced_dot_beside_this_head`, `dot_is_a_flag_tip`,
    `head_already_dotted_or_not_a_decided_note`, `no_head_beside_the_dot`.
    """
    if not aug_dot_join_enabled():
        return {}
    census: Counter = Counter()

    # --- page index: flag boxes, and every live non-refused notehead --------
    flags: Dict[Tuple[int, int], List[Tuple[float, float, float, float]]] = \
        defaultdict(list)
    heads: Dict[Tuple[int, int], List[Tuple[str, Tuple[float, ...]]]] = \
        defaultdict(list)
    dots: List[Tuple[R.Subject, R.Verdict]] = []
    for sub in log.subjects(Kind.GLYPH):
        role = log.verdict(Q.DOT_ROLE, sub)
        if role is not None:
            dots.append((sub, role))
        b = _box(log, sub)
        if b is None:
            continue
        cls, _v, bb, _r = b
        if cls.startswith(FLAG_CLASS_PREFIX):
            flags[(sub.page, sub.system)].append(bb)
        elif cls.startswith("notehead"):
            refused = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
            if refused is not None and refused.outcome is Outcome.DECIDED \
                    and refused.value is True:
                continue
            heads[(sub.page, sub.system)].append((sub.to_key(), bb))

    # head key -> (dot subject, kind) first claim wins, one narrowing per head
    claims: Dict[str, Tuple[R.Subject, R.Verdict, str]] = {}
    for dsub, role in dots:
        named = (role.detail or {}).get("head")
        if role.outcome is Outcome.DECIDED and role.value == "augmentation":
            if not named:
                continue
            kind = "narrowed_decided_dot_named_this_head"
            target = named
        elif role.outcome is Outcome.ABSTAINED \
                and role.reason == "dot_role_ambiguous":
            target = None
            kind = "narrowed_unplaced_dot_beside_this_head"
        else:
            continue
        db = _box(log, dsub)
        if db is None:
            continue
        _c, dval, dpb, _drow = db
        # a flag's own curl is not a dot
        cx, cy = (dpb[0] + dpb[2]) / 2.0, (dpb[1] + dpb[3]) / 2.0
        if any(f[0] <= cx <= f[2] and f[1] <= cy <= f[3]
               for f in flags[(dsub.page, dsub.system)]):
            census["dot_is_a_flag_tip"] += 1
            continue
        if target is None:
            cell = dsub.at(Kind.CELL)
            sp = log.rows(Q.CELL_STAFF_SPACE, cell,
                          scope=Scope.SELF_AND_ANCESTORS)
            if not sp or not dval[3]:
                continue
            k = (dpb[2] - dpb[0]) / float(dval[3])   # page px per cell px
            space = float(sp[-1].value) * k
            if space <= 0:
                continue
            # a mark centred over some OTHER head, above or below it, is that
            # head's staccato (the role decision's own staccato window)
            if any(abs(cx - (hb[0] + hb[2]) / 2.0) <= STACCATO_CENTRED_MAX_SPACES
                   * space and STACCATO_OFFSET_MIN_SPACES * space
                   <= abs((hb[1] + hb[3]) / 2.0 - cy) <= STACCATO_MAX_GAP_SPACES
                   * space for _k, hb in heads[(dsub.page, dsub.system)]):
                census["staccato_like_over_another_head"] += 1
                continue
            best, best_score = None, float("inf")
            for key, hb in heads[(dsub.page, dsub.system)]:
                gap = (dpb[0] - hb[2]) / space
                dy = ((hb[1] + hb[3]) / 2.0 - cy) / space
                if gap < UNRESOLVED_MIN_GAP_SPACES \
                        or gap > UNRESOLVED_MAX_GAP_SPACES \
                        or abs(dy) > UNRESOLVED_MAX_DY_SPACES:
                    continue
                score = gap + 2.0 * abs(dy)
                if score < best_score:
                    best, best_score = key, score
            if best is None:
                census["no_head_beside_the_dot"] += 1
                continue
            target = best
        claims.setdefault(target, (dsub, role, kind))

    for head_key, (dsub, role, kind) in claims.items():
        hsub = R.Subject.from_key(head_key)
        hv = log.verdict(Q.DURATION, hsub)
        if _undotted_narrowing(hv):
            # the reader's own candidates plus each one with a dot, in the
            # reader's order and support; nothing is chosen here
            cands = list(hv.candidates) + [
                R.Candidate(value=_dotted_candidate(dict(c.value)),
                            support=c.support) for c in hv.candidates]
            basis = tuple(x for x in (hv.id, role.id) if x)
            log.record(R.Verdict(
                id=log._next_id("vrd"), subject=hsub, quantity=Q.DURATION,
                outcome=Outcome.NARROWED, value=None,
                decider="reconcile_unjoined_dots",
                reason=NARROWED_REASON, considered=basis, basis=basis,
                used=tuple(hv.used or ()), candidates=tuple(cands),
                supersedes=hv.id,
                detail={"dot": dsub.to_key(), "dot_role": role.reason,
                        "dot_role_outcome": role.outcome.value,
                        "kind": kind, "was_reason": hv.reason,
                        "extended_narrowing": True}))
            census["extended_a_narrowing_with_dotted_candidates"] += 1
            continue
        if not _plain_note(hv):
            census["head_already_dotted_or_not_a_decided_note"] += 1
            continue
        arow = log.rows(Q.AUG_DOT, dsub)
        if arow and arow[-1].id in (hv.used or ()):
            census["already_joined"] += 1
            continue
        plain = dict(hv.value)
        basis = tuple(x for x in (hv.id, role.id) if x)
        out = R.Verdict(
            id=log._next_id("vrd"), subject=hsub, quantity=Q.DURATION,
            outcome=Outcome.NARROWED, value=None,
            decider="reconcile_unjoined_dots", reason=NARROWED_REASON,
            considered=basis, basis=basis, used=tuple(hv.used or ()),
            candidates=(R.Candidate(value=plain, support=1.0),
                        R.Candidate(value=_dotted_candidate(plain),
                                    support=1.0)),
            supersedes=hv.id,
            detail={"dot": dsub.to_key(), "dot_role": role.reason,
                    "dot_role_outcome": role.outcome.value,
                    "kind": kind, "was": plain})
        log.record(out)
        census[kind] += 1
    return dict(census)
