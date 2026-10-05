"""
Learning system — tracks corrections and extracts patterns to improve over time.

Files managed:
- corrections_db.json     — every correction decision with full context
- learned_patterns.json   — extracted patterns per engine/instrument/era
- engine_accuracy.json    — win-rate stats per engine per context
- finetuning_data.jsonl   — image→correction pairs for future training
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import (
    AUTO_ACCEPT_MIN_ACCURACY,
    AUTO_ACCEPT_MIN_SAMPLES,
    CORRECTIONS_DB,
    ENGINE_ACCURACY,
    FINETUNING_DATA,
    LEARNED_PATTERNS,
    PATTERN_MIN_ERROR_RATE,
    PATTERN_MIN_SAMPLES,
)


# ---------------------------------------------------------------------------
# Correction recording
# ---------------------------------------------------------------------------


def record_correction(
    score_title: str,
    measure_number: int,
    part_id: str,
    part_name: str,
    instrument: str,
    era: str,
    engine_a: str,
    engine_b: str,
    engine_a_xml: str,
    engine_b_xml: str,
    winner: str,  # engine name or "human_edit"
    correction_xml: Optional[str] = None,
    difference_type: str = "unknown",
    page_image_path: Optional[str] = None,
) -> None:
    """Record a single correction decision to the corrections database."""
    db = _load_json(CORRECTIONS_DB, [])

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "score_title": score_title,
        "measure_number": measure_number,
        "part_id": part_id,
        "part_name": part_name,
        "instrument": instrument,
        "era": era,
        "engine_a": engine_a,
        "engine_b": engine_b,
        "engine_a_xml": engine_a_xml,
        "engine_b_xml": engine_b_xml,
        "winner": winner,
        "correction_xml": correction_xml,
        "difference_type": difference_type,
        "page_image_path": page_image_path,
    }

    db.append(entry)
    _save_json(CORRECTIONS_DB, db)


def record_batch(corrections: list[dict]) -> None:
    """Record multiple corrections at once (end of review session)."""
    db = _load_json(CORRECTIONS_DB, [])
    db.extend(corrections)
    _save_json(CORRECTIONS_DB, db)


# ---------------------------------------------------------------------------
# Pattern extraction
# ---------------------------------------------------------------------------


def update_patterns() -> dict:
    """Analyze all corrections and extract patterns.

    Updates learned_patterns.json and engine_accuracy.json.
    Returns a summary dict.
    """
    db = _load_json(CORRECTIONS_DB, [])
    if not db:
        return {"total_corrections": 0, "patterns": [], "accuracy": {}}

    # Compute per-engine accuracy by context
    accuracy = _compute_accuracy(db)
    _save_json(ENGINE_ACCURACY, accuracy)

    # Extract patterns
    patterns = _extract_patterns(db, accuracy)
    _save_json(LEARNED_PATTERNS, patterns)

    return {
        "total_corrections": len(db),
        "patterns": patterns,
        "accuracy": accuracy,
    }


def _compute_accuracy(db: list[dict]) -> dict:
    """Compute per-engine win rates, sliced by instrument and era."""
    # Group by (engine_a, engine_b, instrument, era)
    groups: dict[str, dict] = defaultdict(lambda: {"wins_a": 0, "wins_b": 0, "edits": 0, "total": 0})

    for entry in db:
        ea = entry.get("engine_a", "unknown")
        eb = entry.get("engine_b", "unknown")
        instrument = entry.get("instrument", "unknown")
        era = entry.get("era", "unknown")
        winner = entry.get("winner", "")

        # Global key
        global_key = f"{ea}_vs_{eb}"
        # Instrument-specific key
        inst_key = f"{ea}_vs_{eb}:{instrument}"
        # Era-specific key
        era_key = f"{ea}_vs_{eb}:{era}"
        # Full key
        full_key = f"{ea}_vs_{eb}:{instrument}:{era}"

        for key in [global_key, inst_key, era_key, full_key]:
            groups[key]["total"] += 1
            if winner == ea:
                groups[key]["wins_a"] += 1
            elif winner == eb:
                groups[key]["wins_b"] += 1
            else:
                groups[key]["edits"] += 1

    # Convert to accuracy rates
    result = {}
    for key, stats in groups.items():
        if stats["total"] == 0:
            continue
        result[key] = {
            "total": stats["total"],
            "engine_a_rate": stats["wins_a"] / stats["total"],
            "engine_b_rate": stats["wins_b"] / stats["total"],
            "edit_rate": stats["edits"] / stats["total"],
            "wins_a": stats["wins_a"],
            "wins_b": stats["wins_b"],
            "edits": stats["edits"],
        }

    return result


def _extract_patterns(db: list[dict], accuracy: dict) -> list[dict]:
    """Extract human-readable patterns from correction history."""
    patterns = []

    # Group by (engine, instrument, difference_type)
    engine_errors: dict[str, list] = defaultdict(list)

    for entry in db:
        ea = entry.get("engine_a", "")
        eb = entry.get("engine_b", "")
        winner = entry.get("winner", "")
        diff_type = entry.get("difference_type", "unknown")
        instrument = entry.get("instrument", "unknown")

        if winner == ea:
            # engine_b was wrong
            engine_errors[f"{eb}:{instrument}:{diff_type}"].append(entry)
        elif winner == eb:
            # engine_a was wrong
            engine_errors[f"{ea}:{instrument}:{diff_type}"].append(entry)

    for key, entries in engine_errors.items():
        parts = key.split(":")
        if len(parts) != 3:
            continue
        engine, instrument, diff_type = parts

        if len(entries) < PATTERN_MIN_SAMPLES:
            continue

        total_for_engine = sum(
            1 for e in db
            if engine in (e.get("engine_a", ""), e.get("engine_b", ""))
            and e.get("instrument", "") == instrument
            and e.get("difference_type", "") == diff_type
        )

        if total_for_engine == 0:
            continue

        error_rate = len(entries) / total_for_engine

        if error_rate >= PATTERN_MIN_ERROR_RATE:
            patterns.append({
                "engine": engine,
                "instrument": instrument,
                "difference_type": diff_type,
                "error_rate": round(error_rate, 3),
                "sample_count": len(entries),
                "description": (
                    f"{engine} misreads {diff_type} in {instrument} parts "
                    f"{round(error_rate * 100)}% of the time "
                    f"(based on {len(entries)} corrections)"
                ),
            })

    # Sort by error rate descending
    patterns.sort(key=lambda p: p["error_rate"], reverse=True)
    return patterns


# ---------------------------------------------------------------------------
# Auto-accept rules
# ---------------------------------------------------------------------------


def get_auto_accept_rules() -> list[dict]:
    """Get active auto-accept rules based on engine accuracy data."""
    accuracy = _load_json(ENGINE_ACCURACY, {})
    rules = []

    for key, stats in accuracy.items():
        if stats["total"] < AUTO_ACCEPT_MIN_SAMPLES:
            continue

        if stats["engine_a_rate"] >= AUTO_ACCEPT_MIN_ACCURACY:
            engines = key.split("_vs_")
            if len(engines) >= 2:
                context = key.split(":", 1)[1] if ":" in key else "all"
                rules.append({
                    "key": key,
                    "winning_engine": engines[0],
                    "accuracy": stats["engine_a_rate"],
                    "sample_count": stats["total"],
                    "context": context,
                    "description": (
                        f"Auto-accept {engines[0]} for {context}: "
                        f"{round(stats['engine_a_rate'] * 100)}% accuracy "
                        f"over {stats['total']} samples"
                    ),
                })

        if stats["engine_b_rate"] >= AUTO_ACCEPT_MIN_ACCURACY:
            engines = key.split("_vs_")
            if len(engines) >= 2:
                context = key.split(":", 1)[1] if ":" in key else "all"
                # Parse engine_b name (after _vs_)
                eb_part = engines[1].split(":")[0]
                rules.append({
                    "key": key,
                    "winning_engine": eb_part,
                    "accuracy": stats["engine_b_rate"],
                    "sample_count": stats["total"],
                    "context": context,
                    "description": (
                        f"Auto-accept {eb_part} for {context}: "
                        f"{round(stats['engine_b_rate'] * 100)}% accuracy "
                        f"over {stats['total']} samples"
                    ),
                })

    return rules


def check_auto_accept(
    engine_a: str, engine_b: str,
    instrument: str, era: str,
) -> Optional[str]:
    """Check if a disagreement can be auto-resolved.

    Returns the winning engine name if an auto-accept rule matches, else None.
    """
    accuracy = _load_json(ENGINE_ACCURACY, {})

    # Check from most specific to least specific
    keys_to_check = [
        f"{engine_a}_vs_{engine_b}:{instrument}:{era}",
        f"{engine_a}_vs_{engine_b}:{instrument}",
        f"{engine_a}_vs_{engine_b}:{era}",
        f"{engine_a}_vs_{engine_b}",
    ]

    for key in keys_to_check:
        stats = accuracy.get(key)
        if stats is None:
            continue
        if stats["total"] < AUTO_ACCEPT_MIN_SAMPLES:
            continue

        if stats["engine_a_rate"] >= AUTO_ACCEPT_MIN_ACCURACY:
            return engine_a
        if stats["engine_b_rate"] >= AUTO_ACCEPT_MIN_ACCURACY:
            return engine_b

    return None


# ---------------------------------------------------------------------------
# Prompt context generation
# ---------------------------------------------------------------------------


def get_prompt_context() -> str:
    """Generate context string from learned patterns to inject into OMR prompts.

    Returns a string of warnings/guidance based on past corrections.
    """
    patterns = _load_json(LEARNED_PATTERNS, [])
    if not patterns:
        return ""

    lines = ["Based on past correction history, pay extra attention to:"]
    for p in patterns[:10]:  # Top 10 patterns
        lines.append(f"- {p['description']}")

    return "\n".join(lines)


def get_session_summary() -> str:
    """Generate a summary of the learning system's state."""
    db = _load_json(CORRECTIONS_DB, [])
    patterns = _load_json(LEARNED_PATTERNS, [])
    rules = get_auto_accept_rules()

    if not db:
        return "No correction history yet. Patterns will emerge after reviewing a few scores."

    lines = [
        f"Correction history: {len(db)} decisions across past sessions",
        f"Learned patterns: {len(patterns)}",
        f"Auto-accept rules: {len(rules)} active",
    ]

    if rules:
        lines.append("\nActive auto-accept rules:")
        for r in rules:
            lines.append(f"  - {r['description']}")

    if patterns:
        lines.append("\nTop known issues:")
        for p in patterns[:5]:
            lines.append(f"  - {p['description']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fine-tuning data export
# ---------------------------------------------------------------------------


def append_finetuning_entry(
    page_image_path: str,
    wrong_xml: str,
    correct_xml: str,
    context: dict,
) -> None:
    """Append a single training example to the fine-tuning dataset."""
    Path(FINETUNING_DATA).parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "image": page_image_path,
        "input_xml": wrong_xml,
        "correct_xml": correct_xml,
        "context": context,
        "timestamp": datetime.utcnow().isoformat(),
    }

    with open(FINETUNING_DATA, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def _load_json(path: str, default):
    """Load a JSON file, returning default if it doesn't exist."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path: str, data) -> None:
    """Save data to a JSON file."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
