"""Second-opinion reconciliation of clef + time signature against oemer.

The local YOLO pipeline is strong at *detecting* glyphs but weak at two
contextual reads: time signature (digits get misclassified, and an x=0
instrument number gets mistaken for a meter) and clef state (a clef change
or a per-system clef role doesn't always propagate). Those are exactly the
fields an *end-to-end* model reads in context.

This module runs BreezeWhite's `oemer` (MIT, CPU via onnxruntime, no GPU) on
a page image and diffs its clef / time-signature reading against our
pipeline's `.omr.json`. Disagreements are the measures a human should look
at first. oemer is a *second opinion*, not ground truth — treat a mismatch
as "check this," not "oemer is right."

Host-side only (like `maestro_bridge`): oemer isn't installed in the backend
Docker image. Runs against the standalone `tools.omr` pipeline output.

Install (tested with oemer 0.1.8 on Apple Silicon / CPU):
    pip install --no-deps oemer==0.1.8
The `--no-deps` is required: oemer's default pin pulls `onnxruntime-gpu`,
which has no CPU / Apple-Silicon wheel. The CPU `onnxruntime` package
provides the same `onnxruntime` module oemer imports.

Scope note: reliable on single-system-per-page music (leadsheet, piano,
small ensemble) — the same shape oemer handles well. Dense orchestral
conductor scores are best-effort; oemer often mis-segments many staves, so
treat orchestral clef alignment as advisory and lean on the page-level
time-signature comparison there.

CLI
---
    # Diff two files directly (fast; no model run):
    python3 -m tools.omr.oemer_second_opinion \
        --omr-json out.omr.json --page 0 --oemer-xml page0.oemer.musicxml

    # From a PDF page: render it, run oemer, diff against an existing omr.json:
    python3 -m tools.omr.oemer_second_opinion \
        --pdf score.pdf --page 0 --omr-json out.omr.json

    # Diff two MusicXML files (e.g. pipeline export vs oemer):
    python3 -m tools.omr.oemer_second_opinion \
        --pipeline-xml pipeline.musicxml --oemer-xml page0.oemer.musicxml
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Default location of the oemer console script (pip user-install on macOS).
# Override with OEMER_BIN. We call the script rather than importing so each
# run gets a clean process (oemer keeps global prediction state).
DEFAULT_OEMER_BIN = os.environ.get(
    "OEMER_BIN",
    str(Path.home() / "Library/Python/3.9/bin/oemer"),
)


# --------------------------------------------------------------------------- #
# Normalized summary structures
# --------------------------------------------------------------------------- #
@dataclass
class PartTimeline:
    """Clef / time-signature change-points for one staff (top-to-bottom)."""
    index: int
    n_measures: int = 0
    # (measure_number, token) at each point the value *changes*.
    clef_changes: list[tuple[int, str]] = field(default_factory=list)
    time_changes: list[tuple[int, str]] = field(default_factory=list)

    @property
    def initial_clef(self) -> Optional[str]:
        return self.clef_changes[0][1] if self.clef_changes else None

    @property
    def initial_time(self) -> Optional[str]:
        return self.time_changes[0][1] if self.time_changes else None


@dataclass
class Summary:
    source: str            # "pipeline" | "oemer"
    parts: list[PartTimeline] = field(default_factory=list)

    @property
    def n_parts(self) -> int:
        return len(self.parts)

    def global_time_changes(self) -> list[tuple[int, str]]:
        """Meter is usually global; return the first part that carries one."""
        for p in self.parts:
            if p.time_changes:
                return p.time_changes
        return []


# --------------------------------------------------------------------------- #
# Normalization: clefs and time signatures -> canonical tokens
# --------------------------------------------------------------------------- #
# music21 (sign, line, octaveChange) -> our pipeline's clef vocabulary.
_M21_CLEF = {
    ("G", 2, 0): "treble",
    ("G", 2, -1): "treble_8vb",
    ("G", 2, 1): "treble_8va",
    ("F", 4, 0): "bass",
    ("F", 4, -1): "bass_8vb",
    ("F", 4, 1): "bass_8va",
    ("C", 3, 0): "alto",
    ("C", 4, 0): "tenor",
    ("C", 1, 0): "soprano",
    ("percussion", None, 0): "percussion",
}


def _clef_token_from_m21(clef) -> str:
    sign = getattr(clef, "sign", None)
    line = getattr(clef, "line", None)
    oc = int(getattr(clef, "octaveChange", 0) or 0)
    tok = _M21_CLEF.get((sign, line, oc))
    if tok:
        return tok
    # Fall back to a raw descriptor so unknowns are visible, not silently dropped.
    base = f"{sign or '?'}{line if line is not None else ''}"
    return base + (f"{oc:+d}" if oc else "")


def _clef_token_from_pipeline(clef: Optional[str]) -> Optional[str]:
    # Pipeline already emits "treble" / "bass" / "alto" / "tenor" (+ octave
    # suffix like "_8vb"); keep as canonical token directly.
    return clef or None


def _ts_token(numerator: Any, denominator: Any) -> Optional[str]:
    try:
        return f"{int(numerator)}/{int(denominator)}"
    except (TypeError, ValueError):
        return None


CLEF_LABEL = {
    "treble": "treble", "bass": "bass", "alto": "alto", "tenor": "tenor",
    "treble_8vb": "treble 8vb", "treble_8va": "treble 8va",
    "bass_8vb": "bass 8vb", "percussion": "perc.",
}


def _pretty_clef(tok: Optional[str]) -> str:
    if tok is None:
        return "(none)"
    return CLEF_LABEL.get(tok, tok)


# --------------------------------------------------------------------------- #
# Build a Summary from oemer / pipeline output
# --------------------------------------------------------------------------- #
def _push_change(changes: list[tuple[int, str]], measure: int, value: Optional[str]) -> None:
    """Record `value` at `measure` only if it differs from the last recorded."""
    if value is None:
        return
    if not changes or changes[-1][1] != value:
        changes.append((measure, value))


def summarize_musicxml(path: str | Path, source: str = "oemer") -> Summary:
    """Summarize any MusicXML file (used for oemer output, or a pipeline export)."""
    import music21 as m21  # local import: heavy, host-side only

    score = m21.converter.parse(str(path))
    parts_iter = list(score.parts) or [score]  # flat scores expose no .parts
    summ = Summary(source=source)
    for pi, part in enumerate(parts_iter):
        tl = PartTimeline(index=pi)
        measures = list(part.getElementsByClass("Measure"))
        tl.n_measures = len(measures)
        for meas in measures:
            mn = meas.measureNumber
            for c in meas.getElementsByClass(m21.clef.Clef):
                _push_change(tl.clef_changes, mn, _clef_token_from_m21(c))
            for ts in meas.getElementsByClass(m21.meter.TimeSignature):
                _push_change(tl.time_changes, mn, ts.ratioString)
        summ.parts.append(tl)
    return summ


def summarize_omr_json(obj: dict | str | Path, page: int = 0) -> Summary:
    """Summarize one page of a pipeline `.omr.json` result.

    Staves are grouped by `staff_index` (role) across systems on the page and
    their measures concatenated in system order, so each PartTimeline follows
    one instrument row left-to-right. `time_signature: null` means "not seen
    yet" — we carry the last-known value forward (via _push_change dedup).
    """
    if isinstance(obj, (str, Path)):
        obj = json.loads(Path(obj).read_text())
    pages = obj.get("pages", [])
    if page >= len(pages):
        raise IndexError(f"omr.json has {len(pages)} page(s); page {page} requested")
    pg = pages[page]

    # role (staff_index) -> list of (system_index, staff_dict)
    by_role: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for sysm in pg.get("systems", []):
        si = sysm.get("system_index", 0)
        for staff in sysm.get("staves", []):
            by_role[staff.get("staff_index", 0)].append((si, staff))

    summ = Summary(source="pipeline")
    for out_idx, role in enumerate(sorted(by_role)):
        entries = sorted(by_role[role], key=lambda e: e[0])
        tl = PartTimeline(index=out_idx)
        mnum = 0
        # Seed from the first staff's staff-level effective state.
        first_staff = entries[0][1]
        _push_change(tl.clef_changes, 1, _clef_token_from_pipeline(first_staff.get("clef")))
        ts0 = first_staff.get("time_signature")
        if ts0:
            _push_change(tl.time_changes, 1, _ts_token(ts0.get("numerator"), ts0.get("denominator")))
        for _si, staff in entries:
            for meas in staff.get("measures", []):
                mnum += 1
                _push_change(tl.clef_changes, mnum,
                             _clef_token_from_pipeline(meas.get("clef")))
                ts = meas.get("time_signature")
                if ts:
                    _push_change(tl.time_changes, mnum,
                                 _ts_token(ts.get("numerator"), ts.get("denominator")))
        tl.n_measures = mnum
        summ.parts.append(tl)
    return summ


# --------------------------------------------------------------------------- #
# Diff
# --------------------------------------------------------------------------- #
def diff_summaries(pipeline: Summary, oemer: Summary) -> dict:
    """Compare clef (per staff) and time signature (global) between sources."""
    report: dict[str, Any] = {
        "n_parts": {"pipeline": pipeline.n_parts, "oemer": oemer.n_parts},
        "part_count_match": pipeline.n_parts == oemer.n_parts,
        "time_signature": _diff_time(pipeline, oemer),
        "clef_presence": _diff_clef_presence(pipeline, oemer),
        "clefs": _diff_clefs(pipeline, oemer),
    }
    ts = report["time_signature"]
    cl = report["clefs"]
    report["summary"] = {
        "time_sig_agree": ts["verdict"] == "agree",
        "clef_mismatches": sum(1 for c in cl if c["verdict"] == "disagree"),
        "clef_supplied_by_oemer": sum(1 for c in cl if c["verdict"] == "only_oemer"),
    }
    return report


def _clef_presence(summ: Summary) -> set[str]:
    """Distinct clef tokens seen anywhere on the page (alignment-free)."""
    seen: set[str] = set()
    for p in summ.parts:
        for _m, tok in p.clef_changes:
            seen.add(tok)
    return seen


def _diff_clef_presence(pipeline: Summary, oemer: Summary) -> dict:
    """Do both tools agree on *which* clefs appear? Robust to part mis-alignment.

    On grand-staff / multi-system pages the two tools often disagree on how
    many parts exist (oemer tends to collapse a grand staff into one stream),
    so per-staff clef matching is unreliable there. This set comparison still
    answers "did oemer see the same clef types the pipeline did?".
    """
    p, o = _clef_presence(pipeline), _clef_presence(oemer)
    return {
        "pipeline": sorted(p),
        "oemer": sorted(o),
        "agree": p == o,
        "only_pipeline": sorted(p - o),
        "only_oemer": sorted(o - p),
    }


def _diff_time(pipeline: Summary, oemer: Summary) -> dict:
    p = pipeline.global_time_changes()
    o = oemer.global_time_changes()
    p_init = p[0][1] if p else None
    o_init = o[0][1] if o else None
    if p_init is None and o_init is None:
        verdict = "both_none"
    elif p_init is None:
        verdict = "only_oemer"     # oemer supplies a meter the pipeline missed
    elif o_init is None:
        verdict = "only_pipeline"
    elif p_init == o_init:
        verdict = "agree"
    else:
        verdict = "disagree"
    return {
        "verdict": verdict,
        "pipeline_initial": p_init,
        "oemer_initial": o_init,
        "pipeline_changes": p,
        "oemer_changes": o,
    }


def _diff_clefs(pipeline: Summary, oemer: Summary) -> list[dict]:
    rows: list[dict] = []
    n = max(pipeline.n_parts, oemer.n_parts)
    for i in range(n):
        pp = pipeline.parts[i] if i < pipeline.n_parts else None
        oo = oemer.parts[i] if i < oemer.n_parts else None
        p_clef = pp.initial_clef if pp else None
        o_clef = oo.initial_clef if oo else None
        if p_clef is None and o_clef is None:
            verdict = "both_none"
        elif p_clef is None:
            verdict = "only_oemer"
        elif o_clef is None:
            verdict = "only_pipeline"
        elif p_clef == o_clef:
            verdict = "agree"
        else:
            verdict = "disagree"
        rows.append({
            "staff": i,
            "verdict": verdict,
            "pipeline_clef": p_clef,
            "oemer_clef": o_clef,
            # Extra detail: clef changes each source reports for this staff.
            "pipeline_clef_changes": pp.clef_changes if pp else [],
            "oemer_clef_changes": oo.clef_changes if oo else [],
        })
    return rows


# --------------------------------------------------------------------------- #
# Human-readable report
# --------------------------------------------------------------------------- #
_MARK = {"agree": "OK ", "disagree": "!! ", "only_oemer": "+? ",
         "only_pipeline": "-? ", "both_none": "   "}


def render_report(report: dict) -> str:
    L: list[str] = []
    L.append("=" * 66)
    L.append("  oemer second opinion — clef / time signature reconciliation")
    L.append("=" * 66)
    npp, noo = report["n_parts"]["pipeline"], report["n_parts"]["oemer"]
    L.append(f"staves:  pipeline={npp}  oemer={noo}"
             + ("" if report["part_count_match"] else "   (count differs — clef alignment by order is approximate)"))
    L.append("")

    ts = report["time_signature"]
    L.append("TIME SIGNATURE")
    L.append(f"  {_MARK[ts['verdict']]}pipeline={ts['pipeline_initial'] or '(none)'}"
             f"   oemer={ts['oemer_initial'] or '(none)'}   [{ts['verdict']}]")
    if ts["verdict"] == "only_oemer":
        L.append("      -> pipeline read no meter; oemer suggests one. Worth checking.")
    elif ts["verdict"] == "disagree":
        L.append("      -> sources disagree on the meter. Check the barline.")
    if len(ts["pipeline_changes"]) > 1 or len(ts["oemer_changes"]) > 1:
        L.append(f"      pipeline changes: {ts['pipeline_changes']}")
        L.append(f"      oemer changes:    {ts['oemer_changes']}")
    L.append("")

    cp = report["clef_presence"]
    L.append("CLEFS PRESENT ON PAGE (alignment-free — the reliable clef signal)")
    mark = "OK " if cp["agree"] else "!! "
    L.append(f"  {mark}pipeline={[_pretty_clef(t) for t in cp['pipeline']] or '(none)'}"
             f"   oemer={[_pretty_clef(t) for t in cp['oemer']] or '(none)'}")
    if cp["only_pipeline"]:
        L.append(f"      only pipeline saw: {[_pretty_clef(t) for t in cp['only_pipeline']]}")
    if cp["only_oemer"]:
        L.append(f"      only oemer saw:    {[_pretty_clef(t) for t in cp['only_oemer']]}"
                 "  (a clef the pipeline may have missed)")
    L.append("")

    per_staff_note = "" if report["part_count_match"] else \
        "  (part counts differ — treat per-staff rows as approximate; trust the presence check above)"
    L.append("CLEFS (by staff, top to bottom)" + per_staff_note)
    for row in report["clefs"]:
        L.append(f"  {_MARK[row['verdict']]}staff {row['staff']}: "
                 f"pipeline={_pretty_clef(row['pipeline_clef']):<12} "
                 f"oemer={_pretty_clef(row['oemer_clef']):<12} [{row['verdict']}]")
        # Surface mid-staff clef changes (the clef-reset weakness).
        for label, changes in (("pipeline", row["pipeline_clef_changes"]),
                               ("oemer", row["oemer_clef_changes"])):
            if len(changes) > 1:
                pretty = ", ".join(f"m{m}:{_pretty_clef(t)}" for m, t in changes)
                L.append(f"        {label} clef changes: {pretty}")
    L.append("")

    s = report["summary"]
    L.append("-" * 66)
    L.append(f"  time signature: {'AGREE' if s['time_sig_agree'] else 'CHECK'}"
             f"   |   clef mismatches: {s['clef_mismatches']}"
             f"   |   clefs only oemer saw: {s['clef_supplied_by_oemer']}")
    L.append("-" * 66)
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# Running oemer / rendering a page
# --------------------------------------------------------------------------- #
def render_pdf_page(pdf: str | Path, page: int, out_png: str | Path, dpi: int = 200) -> Path:
    import fitz  # PyMuPDF, a pipeline dependency

    doc = fitz.open(str(pdf))
    pix = doc[page].get_pixmap(dpi=dpi)
    out_png = Path(out_png)
    pix.save(str(out_png))
    return out_png


def _pad_white_border(image_path: str | Path, out_path: str | Path,
                      frac: float = 0.06) -> Path:
    """Add a white margin so no glyph touches the edge.

    Guards an oemer edge bug where its augmentation-dot scan indexes one pixel
    past the right border when a note sits at the edge
    (`IndexError: ... out of bounds` in rhythm_extraction, seen on 0.1.5).
    A margin also just helps oemer's staff detection, so keep it on any version.
    """
    from PIL import Image

    im = Image.open(str(image_path)).convert("RGB")
    w, h = im.size
    m = int(max(w, h) * frac)
    canvas = Image.new("RGB", (w + 2 * m, h + 2 * m), (255, 255, 255))
    canvas.paste(im, (m, m))
    out_path = Path(out_path)
    canvas.save(str(out_path))
    return out_path


def run_oemer(image_path: str | Path, out_xml: str | Path,
              oemer_bin: str = DEFAULT_OEMER_BIN, timeout: int = 900,
              pad_frac: float = 0.06) -> Path:
    out_xml = Path(out_xml)
    if not Path(oemer_bin).exists():
        raise FileNotFoundError(
            f"oemer not found at {oemer_bin}. `pip install oemer` or set OEMER_BIN.")
    src = image_path
    if pad_frac > 0:
        src = _pad_white_border(image_path, out_xml.with_suffix(".padded.png"), pad_frac)
    proc = subprocess.run(
        [oemer_bin, str(src), "-o", str(out_xml)],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0 or not out_xml.exists():
        raise RuntimeError(
            f"oemer failed (exit {proc.returncode}).\n"
            f"stderr tail:\n{proc.stderr[-1500:]}")
    return out_xml


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _build_pipeline_summary(args) -> Summary:
    if args.pipeline_xml:
        return summarize_musicxml(args.pipeline_xml, source="pipeline")
    if args.omr_json:
        return summarize_omr_json(args.omr_json, page=args.page)
    raise SystemExit("Provide --omr-json (a pipeline result) or --pipeline-xml.")


def _build_oemer_summary(args, scratch: Path) -> Summary:
    oemer_xml = args.oemer_xml
    if oemer_xml is None:
        if not args.pdf:
            raise SystemExit("Provide --oemer-xml, or --pdf to run oemer live.")
        png = render_pdf_page(args.pdf, args.page, scratch / "page.png", dpi=args.dpi)
        print(f"[oemer] rendered page {args.page} -> {png}", file=sys.stderr)
        print("[oemer] running (CPU; a few minutes on a dense page)...", file=sys.stderr)
        oemer_xml = run_oemer(png, scratch / "page.oemer.musicxml", timeout=args.timeout)
        print(f"[oemer] wrote {oemer_xml}", file=sys.stderr)
    return summarize_musicxml(oemer_xml, source="oemer")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--omr-json", help="Pipeline .omr.json result (pipeline side).")
    ap.add_argument("--pipeline-xml", help="Pipeline MusicXML export (alt pipeline side).")
    ap.add_argument("--oemer-xml", help="Existing oemer MusicXML (skip running oemer).")
    ap.add_argument("--pdf", help="Score PDF; render --page and run oemer on it.")
    ap.add_argument("--page", type=int, default=0, help="0-based page index (default 0).")
    ap.add_argument("--dpi", type=int, default=200, help="Render DPI for oemer (default 200).")
    ap.add_argument("--timeout", type=int, default=900, help="oemer timeout seconds.")
    ap.add_argument("--json-out", help="Also write the raw diff report as JSON here.")
    ap.add_argument("--scratch", default=None, help="Scratch dir for renders/oemer output.")
    args = ap.parse_args(argv)

    scratch = Path(args.scratch or (Path(args.omr_json or args.pipeline_xml or ".").parent / "oemer_scratch"))
    scratch.mkdir(parents=True, exist_ok=True)

    pipeline = _build_pipeline_summary(args)
    oemer = _build_oemer_summary(args, scratch)
    report = diff_summaries(pipeline, oemer)
    print(render_report(report))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2))
        print(f"\n[report] JSON -> {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
