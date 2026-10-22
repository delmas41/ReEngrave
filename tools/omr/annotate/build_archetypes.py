"""Render a 72×72 PNG thumbnail for every DeepScoresV2 class using Bravura.

The labeling UI (server.py) shows these thumbnails as a category picker so the
labeler can click an archetype instead of typing a SMuFL name. We do this
once and check the PNGs in — it's faster than rendering on every page load
and the labeling UI ships with the repo so the PNGs ship with it too.

For each of the 208 DeepScoresV2 class names from
``tools/omr/training/deepscoresv2_208_classes.json``:

  1. Resolve to a SMuFL glyph name (`_SMUFL_OVERRIDES` for the ~70 DSv2
     names that don't have a 1:1 SMuFL hit — most are notehead-position
     variants where DSv2 distinguishes On-Line vs In-Space but SMuFL
     doesn't, plus the dynamics letter aliases and the alternate-naming
     clefs).
  2. Look up the codepoint in ``glyphnames.json``.
  3. Render the glyph at 72 px with Bravura.otf via Pillow.
  4. For OnLine / InSpace notehead variants, paste a small horizontal
     staff-line indicator behind the glyph so the labeler can tell them
     apart at a glance.
  5. Save to ``static/archetypes/<className>.png``.

A handful of DSv2 classes have no SMuFL glyph at all (``beam``, ``slur``,
``tie``, ``staff``, ``ledgerLine``, ``tupletBracket``, ``ottavaBracket``).
For those we draw a synthetic primitive (a horizontal bar, a curve, etc.)
so the picker tile is still visually distinct.

Output: ``tools/omr/annotate/static/archetypes/<className>.png`` (208 PNGs)
and ``tools/omr/annotate/static/archetypes/README.md`` documenting the
mapping decisions.

Run: ``python3 -m tools.omr.annotate.build_archetypes``
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


_HERE = Path(__file__).parent
_STATIC = _HERE / "static"
_BRAVURA = _STATIC / "bravura" / "Bravura.otf"
_GLYPHNAMES = _STATIC / "bravura" / "glyphnames.json"
_ARCHETYPES = _STATIC / "archetypes"
# The committed copy — training/data/ is gitignored (the DSv2 download lands
# there), so anything kept inside it is absent from a fresh clone.
_CLASSES_JSON = (
    _HERE.parent / "training" / "deepscoresv2_208_classes.json"
)

TILE = 72
FONT_SIZE = 56  # Bravura is large — leave breathing room inside the tile.


# DSv2 class name → SMuFL glyph name. Only DSv2 names that don't already
# match a SMuFL key need an entry here. Empty string means "synthetic
# primitive — render it ourselves" (see _draw_primitive below).
#
# Position suffix (`OnLine` / `InSpace`) is preserved in the *filename*
# but rendered against the same SMuFL glyph; we paint a tiny indicator
# line under the glyph so the labeler can tell them apart visually.
_SMUFL_OVERRIDES: dict[str, str] = {
    # ---- notehead position variants (DSv2: position-tagged, SMuFL: not) ----
    "noteheadBlackOnLine": "noteheadBlack",
    "noteheadBlackOnLineSmall": "noteheadBlack",
    "noteheadBlackInSpace": "noteheadBlack",
    "noteheadBlackInSpaceSmall": "noteheadBlack",
    "noteheadHalfOnLine": "noteheadHalf",
    "noteheadHalfOnLineSmall": "noteheadHalf",
    "noteheadHalfInSpace": "noteheadHalf",
    "noteheadHalfInSpaceSmall": "noteheadHalf",
    "noteheadHalfSmall": "noteheadHalf",
    "noteheadWholeOnLine": "noteheadWhole",
    "noteheadWholeOnLineSmall": "noteheadWhole",
    "noteheadWholeInSpace": "noteheadWhole",
    "noteheadWholeInSpaceSmall": "noteheadWhole",
    "noteheadDoubleWholeOnLine": "noteheadDoubleWhole",
    "noteheadDoubleWholeOnLineSmall": "noteheadDoubleWhole",
    "noteheadDoubleWholeInSpace": "noteheadDoubleWhole",
    "noteheadDoubleWholeInSpaceSmall": "noteheadDoubleWhole",
    "noteheadFullSmall": "noteheadBlack",
    # ---- alternate clef naming (DSv2: clefG, SMuFL: gClef) ----
    "clefG": "gClef",
    "clefF": "fClef",
    "clefC": "cClef",
    # SMuFL has a single cClef glyph; alto vs tenor is a staff-position
    # distinction the engraver chooses, not a separate codepoint. We
    # render the same glyph and let the filename tell the labeler which
    # one they're labeling.
    "cClefAlto": "cClef",
    "cClefTenor": "cClef",
    "clefCAlto": "cClef",
    "clefCTenor": "cClef",
    "clefUnpitchedPercussion": "unpitchedPercussionClef1",
    # ---- "Small" accidental / flag variants → base glyph ----
    "accidentalFlatSmall": "accidentalFlat",
    "accidentalNaturalSmall": "accidentalNatural",
    "accidentalSharpSmall": "accidentalSharp",
    "flag8thDownSmall": "flag8thDown",
    "flag8thUpSmall": "flag8thUp",
    # ---- key-signature aliases (same glyphs as accidentals) ----
    "keyFlat": "accidentalFlat",
    "keyNatural": "accidentalNatural",
    "keySharp": "accidentalSharp",
    # ---- articulation naming ----
    "articulationAccent": "articAccentAbove",
    "articulationStaccato": "articStaccatoAbove",
    "articulationTenuto": "articTenutoAbove",
    "articulationMarcatoAbove": "articMarcatoAbove",
    "articulationMarcatoBelow": "articMarcatoBelow",
    # ---- dynamics (DSv2 has both `dynamicP` and `dynamicLetterP` — both
    # are the same Bravura glyph) ----
    "dynamicP": "dynamicPiano",
    "dynamicM": "dynamicMezzo",
    "dynamicF": "dynamicForte",
    "dynamicS": "dynamicSforzando",
    "dynamicZ": "dynamicZ",
    "dynamicR": "dynamicRinforzando",
    "dynamicLetterP": "dynamicPiano",
    "dynamicLetterM": "dynamicMezzo",
    "dynamicLetterF": "dynamicForte",
    "dynamicLetterS": "dynamicSforzando",
    "dynamicLetterZ": "dynamicZ",
    "dynamicLetterR": "dynamicRinforzando",
    # ---- grace notes / arpeggio / tremolo ----
    "graceNoteAcciaccatura": "graceNoteAcciaccaturaStemUp",
    "arpeggio": "wiggleArpeggiatoUp",
    "tremoloMark": "tremolo1",
    # ---- "rest H-bar number" — multi-measure rest body without the digit ----
    "restHNr": "restHBar",
    # ---- numerals (tuplet digits in second-half-of-list annotation set) ----
    "numeral": "tuplet3",
    "numeral0": "tuplet0",
    "numeral1": "tuplet1",
    "numeral2": "tuplet2",
    "numeral3": "tuplet3",
    "numeral4": "tuplet4",
    "numeral5": "tuplet5",
    "numeral6": "tuplet6",
    "numeral7": "tuplet7",
    "numeral8": "tuplet8",
    "numeral9": "tuplet9",
    # ---- tuple typos in second-half-of-list ----
    "tuple": "tuplet3",
    "tupleBracket": "",  # primitive — see _draw_primitive
    # ---- shapes with no single SMuFL glyph (graphic primitives) ----
    "beam": "",
    "slur": "",
    "tie": "",
    "staff": "",
    "ledgerLine": "",
    "tupletBracket": "",
    "ottavaBracket": "",
}


# Position indicator: notehead glyphs whose DSv2 name encodes whether the
# glyph sits on a staff line vs in a space. Key = DSv2 name, value =
# `(position, is_small)` so the renderer can draw an indicator strip.
_POSITION_TAGS: dict[str, tuple[str, bool]] = {}
for _name in list(_SMUFL_OVERRIDES):
    is_small = _name.endswith("Small")
    base = _name[: -len("Small")] if is_small else _name
    if base.endswith("OnLine"):
        _POSITION_TAGS[_name] = ("OnLine", is_small)
    elif base.endswith("InSpace"):
        _POSITION_TAGS[_name] = ("InSpace", is_small)


def _resolve_smufl_name(dsv2_name: str, glyphnames: dict) -> str | None:
    """Return the SMuFL glyph name for a DSv2 class, or None if synthetic.

    None means "render a primitive shape — there's no Bravura glyph that
    represents this concept" (beams, slurs, ties, ledger lines, staff).
    """
    if dsv2_name in _SMUFL_OVERRIDES:
        target = _SMUFL_OVERRIDES[dsv2_name]
        return target or None  # "" → primitive
    if dsv2_name in glyphnames:
        return dsv2_name
    return None


def _codepoint_char(cp_str: str) -> str:
    """`'U+E0A4'` → the Python str containing that codepoint."""
    return chr(int(cp_str.removeprefix("U+"), 16))


def _draw_glyph(
    codepoint_char: str,
    font: ImageFont.FreeTypeFont,
    position_tag: tuple[str, bool] | None,
) -> Image.Image:
    img = Image.new("RGBA", (TILE, TILE), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    # Optional staff-line position indicator drawn first (under the glyph).
    if position_tag is not None:
        position, _is_small = position_tag
        line_y = TILE // 2 + 2  # mid-tile, slightly below for visual balance
        if position == "OnLine":
            draw.line(
                [(6, line_y), (TILE - 6, line_y)], fill=(120, 120, 200, 200), width=1
            )
        else:  # InSpace — two lines bracketing the notehead
            draw.line(
                [(6, line_y - 7), (TILE - 6, line_y - 7)],
                fill=(120, 120, 200, 200),
                width=1,
            )
            draw.line(
                [(6, line_y + 7), (TILE - 6, line_y + 7)],
                fill=(120, 120, 200, 200),
                width=1,
            )
    # Center the glyph in the tile using its bbox. We anchor to "lt"
    # (left-top) for both the bbox query and the draw call: SMuFL fonts
    # use a baseline that's far below the glyph (so default-anchor text
    # would draw the glyph well past the bottom of the tile).
    bbox = draw.textbbox((0, 0), codepoint_char, font=font, anchor="lt")
    glyph_w = bbox[2] - bbox[0]
    glyph_h = bbox[3] - bbox[1]
    if glyph_w <= 0 or glyph_h <= 0:
        # Some metadata glyphs render to nothing — fall through to "?"
        # so the tile is at least visible.
        draw.text(
            (TILE // 2 - 6, TILE // 2 - 18),
            "?",
            font=font,
            fill=(180, 180, 180, 255),
        )
        return img
    tx = (TILE - glyph_w) // 2 - bbox[0]
    ty = (TILE - glyph_h) // 2 - bbox[1]
    draw.text((tx, ty), codepoint_char, font=font, anchor="lt", fill=(20, 20, 20, 255))
    return img


def _draw_primitive(dsv2_name: str) -> Image.Image:
    """Render a synthetic primitive for shapes Bravura doesn't enumerate."""
    img = Image.new("RGBA", (TILE, TILE), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    mid = TILE // 2
    if dsv2_name == "beam":
        draw.rectangle([8, mid - 4, TILE - 8, mid + 4], fill=(20, 20, 20, 255))
    elif dsv2_name == "ledgerLine":
        draw.rectangle([4, mid - 1, TILE - 4, mid + 1], fill=(20, 20, 20, 255))
    elif dsv2_name == "staff":
        for i, dy in enumerate((-16, -8, 0, 8, 16)):
            draw.line(
                [(4, mid + dy), (TILE - 4, mid + dy)], fill=(20, 20, 20, 255), width=1
            )
    elif dsv2_name == "slur":
        # Pillow's arc draws an arc inside a bounding box.
        draw.arc([6, 12, TILE - 6, TILE - 12], start=180, end=360, fill=(20, 20, 20, 255), width=2)
    elif dsv2_name == "tie":
        # Shorter, flatter arc than slur.
        draw.arc([10, 26, TILE - 10, TILE - 18], start=180, end=360, fill=(20, 20, 20, 255), width=2)
    elif dsv2_name in ("tupletBracket", "tupleBracket"):
        draw.line([(8, mid + 12), (8, mid + 4)], fill=(20, 20, 20, 255), width=2)
        draw.line(
            [(8, mid + 4), (TILE - 8, mid + 4)], fill=(20, 20, 20, 255), width=2
        )
        draw.line(
            [(TILE - 8, mid + 4), (TILE - 8, mid + 12)],
            fill=(20, 20, 20, 255),
            width=2,
        )
        # Small "3" hint
        try:
            f = ImageFont.truetype(str(_BRAVURA), 18)
            draw.text((mid - 5, mid - 14), "3", font=f, fill=(20, 20, 20, 255))
        except Exception:
            pass
    elif dsv2_name == "ottavaBracket":
        draw.line(
            [(20, mid + 2), (TILE - 4, mid + 2)], fill=(20, 20, 20, 255), width=2
        )
        draw.line(
            [(TILE - 4, mid + 2), (TILE - 4, mid + 12)],
            fill=(20, 20, 20, 255),
            width=2,
        )
        try:
            f = ImageFont.truetype(str(_BRAVURA), 22)
            # SMuFL has dedicated "ottava" glyph (8va body) — fallback to literal "8"
            draw.text((4, mid - 14), "8", font=f, fill=(20, 20, 20, 255))
        except Exception:
            pass
    else:
        # Unknown — draw a faint "?" so the labeler can still see something.
        try:
            f = ImageFont.truetype(str(_BRAVURA), 30)
            draw.text((mid - 6, mid - 18), "?", font=f, fill=(180, 180, 180, 255))
        except Exception:
            pass
    return img


def main() -> None:
    if not _BRAVURA.exists():
        raise SystemExit(
            f"missing Bravura.otf at {_BRAVURA} — see "
            f"tools/omr/annotate/static/bravura/README in the archetypes README"
        )
    if not _GLYPHNAMES.exists():
        raise SystemExit(f"missing glyphnames.json at {_GLYPHNAMES}")
    if not _CLASSES_JSON.exists():
        raise SystemExit(f"missing class list at {_CLASSES_JSON}")

    glyphnames = json.loads(_GLYPHNAMES.read_text())
    classes = json.loads(_CLASSES_JSON.read_text())
    # The DSv2 list has duplicates (two annotation sets); render each
    # unique name once.
    unique_classes = list(dict.fromkeys(classes))
    font = ImageFont.truetype(str(_BRAVURA), FONT_SIZE)

    _ARCHETYPES.mkdir(parents=True, exist_ok=True)

    n_smufl = 0
    n_override = 0
    n_primitive = 0
    n_missing = 0
    mapping_rows: list[tuple[str, str, str]] = []

    for dsv2 in unique_classes:
        smufl_name = _resolve_smufl_name(dsv2, glyphnames)
        out = _ARCHETYPES / f"{dsv2}.png"
        if smufl_name is None and dsv2 not in _SMUFL_OVERRIDES:
            n_missing += 1
            mapping_rows.append((dsv2, "(missing)", "no SMuFL match — primitive `?` tile"))
            _draw_primitive(dsv2).save(out)
            continue
        if smufl_name is None:
            # Explicit override that says "draw a primitive"
            n_primitive += 1
            mapping_rows.append((dsv2, "(primitive)", "graphic primitive — no Bravura glyph"))
            _draw_primitive(dsv2).save(out)
            continue
        # Glyph render path
        entry = glyphnames.get(smufl_name)
        if entry is None:
            n_missing += 1
            mapping_rows.append(
                (dsv2, smufl_name, "override target not in glyphnames.json")
            )
            _draw_primitive(dsv2).save(out)
            continue
        cp_char = _codepoint_char(entry["codepoint"])
        pos_tag = _POSITION_TAGS.get(dsv2)
        img = _draw_glyph(cp_char, font, pos_tag)
        img.save(out)
        if dsv2 == smufl_name:
            n_smufl += 1
            kind = "direct SMuFL match"
        else:
            n_override += 1
            kind = "override → SMuFL fallback"
        if pos_tag is not None:
            kind += f" (with {pos_tag[0]} indicator)"
        mapping_rows.append((dsv2, smufl_name, kind))

    # Write README documenting the mapping.
    readme = _ARCHETYPES / "README.md"
    lines: list[str] = []
    lines.append("# Archetype thumbnails — DSv2 class → Bravura SMuFL glyph")
    lines.append("")
    lines.append(
        "Generated by `python3 -m tools.omr.annotate.build_archetypes`. "
        "Do not hand-edit the PNGs; re-run the script and re-commit instead."
    )
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- {n_smufl} direct SMuFL matches")
    lines.append(f"- {n_override} overrides to a close SMuFL glyph")
    lines.append(f"- {n_primitive} synthetic primitives (beam / slur / staff / …)")
    lines.append(f"- {n_missing} unresolved (rendered as `?` placeholder)")
    lines.append(f"- **{len(unique_classes)} unique DSv2 classes total**")
    lines.append("")
    lines.append("## Position tags for noteheads")
    lines.append("")
    lines.append(
        "DeepScoresV2 distinguishes `noteheadBlackOnLine` from "
        "`noteheadBlackInSpace`, but SMuFL has a single `noteheadBlack` "
        "glyph. We render the same glyph in both cases and overlay a small "
        "horizontal staff-line indicator behind the glyph: one line "
        "through the middle for **OnLine** variants, two flanking lines "
        "for **InSpace** variants. Look at the tile, not just the filename."
    )
    lines.append("")
    lines.append("## Full mapping")
    lines.append("")
    lines.append("| DSv2 class | SMuFL glyph used | Notes |")
    lines.append("|---|---|---|")
    for dsv2, smufl_name, kind in sorted(mapping_rows):
        lines.append(f"| `{dsv2}` | `{smufl_name}` | {kind} |")
    lines.append("")
    readme.write_text("\n".join(lines))

    print(f"wrote {len(unique_classes)} archetypes to {_ARCHETYPES}/")
    print(f"  {n_smufl} direct  ·  {n_override} override  ·  "
          f"{n_primitive} primitive  ·  {n_missing} unresolved")


if __name__ == "__main__":
    main()
