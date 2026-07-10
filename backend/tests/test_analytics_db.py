"""DB-backed tests for analytics.apply_auto_accept and
analyze_correction_patterns — covers the auto-accept self-reinforcement fix.

Uses an in-memory SQLite DB (via the same async SQLAlchemy stack as
production) rather than mocks, since the bug lived in the interaction
between apply_auto_accept's return value and the WHERE clause in
analyze_correction_patterns.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import AutoAcceptRule, Base, FlaggedDifference, KnowledgePattern
from modules import analytics


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _make_active_rule(
    db_session,
    *,
    difference_type: str = "note",
    instrument: str | None = None,
    min_audiveris_confidence: float = 0.7,
    min_claude_confidence: float = 0.7,
) -> AutoAcceptRule:
    pattern = KnowledgePattern(
        id=str(uuid.uuid4()),
        pattern_type="instrument_quirk",
        instrument=instrument,
        difference_type=difference_type,
        pattern_description="test pattern",
        occurrence_count=10,
        accept_count=9,
        reject_count=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(pattern)

    rule = AutoAcceptRule(
        id=str(uuid.uuid4()),
        pattern_id=pattern.id,
        rule_description="auto-accept test rule",
        instrument=instrument,
        difference_type=difference_type,
        min_audiveris_confidence=min_audiveris_confidence,
        min_claude_confidence=min_claude_confidence,
        min_confirmations=10,
        current_confirmations=10,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(rule)
    await db_session.flush()
    return rule


# ---------------------------------------------------------------------------
# apply_auto_accept — must return the matched rule id (not just True/False)
# ---------------------------------------------------------------------------


class TestApplyAutoAccept:
    async def test_matching_diff_returns_rule_id(self, db_session):
        rule = await _make_active_rule(db_session)
        diff = {
            "difference_type": "note",
            "instrument": "violin",
            "audiveris_confidence": 0.9,
            "claude_vision_confidence": 0.9,
            "era": "",
        }
        result = await analytics.apply_auto_accept(diff, db_session)
        assert result == rule.id

    async def test_low_omr_confidence_does_not_match(self, db_session):
        # This is the scenario the hardcoded audiveris_confidence=0.5 created:
        # a rule requiring 0.7 could never fire. With a real (low) confidence
        # it correctly still doesn't fire.
        await _make_active_rule(db_session, min_audiveris_confidence=0.7)
        diff = {
            "difference_type": "note",
            "instrument": "violin",
            "audiveris_confidence": 0.5,
            "claude_vision_confidence": 0.9,
            "era": "",
        }
        result = await analytics.apply_auto_accept(diff, db_session)
        assert result is None

    async def test_high_omr_confidence_matches(self, db_session):
        # With a real, page-derived confidence above the rule's threshold,
        # the rule can now actually fire (the point of the fix).
        rule = await _make_active_rule(db_session, min_audiveris_confidence=0.7)
        diff = {
            "difference_type": "note",
            "instrument": "violin",
            "audiveris_confidence": 0.82,
            "claude_vision_confidence": 0.9,
            "era": "",
        }
        result = await analytics.apply_auto_accept(diff, db_session)
        assert result == rule.id

    async def test_no_active_rules_returns_none(self, db_session):
        diff = {
            "difference_type": "note",
            "instrument": "violin",
            "audiveris_confidence": 0.9,
            "claude_vision_confidence": 0.9,
            "era": "",
        }
        result = await analytics.apply_auto_accept(diff, db_session)
        assert result is None


# ---------------------------------------------------------------------------
# analyze_correction_patterns — auto-accepted rows must not self-reinforce
# ---------------------------------------------------------------------------


class TestAnalyzeCorrectionPatternsExcludesAutoAccepts:
    async def test_auto_accepted_rows_are_excluded(self, db_session):
        rule = await _make_active_rule(db_session, difference_type="note", instrument="violin")

        # A real human accept.
        db_session.add(FlaggedDifference(
            id=str(uuid.uuid4()),
            score_id="score-1",
            measure_number=1,
            instrument="violin",
            difference_type="note",
            description="d1",
            human_decision="accept",
            auto_accept_rule_id=None,
            created_at=datetime.utcnow(),
        ))
        # An auto-accepted row (rule fired) — must NOT count toward the
        # pattern's accept rate, or the rule would self-reinforce.
        db_session.add(FlaggedDifference(
            id=str(uuid.uuid4()),
            score_id="score-1",
            measure_number=2,
            instrument="violin",
            difference_type="note",
            description="d2",
            human_decision="accept",
            auto_accepted=True,
            auto_accept_rule_id=rule.id,
            created_at=datetime.utcnow(),
        ))
        await db_session.flush()

        analyses = await analytics.analyze_correction_patterns(db_session)
        matching = [a for a in analyses if a.instrument == "violin" and a.difference_type == "note"]
        assert len(matching) == 1
        assert matching[0].occurrence_count == 1  # only the human-decided row

    async def test_all_auto_accepted_yields_no_pattern(self, db_session):
        rule = await _make_active_rule(db_session, difference_type="rhythm", instrument="cello")
        db_session.add(FlaggedDifference(
            id=str(uuid.uuid4()),
            score_id="score-1",
            measure_number=1,
            instrument="cello",
            difference_type="rhythm",
            description="d1",
            human_decision="accept",
            auto_accepted=True,
            auto_accept_rule_id=rule.id,
            created_at=datetime.utcnow(),
        ))
        await db_session.flush()

        analyses = await analytics.analyze_correction_patterns(db_session)
        matching = [a for a in analyses if a.instrument == "cello" and a.difference_type == "rhythm"]
        assert matching == []
