"""ROADMAP 4.2 -- movement boundaries: parsing, membership, and export split.

A whole work is several movements. A meter or a key carry must never cross a
movement boundary, and a multi-movement gather exports one MusicXML/LilyPond
file PER MOVEMENT rather than one file that silently treats the whole work
as a single continuous piece.

DESIGN DECISION (2026-09-28, recorded in docs/DECISIONS.md): a movement is a
MEMBERSHIP fact, not a new level in the `Subject` path. `record.Kind` and
`record.Subject` are UNCHANGED -- every existing subject id
(`glyph/p/s/st/c/g`) still means exactly what it meant, and a record with no
movement facts reads and exports exactly as it did before this module
existed (the plan's own text names `Kind.MOVEMENT`; inserting a level
between `DOCUMENT` and `PAGE` would change every subject id this repo has
ever saved a record under, including the three acceptance records adopted
2026-09-28, so the manager's call was membership over insertion). The fact
itself is filed as an ordinary Observation (`Q.MOVEMENT_SPANS`) on the
DOCUMENT subject, the same shape as `Q.ROSTER_ENTRY` / `Q.DOSSIER_FACT`: a
fact that is not read off THIS raster, supplied by a human (today the CLI's
`--movements`; a confirmed fact sheet field is future work), and admissible
for exactly that reason.

A SPAN is `{"number": int, "first_page": int, "first_system": int | None,
"last_page": int, "last_system": int | None}`. `first_system`/`last_system`
of `None` mean "from/through the start/end of that PAGE" -- the CLI syntax
never has to name a system count it cannot yet know (that count is decided
during GATHER/ADJUDICATE, after the CLI has already parsed `--movements`).
Spans are inclusive of both ends and must not overlap.

⚠️ NEITHER `movement_of` NOR `same_movement` GUESSES. A `(page, system)` in
the gap between two declared spans answers `None` / `False` rather than
"whichever neighbour is closer" -- CLAUDE.md rule 8: a carry that cannot
tell whether it has crossed a boundary must abstain, never assume it has
not.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .record import DOCUMENT, Kind, Q, Subject

#: `NUMBER:START-END`, comma separated. START/END are `PAGE` or `PAGE.SYSTEM`.
_SPAN_RE = re.compile(
    r"^\s*(?P<number>\d+)\s*:\s*"
    r"(?P<first_page>\d+)(?:\.(?P<first_system>\d+))?\s*-\s*"
    r"(?P<last_page>\d+)(?:\.(?P<last_system>\d+))?\s*$")


class MalformedMovementSpec(ValueError):
    """`--movements` did not parse. Always names the offending segment --
    CLAUDE.md rule 8 again: a bad spec must fail loudly, never fall back to
    "the whole document is one movement" behind the user's back."""


# ─────────────────────────────────────────────────────────────────────────────
# Parsing the CLI spec
# ─────────────────────────────────────────────────────────────────────────────


def parse_movement_spec(spec: str) -> Tuple[Dict[str, Any], ...]:
    """`"1:0-11,2:12.1-20"` -> spans, sorted by `number`.

    Raises `MalformedMovementSpec` naming the offending segment on a bad
    grammar, a movement number repeated, or an END before its own START, and
    on two movements' ranges overlapping.
    """
    if not spec or not spec.strip():
        raise MalformedMovementSpec("empty --movements spec")
    spans: List[Dict[str, Any]] = []
    seen_numbers = set()
    for segment in spec.split(","):
        segment = segment.strip()
        if not segment:
            raise MalformedMovementSpec(
                f"empty segment in --movements spec {spec!r}")
        m = _SPAN_RE.match(segment)
        if not m:
            raise MalformedMovementSpec(
                f"cannot parse movement segment {segment!r} (want "
                f"NUMBER:PAGE[.SYSTEM]-PAGE[.SYSTEM]) in --movements "
                f"spec {spec!r}")
        number = int(m.group("number"))
        if number in seen_numbers:
            raise MalformedMovementSpec(
                f"movement {number} repeated in --movements spec {spec!r}")
        seen_numbers.add(number)
        first_system = (None if m.group("first_system") is None
                        else int(m.group("first_system")))
        last_system = (None if m.group("last_system") is None
                       else int(m.group("last_system")))
        span = {"number": number,
               "first_page": int(m.group("first_page")),
               "first_system": first_system,
               "last_page": int(m.group("last_page")),
               "last_system": last_system}
        if _span_start(span) > _span_end(span):
            raise MalformedMovementSpec(
                f"movement {number} ends before it starts in segment "
                f"{segment!r} of --movements spec {spec!r}")
        spans.append(span)
    spans.sort(key=lambda s: s["number"])
    # ⚠️ OVERLAP, NOT JUST ORDER. Two spans naming an overlapping page/system
    # range would make `movement_of` answer whichever sorts first in the
    # list, silently -- a bad spec is refused rather than resolved by an
    # unstated tie-break.
    for a, b in zip(spans, spans[1:]):
        if _span_end(a) >= _span_start(b):
            raise MalformedMovementSpec(
                f"movements {a['number']} and {b['number']} overlap in "
                f"--movements spec {spec!r}")
    return tuple(spans)


def _span_start(span: Dict[str, Any]) -> Tuple[int, float]:
    fs = span.get("first_system")
    return (span["first_page"], 0 if fs is None else fs)


def _span_end(span: Dict[str, Any]) -> Tuple[int, float]:
    ls = span.get("last_system")
    return (span["last_page"], float("inf") if ls is None else ls)


# ─────────────────────────────────────────────────────────────────────────────
# Membership -- the ONE question every carry asks
# ─────────────────────────────────────────────────────────────────────────────


def movement_of(spans: Sequence[Dict[str, Any]], page: Optional[int],
                system: Optional[int]) -> Optional[int]:
    """The movement NUMBER `(page, system)` falls in, or `None` if no
    declared span covers it. `system=None` (a PAGE-kind subject) is treated
    as that page's own first system for this purpose -- movement facts are
    keyed the same `(page, system)` way a key-signature majority is."""
    if not spans or page is None:
        return None
    here = (page, 0 if system is None else system)
    for span in spans:
        if _span_start(span) <= here <= _span_end(span):
            return span["number"]
    return None


def same_movement(spans: Sequence[Dict[str, Any]], a: Subject,
                  b: Subject) -> bool:
    """True if `a` and `b` are provably in the SAME movement.

    ⚠️ WITH NO SPANS DECLARED THE WHOLE DOCUMENT IS ONE MOVEMENT, exactly as
    before this item -- a record with no `Q.MOVEMENT_SPANS` fact reads and
    carries byte-identically to one from a tree that never heard of
    movements.
    """
    if not spans:
        return True
    ma = movement_of(spans, a.page, a.system)
    mb = movement_of(spans, b.page, b.system)
    if ma is None or mb is None:
        return False
    return ma == mb


def movement_boundaries(spans: Sequence[Dict[str, Any]]
                        ) -> Tuple[Tuple[int, int], ...]:
    """The `(page, system)` each movement AFTER THE FIRST begins at -- the
    cut points a document-wide majority (`header.adjudicate_part_key`) must
    never tally across, on top of whatever cuts a corroborated key CHANGE
    already supplies. Empty with fewer than two spans -- one movement has no
    boundary to cut at, which is the single-movement default's own case."""
    if len(spans) < 2:
        return ()
    ordered = sorted(spans, key=lambda s: s["number"])
    return tuple(
        (s["first_page"], 0 if s["first_system"] is None else s["first_system"])
        for s in ordered[1:])


# ─────────────────────────────────────────────────────────────────────────────
# Reading the fact back -- from a loaded record file
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️ THERE IS NO `spans_from_evidence` HERE, DELIBERATELY. `inventory --check`
# and `wiring --check` both trace a decision's OWN reads by walking helpers
# DEFINED IN ITS OWN MODULE (`inventory._never_read`, `wiring._reads`) -- a
# call that crosses into a shared module like this one is invisible to
# either tool, and `Q.MOVEMENT_SPANS` would report as an inert, unreachable
# declaration on every decision that wants it even though the record it read
# calls _from_ this module. So each of `rhythm.py` / `header.py` reads its
# own `ev.rows(Q.MOVEMENT_SPANS, subject=record.DOCUMENT)` through a small
# same-module helper and hands the resulting SPANS (not the `Evidence`) to
# the pure functions below.


def spans_from_result(result: Dict[str, Any]) -> Tuple[Dict[str, Any], ...]:
    """The same fact, read back out of a LOADED record dict
    (`record_io.load_record`'s own shape) rather than off a live `Log` --
    what EXPORT uses, including on a record `--musicxml`/`--lilypond` loads
    from disk with no gather in this process at all."""
    doc_key = DOCUMENT.to_key()
    for o in (result.get("record") or {}).get("observations") or ():
        if o.get("quantity") == Q.MOVEMENT_SPANS and o.get("subject") == doc_key:
            return tuple(o.get("value") or ())
    return ()


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT-time split -- one filtered record per movement
# ─────────────────────────────────────────────────────────────────────────────


def split_result(result: Dict[str, Any], spans: Sequence[Dict[str, Any]]
                 ) -> List[Tuple[int, Dict[str, Any]]]:
    """One filtered `result` per span, in movement-NUMBER order.

    A row at `Kind.DOCUMENT` (the roster, the dossier, the movement spans
    themselves, ...) is a fact about the WHOLE work and travels into every
    movement's file unchanged; every finer row goes to the one movement
    whose span contains its `(page, system)` and is DROPPED from every
    other movement's file. A row inside NO declared span is dropped from
    every file -- CLAUDE.md rule 8: a page the spec never named is not
    silently assigned to its nearest neighbour.

    ⚠️ NEITHER `basis`/`used`/`considered`/`correlated` NOR `derived_from`
    is followed or repaired here. `export.Record` never dereferences them
    (it indexes purely by `(quantity, subject)`), so a verdict kept because
    its OWN subject is in this movement renders correctly even where one of
    those id lists names a row this filter dropped.
    """
    ordered = sorted(spans, key=lambda s: s["number"])
    rec = result.get("record") or {}
    all_obs = rec.get("observations") or ()
    all_abs = rec.get("abstentions") or ()
    all_vrd = rec.get("verdicts") or ()

    out: List[Tuple[int, Dict[str, Any]]] = []
    for span in ordered:
        number = span["number"]

        def _keep(row: Dict[str, Any]) -> bool:
            sub = Subject.from_key(row["subject"])
            if sub.kind is Kind.DOCUMENT:
                return True
            return movement_of((span,), sub.page, sub.system) == number

        obs = [o for o in all_obs if _keep(o)]
        abst = [a for a in all_abs if _keep(a)]
        vrd = [v for v in all_vrd if _keep(v)]
        sub_result = dict(result)
        sub_result["record"] = {
            "observations": obs, "abstentions": abst, "verdicts": vrd,
            "counts": {"observations": len(obs), "abstentions": len(abst),
                      "verdicts": len(vrd)},
        }
        out.append((number, sub_result))
    return out


def movement_path(base: "str | Path", number: int) -> Path:
    """`out.musicxml`, movement 2 -> `out-mvt2.musicxml`. Same directory,
    same suffix, so `--lilypond`/`--pdf` name their own movement files the
    same way `--musicxml` does."""
    p = Path(base)
    return p.with_name(f"{p.stem}-mvt{number}{p.suffix}")


def export_each(result: Dict[str, Any], spans: Sequence[Dict[str, Any]],
                base_path: "str | Path",
                exporter: Callable[[Dict[str, Any]],
                                   Tuple[str, Dict[str, Any]]]
                ) -> List[Tuple[int, Path, str, Dict[str, Any]]]:
    """Run `exporter` (`export.to_musicxml` or `lilypond.to_lilypond`) once
    per movement, writing `<base>-mvt<N><suffix>` and its own
    `.coverage.json` sidecar beside it -- the same sidecar convention
    `--musicxml`/`--lilypond` already use for a single-movement record.

    Returns `[(number, path, text, report), ...]` in movement order; writing
    the console report is the caller's job, exactly as it is for the
    single-movement path.
    """
    out: List[Tuple[int, Path, str, Dict[str, Any]]] = []
    for number, sub_result in split_result(result, spans):
        text, report = exporter(sub_result)
        path = movement_path(base_path, number)
        path.write_text(text)
        cov = Path(str(path) + ".coverage.json")
        cov.write_text(json.dumps(report, indent=2, default=str))
        out.append((number, path, text, report))
    return out
