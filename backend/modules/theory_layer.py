"""
Theory enrichment layer — wraps the maestro_bridge to add harmony and rhythm
analysis to OMR output.

Used by both `local_omr` (YOLO pipeline) and `claude_vision_omr` (Claude
Vision pipeline) so that downstream consumers see identically-shaped
theory hints in `omr.json` metadata regardless of which OMR engine ran.

Gated behind the MAESTRO_BRIDGE_ENABLED env var (default: off) so that a
stock ReEngrave install without Node 24 + the maestro_bridge npm deps
keeps working unchanged.

Failures are SWALLOWED, not raised. Theory enrichment must never break
OMR — if the bridge times out, returns garbage, or isn't installed, we
log it and return the original omr_json unchanged.

Usage:
    from backend.modules.theory_layer import enrich_omr_result

    enriched = enrich_omr_result(omr_json_dict, musicxml_path)
    # enriched["theory_hints"] is now present with harmony + rhythm keys
    # (or absent if the bridge isn't enabled / failed)
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    """Honor the MAESTRO_BRIDGE_ENABLED env var. Off by default."""
    return os.environ.get("MAESTRO_BRIDGE_ENABLED", "").lower() in ("1", "true", "yes", "on")


def _rerank_enabled() -> bool:
    """Honor MAESTRO_PITCH_RERANK_ENABLED — separate gate so analysis-only
    mode (M0-M3) is possible without M4 auto-correction kicking in."""
    return os.environ.get("MAESTRO_PITCH_RERANK_ENABLED", "").lower() in ("1", "true", "yes", "on")


def _rerank_threshold() -> float:
    """Auto-apply threshold for pitch corrections. Default 0.9. Override
    via MAESTRO_PITCH_RERANK_THRESHOLD env var."""
    try:
        v = float(os.environ.get("MAESTRO_PITCH_RERANK_THRESHOLD", "0.9"))
    except ValueError:
        v = 0.9
    return max(0.0, min(1.0, v))


def compute_theory_hints(musicxml_path: str | Path) -> dict[str, Any] | None:
    """Compute the maestroAnalyst harmony + rhythm hints for a MusicXML file.

    Returns the theory_hints dict, or None if the bridge is disabled or the
    MusicXML is missing. Never raises — bridge failures are swallowed and
    reflected in the returned `errors` list.

    Output shape:
        {
          "engine": "maestroAnalyst-bridge",
          "version": 1,
          "elapsed_seconds": 1.23,
          "harmony": { ... },              # full harmony output, or null on failure
          "rhythm":  { ... },              # full rhythm output, or null on failure
          "errors":  ["..."]               # any per-capability errors
        }
    """
    if not _enabled():
        return None

    if not Path(musicxml_path).exists():
        logger.warning(
            "theory_layer: MusicXML not found at %s; skipping theory hints",
            musicxml_path,
        )
        return None

    # Late import: don't fail at module-import time if the bridge isn't
    # installed. We only need it when actually enriching.
    try:
        from .maestro_bridge import analyze_musicxml, MaestroBridgeError
    except ImportError as e:
        logger.warning(
            "theory_layer: maestro_bridge module unavailable (%s); skipping",
            e,
        )
        return None

    start = time.monotonic()
    errors: list[str] = []
    harmony: dict | None = None
    rhythm: dict | None = None

    try:
        harmony = analyze_musicxml(musicxml_path, capability="harmony")
    except MaestroBridgeError as e:
        msg = f"harmony: {e}"
        errors.append(msg)
        logger.warning("theory_layer: %s", msg)
    except Exception as e:  # noqa: BLE001
        msg = f"harmony: unexpected {type(e).__name__}: {e}"
        errors.append(msg)
        logger.exception("theory_layer: unexpected harmony failure")

    try:
        rhythm = analyze_musicxml(musicxml_path, capability="rhythm")
    except MaestroBridgeError as e:
        msg = f"rhythm: {e}"
        errors.append(msg)
        logger.warning("theory_layer: %s", msg)
    except Exception as e:  # noqa: BLE001
        msg = f"rhythm: unexpected {type(e).__name__}: {e}"
        errors.append(msg)
        logger.exception("theory_layer: unexpected rhythm failure")

    elapsed = time.monotonic() - start
    hints = {
        "engine": "maestroAnalyst-bridge",
        "version": 1,
        "elapsed_seconds": round(elapsed, 3),
        "harmony": harmony,
        "rhythm": rhythm,
        "errors": errors,
    }

    if harmony or rhythm:
        warning_count = (rhythm or {}).get("meta", {}).get("warnings_count", 0) if rhythm else 0
        cadence_count = len((harmony or {}).get("cadences", [])) if harmony else 0
        logger.info(
            "theory_layer: hinted %s — %d harmony cadences, %d rhythm warnings, %.2fs",
            Path(musicxml_path).name,
            cadence_count,
            warning_count,
            elapsed,
        )

    return hints


def enrich_omr_result(
    omr_json: dict[str, Any],
    musicxml_path: str | Path,
) -> dict[str, Any]:
    """Convenience wrapper: add theory_hints into an existing OMR result dict.

    Used by local_omr (which has a transcribe-style omr.json to enrich).
    claude_vision_omr uses compute_theory_hints directly since it has no
    such pre-existing JSON to mutate.

    Modifies omr_json in place and also returns it.
    """
    hints = compute_theory_hints(musicxml_path)
    if hints is not None:
        omr_json["theory_hints"] = hints
    return omr_json


def apply_pitch_corrections(
    omr_json: dict[str, Any],
    musicxml_path: str | Path,
    *,
    threshold: float | None = None,
) -> dict[str, Any]:
    """M4: run harmony → re-rank → apply high-confidence corrections to
    omr_json in place; re-export MusicXML from the corrected detections.

    Gated by MAESTRO_PITCH_RERANK_ENABLED env var. Threshold defaults
    to MAESTRO_PITCH_RERANK_THRESHOLD env var (or 0.9).

    Workflow:
      1. Run harmony analysis on `musicxml_path`.
      2. Write harmony + omr to temp JSON files.
      3. Invoke the bridge's re-rank capability.
      4. For each correction with apply=='auto', mutate the matching
         detection's `pitch` field in `omr_json`. Track the change in
         omr_json['corrections_applied'].
      5. Re-serialize the MusicXML from the corrected omr_json and
         overwrite `musicxml_path`.

    All failures are swallowed and logged — if re-ranking fails for any
    reason, the OMR result is left exactly as it came in. Returns the
    (possibly mutated) omr_json for convenience.
    """
    if not _rerank_enabled():
        return omr_json

    musicxml_path = Path(musicxml_path)
    if not musicxml_path.exists():
        logger.warning("apply_pitch_corrections: MusicXML not found at %s", musicxml_path)
        return omr_json

    # Late imports so we don't fail at import time without the bridge.
    try:
        from .maestro_bridge import (
            analyze_musicxml,
            re_rank_pitches,
            MaestroBridgeError,
        )
    except ImportError as e:
        logger.warning("apply_pitch_corrections: maestro_bridge unavailable (%s)", e)
        return omr_json

    th = threshold if threshold is not None else _rerank_threshold()

    # 1. Harmony analysis on the OMR-emitted MusicXML.
    try:
        harmony = analyze_musicxml(musicxml_path, capability="harmony")
    except (MaestroBridgeError, FileNotFoundError) as e:
        logger.warning("apply_pitch_corrections: harmony analysis failed: %s", e)
        return omr_json
    except Exception:  # noqa: BLE001
        logger.exception("apply_pitch_corrections: unexpected harmony failure")
        return omr_json

    # 2. Stage harmony + omr_json as temp files for the re-rank subprocess.
    import tempfile  # noqa: PLC0415 — local to keep top-level lean

    omr_tmp: str | None = None
    harmony_tmp: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".harmony.json", delete=False, encoding="utf-8"
        ) as hf:
            json.dump(harmony, hf)
            harmony_tmp = hf.name
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".omr.json", delete=False, encoding="utf-8"
        ) as of:
            json.dump(omr_json, of)
            omr_tmp = of.name

        # 3. Invoke re-rank.
        try:
            rerank = re_rank_pitches(omr_tmp, harmony_tmp, threshold=th)
        except MaestroBridgeError as e:
            logger.warning("apply_pitch_corrections: re-rank failed: %s", e)
            return omr_json
        except Exception:  # noqa: BLE001
            logger.exception("apply_pitch_corrections: unexpected re-rank failure")
            return omr_json
    finally:
        for p in (omr_tmp, harmony_tmp):
            if p:
                try:
                    Path(p).unlink()
                except OSError:
                    pass

    # 4. Apply auto-confidence corrections in place.
    applied: list[dict] = []
    for corr in rerank.get("corrections", []):
        if corr.get("apply") != "auto":
            continue
        det = _walk_to_detection(omr_json, corr)
        if det is None:
            continue
        previous = det.get("pitch")
        if previous != corr.get("original_pitch"):
            # Sanity check failed — omr_json drifted between when re-rank
            # snapshotted and now. Skip to avoid wrong-target corrections.
            logger.warning(
                "apply_pitch_corrections: skip drifted correction at %s; expected %r got %r",
                _correction_loc_str(corr), corr.get("original_pitch"), previous,
            )
            continue
        det["pitch"] = corr["corrected_pitch"]
        applied.append({
            "page_index": corr["page_index"],
            "system_index": corr["system_index"],
            "staff_index": corr["staff_index"],
            "measure_index": corr["measure_index"],
            "detection_index": corr["detection_index"],
            "from_pitch": previous,
            "to_pitch": corr["corrected_pitch"],
            "confidence": corr["confidence"],
            "local_key": corr["local_key"],
            "reason": corr["reason"],
        })

    if applied:
        omr_json["corrections_applied"] = applied
        omr_json["corrections_meta"] = {
            "threshold": th,
            "total_corrections_emitted": len(rerank.get("corrections", [])),
            "auto_applied": len(applied),
            "suggestions_only": rerank.get("meta", {}).get("suggestion_count", 0),
            "noteheads_non_diatonic": rerank.get("noteheads_non_diatonic", 0),
        }

        # 5. Re-serialize MusicXML from corrected omr_json.
        try:
            from tools.omr.export import to_musicxml  # type: ignore
            xml_str = to_musicxml(omr_json)
            with open(musicxml_path, "w", encoding="utf-8") as fh:
                fh.write(xml_str)
            logger.info(
                "apply_pitch_corrections: %d auto-corrections applied; MusicXML re-exported to %s",
                len(applied), musicxml_path,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "apply_pitch_corrections: corrections applied to omr_json but MusicXML re-export failed; original MusicXML retained"
            )
            omr_json["corrections_meta"]["xml_reexport_failed"] = True
    else:
        # Still record that we ran, so consumers can tell apart "didn't run"
        # from "ran but found nothing to auto-apply".
        omr_json["corrections_meta"] = {
            "threshold": th,
            "total_corrections_emitted": len(rerank.get("corrections", [])),
            "auto_applied": 0,
            "suggestions_only": rerank.get("meta", {}).get("suggestion_count", 0),
            "noteheads_non_diatonic": rerank.get("noteheads_non_diatonic", 0),
        }

    return omr_json


def _walk_to_detection(omr_json: dict, corr: dict) -> dict | None:
    """Walk omr_json by index keys from a correction record.

    Returns the detection dict, or None if any index is out of range.
    The detection_index addresses the position in detections[], not by
    a global ID — re-rank.ts emits these same indices walking the same
    structure, so they line up.
    """
    try:
        page = omr_json["pages"][corr["page_index"]]
        sys = page["systems"][corr["system_index"]]
        staff = sys["staves"][corr["staff_index"]]
        # measure_index is the GLOBAL measure number, not the array index.
        # Find by match.
        target_m = corr["measure_index"]
        measure = next(
            (m for m in staff["measures"] if m.get("measure_index") == target_m),
            None,
        )
        if measure is None:
            return None
        return measure["detections"][corr["detection_index"]]
    except (KeyError, IndexError, TypeError):
        return None


def _correction_loc_str(corr: dict) -> str:
    return (
        f"p{corr.get('page_index')}/s{corr.get('system_index')}/"
        f"st{corr.get('staff_index')}/m{corr.get('measure_index')}/"
        f"d{corr.get('detection_index')}"
    )


__all__ = [
    "compute_theory_hints",
    "enrich_omr_result",
    "apply_pitch_corrections",
]
