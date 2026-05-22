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

  - **Chord grouping by x-position.** Noteheads whose x-centers fall
    within a small tolerance are considered "simultaneous" → one chord.
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

    chord_groups: list[list[dict[str, Any]]] = []
    for nh in noteheads:
        nh_x = _x_center(nh)
        # Greedy: append to the last group if its x is within tolerance.
        if chord_groups:
            last_group = chord_groups[-1]
            last_x = sum(_x_center(n) for n in last_group) / len(last_group)
            if abs(nh_x - last_x) <= chord_x_tolerance:
                last_group.append(nh)
                continue
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
        events.append({
            "kind": "chord",
            "x_position": x_pos,
            "duration_beats": best_beats,
            "duration_type": best_type,
            "dots": best_dots,
            "noteheads": list(group),
            "rest": None,
        })

    # ── Add rest events ───────────────────────────────────────────────────
    for r in rests:
        events.append({
            "kind": "rest",
            "x_position": _x_center(r),
            "duration_beats": r["duration_beats"],
            "duration_type": r["duration_type"],
            "dots": r.get("dots", 0),
            "noteheads": [],
            "rest": r,
        })

    # Sort everything by x_position so the output is in musical time order.
    events.sort(key=lambda ev: ev["x_position"])
    return events


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
