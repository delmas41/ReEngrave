"""
ReEngrave ↔ maestroAnalyst bridge (Python side).

Spawns the Node tsx subprocess at `tools/maestro_bridge/analyze.ts` to run
music-theory analysis on a MusicXML file. Returns the structured JSON output
documented in `docs/maestro-integration-plan.md`.

Personal-use only: no long-running service, no HTTP, no MCP. One-shot
subprocess per call. ~50-200ms latency including Node cold start.

Usage:
    from backend.modules.maestro_bridge import analyze_musicxml

    result = analyze_musicxml("/path/to/score.musicxml", capability="harmony")
    print(result["overall_key"])  # {"key": "C major", "confidence": 0.91}
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Literal


# Resolve the bridge directory relative to this file (backend/modules/) ->
# repo root -> tools/maestro_bridge/. Works for both web-app context (where
# the backend container mounts the repo) and direct invocation.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BRIDGE_DIR = _REPO_ROOT / "tools" / "maestro_bridge"
_ANALYZE_TS = _BRIDGE_DIR / "analyze.ts"

# Allow override via env for unusual layouts (e.g. running outside the repo).
_ANALYZE_TS_PATH = Path(os.environ.get("MAESTRO_ANALYZE_TS", str(_ANALYZE_TS)))
_NODE_BIN = os.environ.get("MAESTRO_NODE_BIN", "node")
# tsx is installed locally in the bridge's node_modules; the CLI entry is
# node_modules/.bin/tsx (or node_modules/tsx/dist/cli.mjs).
_TSX_BIN = os.environ.get("MAESTRO_TSX_BIN", str(_BRIDGE_DIR / "node_modules" / ".bin" / "tsx"))

# Default timeout — most pieces analyze in <2s; large orchestral scores can
# reach ~10s. 60s gives plenty of headroom.
_DEFAULT_TIMEOUT = float(os.environ.get("MAESTRO_TIMEOUT_S", "60"))


class MaestroBridgeError(RuntimeError):
    """Raised when the bridge subprocess fails or returns malformed output."""


def analyze_musicxml(
    xml_path: str | os.PathLike,
    capability: Literal["harmony", "rhythm", "cross-check"] = "harmony",
    *,
    work_id: str | None = None,
    timeout_s: float | None = None,
) -> dict:
    """Run maestroAnalyst over a MusicXML file via the Node bridge.

    Args:
        xml_path: Path to a .musicxml, .xml, or .mxl file.
        capability: Which capability to run. "harmony", "rhythm", and
                    "cross-check" are all supported.
        work_id: For "cross-check" only — the canonical work identifier
                 from the scholarly DB (e.g. "wtc-i-1", "beethoven-5-i").
                 Required for cross-check. Use list_scholarly_works() to
                 see what's available.
        timeout_s: Subprocess timeout, defaults to MAESTRO_TIMEOUT_S (60s).

    Returns:
        The parsed JSON output from the bridge. Shape depends on capability;
        see docs/maestro-integration-plan.md.

    Raises:
        MaestroBridgeError: subprocess failed, output was malformed, the
                             bridge isn't installed, or cross-check was
                             called without a work_id.
        FileNotFoundError: xml_path does not exist.
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(str(xml_path))

    if not _ANALYZE_TS_PATH.exists():
        raise MaestroBridgeError(
            f"maestro bridge entry not found at {_ANALYZE_TS_PATH}. "
            "Did you run `npm install` in tools/maestro_bridge/?"
        )

    if not Path(_TSX_BIN).exists():
        raise MaestroBridgeError(
            f"tsx binary not found at {_TSX_BIN}. Run `npm install` in tools/maestro_bridge/."
        )

    if capability not in ("harmony", "rhythm", "cross-check"):
        raise NotImplementedError(
            f"capability '{capability}' is not implemented yet. "
            "See docs/maestro-integration-plan.md."
        )

    if capability == "cross-check" and not work_id:
        raise MaestroBridgeError(
            "cross-check requires work_id. Call list_scholarly_works() to see available works."
        )

    cmd = [_NODE_BIN, _TSX_BIN, str(_ANALYZE_TS_PATH), capability, str(xml_path.resolve())]
    if work_id is not None:
        cmd += ["--work", work_id]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s or _DEFAULT_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise MaestroBridgeError(
            f"maestro bridge timed out after {e.timeout}s on {xml_path}"
        ) from e
    except FileNotFoundError as e:
        raise MaestroBridgeError(
            f"could not spawn node: {e}. Is Node 24+ installed and on PATH?"
        ) from e

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-10:]
        raise MaestroBridgeError(
            f"bridge exited with code {proc.returncode}:\n" + "\n".join(stderr_tail)
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise MaestroBridgeError(
            f"bridge returned non-JSON output: {e}. "
            f"stdout head: {proc.stdout[:500]!r}"
        ) from e


def re_rank_pitches(
    omr_json_path: str | os.PathLike,
    harmony_json_path: str | os.PathLike,
    *,
    threshold: float = 0.9,
    timeout_s: float | None = None,
) -> dict:
    """Run the bridge's M4 pitch re-rank capability.

    Args:
        omr_json_path: path to omr.json (with pitch_candidates per notehead,
                       emitted by M4-extended transcribe.py).
        harmony_json_path: path to a saved harmony output JSON (from a prior
                       analyze_musicxml(capability='harmony') call).
        threshold: corrections with confidence >= threshold get apply='auto';
                   below threshold are apply='suggestion'. Default 0.9.
        timeout_s: subprocess timeout.

    Returns:
        Re-rank output dict — see docs/maestro-integration-plan.md.

    Raises:
        MaestroBridgeError: subprocess failed or output was malformed.
        FileNotFoundError: omr_json_path or harmony_json_path doesn't exist.
    """
    omr_json_path = Path(omr_json_path)
    harmony_json_path = Path(harmony_json_path)
    if not omr_json_path.exists():
        raise FileNotFoundError(str(omr_json_path))
    if not harmony_json_path.exists():
        raise FileNotFoundError(str(harmony_json_path))

    if not _ANALYZE_TS_PATH.exists():
        raise MaestroBridgeError(
            f"maestro bridge entry not found at {_ANALYZE_TS_PATH}."
        )
    if not Path(_TSX_BIN).exists():
        raise MaestroBridgeError(
            f"tsx binary not found at {_TSX_BIN}. Run `npm install` in tools/maestro_bridge/."
        )

    cmd = [
        _NODE_BIN, _TSX_BIN, str(_ANALYZE_TS_PATH),
        "re-rank", str(omr_json_path.resolve()),
        "--harmony", str(harmony_json_path.resolve()),
        "--threshold", str(threshold),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s or _DEFAULT_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise MaestroBridgeError(
            f"re-rank timed out after {e.timeout}s"
        ) from e

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-10:]
        raise MaestroBridgeError(
            f"re-rank exited with code {proc.returncode}:\n" + "\n".join(stderr_tail)
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise MaestroBridgeError(f"re-rank returned non-JSON: {e}") from e


def list_scholarly_works(timeout_s: float | None = None) -> dict:
    """List the canonical works available in the scholarly DB.

    Returns the JSON output from `cross-check --list-works`. Use the
    work_id of any entry as the work_id argument to analyze_musicxml.

    Raises:
        MaestroBridgeError: bridge isn't installed or returns malformed JSON.
    """
    if not _ANALYZE_TS_PATH.exists():
        raise MaestroBridgeError(
            f"maestro bridge entry not found at {_ANALYZE_TS_PATH}. "
            "Did you run `npm install` in tools/maestro_bridge/?"
        )
    if not Path(_TSX_BIN).exists():
        raise MaestroBridgeError(
            f"tsx binary not found at {_TSX_BIN}. Run `npm install` in tools/maestro_bridge/."
        )

    cmd = [_NODE_BIN, _TSX_BIN, str(_ANALYZE_TS_PATH), "cross-check", "--list-works"]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s or _DEFAULT_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise MaestroBridgeError(f"bridge timed out after {e.timeout}s listing works") from e

    if proc.returncode != 0:
        stderr_tail = (proc.stderr or "").strip().splitlines()[-5:]
        raise MaestroBridgeError(
            f"bridge exited with code {proc.returncode}:\n" + "\n".join(stderr_tail)
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise MaestroBridgeError(f"bridge returned non-JSON output: {e}") from e


__all__ = [
    "analyze_musicxml",
    "list_scholarly_works",
    "re_rank_pitches",
    "MaestroBridgeError",
]
