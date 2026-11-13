"""ROADMAP 2.307 T1d -- READERS GET MARKS BY OWNER (flag `OMR_PAGE_OWNED_VIEW`, default OFF). STAGED. A TEST PROTOTYPE, not a build.

Sean 2026-11-13 (plan `docs/plan-2026-11-13-page-and-zoom.md` §4 A): "a view is how we look, the page is where facts live, a view's edge is
never evidence". A padded measure cell shows a neighbour staff's head too; once `Q.GLYPH_OWNER` has decided that a glyph's owner is ANOTHER
staff (`adjudicate.is_relocated_copy`: by the decision's domain its twin stands on that staff), the glyph is a COPY of a mark another cell
holds. With the flag ON, ONE rule (`copy_keys`) names those copies once, right after ownership is decided, and from then on no reader that
LISTS marks -- a region query (`Scope.SELF_AND_DESCENDANTS`), `Log.subjects`, `Log.all_rows` / `all_verdicts` (every decision's domain) in
ADJUDICATE / EVALUATE / INFER, and `export.Record.obs_of` / `verdicts_of` / `observations` in EXPORT -- is handed one. A question asked of the
copy BY NAME (`Scope.EXACT`, `Record.verdict`) still answers, so nothing about it is erased from the record.

TWO DOORS, ONE RULE, and why one place is impossible: ADJUDICATE, EVALUATE and INFER share one in-memory `record.Log`; EXPORT reads the
SERIALISED record through its own index (`export.Record`), built from JSON with no Log behind it. The same `copy_keys` rule is applied at
both, over the same `Q.GLYPH_OWNER` verdicts, so they cannot disagree.

NOT DONE: `OMR_RELOCATE_AT_EXPORT` (default OFF) moves a copy whose owner holds no twin; with this flag ON such a copy is hidden and never
relocated. A copy whose owner verdict is not DECIDED is not a copy here (the rule is EXPORT's own drop test).
"""
from __future__ import annotations

import os
from typing import Any, Iterable, Set

ENV = "OMR_PAGE_OWNED_VIEW"


def enabled() -> bool:
    """`OMR_PAGE_OWNED_VIEW` -- default OFF, an allow-list (a typo leaves it off)."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _is_copy(subject_key: str, owner: Any) -> bool:
    from .adjudicate import is_relocated_copy
    return is_relocated_copy(subject_key, owner)


def copy_keys_of_log(log: Any) -> Set[str]:
    """Glyph subject keys whose CURRENT `Q.GLYPH_OWNER` verdict is DECIDED and names another staff."""
    from .record import Q
    out: Set[str] = set()
    seen: Set[str] = set()
    for v in log.all_verdicts():
        if v.quantity != Q.GLYPH_OWNER:
            continue
        k = v.subject.to_key()
        if k in seen:
            continue
        seen.add(k)
        cur = log.verdict(Q.GLYPH_OWNER, v.subject)
        if cur is None or getattr(cur.outcome, "value", cur.outcome) != "decided":
            continue
        if _is_copy(k, cur.value):
            out.add(k)
    return out


def copy_keys_of_verdicts(standing: Iterable[Any]) -> Set[str]:
    """The same rule over EXPORT's standing verdict dicts (`export.Record._v.values()`)."""
    from .record import Q
    return {v["subject"] for v in standing
            if v.get("quantity") == Q.GLYPH_OWNER and v.get("outcome") == "decided" and _is_copy(v["subject"], v.get("value"))}


def apply_to_log(log: Any) -> int:
    """Called ONCE, right after `Q.GLYPH_OWNER` is decided. Returns how many copies are hidden from listing readers."""
    if not enabled():
        return 0
    keys = copy_keys_of_log(log)
    log.hide_from_listing(keys)
    return len(keys)
