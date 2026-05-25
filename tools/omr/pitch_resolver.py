"""Map a notehead's y-position to a pitch using the staff lines and clef.

Phase 2 MVP: treble clef only. Clef detection from the image is Phase 2.5.
"""

from __future__ import annotations

from .template_matcher import SymbolDetection

# Pitch class names in C-major scale order
_PITCH_CYCLE = ["C", "D", "E", "F", "G", "A", "B"]


# Each clef "anchor" maps the position of one staff line to a pitch.
# Position index is measured in HALF-line-spacings from the TOP staff line
# (= position 0). Going down increases the index; each half-spacing = one
# diatonic step.
#
# Treble clef: top line = F5, then below by step: E5 (top space), D5 (4th line),
# C5 (3rd space), B4 (middle line = pos 4), A4 (2nd space), G4 (2nd line),
# F4 (1st space), E4 (bottom line = pos 8)
#
# So pos 0 = F5, increasing pos = decreasing diatonic pitch.
_CLEF_ANCHORS = {
    "treble": ("F", 5),   # (pitch_class, octave) at pos 0 (top line)
    "bass":   ("A", 3),   # top line of bass clef = A3
    "alto":   ("G", 4),   # top line of alto clef = G4
    "tenor":  ("E", 4),   # top line of tenor clef = E4

    # Octave-shifted clefs. A `clef8`/`clef15` glyph detected ABOVE the
    # base clef means "sounds an octave (or two) HIGHER than written"
    # (8va / 15ma), and BELOW means LOWER (8vb / 15mb). transcribe.py
    # appends the suffix to the base clef name; this table just shifts
    # the anchor octave accordingly. Common in real music:
    #   - tenor part written treble_8vb (very common in choral)
    #   - piccolo written treble_8va
    #   - double bass written bass_8vb
    "treble_8va":  ("F", 6),
    "treble_8vb":  ("F", 4),
    "treble_15ma": ("F", 7),
    "treble_15mb": ("F", 3),
    "bass_8va":    ("A", 4),
    "bass_8vb":    ("A", 2),
    "bass_15ma":   ("A", 5),
    "bass_15mb":   ("A", 1),
}


def _pitch_from_position(pos_half_steps: int, clef: str) -> str | None:
    """Given a position measured in half-line-spacings from the top staff line
    (positive = downward), return a pitch label like "C4".

    Each half-spacing on the staff = one diatonic step.
    """
    anchor = _CLEF_ANCHORS.get(clef)
    if anchor is None:
        return None
    pc, octave = anchor
    pc_index = _PITCH_CYCLE.index(pc)
    # Going down = decreasing pitch; pos increases downward
    # Each step in pos shifts pc_index down by 1 (wrapping with octave change)
    new_pc_index = pc_index - pos_half_steps
    # Adjust octave: each full -7 wrap in pc_index = octave down
    new_octave = octave
    while new_pc_index < 0:
        new_pc_index += 7
        new_octave -= 1
    while new_pc_index >= 7:
        new_pc_index -= 7
        new_octave += 1
    return f"{_PITCH_CYCLE[new_pc_index]}{new_octave}"


def pitch_for_notehead(detection: SymbolDetection, clef: str = "treble") -> str | None:
    """Resolve the pitch of a notehead detection using its y-center and the
    cell's canonical staff line positions.

    Returns None if the cell lacks staff line info or the detection is not
    a notehead.
    """
    if detection.category != "notehead":
        return None
    cell = detection.cell
    if not cell.staff_line_ys_canonical or len(cell.staff_line_ys_canonical) < 2:
        return None

    lines = sorted(cell.staff_line_ys_canonical)  # top → bottom (ascending y)
    # Half-spacing reference: distance between adjacent lines / 2
    line_gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    avg_gap = sum(line_gaps) / len(line_gaps)
    half_step = avg_gap / 2.0

    top_y = lines[0]
    y_center = detection.y_center

    # Position in half-steps from top staff line (positive = downward)
    pos_float = (y_center - top_y) / half_step
    pos = int(round(pos_float))

    return _pitch_from_position(pos, clef)


def pitch_candidates_for_notehead(
    detection: SymbolDetection,
    clef: str = "treble",
    *,
    max_distance: float = 1.5,
    top_n: int = 3,
) -> list[tuple[str, float]]:
    """Return top-N pitch candidates for a notehead, weighted by y-position
    proximity.

    Used by M4's in-pipeline re-ranking. The primary `pitch_for_notehead`
    snaps to the single nearest staff position via round(); this function
    surfaces the next-nearest candidates so maestroAnalyst can break ties
    using harmonic context.

    Weight formula: linear falloff, 1.0 when exactly on a staff position,
    0.0 when `max_distance` half-steps away. With `max_distance=1.5` a
    note exactly between two positions (pos_float = N+0.5) gets ~0.67 for
    each adjacent position.

    Args:
        detection: the notehead detection.
        clef: e.g. "treble", "bass", "treble_8vb".
        max_distance: cutoff in half-step units. Candidates farther than
                      this are dropped.
        top_n: maximum number of candidates to return.

    Returns:
        List of (pitch_str, weight) tuples sorted descending by weight.
        Empty list if the cell lacks staff lines, the detection isn't a
        notehead, or no candidates lie within `max_distance`.
    """
    if detection.category != "notehead":
        return []
    cell = detection.cell
    if not cell.staff_line_ys_canonical or len(cell.staff_line_ys_canonical) < 2:
        return []

    lines = sorted(cell.staff_line_ys_canonical)
    line_gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    avg_gap = sum(line_gaps) / len(line_gaps)
    half_step = avg_gap / 2.0

    top_y = lines[0]
    y_center = detection.y_center
    pos_float = (y_center - top_y) / half_step
    nearest = int(round(pos_float))

    candidates: list[tuple[str, float]] = []
    # Scan ±3 half-steps around the nearest integer position. That's
    # always enough room to capture the top-3 closest staff positions
    # given any reasonable max_distance value.
    for offset in range(-3, 4):
        pos = nearest + offset
        dist = abs(pos - pos_float)
        if dist > max_distance:
            continue
        pitch = _pitch_from_position(pos, clef)
        if pitch is None:
            continue
        weight = max(0.0, 1.0 - dist / max_distance)
        candidates.append((pitch, weight))

    candidates.sort(key=lambda x: -x[1])
    return candidates[:top_n]
