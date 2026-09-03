"""FastAPI labeling UI for OMR verdict files (schema_version 2).

Replaces the legacy markdown-editor server. This one renders an
interactive page per cell with:

  - the cell PNG overlaid with all detection bboxes (color-coded by
    verdict)
  - a left sidebar listing every detection
  - a main panel with a cropped close-up of the selected detection, the
    model's predicted class + confidence, and 5 verdict buttons
    (TP / FP / Fix-class / Fix-bbox / Unsure)
  - a hierarchical class picker (tabs by category, grid of Bravura
    archetype thumbnails) for the Fix-class flow
  - a draw-mode for re-bbox'ing (Fix-bbox) and adding missed detections
    (right sidebar)
  - keyboard-first hotkeys (t/f/c/b/u/n/p/Tab/Shift-Tab/1-9)

Writes ``<cell_id>.verdict.json`` files in schema_version 2 (see
``data/user-labeled/README.md`` for the schema definition). Reads
schema_version 1 files transparently — they're surfaced to the UI as
v2 in memory but only persisted as v2 once the labeler hits Save (or
the autosave fires).

Usage
-----

    python3 -m tools.omr.annotate.server \\
        --bench-dir benchmarks/omr-phase-realft \\
        [--host 127.0.0.1] [--port 5050]

    # or, equivalently, just point at the verdicts dir — the rest of
    # the bench dir is auto-derived:
    python3 -m tools.omr.annotate.server \\
        --verdicts-dir benchmarks/omr-phase-realft/verdicts

The bench dir must contain at least::

    benchmarks/<phase>/
      cells.json               # cell manifest (the same one cell-extraction wrote)
      cells/<cell_id>.png      # cell PNGs
      detections/<cell_id>.json   # model detections (run_yolo.py output)
      verdicts/<cell_id>.verdict.json   # this script reads/writes here

It MAY also contain::

      batch_config.json        # single-symbol pass mode — see _load_batch_config
                               # and CLAUDE.md "Single-symbol pass mode"
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image


_HERE = Path(__file__).parent
_STATIC_DIR = _HERE / "static"
_ARCHETYPES_DIR = _STATIC_DIR / "archetypes"
# Bravura template metrics, written by symbol_library/builder.py. Each entry
# records the TRIMMED glyph's shape, which is what makes it a measurement
# rather than a guess — see _glyph_metrics().
_SYMBOL_MANIFEST = _HERE.parent / "symbol_library" / "data" / "manifest.json"
# The COMMITTED copy, one level up from training/data/. That directory is
# gitignored wholesale (it is where the multi-GB DeepScoresV2 download lands),
# so a copy kept inside it exists only on the machine that downloaded the
# dataset — every fresh clone and every git worktree came up without it and
# this module raised on import of the class catalog.
_CLASSES_JSON = _HERE.parent / "training" / "deepscoresv2_208_classes.json"


# ---------------------------------------------------------------------------
# Class catalog (DSv2 class → category, archetype URL)
# ---------------------------------------------------------------------------


# Categories surfaced in the picker, in display order. The first one with
# a substring match wins (so put "noteheadblack" before "notehead").
_CATEGORY_RULES: list[tuple[str, str]] = [
    # Long/specific keys first.
    ("gracenote", "ornament"),
    ("ornament", "ornament"),
    ("arpeggiato", "ornament"),
    ("arpeggio", "ornament"),
    ("fermata", "ornament"),
    ("tremolo", "ornament"),
    ("caesura", "ornament"),
    ("artic", "ornament"),
    ("strings", "ornament"),
    ("keyboardpedal", "ornament"),
    ("fingering", "ornament"),
    ("augmentationdot", "structural"),
    ("dynamic", "dynamic"),
    ("notehead", "notehead"),
    ("rest", "rest"),
    ("accidental", "accidental"),
    ("keyflat", "accidental"),
    ("keynatural", "accidental"),
    ("keysharp", "accidental"),
    ("flag", "flag"),
    ("timesig", "time_sig"),
    ("numeral", "time_sig"),
    ("clef", "clef"),
    ("tuplet", "structural"),
    ("tuple", "structural"),
    ("beam", "structural"),
    ("staff", "structural"),
    ("tie", "structural"),
    ("slur", "structural"),
    ("ledgerline", "structural"),
    ("legerline", "structural"),
    ("brace", "structural"),
    ("coda", "structural"),
    ("segno", "structural"),
    ("repeatdot", "structural"),
    ("ottavabracket", "structural"),
    # Barlines + repeats — their own category (added beyond DSv2's 208 classes)
    ("barline", "barline"),
    ("repeatright", "barline"),
    ("repeatleft", "barline"),
    # Textual dynamic / expression markings (dim., cresc., rit., dolce, pizz.,
    # arco, espress., legato, …) — DSv2 doesn't annotate them, this is a
    # custom catch-all for any italic music word the labeler encounters.
    ("textdynamic", "dynamic"),
    ("stem", "structural"),
]

# Display order of category tabs (also drives the `1`-`9` hotkeys).
_CATEGORY_ORDER = [
    "notehead",
    "rest",
    "accidental",
    "clef",
    "flag",
    "dynamic",
    "ornament",
    "time_sig",
    "barline",
    "structural",
]

# Custom classes that don't exist in DSv2's 208 — added by hand for things
# the dataset didn't annotate. These get included in the labeling picker
# (with archetypes rendered from Bravura) so a human can label them now;
# when verdicts get converted to YOLO training labels, they're appended
# to the class vocabulary as new IDs (208, 209, ...).
_CUSTOM_CLASSES: list[str] = [
    "barlineSingle",
    "barlineDouble",
    "barlineFinal",
    "repeatRight",
    "repeatLeft",
    "textDynamic",  # catch-all for italic text markings — dim. cresc. rit. dolce pizz. arco etc.
]


def _class_to_category(name: str) -> str:
    key = "".join(c for c in name.lower() if c.isalnum())
    for needle, cat in _CATEGORY_RULES:
        if needle in key:
            return cat
    return "structural"  # safe default — visible in picker rather than hidden


def _load_class_catalog() -> tuple[list[dict], dict[str, list[str]]]:
    """Return (classes, categories) where:

    - classes: list of {name, category, has_archetype}
    - categories: {category: [class_name, …]} in display order
    """
    if not _CLASSES_JSON.exists():
        raise FileNotFoundError(
            f"missing class list at {_CLASSES_JSON} — it should be committed; "
            "see tools/omr/training/deepscoresv2_208_classes.json"
        )
    raw = json.loads(_CLASSES_JSON.read_text())
    # The 208 DSv2 classes + custom classes (barlines etc) that DSv2 didn't
    # annotate but humans label by hand. Custom classes appear in the picker
    # but won't have model predictions until we re-train with them included.
    unique = list(dict.fromkeys(list(raw) + _CUSTOM_CLASSES))
    classes = []
    by_cat: dict[str, list[str]] = {c: [] for c in _CATEGORY_ORDER}
    for name in unique:
        cat = _class_to_category(name)
        if cat not in by_cat:
            by_cat[cat] = []
        archetype = _ARCHETYPES_DIR / f"{name}.png"
        classes.append(
            {
                "name": name,
                "category": cat,
                "has_archetype": archetype.exists(),
            }
        )
        by_cat[cat].append(name)
    for cat in by_cat:
        by_cat[cat].sort()
    return classes, by_cat


# ---------------------------------------------------------------------------
# Bench paths
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Bench:
    root: Path

    @property
    def manifest(self) -> Path:
        return self.root / "cells.json"

    @property
    def cells_dir(self) -> Path:
        return self.root / "cells"

    @property
    def detections_dir(self) -> Path:
        return self.root / "detections"

    @property
    def overlays_dir(self) -> Path:
        return self.root / "overlays"

    @property
    def verdicts_dir(self) -> Path:
        return self.root / "verdicts"

    @property
    def prefill_dir(self) -> Path:
        """Per-cell output of `training.mxl_verdicts` — the reference-driven
        pre-fill. Optional: a batch without it behaves exactly as before."""
        return self.root / "prefill"


@dataclass
class ManifestCache:
    by_id: dict[str, dict]
    ordered_ids: list[str]


def _load_manifest(bench: Bench) -> ManifestCache:
    if not bench.manifest.exists():
        raise FileNotFoundError(
            f"missing manifest at {bench.manifest} — run the cell selector first"
        )
    entries = json.loads(bench.manifest.read_text())
    by_id = {e["cell_id"]: e for e in entries}
    return ManifestCache(by_id=by_id, ordered_ids=[e["cell_id"] for e in entries])


def _load_detections(bench: Bench, cell_id: str) -> list[dict]:
    p = bench.detections_dir / f"{cell_id}.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    return data.get("detections", [])


def _load_prefill(bench: Bench, cell_id: str) -> dict | None:
    """The pre-fill record for a cell (status, reason, alignment, hints), or
    None where `mxl_verdicts` never ran. Hints are READ-ONLY markers: the
    reference says a note belongs here and the reading found none. They are
    never labels — the human draws the box, or decides there is nothing."""
    p = bench.prefill_dir / f"{cell_id}.json"
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    hints = [h for h in raw.get("hints", []) if isinstance(h, dict)]
    return {
        "status": raw.get("status"),
        "reason": raw.get("reason", ""),
        "measure_number": raw.get("measure_number"),
        "alignment": raw.get("alignment", {}),
        "n_tp": raw.get("n_tp", 0),
        "n_wrong_category": raw.get("n_wrong_category", 0),
        "n_added": raw.get("n_added", 0),
        "hints": hints,
    }


# ---------------------------------------------------------------------------
# Single-symbol pass mode (optional per-batch `batch_config.json`)
# ---------------------------------------------------------------------------
#
# A labelling campaign sweeps the SAME cell set several times, one symbol
# kind per sweep (hollow noteheads, then rests, then accidentals, …), which
# is far quicker than deciding every class on every cell. What makes it slow
# is the picker: 174 classes to scroll for a pass that only ever needs one.
#
# So a batch may ship a `batch_config.json` naming the classes this pass is
# for. It is entirely optional — with no config the server and UI behave
# exactly as they did before, which is the property the tests pin.


_BATCH_CONFIG_NAME = "batch_config.json"

# DSv2 splits several glyphs by where the notehead sits relative to the staff
# lines. That is GEOMETRY, not appearance — the two variants are the same
# glyph — so a pass can name the pair and let the click position choose.
_POSITION_KEYS = ("on_line", "in_space")

# A notehead is one staff space tall. That is the engraving definition, and
# the Bravura templates agree by construction: SMuFL sets the em box to four
# staff spaces, and `noteheadHalf` trims to exactly size_px/4 pixels tall at
# every size the library renders. Overridable per slot in the config.
_DEFAULT_HEIGHT_SPACES = 1.0
_FALLBACK_ASPECT = 1.0


def _base_glyph_name(class_name: str) -> str:
    """Strip the DSv2 staff-position suffix: noteheadHalfOnLine → noteheadHalf."""
    for suffix in ("OnLine", "InSpace"):
        if class_name.endswith(suffix):
            return class_name[: -len(suffix)]
    return class_name


_glyph_metrics_cache: dict[str, dict] | None = None


def _symbol_metrics() -> dict[str, dict]:
    """Measured Bravura proportions, keyed by base SMuFL glyph name.

    Read from the symbol library's committed manifest, which records each
    template's TRIMMED shape [h, w] and the font size it was rendered at.
    SMuFL's em box is four staff spaces, so ``h / (size_px / 4)`` is the
    glyph's height in staff spaces and ``w / h`` its aspect. Averaged over
    the three rendered sizes.

    Measured this way, `noteheadHalf` and `noteheadBlack` come out 1.000
    spaces tall at aspect 1.167, and `noteheadWhole` 1.000 at 1.722.
    """
    global _glyph_metrics_cache
    if _glyph_metrics_cache is not None:
        return _glyph_metrics_cache
    out: dict[str, list[tuple[float, float]]] = {}
    try:
        raw = json.loads(_SYMBOL_MANIFEST.read_text())
    except (OSError, json.JSONDecodeError):
        _glyph_metrics_cache = {}
        return _glyph_metrics_cache
    for e in raw.get("entries", []):
        shape = e.get("shape") or []
        size_px = e.get("size_px") or 0
        name = e.get("smufl_name") or ""
        if len(shape) != 2 or not size_px or not name:
            continue
        h, w = float(shape[0]), float(shape[1])
        if h <= 0 or w <= 0:
            continue
        out.setdefault(name, []).append((h / (size_px / 4.0), w / h))
    _glyph_metrics_cache = {
        name: {
            "height_spaces": sum(v[0] for v in vals) / len(vals),
            "aspect": sum(v[1] for v in vals) / len(vals),
        }
        for name, vals in out.items()
    }
    return _glyph_metrics_cache


def _glyph_metrics(class_name: str) -> dict:
    """Default click-box geometry for a class, measured where possible."""
    m = _symbol_metrics().get(_base_glyph_name(class_name))
    if m is None:
        return {
            "height_spaces": _DEFAULT_HEIGHT_SPACES,
            "aspect": _FALLBACK_ASPECT,
            "source": "fallback",
        }
    return {
        "height_spaces": round(m["height_spaces"], 4),
        "aspect": round(m["aspect"], 4),
        "source": "bravura",
    }


def _resolve_click_box(spec: Any, class_names: list[str]) -> dict | None:
    """Turn a slot's ``click_box`` config into concrete geometry.

    ``false``/absent → None (drag-to-draw only, which is what a rests pass
    wants: a rest's height varies with its value and no fixed box is right).
    ``true`` → the measured default for the slot's glyph.
    ``{...}`` → those keys, defaults filling the rest.
    """
    if spec is None or spec is False:
        return None
    base = _glyph_metrics(class_names[0]) if class_names else {
        "height_spaces": _DEFAULT_HEIGHT_SPACES,
        "aspect": _FALLBACK_ASPECT,
        "source": "fallback",
    }
    if spec is True:
        return base
    if not isinstance(spec, dict):
        raise ValueError(f"click_box must be true/false or an object, got {spec!r}")
    out = dict(base)
    for key in ("height_spaces", "aspect"):
        if key in spec:
            try:
                out[key] = float(spec[key])
            except (TypeError, ValueError):
                raise ValueError(f"click_box.{key} must be a number, got {spec[key]!r}")
            if out[key] <= 0:
                raise ValueError(f"click_box.{key} must be positive, got {out[key]}")
            out["source"] = "config"
    return out


@dataclass(frozen=True)
class PassSlot:
    """One palette entry — what a single number key selects."""

    index: int
    label: str
    kind: str  # "class" | "staff_position_pair"
    by_position: dict[str, str]  # {"": name} or {"on_line": …, "in_space": …}
    click_box: dict | None

    @property
    def class_names(self) -> list[str]:
        if self.kind == "staff_position_pair":
            return [self.by_position[k] for k in _POSITION_KEYS if k in self.by_position]
        return [self.by_position[""]]

    def class_for(self, position: str) -> str:
        if self.kind == "staff_position_pair":
            return self.by_position.get(position, self.class_names[0])
        return self.by_position[""]


@dataclass(frozen=True)
class PassConfig:
    pass_name: str
    note: str
    slots: list[PassSlot]
    warnings: list[str]

    @property
    def single(self) -> bool:
        return len(self.slots) == 1


def _parse_batch_config(raw: dict, known_classes: set[str]) -> PassConfig:
    """Validate a batch config dict into a PassConfig.

    Raises ValueError on anything malformed. A pass that names no usable
    class is an error rather than a silent fall-back to the full picker:
    serving today's UI to someone who asked for a single-symbol pass is the
    quiet-failure mode this repo has been bitten by before.
    """
    if not isinstance(raw, dict):
        raise ValueError("batch config must be a JSON object")
    entries = raw.get("classes")
    if entries is None:
        entries = raw.get("active_classes")  # accepted alias
    if not isinstance(entries, list) or not entries:
        raise ValueError("batch config needs a non-empty `classes` list")

    warnings: list[str] = []
    slots: list[PassSlot] = []

    def _known(name: str, where: str) -> str | None:
        if name in known_classes:
            return name
        warnings.append(f"{where}: unknown class {name!r} — dropped")
        return None

    for entry in entries:
        idx = len(slots)
        if isinstance(entry, str):
            name = _known(entry, f"classes[{idx}]")
            if name is None:
                continue
            slots.append(
                PassSlot(
                    index=idx,
                    label=name,
                    kind="class",
                    by_position={"": name},
                    click_box=_resolve_click_box(None, [name]),
                )
            )
            continue
        if not isinstance(entry, dict):
            raise ValueError(f"classes[{idx}] must be a string or an object")

        if any(k in entry for k in _POSITION_KEYS):
            by_position: dict[str, str] = {}
            for key in _POSITION_KEYS:
                val = entry.get(key)
                if val is None:
                    continue
                if not isinstance(val, str):
                    raise ValueError(f"classes[{idx}].{key} must be a class name")
                name = _known(val, f"classes[{idx}].{key}")
                if name is not None:
                    by_position[key] = name
            if len(by_position) < 2:
                # One half of the pair survived (or neither) — a pair whose
                # geometry cannot choose is not a pair.
                if not by_position:
                    continue
                only = next(iter(by_position.values()))
                warnings.append(
                    f"classes[{idx}]: only one half of the on_line/in_space pair "
                    f"resolved — treating {only!r} as a plain class"
                )
                slots.append(
                    PassSlot(
                        index=idx,
                        label=str(entry.get("label") or only),
                        kind="class",
                        by_position={"": only},
                        click_box=_resolve_click_box(entry.get("click_box"), [only]),
                    )
                )
                continue
            names = [by_position[k] for k in _POSITION_KEYS if k in by_position]
            slots.append(
                PassSlot(
                    index=idx,
                    label=str(entry.get("label") or _base_glyph_name(names[0])),
                    kind="staff_position_pair",
                    by_position=by_position,
                    click_box=_resolve_click_box(entry.get("click_box"), names),
                )
            )
            continue

        name_raw = entry.get("name")
        if not isinstance(name_raw, str):
            raise ValueError(
                f"classes[{idx}] needs `name`, or an `on_line`/`in_space` pair"
            )
        name = _known(name_raw, f"classes[{idx}].name")
        if name is None:
            continue
        slots.append(
            PassSlot(
                index=idx,
                label=str(entry.get("label") or name),
                kind="class",
                by_position={"": name},
                click_box=_resolve_click_box(entry.get("click_box"), [name]),
            )
        )

    if not slots:
        raise ValueError(
            "batch config resolved to no usable classes: "
            + ("; ".join(warnings) or "none named")
        )
    # Re-index so the number keys are 1..n over what actually resolved.
    slots = [
        PassSlot(
            index=i,
            label=s.label,
            kind=s.kind,
            by_position=s.by_position,
            click_box=s.click_box,
        )
        for i, s in enumerate(slots)
    ]
    return PassConfig(
        pass_name=str(raw.get("pass_name") or "labelling pass"),
        note=str(raw.get("note") or ""),
        slots=slots,
        warnings=warnings,
    )


def _load_batch_config(bench: Bench, known_classes: set[str]) -> PassConfig | None:
    """Read ``<bench>/batch_config.json`` if present. None means no pass mode."""
    p = bench.root / _BATCH_CONFIG_NAME
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"corrupt {_BATCH_CONFIG_NAME}: {e}") from e
    return _parse_batch_config(raw, known_classes)


# ---------------------------------------------------------------------------
# Staff geometry — which variant a click lands on
# ---------------------------------------------------------------------------


def _staff_spacing(staff_line_ys: list[float]) -> float | None:
    """Median gap between adjacent staff lines, in canonical px."""
    ys = sorted(float(y) for y in staff_line_ys or [])
    if len(ys) < 2:
        return None
    gaps = sorted(ys[i + 1] - ys[i] for i in range(len(ys) - 1))
    mid = len(gaps) // 2
    spacing = (
        gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2.0
    )
    return spacing if spacing > 0 else None


def _ledger_side_grid(
    edge_step: int,
    edge_y: float,
    sign: int,
    rungs: list[float] | None,
    spacing: float,
) -> list[tuple[int, float]]:
    """Half-space grid points beyond one staff edge, 6 spaces deep.

    Anchored on the MEASURED ledger rungs where the caller supplies them
    (ledger pitch is publisher-dependent in both directions — Litolff ~1.10x
    the staff spacing, Peters ~0.975x, measured in
    benchmarks/omr-snap-ledger-2026-09/), and extrapolated past the last
    measured rung at the last measured gap. With no rungs this reproduces
    the constant-spacing extrapolation exactly.
    """
    grid: list[tuple[int, float]] = []
    anchor = edge_y
    pitch = spacing
    n = 0
    for rung_y in rungs or []:
        if n >= 6:
            break
        n += 1
        grid.append((edge_step + sign * (2 * n - 1), (anchor + rung_y) / 2.0))
        grid.append((edge_step + sign * (2 * n), rung_y))
        pitch = abs(rung_y - anchor) or pitch
        anchor = rung_y
    while n < 6:
        n += 1
        nxt = anchor + sign * pitch
        grid.append((edge_step + sign * (2 * n - 1), (anchor + nxt) / 2.0))
        grid.append((edge_step + sign * (2 * n), nxt))
        anchor = nxt
    return grid


def snap_to_staff(
    staff_line_ys: list[float],
    y: float,
    ledger_rungs: dict[str, list[float]] | None = None,
) -> dict | None:
    """Snap a y to the nearest half-space position and say what it is.

    Notehead centres sit on a half-space grid: on a line, or in the space
    between two. Steps count half-spaces down from the TOP line, so an even
    step is a line and an odd step a space, and the parity keeps working
    through the ledger positions above and below the staff.

    The grid uses each staff's OWN measured line positions inside the staff
    (they are not perfectly even — one real cell reads 400/502/603/698/800).
    Beyond the staff it anchors on `ledger_rungs` — the rung positions
    measured off the cell image at the clicked x (ledger_grid.py) as
    {"above": [...], "below": [...]}, nearest rung first — because ledger
    pitch is a fact about the ENGRAVING, not derivable from the staff:
    extrapolating at the staff spacing mis-suggested 38% of 2nd-ledger-and-up
    variants on the hollow-campaign labels. Without rungs (or past the last
    measured one) it extrapolates the way it always did, so the in-staff
    grid and the no-image behaviour are unchanged.

    Returns None when the cell carries no usable staff geometry, which is an
    abstention: the caller falls back to asking the labeller.
    """
    ys = sorted(float(v) for v in staff_line_ys or [])
    spacing = _staff_spacing(ys)
    if spacing is None:
        return None
    inner: list[tuple[int, float]] = []
    for i, line_y in enumerate(ys):
        inner.append((2 * i, line_y))
        if i + 1 < len(ys):
            inner.append((2 * i + 1, (line_y + ys[i + 1]) / 2.0))
    # Ledger territory. The cell is the staff plus a few staff spaces of pad
    # (measure_extractor.PAD_*_STAFF_LINES), so 12 half-steps each way covers
    # any crop the extractor produces with room to spare.
    top_step, top_y = inner[0]
    bottom_step, bottom_y = inner[-1]
    rungs = ledger_rungs or {}

    def _snap(above_rungs, below_rungs):
        grid = list(inner)
        grid.extend(_ledger_side_grid(top_step, top_y, -1, above_rungs, spacing))
        grid.extend(
            _ledger_side_grid(bottom_step, bottom_y, 1, below_rungs, spacing)
        )
        return min(grid, key=lambda g: abs(g[1] - float(y)))

    above = rungs.get("above") or []
    below = rungs.get("below") or []
    step, snapped = _snap(above, below)
    # An incomplete ladder is a failed measurement for anything past it: a
    # real note beyond the staff has ledgers printed all the way to it, so a
    # click more than one half-step past the LAST measured rung means the
    # reader lost the trail — extrapolating a whole ladder from one nearby
    # rung measured WORSE than the constant pitch. Beyond a side's measured
    # reach, drop that side's rungs and snap the way the grid always did.
    if step < top_step and above and top_step - step > 2 * min(len(above), 6) + 1:
        step, snapped = _snap([], below)
    elif (
        step > bottom_step
        and below
        and step - bottom_step > 2 * min(len(below), 6) + 1
    ):
        step, snapped = _snap(above, [])
    result = {
        "step": step,
        "snapped_y": round(snapped, 2),
        "position": "on_line" if step % 2 == 0 else "in_space",
        "spacing": round(spacing, 2),
        "ledger": step < 0 or step > bottom_step,
    }
    if ledger_rungs is not None:
        result["measured_rungs"] = {
            "above": len(rungs.get("above") or []),
            "below": len(rungs.get("below") or []),
        }
    return result


def click_box_px(
    click_box: dict, spacing: float, x: float, y: float
) -> dict[str, int]:
    """Centre a click-box of the slot's measured size on (x, y)."""
    h = click_box["height_spaces"] * spacing
    w = h * click_box["aspect"]
    return {
        "x": int(round(x - w / 2.0)),
        "y": int(round(y - h / 2.0)),
        "w": max(1, int(round(w))),
        "h": max(1, int(round(h))),
    }


def _clamp_bbox(b: dict[str, int], width: int | None, height: int | None) -> dict:
    """Keep a box inside the cell image, the way the canvas does."""
    x, y, w, h = b["x"], b["y"], b["w"], b["h"]
    if width:
        x = max(0, min(x, max(0, width - 1)))
        w = max(1, min(w, width - x))
    else:
        x = max(0, x)
    if height:
        y = max(0, min(y, max(0, height - 1)))
        h = max(1, min(h, height - y))
    else:
        y = max(0, y)
    return {"x": x, "y": y, "w": w, "h": h}


# ---------------------------------------------------------------------------
# Verdict schema (v1 → v2 migration)
# ---------------------------------------------------------------------------


_VALID_VERDICTS = {"TP", "FP", "WRONG_CATEGORY", "WRONG_BBOX", "unsure"}


def _empty_v2_state(cell_id: str, detections: list[dict]) -> dict:
    return {
        "cell_id": cell_id,
        "schema_version": 2,
        "labeled_at_utc": None,
        "detections": [_init_detection_v2(d) for d in detections],
        "added_detections": [],
        # Which single-symbol passes have SWEPT this cell (see server.py's
        # pass-mode block). Empty is "never inspected in a pass"; a cell that
        # was inspected and found to hold none of a pass's symbols carries the
        # pass name here with added_detections still []. That is what makes
        # 48/48-inspected provable from the verdicts dir rather than a file
        # per drawn cell only.
        "inspected_passes": [],
    }


def _init_detection_v2(d: dict) -> dict:
    return {
        "id": d["id"],
        "verdict": None,
        "model_predicted_class": d.get("smufl_name", ""),
        "human_corrected_class": None,
        "model_predicted_category": d.get("category", ""),
        "human_corrected_category": None,
        "model_bbox": {
            "x": int(d.get("x", 0)),
            "y": int(d.get("y", 0)),
            "w": int(d.get("w", 0)),
            "h": int(d.get("h", 0)),
        },
        "human_bbox": None,
        "confidence": float(d.get("confidence", 0.0)),
        "notes": "",
    }


def _migrate_v1_to_v2(v1: dict, detections: list[dict]) -> dict:
    """Convert an old schema_v1 verdict dict to the v2 layout.

    v1 schema (existing on disk in benchmarks/omr-phase2.5/):
        {
          cell_id, verdicts: [{detection_id, smufl_name, verdict, actual_label?}],
          fn_noteheads: [{x_canonical, y_canonical, pitch?, class_name?}]
        }
    """
    cell_id = v1.get("cell_id", "")
    v2_detections = [_init_detection_v2(d) for d in detections]
    by_id = {d["id"]: d for d in v2_detections}

    for v in v1.get("verdicts", []):
        did = v.get("detection_id")
        if did not in by_id:
            continue
        v2 = by_id[did]
        verdict = (v.get("verdict") or "").strip()
        actual = (v.get("actual_label") or "").strip()
        if verdict == "TP":
            v2["verdict"] = "TP"
        elif verdict == "FP" and actual:
            v2["verdict"] = "WRONG_CATEGORY"
            v2["human_corrected_class"] = actual
            v2["human_corrected_category"] = _class_to_category(actual)
        elif verdict == "FP":
            v2["verdict"] = "FP"
        elif verdict == "unsure":
            v2["verdict"] = "unsure"

    added = []
    for i, fn in enumerate(v1.get("fn_noteheads", [])):
        x = int(fn.get("x_canonical") or 0)
        y = int(fn.get("y_canonical") or 0)
        cls = (fn.get("class_name") or "noteheadBlackOnLine").strip()
        added.append(
            {
                "id": f"H{i}",
                "human_class": cls,
                "human_category": _class_to_category(cls),
                # Schema v1 didn't store FN bbox — synthesize a small box
                # centered on the captured point; the labeler can fix it
                # in the UI by clicking Fix-bbox on the added item.
                "bbox": {"x": max(0, x - 14), "y": max(0, y - 16), "w": 28, "h": 32},
                "notes": "(migrated from schema_v1 FN — bbox is synthesized)",
            }
        )

    return {
        "cell_id": cell_id,
        "schema_version": 2,
        "labeled_at_utc": None,
        "detections": v2_detections,
        "added_detections": added,
        # v1 predates pass mode — a migrated file has been inspected by no pass.
        "inspected_passes": [],
    }


def _load_or_init_verdict(
    bench: Bench, cell_id: str, detections: list[dict]
) -> tuple[dict, str]:
    """Load the verdict file for a cell.

    Returns (state, source) where source is one of:
        "v2"      — loaded directly from a schema_v2 .verdict.json
        "v1"      — loaded from a schema_v1 file and migrated in memory
        "new"     — no verdict file existed, fresh state generated
    """
    vp = bench.verdicts_dir / f"{cell_id}.verdict.json"
    if vp.exists():
        try:
            raw = json.loads(vp.read_text())
        except json.JSONDecodeError as e:
            raise HTTPException(
                500, detail=f"corrupt verdict file {vp.name}: {e}"
            )
        if raw.get("schema_version") == 2:
            return _reconcile_with_detections(raw, detections), "v2"
        return _migrate_v1_to_v2(raw, detections), "v1"
    return _empty_v2_state(cell_id, detections), "new"


def _reconcile_with_detections(state: dict, detections: list[dict]) -> dict:
    """Fold the newest detection set into a saved verdict state.

    If detections were regenerated since the verdict was last saved,
    bbox/confidence/predicted_class may have shifted. We preserve any
    human decision keyed by detection id; new detection ids start
    pending; ids no longer in the detection set are dropped.
    """
    new_dets: list[dict] = []
    keep: dict[str, dict] = {d["id"]: d for d in state.get("detections", [])}
    for d in detections:
        prior = keep.get(d["id"])
        fresh = _init_detection_v2(d)
        if prior is not None:
            fresh["verdict"] = prior.get("verdict")
            fresh["human_corrected_class"] = prior.get("human_corrected_class")
            fresh["human_corrected_category"] = prior.get("human_corrected_category")
            fresh["human_bbox"] = prior.get("human_bbox")
            fresh["notes"] = prior.get("notes", "")
        new_dets.append(fresh)
    state["detections"] = new_dets
    state.setdefault("added_detections", [])
    # Pass-coverage provenance is keyed on nothing but the cell, so it
    # survives a detection regeneration untouched — the same reason drawn
    # boxes do. A file saved before pass mode existed simply has none.
    state.setdefault("inspected_passes", [])
    state["schema_version"] = 2
    state["cell_id"] = state.get("cell_id") or ""
    return state


def _validate_v2(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise HTTPException(400, detail="payload must be a JSON object")
    out = {
        "cell_id": str(payload.get("cell_id") or "").strip(),
        "schema_version": 2,
        "labeled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "detections": [],
        "added_detections": [],
        "inspected_passes": _coerce_pass_list(payload.get("inspected_passes")),
    }
    if not out["cell_id"]:
        raise HTTPException(400, detail="cell_id is required")
    for d in payload.get("detections") or []:
        if not isinstance(d, dict):
            continue
        verdict = d.get("verdict")
        if verdict is not None and verdict not in _VALID_VERDICTS:
            raise HTTPException(400, detail=f"invalid verdict: {verdict!r}")
        out["detections"].append(
            {
                "id": str(d.get("id") or ""),
                "verdict": verdict,
                "model_predicted_class": d.get("model_predicted_class") or "",
                "human_corrected_class": d.get("human_corrected_class"),
                "model_predicted_category": d.get("model_predicted_category") or "",
                "human_corrected_category": d.get("human_corrected_category"),
                "model_bbox": _coerce_bbox(d.get("model_bbox")),
                "human_bbox": _coerce_bbox(d.get("human_bbox"), allow_none=True),
                "confidence": float(d.get("confidence") or 0.0),
                "notes": str(d.get("notes") or ""),
            }
        )
    for h in payload.get("added_detections") or []:
        if not isinstance(h, dict):
            continue
        out["added_detections"].append(
            {
                "id": str(h.get("id") or ""),
                "human_class": str(h.get("human_class") or ""),
                "human_category": str(h.get("human_category") or ""),
                "bbox": _coerce_bbox(h.get("bbox")),
                "notes": str(h.get("notes") or ""),
            }
        )
    return out


def _coerce_pass_list(v: Any) -> list[str]:
    """Normalize inspected_passes: strings, trimmed, de-duplicated in order.

    ``_validate_v2`` drops any key it does not name, so this field only
    persists because it is coerced here — the same thing that keeps a stray
    key out is what would have silently dropped this one, which is why it is
    threaded rather than passed through.
    """
    if not isinstance(v, list):
        return []
    out: list[str] = []
    for item in v:
        if isinstance(item, str) and item.strip() and item not in out:
            out.append(item)
    return out


def _coerce_bbox(b: Any, allow_none: bool = False) -> dict | None:
    if b is None:
        if allow_none:
            return None
        return {"x": 0, "y": 0, "w": 0, "h": 0}
    return {
        "x": int(b.get("x", 0)),
        "y": int(b.get("y", 0)),
        "w": int(b.get("w", 0)),
        "h": int(b.get("h", 0)),
    }


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------


def _crop_cell(
    cell_png: Path, x: int, y: int, w: int, h: int, pad: int = 12
) -> bytes:
    with Image.open(cell_png) as img:
        iw, ih = img.size
        left = max(0, x - pad)
        top = max(0, y - pad)
        right = min(iw, x + w + pad)
        bottom = min(ih, y + h + pad)
        if right <= left or bottom <= top:
            crop = Image.new("RGB", (16, 16), (255, 255, 255))
        else:
            crop = img.crop((left, top, right, bottom)).convert("RGB")
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Cell status (for the index page)
# ---------------------------------------------------------------------------


def _summarize_cell_status(bench: Bench, cell_id: str, vp: Path) -> dict:
    n_detections = 0
    detections_path = bench.detections_dir / f"{cell_id}.json"
    if detections_path.exists():
        try:
            data = json.loads(detections_path.read_text())
            n_detections = len(data.get("detections", []))
        except json.JSONDecodeError:
            pass
    if not vp.exists():
        return {
            "n_detections": n_detections,
            "n_decided": 0,
            "n_pending": n_detections,
            "n_added": 0,
            "has_verdict": False,
            "schema_version": None,
            "inspected_passes": [],
        }
    try:
        v = json.loads(vp.read_text())
    except json.JSONDecodeError:
        return {
            "n_detections": n_detections,
            "n_decided": 0,
            "n_pending": n_detections,
            "n_added": 0,
            "has_verdict": True,
            "schema_version": "corrupt",
            "inspected_passes": [],
        }
    sv = v.get("schema_version", 1)
    if sv == 2:
        dets = v.get("detections", [])
        n_decided = sum(1 for d in dets if d.get("verdict"))
        return {
            "n_detections": len(dets),
            "n_decided": n_decided,
            "n_pending": max(0, len(dets) - n_decided),
            "n_added": len(v.get("added_detections", [])),
            "has_verdict": True,
            "schema_version": 2,
            "inspected_passes": _coerce_pass_list(v.get("inspected_passes")),
        }
    vds = v.get("verdicts", [])
    n_decided = sum(1 for x in vds if (x.get("verdict") or "").strip())
    return {
        "n_detections": len(vds),
        "n_decided": n_decided,
        "n_pending": max(0, len(vds) - n_decided),
        "n_added": len(v.get("fn_noteheads", [])),
        "has_verdict": True,
        "schema_version": 1,
        "inspected_passes": [],
    }


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(bench: Bench | Path) -> FastAPI:
    if isinstance(bench, Path):
        bench = Bench(root=bench)
    bench.verdicts_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(bench)
    classes, categories = _load_class_catalog()
    by_class_name = {c["name"]: c for c in classes}
    pass_config = _load_batch_config(bench, set(by_class_name))
    if pass_config is not None:
        print(
            f"[server] pass mode: {pass_config.pass_name!r} — "
            f"{len(pass_config.slots)} slot(s): "
            + ", ".join(s.label for s in pass_config.slots)
        )
        for w in pass_config.warnings:
            print(f"[server] WARN: {_BATCH_CONFIG_NAME}: {w}")
    by_cat_order = [c for c in _CATEGORY_ORDER if categories.get(c)]
    for c in categories:
        if c not in by_cat_order and categories[c]:
            by_cat_order.append(c)

    app = FastAPI(
        title="ReEngrave OMR labeler",
        description="Local single-user labeling UI for schema_v2 OMR verdicts.",
    )

    app.mount(
        "/static",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def index_page() -> HTMLResponse:
        return HTMLResponse(_read_static("index.html"))

    @app.get("/cells/{cell_id}", response_class=HTMLResponse)
    def cell_page(cell_id: str) -> HTMLResponse:
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        return HTMLResponse(_read_static("cell.html"))

    def _class_payload(name: str) -> dict:
        cls = by_class_name.get(name, {"name": name, "category": "structural",
                                       "has_archetype": False})
        return {
            "name": name,
            "category": cls["category"],
            "has_archetype": cls["has_archetype"],
            "archetype_url": (
                f"/static/archetypes/{name}.png" if cls["has_archetype"] else None
            ),
        }

    def _slot_payload(slot: PassSlot) -> dict:
        return {
            "index": slot.index,
            "label": slot.label,
            "kind": slot.kind,
            "classes": [_class_payload(n) for n in slot.class_names],
            "by_position": {
                pos: _class_payload(name)
                for pos, name in slot.by_position.items()
                if pos
            },
            "click_box": slot.click_box,
        }

    @app.get("/api/bench")
    def api_bench() -> dict:
        return {
            "root": str(bench.root),
            "n_cells": len(manifest.ordered_ids),
            "n_classes": len(classes),
            "categories": by_cat_order,
            "pass_name": pass_config.pass_name if pass_config else None,
        }

    @app.get("/api/pass")
    def api_pass() -> dict:
        """The restricted palette for this batch, or ``active: false``.

        This is where the palette comes from in pass mode. ``/api/classes``
        deliberately keeps serving the FULL catalog: the UI still needs every
        class by name (to render a model detection's own class, and for the
        explicit escape hatch to the full picker).
        """
        if pass_config is None:
            return {"active": False, "slots": []}
        return {
            "active": True,
            "pass_name": pass_config.pass_name,
            "note": pass_config.note,
            "single": pass_config.single,
            "slots": [_slot_payload(s) for s in pass_config.slots],
            "warnings": pass_config.warnings,
        }

    @app.get("/api/cells")
    def api_cells() -> list[dict]:
        out = []
        for cid in manifest.ordered_ids:
            entry = manifest.by_id[cid]
            vp = bench.verdicts_dir / f"{cid}.verdict.json"
            status = _summarize_cell_status(bench, cid, vp)
            pre = _load_prefill(bench, cid)
            out.append(
                {
                    "cell_id": cid,
                    "source_tag": entry.get("source_tag", ""),
                    "page": entry.get("page"),
                    "system_index": entry.get("system_index"),
                    "staff_index": entry.get("staff_index"),
                    "measure_index": entry.get("measure_index"),
                    "canonical_w": entry.get("cell_canonical_w"),
                    "canonical_h": entry.get("cell_canonical_h"),
                    "n_detections": status["n_detections"],
                    "n_decided": status["n_decided"],
                    "n_pending": status["n_pending"],
                    "n_added": status["n_added"],
                    "has_verdict": status["has_verdict"],
                    "schema_version": status["schema_version"],
                    "inspected_passes": status["inspected_passes"],
                    # Queue mode: how much the reference left for the human.
                    "prefill_status": pre["status"] if pre else None,
                    "n_hints": len(pre["hints"]) if pre else 0,
                    "n_hints_missing": (sum(1 for h in pre["hints"] if h.get("kind") == "missing")
                                        if pre else 0),
                }
            )
        return out

    @app.get("/api/classes")
    def api_classes() -> list[dict]:
        out = []
        for c in classes:
            archetype_url = (
                f"/static/archetypes/{c['name']}.png" if c["has_archetype"] else None
            )
            out.append({**c, "archetype_url": archetype_url})
        return out

    @app.get("/api/categories")
    def api_categories() -> dict:
        return {
            "order": by_cat_order,
            "members": {c: categories.get(c, []) for c in by_cat_order},
        }

    @app.get("/api/cell/{cell_id}")
    def api_cell(cell_id: str) -> dict:
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        idx = manifest.ordered_ids.index(cell_id)
        prev_id = manifest.ordered_ids[idx - 1] if idx > 0 else None
        next_id = (
            manifest.ordered_ids[idx + 1]
            if idx + 1 < len(manifest.ordered_ids)
            else None
        )
        entry = manifest.by_id[cell_id]

        # System-level neighbors: find the cell ID of the first/last cell
        # in the prev/next (system_index, staff_index) on the same source/page.
        # Also collect all cells on the same page for the topbar strip.
        cur_src = entry.get("source_tag", "")
        cur_page = entry.get("page")
        cur_sys = entry.get("system_index")
        cur_staff = entry.get("staff_index")
        cur_meas = entry.get("measure_index")

        same_page_cells = []
        same_system_cells = []
        same_staff_cells = []
        all_systems_on_page = []  # list of (system_index, staff_index) tuples in order seen
        for cid in manifest.ordered_ids:
            e = manifest.by_id[cid]
            if e.get("source_tag") != cur_src or e.get("page") != cur_page:
                continue
            same_page_cells.append({
                "cell_id": cid,
                "system_index": e.get("system_index"),
                "staff_index": e.get("staff_index"),
                "measure_index": e.get("measure_index"),
                "is_current": cid == cell_id,
            })
            sys_staff = (e.get("system_index"), e.get("staff_index"))
            if sys_staff not in all_systems_on_page:
                all_systems_on_page.append(sys_staff)
            if sys_staff == (cur_sys, cur_staff):
                same_staff_cells.append(cid)
            if e.get("system_index") == cur_sys:
                same_system_cells.append(cid)

        # Find prev/next (system, staff) groups within the same page
        try:
            cur_group_idx = all_systems_on_page.index((cur_sys, cur_staff))
        except ValueError:
            cur_group_idx = -1

        def _first_cell_in_group(target_sys: int, target_staff: int) -> str | None:
            for cid in manifest.ordered_ids:
                e = manifest.by_id[cid]
                if (e.get("source_tag") == cur_src and e.get("page") == cur_page
                        and e.get("system_index") == target_sys
                        and e.get("staff_index") == target_staff):
                    return cid
            return None

        prev_staff_id = None
        next_staff_id = None
        if cur_group_idx > 0:
            ps, pst = all_systems_on_page[cur_group_idx - 1]
            prev_staff_id = _first_cell_in_group(ps, pst)
        if cur_group_idx >= 0 and cur_group_idx + 1 < len(all_systems_on_page):
            ns, nst = all_systems_on_page[cur_group_idx + 1]
            next_staff_id = _first_cell_in_group(ns, nst)

        # System-level (ignoring staff). Find the prev/next distinct
        # system_index on the same page.
        unique_systems = []
        for s, _ in all_systems_on_page:
            if s not in unique_systems:
                unique_systems.append(s)
        prev_system_id = None
        next_system_id = None
        try:
            cs_idx = unique_systems.index(cur_sys)
        except ValueError:
            cs_idx = -1
        if cs_idx > 0:
            target = unique_systems[cs_idx - 1]
            # First cell whose system_index == target
            for cid in manifest.ordered_ids:
                e = manifest.by_id[cid]
                if (e.get("source_tag") == cur_src and e.get("page") == cur_page
                        and e.get("system_index") == target):
                    prev_system_id = cid
                    break
        if cs_idx >= 0 and cs_idx + 1 < len(unique_systems):
            target = unique_systems[cs_idx + 1]
            for cid in manifest.ordered_ids:
                e = manifest.by_id[cid]
                if (e.get("source_tag") == cur_src and e.get("page") == cur_page
                        and e.get("system_index") == target):
                    next_system_id = cid
                    break

        return {
            "cell": {
                "cell_id": cell_id,
                "source_tag": cur_src,
                "page": cur_page,
                "system_index": cur_sys,
                "staff_index": cur_staff,
                "measure_index": cur_meas,
                "canonical_w": entry.get("cell_canonical_w"),
                "canonical_h": entry.get("cell_canonical_h"),
                "staff_line_ys": entry.get("staff_line_ys_canonical", []),
                "clef": entry.get("clef", ""),
            },
            "prev_id": prev_id,
            "next_id": next_id,
            "prev_staff_id": prev_staff_id,    # prev (system,staff) group on same page
            "next_staff_id": next_staff_id,    # next (system,staff) group on same page
            "prev_system_id": prev_system_id,  # prev distinct system on same page
            "next_system_id": next_system_id,  # next distinct system on same page
            "page_cells": same_page_cells,     # for the topbar strip
            "index": idx,
            "total": len(manifest.ordered_ids),
            # Reference-driven pre-fill, when `mxl_verdicts` has run on this
            # batch. `hints` draw as ghost markers; nothing here is a label.
            "prefill": _load_prefill(bench, cell_id),
        }

    @app.get("/api/cell/{cell_id}/verdict")
    def api_get_verdict(cell_id: str) -> dict:
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        detections = _load_detections(bench, cell_id)
        state, source = _load_or_init_verdict(bench, cell_id, detections)
        return {"state": state, "source": source}

    @app.post("/api/cell/{cell_id}/verdict")
    async def api_post_verdict(cell_id: str, request: Request) -> dict:
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        payload = await request.json()
        if payload.get("cell_id") != cell_id:
            raise HTTPException(400, detail="cell_id in payload must match URL")
        normalized = _validate_v2(payload)
        out = bench.verdicts_dir / f"{cell_id}.verdict.json"
        out.write_text(json.dumps(normalized, indent=2))
        return {"ok": True, "saved_at": normalized["labeled_at_utc"]}

    @app.get("/api/cell/{cell_id}/snap")
    def api_cell_snap(cell_id: str, x: float, y: float, slot: int = 0) -> dict:
        """Resolve a click (or a moved box's centre) against the staff grid.

        Returns the class the geometry chooses for the pass slot, and — when
        the slot declares a click box — the box to place. One click, one
        label. The arithmetic lives here rather than in the browser so it is
        the tested code that runs, not a second copy of it.
        """
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        if pass_config is None:
            raise HTTPException(409, detail="no pass mode configured for this bench")
        if not 0 <= slot < len(pass_config.slots):
            raise HTTPException(404, detail=f"no slot {slot}")
        target = pass_config.slots[slot]
        entry = manifest.by_id[cell_id]
        rungs = _ledger_rungs_for_click(bench, manifest, entry, cell_id, x)
        snapped = snap_to_staff(
            entry.get("staff_line_ys_canonical", []), y, ledger_rungs=rungs
        )
        if snapped is None:
            # No staff geometry on this cell — abstain rather than guess a
            # variant. The UI falls back to the picker.
            return {
                "available": False,
                "reason": "cell has no staff_line_ys_canonical",
                "slot": slot,
            }
        class_name = target.class_for(snapped["position"])
        bbox = None
        if target.click_box is not None:
            bbox = _clamp_bbox(
                click_box_px(target.click_box, snapped["spacing"], x,
                             snapped["snapped_y"]),
                entry.get("cell_canonical_w"),
                entry.get("cell_canonical_h"),
            )
        return {
            "available": True,
            "slot": slot,
            "class": _class_payload(class_name),
            "bbox": bbox,
            **snapped,
        }

    @app.get("/api/cell/{cell_id}/image")
    def api_cell_image(cell_id: str) -> FileResponse:
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        png = _resolve_cell_png(bench, manifest, cell_id)
        if png is None:
            raise HTTPException(404, detail=f"missing cell PNG for {cell_id}")
        return FileResponse(str(png), media_type="image/png")

    @app.get("/api/cell/{cell_id}/crop")
    def api_cell_crop(
        cell_id: str, x: int, y: int, w: int, h: int, pad: int = 12
    ) -> Response:
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        png = _resolve_cell_png(bench, manifest, cell_id)
        if png is None:
            raise HTTPException(404, detail=f"missing cell PNG for {cell_id}")
        data = _crop_cell(png, x, y, w, h, pad=pad)
        return Response(content=data, media_type="image/png")

    def _render_or_cache_page(cell_id: str) -> tuple[Path, str]:
        """Helper: ensure the source PDF page for this cell is rendered
        to disk and return (path, pdf_stem). Raises HTTPException on error."""
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        entry = manifest.by_id[cell_id]
        pdf_path = entry.get("pdf")
        page_num = entry.get("page")
        if not pdf_path or page_num is None:
            raise HTTPException(
                404,
                detail=f"cell {cell_id} has no pdf+page in manifest"
            )
        # cells.json `page` is 0-indexed, pdf2image is 1-indexed.
        pdf_page_1based = int(page_num) + 1
        cache_dir = bench.root / "page-thumbnails"
        cache_dir.mkdir(parents=True, exist_ok=True)
        pdf_stem = Path(pdf_path).stem
        cache_path = cache_dir / f"{pdf_stem}_p{pdf_page_1based}.png"
        if not cache_path.exists():
            try:
                from pdf2image import convert_from_path  # lazy
            except ImportError:
                raise HTTPException(
                    500,
                    detail="pdf2image not installed — pip install pdf2image"
                )
            pdf_p = Path(pdf_path)
            if not pdf_p.exists():
                raise HTTPException(
                    404, detail=f"source PDF not found at {pdf_path}"
                )
            pages = convert_from_path(
                str(pdf_p),
                dpi=150,
                first_page=pdf_page_1based,
                last_page=pdf_page_1based,
            )
            if not pages:
                raise HTTPException(500, detail="pdf2image returned no pages")
            pages[0].save(str(cache_path), "PNG")
        return cache_path, pdf_stem

    # Source-page DPI used during cell extraction (matches
    # tools/omr/annotate/select_cells_orchestral.py default).
    _SOURCE_DPI = 600
    _PAGE_RENDER_DPI = 150  # what _render_or_cache_page uses

    def _find_cell_bbox_on_page(cell_id: str, page_png: Path) -> dict | None:
        """Locate the cell's bbox on the rendered page by re-running the
        same phase-1 staff/measure detection the cell extractor used,
        finding the matching (system_index, staff_index, measure_index)
        cell, and converting its bbox_page_px from 600 DPI to the
        150 DPI page render space.

        Returns {x, y, w, h, n_cells_on_page} or None if not found.
        Cached per-cell as a JSON sidecar. The PAGE-level phase-1 result
        is cached too so the 2nd cell on the same page is fast."""
        if cell_id not in manifest.by_id:
            return None
        entry = manifest.by_id[cell_id]
        cache_dir = bench.root / "page-thumbnails"
        bbox_cache = cache_dir / f"{cell_id}.bbox.json"
        if bbox_cache.exists():
            try:
                data = json.loads(bbox_cache.read_text())
                # An older negative cache (no x) means we tried and failed.
                # Don't retry: caller will fall back to bare page.
                return data
            except Exception:
                pass

        pdf_path = entry.get("pdf")
        page_idx = entry.get("page")
        sys_idx = entry.get("system_index")
        staff_idx = entry.get("staff_index")
        meas_idx = entry.get("measure_index")
        if any(x is None for x in (pdf_path, page_idx, sys_idx, staff_idx, meas_idx)):
            return None

        # Run phase-1 on the page (cache results per page so multiple cells
        # on the same page don't repeat the work).
        page_cells = _phase1_cache_for_page(Path(pdf_path), int(page_idx))
        if page_cells is None:
            bbox_cache.write_text(json.dumps({"score": 0, "reason": "phase1-failed"}))
            return None

        match = None
        for c in page_cells:
            if (c["system_index"] == sys_idx
                    and c["staff_index"] == staff_idx
                    and c["measure_index"] == meas_idx):
                match = c
                break
        if match is None:
            bbox_cache.write_text(json.dumps({"score": 0, "reason": "no-cell-match"}))
            return None

        # Convert from 600 DPI page-px to 150 DPI page-render-px.
        scale = _PAGE_RENDER_DPI / _SOURCE_DPI
        x0, y0, x1, y1 = match["bbox_page_px"]
        bbox = {
            "x": int(round(x0 * scale)),
            "y": int(round(y0 * scale)),
            "w": int(round((x1 - x0) * scale)),
            "h": int(round((y1 - y0) * scale)),
            "score": 1.0,  # exact (derivation, not heuristic match)
            "source": "phase1",
        }
        bbox_cache.write_text(json.dumps(bbox))
        return bbox

    # Per-page phase-1 cache. Each entry: list of dicts with system_index,
    # staff_index, measure_index, bbox_page_px (at _SOURCE_DPI).
    _phase1_cache: dict[tuple[str, int], list[dict] | None] = {}

    def _phase1_cache_for_page(pdf_path: Path, page_idx: int) -> list[dict] | None:
        key = (str(pdf_path.resolve()), int(page_idx))
        if key in _phase1_cache:
            return _phase1_cache[key]
        cache_dir = bench.root / "page-thumbnails"
        disk_cache = cache_dir / f"phase1_{pdf_path.stem}_p{page_idx}.json"
        if disk_cache.exists():
            try:
                cached = json.loads(disk_cache.read_text())
                _phase1_cache[key] = cached
                return cached
            except Exception:
                pass
        # Run phase-1 detection on the page at SOURCE_DPI.
        try:
            from ..preprocessing import render_page
            from ..staff_detector import detect_staves
            from .. import measure_extractor as _me
        except ImportError:
            _phase1_cache[key] = None
            return None
        try:
            img = render_page(pdf_path, int(page_idx), dpi=_SOURCE_DPI)
            pws = detect_staves(img)
            pws = _me.detect_barlines(pws)
            cells = _me.extract_measures(pws)
        except Exception as exc:
            print(f"[server] WARN: phase1 failed on {pdf_path.name} p{page_idx}: {exc!r}")
            _phase1_cache[key] = None
            disk_cache.write_text(json.dumps([]))
            return None
        out = []
        for c in cells:
            out.append({
                "system_index": int(c.system_index),
                "staff_index": int(c.staff_index),
                "measure_index": int(c.measure_index),
                "bbox_page_px": list(c.bbox_page_px),
            })
        disk_cache.parent.mkdir(parents=True, exist_ok=True)
        disk_cache.write_text(json.dumps(out))
        _phase1_cache[key] = out
        return out

    @app.get("/api/cell/{cell_id}/page")
    def api_cell_page(cell_id: str, highlight: bool = True) -> Response:
        """Render the source PDF page that contains this cell as a PNG.

        If `highlight=true` (default) and the cell crop can be located on
        the page via template matching, draws a yellow rectangle around it
        so the labeler can see the cell's musical context AT a glance.
        Pass `?highlight=false` to get the bare page.
        """
        cache_path, _ = _render_or_cache_page(cell_id)
        if not highlight:
            return FileResponse(str(cache_path), media_type="image/png")
        bbox = _find_cell_bbox_on_page(cell_id, cache_path)
        if not bbox or "x" not in bbox:
            # No confident match — just serve the bare page.
            return FileResponse(str(cache_path), media_type="image/png")
        # Draw the highlight using PIL (lighter weight than re-encoding via cv2)
        try:
            from PIL import Image, ImageDraw  # type: ignore
        except ImportError:
            return FileResponse(str(cache_path), media_type="image/png")
        img = Image.open(cache_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        # Pad the box slightly so the rectangle frame doesn't crop the cell.
        pad = 4
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(img.width - 1, x + w + pad), min(img.height - 1, y + h + pad)
        # Yellow rectangle, 3 px thick, with a translucent inner fill for
        # extra visibility against busy orchestral scores.
        draw.rectangle((x0, y0, x1, y1), outline=(255, 215, 0), width=4)
        # Subtle inner shadow with a thinner inset rectangle.
        draw.rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), outline=(255, 235, 100), width=1)
        import io
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return Response(content=buf.getvalue(), media_type="image/png")

    @app.get("/api/health")
    def api_health() -> dict:
        return {
            "ok": True,
            "bench": str(bench.root),
            "n_cells": len(manifest.ordered_ids),
        }

    return app


def _resolve_cell_png(
    bench: Bench, manifest: ManifestCache, cell_id: str
) -> Path | None:
    png = bench.cells_dir / f"{cell_id}.png"
    if png.exists():
        return png
    # Fall back to the manifest's path — the cells dir is conventional but
    # the manifest entry is authoritative.
    raw = manifest.by_id[cell_id].get("cell_png_path", "")
    if not raw:
        return None
    alt = Path(raw)
    if not alt.is_absolute():
        alt = (bench.root.parent.parent / alt).resolve()
    return alt if alt.exists() else None


# Grayscale cell images for the snap endpoint's ledger-rung read. Tiny cache:
# a labeller works one cell at a time, and a 2048-wide crop decodes in ~10ms.
_GRAY_CACHE: dict[str, tuple[float, Any]] = {}


def _gray_cell_image(png: Path):
    key = str(png)
    mtime = png.stat().st_mtime
    hit = _GRAY_CACHE.get(key)
    if hit is not None and hit[0] == mtime:
        return hit[1]
    import numpy as np

    with Image.open(png) as img:
        arr = np.asarray(img.convert("L"), dtype=np.uint8)
    if len(_GRAY_CACHE) >= 8:
        _GRAY_CACHE.clear()
    _GRAY_CACHE[key] = (mtime, arr)
    return arr


def _ledger_rungs_for_click(
    bench: Bench, manifest: ManifestCache, entry: dict, cell_id: str, x: float
) -> dict | None:
    """Measured ledger rungs at the clicked column, for snap_to_staff.

    Every failure is an abstention (None -> constant-pitch extrapolation, the
    behaviour the snap always had): missing numpy, missing image, or an image
    whose size disagrees with the manifest's canonical frame — a stale or
    re-rendered PNG would put the rungs in the wrong coordinate space, which
    is worse than no rungs. An unexpected error additionally says so on
    stderr, because a click must never 500 over an enrichment.
    """
    try:
        from tools.omr.annotate.ledger_grid import measure_ledger_rungs
    except ImportError:
        return None
    try:
        png = _resolve_cell_png(bench, manifest, cell_id)
        if png is None:
            return None
        img = _gray_cell_image(png)
        cw = entry.get("cell_canonical_w")
        ch = entry.get("cell_canonical_h")
        if cw and ch and (img.shape[1] != cw or img.shape[0] != ch):
            return None
        return measure_ledger_rungs(
            img, entry.get("staff_line_ys_canonical") or [], x
        )
    except Exception as e:  # noqa: BLE001 — enrichment, never fail the click
        print(
            f"[annotate] ledger rung read failed for {cell_id}: {e!r}",
            file=sys.stderr,
        )
        return None


# Templates are loaded from disk every request during local dev so you
# can edit cell.html / cell.js without restarting uvicorn. (uvicorn's
# --reload kicks the server on .py changes but not on template-only
# changes.)
def _read_static(name: str) -> str:
    return (_STATIC_DIR / name).read_text()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _derive_bench(args: argparse.Namespace) -> Bench:
    if args.bench_dir:
        return Bench(root=Path(args.bench_dir).resolve())
    if args.verdicts_dir:
        return Bench(root=Path(args.verdicts_dir).resolve().parent)
    raise SystemExit("must pass --bench-dir or --verdicts-dir")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--bench-dir",
        type=Path,
        help="Benchmark directory (must contain cells.json, cells/, detections/).",
    )
    ap.add_argument(
        "--verdicts-dir",
        type=Path,
        help=(
            "Verdicts directory. If supplied without --bench-dir, "
            "the bench is its parent."
        ),
    )
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5050)
    ap.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (for editing server.py).",
    )
    args = ap.parse_args()

    bench = _derive_bench(args)
    print(f"[server] bench: {bench.root}")
    if not bench.manifest.exists():
        print(f"[server] WARN: manifest missing: {bench.manifest}")
    if not bench.cells_dir.exists():
        print(f"[server] WARN: cells dir missing: {bench.cells_dir}")
    if not bench.detections_dir.exists():
        print(f"[server] WARN: detections dir missing: {bench.detections_dir}")

    try:
        app = create_app(bench)
    except ValueError as e:
        # Almost always a hand-edited batch_config.json. Say what is wrong
        # rather than serving the full picker to someone who asked for a pass.
        raise SystemExit(f"[server] ERROR: {e}")
    url = f"http://{args.host}:{args.port}"
    print(f"[server] listening on {url}")
    print(f"[server] open {url}/ to start labeling")
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
