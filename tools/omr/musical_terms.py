"""Look up a printed string in the Gradus musical terms library (ROADMAP 2.67).

The library is a COPY of Gradus's `exports/musical-terms.json` (gradus-vercel,
`npm run export:terms`), held at `data/musical-terms/musical-terms.json`. Its
header names the Gradus commit it was generated from (`generated_from`). To
refresh it, regenerate the export on the Gradus side and copy the file over;
nothing here edits it.

Each entry is a term as engravers print it (`Allegro`, `Generalpause`,
`Kontrafagott`) with its language, category, printed abbreviations (`G.P.`)
and spelling variants. The export is prose-free: no definitions.

**Read by nothing yet.** This is a lookup table, not a reader. Wiring it into
`direction_lexicon` or `instruments` is the second half of 2.67 and changes
what GATHER accepts, so it waits for Sean.

**Exact match only**, after the folding the export documents (its "Matching
guidance"): case, accents and `ß` folded, and periods, spaces, hyphens and
apostrophes ignored, so `piu` = `più`, `m. g.` = `m.g.`, `Ritard.` = `ritard`.
No fuzzy matching, no stripping of part numbers -- a caller that wants
`Cor. II` looked up as `Cor.` strips the numeral itself.

**Ambiguity is kept.** A string printed for two things (`rit.` = ritardando or
ritenuto, `tr` = trill or trumpet, `Cor.` in Italian and French) returns every
candidate. Choosing between them needs context this table does not have.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

LIBRARY_PATH = (Path(__file__).resolve().parents[2]
                / "data" / "musical-terms" / "musical-terms.json")

_IGNORED = re.compile(r"[.\s\-'’]+")


@dataclass(frozen=True)
class Term:
    id: str
    term: str
    language: str
    category: str
    printed_in_scores: bool
    instrument: bool
    abbreviations: tuple[str, ...]
    variants: tuple[str, ...]
    related_terms: tuple[str, ...]


@dataclass(frozen=True)
class Match:
    term: Term
    matched: str   # the library string that matched, as printed
    via: str       # "term" | "abbreviation" | "variant"


def fold(text: str) -> str:
    """The key two strings must share to match."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _IGNORED.sub("", stripped.casefold())


@lru_cache(maxsize=1)
def library() -> dict:
    """The export as written: `generated_from`, `data_dirty`, `counts`, `terms`."""
    with open(LIBRARY_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def terms() -> tuple[Term, ...]:
    return tuple(
        Term(
            id=row["id"],
            term=row["term"],
            language=row["language"],
            category=row["category"],
            printed_in_scores=row["printedInScores"],
            instrument=row["instrument"],
            abbreviations=tuple(row.get("abbreviations", ())),
            variants=tuple(row.get("variants", ())),
            related_terms=tuple(row.get("relatedTerms", ())),
        )
        for row in library()["terms"]
    )


@lru_cache(maxsize=1)
def _index() -> dict[str, tuple[Match, ...]]:
    index: dict[str, list[Match]] = {}
    for t in terms():
        forms = ([(t.term, "term")]
                 + [(a, "abbreviation") for a in t.abbreviations]
                 + [(v, "variant") for v in t.variants])
        seen: set[str] = set()
        for printed, via in forms:
            key = fold(printed)
            if not key or key in seen:
                continue
            seen.add(key)
            index.setdefault(key, []).append(Match(t, printed, via))
    return {k: tuple(v) for k, v in index.items()}


def lookup(text: str) -> tuple[Match, ...]:
    """Every entry `text` is printed for; empty when it is not in the library."""
    key = fold(text)
    if not key:
        return ()
    return _index().get(key, ())


def by_id(term_id: str) -> Term | None:
    for t in terms():
        if t.id == term_id:
            return t
    return None
