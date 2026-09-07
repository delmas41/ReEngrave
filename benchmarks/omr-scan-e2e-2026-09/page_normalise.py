"""Make a reference encoding's PART STRUCTURE match the printed page.

    Sean, 2026-09-06: "The ground truth should be the scan as it is on the
    page. ... if the 2 flutes are on one staff on the page and on 2 separate
    staves in the MXL."  And: "I would think we should fix a VERSION of the
    MXL to match what we know."

A printed orchestral score CONDENSES. Beethoven 5 is engraved on twelve staves
and the Gradus encoding of it has eighteen parts, because `Flauti` is one staff
carrying Flute 1 and Flute 2. musicdiff pairs PARTS, so six reference parts have
no printed staff to pair with and are charged whole — 513 `entire staff
insert/delete` edits on that row, levied on ink that was read correctly.

This module builds a derived, VERSIONED truth whose parts are the page's staves.

FIVE RULES, AND THEY ARE THE WHOLE SAFETY ARGUMENT.

  1. IT NEVER TOUCHES `library/reference/`. Input is read-only; the output is a
     new file plus a sidecar naming the source, the transform version, and the
     exact merge map. The original stays the original.

  2. THE MERGE MAP COMES FROM A HUMAN, NOT FROM A HEURISTIC. It is
     `works.json`'s `staves[i].parts`, hand-read off the scan. Deriving the
     condensation from the ENCODING would be circular and is the trap measured
     in `benchmarks/omr-condensed-parts-2026-09/FINDINGS.md`: staves carrying
     the SAME printed label are encoded as 1 part in some editions and >1 in
     others, so whether a reference splits is a property of the encoding and
     the page cannot supply the count. A row with no hand map is NOT
     normalised — `normalise()` raises, the caller reports it un-normalised,
     and nothing is guessed.

  3. DIVISI IS A JUDGEMENT AND IS REPORTED SEPARATELY. Over every condensed
     staff-measure, CLAUDE.md measures silent 51.5% + unison 18.3% = 69.8%
     exact duplication; the rest is genuine divisi, where two encoded parts
     play different notes on one printed staff and the engraver chose between a
     chord and two stemmed voices. This transform CHORDS aligned divisi and
     stacks the rest as voices (see `MERGE_CONVENTION`), and every measure's
     class is counted so a normalised figure can never hide the choice.

  4. THE TRANSFORM IS VERSIONED. `TRANSFORM_VERSION` is stamped into every
     sidecar. A future change to rule 3 must be visible in the artefact rather
     than rediscovered by re-deriving it.

  5. ⚠️ A NORMALISED FIGURE IS A NEW BENCHMARK ERA. OMR-NED is symmetric, so
     merging parts moves the DENOMINATOR as well as the numerator. A normalised
     score MAY NOT be differenced against an un-normalised one in either
     direction, and any edits it removes are STRUCTURAL CHARGE REMOVED — the
     metric becoming valid — never the pipeline improving.

    from tools_free import page_normalise            # (it is a benchmark module)
    score, report = page_normalise.normalise(truth_xml, staves_map)
"""
from __future__ import annotations

import copy
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from music21 import chord, converter, note, stream

#: Bump on ANY change to how measures are merged. Stamped into every sidecar.
TRANSFORM_VERSION = "1.2.0"   # 1.1.0: refuse a map that does not name every part
#                             # 1.2.0: a rest, and an UNPITCHED note, are both
#                             #        first-class here — see `_tokens`,
#                             #        `_is_silent` and `_detached`

#: What rule 3 above resolves to, in one string, for the sidecar.
MERGE_CONVENTION = (
    "silent/unison -> one voice (exact duplication, the measured 69.8%); "
    "divisi with every event aligned on (offset,duration) -> one voice of "
    "chords; divisi otherwise -> stacked Voices, one per source part; "
    "any bar carrying an UNPITCHED (percussion) note takes the voice path, "
    "because a chord holds pitches and would drop it"
)


# --------------------------------------------------------------- classify

def _tokens(measure: stream.Measure) -> tuple:
    """A measure's sounding content, as a hashable order-independent key.

    Offsets and durations are `Fraction`s so a triplet compares exactly; a
    float would make 1/3 an inequality with itself across two parts.

    ⚠️ EVERY BODY IS A TUPLE OF STRINGS, AND THAT IS LOAD-BEARING, NOT TIDY.
    The key is sorted, so two events sharing `(offset, duration)` fall through
    to comparing their bodies — and a rest's body used to be the bare `str`
    "R" beside a note's `tuple`, which raises `TypeError: '<' not supported
    between instances of 'str' and 'tuple'` on Python 3. It takes a source bar
    holding both at once, i.e. a part whose measure already has two `Voice`s
    with one resting where the other sounds: Mahler 5's `Vier Trompeten in B.`
    writes exactly that (p3 mm 12 and 14, p4 mm 17-19), which is why no
    already-mapped row reached it. Wrapping the rest changes the sort order of
    nothing that previously sorted, because a `str` and a `tuple` never
    compared successfully; and it shifts every measure's key identically, so
    the equality tests in `classify` are unmoved.

    ⚠️ AND THE `else` BRANCH IS NOT A NOTE. `notesAndRests` also yields
    `Unpitched` — what every one-line percussion part parses to — which has no
    `.pitch` at all, so reaching for one raised `AttributeError` on any
    edition condensing two percussion parts onto one rule. An `Unpitched` is
    identified by the staff position it is DRAWN at, so that is its body.
    """
    out = []
    for el in measure.recurse().notesAndRests:
        off = Fraction(el.getOffsetInHierarchy(measure)).limit_denominator(10080)
        dur = Fraction(el.duration.quarterLength).limit_denominator(10080)
        body: Any
        if isinstance(el, note.Rest):
            body = ("R",)
        elif isinstance(el, chord.Chord):
            body = tuple(sorted(p.nameWithOctave for p in el.pitches))
        elif isinstance(el, note.Note):
            body = (el.pitch.nameWithOctave,)
        else:
            body = ("U", str(getattr(el, "displayStep", "")),
                    str(getattr(el, "displayOctave", "")))
        out.append((off, dur, body))
    return tuple(sorted(out))


def _is_silent(measure: stream.Measure) -> bool:
    """Does this bar sound at all?

    ⚠️ `NotRest`, not `(Note, Chord)`. A bar of `Unpitched` percussion notes is
    neither, and reading it as SILENT is the quiet half of the same fault: a
    condensed percussion staff would take the `silent_all` branch and its notes
    would be DISCARDED without a word — precisely the "better score for the
    wrong reason" this module exists to refuse. Measured over the 20-row scan
    gate: 17 rows carry no `Unpitched` at all, the three Mahler rows that do
    carry it only on one-line percussion parts that stand ALONE on their own
    printed staff, and no map — hand-read or candidate — puts an
    `Unpitched`-bearing part on a CONDENSED staff. So this is a no-op on
    everything currently measurable and a correctness floor for the first
    edition that is not.
    """
    return not any(isinstance(el, note.NotRest)
                   for el in measure.recurse().notesAndRests)


def _has_unpitched(measures: list[stream.Measure]) -> bool:
    """Does any of these bars carry a percussion note with no pitch?

    A `Chord` holds `Pitch`es, so the chord merge cannot represent an
    `Unpitched` and would drop it silently (its `.pitches` is empty, so the
    "add what the other part plays" loop adds nothing). Where one appears the
    transform takes the VOICE path instead, which copies whole events and is
    lossless. Nothing is refused and nothing is guessed.
    """
    return any(isinstance(el, note.Unpitched)
               for m in measures for el in m.recurse().notesAndRests)


def _detached(el):
    """A deepcopy safe to `insert` into a NEW parent stream.

    ⚠️ THE COPY KEEPS A POINTER TO THE ORIGINAL'S PARENT. Measured on Mahler 5
    p3's `Sechs Hörner in F.` m15: `copy.deepcopy` of a `Chord` comes back with
    `activeSite` still set to the SOURCE measure while its own `sites` dict
    holds only `None` — so when `Stream.insert` runs its is-this-still-sorted
    check it calls `sortTuple()`, which does
    `self.sites.siteDict[id(self.activeSite)]`, and raises a bare
    `KeyError: <id>`. (A `Note` copy comes back with `activeSite` None and does
    not, which is why the fault looked intermittent: p5 m31 is the same
    musical shape and does not fire.) Clearing the stale pointer is enough —
    `insert` sets the real one immediately afterwards.
    """
    c = copy.deepcopy(el)
    c.activeSite = None
    return c


def classify(measures: list[stream.Measure]) -> str:
    """`silent_all` | `unison` | `silent_others` | `divisi` for one bar."""
    if len(measures) == 1:
        return "single"
    if all(_is_silent(m) for m in measures):
        return "silent_all"
    toks = [_tokens(m) for m in measures]
    if all(t == toks[0] for t in toks):
        return "unison"
    sounding = [i for i, m in enumerate(measures) if not _is_silent(m)]
    if len(sounding) == 1:
        return "silent_others"
    # more than one sounding part, and they disagree
    sub = [toks[i] for i in sounding]
    if all(t == sub[0] for t in sub):
        # the sounding parts agree with each other; the rest are rests
        return "silent_others"
    return "divisi"


# ------------------------------------------------------------------ merge

def _aligned(measures: list[stream.Measure]) -> bool:
    """Do the sounding parts place every note at the same (offset, duration)?

    That is the case an engraver writes as a CHORD on one staff. Where it does
    not hold — one part in eighths against another in quarters — a chord would
    invent a duration, so the fallback is stacked voices.
    """
    keys = None
    for m in measures:
        if _is_silent(m):
            continue
        k = sorted({(Fraction(el.getOffsetInHierarchy(m)).limit_denominator(10080),
                     Fraction(el.duration.quarterLength).limit_denominator(10080))
                    for el in m.recurse().notesAndRests
                    if not isinstance(el, note.Rest)})
        if keys is None:
            keys = k
        elif k != keys:
            return False
    return keys is not None


def _chord_merge_into(base: stream.Measure,
                      measures: list[stream.Measure]) -> None:
    """Fold every other sounding part's pitches into `base`, IN PLACE.

    In place because `base` is the kept part's own bar and its slurs, hairpins
    and ties point at the note objects living in it; deepcopying the bar would
    leave every one of those spanners pointing at an object no longer in the
    score. Only a note that gains a pitch is replaced (a `Note` cannot hold
    two), and the replacement inherits the original's duration.
    """
    index: dict[tuple, Any] = {}
    for el in list(base.recurse().notesAndRests):
        if isinstance(el, note.Rest):
            continue
        key = (Fraction(el.getOffsetInHierarchy(base)).limit_denominator(10080),
               Fraction(el.duration.quarterLength).limit_denominator(10080))
        index[key] = el
    for other in measures:
        if other is base or _is_silent(other):
            continue
        for el in other.recurse().notesAndRests:
            if isinstance(el, note.Rest):
                continue
            key = (Fraction(el.getOffsetInHierarchy(other)).limit_denominator(10080),
                   Fraction(el.duration.quarterLength).limit_denominator(10080))
            target = index.get(key)
            if target is None:
                continue
            have = {p.nameWithOctave for p in target.pitches}
            add = [p for p in el.pitches if p.nameWithOctave not in have]
            if not add:
                continue
            new = chord.Chord(list(target.pitches) + add)
            new.duration = copy.deepcopy(target.duration)
            holder = target.activeSite
            off = target.offset
            holder.remove(target)
            holder.insert(off, new)
            index[key] = new


def _chord_merge(measures: list[stream.Measure]) -> stream.Measure:
    """One voice, simultaneous notes fused into chords. Requires `_aligned`."""
    sounding = [m for m in measures if not _is_silent(m)]
    base = copy.deepcopy(sounding[0])
    # index base's notes by (offset, duration)
    index: dict[tuple, Any] = {}
    for el in list(base.recurse().notesAndRests):
        if isinstance(el, note.Rest):
            continue
        key = (Fraction(el.getOffsetInHierarchy(base)).limit_denominator(10080),
               Fraction(el.duration.quarterLength).limit_denominator(10080))
        index[key] = el
    for other in sounding[1:]:
        for el in other.recurse().notesAndRests:
            if isinstance(el, note.Rest):
                continue
            key = (Fraction(el.getOffsetInHierarchy(other)).limit_denominator(10080),
                   Fraction(el.duration.quarterLength).limit_denominator(10080))
            target = index.get(key)
            if target is None:
                continue
            have = set(p.nameWithOctave for p in target.pitches)
            add = [p for p in el.pitches if p.nameWithOctave not in have]
            if not add:
                continue
            new = chord.Chord(list(target.pitches) + add)
            new.duration = copy.deepcopy(target.duration)
            holder = target.activeSite
            off = target.offset
            holder.remove(target)
            holder.insert(off, new)
            index[key] = new
    return base


def _voice_merge(measures: list[stream.Measure]) -> stream.Measure:
    """Stacked Voices, one per SOUNDING source part.

    Every copy goes in through `_detached` — see there for the `KeyError` a
    copy still pointing at its old parent raises on the way in. The OFFSET is
    right as it stands: `getOffsetInHierarchy(m)` is measured against the
    source MEASURE, the new `Voice` is inserted at 0.0 in the new measure, so
    a nested-voice event keeps the position it had on the page.
    """
    sounding = [m for m in measures if not _is_silent(m)]
    base = copy.deepcopy(sounding[0])
    out = stream.Measure(number=base.number)
    for el in base:
        if isinstance(el, (note.NotRest, note.Rest, stream.Voice)):
            continue
        out.insert(el.offset, _detached(el))       # clef, key, meter, barline…
    for i, m in enumerate(sounding):
        v = stream.Voice(id=str(i + 1))
        for el in m.recurse().notesAndRests:
            v.insert(el.getOffsetInHierarchy(m), _detached(el))
        out.insert(0.0, v)
    return out


# ------------------------------------------------------------- the driver

class NoHandMap(RuntimeError):
    """Raised when a row has no hand-read staves map. NEVER guessed around."""


class IncompleteMap(NoHandMap):
    """The map exists but does not account for every reference part.

    A subclass of `NoHandMap` so a caller that already abstains on "no map"
    abstains on "half a map" too, without knowing this class exists.
    """


def normalise(truth_xml: Path, staves_map: list[dict] | None,
              *, source_reference: str | None = None) -> tuple[stream.Score, dict]:
    """Return (page-normalised score, provenance/report dict).

    `staves_map` is `works.json`'s `staves` list verbatim: one entry per
    PRINTED staff, each with `parts` naming reference part indices.

    ⚠️ IT MUTATES A DEEPCOPY OF THE SOURCE, IT DOES NOT REBUILD ONE. The first
    version of this function built a fresh `Score` out of merged measures, and
    the Dvořák control — 15 parts to 15 staves, where the transform is asked to
    change NOTHING — moved by 12 edits. The cause was SPANNERS: a slur, a
    hairpin or a tremolo lives outside the measures it decorates, so copying
    measures one at a time silently drops it (Dvořák p5's 14 `<wedge>` became
    0, and `wrong crescendo`/`wrong diminuendo`/`wrong fingered tremolo` all
    fell to zero — a "better" score bought by deleting the evidence). Merging
    in place leaves an unmerged staff literally untouched, which is what makes
    the control a control.
    """
    if not staves_map:
        raise NoHandMap("no hand-read staves map — refusing to guess a "
                        "condensation from the encoding")
    src = converter.parse(str(truth_xml))
    out = copy.deepcopy(src)
    parts = list(out.parts)

    census: dict[str, int] = {}
    per_staff = []
    keepers: list[stream.Part] = []
    named: set[int] = set()

    for spec in staves_map:
        idx = [i for i in spec["parts"] if i < len(parts)]
        if not idx:
            raise NoHandMap(f"staff {spec.get('name')!r} names parts "
                            f"{spec['parts']} but the file has {len(parts)}")
        named.update(idx)
        keep = parts[idx[0]]
        others = [parts[i] for i in idx[1:]]
        staff_census: dict[str, int] = {}

        if others:
            numbers = [m.number
                       for m in keep.getElementsByClass(stream.Measure)]
            for num in numbers:
                bars = [keep.measure(num)]
                bars += [p.measure(num) for p in others]
                bars = [b for b in bars if b is not None]
                if not bars:
                    continue
                kind = classify(bars)
                staff_census[kind] = staff_census.get(kind, 0) + 1
                census[kind] = census.get(kind, 0) + 1
                if kind in ("silent_all", "unison"):
                    continue                      # keep's own bar already IS it
                target = keep.measure(num)
                if kind == "silent_others":
                    if not _is_silent(target):
                        continue                  # keep IS the sounding part
                    source = next(b for b in bars if not _is_silent(b))
                    merged = copy.deepcopy(source)
                elif _aligned(bars) and not _has_unpitched(bars):
                    staff_census["divisi_chorded"] = \
                        staff_census.get("divisi_chorded", 0) + 1
                    census["divisi_chorded"] = census.get("divisi_chorded", 0) + 1
                    # IN PLACE on keep's own bar wherever keep sounds, so
                    # keep's slurs and hairpins keep pointing at real notes.
                    if _is_silent(target):
                        merged = _chord_merge(bars)
                    else:
                        _chord_merge_into(target, bars)
                        continue
                else:
                    staff_census["divisi_voiced"] = \
                        staff_census.get("divisi_voiced", 0) + 1
                    census["divisi_voiced"] = census.get("divisi_voiced", 0) + 1
                    merged = _voice_merge(bars)
                off = target.offset
                keep.remove(target)
                merged.number = num
                keep.insert(off, merged)
        else:
            n = len(keep.getElementsByClass(stream.Measure))
            staff_census["single"] = n
            census["single"] = census.get("single", 0) + n

        keepers.append(keep)
        per_staff.append({"staff": spec.get("name"), "parts": idx,
                          "condensed": len(idx) > 1, "measures": staff_census})

    # ⚠️ A PART THE MAP NEVER NAMES MAY NOT BE DROPPED SILENTLY. Deleting a
    # reference part is deleting evidence, and it makes the score go DOWN — the
    # same shape as the spanner loss the Dvořák control caught. Found by the
    # engraved no-op probe, where an identity map built from `<score-part>`
    # elements had 18 entries against music21's 19 `.parts` (a part declaring
    # `<staves>2</staves>` becomes two `PartStaff`s on parse), so one part was
    # dropped and Dvořák 9 "improved" by 42 edits.
    unmentioned = [i for i in range(len(parts)) if i not in named]
    if unmentioned:
        raise IncompleteMap(
            f"the hand map names {len(named)} of {len(parts)} parts; "
            f"parts {unmentioned} are unaccounted for. Refusing to drop them "
            f"— a normalised truth missing a part scores BETTER for the wrong "
            f"reason.")
    for p in parts:
        if p not in keepers:
            out.remove(p)

    # `divisi_chorded` / `divisi_voiced` PARTITION `divisi`, so they are not
    # summed into the denominator — counting them would double-count the very
    # population the reader is being asked to watch.
    PRIMARY = ("single", "silent_all", "unison", "silent_others", "divisi")
    total = sum(census.get(k, 0) for k in PRIMARY) or 1
    exact = census.get("silent_all", 0) + census.get("unison", 0) \
        + census.get("silent_others", 0) + census.get("single", 0)
    report = {
        "transform": "page_normalise",
        "transform_version": TRANSFORM_VERSION,
        "merge_convention": MERGE_CONVENTION,
        "source_reference": source_reference,
        "source_trimmed_truth": str(truth_xml),
        "n_source_parts": len(parts),
        "n_output_parts": len(out.parts),
        "merge_map": [{"staff": s["staff"], "parts": s["parts"]}
                      for s in per_staff],
        "measure_census": census,
        "measure_census_share": {k: round(v / total, 4) for k, v in census.items()},
        "exact_duplication_share": round(exact / total, 4),
        "divisi_share": round(census.get("divisi", 0) / total, 4),
        "per_staff": per_staff,
        "warning": ("A figure measured against this file is a NEW BENCHMARK "
                    "ERA and may not be differenced against one measured "
                    "against the un-normalised truth. Edits it removes are "
                    "STRUCTURAL CHARGE REMOVED, not pipeline improvement."),
    }
    return out, report


def write(truth_xml: Path, staves_map: list[dict] | None, out_xml: Path,
          *, source_reference: str | None = None) -> dict:
    score, report = normalise(truth_xml, staves_map,
                              source_reference=source_reference)
    out_xml.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out_xml))
    report["output"] = str(out_xml)
    sidecar = out_xml.with_suffix(".provenance.json")
    sidecar.write_text(json.dumps(report, indent=1) + "\n")
    report["sidecar"] = str(sidecar)
    return report
