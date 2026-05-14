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
