"""
SQLAlchemy ORM models for ReEngrave.
Uses SQLAlchemy 2.0 declarative style with DeclarativeBase.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# ORM Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Score(Base):
    """Stores a processed score."""

    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    composer: Mapped[str] = mapped_column(String, nullable=False)
    era: Mapped[str] = mapped_column(String, nullable=False)  # baroque/classical/romantic/modern
    source: Mapped[str] = mapped_column(String, nullable=False)  # imslp/upload
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    original_pdf_path: Mapped[str] = mapped_column(String, nullable=False)
    musicxml_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )  # pending/processing/review/complete/error
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    flagged_differences: Mapped[list[FlaggedDifference]] = relationship(
        "FlaggedDifference", back_populates="score", cascade="all, delete-orphan"
    )


class FlaggedDifference(Base):
    """One per measure difference found by Claude Vision."""

    __tablename__ = "flagged_differences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    score_id: Mapped[str] = mapped_column(String, ForeignKey("scores.id"), nullable=False)
    measure_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instrument: Mapped[str] = mapped_column(String, nullable=False)
    time_signature: Mapped[str] = mapped_column(String, nullable=False, default="4/4")
    key_signature: Mapped[str] = mapped_column(String, nullable=False, default="C major")
    difference_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # note/rhythm/articulation/dynamic/beam/slur/accidental/clef/other
    description: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_snippet_path: Mapped[str] = mapped_column(String, nullable=False, default="")
    musicxml_snippet_path: Mapped[str] = mapped_column(String, nullable=False, default="")
    audiveris_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    claude_vision_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    human_decision: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # accept/reject/edit
    human_edit_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    auto_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_accept_rule_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("auto_accept_rules.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    # Relationships
    score: Mapped[Score] = relationship("Score", back_populates="flagged_differences")
    auto_accept_rule: Mapped[Optional[AutoAcceptRule]] = relationship(
        "AutoAcceptRule", back_populates="flagged_differences"
    )
    finetuning_records: Mapped[list[FineTuningDataset]] = relationship(
        "FineTuningDataset", back_populates="flagged_diff", cascade="all, delete-orphan"
    )


class KnowledgePattern(Base):
    """Patterns learned from accepted/rejected corrections."""

    __tablename__ = "knowledge_patterns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    pattern_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # audiveris_failure/claude_vision_prompt/instrument_quirk
    instrument: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    difference_type: Mapped[str] = mapped_column(String, nullable=False)
    era: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pattern_description: Mapped[str] = mapped_column(Text, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accept_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reject_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    example_ids: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # list of FlaggedDifference UUIDs
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    # Relationships
    auto_accept_rules: Mapped[list[AutoAcceptRule]] = relationship(
        "AutoAcceptRule", back_populates="pattern", cascade="all, delete-orphan"
    )


class AutoAcceptRule(Base):
    """Auto-accept rules derived from patterns."""

    __tablename__ = "auto_accept_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    pattern_id: Mapped[str] = mapped_column(
        String, ForeignKey("knowledge_patterns.id"), nullable=False
    )
    rule_description: Mapped[str] = mapped_column(Text, nullable=False)
    instrument: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    difference_type: Mapped[str] = mapped_column(String, nullable=False)
    min_audiveris_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    min_claude_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    min_confirmations: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    current_confirmations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    # Relationships
    pattern: Mapped[KnowledgePattern] = relationship(
        "KnowledgePattern", back_populates="auto_accept_rules"
    )
    flagged_differences: Mapped[list[FlaggedDifference]] = relationship(
        "FlaggedDifference", back_populates="auto_accept_rule"
    )


class ClaudePromptVersion(Base):
    """Tracks Claude Vision prompt refinements."""

    __tablename__ = "claude_prompt_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    accept_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reject_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )


class FineTuningDataset(Base):
    """Export records for eventual vision model fine-tuning."""

    __tablename__ = "finetuning_dataset"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    flagged_diff_id: Mapped[str] = mapped_column(
        String, ForeignKey("flagged_differences.id"), nullable=False
    )
    image_path: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    split: Mapped[str] = mapped_column(String, nullable=False, default="train")  # train/val/test
    exported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    flagged_diff: Mapped[FlaggedDifference] = relationship(
        "FlaggedDifference", back_populates="finetuning_records"
    )


# ---------------------------------------------------------------------------
# Pydantic Response Schemas
# ---------------------------------------------------------------------------

class ScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    composer: str
    era: str
    source: str
    source_url: Optional[str]
    original_pdf_path: str
    musicxml_path: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    metadata_json: Optional[dict]


class FlaggedDiffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    score_id: str
    measure_number: int
    instrument: str
    time_signature: str
    key_signature: str
    difference_type: str
    description: str
    pdf_snippet_path: str
    musicxml_snippet_path: str
    audiveris_confidence: float
    claude_vision_confidence: float
    human_decision: Optional[str]
    human_edit_value: Optional[str]
    human_reviewed_at: Optional[datetime]
    auto_accepted: bool
    auto_accept_rule_id: Optional[str]
    created_at: datetime


class KnowledgePatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pattern_type: str
    instrument: Optional[str]
    difference_type: str
    era: Optional[str]
    pattern_description: str
    occurrence_count: int
    accept_count: int
    reject_count: int
    edit_count: int
    confidence_threshold: float
    example_ids: Optional[list]
    created_at: datetime
    updated_at: datetime


class AutoAcceptRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pattern_id: str
    rule_description: str
    instrument: Optional[str]
    difference_type: str
    min_audiveris_confidence: float
    min_claude_confidence: float
    min_confirmations: int
    current_confirmations: int
    is_active: bool
    created_at: datetime


class ClaudePromptVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    prompt_text: str
    accept_rate: Optional[float]
    reject_rate: Optional[float]
    total_uses: int
    is_active: bool
    created_at: datetime


class FineTuningDatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    flagged_diff_id: str
    image_path: str
    label: str
    split: str
    exported_at: Optional[datetime]
