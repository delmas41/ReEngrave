"""Parse filled verdict markdowns and produce a P/R/F1 report.

Reads:
    verdicts/<cell_id>.md  — human-filled verdict templates
    detections/<cell_id>.json — original matcher output (smufl_name, category, pitch, conf)

Writes:
    results/report.md         — human-readable summary
    results/per_cell.csv      — one row per cell
    results/per_detection.csv — one row per detection (with verdict)
    results/summary.json      — machine-readable summary

Verdicts the parser understands (case-insensitive, first word wins):
    TP                  true positive
    FP                  false positive
    WRONG_PITCH         right location, wrong pitch (only applies to noteheads)
    UNSURE / SKIP / ??  not yet decided — counted as "pending"
    (blank or "__")     pending

If the verdict line still contains a literal underscore placeholder (`__`),
the detection is counted as pending and excluded from the P/R math.

Missed noteheads (FN) are parsed from lines like:
    FN1 at (x=123, y=456) → pitch=C4
    - FN at (x=__, y=__) → pitch=__         <- placeholder, ignored

CLI:
    python3 -m tools.omr.annotate.score \\
        --verdicts-dir benchmarks/omr-phase2.5/verdicts \\
        --detections-dir benchmarks/omr-phase2.5/detections \\
        --out-dir benchmarks/omr-phase2.5/results
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------


# Detection line, e.g.:
#   - [ ] D0  noteheadBlack (notehead) at (x=82, y=445) → D4  conf=0.83
#          verdict: TP
# (the verdict shows up on the next non-blank line beginning with "verdict:")
_DET_RX = re.compile(
    r"^\s*-\s*\[[ x]\]\s*"             # checkbox
    r"(D\d+)"                          # detection id
    r"\s+(\S+)"                        # smufl_name
    r"\s+\((\w+)\)"                    # (category)
    r"\s+at\s+\(x=(-?\d+),\s*y=(-?\d+)\)"
    r"(?:\s*→\s*([A-Ga-g][#b]?\d))?"   # optional pitch
    r"\s+conf=([0-9.]+)"
)
_VERDICT_RX = re.compile(r"verdict:\s*(.+?)\s*$", re.IGNORECASE)

# "FN1 at (x=123, y=456) → pitch=C4" — anywhere in a line
_FN_RX = re.compile(
    r"FN\d*\s+at\s+\(x=(-?\d+),\s*y=(-?\d+)\)"
    r"(?:\s*→\s*pitch=([A-Ga-g][#b]?\d))?",
    re.IGNORECASE,
)
# "D0 → correct pitch is C4"
_WP_RX = re.compile(
    r"(D\d+)\s*(?:→|->)\s*correct\s+pitch\s+is\s+([A-Ga-g][#b]?\d)",
    re.IGNORECASE,
)


@dataclass
class DetectionVerdict:
    id: str
    smufl_name: str
    category: str
    x: int
    y: int
    pitch: str | None
    confidence: float
    verdict: str          # raw verdict text (lowercased, stripped) or "" if pending
    reason: str           # any trailing word(s) after the verdict keyword

    @property
    def is_pending(self) -> bool:
        if not self.verdict:
            return True
        v = self.verdict.lower()
        return v.startswith("__") or v in {"unsure", "skip", "?", "??"}

    @property
    def classification(self) -> str:
        """One of: 'tp', 'fp', 'wrong_pitch', 'pending'."""
        if self.is_pending:
            return "pending"
        v = self.verdict.lower().split()[0]
        if v in {"tp", "true", "correct"}:
            return "tp"
        if v in {"fp", "false", "wrong"}:
            return "fp"
        if v in {"wrong_pitch", "wrong-pitch", "wrongpitch"}:
            return "wrong_pitch"
        # Unknown verdict text → treat as pending so it's surfaced.
        return "pending"


@dataclass
class MissedNotehead:
    x: int
    y: int
    pitch: str | None = None


@dataclass
class ParsedVerdictFile:
    cell_id: str
    detections: list[DetectionVerdict] = field(default_factory=list)
    missed_noteheads: list[MissedNotehead] = field(default_factory=list)
    wrong_pitch_corrections: dict[str, str] = field(default_factory=dict)


def parse_verdict_markdown(text: str, cell_id: str | None = None) -> ParsedVerdictFile:
    """Parse the verdict markdown produced by build_template.

    Handles partial fills (returns DetectionVerdict with verdict='' for any
    detection whose verdict line is still the placeholder).
    """
    lines = text.splitlines()
    cid = cell_id

    # Pull cell_id from first header line if not given.
    if cid is None:
        for ln in lines[:5]:
            m = re.match(r"^#\s*Cell\s+([\S]+)", ln)
            if m:
                cid = m.group(1)
                break
        if cid is None:
            cid = "unknown"

    parsed = ParsedVerdictFile(cell_id=cid)

    # We allow the verdict to appear on the same line OR up to a few lines later.
    # State machine: when we see a detection line, look ahead for the next
    # verdict: line before another detection line.
    pending: DetectionVerdict | None = None
    in_code_fence = False

    def _flush():
        nonlocal pending
        if pending is not None:
            parsed.detections.append(pending)
            pending = None

    for ln in lines:
        # Track fenced code blocks. Lines inside ``` ... ``` are documentation
        # examples (e.g. "D0 → correct pitch is C4") that the build_template
        # writes as instructions to the user. We must not parse them as real
        # verdict data.
        if ln.lstrip().startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        # Detection line?
        m = _DET_RX.search(ln)
        if m:
            _flush()
            did, smufl, cat, x, y, pitch, conf = m.groups()
            pending = DetectionVerdict(
                id=did, smufl_name=smufl, category=cat,
                x=int(x), y=int(y), pitch=pitch, confidence=float(conf),
                verdict="", reason="",
            )
            # Verdict might be on the same line.
            vm = _VERDICT_RX.search(ln)
            if vm:
                _attach_verdict(pending, vm.group(1))
            continue

        # Verdict line for the most recent detection?
        if pending is not None and pending.verdict == "":
            vm = _VERDICT_RX.search(ln)
            if vm:
                _attach_verdict(pending, vm.group(1))
                continue

        # FN line?
        for fm in _FN_RX.finditer(ln):
            x_str, y_str, pitch = fm.groups()
            if "__" in x_str or "__" in y_str:
                continue
            try:
                x_i, y_i = int(x_str), int(y_str)
            except ValueError:
                continue
            parsed.missed_noteheads.append(MissedNotehead(x=x_i, y=y_i, pitch=pitch))

        # Wrong-pitch correction line?
        for wm in _WP_RX.finditer(ln):
            did, pitch = wm.groups()
            parsed.wrong_pitch_corrections[did] = pitch

    _flush()
    return parsed


def _attach_verdict(det: DetectionVerdict, raw: str) -> None:
    """Set det.verdict + det.reason from a verdict cell, but only if the
    user actually filled it in (i.e. not still the underscore placeholder)."""
    raw = raw.strip()
    if not raw or raw.startswith("_"):
        det.verdict = ""
        det.reason = ""
        return
    # The first token is the verdict keyword; the rest is the reason.
    parts = raw.split(maxsplit=1)
    det.verdict = parts[0].strip().lower()
    det.reason = parts[1].strip() if len(parts) > 1 else ""


# ---------------------------------------------------------------------------
# Scoring math
# ---------------------------------------------------------------------------


@dataclass
class CellScore:
    cell_id: str
    source_tag: str

    # Detection counts (post-pending-filter)
    n_total_detections: int = 0
    n_pending: int = 0

    # Location-correctness (TP+WRONG_PITCH = right location)
    n_loc_tp: int = 0    # right location (TP or WRONG_PITCH)
    n_fp: int = 0
    n_fn: int = 0        # missed noteheads from the FN block

    # Pitch-correctness (only for noteheads with right location)
    n_pitch_correct: int = 0   # TP that are noteheads
    n_pitch_wrong: int = 0     # WRONG_PITCH or noteheads where verdict==fp due to pitch

    # Per-category breakdown (location-level)
    per_category: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def precision(self) -> float | None:
        denom = self.n_loc_tp + self.n_fp
        return self.n_loc_tp / denom if denom else None

    @property
    def recall(self) -> float | None:
        denom = self.n_loc_tp + self.n_fn
        return self.n_loc_tp / denom if denom else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def notehead_pitch_accuracy(self) -> float | None:
        denom = self.n_pitch_correct + self.n_pitch_wrong
        return self.n_pitch_correct / denom if denom else None


def score_cell(parsed: ParsedVerdictFile, source_tag: str = "") -> CellScore:
    cs = CellScore(cell_id=parsed.cell_id, source_tag=source_tag)
    cs.n_total_detections = len(parsed.detections)
    cs.n_fn = len(parsed.missed_noteheads)

    for d in parsed.detections:
        cls = d.classification
        cat = d.category or "unknown"
        bucket = cs.per_category.setdefault(cat, {"tp": 0, "fp": 0, "pending": 0})

        if cls == "pending":
            cs.n_pending += 1
            bucket["pending"] += 1
            continue

        if cls == "tp":
            cs.n_loc_tp += 1
            bucket["tp"] += 1
            if cat == "notehead":
                cs.n_pitch_correct += 1
        elif cls == "wrong_pitch":
            # Right location, wrong pitch — counts as location-TP but pitch-wrong.
            cs.n_loc_tp += 1
            bucket["tp"] += 1
            if cat == "notehead":
                cs.n_pitch_wrong += 1
        elif cls == "fp":
            cs.n_fp += 1
            bucket["fp"] += 1
    return cs


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _aggregate(cells: list[CellScore]) -> dict:
    n_loc_tp = sum(c.n_loc_tp for c in cells)
    n_fp = sum(c.n_fp for c in cells)
    n_fn = sum(c.n_fn for c in cells)
    n_pending = sum(c.n_pending for c in cells)
    n_total = sum(c.n_total_detections for c in cells)
    n_pitch_correct = sum(c.n_pitch_correct for c in cells)
    n_pitch_wrong = sum(c.n_pitch_wrong for c in cells)

    p = n_loc_tp / (n_loc_tp + n_fp) if (n_loc_tp + n_fp) else None
    r = n_loc_tp / (n_loc_tp + n_fn) if (n_loc_tp + n_fn) else None
    f1 = (2 * p * r / (p + r)) if (p and r and (p + r)) else None
    pitch_acc = (n_pitch_correct / (n_pitch_correct + n_pitch_wrong)
                 if (n_pitch_correct + n_pitch_wrong) else None)

    # Category aggregation.
    cats: dict[str, dict[str, int]] = {}
    for c in cells:
        for cat, counts in c.per_category.items():
            agg = cats.setdefault(cat, {"tp": 0, "fp": 0, "pending": 0})
            for k, v in counts.items():
                agg[k] += v

    return {
        "cells": len(cells),
        "n_total_detections": n_total,
        "n_pending": n_pending,
        "n_tp": n_loc_tp,
        "n_fp": n_fp,
        "n_fn": n_fn,
        "precision": p,
        "recall": r,
        "f1": f1,
        "notehead_pitch_correct": n_pitch_correct,
        "notehead_pitch_wrong": n_pitch_wrong,
        "notehead_pitch_accuracy": pitch_acc,
        "per_category": cats,
    }


def _fmt_pct(v: float | None) -> str:
    return "—" if v is None else f"{v * 100:.1f}%"


def _fmt_count(v: int | None) -> str:
    return "—" if v is None else str(v)


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render_report(
    cells: list[CellScore],
    per_piece: dict[str, dict],
    overall: dict,
    n_cells_total: int,
    n_cells_with_any_verdicts: int,
) -> str:
    out: list[str] = []
    out.append("# Phase 2.5 — template matcher scoring report")
    out.append("")
    out.append(f"- Manifest cells: **{n_cells_total}**")
    out.append(f"- Cells with at least one filled verdict: **{n_cells_with_any_verdicts}**")
    out.append(f"- Total detections in scored cells: {overall['n_total_detections']}")
    out.append(f"- Pending (not yet verdict'd): {overall['n_pending']}")
    out.append("")
    out.append("## Overall")
    out.append("")
    out.append(f"- TP (right location): **{overall['n_tp']}**")
    out.append(f"- FP: **{overall['n_fp']}**")
    out.append(f"- FN (missed noteheads): **{overall['n_fn']}**")
    out.append(f"- Precision: **{_fmt_pct(overall['precision'])}**")
    out.append(f"- Recall: **{_fmt_pct(overall['recall'])}**")
    out.append(f"- F1: **{_fmt_pct(overall['f1'])}**")
    out.append(f"- Notehead pitch accuracy "
               f"(of correctly-located noteheads): "
               f"**{_fmt_pct(overall['notehead_pitch_accuracy'])}** "
               f"({overall['notehead_pitch_correct']} / "
               f"{overall['notehead_pitch_correct'] + overall['notehead_pitch_wrong']})")
    out.append("")
    out.append("## By category")
    out.append("")
    out.append("| Category | TP | FP | Pending | Precision |")
    out.append("|---|---|---|---|---|")
    for cat, counts in sorted(overall["per_category"].items()):
        denom = counts["tp"] + counts["fp"]
        prec = counts["tp"] / denom if denom else None
        out.append(f"| {cat} | {counts['tp']} | {counts['fp']} | "
                   f"{counts['pending']} | {_fmt_pct(prec)} |")
    out.append("")
    out.append("## By piece")
    out.append("")
    out.append("| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |")
    out.append("|---|---|---|---|---|---|---|---|")
    for tag, agg in sorted(per_piece.items()):
        out.append(f"| {tag} | {agg['cells']} | {agg['n_tp']} | "
                   f"{agg['n_fp']} | {agg['n_fn']} | "
                   f"{_fmt_pct(agg['precision'])} | "
                   f"{_fmt_pct(agg['recall'])} | "
                   f"{_fmt_pct(agg['f1'])} |")
    out.append("")
    out.append("## Per-cell")
    out.append("")
    out.append("| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for c in cells:
        out.append(
            f"| {c.cell_id} | {c.n_loc_tp} | {c.n_fp} | {c.n_fn} | "
            f"{c.n_pending} | "
            f"{_fmt_pct(c.precision)} | {_fmt_pct(c.recall)} | "
            f"{_fmt_pct(c.f1)} | "
            f"{_fmt_pct(c.notehead_pitch_accuracy)} |"
        )
    out.append("")
    out.append("---")
    out.append("")
    out.append("_Precision = TP / (TP + FP)._  ")
    out.append("_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  ")
    out.append("_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Source-tag inference (so reports can group WTC vs Beethoven)
# ---------------------------------------------------------------------------


def _source_tag_from_cell_id(cid: str) -> str:
    """Cell ids look like `wtc-p5-sys0-s0-m1`. Take everything up to the
    first `-sys`."""
    if "-sys" in cid:
        return cid.split("-sys", 1)[0]
    parts = cid.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else cid


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_verdict_json(
    payload: dict,
    detections_by_id: dict[str, dict],
    cell_id: str | None = None,
) -> ParsedVerdictFile:
    """Parse a .verdict.json file (written by the web annotator) into the
    same ParsedVerdictFile shape the markdown parser produces.

    The web tool stores only per-detection verdicts (TP/FP/unsure) and FN
    noteheads — it does NOT duplicate the detection geometry. We pull
    smufl_name / category / x / y / pitch / confidence out of the matching
    record in `detections_by_id`.
    """
    cid = cell_id or payload.get("cell_id") or "unknown"
    parsed = ParsedVerdictFile(cell_id=cid)

    for row in payload.get("verdicts", []):
        did = row.get("detection_id", "")
        det = detections_by_id.get(did)
        if det is None:
            # The JSON references a detection we don't have on disk; skip
            # rather than fabricating coords.
            continue
        verdict_raw = (row.get("verdict") or "").strip()
        wp = (row.get("wrong_pitch") or "").strip()
        # Web verdict vocabulary: TP / FP / unsure / "". Map to the markdown
        # parser's lowercase form. wrong_pitch is captured separately and
        # routed through wrong_pitch_corrections.
        if verdict_raw.upper() == "TP" and wp:
            verdict_str = "wrong_pitch"
        elif verdict_raw.upper() == "TP":
            verdict_str = "tp"
        elif verdict_raw.upper() == "FP":
            verdict_str = "fp"
        elif verdict_raw.lower() == "unsure":
            verdict_str = "unsure"
        else:
            verdict_str = ""  # treated as pending

        parsed.detections.append(DetectionVerdict(
            id=did,
            smufl_name=det.get("smufl_name", ""),
            category=det.get("category", ""),
            x=int(det.get("x_center", det.get("x", 0)) or 0),
            y=int(det.get("y_center", det.get("y", 0)) or 0),
            pitch=det.get("pitch"),
            confidence=float(det.get("confidence", 0.0) or 0.0),
            verdict=verdict_str,
            reason="",
        ))
        if wp:
            parsed.wrong_pitch_corrections[did] = wp

    for fn in payload.get("fn_noteheads", []):
        try:
            x = int(fn.get("x_canonical"))
            y = int(fn.get("y_canonical"))
        except (TypeError, ValueError):
            continue
        pitch = (fn.get("pitch") or "") or None
        parsed.missed_noteheads.append(MissedNotehead(x=x, y=y, pitch=pitch))

    return parsed


def _detections_by_id(detections_dir: Path | None, cell_id: str) -> dict[str, dict]:
    if not detections_dir:
        return {}
    p = detections_dir / f"{cell_id}.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}
    return {d["id"]: d for d in data.get("detections", [])}


def _collect_parsed_verdicts(
    verdicts_dir: Path,
    detections_dir: Path | None,
) -> list[ParsedVerdictFile]:
    """Return one ParsedVerdictFile per cell, preferring .verdict.json over
    .md when both exist."""
    json_files = {p.name.removesuffix(".verdict.json"): p
                  for p in verdicts_dir.glob("*.verdict.json")}
    # .md files whose stem is not also a .verdict.json
    md_files = sorted(p for p in verdicts_dir.glob("*.md"))

    out: list[ParsedVerdictFile] = []
    seen: set[str] = set()

    for cid, jpath in sorted(json_files.items()):
        try:
            payload = json.loads(jpath.read_text())
        except json.JSONDecodeError:
            continue
        det_map = _detections_by_id(detections_dir, cid)
        parsed = parse_verdict_json(payload, det_map, cell_id=cid)
        out.append(parsed)
        seen.add(cid)

    for mp in md_files:
        cid = mp.stem
        if cid in seen:
            continue
        parsed = parse_verdict_markdown(mp.read_text(), cell_id=cid)
        out.append(parsed)
        seen.add(cid)

    return out


def run_scorer(
    verdicts_dir: Path,
    out_dir: Path,
    detections_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> dict:
    """Parse verdict files, score them, write the report.

    Reads both `<cell>.verdict.json` (written by the web annotator) and
    `<cell>.md` (legacy hand-filled). When both exist for a cell, the JSON
    wins — it represents the live state.

    `detections_dir` is used to resolve detection geometry for JSON verdicts
    (the JSON only stores ids + verdict labels, not coords). It is
    informational for markdown verdicts.
    `manifest_path` is used to count total cells for the "X of Y filled"
    line in the report.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    n_cells_total = len(list(verdicts_dir.glob("*.md")) +
                        list(verdicts_dir.glob("*.verdict.json")))
    if manifest_path and manifest_path.exists():
        try:
            n_cells_total = len(json.loads(manifest_path.read_text()))
        except json.JSONDecodeError:
            pass

    cells: list[CellScore] = []
    per_detection_rows: list[dict] = []

    for parsed in _collect_parsed_verdicts(verdicts_dir, detections_dir):
        # If literally no verdict was filled in for any detection AND no FNs
        # were added, skip — that's an untouched template.
        any_verdict = any(d.classification != "pending"
                          for d in parsed.detections)
        any_fn = bool(parsed.missed_noteheads)
        if not any_verdict and not any_fn:
            continue
        tag = _source_tag_from_cell_id(parsed.cell_id)
        cs = score_cell(parsed, source_tag=tag)
        cells.append(cs)
        for d in parsed.detections:
            per_detection_rows.append({
                "cell_id": parsed.cell_id,
                "source_tag": tag,
                "det_id": d.id,
                "smufl_name": d.smufl_name,
                "category": d.category,
                "x": d.x, "y": d.y,
                "pitch": d.pitch or "",
                "confidence": d.confidence,
                "verdict": d.classification,
                "reason": d.reason,
            })

    n_cells_with_any_verdicts = len(cells)

    overall = _aggregate(cells)
    # Per piece
    per_piece: dict[str, list[CellScore]] = {}
    for c in cells:
        per_piece.setdefault(c.source_tag, []).append(c)
    per_piece_agg = {tag: _aggregate(lst) for tag, lst in per_piece.items()}

    # Write CSVs.
    per_cell_csv = out_dir / "per_cell.csv"
    with per_cell_csv.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cell_id", "source_tag", "n_total", "n_pending",
                    "n_tp", "n_fp", "n_fn",
                    "precision", "recall", "f1",
                    "notehead_pitch_correct", "notehead_pitch_wrong",
                    "notehead_pitch_accuracy"])
        for c in cells:
            w.writerow([
                c.cell_id, c.source_tag, c.n_total_detections, c.n_pending,
                c.n_loc_tp, c.n_fp, c.n_fn,
                _fmt_or_blank(c.precision), _fmt_or_blank(c.recall),
                _fmt_or_blank(c.f1),
                c.n_pitch_correct, c.n_pitch_wrong,
                _fmt_or_blank(c.notehead_pitch_accuracy),
            ])

    per_det_csv = out_dir / "per_detection.csv"
    with per_det_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "cell_id", "source_tag", "det_id", "smufl_name", "category",
            "x", "y", "pitch", "confidence", "verdict", "reason",
        ])
        w.writeheader()
        for row in per_detection_rows:
            w.writerow(row)

    # Report.
    report = render_report(cells, per_piece_agg, overall,
                           n_cells_total=n_cells_total,
                           n_cells_with_any_verdicts=n_cells_with_any_verdicts)
    (out_dir / "report.md").write_text(report)
    (out_dir / "summary.json").write_text(json.dumps({
        "overall": overall,
        "per_piece": per_piece_agg,
        "n_cells_total": n_cells_total,
        "n_cells_with_any_verdicts": n_cells_with_any_verdicts,
    }, indent=2, default=_json_default))

    print(f"wrote {out_dir / 'report.md'}")
    print(f"wrote {per_cell_csv}")
    print(f"wrote {per_det_csv}")
    print(f"\n{n_cells_with_any_verdicts} of {n_cells_total} cells have verdicts.")
    print(f"  TP={overall['n_tp']}  FP={overall['n_fp']}  FN={overall['n_fn']}  pending={overall['n_pending']}")
    print(f"  precision={_fmt_pct(overall['precision'])}  "
          f"recall={_fmt_pct(overall['recall'])}  "
          f"f1={_fmt_pct(overall['f1'])}")
    return overall


def _fmt_or_blank(v: float | None) -> str:
    return "" if v is None else f"{v:.4f}"


def _json_default(o):
    # CellScore aggregator returns nested dicts of primitives already;
    # this helper only ever needs to handle Path or set-like things.
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"unserializable: {type(o)!r}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Score filled verdict markdowns and write a P/R report.")
    ap.add_argument("--verdicts-dir", default="benchmarks/omr-phase2.5/verdicts")
    ap.add_argument("--detections-dir", default="benchmarks/omr-phase2.5/detections")
    ap.add_argument("--manifest", default="benchmarks/omr-phase2.5/cells.json")
    ap.add_argument("--out-dir", default="benchmarks/omr-phase2.5/results")
    args = ap.parse_args()
    run_scorer(
        verdicts_dir=Path(args.verdicts_dir),
        out_dir=Path(args.out_dir),
        detections_dir=Path(args.detections_dir),
        manifest_path=Path(args.manifest),
    )


if __name__ == "__main__":
    main()
