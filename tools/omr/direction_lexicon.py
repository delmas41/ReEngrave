"""Is this string a musical direction, or is it OCR noise?

The counterpart to `instruments.lookup` for the OTHER text on a page. A margin
label is anchored by position — whatever is printed to the left of a staff is an
instrument name and nothing else — so `instruments.py` can afford to accept
almost anything. Text INSIDE a system has no such anchor: the same crop that
holds `legato` also holds a slur read as `~`, a beam group read as `IIII`, and a
fragment of an accidental read as `#`. Something has to decide which of those is
music.

**A lexicon, and nothing looser.** The alternative — accept any OCR block that
looks like a word — was rejected on arithmetic rather than taste. OMR-NED charges
a direction its own character count on BOTH sides: a `legato` we miss costs 6,
and a `IIII` we invent costs 4. Precision and recall are worth the same, so the
reader that abstains and the reader that guesses trade one for one, and only the
gated one is safe on material nobody has measured.

## What it accepts, and the two shapes of it

A direction is one of:

- **A term** — `legato`, `pesante`, `dolce`, `Allegro`. Held in `TERMS` with its
  category, and matched case-insensitively with any trailing period allowed, so
  `espr.` finds `espr`.
- **A phrase** — `Un poco sostenuto`, `espr. e legato`, `Allegro con brio`.
  Accepted when EVERY token is either a term or a `CONNECTIVE` (`un`, `poco`,
  `e`, `con`, `ma`, `non`, ...) AND at least one is a real term. That last
  clause is what keeps `e e e` — three slurs read as letters — out.

Both are deliberately narrow. The categories exist to say what a hit IS, not to
change whether it is accepted: `tempo` and `expression` both export as
`<words>`, and only a caller that wants to place them differently needs to care.

## Why the text is returned unchanged

`lookup` reports what it matched but hands back the ORIGINAL string, because the
metric scores the printed characters. Normalising `Un poco sostenuto` to
`un poco sostenuto` would buy nothing and cost one edit; correcting `Iegato` to
`legato` would buy one. Neither is worth the risk of a reader that rewrites what
it read, so this one does not.
"""
from __future__ import annotations

import re
import dataclasses
from dataclasses import dataclass

#: Words that join direction terms into a phrase. They carry no meaning of
#: their own here, so a string made only of these is rejected.
CONNECTIVE = {
    "a", "al", "alla", "e", "ed", "il", "la", "un", "una", "con", "col",
    "ma", "non", "piu", "più", "meno", "poco", "molto", "assai", "quasi",
    "sempre", "subito", "in", "di", "da",
}
# `the`, `and` and `of` were here and are deliberately gone. No direction in
# this repertoire is English, and their only measured effect was to let OCR
# noise through: a scanned `a Tempo.` came back from the language-model rung as
# `a Tempo. and`, which passed because `and` was glue. Removing them refuses
# that string, and the union then takes the other rung's `a Tempo.` — correct.

#: The intensifiers are in CONNECTIVE **and** here, because they are both. In
#: `Un poco sostenuto` `poco` is glue; on the Mahler page `molto` is printed
#: alone and IS the direction, worth 5 edits. Listing them twice is what lets
#: one word be a phrase on its own without also admitting `e e e` — three
#: slurs read as letters — which the connectives alone would.
_INTENSIFIER = "molto poco piu più meno assai sempre subito quasi"

#: Tempo words — the ones printed at the head of a movement or a section.
_TEMPO = """
    grave largo larghetto lento adagio adagietto andante andantino moderato
    allegretto allegro vivace vivo presto prestissimo maestoso sostenuto
    ritenuto rallentando ritardando rall ritard rit accelerando accel
    stringendo allargando tempo tempus doppio primo prima mosso moto
    langsam schnell bewegt lebhaft massig mässig breit ruhig rasch
    lent vif modere modéré anime animé
"""

#: Expression and articulation words — what is printed under a staff.
_EXPRESSION = """
    legato staccato staccatissimo marcato marcatissimo tenuto ten portato
    pesante leggiero leggiermente dolce dolcissimo cantabile espressivo espress
    espr grazioso scherzando giocoso tranquillo calmo semplice
    appassionato agitato risoluto energico deciso brillante brio bravura
    lusingando morendo smorzando perdendosi calando slancio
    lacrimoso mesto lamentoso teneramente amabile
    sotto voce divisi unis pizzicato pizz arco tremolo trem marc
    sord sordino sordini muta ausdrucksvoll zart getragen breitgestrichen
    gestopft offen dampfer dämpfer flatterzunge
    doux chante chanté expressif
"""

#: Part (instrument) names printed INSIDE a system, at the left of a staff that
#: carries a divided part: `Basso`, `Bassi.`, `Vcl.` (Sean, 2026-10-08, page-by-
#: page review of the scan pages -- he wants them read). A margin label is the
#: other reader's (`instruments.py`); these are the ones printed in the music.
#: Each entry was added because a printed word on the 10 review pages is one:
#: basso, bassi, vcl (and vc / violoncello / violoncelli, its spellings).
_PART = """
    basso bassi vcl vc violoncello violoncelli
"""

#: Dynamic WORDS — the ones spelled out rather than drawn as a glyph. The
#: letter dynamics (`f`, `pp`) are the detector's job (`export.measure_dynamics`)
#: and are deliberately absent, so the two readers cannot both claim one mark.
#: `dimin` (Sean, 2026-10-09): Litolff p8 prints `dimin.`, read whole once the
#: `sempre più p` box fix stopped cutting it to `dim`.
_DYNAMIC_WORD = """
    crescendo cresc decrescendo decresc diminuendo dimin dim
    rinforzando rinf forte piano fortissimo pianissimo mezzo
    sforzando smorz
"""


def _terms(block: str, category: str) -> dict[str, str]:
    return {word: category for word in block.split()}


TERMS: dict[str, str] = {
    **_terms(_TEMPO, "tempo"),
    **_terms(_EXPRESSION, "expression"),
    **_terms(_DYNAMIC_WORD, "dynamic"),
    **_terms(_INTENSIFIER, "expression"),
    **_terms(_PART, "part"),
}

#: A phrase takes the category of its most specific term, not of its first —
#: `Un poco sostenuto` is a tempo mark whose first matching token is `poco`.
_CATEGORY_RANK = ("tempo", "dynamic", "expression", "part")

#: Everything a token may carry and still be the same word: a trailing period
#: on an abbreviation, and the punctuation OCR sometimes attaches.
_STRIP = ".,;:!·•"

#: A phrase longer than this is a title, a copyright line or an OCR run-on, not
#: a direction. Measured against the corpus this exists for: the longest true
#: direction on the three benchmark pages is `Un poco sostenuto`, three tokens.
MAX_PHRASE_TOKENS = 6



@dataclass(frozen=True)
class DirectionHit:
    """What `lookup` matched, alongside the text exactly as it was read."""

    text: str          #: unchanged — the metric scores printed characters
    category: str      #: `tempo` | `expression` | `dynamic` | `part`
    terms: tuple[str, ...]   #: the lexicon entries that matched
    #: Dynamic tokens INSIDE the phrase (`più f` -> ('f',)). The marking is ONE
    #: thing -- word and dynamic mean something only together (Sean,
    #: 2026-10-08) -- so they stay in `text`; the caller links the detector's
    #: dynamic glyph so it is not counted twice.
    dynamics: tuple[str, ...] = ()
    #: ROADMAP 2.67b: the terms-library ids a SCOPED lookup matched beyond
    #: `TERMS` (empty on an unscoped lookup, which never reads the library).
    library: tuple[str, ...] = ()
    #: True when the match is a whole library word in a language outside the
    #: work's scope, accepted only because it is 5+ letters long.
    other_language: bool = False
    #: ROADMAP 2.221 (STAGED, `LexiconScope.tempo_marks`): the metronome tail the text carried after a TEMPO word
    #: (`(♩ = 108)`, `d = 108.`), exactly as read; "" when none. `text` is the tempo WORD alone.
    metronome: str = ""


def _normalise(token: str) -> str:
    return token.strip(_STRIP).lower()


#: Dynamic tokens a phrase may contain: `più f`, `p dolce`, `f marc.`,
#: `sempre p`, `poco a poco cresc.`. A BARE dynamic is not a direction -- it is
#: the dynamic reader's (`export.measure_dynamics`) -- so a string with no real
#: term in it is still refused.
_DYNAMIC_LETTERS = {"p", "pp", "ppp", "f", "ff", "fff", "mp", "mf", "sf", "sfz",
                    "fz", "fp", "rf", "rfz", "sfp"}

#: `a2` / `a 2` / `a.2`: both players of a shared staff play the line (Sean,
#: 2026-10-08: yes, read it). It is text, not a notehead.
_A_DUE = re.compile(r"a\s?\.?\s?2\.?")


def _unglue(token: str) -> list[str]:
    """`pdolce` -> [`p`, `dolce`]: a dynamic letter run glued to the front of a
    term by the OCR. Only where the remainder is a real term and the whole token
    is not (`piano`, `poco`, `pizz` stand)."""
    if token in TERMS or token in CONNECTIVE or token in _DYNAMIC_LETTERS:
        return [token]
    for k in (3, 2, 1):
        if token[:k] in _DYNAMIC_LETTERS and token[k:] in TERMS:
            return [token[:k], token[k:]]
    return [token]


def _trim_ends(text: str) -> str:
    """The reading without OCR punctuation debris at its ends (`, cresc.`,
    `cresc,`). An abbreviation's period stays."""
    return text.strip().lstrip(" ,;:.·•-").rstrip(" ,;:·•-") or text.strip()


def lookup(text: str, *, scope: "LexiconScope | None" = None
           ) -> DirectionHit | None:
    """The direction `text` names, or None if it is not one.

    Case and punctuation are ignored for MATCHING and preserved in the result.

    ROADMAP 2.67b: with a `scope` (the STAGED reader passes one; LEGACY never
    does, so the frozen path is unchanged) a string `TERMS` refuses is asked
    of the terms library under that scope's limits -- see `_library_lookup`.
    `TERMS` is asked first and its answer stands: the library only ever ADDS.
    """
    if not text:
        return None
    if _A_DUE.fullmatch(text.strip().lower()):
        return DirectionHit(text=text.strip(), category="part", terms=("a2",))
    if scope is not None and scope.tempo_marks:
        split = split_metronome(text)
        if split is not None:
            # A tempo word with its metronome mark (`Allegro con brio (♩ = 108)`): the head is looked up as always, and only a
            # TEMPO word may carry the tail (a bar number or a rehearsal letter with a digit is still no direction).
            head_hit = lookup(split[0], scope=scope)
            if head_hit is not None and head_hit.category == "tempo":
                return dataclasses.replace(head_hit, metronome=split[1])
            return None
    prepared = _prepare(text)
    if prepared is None:
        return None
    shown, tokens = prepared
    hit = _curated(shown, tokens)
    if hit is not None or scope is None:
        return hit
    return _library_lookup(text, shown, tokens, scope)


#: ROADMAP 2.221: a metronome tail at the END of a read tempo mark: an optional bracket, the note glyph as an OCR reads it (up to two
#: characters of any kind: `♩`, `d`, `J`, `o`, `)`), an equals sign or the dash a scan prints for it, then 2-3 digits (`ca.` allowed), and
#: closing punctuation. The head must still pass the lexicon, so nothing here admits a digit anywhere else.
_METRONOME_TAIL = re.compile(
    r"^(?P<head>.*?[A-Za-zÀ-ÿ][.,]?)\s*[(\[]?\s*(?P<tail>(?:\S{1,2}\s*)?[=≈_–—\-]+\s*(?:c(?:a|irca)\.?\s*)?\d{2,3}[.,]?\s*[)\]]?\.?)\s*$")


def split_metronome(text: str) -> "tuple[str, str] | None":
    """`(head, tail)` of a text that ends in a metronome mark (`Allegro con brio. d = 108.` -> (`Allegro con brio.`, `d = 108.`)), else None. PURE."""
    m = _METRONOME_TAIL.match((text or "").strip())
    return (m.group("head").strip(), m.group("tail").strip()) if m else None


def _prepare(text: str) -> "tuple[str, list[str]] | None":
    """The noise filters every lookup runs, and the tokens they leave:
    `(the text as shown, its normalised tokens)`, or None if refused."""
    # Musical text is letters, spaces and abbreviation periods. A digit or a
    # bracket means a bar number, a metronome mark or a rehearsal letter — all
    # of which are somebody else's problem, and none of which is a direction.
    if not re.fullmatch(r"[A-Za-zÀ-ÿ' .,\-]+", text.strip()):
        return None
    spaced = []
    glued = False
    for w in text.split():
        norm = _normalise(w)
        parts = _unglue(norm) if norm else []
        if len(parts) == 2:
            glued = True
            spaced += [parts[0], w[w.lower().find(parts[1]):]]
        else:
            spaced.append(w)
    shown = " ".join(spaced) if glued else _trim_ends(text)
    tokens = [_normalise(t) for t in spaced]
    tokens = [t for t in tokens if t]
    if not tokens or len(tokens) > MAX_PHRASE_TOKENS:
        return None

    # A word never follows itself in a direction, and a decoder that says it did
    # is repeating itself. Surya is a language model behind an OCR interface and
    # does this on ambiguous crops: one `arco.` on a scanned Beethoven 5 page
    # came back as `arco. arco. arco. arco.`, which passed because every token
    # was a real term. The other rung read the same crop as `arco.`, so
    # refusing the repetition is what lets the union reach the right answer.
    #
    # ADJACENT, not anywhere: `poco a poco` is a real marking and repeats `poco`
    # with a connective between. Only the immediate repeat is the failure.
    if any(a == b for a, b in zip(tokens, tokens[1:])):
        return None
    return shown, tokens


def _curated(shown: str, tokens: list[str]) -> DirectionHit | None:
    """`TERMS` and `CONNECTIVE` alone: the lexicon as it stood before 2.67b."""
    matched: list[str] = []
    dynamics: list[str] = []
    for token in tokens:
        if token in TERMS:
            matched.append(token)
        elif token in _DYNAMIC_LETTERS:
            dynamics.append(token)
        elif token not in CONNECTIVE:
            return None
    if not matched:
        return None

    categories = {TERMS[t] for t in matched}
    category = next(c for c in _CATEGORY_RANK if c in categories)
    return DirectionHit(text=shown, category=category, terms=tuple(matched),
                        dynamics=tuple(dynamics))


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.67b: the terms library, behind the limits Sean set (2026-10-12)
# ─────────────────────────────────────────────────────────────────────────────
#
# The library (`musical_terms`, 1,755 terms copied from Gradus) is ~10x
# `TERMS`, and every word it adds is a string OCR noise can now land on. So it
# is admitted under three limits, all on the READING side; where a word is
# printed (family, heading placement) is ADJUDICATE's, because only there is
# the staff's instrument known (`adjudicators/text.py`, `_held_back`):
#
# 1. LANGUAGE. Italian and Latin always; the composer's own language (the
#    committed `composer-languages.json`, keyed on the work) and the
#    EDITION's (the language its margin labels are printed in) on top. A word
#    in any other language is accepted only as a whole library entry of 5+
#    letters, never inside a phrase. An unknown work admits every language,
#    and the scope says so.
# 2. NEVER A DIRECTION: theory vocabulary (`printedInScores: false`) and
#    instrument names (`instrument: true`; the in-music part names stay
#    `_PART`'s, and margin labels `instruments.py`'s).
# 3. SHORT FORMS. A library form under 3 letters (`a`, `e`, `et`, `Fl`, `Vc`)
#    never stands alone -- OCR invents those constantly. Inside a phrase it is
#    glue, like a `CONNECTIVE`. The exceptions are the hand marks below.

#: Library forms under 3 letters that are a whole direction on their own:
#: the keyboard hands (`m.g.`, `m.d.`, `m.s.`, `l.H.`, `r.H.`) and `G.P.`.
SHORT_ALONE = frozenset({"mg", "md", "ms", "lh", "rh", "gp",
                         # short `general` words that ARE a direction alone
                         # (the connective rule below): back to the written
                         # octave after 8va, and the cut sign's word.
                         "loco", "vide"})

#: Library entries printed in every repertoire whatever their language:
#: `G.P.` is German (`Generalpause`) and Dvořák, Bruckner and Elgar all print it.
UNIVERSAL = frozenset({"Generalpause"})

#: The library's categories, as this lexicon's (`_CATEGORY_RANK`) -- the
#: library's own is kept on the hit's `library` ids.
_LIBRARY_CATEGORY = {"tempo": "tempo", "dynamics": "dynamic"}

#: A single `general` library word this short or shorter is a connective and
#: never a direction alone (`ein`, `und`, `sehr`, `avec`).
CONNECTIVE_MAX_LETTERS = 4

#: A word outside the scope's languages is admitted only this long (folded).
OTHER_LANGUAGE_MIN_LETTERS = 5


@dataclass(frozen=True)
class LexiconScope:
    """Which library languages a work's directions are read in."""

    #: None = every language (the work, or its composer, is unknown).
    languages: "frozenset[str] | None"
    work_id: "str | None" = None
    composer_languages: "tuple[str, ...] | None" = None
    edition_languages: tuple[str, ...] = ()
    #: ROADMAP 2.221 (flag `OMR_CLAIM_WORDS_FIRST`, set by the STAGED reader only): a tempo word may carry its metronome tail.
    tempo_marks: bool = False

    def admits(self, language: str, term_id: str = "") -> bool:
        return (self.languages is None or language in self.languages
                or term_id in UNIVERSAL)

    def to_json(self) -> dict:
        return {"languages": (sorted(self.languages)
                              if self.languages is not None else None),
                "work_id": self.work_id,
                "composer_languages": (list(self.composer_languages)
                                       if self.composer_languages is not None
                                       else None),
                "edition_languages": list(self.edition_languages),
                "unknown_work": self.languages is None,
                **({"tempo_marks": True} if self.tempo_marks else {})}


def scope_for(work_id: "str | None", label_texts=(), *, tempo_marks: bool = False) -> LexiconScope:
    """The scope for a work, from its composer and its edition's labels."""
    from . import musical_terms as MT
    composer = MT.composer_languages(work_id)
    edition = MT.edition_languages(label_texts)
    if composer is None:
        return LexiconScope(languages=None, work_id=work_id,
                            composer_languages=None, edition_languages=edition, tempo_marks=tempo_marks)
    return LexiconScope(
        languages=frozenset(MT.ALWAYS) | frozenset(composer) | frozenset(edition),
        work_id=work_id, composer_languages=composer, edition_languages=edition, tempo_marks=tempo_marks)


def _eligible(matches):
    """Library matches that may be a direction at all (limit 2)."""
    return [m for m in matches
            if m.term.printed_in_scores and not m.term.instrument]


def _library_category(terms) -> str:
    cats = {_LIBRARY_CATEGORY.get(t.category, "expression") for t in terms}
    return next(c for c in _CATEGORY_RANK if c in cats)


def _library_lookup(text: str, shown: str, tokens: list[str],
                    scope: LexiconScope) -> DirectionHit | None:
    from . import musical_terms as MT

    # The whole string first: `a tempo`, `Tempo I`, `Sehr langsam`, `G.P.`.
    whole = _eligible(MT.lookup(text))
    # A connective alone (`ein`, `und`, `mit`, `wie`, `sehr`) is not a
    # direction: one SHORT word whose every entry is the library's `general`
    # is glue, as in the phrase rule below. The bound is length because
    # `general` also holds real stand-alone directions -- `Attacca`,
    # `Bouché`, `Steigerung`, `Hauptstimme` -- and those are all longer.
    # `Wie oben` (two words) still stands.
    if (whole and len(tokens) == 1
            and len(MT.fold(text)) <= CONNECTIVE_MAX_LETTERS
            and MT.fold(text) not in SHORT_ALONE
            and all(m.term.category == "general"
                    and m.term.id not in UNIVERSAL for m in whole)):
        whole = []
    if whole:
        key = MT.fold(text)
        if len(key) >= 3 or key in SHORT_ALONE:
            inside = [m for m in whole
                      if scope.admits(m.term.language, m.term.id)]
            if inside:
                return DirectionHit(
                    text=shown, category=_library_category(
                        m.term for m in inside),
                    terms=tuple(t for t in tokens if t in TERMS),
                    library=tuple(dict.fromkeys(m.term.id for m in inside)))
            if len(key) >= OTHER_LANGUAGE_MIN_LETTERS:
                return DirectionHit(
                    text=shown, category=_library_category(
                        m.term for m in whole),
                    terms=(), other_language=True,
                    library=tuple(dict.fromkeys(m.term.id for m in whole)))

    # Then a phrase of words, each a `TERMS` entry, a connective, a dynamic
    # letter or a library word in the scope's languages.
    matched: list[str] = []
    library: list[str] = []
    dynamics: list[str] = []
    real = False
    categories: list[str] = []
    for token in tokens:
        if token in TERMS:
            matched.append(token)
            categories.append(TERMS[token])
            real = True
            continue
        if token in _DYNAMIC_LETTERS:
            dynamics.append(token)
            continue
        if token in CONNECTIVE:
            continue
        found = [m for m in _eligible(MT.lookup(token))
                 if scope.admits(m.term.language, m.term.id)]
        if not found:
            return None
        library.extend(m.term.id for m in found)
        if len(MT.fold(token)) < 3:
            continue                      # a short form is glue (limit 3)
        categories.append(_library_category(m.term for m in found))
        # `und mit sehr` is not a direction: a phrase needs a word that MEANS
        # something, not only the library's connectives (`general`).
        if any(m.term.category != "general" for m in found):
            real = True
    if not real:
        return None
    category = next(c for c in _CATEGORY_RANK if c in categories)
    return DirectionHit(text=shown, category=category, terms=tuple(matched),
                        dynamics=tuple(dynamics),
                        library=tuple(dict.fromkeys(library)))
