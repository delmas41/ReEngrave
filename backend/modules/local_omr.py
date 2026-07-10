"""
Local OMR — runs the in-house `tools.omr` pipeline (YOLOv8l + classical CV)
in place of Audiveris.

Provides `run_local_omr(pdf_path, output_dir) -> LocalOmrResult`. The
caller stores the returned MusicXML on `Score.musicxml_path` and the
JSON path on `Score.metadata_json["omr_json_path"]` (consumed by
`export_module` to skip the lossy musicxml2ly hop on LilyPond export).

Phase 4 of the OMR work added rhythm parsing, chord voicing, and direct
LilyPond + MusicXML serializers (`tools.omr.export`). On 4/5 benchmark
PDFs the per-measure beat sums are within +/-0.5 of the time signature
(see benchmarks/omr-phase4-session/retrospective.md). The MusicXML this
emits is single-voice-per-part and OK enough to round-trip through
musicxml2ly for the existing export flow.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Path to the directory containing the `tools/` package.
#
# Two layouts to support:
#   * Docker (WORKDIR=/app, backend/ flattened):  /app/modules/local_omr.py
#                                                  → tools/ lives at /app/tools
#                                                  → parents[1] = /app
#   * Dev (backend/modules/local_omr.py inside repo):
#                                                  → tools/ lives at <repo>/tools
#                                                  → parents[2] = <repo>
def _find_omr_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[1], here.parents[2]):
        if (candidate / "tools" / "omr").is_dir():
            return candidate
    return here.parents[2]  # last-resort fallback


_REPO_ROOT = _find_omr_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LocalOmrResult:
    """Mirrors AudiverisResult so callers can swap engines without changes.

    The `omr_json_path` is unique to this engine — it points at the
    structured transcribe.py JSON, which the LilyPond exporter prefers
    over MusicXML when present (skips the lossy musicxml2ly hop).
    """
    musicxml_path: str
    omr_json_path: str
    confidence_score: float
    measures_count: int
    pages_processed: int = 0
    detections_total: int = 0
    runtime_seconds: float = 0.0
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _weights_path() -> str:
    """Resolve the YOLO weights path from env or fall back to the
    in-tree default.

    Local dev: docker-compose mounts the weights file as a volume at
    /app/tools/omr/training/data/weights/. In production, the same path
    should be populated either by a Docker volume or by downloading the
    file at container start.
    """
    env_path = os.getenv("OMR_WEIGHTS_PATH", "").strip()
    if env_path:
        return env_path
    # Fall back to the default the retrospective documented.
    return str(
        _REPO_ROOT
        / "tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
    )


def _max_pages() -> int:
    """How many pages of a PDF to transcribe in one job. OMR is slow
    (~10-30 s/page on CPU) — capping prevents the BG task from running
    for hours on a 200-page conductor's score.

    Override with OMR_MAX_PAGES env var.
    """
    try:
        return max(1, int(os.getenv("OMR_MAX_PAGES", "5")))
    except ValueError:
        return 5


def _conf_threshold() -> float:
    try:
        return float(os.getenv("OMR_CONF_THRESHOLD", "0.25"))
    except ValueError:
        return 0.25


def _imgsz() -> int:
    try:
        return int(os.getenv("OMR_IMGSZ", "1280"))
    except ValueError:
        return 1280


def _dpi() -> int:
    try:
        return int(os.getenv("OMR_DPI", "300"))
    except ValueError:
        return 300


async def run_local_omr(pdf_path: str, output_dir: str) -> LocalOmrResult:
    """Run the local OMR pipeline on `pdf_path` and write the
    transcribe.py JSON + a MusicXML file to `output_dir`.

    Heavy compute runs in a thread so the asyncio event loop isn't
    blocked. The thread does:
      1. PDF → transcribe.json (Phase 1 + YOLO + rhythm/pitch resolution)
      2. transcribe.json → MusicXML string via tools.omr.export.to_musicxml
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    weights = _weights_path()

    if not os.path.isfile(weights):
        return LocalOmrResult(
            musicxml_path="",
            omr_json_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=(
                f"OMR weights not found at {weights}. "
                "Place the file there or set OMR_WEIGHTS_PATH. "
                "See tools/omr/README.md for download instructions."
            ),
        )

    if not os.path.isfile(pdf_path):
        return LocalOmrResult(
            musicxml_path="",
            omr_json_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"PDF not found at {pdf_path}",
        )

    try:
        result = await asyncio.to_thread(
            _run_omr_blocking,
            pdf_path=pdf_path,
            output_dir=output_dir,
            weights=weights,
            max_pages=_max_pages(),
            conf_threshold=_conf_threshold(),
            imgsz=_imgsz(),
            dpi=_dpi(),
        )
        return result
    except Exception as exc:
        logger.exception("Local OMR failed for %s", pdf_path)
        return LocalOmrResult(
            musicxml_path="",
            omr_json_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Blocking worker (called via asyncio.to_thread)
# ---------------------------------------------------------------------------


def _run_omr_blocking(
    *,
    pdf_path: str,
    output_dir: str,
    weights: str,
    max_pages: int,
    conf_threshold: float,
    imgsz: int,
    dpi: int,
) -> LocalOmrResult:
    # Import here so a missing PyMuPDF / ultralytics doesn't break the
    # backend at import time.
    import fitz  # PyMuPDF
    from tools.omr.transcribe import transcribe
    from tools.omr.export import to_musicxml

    doc = fitz.open(pdf_path)
    n_pages = doc.page_count
    doc.close()
    pages = list(range(min(n_pages, max_pages)))
    if not pages:
        return LocalOmrResult(
            musicxml_path="",
            omr_json_path="",
            confidence_score=0.0,
            measures_count=0,
            error_message=f"PDF has no pages: {pdf_path}",
        )

    logger.info(
        "local_omr: %s → %d pages, weights=%s, conf=%.2f, imgsz=%d, dpi=%d",
        Path(pdf_path).name, len(pages), Path(weights).name,
        conf_threshold, imgsz, dpi,
    )

    omr_result = transcribe(
        pdf_path=Path(pdf_path),
        pages=pages,
        weights=weights,
        conf_threshold=conf_threshold,
        imgsz=imgsz,
        dpi=dpi,
        progress=False,
    )

    # Write the structured JSON to disk so the exporter can read it.
    # We may rewrite this after the theory enrichment step.
    pdf_stem = Path(pdf_path).stem
    json_path = os.path.join(output_dir, f"{pdf_stem}.omr.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(omr_result, fh)

    # Also write a MusicXML so the existing review/Vision flow + the
    # default export path keep working unchanged.
    musicxml_path = os.path.join(output_dir, f"{pdf_stem}.musicxml")
    try:
        xml_str = to_musicxml(omr_result)
        with open(musicxml_path, "w", encoding="utf-8") as fh:
            fh.write(xml_str)
    except Exception as exc:
        logger.exception("MusicXML serialization failed")
        return LocalOmrResult(
            musicxml_path="",
            omr_json_path=json_path,
            confidence_score=_confidence_from_result(omr_result),
            measures_count=int(omr_result.get("n_measures_total", 0)),
            pages_processed=int(omr_result.get("n_pages_processed", 0)),
            detections_total=int(omr_result.get("n_detections_total", 0)),
            runtime_seconds=float(
                omr_result.get("runtime", {}).get("total_s", 0.0)
            ),
            error_message=f"MusicXML serialization failed: {exc}",
        )

    # Theory enrichment via the maestro_bridge — adds harmony + rhythm
    # hints to omr_result if MAESTRO_BRIDGE_ENABLED is set. Failures are
    # swallowed inside theory_layer; OMR proceeds either way.
    try:
        from modules.theory_layer import enrich_omr_result, apply_pitch_corrections
    except ImportError:
        # Two-layer fallback for non-Docker layouts where backend is
        # imported as a package (backend.modules.theory_layer).
        from backend.modules.theory_layer import (  # type: ignore
            enrich_omr_result,
            apply_pitch_corrections,
        )
    omr_result = enrich_omr_result(omr_result, musicxml_path)

    # M4: auto-apply high-confidence pitch corrections (gated by a
    # separate env var MAESTRO_PITCH_RERANK_ENABLED). When this kicks in,
    # the MusicXML on disk is OVERWRITTEN with the corrected version, and
    # the omr_result dict gets a `corrections_applied` audit field.
    omr_result = apply_pitch_corrections(omr_result, musicxml_path)

    # If theory_hints or corrections were added, rewrite the JSON so disk
    # reflects it.
    if "theory_hints" in omr_result or "corrections_applied" in omr_result \
            or "corrections_meta" in omr_result:
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(omr_result, fh)

    return LocalOmrResult(
        musicxml_path=musicxml_path,
        omr_json_path=json_path,
        confidence_score=_confidence_from_result(omr_result),
        measures_count=int(omr_result.get("n_measures_total", 0)),
        pages_processed=int(omr_result.get("n_pages_processed", 0)),
        detections_total=int(omr_result.get("n_detections_total", 0)),
        runtime_seconds=float(
            omr_result.get("runtime", {}).get("total_s", 0.0)
        ),
    )


def _confidence_from_result(result: dict[str, Any]) -> float:
    """Synthesize a 0-1 confidence score.

    Pitch/rhythm coverage alone saturates near 1.0 even on bad pages —
    nearly every notehead gets SOME pitch/duration resolved, right or
    wrong, so a page full of confidently-wrong detections used to still
    score ~1.0. Folds in real signal so bad pages score visibly lower:
    equally-weighted (0.2 each) average of notehead pitch-resolution
    coverage, notehead rhythm-resolution coverage, the fraction of
    measures with no `phase1_warning` (Phase 1 fused/missed a barline),
    the fraction with no `rhythm_sum_warning` (beat count doesn't match
    the time signature), and the mean raw YOLO detection confidence.
    """
    n_nh = max(1, int(result.get("n_noteheads_total", 0)))
    pitched = int(result.get("n_noteheads_pitched_total", 0))
    timed = int(result.get("n_noteheads_with_duration_total", 0))
    pitch_cov = pitched / n_nh
    rhythm_cov = timed / n_nh

    n_measures = 0
    n_phase1_warn = 0
    n_rhythm_warn = 0
    conf_sum = 0.0
    n_dets = 0
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                for measure in staff.get("measures", []):
                    n_measures += 1
                    if "phase1_warning" in measure:
                        n_phase1_warn += 1
                    if "rhythm_sum_warning" in measure:
                        n_rhythm_warn += 1
                    for det in measure.get("detections", []):
                        conf_sum += float(det.get("confidence", 0.0))
                        n_dets += 1

    clean_structure = 1.0 - (n_phase1_warn / n_measures) if n_measures else 1.0
    clean_rhythm = 1.0 - (n_rhythm_warn / n_measures) if n_measures else 1.0
    mean_det_conf = (conf_sum / n_dets) if n_dets else 0.0

    return 0.2 * (pitch_cov + rhythm_cov + clean_structure + clean_rhythm + mean_det_conf)
