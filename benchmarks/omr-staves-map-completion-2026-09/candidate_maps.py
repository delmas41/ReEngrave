"""Candidate `staves` maps for the five unmapped scan-gate rows.

NOT hand-read by me — every allocation here is TRANSCRIBED from works.json's
own hand-read prose:

  * `mahler-…-p2`  : `condensation.staves_as_printed`, a complete 22-entry
                     structured map already in the file.
  * `mahler-…-p3/4/5`: the `notes` field of each row, which spells the future
                     `staves_as_printed` out instrument by instrument
                     ("Fag.1/2->[10], Contraf.->[11], …"), drafted by the
                     sessions that verified those windows against the print.

So this module is a TRANSCRIPTION, and its own correctness is checkable by
reading it against those two sources. It is not evidence and it is not a
proposal to merge — `probe_mappable.py` asks whether the consumer accepts it.

⚠️ TWO CONVENTIONS ARE MINE AND ARE MARKED.

  `absent`  a reference part with NO printed staff on this page. The Mahler
            pages are one system each and tacet-suppress whole sections, so
            p3 prints no flute staff at all. `page_normalise` refuses to drop
            a part (rule: a normalised truth missing a part scores better for
            the wrong reason), so these are folded onto a nominated staff.
            EVERY ONE IS ASSERTED SILENT over the row's window before it is
            folded, and `probe_mappable.py` re-runs the fold against a
            different target to show the output does not move.

  horn/trumpet splits carried from p2's own `sensitivity_allocation`
            discussion: which of the three horn parts share the upper staff is
            genuinely 50/50 and was priced there at 8 edits.
"""
from __future__ import annotations

# Reference part index -> name, from the trimmed truth's <part-list>.
# 0 Piccolo            1,2 Vier Flöten      3,4 Drei Hoboen     5 English Horn
# 6,7 Drei Klarinetten 8 Bass Clarinet      9 C Clarinet        10 Zwei Fagotte
# 11 Contrafagotte     12,13,14 Sechs Hörner 15,16 F Trumpet
# 17,18 Vier Trompeten 19,20 Drei Posaunen  21 Tuba             22 Pauken
# 23 Becken            24 Grosse Trommel    25 Kleine Trommel   26 Tamtam
# 27 Violin            28 Erste Violinen    29,30,31 Zweite Violinen
# 32,33 Violen         34,35 Violoncelle    36,37 Bässe

def _s(name, parts, lines=5, **kw):
    d = {"name": name, "parts": list(parts)}
    if lines != 5:
        d["lines"] = lines
    d.update(kw)
    return d


# ---------------------------------------------------------------- Mahler p2
# Verbatim from works.json condensation.staves_as_printed, MINUS the one entry
# whose `parts` is empty (the printed `Becken u. Gr.Trommel von einem
# geschlagen` rule, which the reference has no part for). Recorded, not lost:
# see UNREPRESENTABLE below.
MAHLER_P2 = [
    _s("Vier Flöten", [0, 1, 2]),
    _s("Drei Hoboen", [3, 4, 5]),
    _s("Drei Klarinetten in A", [6, 7, 8, 9]),
    _s("Zwei Fagotte", [10]),
    _s("Contrafagott", [11]),
    _s("Sechs Hörner in F (upper)", [12, 13]),
    _s("Sechs Hörner in F (lower)", [14]),
    _s("Vier Trompeten in B (upper)", [15, 17]),
    _s("Vier Trompeten in B (lower)", [16, 18]),
    _s("Drei Posaunen", [19, 20]),
    _s("Tuba", [21]),
    _s("Pauken", [22]),
    _s("Becken", [23], lines=1),
    _s("Grosse Trommel", [24], lines=1),
    _s("Kleine Trommel", [25], lines=1),
    _s("Tamtam", [26], lines=1),
    _s("Erste Violinen", [27, 28]),
    _s("Zweite Violinen", [29, 30, 31]),
    _s("Violen", [32, 33]),
    _s("Violoncelle", [34, 35]),
    _s("Bässe", [36, 37]),
]

# ---------------------------------------------------------------- Mahler p3
# From the row's own `notes`: "Fag.1/2->[10], Contraf.->[11], Hörner 1/3/5 +
# 2/4/6 -> {12,13,14} (split ambiguous, as priced on p.2), B-Tromp.1/2->[15,17]
# with 17 pinned by the continuing fanfare, B-Tromp.3/4->[16,18],
# Posaunen->[19,20], Tuba->[21], Becken->[23], Gr.Tr.->[24],
# Erste Viol.->[27,28], Zweite Viol.->[29,30,31], Violen->[32,33],
# Vcelle.->[34,35], Bässe->[36,37]."
MAHLER_P3 = [
    _s("Fag. 1/2", [10], absent=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
    _s("Contraf.", [11]),
    _s("F-Hörner 1/3/5", [12, 13]),
    _s("F-Hörner 2/4/6", [14]),
    _s("B-Tromp. 1/2", [15, 17]),
    _s("B-Tromp. 3/4", [16, 18]),
    _s("Posaunen 1/2/3", [19, 20]),
    _s("Tuba", [21], absent=[22, 25, 26]),
    _s("Becken", [23], lines=1),
    _s("Gr.Tr.", [24], lines=1),
    _s("Erste Viol.", [27, 28]),
    _s("Zweite Viol.", [29, 30, 31]),
    _s("Violen", [32, 33]),
    _s("Vcelle.", [34, 35]),
    _s("Bässe", [36, 37]),
]

# ---------------------------------------------------------------- Mahler p4
# From the row's own `notes`: "Hoboen->[3,4,5], A-Klar.->[6,7,8,9], Fag.->[10],
# Contraf.->[11], F-Hörner 1.3.5 + 2.4.6 -> {12,13,14}, B-Tromp. 1.2->[15,17],
# B-Tromp. 3.4->[16,18], Posaunen->[19,20], Tuba->[21], Pauken->[22],
# Becken->[23], Gr.Tr.->[24], Kl.Tr.->[25], Erste Viol.->[27,28],
# Zweite Viol.->[29,30,31], Violen->[32,33], Vcelle. get. (two staves)->[34],[35],
# Bässe get. (two staves)->[36],[37]."
MAHLER_P4 = [
    _s("Hoboen 1.2.3", [3, 4, 5], absent=[0, 1, 2]),
    _s("A-Klar. 1.2.3", [6, 7, 8, 9]),
    _s("Fag. 1/2", [10]),
    _s("Contraf.", [11]),
    _s("F-Hörner 1.3.5", [12, 13]),
    _s("F-Hörner 2.4.6", [14]),
    _s("B-Tromp. 1.2", [15, 17]),
    _s("B-Tromp. 3.4", [16, 18]),
    _s("Posaunen", [19, 20]),
    _s("Tuba", [21]),
    _s("Pauken", [22], absent=[26]),
    _s("Becken", [23], lines=1),
    _s("Gr.Tr.", [24], lines=1),
    _s("Kl.Tr.", [25], lines=1),
    _s("Erste Viol.", [27, 28]),
    _s("Zweite Viol.", [29, 30, 31]),
    _s("Violen", [32, 33]),
    _s("Vcelle. get. (upper)", [34]),
    _s("Vcelle. get. (lower)", [35]),
    _s("Bässe get. (upper)", [36]),
    _s("Bässe get. (lower)", [37]),
]

# ---------------------------------------------------------------- Mahler p5
# From the row's own `notes`: "p.4's allocation minus Hoboen plus Tamtam->[26]."
MAHLER_P5 = [
    _s("A-Klar. 1.2", [6, 7, 8, 9], absent=[0, 1, 2, 3, 4, 5]),
    _s("Fag. 1/2", [10]),
    _s("Contraf.", [11]),
    _s("F-Hörner 1.3.5", [12, 13]),
    _s("F-Hörner 2.4.6", [14]),
    _s("B-Tromp. 1.2", [15, 17]),
    _s("B-Tromp. 3.4", [16, 18]),
    _s("Posaunen", [19, 20]),
    _s("Tuba", [21]),
    _s("Pauken", [22]),
    _s("Becken", [23], lines=1),
    _s("Gr.Tr.", [24], lines=1),
    _s("Kl.Tr.", [25], lines=1),
    _s("Tamtam", [26], lines=1),
    _s("Erste Viol.", [27, 28]),
    _s("Zweite Viol.", [29, 30, 31]),
    _s("Violen", [32, 33]),
    _s("Vcelle. get. (upper)", [34]),
    _s("Vcelle. get. (lower)", [35]),
    _s("Bässe get. (upper)", [36]),
    _s("Bässe get. (lower)", [37]),
]

# ------------------------------------------------------------------- Bach
# 12 printed staves per system; the trimmed truth has ELEVEN parts, because
# the Cembalo is a GRAND STAFF — two printed staves, one encoded part. The map
# idiom is one entry per printed staff naming the parts it CARRIES, and there
# is no part for the second Cembalo staff to name. See probe_mappable.py:
# a 1:1 map here is an identity transform and removes nothing.
BACH_P1 = [
    _s("Violini I", [0]),
    _s("Violini II", [1]),
    _s("Violini III", [2]),
    _s("Viole I", [3]),
    _s("Viole II", [4]),
    _s("Viole III", [5]),
    _s("Violoncelli I", [6]),
    _s("Violoncelli II", [7]),
    _s("Violoncelli III", [8]),
    _s("Contrabasso", [9]),
    _s("Cembalo (grand staff, 2 printed staves)", [10], printed_staves=2),
]

CANDIDATES = {
    "mahler-sym5-mvt1-local-p2": MAHLER_P2,
    "mahler-sym5-mvt1-local-p3": MAHLER_P3,
    "mahler-sym5-mvt1-local-p4": MAHLER_P4,
    "mahler-sym5-mvt1-local-p5": MAHLER_P5,
    "bach-brandenburg3-mvt1-468678-p1": BACH_P1,
}

#: Printed staves the REFERENCE cannot represent, by row. Recorded so the map's
#: entry count can be reconciled with the page's printed count.
UNREPRESENTABLE = {
    "mahler-sym5-mvt1-local-p2": [
        "Becken u. Gr.Trommel von einem geschlagen (1 line) — works.json: "
        "'printed, labelled, and carrying its own meter and rest — the "
        "reference has no part for it'"],
    "bach-brandenburg3-mvt1-468678-p1": [
        "Cembalo lower staff — the reference encodes the Cembalo as ONE part "
        "spanning both printed staves (a grand staff), and the map idiom "
        "cannot split one part across two entries"],
}


def flat(row_id: str) -> list[dict]:
    """The map as `page_normalise` wants it: `absent` folded into `parts`.

    ⚠️ ORDER IS LOAD-BEARING AND THE FOLDS GO LAST. `page_normalise` keeps
    `parts[idx[0]]` and merges the rest into it, so the FIRST index decides
    which part's bar survives a `silent_all` measure — i.e. whose RESTS the
    derived truth carries. Sorting the folds in ahead of the printed part
    made a silent Piccolo the kept part of the Fagotte staff; measured, that
    moved the output (`fold_target_control.identical_content: false` on all
    three rows) purely in rest spelling. Printed first, folds after.
    """
    out = []
    for spec in CANDIDATES[row_id]:
        parts = list(spec["parts"]) + list(spec.get("absent") or [])
        out.append({"name": spec["name"], "parts": parts})
    return out


def printed_only(row_id: str) -> list[dict]:
    """The map WITHOUT the absent folds — what the page actually prints."""
    return [{"name": s["name"], "parts": list(s["parts"])}
            for s in CANDIDATES[row_id]]


def flat_sorted(row_id: str) -> list[dict]:
    """The same map with each entry's `parts` SORTED — works.json's own shape.

    `merge_additions.shape_problems` refuses an entry whose `parts` is not
    sorted-unique, and every already-merged row satisfies that. But
    `page_normalise` keeps `parts[idx[0]]` and merges the rest INTO it, so the
    first index decides whose bar survives a `silent_all` measure — i.e. whose
    RESTS the derived truth carries. On the existing rows the two conventions
    agree by luck (a condensed staff's parts are contiguous and ascending, so
    the lowest index IS the printed staff's own first part). A tacet fold
    breaks that luck: sorting puts a silent Piccolo ahead of the Fagotte.

    Priced as its own arm in `price_maps.py` rather than argued about.
    """
    return [{"name": s["name"], "parts": sorted(s["parts"])}
            for s in flat(row_id)]


def five_line_only(row_id: str) -> list[dict]:
    """DIAGNOSTIC arm: the one-line percussion entries folded into the
    five-line staff above them, so the derived truth has exactly as many parts
    as the page has FIVE-LINE staves.

    ⚠️ THIS IS NOT A CANDIDATE MAP AND MUST NOT BE MERGED. It says the Becken
    is printed on the Pauken staff, which is false. It exists to separate two
    things the honest map conflates: the cost of a percussion part we never
    read, and the cost of musicdiff's part alignment SHEDDING four arbitrary
    parts because the truth is longer than the prediction (measured: the parts
    it sheds are the string section, not the percussion).
    """
    out: list[dict] = []
    for spec in CANDIDATES[row_id]:
        parts = list(spec["parts"]) + list(spec.get("absent") or [])
        if spec.get("lines") == 1 and out:
            out[-1] = {"name": out[-1]["name"] + " +perc",
                       "parts": out[-1]["parts"] + parts}
        else:
            out.append({"name": spec["name"], "parts": parts})
    return out


def absent_parts(row_id: str) -> list[int]:
    out: list[int] = []
    for spec in CANDIDATES[row_id]:
        out += list(spec.get("absent") or [])
    return sorted(out)
