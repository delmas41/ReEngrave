"""Resolve WHICH staff line a detected clef names, from its geometry.

The detector's class space (DeepScoresV2) carries exactly two C-clef classes,
`cClefAlto` and `cClefTenor`, and it is asked to tell them apart from
appearance alone. It cannot — not reliably, and not because the model is
weak. **They are the same glyph.** An alto clef and a tenor clef are one
drawing printed one staff line apart; the ink is identical. Everything that
distinguishes them lives in the glyph's vertical position on the staff, which
a class label throws away. Soprano, mezzo-soprano and baritone clefs are the
same glyph again, on three more lines, and DSv2 has no classes for them at
all — so no amount of training on that label space can ever emit one.

That is why alto/tenor confusion survived a clef-targeted fine-tune (1/3 alto
on the first run; the corrected retrain fixed alto but flipped some tenors the
other way — see `benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`). It is a
mislabelled *task*, not an under-trained model.

So this module doesn't ask the classifier which C-clef it is. It measures.

    the clef's named line  ──►  snap to the nearest of the 5 staff lines
                                ──►  look the clef up by (family, line)

The detector is left with the job it can actually do — *finding* a clef and
naming its family (G / C / F), which is a real visual distinction — and
geometry decides the rest. The result is exact rather than probabilistic: a
C-clef centred on the middle line IS an alto clef, and a C-clef centred one
line above it IS a tenor clef, with no confusion matrix in between.

## Where a clef's named line sits inside its bounding box

A C-clef is vertically symmetric about the line it names (Bravura's
`cClefAlto` bbox runs −2.0 … +2.0 staff spaces around the line), so the
named line is simply the bbox's vertical centre — no calibration needed, and
the symmetry holds for the archaic "ladder" C-clefs of 19th-century
engravings just as it does for a modern font.

G and F clefs are NOT symmetric: a G clef hangs far below its line and an F
clef sits mostly below its own, so their named line is at some family-specific
fraction of the bbox height. Those fractions are measurable (see
`tools/omr/training/calibrate_clef_anchors.py`) but they are also *unnecessary*
in practice, because the alternatives are vanishingly rare — french violin
clef (G on line 1), varbaritone (F on 3) and sub-bass (F on 5) essentially do
not occur in the repertoire this pipeline targets, while treble and bass are
everywhere. Guessing a rare clef from an uncalibrated offset would shift every
pitch on the staff, so geometric resolution is **enabled for C clefs only** by
default. `ClefGeometryConfig` can turn on the G/F families once their anchor
fractions are calibrated, and the machinery is family-agnostic either way.

## Abstention

Snapping is only trusted when the estimated line lands close to an actual
staff line (`max_residual`, in units of one line spacing). A clef whose box is
badly fitted, or a cell with no usable staff-line geometry, falls back to the
class label rather than inventing a clef — the same abstain-when-blind rule the
rest of the verification layer follows (`docs/internal-consistency-checks.md`).
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# The clef table
# ---------------------------------------------------------------------------
#
# Staff lines are numbered the conventional way: line 1 = BOTTOM, line 5 = TOP.
# Each entry is the clef that results from printing that family's glyph on that
# line. Names match LilyPond's `\clef` arguments exactly (and are the keys
# `pitch_resolver._CLEF_ANCHORS` / `export._MXL_CLEF_SIGN` use), so a resolved
# clef flows straight through to LilyPond and MusicXML with no translation.

CLEF_BY_FAMILY_LINE: dict[str, dict[int, str]] = {
    "G": {
        1: "french",        # G clef on line 1 — french violin clef
        2: "treble",        # the ordinary treble clef
    },
    "C": {
        1: "soprano",
        2: "mezzosoprano",
        3: "alto",          # C4 on the middle line — violas, alto voice
        4: "tenor",         # one line up — trombones, cellos, tenor voice
        5: "baritone",      # C-clef baritone
    },
    "F": {
        3: "varbaritone",   # F-clef baritone
        4: "bass",          # the ordinary bass clef
        5: "subbass",
    },
}

# Inverse lookup: clef name → (family, line-from-bottom).
CLEF_TO_FAMILY_LINE: dict[str, tuple[str, int]] = {
    name: (family, line)
    for family, lines in CLEF_BY_FAMILY_LINE.items()
    for line, name in lines.items()
}

# The default clef for each family — what the class label alone can tell us,
# and what we fall back to whenever geometry abstains.
DEFAULT_CLEF_FOR_FAMILY: dict[str, str] = {"G": "treble", "C": "alto", "F": "bass"}

# Fraction of the bounding box height, measured DOWN FROM THE TOP, at which
# the clef's named line crosses the glyph. 0.5 = vertically centred on it.
#
# Only the C entry is trusted by default (it follows from the glyph's symmetry
# rather than from a measurement). The G and F values are the Bravura
# reference-font proportions and are provided so that enabling those families
# is a config change rather than a code change — but they are unverified
# against this detector's boxes, hence `families` below.
ANCHOR_FRACTION_FROM_TOP: dict[str, float] = {
    "C": 0.500,
    "G": 0.625,
    "F": 0.285,
}


@dataclass(frozen=True)
class ClefGeometryConfig:
    """Knobs for geometric clef resolution.

    families:      which clef families geometry is allowed to resolve. C only
                   by default — see the module docstring on why guessing a rare
                   G/F variant is a bad trade.
    max_residual:  how far (in line spacings) the estimated named line may sit
                   from the nearest real staff line before we abstain. 0.35 is
                   comfortably inside the half-spacing that separates a line
                   from the space next to it, so a box has to be genuinely
                   misfitted to be rejected.
    """

    families: frozenset[str] = frozenset({"C"})
    max_residual: float = 0.35


DEFAULT_CONFIG = ClefGeometryConfig()


@dataclass(frozen=True)
class ClefRead:
    """The outcome of resolving one clef detection.

    name:      the resolved clef ("alto", "tenor", "treble", …) — always a key
               of `pitch_resolver._CLEF_ANCHORS`.
    family:    "G" / "C" / "F".
    line:      staff line the clef names (1 = bottom … 5 = top), or None when
               resolution fell back to the class label.
    source:    "geometry" when the line was measured, "class" when the class
               label decided it.
    residual:  distance from the estimated named line to the staff line it
               snapped to, in line spacings. None when geometry didn't run.
    """

    name: str
    family: str
    line: int | None
    source: str
    residual: float | None = None


def _clef_core(smufl: str | None) -> str | None:
    """Reduce a clef class name to the part that identifies it.

    The same clef travels under two spellings — DeepScoresV2 writes `cClefAlto`
    and `gClef`, while the detector wrapper re-emits them as `clefCAlto` and
    `clefG` — so matching on prefixes means silently handling only one of them.
    Deleting the word "clef" (and the "Change" suffix that marks a mid-staff
    clef change, which names the same clef) collapses both spellings onto the
    same core: "calto", "ctenor", "g", "f".

    Returns None for classes that name no pitch.
    """
    if not smufl:
        return None
    s = smufl.lower()
    if "percussion" in s or s in ("clef8", "clef15"):
        return None
    core = s.replace("clef", "").replace("change", "")
    return core or None


def clef_family(smufl: str | None) -> str | None:
    """Map a clef class name to a clef family ("G" / "C" / "F"), or None if the
    class is not a pitched clef.

    `clef8` / `clef15` are octave markers that attach to another clef, and
    percussion clefs name no pitch — both are None, matching the behaviour
    `transcribe._clef_name_from_class` already relies on.
    """
    core = _clef_core(smufl)
    if not core:
        return None
    initial = core[0]
    return {"c": "C", "g": "G", "f": "F"}.get(initial)


def clef_name_from_class(smufl: str | None) -> str | None:
    """The class-label-only reading of a clef detection — the fallback when
    geometry can't run. Generic/unknown C-clef classes resolve to alto, the
    commonest C clef.
    """
    family = clef_family(smufl)
    if family is None:
        return None
    if family == "C":
        core = _clef_core(smufl) or ""
        if "tenor" in core:
            return "tenor"
        return "alto"
    return DEFAULT_CLEF_FOR_FAMILY[family]


def _snap_to_staff_line(
    y: float, staff_line_ys: list[int] | list[float]
) -> tuple[int, float] | None:
    """Snap a y coordinate to the nearest staff line.

    Returns `(line_from_bottom, residual_in_line_spacings)`, or None if the
    staff geometry is unusable. Lines are numbered 1 = bottom … 5 = top, and
    the residual is unsigned.

    Staves with more or fewer than 5 detected lines are rejected rather than
    guessed at: the family→line table is defined on a 5-line staff, so a
    4-line or 6-line reading would silently mis-number every clef.
    """
    if not staff_line_ys or len(staff_line_ys) != 5:
        return None
    ys = sorted(float(v) for v in staff_line_ys)  # ascending y = top → bottom
    gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
    spacing = sum(gaps) / len(gaps)
    if spacing <= 0:
        return None
    best_idx = min(range(5), key=lambda i: abs(ys[i] - y))
    residual = abs(ys[best_idx] - y) / spacing
    # ys is top→bottom (index 0 = top = line 5), so flip to line-from-bottom.
    return 5 - best_idx, residual


def resolve_clef(
    smufl: str | None,
    *,
    y_top: float | None = None,
    height: float | None = None,
    anchor_y: float | None = None,
    staff_line_ys: list[int] | list[float] | None = None,
    config: ClefGeometryConfig = DEFAULT_CONFIG,
) -> ClefRead | None:
    """Resolve a clef detection to a clef name, preferring measured geometry
    over the class label.

    Returns None when the detection is not a pitched clef (percussion, octave
    marker, unrecognised class) — the caller should ignore it, exactly as it
    would have ignored a None from the old class-only mapping.

    Pass either a bounding box (`y_top` + `height`) or, when the named line has
    been measured directly, `anchor_y`.

    Geometry runs only when the family is enabled, a measurement is present,
    and the cell has a clean 5-line staff; otherwise the class label decides
    and `source` says so.
    """
    family = clef_family(smufl)
    if family is None:
        return None

    fallback = clef_name_from_class(smufl)
    assert fallback is not None  # family is not None ⇒ a name exists

    # `anchor_y` is the named line measured directly — what the CV locator
    # produces by finding the glyph's axis of symmetry. Falling back to the
    # box, the line is a family-specific fraction of the way down it.
    if anchor_y is None and y_top is not None and height is not None and height > 0:
        anchor_y = y_top + ANCHOR_FRACTION_FROM_TOP[family] * height
    if family not in config.families or anchor_y is None or not staff_line_ys:
        return ClefRead(name=fallback, family=family, line=None, source="class")

    snapped = _snap_to_staff_line(anchor_y, staff_line_ys)
    if snapped is None:
        return ClefRead(name=fallback, family=family, line=None, source="class")

    line, residual = snapped
    name = CLEF_BY_FAMILY_LINE[family].get(line)
    if name is None or residual > config.max_residual:
        # The glyph landed on a line this family never uses (e.g. a C clef
        # apparently on a ledger line), or too far from any line to trust.
        # Abstain: the class label is a weaker signal, but it is never absurd.
        return ClefRead(
            name=fallback, family=family, line=None, source="class", residual=residual
        )

    return ClefRead(
        name=name, family=family, line=line, source="geometry", residual=residual
    )


def resolve_clef_for_detection(
    detection,
    *,
    config: ClefGeometryConfig = DEFAULT_CONFIG,
) -> ClefRead | None:
    """`resolve_clef` for a `SymbolDetection`, pulling the box and the cell's
    canonical staff-line positions off the detection itself.

    Canonical coordinates are the right frame to work in: every cell is
    rescaled so the staff span is constant, so the box and the staff lines are
    already in the same units and the snap is scale-free.
    """
    cell = getattr(detection, "cell", None)
    staff_line_ys = getattr(cell, "staff_line_ys_canonical", None) if cell else None
    return resolve_clef(
        detection.smufl_name,
        y_top=detection.y_canonical,
        height=detection.height_canonical,
        staff_line_ys=staff_line_ys,
        config=config,
    )
