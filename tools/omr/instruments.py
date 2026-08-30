"""Instrument lexicon — a printed staff label to what it implies musically.

Given a margin label like "2 Clarinetti in B", this maps to the canonical
instrument, its family, its default clef, its written range, and its
transposition. That single join supplies three of the four deductions a human
makes at a glance (see NOTES.md -> "Contextual analysis roadmap"): whether the
staff transposes, what clef to expect, and what register it should occupy.

## Transposition conventions

Two numbers, both from the point of view of what is PRINTED on the staff:

`fifths_offset` — written key = concert key + offset, in circle-of-fifths steps.
    It depends only on the key the instrument is "in", by the identity
    **offset = -fifths(key_name)**: an instrument in B-flat (key of Bb = -2
    fifths) prints +2, one in A (key of A = +3) prints -3. These are the same
    numbers `transcribe._TRANSPOSITION_FIFTHS_OFFSETS` already uses.

`chromatic` — sounding pitch = written pitch + chromatic, in semitones. This is
    the MusicXML `<transpose><chromatic>` convention. Unlike `fifths_offset` it
    depends on the octave the instrument speaks in, so it cannot be derived from
    the key name alone (a horn in E-flat sounds a major 6th BELOW written, -9,
    while a trumpet in E-flat sounds a minor 3rd ABOVE, +3). It is therefore
    stored per instrument, and left None where the label alone does not settle it.

Ranges are WRITTEN MIDI numbers (what appears on the staff), generous rather
than strict — they exist to catch a clef error that shifts a staff by an octave
or more, not to police an unusual note.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# ── circle-of-fifths for "in X" parsing ─────────────────────────────────────

_KEY_FIFTHS = {
    "c": 0, "g": 1, "d": 2, "a": 3, "e": 4, "b": 5,
    "f": -1, "bb": -2, "eb": -3, "ab": -4, "db": -5, "gb": -6,
    # German / Italian spellings seen on real title pages
    "h": 5, "es": -3, "as": -4, "b-flat": -2, "e-flat": -3, "a-flat": -4,
    "fis": 6, "cis": 7, "des": -5, "ges": -6,
}

# "in B", "in Es", "in F", "(Es)", "in C.G"
_IN_KEY_RE = re.compile(
    r"(?:\bin\s+|\()\s*([A-Ha-h](?:b|-flat|is|s)?)\b", re.IGNORECASE
)

# A transposing instrument often carries its key with no "in" at all, as a bare
# token after the abbreviation: "Cor. D.", "Tr. Es", "Cl. B". Only consulted for
# instruments that actually take a key, so "Vl. I" / "S." can't be misread.
_BARE_KEY_RE = re.compile(r"(?:^|\s)([a-h](?:b|is|s)?)\s*$")


@dataclass(frozen=True)
class Match:
    """A label resolved to an instrument, with enough provenance to judge it."""

    instrument: "Instrument"
    fifths_offset: int          # written key = concert key + this
    alias: str                  # the alias that fired
    coverage: float             # fraction of the label's letters the alias covers
    ocr_folded: bool            # matched only after folding OCR confusions

    @property
    def confidence(self) -> str:
        """high / medium / low.

        Alias LENGTH is not the risk — `Fl.` `Ob.` `Vc.` are the standard
        unambiguous abbreviations. The risk is a short alias firing inside a
        garbled label, which `coverage` measures directly, and a match that
        needed the OCR fold, which is a guess by construction.
        """
        if self.ocr_folded:
            return "low"
        if self.coverage >= 0.6:
            return "high"
        return "medium"


@dataclass(frozen=True)
class Instrument:
    """One canonical orchestral instrument."""

    name: str
    family: str                       # woodwind|brass|percussion|keyboard|voice|string
    default_clef: str                 # treble|bass|alto|tenor
    written_range: tuple[int, int]    # generous written MIDI lo, hi
    chromatic: int | None = 0         # sounding = written + chromatic; None = key-dependent
    default_fifths_offset: int = 0    # used when the label names no key
    unpitched: bool = False           # exclude from key / pitch reasoning
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Aliases are matched after normalization (accents stripped, lowercased,
# punctuation and part numbers removed), so "Flöten" -> "floten", "Fl." -> "fl".
INSTRUMENTS: tuple[Instrument, ...] = (
    # ── woodwind ───────────────────────────────────────────────────────────
    Instrument("Piccolo", "woodwind", "treble", (74, 108), 12, 0,
               aliases=("piccolo", "picc", "ottavino", "kleine flote", "petite flute", "fl picc")),
    Instrument("Flute", "woodwind", "treble", (59, 96), 0, 0,
               aliases=("flute", "flutes", "flauto", "flauti", "flote", "floten", "fl", "fla", "fl gr")),
    Instrument("Oboe", "woodwind", "treble", (58, 91), 0, 0,
               aliases=("oboe", "oboen", "oboi", "hoboen", "hautbois", "ob")),
    Instrument("English horn", "woodwind", "treble", (52, 86), -7, 1,
               aliases=("english horn", "cor anglais", "corno inglese", "englisch horn",
                        "englischhorn", "c ing", "c a")),
    Instrument("Clarinet", "woodwind", "treble", (50, 91), None, 2,
               aliases=("clarinet", "clarinets", "clarinetto", "clarinetti", "klarinette",
                        "klarinetten", "clarinette", "clarinettes", "cl", "clar", "kl")),
    Instrument("Bass clarinet", "woodwind", "treble", (38, 79), None, 2,
               # NOT "cl b": on real scores "Cl. B." means clarinet in B-flat far
               # more often than bass clarinet, which is written "B. Cl." / "Bcl".
               aliases=("bass clarinet", "clarinetto basso", "bassklarinette",
                        "clarinette basse", "b cl", "bcl")),
    Instrument("Bassoon", "woodwind", "bass", (34, 72), 0, 0,
               aliases=("bassoon", "bassoons", "fagotto", "fagotti", "fagott", "fagotte",
                        "basson", "bassons", "fag", "fg")),
    Instrument("Contrabassoon", "woodwind", "bass", (22, 60), -12, 0,
               aliases=("contrabassoon", "double bassoon", "contrafagotto",
                        "contrafagotte", "kontrafagott", "contrebasson",
                        "cfag", "kfag")),
    Instrument("Saxophone", "woodwind", "treble", (49, 89), None, 3,
               aliases=("saxophone", "saxophon", "sax", "sassofono")),
    # Boulanger scores one; without it "Bass Sarrusophone" resolves on the word
    # "Bass" and lands in the voices, fifteen part names adrift.
    Instrument("Sarrusophone", "woodwind", "bass", (28, 67), 0, 0,
               aliases=("sarrusophone", "sarrusophon", "sarrus")),

    # ── brass ──────────────────────────────────────────────────────────────
    Instrument("Horn", "brass", "treble", (41, 77), None, 1,
               aliases=("horn", "horns", "corno", "corni", "horner", "cor", "cors", "hn")),
    # NOT "tp": in the German/Italian orchestral convention these scores use,
    # "Tr." is Trombe (trumpets) and "Tp." on the staff below it is Timpani —
    # measured on Beethoven 1 (imslp-00074 p40), whose system reads
    # Fl / Ob / Cl / Fag / Cor / Tr / Tp. "Tpt." remains the unambiguous English
    # trumpet abbreviation.
    #
    # The score-order prior now settles this properly, from where the staff
    # SITS rather than from which convention is commoner: see
    # AMBIGUOUS_ALIASES below and `score_layouts.resolve_ambiguous_label`. This
    # table still has to name one instrument, and names the reading that is
    # right when the prior has no opinion.
    Instrument("Trumpet", "brass", "treble", (52, 84), None, 2,
               aliases=("trumpet", "trumpets", "tromba", "trombe", "trompete", "trompeten",
                        "trompette", "trompettes", "tr", "tpt", "clarino", "clarini")),
    Instrument("Trombone", "brass", "bass", (34, 72), 0, 0,
               aliases=("trombone", "trombones", "trombono", "tromboni", "posaune",
                        "posaunen", "trb", "tbn", "pos")),
    # "tenor tuba" before the voice aliases can reach it: the alias index is
    # longest-first, so without it "Tenor Tuba in B-flat" resolves to the VOICE
    # Tenor and takes Holst's Planets out of score order on all eight movements.
    Instrument("Tuba", "brass", "bass", (26, 65), 0, 0,
               aliases=("tenor tuba", "tenortuba", "tuba", "tuben", "basstuba",
                        "bass tuba", "tb")),

    # ── percussion ─────────────────────────────────────────────────────────
    Instrument("Timpani", "percussion", "bass", (36, 60), 0, 0,
               aliases=("timpani", "timpano", "tympani", "pauken", "timbales", "kettledrum",
                        "timp", "tmp", "pk", "tp")),
    Instrument("Percussion", "percussion", "treble", (0, 127), 0, 0, unpitched=True,
               aliases=("percussion", "schlagzeug", "batteria", "batterie", "perc",
                        "gran cassa", "grosse trommel", "bass drum", "piatti", "becken",
                        "cymbals", "triangolo", "triangel", "triangle", "tamburo",
                        "kleine trommel", "snare drum", "tamburo militare", "tam tam", "tam-tam", "bass drums", "drums", "drum",
                        # named in the Gradus corpus and unresolved before:
                        "tamtam", "cymbal", "tambourine", "tamburino",
                        "glockenspiel", "xylophone", "xylophon", "tubular bells",
                        "cloches", "castanets", "cassa")),

    # ── keyboard / plucked ─────────────────────────────────────────────────
    Instrument("Harp", "keyboard", "treble", (24, 104), 0, 0,
               aliases=("harp", "harpe", "arpa", "harfe", "arp", "hrf")),
    Instrument("Piano", "keyboard", "treble", (21, 108), 0, 0,
               aliases=("piano", "pianoforte", "klavier", "pf", "pno", "cembalo",
                        "harpsichord", "clavicembalo", "celesta", "celeste")),
    Instrument("Organ", "keyboard", "treble", (24, 96), 0, 0,
               aliases=("organ", "orgel", "organo", "orgue", "org")),

    # ── voice ──────────────────────────────────────────────────────────────
    Instrument("Soprano", "voice", "treble", (60, 84), 0, 0,
               aliases=("soprano", "sopran", "sopr")),
    Instrument("Alto", "voice", "treble", (55, 79), 0, 0,
               aliases=("alto", "alt", "contralto", "mezzosoprano", "mezzo soprano",
                        "mezzo")),
    Instrument("Tenor", "voice", "treble", (48, 72), -12, 0,
               aliases=("tenore", "tenor", "ten")),
    Instrument("Bass voice", "voice", "bass", (40, 64), 0, 0,
               aliases=("basso", "bass", "bass solo", "bariton", "baritone", "basse")),
    Instrument("Chorus", "voice", "treble", (40, 84), 0, 0,
               aliases=("coro", "chor", "chorus", "choeur")),

    # ── strings ────────────────────────────────────────────────────────────
    Instrument("Violin", "string", "treble", (55, 100), 0, 0,
               aliases=("violin", "violins", "violino", "violini", "violine", "violinen",
                        # no bare "v": a single letter matches OCR noise
                        # ("V}a." for Vla. would resolve to Violin).
                        "violon", "violons", "vl", "vln", "vni")),
    Instrument("Viola", "string", "alto", (48, 88), 0, 0,
               aliases=("viola", "viole", "violas", "violen", "bratsche", "bratschen",
                        "alto viola",
                        "vla", "vl a", "br")),
    Instrument("Cello", "string", "bass", (36, 81), 0, 0,
               aliases=("cello", "violoncello", "violoncelli", "violoncellos",
                        "violoncelle", "violoncelles", "violoncell",
                        "celli", "vc", "vcl", "vlc")),
    Instrument("Contrabass", "string", "bass", (28, 67), -12, 0,
               aliases=("contrabass", "double bass", "contrabasso", "contrabassi",
                        "contrebasse", "contrebasses", "contrabasses", "kontrabass",
                        "kontrabasse", "kontrabaß", "violone", "basse", "bassi",
                        "basso", "cb", "kb", "ctb", "db")),
)

# Aliases one lexicon cannot settle, and what they could be, most-likely first.
# `Tp.` is Timpani in the German and Italian tradition and Trumpet in the
# English one; the alias table has to pick one, and picks the commoner reading
# for this corpus. POSITION settles it properly — a staff below the trumpets is
# the timpani — which is what `score_layouts.resolve_ambiguous_label` does with
# the reading a caller has already made. Keep the first entry equal to whichever
# instrument actually carries the alias above, so nothing changes when the
# score-order prior has no opinion.
AMBIGUOUS_ALIASES: dict[str, tuple[str, ...]] = {
    "tp": ("Timpani", "Trumpet"),
    # "Cor." is Corno (horn) everywhere in the German/Italian tradition, and
    # "Cor" is French for horn too — but a French score's "Cor Anglais" is
    # caught by its own longer alias, so this one is listed for the rarer case
    # of a bare "Cor." on a French wind score meaning cornet.
    "cor": ("Horn", "Trumpet"),
    # "Basso" and "Bässe" are the contrabasses at the foot of an orchestral
    # score and the bass voice under a vocal stave, and the word is identical.
    # Measured over 89 orchestral movements in the Gradus MusicXML library, the
    # voice reading takes Mozart 41 and Mahler 5 out of score order — the label
    # sits directly below the cellos, where no voice belongs. Position settles
    # it, so both readings are offered here rather than one being chosen.
    # First entry stays the lexicon's own answer, so nothing moves when the
    # score-order prior has no opinion.
    "basso": ("Bass voice", "Contrabass"),
    "basse": ("Bass voice", "Contrabass"),
    "bass": ("Bass voice", "Contrabass"),
    "bassi": ("Contrabass", "Bass voice"),
}


def candidates_for_alias(alias: str) -> tuple["Instrument", ...]:
    """Every instrument an ambiguous alias could mean, most-likely first.

    Empty for an alias that is not ambiguous — the caller then has nothing to
    resolve and keeps the lexicon's answer.
    """
    names = AMBIGUOUS_ALIASES.get(alias, ())
    by_name = {inst.name: inst for inst in INSTRUMENTS}
    return tuple(by_name[n] for n in names if n in by_name)


_STRIP_TOKENS = re.compile(
    r"\b(?:i{1,3}v?|iv|vi{0,3}|[0-9]+|solo|soli|tutti|con|e|und|and|a|due|zu|"
    r"muta|div|divisi|senza|sord|coll|col)\b"
)


def normalize_label(text: str) -> str:
    """Fold a printed label to a matchable key: accents stripped, lowercase,
    punctuation and part numbers removed.

    'Flöten 1. 2.' -> 'floten', '2 Clarinetti in B' -> 'clarinetti in b'
    """
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"[.,;:_/\\|()\[\]{}*°º]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_in_key(text: str) -> int | None:
    """Circle-of-fifths offset implied by an 'in X' / '(X)' suffix.

    Written key = concert key + offset, so offset = -fifths(named key):
    'in B' (German B = B-flat) -> +2, 'in A' -> -3, 'in F' -> +1.
    Returns None when the label names no key.
    """
    m = _IN_KEY_RE.search(text)
    if not m:
        return None
    key = m.group(1).lower()
    # German 'B' means B-flat and 'H' means B-natural; on Italian/French title
    # pages a bare 'B' after "in" is also conventionally B-flat.
    if key == "b":
        key = "bb"
    fifths = _KEY_FIFTHS.get(key)
    return None if fifths is None else -fifths


def takes_key(inst: "Instrument") -> bool:
    """Whether this instrument is normally built in a key, and so may carry a
    bare key token after its abbreviation."""
    return inst.chromatic is None or inst.default_fifths_offset != 0


def _parse_bare_key(text: str, alias: str) -> int | None:
    """Circle-of-fifths offset from a bare key token trailing the alias."""
    tail = text[text.find(alias) + len(alias):]
    m = _BARE_KEY_RE.search(tail)
    if not m:
        return None
    key = m.group(1).lower()
    if key == "b":
        key = "bb"
    fifths = _KEY_FIFTHS.get(key)
    return None if fifths is None else -fifths


# Longest alias first so "bass clarinet" wins over "cl", "corno inglese" over "cor".
_ALIAS_INDEX: tuple[tuple[str, Instrument], ...] = tuple(
    sorted(
        ((alias, inst) for inst in INSTRUMENTS for alias in inst.aliases),
        key=lambda pair: -len(pair[0]),
    )
)


# Characters OCR routinely swaps on printed score margins. Only the
# unambiguous families: the i/l/1 stroke group and o/0. Deliberately NOT c/e —
# folding those would merge distinct instrument names.
_OCR_FOLD = str.maketrans({
    "l": "i", "1": "i", "|": "i", "!": "i", "}": "i", "{": "i", "]": "i", "[": "i",
    "0": "o",
})


def _fold_ocr(text: str) -> str:
    return text.translate(_OCR_FOLD)


def _letters(text: str) -> int:
    return sum(1 for c in text if c.isalpha())


def _search(candidate: str, folded: bool) -> tuple[str, Instrument] | None:
    for alias, inst in _ALIAS_INDEX:
        probe = _fold_ocr(alias) if folded else alias
        if re.search(rf"(?<![a-z]){re.escape(probe)}(?![a-z])", candidate):
            return alias, inst
    return None


# Words that name a voice AND size an instrument: "Bass Clarinet", "Tenor
# Tuba", "Alto Flute", "Bb (basso) Horn". The alias index is longest-first, so
# where the label carries no longer alias these win and put a HORN among the
# voices — measured on Beethoven 4 and 9, 31 part names between them.
#
# They stay in the voice aliases, because alone they really do name a voice: a
# chorale's "Bass" is a bass. What settles it is whether the label names
# anything else — see `_prefer_instrument_over_voice`.
VOICE_QUALIFIERS = frozenset({
    "soprano", "alto", "tenor", "bass", "basso", "basse", "bassi",
    "bariton", "baritone", "mezzo",
})


def _all_matches(text: str) -> list["Match"]:
    """Every instrument whose alias matches `text`, longest alias first.

    `lookup` returns only the winner, which is right when a label names one
    instrument and unhelpful when it names one ambiguously.
    """
    norm = normalize_label(text)
    if not norm:
        return []
    stripped = re.sub(r"\s+", " ", _STRIP_TOKENS.sub(" ", norm)).strip()
    probes = (norm, stripped, norm.replace(" ", ""), stripped.replace(" ", ""))
    seen: dict[str, Match] = {}
    for folded in (False, True):
        for candidate in probes:
            if not candidate:
                continue
            probe = _fold_ocr(candidate) if folded else candidate
            for alias, inst in _ALIAS_INDEX:
                a = _fold_ocr(alias) if folded else alias
                if inst.name in seen:
                    continue
                if not re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", probe):
                    continue
                coverage = _letters(alias) / max(1, _letters(candidate))
                seen[inst.name] = Match(inst, inst.default_fifths_offset, alias,
                                        min(1.0, coverage), folded)
        if seen:
            break
    return sorted(seen.values(), key=lambda m: -_letters(m.alias))


def _prefer_instrument_over_voice(text: str, winner: "Match") -> "Match":
    """Let an instrument noun beat a voice word in the same label.

    "Bb (basso) Horn 4" names a horn. It resolved to a bass VOICE because
    "basso" is longer than "horn" and the alias index prefers length — a rule
    that is right for "Bass Clarinet" beating "Bass" and wrong here, because
    the longer alias is the qualifier rather than the noun.

    The discriminator is whether the other reading fires on a DIFFERENT word.
    "Bb (basso) Horn" matches `basso` and `horn`, two words, so the label names
    an instrument and says what size it is. "Basso" alone matches `basso` for
    both the voice and the contrabass — one word, two readings — which is
    genuine ambiguity that only position can settle, and is left to
    `AMBIGUOUS_ALIASES` untouched.
    """
    if winner.instrument.family != "voice" or winner.alias not in VOICE_QUALIFIERS:
        return winner
    for other in _all_matches(text):
        if other.instrument.family != "voice" and other.alias != winner.alias:
            return Match(other.instrument, other.instrument.default_fifths_offset,
                         other.alias, other.coverage, other.ocr_folded)
    return winner


def lookup(text: str) -> Match | None:
    """Match a printed label to an instrument.

    Returns `(instrument, fifths_offset)`, where the offset comes from an
    explicit "in X" when the label carries one, then from a bare trailing key
    token for instruments that take one ("Cor. D."), and from the instrument's
    own default otherwise. Returns None if nothing matches.
    """
    norm = normalize_label(text)
    if not norm:
        return None
    stripped = re.sub(r"\s+", " ", _STRIP_TOKENS.sub(" ", norm)).strip()

    # OCR splits one printed word across spans, so the joined label can carry a
    # space the alias does not ("Tim p." for Timp., "V la." for Vla.). A
    # space-collapsed probe recovers those, tried last so it cannot pre-empt a
    # clean match.
    collapsed = norm.replace(" ", "")
    stripped_collapsed = stripped.replace(" ", "")

    # Exact first; only fall back to the OCR fold if nothing matched cleanly.
    for folded in (False, True):
        for candidate in (norm, stripped, collapsed, stripped_collapsed):
            if not candidate:
                continue
            probe = _fold_ocr(candidate) if folded else candidate
            hit = _search(probe, folded)
            if hit is None:
                continue
            alias, inst = hit
            offset = parse_in_key(norm)
            if offset is None and takes_key(inst):
                offset = _parse_bare_key(probe, _fold_ocr(alias) if folded else alias)
            if offset is None:
                offset = inst.default_fifths_offset
            coverage = _letters(alias) / max(1, _letters(candidate))
            return _prefer_instrument_over_voice(
                text, Match(inst, offset, alias, min(1.0, coverage), folded)
            )
    return None
