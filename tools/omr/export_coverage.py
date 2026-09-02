"""Does everything the truth would SHOW survive into our output?

WHY THIS EXISTS. Seven times now the defect has been the same shape: the
pipeline recognises something correctly and then loses it on the way to the
file. Beams, augmentation dots, dynamics, tuplet markers, slur arcs, fermatas,
accidentals — 0.3164 to 0.1242 on the benchmark, and almost none of it from
making the detector better.

Six of the seven were found FORENSICALLY: a metric bucket grew, someone opened
the op list, and the cause was underneath. That works, and it only ever finds
what is already large.

THE OBVIOUS PROACTIVE CHECK DOES NOT WORK, and knowing why is the whole design.
Auditing the detector's class space for classes nothing downstream mentions
calls accidentals CONSUMED — because they are, into `pitch` — and clefs and
time-signature digits likewise, into `<attributes>`. Run against the benchmark
it surfaced `repeatDot` x4 and `fingering3` x1 and nothing else, while a
64-edit gap sat in plain sight. The question is not "does anything consume this
class". It is:

    Does everything the truth would SHOW survive into our output?

Answered by counting elements in the truth file and in ours. The signature of
an export gap is categorical — truth has N, we emit ZERO — which is exactly
what distinguishes it from a recognition shortfall, where we emit some and miss
some. All seven read `truth N, ours 0`.

WHAT IT DOES NOT LOOK AT. A MusicXML file is mostly not notation: metadata,
page layout, MIDI playback hints, part bookkeeping. We emit none of that and
never will, and a check that reported it would list 55 elements, be ignored,
and then be deleted. `VISIBLE` is therefore a curated list of things a reader
sees on the page, and everything else is out of scope by construction.

⚠️ KNOWN DEFECT, FOUND WITHIN AN HOUR OF LANDING — THE ARTIFACTS ARE NOT PINNED.
`survey()` reads the benchmark's `.omr.musicxml` files from disk, and those are
gitignored artifacts of WHATEVER CONFIGURATION LAST RAN THE EVAL. That makes the
three repository tests below depend on something no test controls:

  * a run with `--direction-text` leaves `<words>` in them, so `words` — listed
    in KNOWN_GAPS as a flag decision — is suddenly emitted, and the
    staleness test fails;
  * fixtures predating a fix are missing elements the exporter now writes, and
    the seven-stay-fixed test fails.

Both are FALSE REDS: the exporter is healthy and the test is reading a stale or
differently-configured artifact. That is the failure mode most likely to get a
check switched off, so it is written here rather than in a commit message.

The real fix is for the check to run against freshly generated output rather
than a leftover artifact, which is a design change and wants its own session.
The cheaper interim fix is a provenance stamp: have `orchestral_eval` record the
commit and the configuration it ran with beside the fixtures, and have these
three tests SKIP unless that stamp says "default config, current tree". Neither
is done. Until one is, a red here means "check what last wrote the fixtures"
before it means "the exporter regressed".

    python3 -m tools.omr.export_coverage        # the report
    python3 -m tools.omr.export_coverage --all  # including what is accepted
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
WORKS = ("beethoven-sym5-mvt1", "brahms-sym1-mvt1", "mahler-sym5-mvt1")

#: MusicXML elements that are NOTATION — ink a reader sees on the page. Only
#: these are checked. Each is here because losing it would change what the score
#: says, which is the test for membership; `<midi-program>` and `<tenths>` fail
#: it, and so do `<voice>` and `<duration>`, which are bookkeeping for a
#: renderer rather than marks on paper.
VISIBLE: dict[str, str] = {
    "accidental":    "the sharp/flat/natural the engraver drew",
    "articulations": "staccato, accent, tenuto — the marks on a notehead",
    "accent":        "an accent specifically, the commonest of them here",
    "barline":       "a repeat, a double bar, a final bar",
    "bar-style":     "which kind of barline it is",
    "beam":          "the beams joining a group",
    "dot":           "an augmentation dot",
    "dynamics":      "p, f, sf — the dynamic letters",
    "fermata":       "a pause over a note or a rest",
    "lyric":         "sung text under a note",
    "metronome":     "a metronome mark",
    "notations":     "the block that carries ties, slurs, tuplets, fermatas",
    "slur":          "a phrase slur",
    "stem":          "which way a stem points",
    "tied":          "the tie's notation half",
    "time-modification": "the 3-in-the-time-of-2 of a tuplet",
    "tuplet":        "the tuplet bracket",
    "wedge":         "a crescendo or diminuendo hairpin",
    "words":         "a printed direction — legato, Allegro con brio",
}

#: Elements the truth shows that we knowingly do not emit, each with the reason
#: and its size. This is an INVENTORY, not a suppression list: it is the honest
#: statement of what the exporter still drops, and everything in it is either a
#: decision already taken or an open item someone can pick up. Anything NOT here
#: is a new gap and fails the test.
KNOWN_GAPS: dict[str, str] = {
    "accent": (
        "EIGHTH GAP, open and cheap. Mahler's truth has 6 and the detector "
        "finds exactly 6 (articAccentBelow x5, articAccentAbove x1). Nothing "
        "consumes them. This is the next one to close."
    ),
    "articulations": (
        "The <notations> wrapper the accents would sit in — same item as "
        "`accent`, and it appears the moment that does."
    ),
    "wedge": (
        "NINTH GAP, open. Mahler's truth has 6 hairpins; the detector finds 4 "
        "(dynamicCrescendoHairpin x2, dynamicDiminuendoHairpin x2). Partial "
        "detection, so this one is not purely an export fix."
    ),
    "barline": (
        "Documented limitation — repeat signs are dropped on export, tied to "
        "multi-type barline classification. NOTES.md items 5 and 6."
    ),
    "bar-style": (
        "The style of a barline, so it arrives with `barline` and is the "
        "same open item — a repeat cannot be written without it."
    ),
    "lyric": (
        "We do not read vocal text at all and there is no detector for it. "
        "Out of scope rather than missing."
    ),
    "metronome": (
        "Read by `--direction-text` (off by default, needs .venv-surya), which "
        "emits <words>. The structured <metronome> form is not built."
    ),
    "words": (
        "Read by `--direction-text`, which is OFF BY DEFAULT — so this is a "
        "flag decision, not a gap. With it on, `wrong direction` is 151 -> 7."
    ),
    "stem": (
        "`transcribe` computes stem direction and uses it for voice splitting; "
        "the exporter never writes <stem>up/down</stem>. Truth-visible and "
        "musicdiff does not score it, so it costs nothing today — which is why "
        "it stayed invisible to every forensic hunt."
    ),
}


_ELEMENT = re.compile(r"<([a-z][a-z0-9-]*)[ />]")


def element_counts(xml: str) -> Counter:
    return Counter(_ELEMENT.findall(xml))


def compare(truth_xml: str, ours_xml: str) -> list[tuple[str, int, int]]:
    """`(element, in_truth, in_ours)` for every VISIBLE element we emit NONE of.

    Only the categorical case — truth has some, we have zero. Emitting fewer
    than the truth is a recognition shortfall and belongs to the accuracy
    metric, not here; conflating the two is what would make this noisy enough
    to ignore.
    """
    t, o = element_counts(truth_xml), element_counts(ours_xml)
    return [(name, t[name], o[name])
            for name in sorted(VISIBLE)
            if t[name] > 0 and o[name] == 0]


def survey(fixtures: Path = FIXTURES,
           works: tuple[str, ...] = WORKS) -> list[tuple[str, int, int]]:
    """The same comparison pooled over every benchmark work on disk."""
    truth, ours = Counter(), Counter()
    for work in works:
        t, o = fixtures / f"{work}.musicxml", fixtures / f"{work}.omr.musicxml"
        if not (t.is_file() and o.is_file()):
            continue
        truth += element_counts(t.read_text())
        ours += element_counts(o.read_text())
    if not truth:
        return []
    return [(name, truth[name], ours[name])
            for name in sorted(VISIBLE)
            if truth[name] > 0 and ours[name] == 0]


def unexplained(found: list[tuple[str, int, int]]) -> list[tuple[str, int, int]]:
    """The gaps that are not already written down in `KNOWN_GAPS`."""
    return [g for g in found if g[0] not in KNOWN_GAPS]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                    help="list the known gaps too, with their reasons")
    args = ap.parse_args(argv)

    found = survey()
    if not found:
        print("no fixtures on disk — run `orchestral_eval` first"
              if not (FIXTURES / f"{WORKS[0]}.musicxml").is_file()
              else "every visible element the truth shows also appears in ours")
        return 0
    new = unexplained(found)
    if args.all:
        print("VISIBLE elements the truth shows and we emit none of:\n")
        for name, t, o in found:
            note = KNOWN_GAPS.get(name, "*** NOT EXPLAINED ***")
            print(f"  {name:18s} truth {t:4d}   ours {o}\n      {note}\n")
    for name, t, o in new:
        print(f"NEW EXPORT GAP: <{name}> — the truth has {t} and we emit none. "
              f"{VISIBLE[name]}.", file=sys.stderr)
    if new:
        print("\nIf this is deliberate, add it to KNOWN_GAPS with the reason. "
              "If it is not, it is the shape that has cost this project seven "
              "fixes.", file=sys.stderr)
    return 1 if new else 0


if __name__ == "__main__":
    raise SystemExit(main())
