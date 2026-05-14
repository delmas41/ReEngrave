"""Local Flask app for filling in Phase 2.5 verdict files via a web UI.

Usage:
    python3 -m tools.omr.annotate.server \\
        [--bench-dir benchmarks/omr-phase2.5] \\
        [--host 127.0.0.1] [--port 5050]

The app reads cells.json + detections/*.json + overlays/*.png from
`--bench-dir`, and writes verdicts as `verdicts/<cell_id>.verdict.json`
(separate from the legacy markdown files, which it can also read for
pre-fill).

UI overview:
    GET /                          → cell list with status badges
    GET /cells/<cell_id>           → cell detail (overlay + radio buttons)
    GET /cells/<cell_id>/overlay.png
    GET /cells/<cell_id>/verdict.json  → current state (json > md > empty)
    POST /cells/<cell_id>/verdict.json → writes .verdict.json
    GET /score                     → runs the scorer and renders the report
"""

from __future__ import annotations

import argparse
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    request,
    send_file,
    url_for,
)

from .score import parse_verdict_markdown, run_scorer


# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------


@dataclass
class Bench:
    """Bundle of paths for one benchmark directory."""

    root: Path  # benchmarks/omr-phase2.5

    @property
    def manifest_path(self) -> Path:
        return self.root / "cells.json"

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
    def results_dir(self) -> Path:
        return self.root / "results"

    def load_manifest(self) -> list[dict]:
        if not self.manifest_path.exists():
            return []
        return json.loads(self.manifest_path.read_text())

    def detection_path(self, cell_id: str) -> Path:
        return self.detections_dir / f"{cell_id}.json"

    def overlay_path(self, cell_id: str) -> Path:
        return self.overlays_dir / f"{cell_id}.png"

    def verdict_json_path(self, cell_id: str) -> Path:
        return self.verdicts_dir / f"{cell_id}.verdict.json"

    def verdict_md_path(self, cell_id: str) -> Path:
        return self.verdicts_dir / f"{cell_id}.md"


def _load_detections(bench: Bench, cell_id: str) -> list[dict]:
    p = bench.detection_path(cell_id)
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    return data.get("detections", [])


def _empty_verdict_state(cell_id: str, detections: list[dict]) -> dict:
    return {
        "cell_id": cell_id,
        "verdicts": [
            {
                "detection_id": d["id"],
                "smufl_name": d["smufl_name"],
                "verdict": "",
            }
            for d in detections
        ],
        "fn_noteheads": [],
    }


def _state_from_markdown(
    cell_id: str, md_text: str, detections: list[dict]
) -> dict:
    """Bootstrap a verdict-state dict from an existing pre-filled .md file."""
    parsed = parse_verdict_markdown(md_text, cell_id=cell_id)
    by_id_md = {d.id: d for d in parsed.detections}
    verdicts = []
    for d in detections:
        md_det = by_id_md.get(d["id"])
        v_label = ""
        if md_det is not None and md_det.verdict:
            cls = md_det.classification
            if cls == "tp":
                v_label = "TP"
            elif cls == "fp":
                v_label = "FP"
            elif cls == "wrong_pitch":
                # Treat WRONG_PITCH as TP + wrong_pitch correction.
                v_label = "TP"
            elif cls == "pending":
                v_label = "unsure" if md_det.verdict else ""
        row: dict[str, Any] = {
            "detection_id": d["id"],
            "smufl_name": d["smufl_name"],
            "verdict": v_label,
        }
        wp = parsed.wrong_pitch_corrections.get(d["id"])
        if wp:
            row["wrong_pitch"] = wp
        verdicts.append(row)

    fn_noteheads = []
    for i, fn in enumerate(parsed.missed_noteheads, start=1):
        fn_noteheads.append({
            "id": f"FN{i}",
            "x_canonical": int(fn.x),
            "y_canonical": int(fn.y),
            "pitch": fn.pitch or "",
        })

    return {
        "cell_id": cell_id,
        "verdicts": verdicts,
        "fn_noteheads": fn_noteheads,
    }


def _load_verdict_state(bench: Bench, cell_id: str) -> dict:
    """Return the current verdict state for a cell.

    Preference order:
      1. <cell_id>.verdict.json (the live state written by this tool)
      2. <cell_id>.md (legacy hand-filled markdown — parsed for pre-fill)
      3. empty template
    """
    detections = _load_detections(bench, cell_id)

    json_path = bench.verdict_json_path(cell_id)
    if json_path.exists():
        try:
            state = json.loads(json_path.read_text())
            # Make sure the verdicts list aligns with the current detections;
            # if a detection appeared/disappeared we patch the diff in.
            state = _reconcile_state(state, detections, cell_id)
            return state
        except json.JSONDecodeError:
            pass

    md_path = bench.verdict_md_path(cell_id)
    if md_path.exists():
        return _state_from_markdown(cell_id, md_path.read_text(), detections)

    return _empty_verdict_state(cell_id, detections)


def _reconcile_state(state: dict, detections: list[dict], cell_id: str) -> dict:
    """Make sure state['verdicts'] has one row per detection in order."""
    by_id = {v["detection_id"]: v for v in state.get("verdicts", [])}
    new_rows: list[dict] = []
    for d in detections:
        prev = by_id.get(d["id"])
        if prev is None:
            new_rows.append({
                "detection_id": d["id"],
                "smufl_name": d["smufl_name"],
                "verdict": "",
            })
        else:
            prev["smufl_name"] = d["smufl_name"]
            new_rows.append(prev)
    state["verdicts"] = new_rows
    state["cell_id"] = cell_id
    state.setdefault("fn_noteheads", [])
    return state


def _status_for_state(state: dict) -> str:
    verdicts = state.get("verdicts", [])
    if not verdicts:
        # No detections — if FNs were added we still count it partial.
        return "partially-filled" if state.get("fn_noteheads") else "empty"
    filled = [v for v in verdicts if v.get("verdict")]
    if not filled and not state.get("fn_noteheads"):
        return "empty"
    if len(filled) == len(verdicts):
        return "pre-filled"
    return "partially-filled"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


_VALID_VERDICTS = {"TP", "FP", "unsure", ""}
_PITCH_RX = re.compile(r"^[A-Ga-g][#b]?\d$")


def _validate_state(state: dict, expected_cell_id: str) -> tuple[dict, list[str]]:
    """Return (cleaned_state, errors). Drop unknown keys, coerce types."""
    errors: list[str] = []
    cid = state.get("cell_id", expected_cell_id)
    if cid != expected_cell_id:
        errors.append(
            f"cell_id mismatch: payload says {cid!r}, "
            f"URL says {expected_cell_id!r}"
        )

    out_verdicts = []
    for i, v in enumerate(state.get("verdicts", [])):
        if not isinstance(v, dict):
            errors.append(f"verdicts[{i}] is not an object")
            continue
        did = str(v.get("detection_id") or "")
        smufl = str(v.get("smufl_name") or "")
        verdict = str(v.get("verdict") or "")
        if verdict not in _VALID_VERDICTS:
            errors.append(
                f"verdicts[{i}]: bad verdict {verdict!r} "
                f"(want one of {sorted(_VALID_VERDICTS)})"
            )
            verdict = ""
        row: dict[str, Any] = {
            "detection_id": did,
            "smufl_name": smufl,
            "verdict": verdict,
        }
        wp = str(v.get("wrong_pitch") or "").strip()
        if wp:
            if not _PITCH_RX.match(wp):
                errors.append(
                    f"verdicts[{i}]: wrong_pitch {wp!r} is not a valid pitch"
                )
            else:
                row["wrong_pitch"] = wp
        # actual_label: optional free-text/SMuFL name of what the detection
        # ACTUALLY is. Only meaningful when verdict=FP (matcher's category
        # is wrong) but we pass it through regardless so the field survives
        # a verdict change.
        actual = str(v.get("actual_label") or "").strip()
        if actual:
            row["actual_label"] = actual
        out_verdicts.append(row)

    out_fns = []
    for i, fn in enumerate(state.get("fn_noteheads", [])):
        if not isinstance(fn, dict):
            errors.append(f"fn_noteheads[{i}] is not an object")
            continue
        try:
            x = int(fn.get("x_canonical"))
            y = int(fn.get("y_canonical"))
        except (TypeError, ValueError):
            errors.append(f"fn_noteheads[{i}]: x_canonical/y_canonical missing")
            continue
        pitch = str(fn.get("pitch") or "").strip()
        if pitch and not _PITCH_RX.match(pitch):
            errors.append(
                f"fn_noteheads[{i}]: pitch {pitch!r} is not valid (e.g. C4, F#4)"
            )
        out_fns.append({
            "id": str(fn.get("id") or f"FN{i + 1}"),
            "x_canonical": x,
            "y_canonical": y,
            "pitch": pitch,
        })

    cleaned = {
        "cell_id": expected_cell_id,
        "verdicts": out_verdicts,
        "fn_noteheads": out_fns,
    }
    return cleaned, errors


# ---------------------------------------------------------------------------
# Templates (inline; no Jinja files on disk)
# ---------------------------------------------------------------------------


_BASE_CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica,
       Arial, sans-serif; margin: 0; padding: 0; color: #222;
       background: #fafafa; }
header { background: #1f2937; color: #fff; padding: 10px 16px;
         display: flex; align-items: center; gap: 16px; }
header a { color: #fff; text-decoration: none; }
header nav { display: flex; gap: 12px; }
header h1 { font-size: 16px; margin: 0; }
main { padding: 16px; max-width: 1600px; margin: 0 auto; }
table { border-collapse: collapse; width: 100%; background: #fff; }
th, td { padding: 8px 10px; border-bottom: 1px solid #eee;
         text-align: left; font-size: 13px; }
th { background: #f3f4f6; font-weight: 600; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px;
         font-size: 11px; font-weight: 600; }
.badge.empty   { background: #fee2e2; color: #b91c1c; }
.badge.partial { background: #fef3c7; color: #92400e; }
.badge.pre     { background: #d1fae5; color: #065f46; }
.btn { display: inline-block; padding: 6px 10px; border-radius: 4px;
       background: #2563eb; color: #fff; text-decoration: none;
       font-size: 13px; cursor: pointer; border: 0; }
.btn.muted { background: #6b7280; }
.btn:hover { filter: brightness(1.1); }
.row { display: flex; gap: 16px; }
.col { flex: 1; min-width: 0; }
.overlay-wrap { position: relative; display: inline-block;
                border: 1px solid #ddd; background: #fff;
                max-width: 100%; }
.overlay-wrap img { display: block; max-width: 100%; height: auto; }
.fn-marker { position: absolute; width: 18px; height: 18px;
             margin-left: -9px; margin-top: -9px;
             border: 2px solid #ef4444; border-radius: 50%;
             pointer-events: none; background: rgba(239, 68, 68, 0.2); }
.fn-marker .label { position: absolute; top: -16px; left: 0;
                    font-size: 10px; color: #ef4444; font-weight: 700;
                    white-space: nowrap; }
.det-row { padding: 6px 8px; border-bottom: 1px solid #eee;
           display: grid; grid-template-columns: 38px 1fr 220px 120px;
           gap: 8px; align-items: center; }
.det-row.focused { background: #fef9c3; }
.det-id { font-weight: 700; }
.smufl { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
         font-size: 12px; color: #374151; }
.meta { font-size: 11px; color: #6b7280; }
.verdict-radio label { margin-right: 8px; font-size: 12px; }
.verdict-radio input { margin-right: 2px; }
.wrong-pitch-input { width: 80px; font-size: 12px; padding: 2px 4px; }
.help { background: #fef3c7; border: 1px solid #fde68a;
        padding: 8px 12px; border-radius: 4px;
        margin-bottom: 12px; font-size: 12px; color: #92400e; }
.summary { position: sticky; bottom: 0; background: #1f2937; color: #fff;
           padding: 8px 16px; font-size: 13px; }
.summary span { margin-right: 16px; }
.summary .save-status { font-style: italic; color: #d1d5db; }
.fn-add-panel { background: #fff; border: 1px solid #ddd;
                padding: 10px; margin-top: 12px; border-radius: 4px; }
.fn-list { font-size: 12px; }
.fn-list .fn-line { padding: 4px 0; border-bottom: 1px solid #f0f0f0;
                    display: flex; gap: 8px; align-items: center; }
.fn-list button { font-size: 11px; padding: 1px 6px; }
input[type="text"], select { padding: 4px 6px; font-size: 13px; }
.zoom-controls { margin: 8px 0; }
.zoom-controls button { margin-right: 4px; }
pre { background: #fff; border: 1px solid #ddd; padding: 12px;
      overflow: auto; font-size: 12px; }

/* ─── Queue (one-at-a-time) view ─────────────────────────────────────────── */
.queue-view { max-width: 1100px; margin: 0 auto; }
.queue-header { margin-bottom: 12px; }
.queue-progress { display: flex; align-items: center; gap: 14px;
                  font-size: 13px; color: #555; }
.queue-progress .pos { font-weight: 700; color: #1f2937; font-size: 14px; }
.queue-progress progress { flex: 1; height: 8px; }
.queue-context { margin-top: 6px; font-size: 13px; color: #6b7280; }
.queue-context a { color: #2563eb; }

.crop-wrap { background: #fff; border: 1px solid #ddd; padding: 16px;
             display: flex; align-items: center; justify-content: center;
             min-height: 240px; max-height: 60vh; overflow: hidden; }
.crop-wrap img.crop { display: block; max-width: 100%; max-height: 56vh;
                       width: auto; height: auto;
                       image-rendering: -webkit-optimize-contrast; }

.matcher-says { margin-top: 10px; font-size: 14px;
                background: #f3f4f6; padding: 8px 12px; border-radius: 4px; }
.matcher-says strong { color: #1f2937; }
.matcher-says .matcher-pitch { margin-left: 8px; color: #374151; }
.matcher-says .conf { float: right; color: #6b7280; font-size: 12px; }

.already { background: #fef9c3; border: 1px solid #fde68a;
           padding: 6px 10px; border-radius: 4px; font-size: 13px;
           margin: 8px 0; color: #713f12; }

.queue-actions { display: flex; flex-direction: column; gap: 10px;
                  margin-top: 14px; }
.big-btn { padding: 16px 18px; font-size: 16px; border-radius: 6px;
            border: 2px solid transparent; background: #fff;
            cursor: pointer; text-align: left; display: flex;
            align-items: center; gap: 12px;
            transition: background 0.1s, border-color 0.1s; }
.big-btn .key { display: inline-block; padding: 4px 10px; min-width: 30px;
                 text-align: center; background: #1f2937; color: #fff;
                 border-radius: 4px; font-family: ui-monospace, Menlo, monospace;
                 font-size: 13px; }
.big-btn.tp { border-color: #16a34a; color: #15803d; }
.big-btn.tp:hover, .big-btn.tp.sel { background: #dcfce7; }
.big-btn.fp { border-color: #dc2626; color: #b91c1c; }
.big-btn.fp:hover, .big-btn.fp.sel { background: #fee2e2; }
.big-btn.wp { border-color: #d97706; color: #92400e; }
.big-btn.wp:hover, .big-btn.wp.sel { background: #fef3c7; }
.big-btn.unsure { border-color: #6b7280; color: #4b5563; }
.big-btn.unsure:hover, .big-btn.unsure.sel { background: #f3f4f6; }

.wp-row { padding: 6px 14px; background: #fffbeb;
          border: 1px solid #fde68a; border-radius: 4px;
          display: flex; align-items: center; gap: 8px;
          font-size: 13px; }
.wp-row input { font-size: 14px; padding: 4px 8px; min-width: 120px; }

.nav-row { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.btn.ghost { background: transparent; color: #2563eb;
              border: 1px solid #cbd5e1; }
.btn.ghost:hover { background: #f1f5f9; }

#status { margin-top: 12px; font-size: 13px; min-height: 18px; }
#status.ok { color: #15803d; }
#status.err { color: #b91c1c; }

.shortcuts-help { margin-top: 18px; font-size: 12px; color: #6b7280; }
.shortcuts-help kbd { background: #f3f4f6; border: 1px solid #d1d5db;
                       border-radius: 3px; padding: 1px 6px;
                       font-family: ui-monospace, Menlo, monospace;
                       font-size: 11px; }
.shortcuts-help ul { margin: 6px 0; padding-left: 20px; }

.queue-cta { background: #1f2937; color: #fff;
             padding: 14px 18px; border-radius: 6px;
             margin-bottom: 14px; display: flex; align-items: center;
             justify-content: space-between; gap: 16px; }
.queue-cta h2 { margin: 0; font-size: 16px; }
.queue-cta p { margin: 4px 0 0; font-size: 13px; color: #d1d5db; }
.queue-cta a.btn { background: #16a34a; padding: 10px 16px;
                    font-size: 15px; }

.clef-bar { margin-top: 8px; padding: 8px 12px; border-radius: 4px;
             font-size: 13px; display: flex; align-items: center;
             gap: 10px; flex-wrap: wrap; }
.clef-bar.clef-treble { background: #e0f2fe; border: 1px solid #7dd3fc; }
.clef-bar.clef-bass   { background: #fef3c7; border: 1px solid #fcd34d; }
.clef-bar.clef-alto   { background: #f3e8ff; border: 1px solid #d8b4fe; }
.clef-bar.clef-tenor  { background: #fce7f3; border: 1px solid #f9a8d4; }
.clef-bar select { padding: 4px 8px; font-size: 14px;
                    font-weight: 700; text-transform: uppercase; }

.actual-label-row { padding: 8px 12px; background: #f9fafb;
                     border: 1px dashed #cbd5e1; border-radius: 4px;
                     display: flex; align-items: center; gap: 10px;
                     font-size: 12px; color: #475569;
                     flex-wrap: wrap; }
.actual-label-row label { font-weight: 600; }
.actual-label-row input { flex: 1; min-width: 220px; padding: 5px 8px;
                          font-size: 13px; }
.clef-bar .clef-hint { color: #6b7280; font-size: 12px; }
#clef-save-status { font-style: italic; color: #6b7280; font-size: 12px; }
"""


def _page(title: str, body_html: str) -> str:
    return (
        "<!doctype html>\n<html><head>"
        f"<title>{title} — ReEngrave annotate</title>"
        "<meta charset='utf-8'>"
        f"<style>{_BASE_CSS}</style>"
        "</head><body>"
        "<header>"
        "<h1>ReEngrave · Phase 2.5 annotate</h1>"
        "<nav>"
        "<a href='/'>Cells</a>"
        "<a href='/queue'>Queue</a>"
        "<a href='/score'>Run scorer</a>"
        "</nav>"
        "</header>"
        f"<main>{body_html}</main>"
        "</body></html>"
    )


def _render_cell_list(rows: list[dict]) -> str:
    counts = {"pre-filled": 0, "partially-filled": 0, "empty": 0}
    for r in rows:
        counts[r["status"]] += 1

    total_dets = sum(r["n_detections"] for r in rows)
    total_done = sum(r["n_filled"] for r in rows)
    pct = (total_done / total_dets * 100.0) if total_dets else 0.0
    lines = [
        "<div class='queue-cta'>"
        "<div>"
        "<h2>One-at-a-time annotation</h2>"
        f"<p>{total_done} of {total_dets} detections reviewed ({pct:.0f}%). "
        "Show a big crop of one detection at a time and use keyboard shortcuts.</p>"
        "</div>"
        "<a class='btn' href='/queue'>Start annotating →</a>"
        "</div>",
        f"<p>{len(rows)} cells. "
        f"<span class='badge pre'>pre-filled: {counts['pre-filled']}</span> "
        f"<span class='badge partial'>partial: {counts['partially-filled']}</span> "
        f"<span class='badge empty'>empty: {counts['empty']}</span></p>",
        "<table><thead><tr>"
        "<th>cell_id</th><th>source</th><th>page</th>"
        "<th>sys</th><th>staff</th><th>m</th>"
        "<th>detections</th><th>verdicts</th><th>FNs</th>"
        "<th>status</th><th></th>"
        "</tr></thead><tbody>",
    ]
    for r in rows:
        badge_class = {
            "pre-filled": "pre",
            "partially-filled": "partial",
            "empty": "empty",
        }[r["status"]]
        lines.append(
            "<tr>"
            f"<td><a href='/cells/{r['cell_id']}'>{r['cell_id']}</a></td>"
            f"<td>{r['source_tag']}</td>"
            f"<td>{r['page']}</td>"
            f"<td>{r['system_index']}</td>"
            f"<td>{r['staff_index']}</td>"
            f"<td>{r['measure_index']}</td>"
            f"<td>{r['n_detections']}</td>"
            f"<td>{r['n_filled']} / {r['n_detections']}</td>"
            f"<td>{r['n_fns']}</td>"
            f"<td><span class='badge {badge_class}'>{r['status']}</span></td>"
            f"<td><a class='btn' href='/cells/{r['cell_id']}'>open</a></td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def _render_cell_detail(
    entry: dict, detections: list[dict], state: dict,
    prev_id: str | None, next_id: str | None,
) -> str:
    cid = entry["cell_id"]
    # Build a quick map from detection_id → verdict row.
    by_id = {v["detection_id"]: v for v in state["verdicts"]}

    # Detection rows.
    det_rows = []
    for d in detections:
        v = by_id.get(d["id"], {"verdict": "", "wrong_pitch": ""})
        smufl = d["smufl_name"]
        is_notehead = d["category"] == "notehead"
        pitch_str = f" → {d['pitch']}" if d.get("pitch") else ""
        verdict = v.get("verdict", "")

        def _checked(val: str) -> str:
            return "checked" if verdict == val else ""

        wp_value = v.get("wrong_pitch", "") if is_notehead else ""
        wp_hidden = "" if is_notehead else "style='visibility:hidden'"

        det_rows.append(f"""
        <div class="det-row" data-det-id="{d['id']}" data-is-notehead="{int(is_notehead)}">
          <div class="det-id">{d['id']}</div>
          <div>
            <div class="smufl">{smufl} ({d['category']})</div>
            <div class="meta">at ({d['x_center']}, {d['y_center']}){pitch_str} · conf={d['confidence']:.2f}</div>
          </div>
          <div class="verdict-radio">
            <label><input type="radio" name="v_{d['id']}" value="TP" {_checked('TP')}>TP</label>
            <label><input type="radio" name="v_{d['id']}" value="FP" {_checked('FP')}>FP</label>
            <label><input type="radio" name="v_{d['id']}" value="unsure" {_checked('unsure')}>unsure</label>
            <label><input type="radio" name="v_{d['id']}" value="" {_checked('')}>—</label>
          </div>
          <div {wp_hidden}>
            <input type="text" class="wrong-pitch-input" data-det-id="{d['id']}"
                   placeholder="wrong→pitch" value="{wp_value}">
          </div>
        </div>""")

    # FN list
    fn_list_html = []
    for fn in state["fn_noteheads"]:
        fn_list_html.append(f"""
          <div class="fn-line" data-fn-id="{fn['id']}">
            <strong>{fn['id']}</strong>
            <span>at (x={fn['x_canonical']}, y={fn['y_canonical']})</span>
            <span>pitch=<input type="text" class="fn-pitch" data-fn-id="{fn['id']}"
                value="{fn.get('pitch', '')}" style="width:60px"></span>
            <button onclick="removeFN('{fn['id']}')">remove</button>
          </div>""")

    nav_links = []
    if prev_id:
        nav_links.append(f"<a class='btn muted' href='/cells/{prev_id}'>← {prev_id}</a>")
    nav_links.append(f"<a class='btn muted' href='/'>list</a>")
    if next_id:
        nav_links.append(f"<a class='btn muted' href='/cells/{next_id}'>{next_id} →</a>")

    canonical_w = entry.get("cell_canonical_w", 2048)
    canonical_h = entry.get("cell_canonical_h", 500)

    pitch_options = []
    for octave in range(3, 7):
        for note in ["C", "D", "E", "F", "G", "A", "B"]:
            pitch_options.append(f"{note}{octave}")
    pitch_options_html = "".join(
        f"<option value='{p}'>{p}</option>" for p in pitch_options)

    body = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <h2 style="margin:0">Cell <code>{cid}</code></h2>
      <div>{' '.join(nav_links)}</div>
    </div>

    <div class="help">
      <strong>Keys:</strong> <code>t</code>=TP · <code>f</code>=FP · <code>u</code>=unsure ·
      <code>space</code>=next detection ·
      Click the image to fill in FN coordinates.
      Auto-saves 300ms after each change.
      &nbsp;·&nbsp; <strong>Status:</strong> {state.get('cell_id')} ·
      detections={len(detections)} · FNs={len(state['fn_noteheads'])}
    </div>

    <div class="row">
      <div class="col" style="flex: 2;">
        <div class="zoom-controls">
          <button onclick="setZoom(0.5)">50%</button>
          <button onclick="setZoom(1.0)">100%</button>
          <button onclick="setZoom(1.5)">150%</button>
          <button onclick="setZoom(2.0)">200%</button>
          <span class="meta">click image to set FN coords (canonical {canonical_w}×{canonical_h})</span>
        </div>
        <div class="overlay-wrap" id="overlay-wrap">
          <img id="overlay-img" src="/cells/{cid}/overlay.png"
               data-canonical-w="{canonical_w}" data-canonical-h="{canonical_h}">
          <div id="fn-markers"></div>
        </div>

        <div class="fn-add-panel">
          <h3 style="margin-top:0">Add missed notehead (FN)</h3>
          <p class="meta">Click the overlay to capture x/y, then pick a pitch.</p>
          <div style="display:flex; gap:8px; align-items:center;">
            x=<input id="fn-x" type="number" style="width:70px">
            y=<input id="fn-y" type="number" style="width:70px">
            pitch=
            <select id="fn-pitch-select">
              <option value="">(choose)</option>
              {pitch_options_html}
            </select>
            or type:<input id="fn-pitch-text" type="text" style="width:70px" placeholder="F#4">
            <button class="btn" onclick="addFN()">Add FN</button>
          </div>
          <div class="fn-list" id="fn-list">
            {''.join(fn_list_html)}
          </div>
        </div>
      </div>

      <div class="col" style="flex: 1.2;">
        <h3>Detections ({len(detections)})</h3>
        <div id="det-list">
          {''.join(det_rows)}
        </div>
      </div>
    </div>

    <div class="summary">
      <span id="sum-tp">TP: 0</span>
      <span id="sum-fp">FP: 0</span>
      <span id="sum-unsure">unsure: 0</span>
      <span id="sum-empty">unfilled: 0</span>
      <span id="sum-fn">FN: 0</span>
      <span class="save-status" id="save-status">all saved</span>
    </div>

    <script>
    const CELL_ID = {json.dumps(cid)};
    const state = {json.dumps(state)};
    const detections = {json.dumps(detections)};

    function $(id) {{ return document.getElementById(id); }}

    function updateSummary() {{
      const counts = {{ TP: 0, FP: 0, unsure: 0, empty: 0 }};
      for (const v of state.verdicts) {{
        if (v.verdict === "TP") counts.TP++;
        else if (v.verdict === "FP") counts.FP++;
        else if (v.verdict === "unsure") counts.unsure++;
        else counts.empty++;
      }}
      $("sum-tp").textContent = "TP: " + counts.TP;
      $("sum-fp").textContent = "FP: " + counts.FP;
      $("sum-unsure").textContent = "unsure: " + counts.unsure;
      $("sum-empty").textContent = "unfilled: " + counts.empty;
      $("sum-fn").textContent = "FN: " + state.fn_noteheads.length;
    }}

    let saveTimer = null;
    let saveInflight = false;
    let pendingSave = false;

    function scheduleSave() {{
      $("save-status").textContent = "saving…";
      if (saveTimer) clearTimeout(saveTimer);
      saveTimer = setTimeout(doSave, 300);
    }}

    async function doSave() {{
      if (saveInflight) {{ pendingSave = true; return; }}
      saveInflight = true;
      try {{
        const resp = await fetch(`/cells/${{CELL_ID}}/verdict.json`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify(state),
        }});
        const j = await resp.json();
        if (resp.ok && j.ok) {{
          $("save-status").textContent = "saved " + new Date().toLocaleTimeString();
        }} else {{
          $("save-status").textContent = "ERROR: " + (j.errors || []).join("; ");
        }}
      }} catch (e) {{
        $("save-status").textContent = "save FAILED: " + e.message;
      }} finally {{
        saveInflight = false;
        if (pendingSave) {{ pendingSave = false; doSave(); }}
      }}
    }}

    // Wire radio buttons.
    document.querySelectorAll('.verdict-radio input[type=radio]').forEach(r => {{
      r.addEventListener('change', () => {{
        const detId = r.name.slice(2); // strip "v_"
        const row = state.verdicts.find(v => v.detection_id === detId);
        if (row) {{
          row.verdict = r.value;
          updateSummary();
          scheduleSave();
        }}
      }});
    }});

    // Wire wrong-pitch text inputs.
    document.querySelectorAll('.wrong-pitch-input').forEach(inp => {{
      inp.addEventListener('input', () => {{
        const detId = inp.dataset.detId;
        const row = state.verdicts.find(v => v.detection_id === detId);
        if (!row) return;
        if (inp.value.trim()) row.wrong_pitch = inp.value.trim();
        else delete row.wrong_pitch;
        scheduleSave();
      }});
    }});

    // Image click → capture FN coordinates (convert from displayed px to canonical).
    function imageToCanonical(clientX, clientY) {{
      const img = $("overlay-img");
      const rect = img.getBoundingClientRect();
      const canonW = parseInt(img.dataset.canonicalW);
      const canonH = parseInt(img.dataset.canonicalH);
      const xPct = (clientX - rect.left) / rect.width;
      const yPct = (clientY - rect.top) / rect.height;
      return [Math.round(xPct * canonW), Math.round(yPct * canonH)];
    }}

    $("overlay-img").addEventListener('click', (ev) => {{
      const [x, y] = imageToCanonical(ev.clientX, ev.clientY);
      $("fn-x").value = x;
      $("fn-y").value = y;
    }});

    function renderFnMarkers() {{
      const markers = $("fn-markers");
      const img = $("overlay-img");
      markers.innerHTML = "";
      if (!img.complete) return;
      const canonW = parseInt(img.dataset.canonicalW);
      const canonH = parseInt(img.dataset.canonicalH);
      for (const fn of state.fn_noteheads) {{
        const xPct = (fn.x_canonical / canonW) * 100;
        const yPct = (fn.y_canonical / canonH) * 100;
        const m = document.createElement("div");
        m.className = "fn-marker";
        m.style.left = xPct + "%";
        m.style.top = yPct + "%";
        m.innerHTML = `<span class="label">${{fn.id}}${{fn.pitch ? ' ' + fn.pitch : ''}}</span>`;
        markers.appendChild(m);
      }}
      renderFnList();
    }}

    function renderFnList() {{
      const list = $("fn-list");
      list.innerHTML = "";
      for (const fn of state.fn_noteheads) {{
        const line = document.createElement("div");
        line.className = "fn-line";
        line.innerHTML = `
          <strong>${{fn.id}}</strong>
          <span>at (x=${{fn.x_canonical}}, y=${{fn.y_canonical}})</span>
          <span>pitch=<input type="text" class="fn-pitch" data-fn-id="${{fn.id}}"
              value="${{fn.pitch || ''}}" style="width:60px"></span>
          <button data-fn-id="${{fn.id}}">remove</button>`;
        list.appendChild(line);
      }}
      // Rewire.
      list.querySelectorAll('.fn-pitch').forEach(inp => {{
        inp.addEventListener('input', () => {{
          const fnId = inp.dataset.fnId;
          const fn = state.fn_noteheads.find(f => f.id === fnId);
          if (fn) {{ fn.pitch = inp.value.trim(); scheduleSave(); renderFnMarkers(); }}
        }});
      }});
      list.querySelectorAll('button').forEach(btn => {{
        btn.addEventListener('click', () => {{
          removeFN(btn.dataset.fnId);
        }});
      }});
    }}

    function nextFnId() {{
      let max = 0;
      for (const fn of state.fn_noteheads) {{
        const m = /^FN(\\d+)$/.exec(fn.id);
        if (m) max = Math.max(max, parseInt(m[1]));
      }}
      return "FN" + (max + 1);
    }}

    function addFN() {{
      const x = parseInt($("fn-x").value);
      const y = parseInt($("fn-y").value);
      if (isNaN(x) || isNaN(y)) {{ alert("set x/y first"); return; }}
      const pitchSel = $("fn-pitch-select").value;
      const pitchTxt = $("fn-pitch-text").value.trim();
      const pitch = pitchTxt || pitchSel || "";
      state.fn_noteheads.push({{
        id: nextFnId(),
        x_canonical: x,
        y_canonical: y,
        pitch: pitch,
      }});
      $("fn-x").value = "";
      $("fn-y").value = "";
      $("fn-pitch-select").value = "";
      $("fn-pitch-text").value = "";
      renderFnMarkers();
      updateSummary();
      scheduleSave();
    }}

    function removeFN(id) {{
      state.fn_noteheads = state.fn_noteheads.filter(f => f.id !== id);
      renderFnMarkers();
      updateSummary();
      scheduleSave();
    }}

    function setZoom(z) {{
      const img = $("overlay-img");
      img.style.maxWidth = "none";
      const canonW = parseInt(img.dataset.canonicalW);
      img.style.width = (canonW * z) + "px";
      setTimeout(renderFnMarkers, 50);
    }}

    // Keyboard shortcuts: navigate detections + set verdict.
    let focusedIdx = 0;
    function refreshFocus() {{
      document.querySelectorAll('.det-row').forEach((el, i) => {{
        el.classList.toggle('focused', i === focusedIdx);
        if (i === focusedIdx) el.scrollIntoView({{block: 'nearest'}});
      }});
    }}

    function setVerdictForFocused(value) {{
      const rows = document.querySelectorAll('.det-row');
      if (focusedIdx >= rows.length) return;
      const detId = rows[focusedIdx].dataset.detId;
      const radio = document.querySelector(
        `input[type=radio][name="v_${{detId}}"][value="${{value}}"]`);
      if (radio) {{ radio.checked = true; radio.dispatchEvent(new Event('change')); }}
    }}

    document.addEventListener('keydown', (ev) => {{
      // Skip if focus is in a text/number input.
      const tag = (ev.target.tagName || '').toLowerCase();
      if (tag === 'input' && ev.target.type !== 'radio') return;
      if (tag === 'select' || tag === 'textarea') return;

      const k = ev.key.toLowerCase();
      if (k === 't') {{ setVerdictForFocused('TP'); ev.preventDefault(); }}
      else if (k === 'f') {{ setVerdictForFocused('FP'); ev.preventDefault(); }}
      else if (k === 'u') {{ setVerdictForFocused('unsure'); ev.preventDefault(); }}
      else if (k === ' ' || k === 'arrowdown') {{
        focusedIdx = Math.min(focusedIdx + 1, detections.length - 1);
        refreshFocus(); ev.preventDefault();
      }} else if (k === 'arrowup') {{
        focusedIdx = Math.max(0, focusedIdx - 1);
        refreshFocus(); ev.preventDefault();
      }}
    }});

    // Click a det-row to focus it.
    document.querySelectorAll('.det-row').forEach((el, i) => {{
      el.addEventListener('click', () => {{ focusedIdx = i; refreshFocus(); }});
    }});

    // Initial render.
    $("overlay-img").addEventListener('load', renderFnMarkers);
    if ($("overlay-img").complete) renderFnMarkers();
    refreshFocus();
    updateSummary();
    </script>
    """
    return body


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _detection_crop_png(cell_png_path: Path, det: dict, padding_factor: float = 2.5) -> bytes:
    """Crop the cell PNG around a detection and draw the detection bbox in red.

    Returns PNG bytes ready to send to the browser.
    """
    from PIL import Image, ImageDraw

    img = Image.open(cell_png_path).convert("RGB")
    img_w, img_h = img.size
    x = int(det.get("x", 0))
    y = int(det.get("y", 0))
    w = int(det.get("w", 0))
    h = int(det.get("h", 0))
    # Padding around the bbox so the user can see surrounding context.
    pad = int(max(w, h, 30) * padding_factor)
    crop_l = max(0, x - pad)
    crop_t = max(0, y - pad)
    crop_r = min(img_w, x + w + pad)
    crop_b = min(img_h, y + h + pad)
    crop = img.crop((crop_l, crop_t, crop_r, crop_b))

    # Draw the detection bbox + a small crosshair at its center.
    draw = ImageDraw.Draw(crop)
    rx = x - crop_l
    ry = y - crop_t
    draw.rectangle([rx, ry, rx + w - 1, ry + h - 1], outline=(220, 30, 30), width=4)

    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    return buf.getvalue()


def _all_queue_positions(bench: Bench) -> list[tuple[str, int, dict, dict, int, int]]:
    """Walk every (cell, detection_index) pair in manifest order.

    Returns a list of tuples (cell_id, idx, detection_dict, verdict_dict,
    overall_position, overall_total). Useful for both queue navigation and
    progress display.
    """
    manifest = bench.load_manifest()
    items: list[tuple[str, int, dict, dict]] = []
    for entry in manifest:
        cid = entry["cell_id"]
        detections = _load_detections(bench, cid)
        state = _load_verdict_state(bench, cid)
        verdicts_by_id = {v["detection_id"]: v for v in state["verdicts"]}
        for idx, d in enumerate(detections):
            v = verdicts_by_id.get(d["id"], {"verdict": ""})
            items.append((cid, idx, d, v))
    total = len(items)
    return [(c, i, d, v, pos + 1, total) for pos, (c, i, d, v) in enumerate(items)]


def _find_queue_position(
    bench: Bench, target_cell: str | None, target_idx: int | None,
) -> tuple[str, int, dict, dict, int, int] | None:
    """Find a specific queue position, OR the first unreviewed one if target
    is None."""
    items = _all_queue_positions(bench)
    if not items:
        return None
    if target_cell is not None and target_idx is not None:
        for it in items:
            if it[0] == target_cell and it[1] == target_idx:
                return it
        return None
    # First unreviewed
    for it in items:
        verdict = it[3].get("verdict", "")
        if not verdict:
            return it
    # All reviewed: return the last one (so the user lands somewhere sensible).
    return items[-1]


def _adjacent_queue_position(
    bench: Bench, cell_id: str, idx: int, direction: str,
) -> tuple[str, int] | None:
    """Return the prev/next position regardless of review state."""
    items = _all_queue_positions(bench)
    for pos, it in enumerate(items):
        if it[0] == cell_id and it[1] == idx:
            if direction == "next":
                target = pos + 1
            else:
                target = pos - 1
            if 0 <= target < len(items):
                return (items[target][0], items[target][1])
            return None
    return None


def _next_unreviewed_after(
    bench: Bench, cell_id: str, idx: int,
) -> tuple[str, int] | None:
    """Find the next position with empty verdict AFTER (cell_id, idx)."""
    items = _all_queue_positions(bench)
    seen_current = False
    for it in items:
        if not seen_current:
            if it[0] == cell_id and it[1] == idx:
                seen_current = True
            continue
        if not it[3].get("verdict"):
            return (it[0], it[1])
    return None


_PITCH_OPTIONS = [
    f"{n}{octave}" for octave in range(2, 7)
    for n in ("C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb",
              "G", "G#", "Ab", "A", "A#", "Bb", "B")
]


def _render_queue_view(
    bench: Bench, cell_id: str, idx: int, det: dict, verdict: dict,
    position: int, total: int, cell_entry: dict | None = None,
) -> str:
    """Render the focused single-detection page."""
    items = _all_queue_positions(bench)
    n_reviewed = sum(1 for it in items if it[3].get("verdict"))
    n_remaining = total - n_reviewed

    is_notehead = (det.get("category") == "notehead") or det.get("smufl_name", "").startswith("notehead")
    current_pitch = det.get("pitch") or ""
    wrong_pitch = verdict.get("wrong_pitch", "")
    current_verdict = (verdict.get("verdict") or "").strip()
    current_clef = (cell_entry or {}).get("clef", "treble")
    actual_label = verdict.get("actual_label", "")

    # Selected radio state for the buttons
    sel_tp = current_verdict.lower() in {"tp", "true", "correct"}
    sel_fp = current_verdict.lower() in {"fp", "false", "wrong"}
    sel_wp = bool(wrong_pitch)
    sel_unsure = current_verdict.lower() in {"unsure", "skip", "?"}

    prev_pos = _adjacent_queue_position(bench, cell_id, idx, "prev")
    next_pos = _adjacent_queue_position(bench, cell_id, idx, "next")
    prev_link = (f"/queue/{prev_pos[0]}/{prev_pos[1]}" if prev_pos
                 else "#")
    next_link = (f"/queue/{next_pos[0]}/{next_pos[1]}" if next_pos
                 else "/")

    pitch_options_html = "".join(
        f"<option value='{p}'>{p}</option>" for p in _PITCH_OPTIONS
    )

    pitch_picker = ""
    if is_notehead:
        pitch_picker = (
            "<div class='wp-row'>"
            "<label for='wrong_pitch'>Correct pitch:</label> "
            f"<input id='wrong_pitch' type='text' list='pitch-list' "
            f"value='{_html_escape(wrong_pitch)}' "
            f"placeholder='e.g. C4 or F#5' />"
            f"<datalist id='pitch-list'>{pitch_options_html}</datalist>"
            "</div>"
        )

    # Common SMuFL labels for the actual-label datalist. Free-text input
    # accepts anything; this is just for autocomplete.
    common_labels = [
        "noteheadBlack", "noteheadHalf", "noteheadWhole",
        "restWhole", "restHalf", "restQuarter", "rest8th", "rest16th",
        "accidentalSharp", "accidentalFlat", "accidentalNatural",
        "accidentalDoubleSharp", "accidentalDoubleFlat",
        "gClef", "fClef", "cClefAlto", "cClefTenor",
        "flag8thUp", "flag8thDown", "flag16thUp", "flag16thDown",
        "stem", "beam",
        "barlineSingle", "barlineFinal",
        "augmentationDot",
        "fermataAbove", "fermataBelow",
        "articStaccato", "articTenuto", "articAccent",
        "dynamicForte", "dynamicPiano", "dynamicMezzoForte", "dynamicMezzoPiano",
        "tie", "slur",
        "tupletBracket",
        "nothing (smudge / scan artifact)",
    ]
    actual_options_html = "".join(
        f"<option value='{_html_escape(c)}'>" for c in common_labels
    )

    pitch_info = (f"<span class='matcher-pitch'>→ pitch <strong>{_html_escape(current_pitch)}</strong></span>"
                  if current_pitch else "")

    badge_existing = ""
    if current_verdict:
        badge_existing = (
            f"<p class='already'>Already marked: "
            f"<strong>{_html_escape(current_verdict)}</strong>"
            + (f" (wrong pitch → {_html_escape(wrong_pitch)})" if wrong_pitch else "")
            + ".  Use the buttons below to change.</p>"
        )

    clef_options = ["treble", "bass", "alto", "tenor"]
    clef_select_opts = "".join(
        f"<option value='{c}'{' selected' if c == current_clef else ''}>{c}</option>"
        for c in clef_options
    )

    body = f"""
<section class='queue-view'>
  <div class='queue-header'>
    <div class='queue-progress'>
      <span class='pos'>Detection {position} of {total}</span>
      <span class='reviewed'>{n_reviewed} reviewed · {n_remaining} remaining</span>
      <progress max='{total}' value='{n_reviewed}'></progress>
    </div>
    <div class='queue-context'>
      <strong>Cell:</strong> <a href='/cells/{cell_id}'>{cell_id}</a>
      &nbsp;·&nbsp;
      <strong>Detection:</strong> {det.get('id', '?')} ({_html_escape(det.get('smufl_name', '?'))})
    </div>
    <div class='clef-bar clef-{_html_escape(current_clef)}'>
      <strong>Clef:</strong>
      <select id='clef-select' aria-label='change clef for this cell'>{clef_select_opts}</select>
      <span class='clef-hint'>changing the clef re-resolves every notehead pitch in this cell</span>
      <span id='clef-save-status'></span>
    </div>
  </div>

  <div class='crop-wrap'>
    <img class='crop' src='/cells/{cell_id}/d/{idx}/crop.png?v={position}'
         alt='detection crop'>
  </div>

  <div class='matcher-says'>
    <span>Matcher's guess:</span>
    <strong>{_html_escape(det.get('smufl_name', '?'))}</strong>
    {pitch_info}
    <span class='conf'>conf {det.get('confidence', 0):.2f}</span>
  </div>

  {badge_existing}

  <form id='qform' class='queue-actions'>
    <input type='hidden' name='cell_id' value='{cell_id}'>
    <input type='hidden' name='det_idx' value='{idx}'>

    <button type='button' class='big-btn tp{" sel" if sel_tp else ""}' data-action='TP'>
      <span class='key'>C</span> Correct (TP)
    </button>
    <button type='button' class='big-btn fp{" sel" if sel_fp else ""}' data-action='FP'>
      <span class='key'>F</span> Wrong (FP)
    </button>
    {"<button type='button' class='big-btn wp" + (" sel" if sel_wp else "") + "' data-action='WP'><span class='key'>P</span> Right symbol, wrong pitch</button>" if is_notehead else ""}
    <button type='button' class='big-btn unsure{" sel" if sel_unsure else ""}' data-action='UNSURE'>
      <span class='key'>U</span> Unsure
    </button>

    {pitch_picker}

    <div class='actual-label-row'>
      <label for='actual_label'>What it actually is (optional, only matters for FP):</label>
      <input id='actual_label' type='text' list='label-list'
             value='{_html_escape(actual_label)}'
             placeholder='e.g. restQuarter, accidentalSharp, nothing (smudge)…' />
      <datalist id='label-list'>{actual_options_html}</datalist>
    </div>

    <div class='nav-row'>
      <a class='btn ghost' href='{prev_link}'>← prev</a>
      <a class='btn ghost' href='{next_link}'>skip →</a>
      <a class='btn ghost' href='/queue'>jump to next unreviewed</a>
      <a class='btn ghost' href='/cells/{cell_id}'>summary view</a>
    </div>
  </form>

  <div id='status' class='status'></div>

  <details class='shortcuts-help'>
    <summary>Keyboard shortcuts</summary>
    <ul>
      <li><kbd>C</kbd> — mark Correct (TP)</li>
      <li><kbd>F</kbd> — mark Wrong (FP)</li>
      <li><kbd>P</kbd> — wrong pitch (noteheads only)</li>
      <li><kbd>U</kbd> or <kbd>Space</kbd> — Unsure (and advance)</li>
      <li><kbd>←</kbd> / <kbd>→</kbd> — prev / next detection</li>
    </ul>
  </details>
</section>
"""

    js = f"""
<script>
(function() {{
  const cellId = {cell_id!r};
  const detIdx = {idx};
  const isNotehead = {str(is_notehead).lower()};
  const nextHref = {next_link!r};

  function showStatus(msg, cls) {{
    const el = document.getElementById('status');
    el.textContent = msg;
    el.className = 'status ' + (cls || '');
  }}

  async function postVerdict(action, wrongPitchValue) {{
    const payload = {{
      cell_id: cellId,
      det_idx: detIdx,
      action: action,
    }};
    // actual_label is optional and only persists for FP, but pass it through
    // on every action so the field survives a verdict change.
    const labelEl = document.getElementById('actual_label');
    if (labelEl && labelEl.value.trim()) {{
      payload.actual_label = labelEl.value.trim();
    }}
    if (action === 'WP') {{
      payload.wrong_pitch = (wrongPitchValue || '').trim();
      if (!payload.wrong_pitch) {{
        showStatus('Enter the correct pitch below first.', 'err');
        return false;
      }}
    }}
    showStatus('Saving…', '');
    try {{
      const resp = await fetch('/queue/' + cellId + '/' + detIdx, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload),
      }});
      const data = await resp.json();
      if (!resp.ok || !data.ok) {{
        showStatus('Save failed: ' + (data.error || resp.statusText), 'err');
        return false;
      }}
      showStatus('Saved · advancing…', 'ok');
      // Go to the next page server-side determined.
      window.location.href = data.next_url || nextHref;
      return true;
    }} catch (err) {{
      showStatus('Network error: ' + err.message, 'err');
      return false;
    }}
  }}

  document.querySelectorAll('.big-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const action = btn.dataset.action;
      const wp = document.getElementById('wrong_pitch');
      postVerdict(action, wp ? wp.value : '');
    }});
  }});

  // Keyboard shortcuts.
  document.addEventListener('keydown', (e) => {{
    // Don't intercept typing in the pitch field.
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea') return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === 'c') {{ e.preventDefault(); postVerdict('TP'); }}
    else if (k === 'f') {{ e.preventDefault(); postVerdict('FP'); }}
    else if (k === 'p' && isNotehead) {{
      e.preventDefault();
      const wp = document.getElementById('wrong_pitch');
      if (wp) wp.focus();
    }}
    else if (k === 'u' || k === ' ') {{ e.preventDefault(); postVerdict('UNSURE'); }}
    else if (e.key === 'ArrowLeft') {{
      e.preventDefault();
      window.location.href = {prev_link!r};
    }}
    else if (e.key === 'ArrowRight') {{
      e.preventDefault();
      window.location.href = {next_link!r};
    }}
  }});

  // When user hits Enter in the wrong-pitch field, treat as submit WP.
  const wpEl = document.getElementById('wrong_pitch');
  if (wpEl) {{
    wpEl.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter') {{
        e.preventDefault();
        postVerdict('WP', wpEl.value);
      }}
    }});
  }}

  // Clef change → POST + reload so the new pitches show.
  const clefEl = document.getElementById('clef-select');
  const clefStatusEl = document.getElementById('clef-save-status');
  if (clefEl) {{
    clefEl.addEventListener('change', async () => {{
      const newClef = clefEl.value;
      clefStatusEl.textContent = ' saving…';
      try {{
        const resp = await fetch('/cells/' + cellId + '/clef', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ clef: newClef }}),
        }});
        const data = await resp.json();
        if (!resp.ok || !data.ok) {{
          clefStatusEl.textContent = ' (save failed)';
          return;
        }}
        clefStatusEl.textContent = ' saved · reloading…';
        // Reload the page so the matcher's "guess" pitch shows the new clef.
        window.location.reload();
      }} catch (err) {{
        clefStatusEl.textContent = ' (network error)';
      }}
    }});
  }}
}})();
</script>
"""
    return body + js


def create_app(bench_dir: str | Path) -> Flask:
    bench = Bench(root=Path(bench_dir).resolve())
    app = Flask(__name__)
    app.config["BENCH"] = bench

    @app.route("/")
    def index():
        manifest = bench.load_manifest()
        rows = []
        for entry in manifest:
            cid = entry["cell_id"]
            detections = _load_detections(bench, cid)
            state = _load_verdict_state(bench, cid)
            n_filled = sum(1 for v in state["verdicts"] if v.get("verdict"))
            rows.append({
                "cell_id": cid,
                "source_tag": entry.get("source_tag", ""),
                "page": entry.get("page", ""),
                "system_index": entry.get("system_index", ""),
                "staff_index": entry.get("staff_index", ""),
                "measure_index": entry.get("measure_index", ""),
                "n_detections": len(detections),
                "n_filled": n_filled,
                "n_fns": len(state["fn_noteheads"]),
                "status": _status_for_state(state),
            })
        return _page("Cells", _render_cell_list(rows))

    @app.route("/cells/<cell_id>")
    def cell_detail(cell_id: str):
        manifest = bench.load_manifest()
        ids = [e["cell_id"] for e in manifest]
        if cell_id not in ids:
            abort(404, f"unknown cell {cell_id!r}")
        idx = ids.index(cell_id)
        prev_id = ids[idx - 1] if idx > 0 else None
        next_id = ids[idx + 1] if idx + 1 < len(ids) else None
        entry = manifest[idx]

        detections = _load_detections(bench, cell_id)
        state = _load_verdict_state(bench, cell_id)
        body = _render_cell_detail(entry, detections, state, prev_id, next_id)
        return _page(cell_id, body)

    @app.route("/cells/<cell_id>/overlay.png")
    def cell_overlay(cell_id: str):
        p = bench.overlay_path(cell_id)
        if not p.exists():
            abort(404)
        return send_file(p, mimetype="image/png")

    @app.route("/cells/<cell_id>/verdict.json", methods=["GET", "POST"])
    def cell_verdict(cell_id: str):
        manifest = bench.load_manifest()
        ids = {e["cell_id"] for e in manifest}
        if cell_id not in ids:
            abort(404, f"unknown cell {cell_id!r}")

        if request.method == "GET":
            return jsonify(_load_verdict_state(bench, cell_id))

        # POST
        try:
            payload = request.get_json(force=True)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "errors": [f"bad JSON: {exc}"]}), 400
        if not isinstance(payload, dict):
            return jsonify({"ok": False, "errors": ["payload must be a JSON object"]}), 400

        cleaned, errors = _validate_state(payload, cell_id)
        if errors:
            # Validation errors are non-fatal — we still save the cleaned-up
            # payload, but we report them so the UI can surface them.
            pass

        bench.verdicts_dir.mkdir(parents=True, exist_ok=True)
        bench.verdict_json_path(cell_id).write_text(
            json.dumps(cleaned, indent=2))
        return jsonify({"ok": True, "errors": errors, "state": cleaned})

    @app.route("/queue")
    def queue_start():
        """Find the next unreviewed detection and redirect to it."""
        pos = _find_queue_position(bench, None, None)
        if pos is None:
            return _page(
                "Queue",
                "<p>No detections to review (manifest empty?).</p>"
                "<p><a class='btn' href='/'>← back to cells</a></p>",
            )
        cell_id, idx, _, _, _, _ = pos
        return redirect(url_for("queue_one", cell_id=cell_id, idx=idx))

    @app.route("/queue/<cell_id>/<int:idx>")
    def queue_one(cell_id: str, idx: int):
        pos = _find_queue_position(bench, cell_id, idx)
        if pos is None:
            abort(404, f"unknown queue position: {cell_id} #{idx}")
        cell_id, idx, det, verdict, position, total = pos
        manifest = bench.load_manifest()
        cell_entry = next((e for e in manifest if e["cell_id"] == cell_id), None)
        body = _render_queue_view(bench, cell_id, idx, det, verdict,
                                  position, total, cell_entry=cell_entry)
        return _page(f"queue · {cell_id} #{idx}", body)

    @app.route("/cells/<cell_id>/clef", methods=["POST"])
    def update_cell_clef(cell_id: str):
        """Update the clef assigned to a cell + re-resolve its notehead pitches."""
        manifest = bench.load_manifest()
        entry = next((e for e in manifest if e["cell_id"] == cell_id), None)
        if entry is None:
            return jsonify({"ok": False, "error": f"unknown cell {cell_id!r}"}), 404
        try:
            payload = request.get_json(force=True) or {}
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "error": f"bad JSON: {exc}"}), 400
        new_clef = str(payload.get("clef", "")).strip().lower()
        if new_clef not in {"treble", "bass", "alto", "tenor"}:
            return jsonify({"ok": False, "error": f"invalid clef {new_clef!r}"}), 400

        entry["clef"] = new_clef
        bench.manifest_path.write_text(json.dumps(manifest, indent=2))

        # Re-resolve every notehead pitch in this cell's detection JSON.
        det_path = bench.detection_path(cell_id)
        n_changed = 0
        n_total = 0
        if det_path.exists():
            try:
                from ..pitch_resolver import pitch_for_notehead
            except Exception:
                pitch_for_notehead = None  # type: ignore
            if pitch_for_notehead is not None:
                data = json.loads(det_path.read_text())
                staff_lines = entry.get("staff_line_ys_canonical", [])
                for d in data.get("detections", []):
                    if d.get("category") != "notehead":
                        continue
                    n_total += 1

                    class _V:
                        pass
                    view = _V()
                    view.smufl_name = d.get("smufl_name", "")
                    view.category = d.get("category", "")
                    view.x_center = d.get("x_center", 0)
                    view.y_center = d.get("y_center", 0)
                    view.cell = _V()
                    view.cell.staff_line_ys_canonical = staff_lines
                    new_pitch = pitch_for_notehead(view, clef=new_clef)
                    if new_pitch != d.get("pitch"):
                        d["pitch"] = new_pitch
                        n_changed += 1
                det_path.write_text(json.dumps(data, indent=2))

        return jsonify({
            "ok": True,
            "clef": new_clef,
            "noteheads_total": n_total,
            "noteheads_repitched": n_changed,
        })

    @app.route("/queue/<cell_id>/<int:idx>", methods=["POST"])
    def queue_record(cell_id: str, idx: int):
        try:
            payload = request.get_json(force=True) or {}
        except Exception as exc:  # noqa: BLE001
            return jsonify({"ok": False, "error": f"bad JSON: {exc}"}), 400
        action = str(payload.get("action", "")).upper()
        wrong_pitch = (payload.get("wrong_pitch") or "").strip() or None
        actual_label = (payload.get("actual_label") or "").strip() or None

        detections = _load_detections(bench, cell_id)
        if idx < 0 or idx >= len(detections):
            return jsonify({"ok": False, "error": f"detection index {idx} out of range"}), 400
        det = detections[idx]

        state = _load_verdict_state(bench, cell_id)
        verdicts_by_id = {v["detection_id"]: v for v in state["verdicts"]}
        v = verdicts_by_id.get(det["id"])
        if v is None:
            v = {"detection_id": det["id"], "smufl_name": det["smufl_name"], "verdict": ""}
            state["verdicts"].append(v)
            verdicts_by_id[det["id"]] = v

        if action == "TP":
            v["verdict"] = "TP"
            v.pop("wrong_pitch", None)
        elif action == "FP":
            v["verdict"] = "FP"
            v.pop("wrong_pitch", None)
        elif action == "UNSURE":
            v["verdict"] = "unsure"
            v.pop("wrong_pitch", None)
        elif action == "WP":
            if not wrong_pitch:
                return jsonify({"ok": False, "error": "wrong_pitch required for action WP"}), 400
            v["verdict"] = "TP"
            v["wrong_pitch"] = wrong_pitch
        else:
            return jsonify({"ok": False, "error": f"unknown action {action!r}"}), 400

        # actual_label is only meaningful for FP (matcher's category is wrong).
        # On TP/WP/UNSURE we drop it.
        if action == "FP" and actual_label:
            v["actual_label"] = actual_label
        else:
            v.pop("actual_label", None)

        # Re-validate + persist
        cleaned, errors = _validate_state(state, cell_id)
        bench.verdicts_dir.mkdir(parents=True, exist_ok=True)
        bench.verdict_json_path(cell_id).write_text(json.dumps(cleaned, indent=2))

        # Find the next unreviewed AFTER this one. Fall through to adjacent
        # next if everything is reviewed.
        nxt = _next_unreviewed_after(bench, cell_id, idx)
        if nxt is None:
            adj = _adjacent_queue_position(bench, cell_id, idx, "next")
            if adj:
                next_url = url_for("queue_one", cell_id=adj[0], idx=adj[1])
            else:
                next_url = "/"  # back to the index — all done
        else:
            next_url = url_for("queue_one", cell_id=nxt[0], idx=nxt[1])

        return jsonify({"ok": True, "errors": errors, "next_url": next_url})

    @app.route("/cells/<cell_id>/d/<int:idx>/crop.png")
    def detection_crop(cell_id: str, idx: int):
        manifest = bench.load_manifest()
        entry = next((e for e in manifest if e["cell_id"] == cell_id), None)
        if entry is None:
            abort(404)
        cell_png_rel = entry.get("cell_png_path", "")
        # Manifest paths are repo-relative; resolve them from the project root
        # (which is the parent of `benchmarks/`).
        cell_png = Path(cell_png_rel)
        if not cell_png.is_absolute():
            # Try resolving relative to repo root (= parent of bench.root.parent)
            candidate = bench.root.parent.parent / cell_png
            if not candidate.exists():
                # Fallback: relative to bench.root itself (older format)
                candidate = bench.root / cell_png
            cell_png = candidate
        if not cell_png.exists():
            abort(404, f"cell PNG missing: {cell_png}")
        detections = _load_detections(bench, cell_id)
        if idx < 0 or idx >= len(detections):
            abort(404)
        png = _detection_crop_png(cell_png, detections[idx])
        return Response(png, mimetype="image/png")

    @app.route("/score")
    def score():
        if not bench.manifest_path.exists():
            return _page("Score",
                         "<p>No manifest at "
                         f"<code>{bench.manifest_path}</code>.</p>")
        out_dir = bench.results_dir
        try:
            run_scorer(
                verdicts_dir=bench.verdicts_dir,
                out_dir=out_dir,
                detections_dir=bench.detections_dir,
                manifest_path=bench.manifest_path,
            )
        except Exception as exc:  # noqa: BLE001
            return _page("Score",
                         f"<h2>Scorer failed</h2><pre>{exc}</pre>")
        report = (out_dir / "report.md").read_text()
        # Render as <pre> (cheap, no markdown deps).
        return _page(
            "Score report",
            f"<p><a class='btn' href='/'>← back</a></p><pre>{_html_escape(report)}</pre>",
        )

    return app


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-dir", default="benchmarks/omr-phase2.5")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5050)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    app = create_app(args.bench_dir)
    print(f"serving {args.bench_dir} → http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
