"""The graded identity corpus — hand-read truth, in ONE place.

Phase 0 of `docs/scope-identity-upstream-2026-09-06.md`.  Neither standing
benchmark can see staff identity at all: part names do not reach OMR-NED
(musicdiff does not score them), so the identity layer is invisible to the
headline figure, to the 20-row scan gate and to `orchestral_eval`.  Everything
this module holds was hand-read by earlier sessions and lived in two separate
scripts; unifying it is what makes an identity change judgeable.

## What "judgeable" means, and why the rule is strict

Only **FULL systems** are scored: a system of exactly N staves in a page region
whose maximum is N IS that region's lineup, in printed order — nothing can be
added to a full lineup.  REDUCED systems (tacet staves suppressed) are NOT
scored, because which parts were dropped is a fact about the page this harness
does not know.  That costs coverage — 44.3% of the pooled document — and it is
the price of a truth that cannot be argued with.

## The names are a MUSICIAN's, not the lexicon's

Every name below is the canonical `instruments.Instrument.name` value a
musician would give the staff, read off the printed margin at 600 dpi.  It is
deliberately NOT what `instruments.lookup` returns for the printed string: a
lexicon fault must show up as an error, not score as correct against itself.

## Provenance of each lineup

* `beet5` — `benchmarks/omr-absent-instrument-veto-2026-09/probe/
  score_full_systems.py`, crops `p1-margin.png`, `p44-margin.png`.
* `brahms1` — `benchmarks/omr-brahms-lineup-2026-09/probe/
  score_brahms_lineups.py`, crops in that benchmark's `out/crops/`, with the
  work's IMSLP roster (`source_kind: catalog`, independent of the reference
  encoding) corroborating the inventory.
* `dvorak9` — the Beethoven scorer's second work; carried for completeness,
  no committed arm reaches it here.

⚠️ **Two facts a span model would get wrong, both recorded by the hand
reading.**  Brahms movement 3 is TWELVE staves — no contrabassoon, no timpani —
so lineups do not only GROW toward the finale.  And Brahms's second movement
changes its lineup WITHOUT changing its staff count (a horn staff out, a solo
violin in), which is why two different 14-staff lineups appear below.
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Lineups: (first_page, last_page, n_staves) -> instruments, top to bottom.
# ─────────────────────────────────────────────────────────────────────────────
LINEUPS: dict[str, list[tuple[int, int, int, list[str]]]] = {
    "beet5": [
        # movements 1-3, twelve staves — crops/p1-margin.png
        (0, 43, 12, ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Trumpet",
                     "Timpani", "Violin", "Violin", "Viola", "Cello",
                     "Contrabass"]),
        # finale, seventeen staves — crops/p44-margin.png
        (44, 200, 17, ["Piccolo", "Flute", "Oboe", "Clarinet", "Bassoon",
                       "Contrabassoon", "Horn", "Trumpet", "Timpani",
                       "Trombone", "Trombone", "Trombone", "Violin", "Violin",
                       "Viola", "Cello", "Contrabass"]),
    ],
    "brahms1": [
        # movement 1, fourteen staves — p000-margin-all-sys0{,b}.png
        (0, 25, 14, ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                     "Horn", "Horn", "Trumpet", "Timpani", "Violin", "Violin",
                     "Viola", "Cello", "Contrabass"]),
        # movement 2 from the violin-solo entry — a DIFFERENT fourteen:
        # six string staves and ONE horn staff.  p033/p035-margin-all-*.png
        (33, 35, 14, ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                      "Horn", "Trumpet", "Timpani", "Violin", "Violin",
                      "Violin", "Viola", "Cello", "Contrabass"]),
        # movement 3, TWELVE staves — no Kontrafagott, no Pauken.
        # p036-margin-all-look.png
        (36, 44, 12, ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Horn",
                      "Trumpet", "Violin", "Violin", "Viola", "Cello",
                      "Contrabass"]),
        # finale, sixteen staves; 3 trombones braced over TWO staves, so slot 9
        # is the SECOND TROMBONE staff and not a tuba (the work has no tuba).
        # p045-margin-all-{A,B,C}.png
        (45, 85, 16, ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon",
                      "Horn", "Horn", "Trumpet", "Trombone", "Trombone",
                      "Timpani", "Violin", "Violin", "Viola", "Cello",
                      "Contrabass"]),
    ],
    "dvorak9": [
        (0, 200, 15, ["Flute", "Oboe", "Clarinet", "Bassoon", "Horn", "Horn",
                      "Trumpet", "Trombone", "Trombone", "Timpani", "Violin",
                      "Violin", "Viola", "Cello", "Contrabass"]),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# IMPOSSIBLE names — an instrument the document cannot be printing there.
#
# This is the WEAK grade, and it is kept beside the identity grade rather than
# folded into it: `impossible` can only fall, so it scores a categorically
# wrong name traded for an ordinarily wrong one as FREE.  The two columns
# disagree on the Brahms `refuse`/`search` arms and the harness shows the
# disagreement rather than averaging it away.
#
# Rules as the veto-pricing and span-composition sessions defined them, so
# their recorded figures reproduce here exactly.
# ─────────────────────────────────────────────────────────────────────────────
IMPOSSIBLE: dict[str, tuple[int, tuple[str, ...]]] = {
    #        first page the instrument may appear,  names
    "beet5": (44, ("Piccolo", "Contrabassoon", "Trombone")),
    "brahms1": (45, ("Trombone", "Tuba")),
}

#: Names no page of the work may carry at all.  Brahms 1 has NO tuba (IMSLP
#: `InstrDetail` "3, 0" — three trombones, zero tubas), so a `Tuba` anywhere is
#: impossible, not merely early.  Reported separately so the page-scoped rule
#: above still reproduces the recorded numbers.
NEVER: dict[str, tuple[str, ...]] = {
    "beet5": (),
    "brahms1": ("Tuba",),
}

#: Which physical engraving each work is.  Used ONLY as the calibration fold:
#: two scans of one plate are one engraving, and a held-out split by row would
#: leak.
ENGRAVING = {
    "beet5": "litolff-beethoven5-imslp984073",
    "brahms1": "breitkopf-brahms1-imslp317803",
    "dvorak9": "simrock-dvorak9",
}

PUBLISHER = {
    "beet5": "Litolff",
    "brahms1": "Breitkopf",
    "dvorak9": "Simrock",
}


def truth_for(work: str, page: int, n_staves: int):
    """The printed lineup, or `(None, None)` if this system is not judgeable."""
    for lo, hi, k, names in LINEUPS.get(work, []):
        if lo <= page <= hi and n_staves == k:
            return f"p{lo}-{hi}/{k}", names
    return None, None


def is_impossible(work: str, page: int, name: str | None) -> bool:
    """The RECORDED rule, page-scoped, and nothing else.

    ⚠️ Deliberately does NOT fold in `NEVER`.  The veto-pricing and
    span-composition sessions' figures (Brahms 36 / 149 / 0) are the assertion
    `selftest.py` makes, and widening the rule here would break the harness's
    only tie to an independently measured number.  The work-wide names are a
    SEPARATE column — see `is_never`.
    """
    if not name:
        return False
    first, names = IMPOSSIBLE.get(work, (0, ()))
    return page < first and name in names


def is_never(work: str, name: str | None) -> bool:
    """A name the work does not contain ANYWHERE.

    Reported apart from `impossible` because it catches a different thing: the
    Brahms finale's `Trombone -> Tuba` x17 residue, which is inside the pages
    where a trombone IS legal and so is invisible to the page-scoped rule, but
    which names an instrument the work does not have at all.
    """
    return bool(name) and name in NEVER.get(work, ())
