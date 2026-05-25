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

import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    """Honor the MAESTRO_BRIDGE_ENABLED env var. Off by default."""
    return os.environ.get("MAESTRO_BRIDGE_ENABLED", "").lower() in ("1", "true", "yes", "on")


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


__all__ = ["compute_theory_hints", "enrich_omr_result"]
