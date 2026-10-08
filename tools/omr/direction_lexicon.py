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
_DYNAMIC_WORD = """
    crescendo cresc decrescendo decresc diminuendo dim
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


def lookup(text: str) -> DirectionHit | None:
    """The direction `text` names, or None if it is not one.

    Case and punctuation are ignored for MATCHING and preserved in the result.
    """
    if not text:
        return None
    if _A_DUE.fullmatch(text.strip().lower()):
        return DirectionHit(text=text.strip(), category="part", terms=("a2",))
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
