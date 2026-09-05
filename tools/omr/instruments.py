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

    @property
    def alternatives(self) -> tuple["Instrument", ...]:
        """Every instrument this match's ALIAS could have meant, best first.

        Empty when the alias is unambiguous — which is the common case, and the
        reason a caller may simply read `.instrument`.

        ⚠️ **`lookup` returns ONE answer and an ambiguous alias has more than
        one.** `Basso` is the contrabasses at the foot of an orchestral score
        and the bass voice under a vocal stave; the lexicon has to name one, so
        it names the commoner, and a caller that compares `.instrument.name` to
        a printed label scores the OTHER reading as an error. That silently
        cost `benchmarks/omr-part-staff-join-2026-08/RESULTS.md` and two probes
        in `benchmarks/omr-staff-identity-2026-09/` a correct `Contrabass`
        each.

        The information was always derivable — `candidates_for_alias(m.alias)`
        — but a caller had to know to ask, and three harnesses in a row did
        not. It is a property here so that the ambiguity travels WITH the
        answer instead of beside it. `lookup`'s return value is unchanged, so
        no existing call site moves.
        """
        return candidates_for_alias(self.alias)

    @property
    def is_ambiguous(self) -> bool:
        """Whether the alias that fired could have named another instrument.

        The question `dossier.join_parts_to_slots` asks before letting a label
        PIN a staff, and the question a scorer should ask before calling a
        disagreement an error.
        """
        return len(self.alternatives) > 1


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


# A CONTRABASSOON IS PRINTED AS A BASSOON NAME WITH A CONTRA- QUALIFIER, and
# the two halves vary independently — four languages of noun (fagotto / fagott /
# basson / bassoon, each with its own plural and abbreviation) against four
# languages of qualifier plus the abbreviations a crowded margin actually uses
# ("C. Fag.", "Cfg.", "Cont. Fag."). The spellings are therefore a CROSS
# PRODUCT, and hand-listing it covered six of the two dozen a real score prints.
#
# That is not a cosmetic shortfall. The missing spellings do not ABSTAIN — the
# bassoon noun inside them matches on its own and the qualifier is ignored, so
# `Contra-Fagott` and `Cont. Fag.` read as **Bassoon**, and `C. Fagotto` as
# Bassoon at HIGH confidence, which is enough to pin a staff to the wrong part
# in `dossier.join_parts_to_slots`. It is the same failure the `C. Fag.` comment
# below already records, one spelling at a time.
#
# So the set is DERIVED from the bassoon's own aliases, the move
# `VOICE_QUALIFIERS` makes for the same reason: a hand-list of a cross product
# is a bug with a slow fuse. This does NOT loosen matching — every generated
# string still has to appear in the label, word-bounded, exactly. It completes
# the vocabulary; it does not widen the gate.
#
# The prefixes are only the ones real scores print. `ctr`/`ktr` are plausible
# and unevidenced, so they are left out rather than guessed at.
_BASSOON_ALIASES = ("bassoon", "bassoons", "fagotto", "fagotti", "fagott",
                    "fagotte", "basson", "bassons", "fag", "fg")

_CONTRA_PREFIXES = ("contra", "kontra", "contre", "cont", "kont", "double",
                    "c", "k")

#: Both spacings, because normalization keeps the space a printed "C. Fag."
#: leaves behind while "Cfg." has none. Order does not matter — `_ALIAS_INDEX`
#: sorts every alias longest-first, which is what makes a generated
#: "contrafagott" beat the plain "fagott" inside it.
_CONTRA_ALIASES: tuple[str, ...] = tuple(dict.fromkeys(
    prefix + sep + stem
    for prefix in _CONTRA_PREFIXES
    for stem in _BASSOON_ALIASES
    for sep in ("", " ")
))


# ── the plural is a cross product too, and the hand-list was DIRECTIONAL ─────
#
# A word-bounded alias cannot fire inside its own plural: `oboe` is followed by
# an `s` in `oboes`, which is a letter, so the boundary refuses it. That is why
# the table hand-lists `flutes`, `clarinets`, `horns`, `cors`. It lists them for
# some instruments and not others — and the omission is not a shortfall, it is a
# WRONG ANSWER, because the plurals that DO exist are the short generic nouns:
#
#     `English horns` -> **Horn** (brass!)   `horns` is listed, `english horns` is not
#     `cors anglais`  -> **Horn** (brass!)   `cors`  is listed, `cors anglais`  is not
#     `bass clarinets`-> **Clarinet**        `clarinets` listed, `bass clarinets` not
#
# So pluralising a label systematically DEFEATS the long specific compound and
# hands the staff to the short generic noun inside it — the `Contra-Fagott`
# failure again, and cross-family in two of the three cases above.
# `_ALIAS_INDEX` is longest-first and can only do its job if both lengths of
# alias have a plural; deriving them uniformly restores that ordering.
#
# The rule is deliberately narrow. Only the LAST word is pluralised, and only
# when it is alphabetic and at least four letters, so the two-letter margin
# abbreviations (`vl`, `hr`, `gr tr`) generate nothing — those are printed with
# a stop, never an `s`. `-s` unless the word ends in a sibilant, where English
# takes `-es` (`double bass` -> `double basses`).
#
# ⚠️ This does NOT widen the gate, for the same reason `_CONTRA_ALIASES` does
# not: every generated string still has to appear in the label, word-bounded,
# exactly. It completes the vocabulary. Non-English stems generate inert
# strings (`corno ingleses` is on no page ever printed) and cost nothing but a
# row in the index. Measured: 303 generated forms, ZERO colliding with an
# existing alias of a different instrument.
#
# Plurals that are not formed on the last word are NOT derivable and stay
# hand-listed beside the singular — `cors anglais` and `corni inglesi` inflect
# the NOUN and leave the adjective, which no suffix rule produces.
def _pluralize(alias: str) -> str | None:
    """The English plural of an alias, or None where the rule does not apply."""
    head, _, last = alias.rpartition(" ")
    if len(last) < 4 or not last.isalpha():
        return None
    if last.endswith(("s", "x", "z", "ch", "sh")):
        plural = last + "es"
    else:
        plural = last + "s"
    return f"{head} {plural}" if head else plural


def aliases_of(inst: "Instrument") -> tuple[str, ...]:
    """Every string that may match this instrument: printed aliases + plurals.

    The one place the vocabulary is assembled, so `_ALIAS_INDEX`,
    `VOICE_QUALIFIERS` and `AMBIGUOUS_ALIASES` cannot drift apart.
    """
    out = list(inst.aliases)
    # ⚠️ A REGISTER WORD'S PLURAL IS NOT RELIABLY THE SAME INSTRUMENT, so the
    # voices are excluded from the derivation. In French an orchestra's `Altos`
    # are the VIOLAS and its `Basses` are the double basses — measured, 23 of
    # the 1422-label corpus's `Altos` are Ravel's violas and none is a singer —
    # so deriving `altos` from the voice `alto` invents a cross-family error on
    # the commonest French string label. Where such a plural is real it is
    # listed on the instrument that owns it (`altos` on Viola) and declared
    # ambiguous, which is a decision with evidence behind it rather than a
    # suffix rule. `Chorus` is not a register and keeps its plurals.
    pluralize = not (inst.family == "voice" and inst.name != "Chorus")
    for alias in inst.aliases if pluralize else ():
        plural = _pluralize(alias)
        if plural is not None:
            out.append(plural)
    return tuple(dict.fromkeys(out))


# Aliases are matched after normalization (accents stripped, lowercased,
# punctuation and part numbers removed), so "Flöten" -> "floten", "Fl." -> "fl".
INSTRUMENTS: tuple[Instrument, ...] = (
    # ── woodwind ───────────────────────────────────────────────────────────
    # "fl pic" beside "fl picc": Beethoven 5's fourth movement prints "Fl. Pic."
    # and the one-c spelling missed, so the staff read as a FLUTE — which is not
    # a near-miss but a different part, and on a page whose flutes are on the
    # next staff down it displaces every wind below it. It is flauto piccolo,
    # the Italian name for the instrument, not a flute-and-piccolo shared staff:
    # benchmarks/omr-part-staff-join-2026-08/ground-truth-beet5-p48.json shows
    # the merge count only closes under that reading.
    Instrument("Piccolo", "woodwind", "treble", (74, 108), 12, 0,
               aliases=("piccolo", "picc", "ottavino", "kleine flote", "petite flute",
                        "fl picc", "fl pic")),
    Instrument("Flute", "woodwind", "treble", (59, 96), 0, 0,
               aliases=("flute", "flutes", "flauto", "flauti", "flote", "floten", "fl", "fla", "fl gr")),
    Instrument("Oboe", "woodwind", "treble", (58, 91), 0, 0,
               aliases=("oboe", "oboen", "oboi", "hoboen", "hautbois", "ob")),
    # `cors anglais` and `corni inglesi` inflect the NOUN and leave the
    # adjective, so `_pluralize` cannot make them — and without them the
    # plural resolves to **Horn**, a different FAMILY, because `cors` and
    # `horns` are listed for the horn and the compound is not.
    Instrument("English horn", "woodwind", "treble", (52, 86), -7, 1,
               aliases=("english horn", "cor anglais", "cors anglais",
                        "corno inglese", "corni inglesi", "englisch horn",
                        "englischhorn", "c ing", "c a")),
    # A BASSET HORN IS NOT A HORN — it is the alto clarinet in F, a WOODWIND,
    # and `Basset horn` resolved to Horn [brass] on the bare `horn` inside it
    # at medium confidence. That is the `Tr. Alt.` shape (a qualifier beaten by
    # a substring) with one difference that matters: there was no qualifier to
    # lose, because the lexicon held no basset horn at all, so no longer alias
    # existed for `_ALIAS_INDEX` to prefer.
    #
    # ⚠️ There is NO mechanism here to fix. That a basset horn is a clarinet
    # and a flugelhorn is not a horn is lexical knowledge; no rule derives it
    # from the string. The mechanism question — "which absent instruments are
    # CAPTURED by a shorter alias rather than abstaining?" — is answered in
    # benchmarks/omr-lexicon-2026-09/FINDINGS.md, and the answer is why these
    # four entries exist and why the rest of the absent list needed none.
    Instrument("Basset horn", "woodwind", "treble", (50, 86), -7, 1,
               aliases=("basset horn", "bassett horn", "bassetthorn",
                        "bassett horn", "corno di bassetto", "corni di bassetto",
                        "cor de basset", "cors de basset")),
    Instrument("Clarinet", "woodwind", "treble", (50, 91), None, 2,
               aliases=("clarinet", "clarinets", "clarinetto", "clarinetti", "klarinette",
                        "klarinetten", "clarinette", "clarinettes", "cl", "clar", "kl",
                        "klar")),                    # Mahler: "A-Klar."
    Instrument("Bass clarinet", "woodwind", "treble", (38, 79), None, 2,
               # NOT "cl b": on real scores "Cl. B." means clarinet in B-flat far
               # more often than bass clarinet, which is written "B. Cl." / "Bcl".
               aliases=("bass clarinet", "clarinetto basso", "bassklarinette",
                        "clarinette basse", "b cl", "bcl")),
    Instrument("Bassoon", "woodwind", "bass", (34, 72), 0, 0,
               aliases=_BASSOON_ALIASES),
    # `_CONTRA_ALIASES` regenerates every spelling that used to be hand-listed
    # here — including "c fag" beside the closed-up "cfag", the pair whose
    # absence once read a contrabassoon as a BASSOON. `contraf` is kept
    # separately because it is a TRUNCATION rather than qualifier-plus-noun, so
    # no cross product produces it.
    Instrument("Contrabassoon", "woodwind", "bass", (22, 60), -12, 0,
               aliases=_CONTRA_ALIASES + ("contraf",)),   # Mahler: "Contraf."
    Instrument("Saxophone", "woodwind", "treble", (49, 89), None, 3,
               aliases=("saxophone", "saxophon", "sax", "sassofono")),
    # Boulanger scores one; without it "Bass Sarrusophone" resolves on the word
    # "Bass" and lands in the voices, fifteen part names adrift.
    Instrument("Sarrusophone", "woodwind", "bass", (28, 67), 0, 0,
               aliases=("sarrusophone", "sarrusophon", "sarrus")),
    # Bach and Handel score them and the lexicon abstained; `2 recorders` is in
    # the IMSLP instrumentation residual.
    Instrument("Recorder", "woodwind", "treble", (60, 96), 0, 0,
               aliases=("recorder", "flauto dolce", "flauti dolci", "blockflote",
                        "blockfloten", "flute a bec")),
    # The baritone oboe Strauss writes for (Alpensinfonie, Salome). Absent, and
    # it abstained rather than misresolving — a gap, not a fault. Two works in
    # the IMSLP residual name it.
    Instrument("Heckelphone", "woodwind", "bass", (46, 79), -12, 0,
               aliases=("heckelphone", "heckelphon", "hckl")),

    # ── brass ──────────────────────────────────────────────────────────────
    Instrument("Horn", "brass", "treble", (41, 77), None, 1,
               # "hr" is the German/English abbreviation (Hörner) — safe as a
               # bare 2-letter alias because the word-boundary index refuses a
               # letter on either side, so it cannot fire inside "hrf" (Harp)
               # or any other alias. Measured 2026-09-03 over 1422 real margin
               # labels: 16 hits, all Brahms 1 / Breitkopf horn staves, 0
               # collisions with anything else.
               aliases=("horn", "horns", "corno", "corni", "horner", "cor", "cors",
                        "hn", "hr")),
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
               # "trpt" is a distinct 4-letter abbreviation from "tpt" above —
               # not a typo of it, a different printed shorthand ("Trpt." on
               # Brahms 1 / Breitkopf) — and unambiguous: 0 collisions over
               # every alias in this table and over 1422 real margin labels,
               # where it fires only on that edition's trumpet staves.
               aliases=("trumpet", "trumpets", "tromba", "trombe", "trompete", "trompeten",
                        "trompette", "trompettes", "tr", "tpt", "trpt", "clarino", "clarini",
                        "tromp")),                   # Mahler: "B-Tromp."
    # `Tr.` is Trombe AND Tromboni, and one page prints both: Beethoven 5
    # (IMSLP984073) p.47 reads `Tr.` over the trumpets and, four staves below,
    # `Tr. Alt. / Tr. Ten. / Tr. Bas.` over the three trombones of the finale.
    # So the abbreviation cannot separate them and the part name beside it can:
    # a trombone section is scored by REGISTER and a trumpet section by number
    # and key ("Tr. I", "Trombe in C"), never the other way round. These aliases
    # are longer than the bare `tr`, so a register-qualified `Tr.` reads as the
    # trombone it is while a bare one keeps the Trumpet the table names above.
    # "Tr. Bas." stays the trombone HERE but is listed in AMBIGUOUS_ALIASES,
    # because tromba bassa is real — position settles it, this row is only the
    # answer when the prior has no opinion.
    #
    # NOT "tr b": on a real score "Tr. B." is a trumpet in B-flat far more often
    # than a bass trombone, the same trap as "Cl. B." above. A bass TRUMPET does
    # exist (Wagner, Strauss) but prints "Tromba bassa" / "Basstrompete", which
    # carries its own noun and never reaches these.
    Instrument("Trombone", "brass", "bass", (34, 72), 0, 0,
               aliases=("trombone", "trombones", "trombono", "tromboni", "posaune",
                        "posaunen", "trb", "tbn", "pos",
                        "tr alt", "tr alto", "tr ten", "tr tenor", "tr tenore",
                        "tr bas", "tr bass", "tr basso")),
    # "tenor tuba" before the voice aliases can reach it: the alias index is
    # longest-first, so without it "Tenor Tuba in B-flat" resolves to the VOICE
    # Tenor and takes Holst's Planets out of score order on all eight movements.
    Instrument("Tuba", "brass", "bass", (26, 65), 0, 0,
               aliases=("tenor tuba", "tenortuba", "tuba", "tuben", "basstuba",
                        "bass tuba", "tb")),
    # ⚠️ A CORNET SECTION CANNOT BE ENCODED WITHOUT THIS, and it is the French
    # and Russian repertoire, not an exotic: Berlioz, Franck and Tchaikovsky
    # all print trumpets and cornets on separate staves. `2 cornets` is the
    # single largest line in the IMSLP instrumentation residual — 14 of 99
    # unparsed fragments, one missing entry costing 14% of it.
    #
    # It ABSTAINED rather than misresolving (`cor` is blocked by the `n` after
    # it, `corno` by the `e`), so this is a pure gap: nothing that resolves
    # today changes. Built in B-flat or A like the trumpet, hence the same
    # key-dependent chromatic and the same default.
    Instrument("Cornet", "brass", "treble", (52, 84), None, 2,
               aliases=("cornet", "cornett", "kornett", "cornetto", "cornetti",
                        "cornetta", "piston", "pistons", "cnt")),
    # Not a horn, and it never reached the horn either — `horn` inside
    # `flugelhorn` is preceded by a letter, so the closed-up spelling abstained.
    # The SPACED spelling did not: `Flügel Horn` resolved to Horn. Both forms
    # are listed.
    Instrument("Flugelhorn", "brass", "treble", (52, 84), None, 2,
               aliases=("flugelhorn", "flugel horn", "flugelhorner", "fluegelhorn",
                        "flicorno", "bugle")),
    # Berlioz and Mendelssohn score the ophicleide where a modern edition puts
    # a tuba; two IMSLP works name it. Absent and abstaining.
    Instrument("Ophicleide", "brass", "bass", (28, 67), 0, 0,
               aliases=("ophicleide", "ophicleides", "oficleide", "ophikleide")),
    Instrument("Euphonium", "brass", "bass", (34, 72), 0, 0,
               aliases=("euphonium", "euphonion", "eufonio")),
    # The ophicleide's predecessor; Berlioz and Mendelssohn score both.
    Instrument("Serpent", "brass", "bass", (28, 67), 0, 0,
               aliases=("serpent", "serpente", "serpentone")),

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
                        # "Gr. Tr." and "Kl. Tr." are the Grosse and Kleine
                        # Trommel. They have to out-rank the two-letter "tr"
                        # (Trompete) and "kl" (Klarinette), which the
                        # longest-alias-wins index does. Before this, Mahler 5
                        # p.4 read its bass drum as a TRUMPET and its snare as
                        # a CLARINET — and the bass drum reading PINNED.
                        "gr tr", "kl tr",
                        "glockenspiel", "xylophone", "xylophon", "tubular bells",
                        "cloches", "castanets", "cassa",
                        # named in the IMSLP instrumentation residual and
                        # unresolved before. `bells` is safe beside the longer
                        # `tubular bells`, which the longest-first index still
                        # prefers, and cannot fire inside `cowbells` because
                        # that is one word.
                        "bells", "cowbells", "glocken", "glocke", "gong", "tamtams",
                        "wind machine", "windmaschine", "slapstick", "peitsche",
                        "rute", "ruthe", "anvil", "amboss", "crotales",
                        "marimba", "vibraphone", "chimes", "woodblock",
                        "tenor drum", "field drum", "ratsche", "ratchet",
                        "sleigh bells", "bell", "guiro", "hammer",
                        "sleigh bell")),

    # ── keyboard / plucked ─────────────────────────────────────────────────
    Instrument("Harp", "keyboard", "treble", (24, 104), 0, 0,
               aliases=("harp", "harpe", "arpa", "harfe", "arp", "hrf")),
    Instrument("Piano", "keyboard", "treble", (21, 108), 0, 0,
               aliases=("piano", "pianoforte", "klavier", "pf", "pno", "cembalo",
                        "harpsichord", "clavicembalo", "celesta", "celeste")),
    Instrument("Organ", "keyboard", "treble", (24, 96), 0, 0,
               aliases=("organ", "orgel", "organo", "orgue", "org")),
    # ⚠️ FAMILY follows the Harp's precedent, not the organology. A mandolin
    # and a guitar are plucked strings, but `Harp` is filed "keyboard" here and
    # the families are consumed as SCORE POSITION (a staff-identity workstream
    # measures family precision 0.955 against instrument 0.873) — these staves
    # sit with the harp, above the strings, never among the violins. Filing
    # them "string" would be right about the instrument and wrong about every
    # consumer.
    Instrument("Mandolin", "keyboard", "treble", (55, 91), 0, 0,
               aliases=("mandolin", "mandoline", "mandolino", "mandolina")),
    Instrument("Guitar", "keyboard", "treble", (40, 84), -12, 0,
               aliases=("guitar", "guitare", "gitarre", "chitarra")),

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
                        # A bare "viol" — "Erste Viol.", "Zweite Viol." The
                        # alias index matches on word boundaries, so it cannot
                        # fire inside "violen", "viola" or "violoncelle".
                        "violon", "violons", "vl", "vln", "vni", "viol")),
    # `Altos` is what a FRENCH score calls its violas, and it is the largest
    # single string in the margin corpus that resolved to nothing: 23 of
    # Ravel's Boléro labels, plus two more in the reference part names. Listed
    # here rather than derived from the voice `alto`, because a register word's
    # plural belongs to whichever instrument the language gives it to — see
    # `aliases_of`. `alti` is the Italian. Both are declared ambiguous: a
    # chorus really does have altos.
    Instrument("Viola", "string", "alto", (48, 88), 0, 0,
               aliases=("viola", "viole", "violas", "violen", "bratsche", "bratschen",
                        "alto viola", "altos", "alti",
                        "vla", "vl a", "br")),
    Instrument("Cello", "string", "bass", (36, 81), 0, 0,
               aliases=("cello", "violoncello", "violoncelli", "violoncellos",
                        "violoncelle", "violoncelles", "violoncell",
                        "celli", "vc", "vcl", "vlc",
                        "vcelle")),                  # Mahler: "Vcelle. get."
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
_DECLARED_AMBIGUOUS_ALIASES: dict[str, tuple[str, ...]] = {
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
    # "Tr. Bas." is Trombone basso in the Italian tradition and Tromba bassa —
    # the bass trumpet Wagner and Strauss write for — in the German. The lexicon
    # reads it as the trombone, which is much the commoner, and listing it here
    # says the reading is not certain enough to PIN a staff on
    # (`dossier.join_parts_to_slots`). Position settles it, as it does for `Tp.`.
    "tr bas": ("Trombone", "Trumpet"),
    # French `Altos` / Italian `Alti` are the VIOLAS of an orchestra and the
    # altos of a chorus, and the word is identical. The lexicon reads the
    # violas, which is what every occurrence in both corpora is; listing it
    # here says the reading may not PIN a staff.
    "altos": ("Viola", "Alto"),
    "alti": ("Viola", "Alto"),
}

#: The declared table plus the plurals `_pluralize` derives from it, because an
#: ambiguity is a property of the WORD and not of its number — a French score's
#: `Basses` is exactly as undecidable as its `Basse`, and only the singular was
#: listed. `dossier.join_parts_to_slots` reads this as the set of aliases that
#: may not PIN a staff, so a plural missing from it is a wrong pin, not a
#: missing one. Declared entries always win a collision.
AMBIGUOUS_ALIASES: dict[str, tuple[str, ...]] = {
    **{p: names
       for alias, names in _DECLARED_AMBIGUOUS_ALIASES.items()
       if (p := _pluralize(alias)) is not None},
    **_DECLARED_AMBIGUOUS_ALIASES,
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
    r"muta|div|divisi|get|geteilt|senza|sord|coll|col)\b"
)


def normalize_label(text: str) -> str:
    """Fold a printed label to a matchable key: accents stripped, lowercase,
    punctuation and part numbers removed.

    'Flöten 1. 2.' -> 'floten', '2 Clarinetti in B' -> 'clarinetti in b'
    """
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    # The hyphen is a SEPARATOR, not punctuation to drop silently. German
    # scores build abbreviations with it constantly — "A-Klar.", "B-Tromp.",
    # "Es-Klar." — and keeping it defeats the word-boundary match: `kl` inside
    # `a-klar` is followed by a letter, so nothing fires and the staff reads as
    # nothing at all. Measured on Mahler 5 p.4, where it costs the clarinets
    # and the trumpets.
    t = re.sub(r"[.,;:_/\|()\[\]{}*°º-]+", " ", t)
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


def _rescued_by_a_longer_alias(inst: "Instrument", target: str) -> bool:
    """Whether `inst` holds an alias at least as long as anything that fires on
    `target` — the property that makes `_ALIAS_INDEX`'s longest-first ordering
    return the right instrument. Used by the tests, not by `lookup`."""
    return any(
        re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", target)
        for a in aliases_of(inst)
    )


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
        ((alias, inst) for inst in INSTRUMENTS for alias in aliases_of(inst)),
        key=lambda pair: -len(pair[0]),
    )
)


# Characters OCR routinely swaps on printed score margins. Only the RARE
# confusions: the i/l/1 stroke group, o/0, and v/y. A fold is applied to both
# the alias and the candidate and then matched as a word-bounded substring, so
# it is safe only where the folded character does not distinguish real
# instrument names — which is why the SET is deliberately small.
#
# `y -> v` is the one added after the others (a printed "Violino II." read as
# "Yiolino II.", surfaced 2026-09-02 in labelling). It is safe for the same
# reason the stroke group is: `y` is rare in the vocabulary — only `tympani`
# and `xylophone` carry one, and both resolve on the EXACT pass before the fold
# ever runs — so folding it collides with nothing. Measured: zero collisions
# over all 260 aliases and every margin-label corpus truth string, and it
# resolves the whole V->Y family (Yiolino/Yiola/Yioloncello/Yni).
#
# Deliberately NOT the COMMON-letter confusions — c/e, a/u, b/h, n/m. Folding
# those merges distinct names and widens what garbage resolves, and a wrong
# resolution PINS a staff to the wrong part (`dossier.join_parts_to_slots`
# pins on any unambiguous alias, folded or not). The cost is real and specific:
# the margin corpora's own unrecovered reads `Oh.`->`Ob.` and `Fug.`->`Fag.`
# would need exactly b/h and a/u, and are left unread rather than bought at that
# price. See benchmarks/omr-margin-labels-2026-08/OCR_CONFUSIONS_2026-09-02.md.
_OCR_FOLD = str.maketrans({
    "l": "i", "1": "i", "|": "i", "!": "i", "}": "i", "{": "i", "]": "i", "[": "i",
    "0": "o",
    "y": "v",
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
#
# DERIVED from the voice instruments' own aliases rather than hand-listed,
# because the hand-listed set WAS the bug: it held the spelled-out `alto` and
# `tenor` and not the abbreviated `alt` and `ten` that Italian and German scores
# actually print, so `Fl. Alt.` and `Cl. Alt.` resolved to a singer at high
# confidence. Any register word that can win the alias index is by construction
# an alias of a voice, so deriving the set closes the whole family at once
# instead of one spelling at a time.
#
# `Chorus` is excluded: "Coro" / "Chor" name an ensemble, never a register, and
# a label that says both ("Coro. Corni") should keep the chorus.
VOICE_QUALIFIERS = frozenset(
    alias
    for inst in INSTRUMENTS
    if inst.family == "voice" and inst.name != "Chorus"
    for alias in aliases_of(inst)
)

# A VOICE IS NOT THE ONLY INSTRUMENT WHOSE NAME DOUBLES AS A SIZE WORD.
# `Contrabass` is the string bass AND the qualifier on `Contrabass clarinet`,
# `Contrabass trombone`, `Contrabass tuba` — and being ten letters it beats
# every one of those nouns in a longest-first index, so all three resolved to a
# STRING, the same cross-family error `Basset horn` made in the other
# direction. `Contrabass tuba` did it at HIGH confidence, which is what pins a
# staff to the wrong part.
#
# Only the full qualifier spellings, never `cb` / `kb` / `db`: a two-letter
# alias next to another two-letter alias is a coin flip, and no score prints
# `Cb. Clar.`
SIZE_QUALIFIERS = frozenset(
    alias
    for inst in INSTRUMENTS
    if inst.name == "Contrabass"
    for alias in aliases_of(inst)
    if alias.startswith(("contra", "kontra", "contre", "double"))
)

QUALIFIERS = VOICE_QUALIFIERS | SIZE_QUALIFIERS


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


def _adjacent(norm: str, a: str, b: str) -> bool:
    """Do these two aliases stand SIDE BY SIDE, in either order, in `norm`?

    ⚠️ On `norm`, never on the `_STRIP_TOKENS` output, and that is the whole
    point of the test. A CONJUNCTION is what separates a compound instrument
    from a condensed staff — "Contrabass clarinet" is one instrument, and
    "Contrabassi e Violoncelli" is two staves' worth printed on one — and the
    two labels are word-for-word identical once `e` is stripped. `_STRIP_TOKENS`
    deletes exactly the evidence that tells them apart, so the adjacency test
    reads the string BEFORE it runs.
    """
    gap = r"[^a-z]+"
    for first, second in ((a, b), (b, a)):
        if re.search(rf"(?<![a-z]){re.escape(first)}{gap}{re.escape(second)}(?![a-z])",
                     norm):
            return True
    return False


def _prefer_instrument_over_qualifier(text: str, winner: "Match") -> "Match":
    """Let an instrument noun beat a SIZE word standing next to it.

    "Bb (basso) Horn 4" names a horn. It resolved to a bass VOICE because
    "basso" is longer than "horn" and the alias index prefers length — a rule
    that is right for "Bass Clarinet" beating "Bass" and wrong here, because
    the longer alias is the qualifier rather than the noun. "Contrabass
    trombone" and "Contrabass tuba" are the same sentence with the string bass
    playing the qualifier, and they were wrong the same way.

    Two conditions, and the second is the one added on 2026-09-05:

    1. the other reading fires on a DIFFERENT word. "Basso" ALONE matches
       `basso` for both the voice and the contrabass — one word, two readings —
       which is genuine ambiguity only position can settle, and is left to
       `AMBIGUOUS_ALIASES` untouched;
    2. for a SIZE qualifier only, the two words are ADJACENT. A qualifier
       modifies the noun beside it; anything between them means the label is
       naming two things, not sizing one. Without it, "Contrabassi e
       Violoncelli" — the commonest label at the foot of an orchestral score —
       becomes a cello.

    ⚠️ **The adjacency test does NOT apply to the voice qualifiers, and that
    asymmetry is measured, not tidy.** A condensed staff pairs two
    INSTRUMENTS; it never pairs an instrument with a voice, so the voice half
    of this rule has nothing to protect and adjacency only costs it reach.
    Applied to both halves it regressed `Horn in B♭ basso` — a real part name
    in the reference corpus — from Horn to a bass VOICE, because "in Bb"
    stands between the noun and its qualifier. The voice half is therefore
    left exactly as it was measured in 2026-08, and the new condition rides
    only on the aliases that needed it.
    """
    if winner.alias not in QUALIFIERS:
        return winner
    norm = normalize_label(text)
    needs_adjacency = winner.alias in SIZE_QUALIFIERS
    for other in _all_matches(text):
        # `family != "voice"` is the 2026-08 rule's own test and is kept
        # verbatim, so a label naming a chorus beside a register word still
        # reads as the chorus it did before.
        if other.instrument.family == "voice" or other.alias in QUALIFIERS:
            continue
        if other.alias == winner.alias:
            continue
        if needs_adjacency and not _adjacent(norm, winner.alias, other.alias):
            continue
        return Match(other.instrument, other.instrument.default_fifths_offset,
                     other.alias, other.coverage, other.ocr_folded)
    return winner


#: Kept under the old name: it is what the tests and the findings files call it,
#: and the voices are still the bulk of what it does.
_prefer_instrument_over_voice = _prefer_instrument_over_qualifier


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
            return _prefer_instrument_over_qualifier(
                text, Match(inst, offset, alias, min(1.0, coverage), folded)
            )
    return None
