"""How many players a printed staff carries, read off its margin label.

A conductor's page CONDENSES: one staff labelled `Flauti` is played by two
flutes, and a reference encoding may hold two parts behind it. This module
reads the label for evidence of more than one player.

⚠️ **WHAT THIS CANNOT KNOW.** Whether the reference SPLITS a condensed staff is
a property of the encoding, not of the engraving. Measured in
`benchmarks/omr-condensed-parts-2026-09/FINDINGS.md`: the identical printed
label `Flauti` is TWO reference parts in the Gradus Beethoven 5 and ONE in the
Gradus Dvořák 9, on pages engraved the same way. So a label reader is evidence
about the PAGE and only a hypothesis about the FILE, and every tier here is
reported separately so the two can be priced apart.

The tiers, weakest evidence last:

  explicit   a counted enumeration is PRINTED — `Corni I.II.`, `4 Hörner 1./2.`,
             `Fag. 1/2`. The page itself names the players on this staff.
  compound   two different instrument nouns joined by `e` / `u.` / `und` —
             `Violoncello e Basso`. Two parts by construction.
  numeral    a leading count — `2 Flöten`, `Drei Hoboen`. ⚠️ the count is of the
             SECTION, not of this staff: Brahms prints `4 Hörner in C 1./2.`
             on a staff carrying two, so a numeral is only used where no
             enumeration narrows it.
  plural     a bare plural section noun — `Flauti`, `Trombe`, `Hörner`. This is
             the tier the Dvořák control falsifies as a splitting rule.
"""
from __future__ import annotations

import re
import unicodedata

# Section nouns whose plural form implies more than one player. Singular forms
# are deliberately NOT here — `Flauto` is one flute.
_PLURAL_SECTIONS = {
    "flauti", "floten", "floeten", "flutes", "flotes",
    "oboi", "hoboen", "oboen", "hautbois", "oboes",
    "clarinetti", "klarinetten", "clarinettes", "clarinets",
    "fagotti", "fagotte", "fagotts", "bassons", "bassoons",
    "corni", "horner", "hoerner", "cors", "horns",
    "trombe", "trompeten", "trompettes", "trumpets",
    "tromboni", "posaunen", "trombones",
    "violini", "violinen", "violons", "violins",
    "viole", "violen", "altos", "violas",
    "violoncelli", "violoncelle", "celli", "cellos",
    "contrabassi", "kontrabasse", "basse", "bassi",
}

# Written-out counts, the languages these editions print in.
_WORD_NUMBERS = {
    "due": 2, "tre": 3, "quattro": 4,
    "zwei": 2, "drei": 3, "vier": 4, "funf": 5, "sechs": 6,
    "two": 2, "three": 3, "four": 4,
    "deux": 2, "trois": 3, "quatre": 4,
}

# `I.II.` / `1./2.` / `1.2.` / `1/2` — an enumeration of the players on THIS
# staff. Matched as a run so `I.II.III.` counts three.
_ROMAN = r"(?:IV|I{1,3}|VI{0,3}|V)"
_ENUM_ROMAN = re.compile(rf"(?<![a-z])(?:{_ROMAN}[./]+\s*){{2,}}", re.I)
# `1./2.`, `1/2`, `1.2.` — the separator may be more than one character, which
# is what `4 Hörner in C 1./2.` needs: with a single-character class the run
# does not match and the leading `4` (the SECTION size) wins instead.
_ENUM_ARABIC = re.compile(r"(?<!\d)\d\s*[./]+\s*\d(?:\s*[./]+\s*\d)*")


def _fold(text: str) -> str:
    """Lowercase and strip accents, so `Hörner` and `Horner` are one word."""
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def _enumeration_count(folded: str) -> int:
    m = _ENUM_ARABIC.search(folded)
    if m:
        return len([p for p in re.split(r"[./\s]+", m.group(0)) if p.strip()])
    # Roman numerals. Each must be FOLLOWED by a separator (`I.II.`), which is
    # what keeps a key name out: `in E` and `in C` carry no dot, and `i` inside
    # a word is excluded by the lookbehind.
    for m in _ENUM_ROMAN.finditer(folded):
        parts = [p for p in re.split(r"[./\s]+", m.group(0)) if p.strip()]
        if len(parts) >= 2:
            return len(parts)
    return 0


def players_for_label(label: str | None, instrument: str | None = None,
                      *, tiers: tuple[str, ...] = (
                          "explicit", "compound", "numeral", "plural")) -> int:
    """Players on the staff this label names. 1 when nothing says otherwise.

    `tiers` selects which evidence is admitted, so an arm can price one tier at
    a time. Returns 1 for an unreadable or missing label — abstention is the
    fallback and a page with no labels must export unchanged.
    """
    if not label:
        return 1
    folded = _fold(label)

    if "explicit" in tiers:
        n = _enumeration_count(folded)
        if n >= 2:
            return n

    if "compound" in tiers:
        # `Violoncello e Basso`, `Becken u. Gr.Trommel` — two nouns, one staff.
        halves = re.split(r"\s(?:e|ed|u\.?|und|and|et|&)\s", folded)
        if len(halves) >= 2 and all(h.strip() for h in halves):
            # Only when both halves carry a word that is not a key or a number.
            if all(re.search(r"[a-z]{3,}", h) for h in halves):
                return len(halves)

    if "numeral" in tiers:
        m = re.match(r"\s*(\d+)\s+[a-z]", folded)
        if m and 2 <= int(m.group(1)) <= 8:
            return int(m.group(1))
        first = folded.strip().split()[:1]
        if first and first[0] in _WORD_NUMBERS:
            return _WORD_NUMBERS[first[0]]

    if "plural" in tiers:
        for word in re.findall(r"[a-z]+", folded):
            if word in _PLURAL_SECTIONS:
                return 2

    return 1
