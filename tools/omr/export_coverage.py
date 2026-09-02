"""Does everything the truth would SHOW survive into our output?

WHY THIS EXISTS. Eight times now the defect has been the same shape: the
pipeline recognises something correctly and then loses it on the way to the
file. Beams, augmentation dots, dynamics, tuplet markers, slur arcs, fermatas,
accidentals, articulations. Most of the benchmark's fall from its 0.3164
opening is those, and almost none of it is a better detector. (The CURRENT
figure is not restated here; it lives in CLAUDE.md's OMR-NED section and
nowhere else, for the reason `tools/omr/accuracy_record.py` gives. An earlier
draft of this paragraph quoted 0.1242 and was stale within a day.)

THE LIST, NUMBERED, because the ordinal has been reconstructed from memory
twice and collided both times. `0eb1271` calls articulations "the seventh time"
while `d112052` and `docs/next-steps-omr-2026-09-01.md` §2b both call printed
accidentals the seventh — the two were written on branches that could not see
each other. Counted once, in the order they were fixed:

    1  beams                d272ac3   detected, never exported
    2  augmentation dots    52ba215   detected, counted twice
    3  dynamics             89277a2   detected, never exported
    4  tuplet markers       d5079d5   sitting unread in the JSON
    5  slur arcs            bae93b1   detected, never rejoined across a barline
    6  fermatas             (in §3)   detected at 0.90-0.95, never exported
    7  printed accidentals  d112052   folded into <alter>, <accidental> dropped
    8  articulations        0eb1271   ten artic* classes, one docstring mention
    9  hairpins                       OPEN — and not purely an export fix

(8 landed on main in `bdda54d` on 2026-09-02. An earlier draft of this list
said it was unmerged and told the reader to run `git show 0eb1271` before
rewriting it; that warning did its job for about an hour.)

Six of the first seven were found FORENSICALLY: a metric bucket grew, someone
opened the op list, and the cause was underneath. That works, and it only ever
finds what is already large.

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

WHERE OUR SIDE COMES FROM, AND WHY IT IS NOT THE FILE ON DISK. Until 2026-09-02
this read the benchmark's `<work>.omr.musicxml` — a gitignored artifact of
whatever configuration last ran the eval — so the three repository tests
depended on something no test controlled. That was reported as a source of
false REDS (a `--direction-text` run leaves `<words>`; a run predating a fix is
missing elements the exporter now writes), and it was. The worse failure was
the other one, and it went unnamed: **a false GREEN.** Break `to_musicxml`
right now and those tests read yesterday's file and pass. A check whose whole
promise is "caught the day it appears" cannot be reading yesterday's output.

So it exports its own. `<work>.omr.json` is the transcription — the exact dict
`orchestral_eval` hands to `to_musicxml` — and re-exporting it here is
byte-identical to what the eval wrote (verified on all three works) and costs
0.06 s for the set. Our side is therefore always THIS TREE'S exporter, on every
run of the suite, with no eval run needed and none trusted.

THE CONFIGURATION IS READ OFF THE ARTIFACT, not off a stamp beside it.
`transcribe` records its own knobs in the result it returns, and leaves a
`direction_text` block there iff that reader ran. A sidecar file recording the
same thing can drift out of step with the artifact it describes; a field inside
the artifact cannot. That turns the `--direction-text` false red into a REAL
ASSERTION in both directions: with the reader off, `<words>` is a known gap;
with it on and words placed, `<words>` MUST appear, and its absence is exactly
the shape this module exists to catch.

WHAT REMAINS UNPINNED, stated plainly because the next person meeting a red
should know where to look first:

  * **the truth side.** `<work>.musicxml` is generated by `orchestral_eval`'s
    `excerpt()` and is gitignored too. It moves when the fixture render changes
    — as it did on 2026-09-02, when `_restore_rest_fermatas` put 22 fermatas
    back — and a truth that has LOST an element makes that element look like a
    gap somebody closed rather than one still open.
  * **transcribe-side staleness.** A JSON older than a change in `transcribe`
    is still stale. That residue is smaller than it sounds: the JSON stores raw
    DETECTIONS rather than events, so grouping, rhythm, pitch, beams and slurs
    are all re-derived here, and every one of the seven fixes was on the export
    side of that line and IS picked up by a fresh export of an old JSON. What
    stays frozen is detection and transcribe's own annotation passes, which
    move accuracy rather than the categorical presence this check tests.

Neither is silent: `--all` prints what configuration wrote each artifact and
whether the tree has moved under it since.

THREE THINGS ARE REFUSED RATHER THAN POOLED, because the counts are added across
works and each of these makes the sum mean something other than what it says: a
work whose transcription is absent (`incomplete`), a set written under mixed
configurations (`disagreement`), and — the one the report cannot see — a truth
file older than the render that produced it. The first two abstain loudly. The
third is why `--all` prints provenance at all.

`cbd8ca2` got to the flag half of this first, by a different route: a
`FLAG_DEPENDENT` set exempted from the staleness check, with the observation —
correct, and the reason that commit's shape survives here — that EXEMPTING IS
NOT SKIPPING. A skip switches the whole check off for anyone whose last run used
a flag; an exemption leaves it running and correct either way.

Knowing the configuration takes that one step further, because the exemption is
symmetric and the fact is not. Exempting `words` is right while the reader is
off and too weak once it is on: a reader that placed 15 words against an
exporter that wrote none would be the NEXT one of the nine above, on the newest
layer, and an exemption says nothing about it. So the entries stay named, and
what the configuration buys is the ability to ASSERT rather than excuse.

    python3 -m tools.omr.export_coverage        # the report
    python3 -m tools.omr.export_coverage --all  # including what is accepted
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.omr import accuracy_record
from .export import to_musicxml

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "benchmarks" / "omr-orchestral-e2e" / "fixtures"

#: Every work the default benchmark writes into `FIXTURES` — read from the
#: benchmark's definition rather than restated, so widening the benchmark cannot
#: leave this check surveying a subset of the fixtures sitting on disk. Three
#: canonical works until 2026-09-02, eleven since.
#:
#: ⚠️ `survey()` pools, so more works cut both ways: the truth side sees more
#: kinds of notation (which is why the widening is worth doing here at all),
#: while a gap in ONE work is masked if another work emits that element. The
#: categorical signature is `truth N, ours 0` POOLED, and it always was — this
#: widens what the check can see without changing what it means.
WORKS = accuracy_record.BENCHMARK_WORKS

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
    "wedge": (
        "NINTH GAP, open — and genuinely unclaimed: `git log --all -S wedge` "
        "and `-S hairpin` over export.py and transcribe.py return nothing on "
        "any branch. Mahler's truth has 6 hairpins; the detector finds 4 "
        "(dynamicCrescendoHairpin x2, dynamicDiminuendoHairpin x2). Partial "
        "detection, so unlike the eight above this is not purely an export "
        "fix, and closing it cannot be priced from this inventory alone. "
        "Widened to 11 works the truth carries 17 hairpins across three of them "
        "— Mahler 5 (6), Tchaikovsky 6 (6), Brahms 4 (5) — three times what the "
        "three-work corpus could show."
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
        "A tempo mark is read by the direction reader and emitted as <words>; "
        "the structured <metronome> form is not built. So this is a gap under "
        "BOTH configurations — unlike `words` beside it — and it is NOT in "
        "FLAG_DEPENDENT. Measured rather than reasoned: on a full "
        "`--direction-text` eval <metronome> is still absent from the export."
    ),
    "words": (
        "CONDITIONAL — the only entry here that is, and since 2026-09-02 the "
        "reader that fills it is ON by default. It stays written down because "
        "the OTHER configuration is still reachable: `--no-direction-text`, and "
        "any machine with neither .venv-surya nor Tesseract, where no words are "
        "placed and none can be exported. With words actually placed the "
        "explanation is spent and a missing <words> is a real gap — "
        "`expected_gaps` is where that applies. The `wrong direction` 151 -> 7 "
        "pair is pre-boundary — the three canonical works — and does not carry "
        "to the 11-work set, where all eleven truths print words (52 in total, "
        "most of them Brahms 1's 16 and Bruckner's 10)."
    ),
    "stem": (
        "`transcribe` computes stem direction and uses it for voice splitting; "
        "the exporter never writes <stem>up/down</stem>. Truth-visible and "
        "musicdiff does not score it, so it costs nothing today — which is why "
        "it stayed invisible to every forensic hunt."
    ),
}

#: The entries of `KNOWN_GAPS` whose status is a FLAG decision rather than a
#: fact about the exporter. `cbd8ca2` named this set; what changed here is that
#: knowing the configuration lets the check ASSERT on them instead of merely
#: excusing them — an explanation of the form "we only emit this behind a flag"
#: stops explaining anything the moment the flag is on.
#:
#: ⚠️ `metronome` was in this set and has been TAKEN OUT, measured rather than
#: reasoned: on a `--direction-text` run of the whole benchmark, `<metronome>`
#: is STILL absent from the export. The reader emits a tempo mark as <words>
#: and the structured form is not built, so it is an ordinary unconditional gap
#: — and exempting it would hide a real regression on the day it is built.
FLAG_DEPENDENT: frozenset[str] = frozenset({"words"})


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


@dataclass(frozen=True)
class Run:
    """One benchmark work, with our side EXPORTED BY THIS TREE.

    `ours` is `to_musicxml` applied to the stored transcription here and now —
    never the `.omr.musicxml` sitting beside it, which was written by whatever
    tree last ran the eval. `stale_export` records whether those two differ. It
    is not a failure: it means the tree has moved since the eval ran, which is
    the ordinary state of things and the first thing worth knowing if something
    else here goes red.
    """
    work: str
    truth: str
    ours: str
    result: dict[str, Any]
    stale_export: bool

    @property
    def direction_reader_ran(self) -> bool:
        """Did the direction pass execute at all?

        ⚠️ NOT "was there a reader to run". `transcribe` sets `available`
        False only when the pass RAISED — `_optional_pass_failure`, an import
        error, a defect. A machine with neither `.venv-surya` nor Tesseract
        raises nothing: `read_directions` returns normally with
        `reason="no OCR rung available"`, so `available` is True and
        `n_placed` is 0. An earlier version of this docstring had that
        backwards.

        Which is why the conditional gap is gated on `directions_placed` and
        not on this: a reader with nothing to read and a reader that read
        nothing both export no words, and neither is a broken promise.
        """
        return bool((self.result.get("direction_text") or {}).get("available"))

    @property
    def directions_placed(self) -> int:
        """How many words the reader actually attached to the music.

        Distinct from `direction_reader_ran`: on a real scan the reader runs,
        proposes candidates, and the lexicon refuses every one of them, so it
        places nothing. That is the reader working correctly, and it must not
        be read as an exporter that dropped something.
        """
        return int((self.result.get("direction_text") or {}).get("n_placed") or 0)

    @property
    def configuration(self) -> str:
        """One line naming what wrote this artifact, for a failure message."""
        r = self.result
        bits = [f"dpi={r.get('dpi')}", f"conf={r.get('conf_threshold')}",
                f"headers={r.get('read_headers')}",
                f"dossier={'yes' if r.get('dossier') else 'no'}"]
        if r.get("direction_text") is None:
            bits.append("direction-text=off")
        elif self.direction_reader_ran:
            bits.append(f"direction-text=on ({self.directions_placed} placed)")
        else:
            bits.append("direction-text=ASKED FOR BUT ABSTAINED")
        if self.stale_export:
            bits.append("the .omr.musicxml beside it is from an older tree")
        return ", ".join(bits)


def load_run(work: str, fixtures: Path | None = None) -> Run | None:
    """Read one work's truth and transcription, and export the transcription.

    `fixtures` resolves at CALL time rather than binding `FIXTURES` as a default
    argument, so pointing the check at another directory — a `--direction-text`
    run written to its own `--work-dir`, say — works by reassigning the module
    constant. Bound as a default it silently did not.

    Returns `None` when either file is absent. The `.omr.musicxml` is NOT a
    fallback: reading it is the defect this function exists to remove, and a
    silent fallback would reinstate it on exactly the machines where nobody
    would notice.
    """
    fixtures = FIXTURES if fixtures is None else fixtures
    truth_path = fixtures / f"{work}.musicxml"
    json_path = fixtures / f"{work}.omr.json"
    if not (truth_path.is_file() and json_path.is_file()):
        return None
    result = json.loads(json_path.read_text())
    ours = to_musicxml(result)
    on_disk = fixtures / f"{work}.omr.musicxml"
    stale = on_disk.is_file() and on_disk.read_text() != ours
    return Run(work=work, truth=truth_path.read_text(), ours=ours,
               result=result, stale_export=stale)


def expected_gaps(runs: list[Run]) -> dict[str, str]:
    """`KNOWN_GAPS`, minus the entries this configuration has spent.

    `words` is explained by "the direction reader placed nothing here" — which
    since 2026-09-02 means `--no-direction-text`, or a machine with no OCR rung,
    rather than the old default. Once the reader HAS placed something that
    explanation is spent, and a missing `<words>` is the recognised-then-dropped
    shape rather than a flag decision. Placement is the condition rather than
    merely running, because a reader that ran and accepted nothing has nothing
    to export.
    """
    if any(r.directions_placed for r in runs):
        return {k: v for k, v in KNOWN_GAPS.items() if k not in FLAG_DEPENDENT}
    return dict(KNOWN_GAPS)


def configuration_disagreement(runs: list[Run]) -> str | None:
    """Why these runs cannot be pooled, or `None` if they can.

    The survey adds the works' element counts together, so it is coherent only
    if they were produced the same way. `--works mahler-sym5-mvt1` leaves the
    other two from an earlier configuration, and pooling those makes `words`
    mean nothing in either direction.
    """
    on = sorted(r.work for r in runs if r.direction_reader_ran)
    off = sorted(r.work for r in runs if not r.direction_reader_ran)
    if on and off:
        return (f"the direction reader ran for {on} and not for {off} — these "
                "artifacts came from different configurations, and pooling them "
                "makes <words> meaningless in both directions. Re-run "
                "orchestral_eval over all of them the same way.")
    return None


@dataclass(frozen=True)
class Survey:
    """The pooled comparison over every benchmark work on disk."""
    runs: list[Run]
    gaps: list[tuple[str, int, int]]
    expected: dict[str, str]
    disagreement: str | None
    absent: tuple[str, ...] = ()

    @property
    def incomplete(self) -> str | None:
        """Why this survey cannot be read as a statement about the exporter.

        The counts are POOLED, so a missing work removes truth AND ours
        together and every conclusion moves in a direction that looks like good
        news: an element only Mahler's truth carries — `accent`, `wedge`,
        `tuplet` — reads as a gap somebody CLOSED when Mahler is simply not on
        disk. `--works mahler-sym5-mvt1` and an eval still mid-run both land
        here, and so does the very first run of the suite on a fresh clone.
        """
        if self.absent:
            return (f"{list(self.absent)} have no transcription on disk, and "
                    "the survey pools counts across works — an element only a "
                    "missing work's truth carries reads as a gap that was "
                    "closed. Run orchestral_eval over the whole set.")
        return None

    @property
    def unexplained(self) -> list[tuple[str, int, int]]:
        """Gaps not written down in the inventory this configuration expects."""
        return [g for g in self.gaps if g[0] not in self.expected]

    @property
    def stale_entries(self) -> list[str]:
        """Inventory entries for elements we now emit — history, not exporter."""
        return sorted(set(self.expected) - self.missing)

    @property
    def missing(self) -> set[str]:
        return {name for name, _, _ in self.gaps}

    @property
    def provenance(self) -> str:
        return "\n".join(f"  {r.work:22s} {r.configuration}" for r in self.runs)


def survey(fixtures: Path | None = None,
           works: tuple[str, ...] = WORKS) -> Survey:
    """Every work on disk, exported here, compared element by element."""
    loaded = {w: load_run(w, fixtures) for w in works}
    runs = [r for r in loaded.values() if r is not None]
    absent = tuple(w for w, r in loaded.items() if r is None)
    truth, ours = Counter(), Counter()
    for run in runs:
        truth += element_counts(run.truth)
        ours += element_counts(run.ours)
    gaps = [(name, truth[name], ours[name])
            for name in sorted(VISIBLE)
            if truth[name] > 0 and ours[name] == 0]
    return Survey(runs=runs, gaps=gaps, expected=expected_gaps(runs),
                  disagreement=configuration_disagreement(runs), absent=absent)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                    help="list the known gaps too, with their reasons")
    args = ap.parse_args(argv)

    s = survey()
    if not s.runs:
        print("no fixtures on disk — run `orchestral_eval` first")
        return 0
    if args.all:
        print("what wrote these artifacts (the transcription's own record):")
        print(s.provenance + "\n")
    if s.incomplete:
        print(f"INCOMPLETE: {s.incomplete}", file=sys.stderr)
        return 1
    if s.disagreement:
        print(f"MIXED CONFIGURATIONS: {s.disagreement}", file=sys.stderr)
        return 1
    if not s.gaps:
        print("every visible element the truth shows also appears in ours")
        return 0
    if args.all:
        print("VISIBLE elements the truth shows and we emit none of:\n")
        for name, t, o in s.gaps:
            note = s.expected.get(name, "*** NOT EXPLAINED ***")
            print(f"  {name:18s} truth {t:4d}   ours {o}\n      {note}\n")
    for name, t, o in s.unexplained:
        print(f"NEW EXPORT GAP: <{name}> — the truth has {t} and we emit none. "
              f"{VISIBLE[name]}.", file=sys.stderr)
    if s.unexplained:
        print("\nIf this is deliberate, add it to KNOWN_GAPS with the reason. "
              "If it is not, it is the shape that has cost this project seven "
              "fixes.", file=sys.stderr)
    return 1 if s.unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main())
