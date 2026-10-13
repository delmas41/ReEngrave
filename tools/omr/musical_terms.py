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


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.67b: which languages a work's directions may be in
# ─────────────────────────────────────────────────────────────────────────────

COMPOSER_LANGUAGES_PATH = LIBRARY_PATH.with_name("composer-languages.json")

#: Accepted for EVERY work: Italian is the lingua franca of directions in this
#: repertoire (95-100% of the printed words of most composers in the reference
#: encodings), and the Latin entries (`ad lib.`, `tacet`) are printed by all.
ALWAYS = frozenset({"Italian", "Latin"})


@lru_cache(maxsize=1)
def _composer_table() -> dict[str, tuple[str, ...]]:
    with open(COMPOSER_LANGUAGES_PATH, encoding="utf-8") as fh:
        return {k: tuple(v) for k, v in json.load(fh)["languages"].items()}


def composer_of(work_id: str | None) -> str | None:
    """`mahler--symphony-5` -> `mahler`; None for no work id."""
    if not work_id:
        return None
    return str(work_id).split("--", 1)[0] or None


def composer_languages(work_id: str | None) -> tuple[str, ...] | None:
    """The composer's own direction language(s) besides Italian, from the
    committed table; `()` for Italian-only; None when the composer is UNKNOWN
    (no work id, or a composer the table does not list)."""
    composer = composer_of(work_id)
    if composer is None:
        return None
    return _composer_table().get(composer)


_LABEL_TAIL = re.compile(
    r"^(?:in|en|aus|[ivx]+\.?|\d+\.?|[a-h](?:es|is|s)?\.?|[a-h][#b♭♯]?)$",
    re.IGNORECASE)


def label_language(text: str) -> str | None:
    """The ONE language an instrument label is printed in, or None.

    `Flöte` -> German, `Flûte` -> French, `Flauto` -> Italian; `Fl.` (printed
    the same in three languages), `Oboe` (one entry for several languages) and
    an unknown string -> None. A trailing key or part number (`Hörner in F`,
    `Cor. II`) is dropped before the lookup, never matched."""
    tokens = str(text).split()
    while tokens and _LABEL_TAIL.match(tokens[-1]):
        tokens.pop()
    while tokens:
        hits = [m for m in lookup(" ".join(tokens)) if m.term.instrument]
        if hits:
            langs = {m.term.language for m in hits}
            return langs.pop() if len(langs) == 1 else None
        tokens.pop()
    return None


def edition_languages(label_texts, *, min_labels: int = 2) -> tuple[str, ...]:
    """Languages the EDITION prints its instrument labels in, besides Italian:
    a language counts once at least `min_labels` DISTINCT labels name it on
    their own (one label is a stray, or a misread). Sean 2026-10-12: a German
    edition of Tchaikovsky prints German words (`Flöte`, `Vorbereiten`)."""
    seen: dict[str, set[str]] = {}
    for text in label_texts:
        lang = label_language(text)
        if lang and lang not in ALWAYS:
            seen.setdefault(lang, set()).add(fold(text))
    return tuple(sorted(l for l, s in seen.items() if len(s) >= min_labels))


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.67b: where a term is printed
# ─────────────────────────────────────────────────────────────────────────────

#: The instrument families a technique word is printed for, by library id.
#: CONVENTION (Sean 2026-10-12, "yes"): checked against the reference
#: encodings (pizz./arco/div./geteilt/gestrichen/G-Saite only ever on strings,
#: offen/gestopft only on brass, m.g./m.d./l.H./una corda/Ped. only on
#: keyboard, a2/a3/zu 2 on winds and brass 99%). Families are
#: `instruments.Instrument.family` (harp is `keyboard` there). A word not
#: listed is printed for any family. The mutes take keyboard and percussion
#: too: Beethoven's `senza sordino` is the piano's pedal, a timpani is muffled
#: `con sord.`.
_STRINGS = ("string",)
_BRASS = ("brass",)
_WINDS = ("woodwind", "brass")
_KEYS = ("keyboard",)
_MUTES = ("string", "brass", "keyboard", "percussion")
_PERC = ("percussion",)
FAMILY_OF: dict[str, tuple[str, ...]] = {
    **dict.fromkeys((
        "pizzicato", "pizzicato-sempre", "arco", "col-arco", "col-legno",
        "col-legno-battuto", "col-legno-tratto", "sul-ponticello",
        "poco-sul-ponticello", "sul-tasto", "spiccato", "flautando",
        "ricochet", "saltando", "sur-la-touche", "sur-le-chevalet",
        "griffbrett", "divisi", "divided", "geteilt", "nicht-geteilt",
        "non-divisi", "gestrichen", "gezogen", "breit-gestrichen",
        "kurz-gestrichen", "lang-gestrichen", "g-saite", "d-saite", "a-saite",
        "c-saite", "e-saite", "sul-sol", "sul-re", "sul-la", "sul-mi",
        "sul-do", "al-tallone", "au-talon", "alla-punta", "punta-d-arco",
        "archet", "avec-l-archet", "mit-bogen", "bogen", "viel-bogen",
        "viel-bogen-wechseln", "wenig-bogen", "strich", "strich-fur-strich",
        "breiter-strich", "down-bow", "up-bow"), _STRINGS),
    **dict.fromkeys((
        "gestopft", "bouche", "cuivre", "offen", "stopped", "chiuso"),
        _BRASS),
    **dict.fromkeys((
        "a-due", "a-tre", "a-quattro", "zu-2", "schalltrichter-auf",
        "schalltrichter-ab", "pavillon-en-l-air", "campana-in-aria",
        "bell-up", "flutter-tongue", "frullato"), _WINDS),
    **dict.fromkeys((
        "con-sordino", "senza-sordino", "sordino", "mute", "with-mute",
        "without-mute", "dampfer", "dampfer-ab", "dampfer-absetzen",
        "dampfer-auf", "ohne-dampfer", "gedampft", "avec-sourdine",
        "sans-sourdine", "mettez-les-sourdines", "otez-les-sourdines",
        "enlevez-la-sourdine", "alzate-sordini", "via-sordini"), _MUTES),
    **dict.fromkeys((
        "una-corda", "tre-corde", "due-corde", "trois-cordes", "une-corde",
        "tutte-le-corde", "sempre-una-corda", "con-pedale", "senza-pedale",
        "pedale", "pedal-en", "pedale-fr", "pedal-down", "sans-pedale",
        "avec-pedale", "ohne-pedal", "con-due-pedali", "with-both-pedals",
        "mit-verschiebung", "ohne-verschiebung", "main-gauche",
        "main-droite", "mano-destra", "mano-sinistra", "left-hand",
        "right-hand", "linke-hand", "rechte-hand", "colla-destra",
        "colla-sinistra", "manuale", "full-organ", "organ-pedal"), _KEYS),
    **dict.fromkeys((
        "bacchette-di-legno", "bacchette-di-spugna", "bacchette-di-timpani",
        "baguettes-d-eponge", "baguettes-de-bois", "baguettes-de-timbales",
        "schlagel", "filzschlagel", "holzschlagel", "schwammschlagel",
        "felt-sticks", "wooden-sticks", "brushes", "con-spazzole",
        "side-stick", "soft-felt-striker", "with-metal-striker",
        "becken-freihangend", "mit-tellern"), _PERC),
}

#: The tempo words that head a movement or a section: printed above the
#: system and repeated either above the first string staff (Sean 2026-10-12,
#: "yes") or under the system's last staff (the print: Breitkopf Brahms 1 p3,
#: `Allegro` at bar 38 under the K.-B.), never under any other staff. A library tempo entry is a HEADING when its
#: first word is one of these (`Allegro con brio`, `Sehr langsam` is not --
#: `sehr` is not here, and that is the conservative side: a word that is not
#: a heading is never held back for its place).
HEADING_FIRST_WORDS = frozenset(fold(w) for w in """
    grave largo larghetto lento adagio adagietto andante andantino moderato
    allegretto allegro vivace vivacissimo vivo presto prestissimo maestoso
    langsam mässig lebhaft schnell rasch lent modéré vif vite
""".split())

#: Form words (`Trio`, `Coda`, `Variation`) are headings too; the ones that
#: steer a performer around the score are printed at a bar on every staff as
#: often as above the system, and are not limited.
NAVIGATION = frozenset({
    "al-fine", "al-segno", "anfang", "bis", "da-capo", "da-capo-al-coda",
    "da-capo-al-fine", "dal-segno", "dal-segno-al-coda", "dal-segno-al-fine",
    "end-en", "ende", "erstes-mal", "fin-fr", "fine", "first-time",
    "hohepunkt", "last-time", "pour-finir", "prima-volta", "repeat",
    "replica", "second-time", "seconda-volta", "segno", "senza-replica",
    "to-coda", "zum-schluss", "zweites-mal",
})


def is_heading(term: Term) -> bool:
    if term.category == "form":
        return term.id not in NAVIGATION
    if term.category != "tempo":
        return False
    first = term.term.split()[0] if term.term.split() else ""
    return fold(first) in HEADING_FIRST_WORDS
