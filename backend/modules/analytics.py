"""
Analytics and self-improving agent layer for ReEngrave.
Analyzes correction patterns, maintains a knowledge base, and manages
auto-accept rules derived from accumulated human decisions.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    AutoAcceptRule,
    FlaggedDifference,
    FineTuningDataset,
    KnowledgePattern,
    Score,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PatternAnalysis:
    pattern_type: str
    instrument: Optional[str]
    difference_type: str
    occurrence_count: int
    accept_rate: float
    reject_rate: float
    suggested_rule: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_correction_patterns(db: AsyncSession) -> list[PatternAnalysis]:
    """Query FlaggedDifference, group by instrument + difference_type,
    compute accept/reject rates, and return PatternAnalysis objects.
    """
    result = await db.execute(
        select(
            FlaggedDifference.instrument,
            FlaggedDifference.difference_type,
            func.count().label("total"),
            func.sum(
                (FlaggedDifference.human_decision == "accept").cast(int)
            ).label("accepts"),
            func.sum(
                (FlaggedDifference.human_decision == "reject").cast(int)
            ).label("rejects"),
            func.sum(
                (FlaggedDifference.human_decision == "edit").cast(int)
            ).label("edits"),
        )
        .where(FlaggedDifference.human_decision.isnot(None))
        .group_by(FlaggedDifference.instrument, FlaggedDifference.difference_type)
    )

    rows = result.all()
    analyses: list[PatternAnalysis] = []

    for row in rows:
        instrument, diff_type, total, accepts, rejects, edits = row
        accepts = accepts or 0
        rejects = rejects or 0
        total = total or 1

        accept_rate = accepts / total
        reject_rate = rejects / total

        suggested_rule: Optional[str] = None
        if accept_rate >= 0.8 and total >= 10:
            suggested_rule = (
                f"Auto-accept {diff_type} differences for {instrument} "
                f"(accept rate: {accept_rate:.0%}, n={total})"
            )

        analyses.append(
            PatternAnalysis(
                pattern_type="instrument_quirk" if instrument != "unknown" else "audiveris_failure",
                instrument=instrument,
                difference_type=diff_type,
                occurrence_count=total,
                accept_rate=accept_rate,
                reject_rate=reject_rate,
                suggested_rule=suggested_rule,
            )
        )

    return analyses


async def update_knowledge_base(db: AsyncSession) -> None:
    """Analyze correction patterns and create/update KnowledgePattern records."""
    analyses = await analyze_correction_patterns(db)

    for analysis in analyses:
        # Check for existing pattern
        existing = await db.execute(
            select(KnowledgePattern).where(
                KnowledgePattern.instrument == analysis.instrument,
                KnowledgePattern.difference_type == analysis.difference_type,
                KnowledgePattern.pattern_type == analysis.pattern_type,
            )
        )
        pattern = existing.scalar_one_or_none()

        accept_count = int(analysis.accept_rate * analysis.occurrence_count)
        reject_count = int(analysis.reject_rate * analysis.occurrence_count)

        if pattern is None:
            pattern = KnowledgePattern(
                id=str(uuid.uuid4()),
                pattern_type=analysis.pattern_type,
                instrument=analysis.instrument,
                difference_type=analysis.difference_type,
                pattern_description=analysis.suggested_rule or (
                    f"{analysis.difference_type} differences for "
                    f"{analysis.instrument or 'all instruments'}"
                ),
                occurrence_count=analysis.occurrence_count,
                accept_count=accept_count,
                reject_count=reject_count,
                edit_count=analysis.occurrence_count - accept_count - reject_count,
                example_ids=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(pattern)
        else:
            pattern.occurrence_count = analysis.occurrence_count
            pattern.accept_count = accept_count
            pattern.reject_count = reject_count
            pattern.edit_count = analysis.occurrence_count - accept_count - reject_count
            pattern.updated_at = datetime.utcnow()

    await db.flush()


async def evaluate_auto_accept_rules(db: AsyncSession) -> None:
    """Promote KnowledgePatterns with high accept rates to AutoAcceptRules.

    Threshold: > 80% accept rate AND > 10 occurrences.
    """
    result = await db.execute(
        select(KnowledgePattern).where(
            KnowledgePattern.occurrence_count >= 10,
        )
    )
    patterns = result.scalars().all()

    for pattern in patterns:
        if pattern.occurrence_count == 0:
            continue
        accept_rate = pattern.accept_count / pattern.occurrence_count
        if accept_rate < 0.8:
            continue

        # Check if rule already exists for this pattern
        existing_rule = await db.execute(
            select(AutoAcceptRule).where(AutoAcceptRule.pattern_id == pattern.id)
        )
        rule = existing_rule.scalar_one_or_none()

        if rule is None:
            rule = AutoAcceptRule(
                id=str(uuid.uuid4()),
                pattern_id=pattern.id,
                rule_description=pattern.pattern_description,
                instrument=pattern.instrument,
                difference_type=pattern.difference_type,
                min_audiveris_confidence=0.7,
                min_claude_confidence=0.7,
                min_confirmations=10,
                current_confirmations=pattern.occurrence_count,
                is_active=pattern.occurrence_count >= 10,
                created_at=datetime.utcnow(),
            )
            db.add(rule)
        else:
            rule.current_confirmations = pattern.occurrence_count
            rule.is_active = pattern.occurrence_count >= rule.min_confirmations

    await db.flush()


async def apply_auto_accept(diff: dict, db: AsyncSession) -> bool:
    """Check if a new FlaggedDifference matches any active AutoAcceptRule.

    Returns True if the diff was auto-accepted.

    TODO: Extend matching logic to also consider era and key/time signature context.
    """
    result = await db.execute(
        select(AutoAcceptRule).where(
            AutoAcceptRule.is_active.is_(True),
            AutoAcceptRule.difference_type == diff.get("difference_type"),
        )
    )
    rules = result.scalars().all()

    audiveris_conf = diff.get("audiveris_confidence", 0.0)
    claude_conf = diff.get("claude_vision_confidence", 0.0)
    instrument = diff.get("instrument", "")

    for rule in rules:
        instrument_match = rule.instrument is None or rule.instrument == instrument
        conf_match = (
            audiveris_conf >= rule.min_audiveris_confidence
            and claude_conf >= rule.min_claude_confidence
        )
        if instrument_match and conf_match:
            return True

    return False


async def generate_learning_report(db: AsyncSession) -> dict:
    """Return a comprehensive report of the self-improving agent's state.

    TODO: Add trend analysis over time (acceptance rates per week, etc.)
    """
    # Total corrections
    total_result = await db.execute(
        select(func.count()).where(FlaggedDifference.human_decision.isnot(None))
    )
    total_corrections = total_result.scalar() or 0

    # Accept rate
    accept_result = await db.execute(
        select(func.count()).where(FlaggedDifference.human_decision == "accept")
    )
    total_accepts = accept_result.scalar() or 0
    accept_rate = total_accepts / total_corrections if total_corrections > 0 else 0.0

    # Active auto rules
    rules_result = await db.execute(
        select(AutoAcceptRule).where(AutoAcceptRule.is_active.is_(True))
    )
    active_rules = rules_result.scalars().all()

    # Top patterns
    patterns_result = await db.execute(
        select(KnowledgePattern).order_by(KnowledgePattern.occurrence_count.desc()).limit(10)
    )
    top_patterns = patterns_result.scalars().all()

    # Scores overview
    scores_result = await db.execute(select(func.count(Score.id)))
    total_scores = scores_result.scalar() or 0

    return {
        "total_scores": total_scores,
        "total_corrections": total_corrections,
        "accept_rate": round(accept_rate, 4),
        "total_accepts": total_accepts,
        "total_rejects": total_corrections - total_accepts,
        "active_auto_rules": len(active_rules),
        "top_patterns": [
            {
                "instrument": p.instrument,
                "difference_type": p.difference_type,
                "occurrences": p.occurrence_count,
                "accept_rate": (
                    round(p.accept_count / p.occurrence_count, 4)
                    if p.occurrence_count > 0 else 0.0
                ),
            }
            for p in top_patterns
        ],
        "active_auto_rules_detail": [
            {
                "id": r.id,
                "instrument": r.instrument,
                "difference_type": r.difference_type,
                "confirmations": r.current_confirmations,
                "description": r.rule_description,
            }
            for r in active_rules
        ],
        # TODO: Add prompt_performance once ClaudePromptVersion tracking is active
        "prompt_performance": {},
        "suggested_improvements": _generate_suggestions(top_patterns),
    }


async def export_finetuning_dataset(db: AsyncSession, output_dir: str) -> str:
    """Export accepted corrections as a JSONL dataset for vision model fine-tuning.

    Format per line:
      {"image_path": "...", "label": "...", "metadata": {...}}

    Returns the path to the .jsonl file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    result = await db.execute(
        select(FlaggedDifference).where(
            FlaggedDifference.human_decision.in_(["accept", "edit"]),
            FlaggedDifference.pdf_snippet_path != "",
        )
    )
    diffs = result.scalars().all()

    out_path = os.path.join(output_dir, "finetuning_dataset.jsonl")
    now = datetime.utcnow()

    with open(out_path, "w", encoding="utf-8") as f:
        for diff in diffs:
            label = diff.human_edit_value or diff.musicxml_snippet_path
            record = {
                "image_path": diff.pdf_snippet_path,
                "label": label,
                "metadata": {
                    "measure_number": diff.measure_number,
                    "instrument": diff.instrument,
                    "difference_type": diff.difference_type,
                    "description": diff.description,
                    "audiveris_confidence": diff.audiveris_confidence,
                    "claude_vision_confidence": diff.claude_vision_confidence,
                    "human_decision": diff.human_decision,
                },
            }
            f.write(json.dumps(record) + "\n")

            # Record export in FineTuningDataset table
            ft_record = FineTuningDataset(
                id=str(uuid.uuid4()),
                flagged_diff_id=diff.id,
                image_path=diff.pdf_snippet_path,
                label=label or "",
                split=_assign_split(),
                exported_at=now,
            )
            db.add(ft_record)

    await db.flush()
    return out_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_suggestions(patterns: list[KnowledgePattern]) -> list[str]:
    """Generate human-readable improvement suggestions from top patterns."""
    suggestions: list[str] = []
    for p in patterns:
        if p.occurrence_count == 0:
            continue
        accept_rate = p.accept_count / p.occurrence_count
        if accept_rate > 0.9 and p.occurrence_count >= 5:
            suggestions.append(
                f"Consider enabling auto-accept for {p.difference_type} "
                f"in {p.instrument or 'all instruments'} "
                f"(accept rate {accept_rate:.0%}, n={p.occurrence_count})"
            )
        elif accept_rate < 0.2 and p.occurrence_count >= 5:
            suggestions.append(
                f"Review Claude prompt for {p.difference_type} detection – "
                f"high reject rate ({1 - accept_rate:.0%}, n={p.occurrence_count})"
            )
    return suggestions


_split_counter = 0


def _assign_split() -> str:
    """Assign train/val/test split in 80/10/10 ratio."""
    global _split_counter
    _split_counter += 1
    if _split_counter % 10 == 0:
        return "test"
    elif _split_counter % 10 == 9:
        return "val"
    return "train"
