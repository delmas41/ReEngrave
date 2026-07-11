"""Voicing & chord grouping for transcribe.py output.

Phase 4e. Takes a measure's list of detection dicts (the JSON shape that
transcribe.py emits) and produces an ordered list of **musical events** —
each event is one chord (1+ noteheads sharing the same start time) or one
rest, with a definite x-position and duration.

This is what real notation IS: a sequence of events with start times, not
just a flat list of notehead detections. Downstream exporters (MusicXML,
LilyPond) need this structure to render correctly — without chord
grouping, three noteheads stacked at the same beat would render as three
overlapping single notes instead of one chord.

V1 keeps things deliberately simple:

  - **Chord grouping by x-position, gated by stem direction.** Noteheads
    whose x-centers fall within a small tolerance are considered
    "simultaneous" and grouped into one chord — UNLESS they have
    explicit, conflicting stem directions (one up, one down), in which
    case they're kept as separate same-x events instead (audit
    follow-up, 2026-07: divisi / two-voice writing at the same beat was
    otherwise getting merged into one chord).
  - **Duration = mode of the chord's noteheads.** Realistically all
    noteheads in a chord share one stem, so they should have the same
    duration. If the detector disagrees (one of three was a half, the
    others quarters), we take the most common.
  - **Single voice per staff.** No stem-up vs stem-down splitting yet.
    Two-voice piano writing (LH chord + RH melody on the bass staff)
    will get merged into one voice. That's acceptable for v1; Phase
    4f-ish will revisit.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def _is_pitched_notehead(det: dict[str, Any]) -> bool:
    """Notehead with a resolved pitch and a duration."""
    return (
        det.get("category") == "notehead"
        and det.get("pitch") is not None
        and det.get("duration_beats") is not None
    )


def _is_durationed_rest(det: dict[str, Any]) -> bool:
    """Rest with a resolved duration."""
    return (
        det.get("category") == "rest"
        and det.get("duration_beats") is not None
    )


def _x_center(det: dict[str, Any]) -> int:
    bbox = det.get("bbox", [0, 0, 0, 0])
    return bbox[0] + bbox[2] // 2


def _bbox_width(det: dict[str, Any]) -> int:
    return det.get("bbox", [0, 0, 0, 0])[2]


def group_chords_in_measure(
    detections: list[dict[str, Any]],
    *,
    chord_x_tolerance: float | None = None,
) -> list[dict[str, Any]]:
    """Turn one measure's flat detection list into an ordered list of
    musical events.

    Returns: list of event dicts, each with:
      - `kind`: "chord" or "rest"
      - `x_position`: x-center of the event (canonical coords)
      - `duration_beats`: float
      - `duration_type`: str
      - `dots`: int
      - `noteheads`: list[detection dict]  (for chords; empty for rests)
      - `rest`: detection dict             (for rests; None for chords)

    Events are sorted by x_position (= musical time).
    """
    # Pull out the pitched noteheads + durationed rests in x-order.
    noteheads = sorted(
        (d for d in detections if _is_pitched_notehead(d)),
        key=_x_center,
    )
    rests = sorted(
        (d for d in detections if _is_durationed_rest(d)),
        key=_x_center,
    )

    # ── Chord grouping ────────────────────────────────────────────────────
    # Noteheads within `chord_x_tolerance` of each other (in x) are the
    # same chord. Default tolerance is ~60% of an average notehead width
    # — wide enough to capture stems-shifted-left or right (which happens
    # for second-interval chords) but narrow enough to keep adjacent
    # rapid passages separate.
    if chord_x_tolerance is None:
        if noteheads:
            avg_w = sum(_bbox_width(n) for n in noteheads) / len(noteheads)
            chord_x_tolerance = avg_w * 0.6
        else:
            chord_x_tolerance = 30.0  # fallback

    # Divisi guard (audit follow-up, 2026-07): on dense orchestral pages,
    # two independent voices frequently sit at nearly the same x with
    # OPPOSITE stem directions (e.g. divisi strings — upper divisi
    # stem-up, lower divisi stem-down). x-only grouping used to merge
    # these into one "chord" and pick a single duration via mode-vote
    # over the merged noteheads, corrupting both durations and — via
    # split_events_into_voices downstream — the per-voice beat sum.
    # A real chord's noteheads share ONE physical stem, so a genuine
    # chord's members should never disagree on stem direction; when they
    # do, treat it as two simultaneous single-x events instead of one
    # chord, so each keeps its own (already independently resolved —
    # see rhythm.py) duration. Same/unknown direction still merges as
    # before — this only changes behavior for the explicit-conflict case.
    def _directions_conflict(nh, group) -> bool:
        nh_dir = nh.get("stem_direction")
        if not nh_dir:
            return False  # unknown direction never blocks a merge
        group_dirs = {n.get("stem_direction") for n in group if n.get("stem_direction")}
        return bool(group_dirs) and nh_dir not in group_dirs

    chord_groups: list[list[dict[str, Any]]] = []
    for nh in noteheads:
        nh_x = _x_center(nh)
        # Search backward for the nearest x-compatible, direction-
        # compatible open group. Noteheads are x-sorted and groups are
        # created in non-decreasing x order (a divisi split creates two
        # groups at nearly the same x, back to back), so once a group is
        # further than `chord_x_tolerance` away, every earlier group is
        # too — safe to stop scanning.
        target = None
        for group in reversed(chord_groups):
            group_x = sum(_x_center(n) for n in group) / len(group)
            if abs(nh_x - group_x) > chord_x_tolerance:
                break
            if _directions_conflict(nh, group):
                continue
            target = group
            break
        if target is not None:
            target.append(nh)
        else:
            chord_groups.append([nh])

    # ── Build chord events ────────────────────────────────────────────────
    events: list[dict[str, Any]] = []
    for group in chord_groups:
        # Duration: take the most-common (duration_beats, duration_type, dots).
        durations = Counter(
            (n["duration_beats"], n["duration_type"], n["dots"]) for n in group
        )
        (best_beats, best_type, best_dots), _ = durations.most_common(1)[0]
        x_pos = int(sum(_x_center(n) for n in group) / len(group))
        # Stem direction: most-common direction in the group (if any).
        directions = Counter(
            n.get("stem_direction") for n in group if n.get("stem_direction")
        )
        stem_dir = directions.most_common(1)[0][0] if directions else None
        # Tie flags: an event ties INTO the next event if ANY of its
        # noteheads has `tied_to_next` set, and similarly for `tied_from_prev`.
        # In practice most ties bind one notehead, but for chord-to-chord
        # ties the convention is "if any voice is tied, the chord is tied."
        tied_to_next = any(n.get("tied_to_next") for n in group)
        tied_from_prev = any(n.get("tied_from_prev") for n in group)
        events.append({
            "kind": "chord",
            "x_position": x_pos,
            "duration_beats": best_beats,
            "duration_type": best_type,
            "dots": best_dots,
            "stem_direction": stem_dir,
            "noteheads": list(group),
            "rest": None,
            "tied_to_next": tied_to_next,
            "tied_from_prev": tied_from_prev,
        })

    # ── Add rest events ───────────────────────────────────────────────────
    for r in rests:
        events.append({
            "kind": "rest",
            "x_position": _x_center(r),
            "duration_beats": r["duration_beats"],
            "duration_type": r["duration_type"],
            "dots": r.get("dots", 0),
            "stem_direction": None,
            "noteheads": [],
            "rest": r,
        })

    # Sort everything by x_position so the output is in musical time order.
    events.sort(key=lambda ev: ev["x_position"])
    return events


def split_events_into_voices(
    events: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Split a measure's events into 1 or 2 voices.

    V1 rule:
      - If at least one event has stem-up AND another has stem-down at a
        different x position, emit TWO voices: voice 1 = stem-up + rests,
        voice 2 = stem-down + rests.
      - Otherwise, single voice (all events on one staff line).

    Rests appear in BOTH voices in the two-voice case so that LilyPond /
    MusicXML render barlines + rhythm correctly per voice. The MusicXML
    `<voice>` tag distinguishes which voice the rest belongs to; in
    LilyPond, `\voiceTwo` rests appear lower on the staff.

    Returns a list of voice-event-lists in voice-number order.
    """
    # Detect whether we have both stem-up and stem-down note events.
    up_events = [e for e in events if e["kind"] == "chord"
                 and e.get("stem_direction") == "up"]
    down_events = [e for e in events if e["kind"] == "chord"
                   and e.get("stem_direction") == "down"]
    rest_events = [e for e in events if e["kind"] == "rest"]
    unknown_events = [e for e in events if e["kind"] == "chord"
                      and e.get("stem_direction") not in ("up", "down")]

    # If only one direction (or none) appears, single voice.
    if not up_events or not down_events:
        return [events]

    # Two-voice split: stem-up = voice 1, stem-down = voice 2. Unknown-
    # direction notes go in voice 1 (closer to the "main" line). Rests
    # appear in both voices.
    v1 = sorted(up_events + unknown_events + rest_events,
                key=lambda e: e["x_position"])
    v2 = sorted(down_events + rest_events, key=lambda e: e["x_position"])
    return [v1, v2]


def group_chords_in_transcribe_result(result: dict[str, Any]) -> None:
    """Walk a transcribe.py result tree and add a `voices` array to each
    measure dict. The new schema looks like:

        measures[j]["voices"] = [
            {
                "voice_index": 0,
                "events": [
                    {kind, x_position, duration_beats, duration_type,
                     dots, noteheads (refs into detections), rest (ref)},
                    ...
                ]
            }
        ]

    V1 emits exactly one voice per staff. Future versions may split into
    multiple voices based on stem direction or rest interleaving.

    Mutates `result` in place. Returns None.
    """
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for measure in staff.get("measures", []):
                    events = group_chords_in_measure(
                        measure.get("detections", [])
                    )
                    measure["voices"] = [{
                        "voice_index": 0,
                        "n_events": len(events),
                        "events": events,
                    }]
