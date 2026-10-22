"""Per-part, per-bar scoring of an exported MusicXML file against a
reference encoding — ROADMAP 1.6, the SMALL re-gather (CLAUDE.md §6b,
2026-09-30: "a 1 page test ... instead of a full regather of a movement").

Pure and in-memory: given the `<part>` element of a reference score and the
`<part>` element of our export (or, for a condensed family, several parts on
one side unioned against one on the other — the caller's job, not this
module's), this parses each measure into NOTE events — onset and duration as
quarter-length `Fraction`s, so two files with different `<divisions>` still
compare correctly, and pitch as `<step><alter><octave>` — and scores ONE
(part-or-family, bar) cell at a time.

REST DURATION IS NOT SCORED HERE. "A whole rest means the BAR" (CLAUDE.md
§10) is a distinct, already-measured convention (`bars_add_up_control`,
`bars_held_out_sum` in `tools/omr/acceptance.py`); folding rests into this
scorer's missing/extra counts would double-charge a narrowed duration once
here and once there. This module answers only "which NOTES reached the file,
at the right place, right pitch, right length" — CLAUDE.md §10's own
distinction between "cannot tell" and "wrong" holds here too: a bar this
module was not given (the caller's alignment step held it out, e.g. a
condensed staff or a bar the exporter refused) is NOT COMPARABLE and must
never be silently scored as 0-for-0.

Matching within a bar, per onset (quantized to 1/64 of a quarter note, which
absorbs `<divisions>` rounding — Litolff/Brahms/engraved gathers all use a
Q.DURATION grid coarser than a 64th):
    1. exact (pitch, duration) pairs removed first          -> matched_exact
    2. same pitch, different duration, paired next           -> duration_wrong
    3. remaining same-onset notes paired arbitrarily          -> pitch_wrong
    4. whatever is left on the reference side                -> missing
    5. whatever is left on our side                           -> extra
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

ONSET_QUANTUM = Fraction(1, 64)  # quarter-lengths


@dataclass(frozen=True)
class Event:
    onset: Fraction
    duration: Fraction
    pitch: Optional[str]  # None = rest
    voice: str


def _pitch_key(note_el) -> Optional[str]:
    """`<step><alter as +N/-N/0><octave>`, e.g. 'C+1 4' -> 'C+14'. None for a
    rest or a note with no `<pitch>` (a grace/unpitched percussion note —
    neither acceptance document's condensed families have one on the count
    page; a caller finding one should treat it the same as a rest)."""
    if note_el.find("rest") is not None:
        return None
    p = note_el.find("pitch")
    if p is None:
        return None
    step = p.findtext("step") or ""
    alter_text = p.findtext("alter")
    try:
        alter = int(float(alter_text)) if alter_text is not None else 0
    except ValueError:
        alter = 0
    octave = p.findtext("octave") or ""
    return f"{step}{alter:+d}{octave}"


def parse_part_bars(part_el) -> Dict[str, List[Event]]:
    """`<part>` -> {measure-number-string: [Event, ...]}, EVERY voice, in
    document order. `<divisions>` carries forward across measures (only
    re-stated where it changes, same as MusicXML itself); a measure read
    before any `<divisions>` has been seen yields duration 0 for every
    event in it (never a crash — a caller comparing durations will see a
    0-length note and can decide what that means for its own bar)."""
    out: Dict[str, List[Event]] = {}
    divisions: Optional[Fraction] = None
    for measure in part_el.findall("measure"):
        num = measure.get("number") or ""
        attrs = measure.find("attributes")
        if attrs is not None:
            d = attrs.find("divisions")
            if d is not None and d.text:
                divisions = Fraction(d.text)
        events: List[Event] = []
        onset = Fraction(0)
        for el in measure:
            if el.tag == "note":
                dur_el = el.find("duration")
                if dur_el is not None and dur_el.text and divisions:
                    dur = Fraction(int(dur_el.text), 1) / divisions
                else:
                    dur = Fraction(0)
                is_chord = el.find("chord") is not None
                voice = el.findtext("voice") or "1"
                this_onset = onset if not is_chord else (
                    events[-1].onset if events else onset)
                pitch = _pitch_key(el)
                events.append(Event(this_onset, dur, pitch, voice))
                if not is_chord:
                    onset += dur
            elif el.tag == "backup":
                dur_el = el.find("duration")
                if dur_el is not None and dur_el.text and divisions:
                    onset -= Fraction(int(dur_el.text), 1) / divisions
            elif el.tag == "forward":
                dur_el = el.find("duration")
                if dur_el is not None and dur_el.text and divisions:
                    onset += Fraction(int(dur_el.text), 1) / divisions
        out[num] = events
    return out


def _quantize(value: Fraction) -> Fraction:
    return Fraction(round(value / ONSET_QUANTUM)) * ONSET_QUANTUM


@dataclass
class BarScore:
    ref_n: int
    our_n: int
    matched_exact: int = 0
    duration_wrong: int = 0
    pitch_wrong: int = 0
    missing: int = 0
    extra: int = 0
    details: List[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ref_n": self.ref_n, "our_n": self.our_n,
            "matched_exact": self.matched_exact,
            "duration_wrong": self.duration_wrong,
            "pitch_wrong": self.pitch_wrong,
            "missing": self.missing, "extra": self.extra,
        }


def score_bar(ref_events: Sequence[Event], our_events: Sequence[Event]
             ) -> BarScore:
    """Score ONE (part-or-family, bar) cell. NOTES only (pitch is not
    None) — rests are the caller's business, not this scorer's (module
    docstring)."""
    ref_notes = [(_quantize(e.onset), e.pitch, e.duration)
                for e in ref_events if e.pitch is not None]
    our_notes = [(_quantize(e.onset), e.pitch, e.duration)
                for e in our_events if e.pitch is not None]

    ref_by_onset: Dict[Fraction, List[Tuple]] = {}
    our_by_onset: Dict[Fraction, List[Tuple]] = {}
    for onset, pitch, dur in ref_notes:
        ref_by_onset.setdefault(onset, []).append((pitch, dur))
    for onset, pitch, dur in our_notes:
        our_by_onset.setdefault(onset, []).append((pitch, dur))

    matched_exact = duration_wrong = pitch_wrong = 0
    details: List[dict] = []
    for onset in sorted(set(ref_by_onset) | set(our_by_onset)):
        rlist = list(ref_by_onset.get(onset, []))
        olist = list(our_by_onset.get(onset, []))

        # pass 1: exact (pitch, duration)
        i = 0
        while i < len(rlist):
            if rlist[i] in olist:
                olist.remove(rlist[i])
                rlist.pop(i)
                matched_exact += 1
            else:
                i += 1

        # pass 2: same pitch, different duration
        i = 0
        while i < len(rlist):
            pitch = rlist[i][0]
            hit = next((j for j, o in enumerate(olist) if o[0] == pitch), None)
            if hit is not None:
                details.append({
                    "onset": str(onset), "kind": "duration_wrong",
                    "pitch": pitch, "ref_duration": str(rlist[i][1]),
                    "our_duration": str(olist[hit][1]),
                })
                olist.pop(hit)
                rlist.pop(i)
                duration_wrong += 1
            else:
                i += 1

        # pass 3: same onset, different pitch — paired arbitrarily (there is
        # no ground truth linking WHICH ref note a given wrong our-note was
        # meant to be; the count is still exact, only the pairing is a
        # choice)
        n_pair = min(len(rlist), len(olist))
        for k in range(n_pair):
            details.append({
                "onset": str(onset), "kind": "pitch_wrong",
                "ref_pitch": rlist[k][0], "our_pitch": olist[k][0],
            })
        pitch_wrong += n_pair
        rlist = rlist[n_pair:]
        olist = olist[n_pair:]

        for pitch, _dur in rlist:
            details.append({"onset": str(onset), "kind": "missing", "pitch": pitch})
        for pitch, _dur in olist:
            details.append({"onset": str(onset), "kind": "extra", "pitch": pitch})

    missing = sum(1 for d in details if d["kind"] == "missing")
    extra = sum(1 for d in details if d["kind"] == "extra")
    return BarScore(ref_n=len(ref_notes), our_n=len(our_notes),
                    matched_exact=matched_exact, duration_wrong=duration_wrong,
                    pitch_wrong=pitch_wrong, missing=missing, extra=extra,
                    details=details)


def align_and_score(ref_by_bar: Dict[str, List[Event]],
                    our_by_bar: Dict[str, List[Event]],
                    bar_numbers: Sequence[str], *,
                    held_out: Optional[set] = None,
                    ) -> Tuple[Dict[str, BarScore], List[str]]:
    """Score every bar in `bar_numbers` that is COMPARABLE, and name the
    rest. A bar is comparable when it is not in `held_out` (a bar the
    exporter itself refused — `bars_held_out_sum`'s own list, or a condensed
    staff the caller could not align) AND both sides have a measure numbered
    `bar` AND at least one side has a note in it. Neither absence is folded
    into a 0-valued score — a bar this function skips must never be read as
    "0 of 0 matched", which is what a fallback answering "cannot tell" with
    a clean number looks like (CLAUDE.md rule 8).

    Returns `(scores_by_bar, skipped_bar_numbers)`.
    """
    held_out = held_out or set()
    scores: Dict[str, BarScore] = {}
    skipped: List[str] = []
    for bar in bar_numbers:
        if bar in held_out:
            skipped.append(bar)
            continue
        ref_events = ref_by_bar.get(bar)
        our_events = our_by_bar.get(bar)
        if ref_events is None or our_events is None:
            skipped.append(bar)
            continue
        ref_notes = [e for e in ref_events if e.pitch is not None]
        our_notes = [e for e in our_events if e.pitch is not None]
        if not ref_notes and not our_notes:
            skipped.append(bar)
            continue
        scores[bar] = score_bar(ref_events, our_events)
    return scores, skipped


def sum_scores(scores: Sequence[BarScore]) -> BarScore:
    total = BarScore(ref_n=0, our_n=0)
    for s in scores:
        total.ref_n += s.ref_n
        total.our_n += s.our_n
        total.matched_exact += s.matched_exact
        total.duration_wrong += s.duration_wrong
        total.pitch_wrong += s.pitch_wrong
        total.missing += s.missing
        total.extra += s.extra
    return total
