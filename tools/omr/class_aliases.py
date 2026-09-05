"""The detector's vocabulary spells some glyphs TWICE, and consumers read one spelling.

The 208-class space is two annotation vocabularies merged end to end: a fine one
at ids 0-135 (`dynamicP`, `articStaccatoAbove`, `tupletBracket`) and a coarse one
at ids 136-207 (`dynamicLetterP`, `articulationStaccato`, `tupleBracket`). Forty
classes carry the SAME name at both ids, so a name-based lookup sees both and
nothing is lost. Thirty-two do not — and every consumer in this pipeline was
written against the fine spelling alone.

So a detection at id 192 (`dynamicLetterF`) is a forte the exporter cannot read:
`export._DYNAMIC_LETTER` has no such key, the letter never joins a word, and the
mark is dropped with no warning anywhere. This is the shape that has cost this
project eight fixes — a signal recognised correctly and thrown away on the way
out — and it is the same fault as `fingering3`/`tuplet3`, where a triplet digit
arrived under two class names and only one was read.

⚠️ **IT COSTS NOTHING TODAY, AND THAT IS NOT A REASON TO LEAVE IT.** Measured
2026-09-04 on the three engraved orchestral fixtures and on a scanned Brahms 1
page (Breitkopf, 1517 detections, scan production weights): the coarse block
fires **zero** times. What makes it live is the LABELING side — 26 of the hollow
campaign's hand-drawn boxes are classed `dynamicLetterF`/`P`/`S`, and
`data/user-labeled/catalog.yaml` carries the coarse spelling at ids 190-195 —
so the next fine-tune trains those ids and the exporter still cannot spell them.

⚠️ **A COARSER NAME IS NOT ALWAYS A SYNONYM.** `numeral4` is not `timeSig4`: the
coarse vocabulary has one numeral class for time signatures, tuplet digits,
fingerings and measure numbers alike, and CLAUDE.md records what a spurious
`timeSig4` costs — five of them fired on barline fragments and shipped a page as
common time. Only exact twins are renamed here. Everything else is recorded in
`COARSER_THAN_CANONICAL` with what it would take to close it, and
`unaccounted()` fails on anything in neither table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

#: Coarse spelling -> the spelling every consumer in this pipeline knows.
#:
#: Each pair was verified by asking every class-name consumer what it returns
#: for both names (`_class_name_to_category`, `rhythm._intrinsic_notehead_duration`
#: / `_rest_duration` / `_flag_duration` / `_tuplet_digit`,
#: `transcribe.articulation_kind`, `clef_geometry.clef_name_from_class`,
#: `export._DYNAMIC_LETTER`) and keeping only the pairs that denote ONE glyph —
#: same articulation and same side, same dynamic letter, same bracket. A pair
#: where the coarse name drops a distinction the fine one makes is NOT here.
ALIASES: dict[str, str] = {
    # ---- dynamics: one letter, two spellings. The headline case. ----
    "dynamicLetterP": "dynamicP",
    "dynamicLetterM": "dynamicM",
    "dynamicLetterF": "dynamicF",
    "dynamicLetterS": "dynamicS",
    "dynamicLetterZ": "dynamicZ",
    "dynamicLetterR": "dynamicR",
    # ---- articulations: only the two that state their side. ----
    # `articulationAccent` / `Staccato` / `Tenuto` do NOT and are below.
    "articulationMarcatoAbove": "articMarcatoAbove",
    "articulationMarcatoBelow": "articMarcatoBelow",
    # ---- structural ----
    "arpeggio": "arpeggiato",
    "tupleBracket": "tupletBracket",
    "legerLine": "ledgerLine",
}

#: Coarse names that are genuinely coarser than the fine vocabulary — each with
#: what it loses, and what it would take to resolve. NOT a suppression list:
#: `unaccounted()` fails on anything absent from both tables, so a new weights
#: file introducing a new class is a loud failure rather than a silent drop.
COARSER_THAN_CANONICAL: dict[str, str] = {
    "articulationAccent": (
        "no SIDE. `articAccentAbove`/`Below` are separate classes and "
        "`articulation_kind` returns the side, which "
        "`_attach_articulations_in_cell` then requires geometry to agree with "
        "— a mark labelled Above that sits below every notehead belongs to "
        "none of them. Renaming would have to invent a side. Resolving it "
        "from the notehead the mark attaches to is a measured change, not a "
        "spelling change."
    ),
    "articulationStaccato": "no SIDE — see `articulationAccent`.",
    "articulationTenuto": "no SIDE — see `articulationAccent`.",
    "tuple": (
        "no NUMBER. `tuplet3`/`tuplet5`/... are separate classes and "
        "`rhythm._tuplet_digit` reads the count off the name. Only `tuplet3` "
        "is acted on at all (3:2), and the tuplet reader abstains rather than "
        "guesses a normal-count, so a `tuple` renamed to `tuplet3` would "
        "assert a triplet the page never claimed."
    ),
    "numeral": "no ROLE — see `numeral0`.",
    **{
        f"numeral{d}": (
            "no ROLE. The coarse vocabulary has one numeral class for time "
            "signatures, tuplet digits, fingerings and measure numbers alike, "
            "and the fine one splits them (`timeSig4`, `tuplet4`, "
            "`fingering4`). ⚠️ Do NOT map this to `timeSig`: CLAUDE.md records "
            "five `timeSig4` fired on barline fragments shipping a 2/4 page as "
            "common time, and a wrong meter cost 390 LilyPond bar-check "
            "failures against 164 for no meter at all."
        )
        for d in range(10)
    },
    "clefC": (
        "no LINE — alto and tenor are the same glyph on different lines. "
        "Already handled and needs no rename: `clef_geometry.clef_name_from_class` "
        "documents that a generic C clef resolves to alto (the commoner), and "
        "`resolve_clef` MEASURES the line off the staff anyway, which is the "
        "whole point of reading clefs geometrically rather than by class."
    ),
    "noteheadFullSmall": (
        "no STAFF POSITION, and `full` is the coarse spelling of `black`. The "
        "position does not matter — pitch is resolved from the notehead's y "
        "against the staff grid, never from the class name — but the SPELLING "
        "did: `rhythm._NOTEHEAD_INTRINSIC` matched `noteheadblack` and not "
        "`noteheadfull`, so this head got a category and no duration. Closed "
        "in the consumer (a prefix, not a rename), because renaming it to "
        "`noteheadBlackOnLineSmall` would assert a line it does not stand on."
    ),
    "noteheadHalfSmall": (
        "no STAFF POSITION, which does not matter (pitch comes from geometry). "
        "Every consumer already returns the same answer as for "
        "`noteheadHalfOnLineSmall`, so there is nothing to rename."
    ),
    "noteheadWhole": (
        "no STAFF POSITION, which does not matter. Every consumer already "
        "agrees with `noteheadWholeOnLine`."
    ),
    "tremoloMark": (
        "no STROKE COUNT (`tremolo1`-`tremolo5`). Nothing downstream reads a "
        "tremolo's count today — both names give category `ornament` and "
        "stop there — so there is nothing to lose yet and nothing to rename."
    ),
    "graceNoteAcciaccatura": (
        "no STEM DIRECTION. Every consumer already agrees with "
        "`graceNoteAcciaccaturaStemUp`. (In isolation this name also reads as "
        "a treble clef, because `clef_geometry.clef_family` takes the leading "
        "letter of the core — harmless and unreachable: every caller filters "
        "`category != 'clef'` first, and this is an `ornament`.)"
    ),
}

#: The committed vocabulary of record. Verified index-for-index against every
#: checkpoint in `omr-weights/` on 2026-09-04, and against
#: `data/user-labeled/catalog.yaml`, so tests need no weights file.
_VOCABULARY_JSON = Path(__file__).parent / "training" / "deepscoresv2_208_classes.json"


#: Where the fine vocabulary ends and the coarse one begins. The 208-class space
#: is two annotation vocabularies concatenated: ids 0-135 fine, 136-207 coarse.
#: Named rather than inlined because `unaccounted()` needs to know which names
#: are the ones this pipeline's consumers were written against — and a bare
#: `[:136]` in that function would read as a slice rather than as a fact about
#: the class space. `test_class_aliases.py` pins the boundary.
FINE_BLOCK_SIZE = 136


def vocabulary() -> list[str]:
    """The 208 class names, in id order."""
    raw = json.loads(_VOCABULARY_JSON.read_text())
    return raw if isinstance(raw, list) else (raw.get("classes") or list(raw.values())[0])


def fine_vocabulary() -> set[str]:
    """The spellings every consumer in this pipeline was written against."""
    return set(vocabulary()[:FINE_BLOCK_SIZE])


def canonical(name: str) -> str:
    """The spelling this pipeline's consumers know. Unchanged if there is no alias."""
    return ALIASES.get(name, name)


def canonicalize_names(names: Mapping[int, str]) -> dict[int, str]:
    """An id->name map with every coarse spelling renamed to its exact twin.

    Applied once, where the detector reads the model's own `names`, so every
    consumer downstream sees one spelling and no call site has to know this
    file exists.
    """
    return {int(i): canonical(str(n)) for i, n in names.items()}


def unaccounted(names: Iterable[str]) -> list[str]:
    """Names with no decision recorded — not a fine spelling, not renamed by
    `ALIASES`, not explained by `COARSER_THAN_CANONICAL`.

    Two things fail here, and both should. A coarse name nobody has classified
    is a silent drop waiting to happen — that is this file's whole subject. And
    a checkpoint whose class space has GROWN beyond the vocabulary of record
    fails too, rather than quietly discarding whatever the new class detects.
    """
    fine = fine_vocabulary()
    return sorted(
        n for n in set(names)
        if n not in fine and n not in ALIASES and n not in COARSER_THAN_CANONICAL
    )
