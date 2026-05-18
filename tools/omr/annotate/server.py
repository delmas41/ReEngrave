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
"""

from __future__ import annotations

import argparse
import io
import json
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
_CLASSES_JSON = _HERE.parent / "training" / "data" / "deepscoresv2_208_classes.json"


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
    ("barline", "structural"),
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
    "structural",
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
            f"missing class list at {_CLASSES_JSON} — see "
            "tools/omr/training/data/deepscoresv2_208_classes.json"
        )
    raw = json.loads(_CLASSES_JSON.read_text())
    unique = list(dict.fromkeys(raw))
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

    @app.get("/api/bench")
    def api_bench() -> dict:
        return {
            "root": str(bench.root),
            "n_cells": len(manifest.ordered_ids),
            "n_classes": len(classes),
            "categories": by_cat_order,
        }

    @app.get("/api/cells")
    def api_cells() -> list[dict]:
        out = []
        for cid in manifest.ordered_ids:
            entry = manifest.by_id[cid]
            vp = bench.verdicts_dir / f"{cid}.verdict.json"
            status = _summarize_cell_status(bench, cid, vp)
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

    @app.get("/api/cell/{cell_id}/page")
    def api_cell_page(cell_id: str) -> FileResponse:
        """Render the source PDF page that contains this cell as a PNG and
        return it (cached). Lets the labeler see the full musical context
        surrounding the cropped measure-cell."""
        if cell_id not in manifest.by_id:
            raise HTTPException(404, detail=f"unknown cell {cell_id}")
        entry = manifest.by_id[cell_id]
        pdf_path = entry.get("pdf")
        page_num = entry.get("page")
        if not pdf_path or not page_num:
            raise HTTPException(
                404,
                detail=f"cell {cell_id} has no pdf+page in manifest"
            )
        # Cache rendered pages under benchmarks/.../page-thumbnails/
        cache_dir = bench.root / "page-thumbnails"
        cache_dir.mkdir(parents=True, exist_ok=True)
        # PDF path → safe filename
        pdf_stem = Path(pdf_path).stem
        cache_path = cache_dir / f"{pdf_stem}_p{page_num}.png"
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
                dpi=150,  # readable but not huge — keep load fast
                first_page=int(page_num),
                last_page=int(page_num),
            )
            if not pages:
                raise HTTPException(500, detail="pdf2image returned no pages")
            pages[0].save(str(cache_path), "PNG")
        return FileResponse(str(cache_path), media_type="image/png")

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

    app = create_app(bench)
    url = f"http://{args.host}:{args.port}"
    print(f"[server] listening on {url}")
    print(f"[server] open {url}/ to start labeling")
    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
