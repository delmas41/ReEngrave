"""Does everything the truth would SHOW survive into our output?

WHY THIS EXISTS. Nine times now the defect has been the same shape: the
pipeline recognises something correctly and then loses it on the way to the
file. Beams, augmentation dots, dynamics, tuplet markers, slur arcs, fermatas,
accidentals, articulations, hairpins. Most of the benchmark's fall from its 0.3164
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
    9  hairpins             (in §9)   two classes, no mention downstream
   10  ornaments            (in §10)  four ornament classes + five tremolo,
                                 and THE CHECK ITSELF COULD NOT SEE IT

⚠️ THE NINTH IS NOT THE EIGHT REPEATED, and the difference is worth keeping.
The first eight were export fixes outright: the detector had the symbol and the
file did not. Hairpins are DETECTED PARTIALLY — 9 boxes against 8 truth
hairpins over the 11 works. Wiring the exporter alone took `<wedge>` from zero
to 10 elements and from 3 truth hairpins matched to 4 — and it could not have
taken it further that day, because 3 of Mahler's 4 detections were landing on
the staff BELOW the one that prints them: a hairpin is drawn in the gap under
its staff, so a contested copy sits roughly midway between the two staves
bracketing that gap, and `transcribe._dedupe_cross_staff_detections` awarded it
to the nearer five-line band — staff 18, which carries ZERO detected noteheads
anywhere on the page, orphaning the hairpin at the exporter (which anchors a
wedge to noteheads on its OWN staff). A same-day fix adds a veto keyed on
notehead presence in the contested bar, ahead of distance, for exactly the two
wedge classes (`benchmarks/omr-hairpins-2026-09/FINDINGS.md` §6): all four of
Mahler's hairpins now land on the Trumpet staff that prints them, taking the
11-work total from 5 of 8 truth hairpins exported to 7, 3 of 3 for Mahler
specifically. **Closing a categorical gap is not the same as reading the
symbol**, and this entry leaving the inventory says only the first — the one
truth hairpin still unexported is Brahms 4's, where the anchor lands on the
wrong notehead order rather than the wrong staff (FINDINGS.md §2), and one
Mahler pair is now correctly paired but not exact (a duration edit, not a
miss) — neither is what this fix addresses.

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
some. All nine read `truth N, ours 0`.

⚠️ AND THE TENTH WAS THE CHECK'S OWN BLIND SPOT (2026-09-08). `<ornaments>` —
truth 12 on the engraved benchmark, 131 on the scan gate, ours ZERO, with
`ornamentTrill` firing 21 times across the committed artifacts — was invisible
here for the same reason the class-space audit above is useless: the question
was asked of a HAND-WRITTEN LIST. `compare()` iterated a 19-name `VISIBLE`
dict, so an element in neither `VISIBLE` nor `KNOWN_GAPS` failed nothing, and
nobody had to write anything down for that to be true. **A check built to
remove a blind spot had one, in the same shape.**

WHAT IT DOES NOT LOOK AT, AND WHY THAT IS NOW DERIVED. The old paragraph here
said: a MusicXML file is mostly not notation — metadata, page layout, MIDI
playback hints, part bookkeeping — and a check that reported all of it would
list 55 elements, be ignored, and then be deleted. **That objection is real and
it survives the rewrite**; deriving the set from the truth files brings all 55
back. It is answered by three structural rules and one short deny-list, in this
order, measured over the committed copy of the whole 11-work benchmark in
`benchmarks/omr-margin-window-truncation-2026-09/out/fixtures-control/` (truth
and that run's export, both in git — so the funnel is reproducible on a clean
clone with no eval run; `benchmarks/omr-export-gaps-2026-09/
probe-ornaments-2026-09-08/probe_derived_coverage.py` prints it):

    every element inside <measure>, pooled                       88
    ... minus the ones we DO emit (the categorical rule)          40   <- "55"
    ... minus every element whose PARENT is also missing (rollup) 19
    ... minus NOT_NOTATION (print, sound, staff-details)          16

⚠️ THE ROLLUP DOES 21 OF THE 24, and the deny-list 3. The short list is a
CONSEQUENCE of a structural rule, not a promise anyone has to keep.

**The rollup is the load-bearing half, and it is the ornaments arithmetic
itself.** `<tremolo>` lives inside `<ornaments>`; if we emit no `<ornaments>`
then `<tremolo>` is not a second gap, it is the same gap seen from the inside.
The handoff table that opened this work listed `ornaments` 12 and `tremolo` 12
as two rows — and the truth file holds twelve `<ornaments>` blocks containing
twelve `<tremolo>` and nothing else. Rollup makes that one row by construction.

⚠️ **`NOT_NOTATION` IS NOT `VISIBLE` WEARING A DIFFERENT HAT**, and the
difference is the point rather than a defence of it. `VISIBLE` was an
ALLOW-list, so the default for an unmet element was *silently unchecked*.
`NOT_NOTATION` is a DENY-list, so the default is *fails until someone writes
down why*. The failure direction is inverted; that is the property that makes
the tenth gap impossible to repeat, and it is why the list being short is a
consequence of the rules above rather than a promise.

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
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
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

#: The scope of the question, and the ONE structural fact this check rests on.
#:
#: A MusicXML file is mostly not notation — metadata, page layout, MIDI
#: playback hints, part bookkeeping — and MusicXML puts all of it OUTSIDE
#: `<measure>`. `<score-partwise>` opens with `<work>`, `<identification>`,
#: `<defaults>` and `<part-list>`, and then every note, rest, clef, direction
#: and barline in the document lives inside a `<measure>`. So "the music" is
#: not a curated opinion here; it is a subtree, named once.
#:
#: ⚠️ WHAT THIS EXCLUDES, stated rather than implied: `<part-name>` and
#: `<work-title>` ARE ink a reader sees and are outside a measure, so this
#: check does not watch them. `label_contradiction.py` watches part naming
#: from the other side (the printed margin against the exported name), which is
#: a stronger question than presence; nothing watches `<work-title>`.
MUSIC_SUBTREE = "measure"

#: In-measure elements that are BOOKKEEPING — no reader ever sees them, so
#: "the truth has them and we emit none" says nothing about the exporter.
#:
#: ⚠️ THIS IS NOT `VISIBLE` WEARING A DIFFERENT HAT, and the difference is the
#: whole point of the rewrite. `VISIBLE` was an ALLOW-list: an element in
#: neither it nor `KNOWN_GAPS` was checked by NOTHING, silently, and nobody had
#: to write anything down — which is how `<ornaments>` (truth 12 engraved, 131
#: scan, ours 0) sat unreported by the very module built to report it. This is
#: a DENY-list: the default is now "fails until someone writes down why", and
#: an element missing from this table is loud rather than invisible. The
#: failure direction is inverted, which is the property that matters.
#:
#: It is also short — three entries against nineteen — because the ROLLUP below
#: removes the bulk of what a derived set would otherwise report. Each entry
#: must be OBSERVED in the truth (`Survey.stale_bookkeeping`, asserted by
#: `test_a_bookkeeping_entry_the_truth_never_shows_is_flagged`), so it
#: cannot grow into a list describing history.
NOT_NOTATION: dict[str, str] = {
    "print": (
        "A layout instruction — page and system breaks, staff distances, "
        "margins. It positions ink; it is not ink. We lay nothing out and "
        "never will: the renderer does."
    ),
    "sound": (
        "MIDI playback — tempo, dynamics as velocities, segno/dacapo jumps for "
        "a player rather than for a reader. `<direction>`'s audible twin, and "
        "the reader sees the `<direction-type>` beside it, which IS checked."
    ),
    "staff-details": (
        "How many lines a staff has and how far apart they are printed — a "
        "property of the rendering surface. `<staff-lines>` on a one-line "
        "percussion staff is real information we do not carry, but its "
        "NOTATION consequence is `<unpitched>`, which this check reports."
    ),
}


_ELEMENT = re.compile(r"<([a-z][a-z0-9-]*)[ />]")


def element_counts(xml: str) -> Counter:
    """Every element name in a document, however malformed.

    Deliberately a regex and not a parser: our side is compared by COUNT only,
    and the tests build a broken export on purpose (`<dropped>x</accidental>`)
    to prove a dropped element is seen. A parser would raise on exactly the
    input this check exists to describe.
    """
    return Counter(_ELEMENT.findall(xml))


@dataclass(frozen=True)
class TruthElement:
    """One element name as the TRUTH document uses it."""
    name: str
    count: int
    #: Every ancestor name observed above it, within the music subtree.
    ancestors: frozenset[str]
    #: One observed path from the subtree root down to it, for a message.
    path: tuple[str, ...]

    @property
    def where(self) -> str:
        return " > ".join(self.path)


def notation_index(truth_xml: str) -> dict[str, TruthElement]:
    """Every element the truth prints INSIDE the music, with its parentage.

    Derived from the document, not from a list. `ancestors` is what makes the
    rollup possible: an element whose parent we also emit none of is the same
    gap seen from the inside, and reporting both is what would turn this into
    the 55-line report nobody reads.

    Namespaces are stripped, and a document with no `<measure>` yields nothing —
    which `Survey.incomplete` and the caller's own emptiness checks catch.

    ⚠️ Only the TRUTH side is parsed. Our side stays a regex count
    (`element_counts`), because the tests build a broken export on purpose and
    a parser would raise on exactly the input this check exists to describe. A
    truth that does not parse raises here rather than producing a quiet partial
    answer — a corrupt truth invalidates the comparison and musicdiff would
    refuse it too.
    """
    root = ET.fromstring(truth_xml)
    found: dict[str, TruthElement] = {}

    def tag(e) -> str:
        t = e.tag
        return t.rsplit("}", 1)[-1] if isinstance(t, str) and "}" in t else str(t)

    def walk(node, path: tuple[str, ...]) -> None:
        for child in node:
            name = tag(child)
            here = path + (name,)
            prev = found.get(name)
            if prev is None:
                found[name] = TruthElement(name, 1, frozenset(path), here)
            else:
                found[name] = TruthElement(
                    name, prev.count + 1, prev.ancestors | frozenset(path),
                    prev.path)
            walk(child, here)

    for measure in root.iter():
        if tag(measure) == MUSIC_SUBTREE:
            walk(measure, (MUSIC_SUBTREE,))
    return found


def compare(truth_xml: str, ours_xml: str) -> list[tuple[str, int, int]]:
    """`(element, in_truth, in_ours)` for every gap-HEAD the truth shows.

    Three rules, in order, and each is structural rather than curated:

    1. **Scope.** Only elements inside `MUSIC_SUBTREE`. Everything above it is
       the file's header and we do not claim to reproduce it.
    2. **Categorical only.** Truth has some, we have zero. Emitting fewer is a
       recognition shortfall and belongs to the accuracy metric; conflating the
       two is what would make this noisy enough to ignore.
    3. **Rollup.** An element is reported only if no ANCESTOR of it is also
       missing. `<tremolo>` lives inside `<ornaments>`; if we emit no
       `<ornaments>` then `<tremolo>` is not a second gap, it is the same one
       counted twice — which is exactly the arithmetic that made the handoff
       table read as two findings when the two truth files carrying ornaments
       contain 12 `<ornaments>` holding 12 `<tremolo>` and nothing else.

    `NOT_NOTATION` then removes what survives all three and is still invisible
    to a reader. It is applied by the caller (`Survey.unexplained`) rather than
    here, so `compare` reports the honest structural answer and the report says
    which entries spent it.
    """
    index = notation_index(truth_xml)
    ours = element_counts(ours_xml)
    missing = {n for n, e in index.items() if e.count > 0 and ours[n] == 0}
    return sorted((n, index[n].count, 0) for n in missing
                  if not (index[n].ancestors & missing))


def gap_locations(truth_xml: str) -> dict[str, str]:
    """`element -> "measure > note > notations > ornaments"`, for a message.

    Replaces the hand-written `VISIBLE[name]` description the failure line used
    to carry. Deriving the set means there is no blurb for an element nobody
    has met yet — and where the element SITS is more use than a blurb anyway:
    it names the block a reader would have to open to fix it.
    """
    return {n: e.where for n, e in notation_index(truth_xml).items()}


#: Elements the truth shows that we knowingly do not emit, each with the reason
#: and its size. This is an INVENTORY, not a suppression list: it is the honest
#: statement of what the exporter still drops, and everything in it is either a
#: decision already taken or an open item someone can pick up. Anything NOT here
#: is a new gap and fails the test.
KNOWN_GAPS: dict[str, str] = {
    "barline": (
        "Documented limitation — repeat signs are dropped on export, tied to "
        "multi-type barline classification. NOTES.md items 5 and 6. ⚠️ Covers "
        "`<bar-style>` and `<repeat>` too, which had an entry of their own "
        "until the rollup landed: both are CHILDREN of <barline>, so they are "
        "the same gap seen from the inside and are no longer reportable "
        "separately. A repeat cannot be written without its bar-style anyway, "
        "which is what that entry said."
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
    # ---- ⚠️ THE FOURTEEN BELOW ARRIVED WITH THE DERIVED SET (2026-09-08) ----
    # Every one of them was ALREADY a gap and was reported by nothing, because
    # it was absent from the hand-written `VISIBLE` allow-list. They are the
    # backlog the old check could not see, written down once. Predicted here
    # against the committed 11-work fixture copy in
    # `benchmarks/omr-margin-window-truncation-2026-09/out/fixtures-control/`
    # (truth + that run's export); the sizes are that pool's.
    "ornaments": (
        "⚠️ THE EXPORT IS BUILT AND THE REMAINING GAP IS DETECTION. "
        "`transcribe._attach_ornaments_in_cell` places trill/turn/mordent/"
        "tremolo and both exporters emit them (2026-09-08). The 12 "
        "<ornaments> in the engraved truth are 12 <tremolo> and NOTHING ELSE "
        "— all of Beethoven 3's, all `type=\"single\">1` — and across all "
        "7,090 committed JSON artifacts there is not ONE `tremolo1`-"
        "`tremolo5` detection at any confidence. The 33 ornament detections "
        "that DO exist (21 `ornamentTrill`, 6 `ornamentTurn`, 3 "
        "`ornamentTurnInverted`, 3 `ornamentMordent`) are all on scans, none "
        "on a benchmark work. Same shape as hairpins on scans: emitting is "
        "not reading. ⚠️ THIS ENTRY MUST LEAVE THE DAY THE DETECTOR FIRES "
        "ONE HERE — `test_the_inventory_has_no_stale_entries` enforces that."
    ),
    "transpose": (
        "The written-to-sounding interval of a transposing part. `instruments."
        "py` carries the offsets and the contextual pass names the "
        "instruments, so the fact is in the pipeline and the exporter never "
        "writes <transpose>. 92 in the engraved truth. A real open item, and "
        "the largest single one on this list after <stem>."
    ),
    "detached-legato": (
        "An articulation outside the five DSv2 labels (staccato, "
        "staccatissimo, accent, marcato, tenuto). No class exists for it, so "
        "it is unreadable rather than dropped — 14 in the engraved truth."
    ),
    "spiccato": (
        "The same: an articulation with no DSv2 class. 4 in the engraved "
        "truth. Listed apart from `detached-legato` because they are separate "
        "elements and each must leave on its own evidence."
    ),
    "grace": (
        "A grace note. ⚠️ MEASURED AND RECORDED AS A CEILING, not a "
        "conjecture: the transcription holds ZERO `*Small` detections on any "
        "page — a grace head is read as an ordinary notehead — and the "
        "pre-fill work priced two candidate fixes and refuted both "
        "(docs/handoff-2026-09-03-prefill-measured.md). The untried route is "
        "geometry: a grace head measures 41x38 against 51-83 in the same cell."
    ),
    "unpitched": (
        "A percussion note on a staff with no pitch. Handoff step 4 names the "
        "cause: one-line percussion staves the detector never finds, 3 of the "
        "20 scan rows. Its <attributes> twin `<staff-details>` is in "
        "NOT_NOTATION — the LINE COUNT is a rendering property, the note on it "
        "is not."
    ),
    "normal-type": (
        "The third child of <time-modification>. We write <actual-notes> and "
        "<normal-notes> — the RATIO, which is what the note is worth — and not "
        "the written value the ratio is against, which a reader derives from "
        "the notes under the bracket. 141 in the engraved truth, and worth "
        "nothing to musicdiff; kept written down rather than closed silently."
    ),
    "tuplet-actual": (
        "An optional display child of <tuplet> saying how the bracket's "
        "NUMBER should be drawn. We write the bracket and its `number=` "
        "attribute; how a renderer letters it is the renderer's. 47 in the "
        "engraved truth."
    ),
    "tuplet-normal": (
        "The other half of the same pair, and the same reason. Two entries "
        "rather than one because they are two elements and each must leave on "
        "its own evidence."
    ),
    "display-step": (
        "Where on the staff a REST is printed. The pipeline knows a rest's y "
        "— that is how it is assigned to a staff at all — and the exporter "
        "places every rest at the renderer's default height instead. 5 in the "
        "engraved truth. Placement rather than presence, so it is here and not "
        "in NOT_NOTATION: it changes where visible ink lands."
    ),
    "display-octave": (
        "The other half of the same coordinate, and the same reason."
    ),
    "offset": (
        "How far along the bar a <direction> is drawn from the note it is "
        "attached to, in divisions. Our directions are emitted at the head of "
        "the bar or beside the note they anchor to, with no sub-beat offset — "
        "3 in the engraved truth. Placement rather than presence, like "
        "`display-step`."
    ),
    "staff": (
        "Which staff of a MULTI-STAFF part a note belongs to. `_stitch_slots` "
        "joins staves into parts one staff at a time, so every part we write "
        "has exactly one staff and <staff> has nothing to say. It becomes a "
        "real gap the day a part carries two staves — which is handoff step 4 "
        "and `OMR_CONDENSED_PARTS`, not this list."
    ),
    "staves": (
        "The <attributes> declaration of the same fact, and the same reason: "
        "one staff per part means the default of 1 is correct."
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
    #: `element -> "measure > note > notations > ornaments"`, derived from the
    #: truth. Replaces the hand-written blurb the failure line used to carry.
    where: dict[str, str] = field(default_factory=dict)
    #: Pooled element counts on OUR side. Only `stale_entries` reads it, and
    #: only it can: "we emit this now" is a fact about our output, and neither
    #: the gap list nor the truth index can state it — see that property.
    ours_counts: Counter = field(default_factory=Counter)

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
        """Gaps explained by NEITHER table — the ones that fail.

        Two tables, and they are different claims about the same element:
        `NOT_NOTATION` says *no reader ever sees this*, `expected` (KNOWN_GAPS
        minus what the configuration has spent) says *a reader sees it and we
        deliberately do not emit it, here is why*. Keeping them apart is what
        stops the second becoming a dumping ground for the first.
        """
        return [g for g in self.gaps
                if g[0] not in self.expected and g[0] not in NOT_NOTATION]

    @property
    def bookkeeping(self) -> list[tuple[str, int, int]]:
        """The gaps `NOT_NOTATION` accounts for — reported by `--all`, never a
        failure. Named so the deny-list is visible in the report rather than
        merely subtracted out of it."""
        return [g for g in self.gaps if g[0] in NOT_NOTATION]

    @property
    def stale_bookkeeping(self) -> list[str]:
        """`NOT_NOTATION` entries this truth never shows.

        The same discipline `stale_entries` applies to `KNOWN_GAPS`: an
        exclusion for an element nobody prints is dead text, and a deny-list
        allowed to accumulate dead text is how `VISIBLE` got to nineteen names
        nobody re-read. ⚠️ Only meaningful on a COMPLETE survey — see
        `incomplete`.
        """
        return sorted(n for n in NOT_NOTATION if n not in self.where)

    @property
    def stale_entries(self) -> list[str]:
        """Inventory entries for elements WE NOW EMIT — history, not exporter.

        ⚠️ REDEFINED WITH THE DERIVED SET (2026-09-08), and the old definition
        was only ever right by luck. It was `expected - missing`, which calls
        an entry stale in three different situations and means it in one:

          * we emit it now — genuinely stale, the case this test is for;
          * the truth does not print it at all — says nothing either way, and
            with a curated `VISIBLE` this could not arise because every entry
            named something all three canonical truths printed. It arises now:
            `<grace>` and `<unpitched>` are gaps on the SCAN truths and absent
            from the engraved ones;
          * it is rolled up under a missing parent — reported through its
            parent, not closed.

        So the question is asked of our own output directly. An entry is spent
        when the exporter writes the element, and by nothing else.
        """
        return sorted(n for n in self.expected if self.ours_counts[n] > 0)

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
    # POOLED, and pooled correctly: the truth's structure is unioned across
    # works before the rollup runs, so an element one work nests under a parent
    # another work never prints is still rolled up. Concatenating the truths
    # into one document is what makes that a fact about the pool rather than a
    # per-work answer summed afterwards.
    pooled_truth = ("<pool>" + "".join(_strip_prolog(r.truth) for r in runs)
                    + "</pool>")
    pooled_ours = "".join(r.ours for r in runs)
    gaps = compare(pooled_truth, pooled_ours) if runs else []
    where = gap_locations(pooled_truth) if runs else {}
    return Survey(runs=runs, gaps=gaps, expected=expected_gaps(runs),
                  disagreement=configuration_disagreement(runs), absent=absent,
                  where=where, ours_counts=element_counts(pooled_ours))


_PROLOG = re.compile(r"^\s*(<\?xml[^>]*\?>|<!DOCTYPE[^>]*>)\s*", re.I)


def _strip_prolog(xml: str) -> str:
    """Drop the XML declaration and DOCTYPE so several files can be wrapped.

    Both are legal only at the head of a document, so a naive concatenation is
    not parseable. Nothing else is touched — this is a splice, not a rewrite.
    """
    prev = None
    while prev != xml:
        prev = xml
        xml = _PROLOG.sub("", xml, count=1)
    return xml


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
        print(f"{len(s.where)} elements inside <measure> in the truth; "
              f"{len(s.gaps)} of them are gap HEADS (an element whose own "
              "parent is also missing is the same gap, and is rolled up).\n")
        for name, t, o in s.gaps:
            note = (NOT_NOTATION.get(name) or s.expected.get(name)
                    or "*** NOT EXPLAINED ***")
            tier = "bookkeeping" if name in NOT_NOTATION else "known gap"
            if name not in NOT_NOTATION and name not in s.expected:
                tier = "UNEXPLAINED"
            print(f"  {name:18s} truth {t:4d}   ours {o}   [{tier}]"
                  f"\n      at  {s.where.get(name, '?')}"
                  f"\n      {note}\n")
    for name, t, o in s.unexplained:
        # No hand-written blurb any more — the set is derived, so there is none
        # for an element nobody has met. Where it SITS is derived too, and says
        # more: it names the block someone would have to open.
        print(f"NEW EXPORT GAP: <{name}> — the truth has {t} and we emit none. "
              f"It sits at {s.where.get(name, '?')}.", file=sys.stderr)
    if s.unexplained:
        print("\nIf a reader sees it and we deliberately drop it, add it to "
              "KNOWN_GAPS with the reason. If no reader ever sees it, add it "
              "to NOT_NOTATION instead — the two are different claims. If it "
              "is neither, it is the shape that has cost this project ten "
              "fixes.", file=sys.stderr)
    return 1 if s.unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main())
