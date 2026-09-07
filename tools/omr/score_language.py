"""The language a score is PRINTED IN, voted from its own unambiguous labels.

## The gap this closes

`instruments.py` holds every spelling of an instrument in one flat bag:

    Timpani: ("timpani", "timpano", "tympani", "pauken", "timbales",
              "kettledrum", "timp", "tmp", "pk", "tp")

Italian, German, French and English together. Language appears in that file
only in COMMENTS — never in data, never in logic — so an ambiguous
abbreviation is settled by whichever reading is commoner across the whole
corpus, frozen identically for every document (`_DECLARED_AMBIGUOUS_ALIASES`).

A score is not the corpus. It is one printing, by one publisher, in one
tradition, and it says so in every unambiguous label it prints:

    Litolff    Flauti / Oboi / Clarinetti / Fagotti / Corni / Trombe / Timpani
    Breitkopf  Floten / Oboen / Klarinetten / Fagotte / Horner / Trompeten / Pauken

## The inference is an EXCLUSION, not a preference

Not *"this looks German so prefer German readings"* — that is a popularity
contest with a smaller population. The usable form is:

> **If a score labels its timpani `Pk.`, then `Tp.` on that same score cannot
> be the timpani, because a score does not name one instrument in two
> languages.**

⚠️ **It has to be two LANGUAGES, and the corpus says so.** The naive exclusion
— *"this instrument is already named elsewhere, so this alias is something
else"* — is FALSIFIED by the first document it meets: Beethoven 5 / Litolff
prints `Timpani in C.G.` on its opening page and `Tp.` on the pages after it.
Same instrument, same language, two lengths of the same word. What excludes is
a rival SPELLING FROM ANOTHER TRADITION, which is exactly what the language
reading detects.

## What this module is, and is not

It is a **reader of documents**, not an extension of the lexicon. Nothing here
edits `instruments.INSTRUMENTS` or `instruments.AMBIGUOUS_ALIASES`; per-language
alias lists inside the lexicon would fragment the one table every consumer
reads. The tagging lives beside it, keyed on the aliases the lexicon already
has, and `test_score_language.py` fails if any spelling here stops being one.

⚠️ **It ABSTAINS far more than it fires, on purpose.** Three of the ambiguous
alias families the corpus exercises are undecidable BY LANGUAGE and are left
alone:

* `basso` / `basse` / `bassi` — the bass VOICE and the double basses are the
  same word in Italian, French and English alike. Language separates nothing,
  and Handel's Messiah prints `BASSO` (the voice) and `Bassi` (the strings) on
  one page. Score order settles this; language must not touch it.
* `tr bas` — `Trombone basso` and `Tromba bassa` are both Italian.
* `cor` — Horn in French and the standard Italian abbreviation of `Corni`
  alike, so no reading of the document changes the answer.

That leaves the families where the two candidates come from two traditions,
which is where a language reading is evidence rather than decoration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Sequence

from tools.omr import instruments as _instruments

#: The traditions an orchestral margin is printed in. `en` covers the modern
#: Anglo-American engraving convention, which is a real fourth tradition and
#: not a fallback.
LANGUAGES: tuple[str, ...] = ("it", "de", "fr", "en")


# ── which spellings belong to which tradition ────────────────────────────────
#
# ONLY DIAGNOSTIC SPELLINGS ARE LISTED. A spelling that several traditions
# share (`flute` is French and English once accents are stripped, `trombone` is
# Italian, French and English, `fag` is Italian and German) belongs in more
# than one list, is tagged with all of them by `_ALIAS_LANGUAGES` below, and
# then casts NO vote. Listing it in one language would be the fault this module
# exists to fix, one row further down.
#
# ⚠️ Two abbreviations that look diagnostic and are not, both learned from the
# corpus: `cor` is French for horn AND the Italian abbreviation of `Corni` that
# Litolff prints on every Beethoven page, and `tr` is Trombe, Trompete and
# Trompette at once. Both are tagged multi-language and are inert here.
_LANGUAGE_SPELLINGS: dict[str, tuple[str, ...]] = {
    "it": (
        "flauto", "flauti", "ottavino", "flauto dolce", "flauti dolci",
        "oboi", "clarinetto", "clarinetti", "clarinetto basso",
        "fagotto", "fagotti", "contrafagotto", "contrafagotti",
        "corno", "corni", "corno inglese", "corni inglesi",
        "corno di bassetto", "corni di bassetto",
        "tromba", "trombe", "clarino", "clarini",
        "trombono", "tromboni", "cornetto", "cornetti", "cornetta",
        "flicorno", "eufonio", "serpente", "serpentone", "oficleide",
        "timpano", "gran cassa", "piatti", "tamburo", "tamburo militare",
        "tamburino", "triangolo", "batteria", "cassa",
        "arpa", "organo", "clavicembalo", "pianoforte",
        "mandolino", "chitarra", "sassofono",
        "violino", "violini", "viole", "violoncello", "violoncelli",
        "contrabasso", "contrabassi", "celli",
        "coro", "contralto", "tenore",
    ),
    "de": (
        "flote", "floten", "kleine flote", "blockflote", "blockfloten",
        "oboen", "hoboen", "klarinette", "klarinetten", "kl", "klar",
        "bassklarinette", "fagott", "fagotte", "kontrafagott", "kontrafagotte",
        "englisch horn", "englischhorn", "bassett horn", "bassetthorn",
        "horner", "hr", "trompete", "trompeten", "posaune", "posaunen",
        "tuben", "basstuba", "kornett", "flugelhorner", "fluegelhorn",
        "pauken", "pk", "schlagzeug", "grosse trommel", "kleine trommel",
        "becken", "glocken", "glocke", "windmaschine", "peitsche", "rute",
        "ruthe", "amboss", "ratsche", "triangel", "xylophon", "gr tr", "kl tr",
        "harfe", "klavier", "orgel", "gitarre",
        "violine", "violinen", "bratsche", "bratschen", "br", "violoncell",
        "kontrabass", "kontrabasse", "basse",
        "sopran", "chor", "saxophon", "sarrusophon", "heckelphon",
    ),
    "fr": (
        # ⚠️ `flutes` is HERE as well as under `en`, and the corpus is why. It
        # was tagged English-only for one revision, and `2 Grandes Flutes` /
        # `Petites Flutes` on Ravel's own head page then cast two ENGLISH votes
        # on a French score — normalization strips the circumflex, so
        # `Flûtes` and `Flutes` are one string. Tagged both, it is inert.
        "flutes",
        "petite flute", "flute a bec", "hautbois",
        "clarinette", "clarinettes", "clarinette basse",
        "basson", "bassons", "contrebasson", "contrebassons",
        "cor anglais", "cors anglais", "cor de basset", "cors de basset",
        "trompette", "trompettes", "piston", "pistons",
        "timbales", "batterie", "cloches",
        "harpe", "orgue", "guitare", "mandoline",
        "violon", "violons", "altos", "violoncelle", "violoncelles",
        "contrebasse", "contrebasses", "choeur",
        # ⚠️ `basse` is tagged German as well, and it is the largest false vote
        # the corpus produced: Mahler 5's `Bässe` normalizes to `basse`, which
        # is also the French word, and it cast TWELVE French votes on a German
        # score — 19% of that document's evidence, more than any single true
        # marker on it. The lexicon strips accents before matching, so the
        # letter that carries the language is gone by the time this sees the
        # string. Tagged both, inert.
        "basse",
    ),
    "en": (
        "flutes", "oboes", "clarinet", "clarinets",
        "bassoon", "bassoons", "contrabassoon", "double bassoon",
        "english horn", "basset horn", "horns", "trumpet", "trumpets",
        "cornet", "kettledrum", "snare drum", "bass drum", "tubular bells",
        "harpsichord", "recorder",
        "violins", "violas", "double bass", "contrabass", "chorus",
        # ⚠️ NOT `tpt` / `trpt` / `vln` / `vla` / `tbn`. They look like the
        # modern English abbreviations and they are printed by engravers of
        # every tradition: `Trpt.` appears on Brahms 1 / BREITKOPF, which
        # `instruments.py` already records, and it cast 8 English votes on that
        # German score — the second-largest false vote in the corpus. A Latin
        # consonant skeleton carries no language.
    ),
}

#: alias -> every tradition that prints it. Built by inversion, so a spelling
#: named under two languages is automatically inert instead of silently voting
#: for whichever list was read last.
_ALIAS_LANGUAGES: dict[str, frozenset[str]] = {}
for _lang, _spellings in _LANGUAGE_SPELLINGS.items():
    for _s in _spellings:
        _ALIAS_LANGUAGES[_s] = _ALIAS_LANGUAGES.get(_s, frozenset()) | {_lang}


def languages_of_alias(alias: str) -> frozenset[str]:
    """Every tradition that prints `alias`; empty where it is not tagged."""
    return _ALIAS_LANGUAGES.get(alias, frozenset())


def is_diagnostic(alias: str) -> bool:
    """Whether this alias identifies ONE tradition, and so may cast a vote."""
    return len(_ALIAS_LANGUAGES.get(alias, ())) == 1


# ── what a language reading settles, and what it may not ─────────────────────
#
# alias -> {language: instrument name}. An alias absent from a language's map
# ABSTAINS in that language: the entry means "this tradition prints this
# abbreviation for this instrument", never "the other reading is unlikely".
#
# ⚠️ Every family here is one where the two candidates come from two
# traditions. The families where BOTH readings live in ONE language are
# deliberately absent — see the module docstring; adding them would break
# Handel.
LANGUAGE_READINGS: dict[str, dict[str, str]] = {
    # `Tp.` is Timpani in the Italian and German orchestral tradition (Timpani,
    # and German scores that keep the Italian nouns) and Trumpet in the modern
    # English one. French prints `Timbales` and abbreviates `Timb.`, never
    # `Tp.`, so French ABSTAINS rather than guessing.
    "tp": {"it": "Timpani", "de": "Timpani", "en": "Trumpet"},
    # `Tb.` is Tromboni in an Italian score and the Tuba in a German one
    # (`Tb.` for Basstuba). ⚠️ The lexicon reads it as Tuba unconditionally,
    # and over the 1422-label corpus EVERY bare `Tb.` is Litolff's Beethoven 6,
    # an Italian score whose `Tb.` is the two trombones — while every real tuba
    # in that corpus is spelled `Tuba` in full. English abstains: `Tbn.` and
    # `Tba.` are the unambiguous English abbreviations and `tbn` already
    # resolves on its own.
    "tb": {"it": "Trombone", "de": "Tuba"},
    # French `Altos` are an orchestra's VIOLAS; English/Italian `Altos` are a
    # chorus's. This agrees with the lexicon's own first answer on the French
    # side — it is listed so the agreement is EVIDENCED rather than lucky, and
    # so an English choral score gets the other reading.
    "altos": {"fr": "Viola", "en": "Alto", "it": "Alto"},
}

#: Aliases this module may decide that `instruments.AMBIGUOUS_ALIASES` does not
#: yet declare. Kept HERE and not there, because declaring an alias ambiguous in
#: the lexicon changes what `dossier.join_parts_to_slots` will let PIN a staff —
#: a default change, and this module changes no default.
EXTRA_AMBIGUOUS: dict[str, tuple[str, ...]] = {
    "tb": ("Tuba", "Trombone"),
}


@dataclass(frozen=True)
class LanguageReading:
    """What a document's own unambiguous labels say about its tradition."""

    language: str | None          # None = abstained
    votes: dict[str, int]         # tradition -> diagnostic labels seen
    n_diagnostic: int             # votes cast at all
    n_labels: int                 # labels offered

    @property
    def share(self) -> float:
        """The winner's share of the diagnostic votes; 0.0 when none were cast."""
        if not self.n_diagnostic:
            return 0.0
        return max(self.votes.values()) / self.n_diagnostic

    @property
    def is_mixed(self) -> bool:
        """More than one tradition is genuinely represented.

        Reported rather than suppressed: a German publisher setting Italian
        instrument names is a real and common object, and a reading that hid it
        would be claiming a certainty the page does not have.
        """
        return sum(1 for v in self.votes.values() if v) > 1


#: A document needs this many diagnostic labels before its language is claimed.
#: Not tuned — one label is an OCR accident.
MIN_DIAGNOSTIC_VOTES = 3

#: …and the winner must hold this much of them. A score that mixes traditions
#: near evenly has no single answer and gets none.
MIN_SHARE = 0.70


def _matches(labels: Sequence[str]) -> list:
    """`instruments.lookup` per label, resolved once and memoized by string.

    ⚠️ Shared between the vote and the re-decision on purpose. `lookup` costs
    ~23 ms — the alias index is a few thousand entries wide after the
    contrabassoon cross product and the derived plurals — so a 400-label
    document is ~9 s per pass, and the obvious two-pass shape (vote the
    language, then re-decide the labels) pays it twice for nothing.
    """
    seen: dict[str, object] = {}
    out = []
    for text in labels:
        if text not in seen:
            seen[text] = _instruments.lookup(text)
        out.append(seen[text])
    return out


def detect(labels: Iterable[str]) -> LanguageReading:
    """Vote a document's tradition out of the labels it prints.

    Every label is resolved by the ordinary lexicon; a label whose alias names
    exactly one tradition casts one vote. Ambiguous and untagged aliases are
    inert, so the evidence is strictly the spellings that could only have been
    printed by one publisher's convention.
    """
    seen = list(labels)
    return _detect_from_matches(_matches(seen), len(seen))


def _detect_from_matches(matches: Sequence, n_labels: int) -> LanguageReading:
    votes = {lang: 0 for lang in LANGUAGES}
    for match in matches:
        if match is None:
            continue
        langs = _ALIAS_LANGUAGES.get(match.alias, ())
        if len(langs) == 1:
            votes[next(iter(langs))] += 1
    n = sum(votes.values())
    reading = LanguageReading(None, votes, n, n_labels)
    if n < MIN_DIAGNOSTIC_VOTES:
        return reading
    winner = max(votes, key=lambda k: votes[k])
    if votes[winner] / n < MIN_SHARE:
        return reading
    return LanguageReading(winner, votes, n, n_labels)


def resolve_alias(alias: str, reading: LanguageReading) -> str | None:
    """The instrument `alias` names in this document's tradition, or None.

    None means ABSTAIN — the caller keeps whatever the lexicon said. That
    covers three separate cases on purpose, and none of them is a weak
    preference: the document's language was not readable, this tradition has no
    recorded convention for the alias, or the alias is one both readings share
    a language on.
    """
    if reading.language is None:
        return None
    return LANGUAGE_READINGS.get(alias, {}).get(reading.language)


def candidates(alias: str) -> tuple[str, ...]:
    """Instrument names `alias` could mean — the lexicon's, widened by ours."""
    declared = tuple(i.name for i in _instruments.candidates_for_alias(alias))
    return declared or EXTRA_AMBIGUOUS.get(alias, ())


@dataclass(frozen=True)
class Decision:
    """One label, and what the language reading did to its reading."""

    text: str
    alias: str | None
    lexicon: str | None           # instrument name the lexicon returned
    language: str | None          # instrument name this module returned
    changed: bool


def enabled() -> bool:
    """`OMR_SCORE_LANGUAGE` — default OFF.

    The signal is measured and the wiring into `contextual` is a separate,
    sequenced change; until then this is the switch a caller consults.
    """
    return os.environ.get("OMR_SCORE_LANGUAGE", "0").strip().lower() in (
        "1", "true", "yes", "on")


def resolve_document(labels: Sequence[str],
                     reading: LanguageReading | None = None,
                     ) -> tuple[LanguageReading, list[Decision]]:
    """Read a document's language, then re-decide the labels it settles.

    One pass over one document's labels — the unit the signal is a property of.
    Returns the reading beside a decision per label, so a caller can report the
    evidence rather than only the verdict.
    """
    matches = _matches(labels)
    if reading is None:
        reading = _detect_from_matches(matches, len(labels))
    out: list[Decision] = []
    for text, match in zip(labels, matches):
        if match is None:
            out.append(Decision(text, None, None, None, False))
            continue
        lex = match.instrument.name
        lang = resolve_alias(match.alias, reading)
        out.append(Decision(text, match.alias, lex, lang,
                            lang is not None and lang != lex))
    return reading, out
