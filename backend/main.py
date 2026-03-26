"""
ReEngrave FastAPI application.
All API routes for IMSLP search, file import, OMR processing,
Claude Vision comparison, review, export, and analytics.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.limiter import limiter
from database.connection import create_all_tables, get_db
from database.models import (
    AutoAcceptRule,
    FlaggedDifference,
    KnowledgePattern,
    Score,
    AutoAcceptRuleResponse,
    FlaggedDiffResponse,
    KnowledgePatternResponse,
    ScoreResponse,
    User,
)
from dependencies import get_current_user
from modules import (
    analytics,
    audiveris_omr,
    claude_vision,
    export_module,
    file_import,
    imslp_agent,
)
from modules.export_module import ExportFormat
from routers.auth import router as auth_router
from routers.payments import router as payments_router, webhook_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup."""
    await create_all_tables()
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = FastAPI(
    title="ReEngrave API",
    version="0.2.0",
    description="Music score re-engraving pipeline with OMR and Claude Vision",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS – must allow credentials for httpOnly refresh cookie
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(webhook_router)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class DownloadScoreRequest(BaseModel):
    url: str
    score_title: str
    composer: str
    era: str


class DecisionRequest(BaseModel):
    decision: str  # accept | reject | edit
    edit_value: Optional[str] = None


class BulkDecideRequest(BaseModel):
    diff_ids: list[str]
    decision: str


# ---------------------------------------------------------------------------
# Background task helpers
# ---------------------------------------------------------------------------


async def _bg_download_and_process(
    score_id: str,
    url: str,
    db_session_factory,
) -> None:
    """Background task: download PDF from IMSLP and run OMR."""
    from database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Score).where(Score.id == score_id))
        score = result.scalar_one_or_none()
        if score is None:
            return

        try:
            score.status = "processing"
            await db.commit()

            local_path = await imslp_agent.download_score(url, settings.upload_dir)
            score.original_pdf_path = local_path
            await db.commit()

            omr_result = await audiveris_omr.run_audiveris(
                local_path, os.path.join(settings.upload_dir, score_id)
            )
            if omr_result.musicxml_path:
                score.musicxml_path = omr_result.musicxml_path
                score.status = "review"
            else:
                score.status = "error"
                score.metadata_json = {"error": omr_result.error_message}

            await db.commit()
        except Exception as exc:
            score.status = "error"
            score.metadata_json = {"error": str(exc)}
            await db.commit()


# ---------------------------------------------------------------------------
# IMSLP routes
# ---------------------------------------------------------------------------


@app.get("/api/imslp/search")
async def search_imslp(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """Search IMSLP for scores matching the query."""
    results = await imslp_agent.search_imslp(q, max_results)
    return [
        {
            "title": r.title,
            "composer": r.composer,
            "era": r.era,
            "url": r.url,
            "pdf_urls": r.pdf_urls,
            "description": r.description,
        }
        for r in results
    ]


@app.post("/api/imslp/download")
async def download_imslp_score(
    body: DownloadScoreRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download an IMSLP PDF and start the OMR pipeline as a background task."""
    score_id = str(uuid.uuid4())
    score = Score(
        id=score_id,
        title=body.score_title,
        composer=body.composer,
        era=body.era,
        source="imslp",
        source_url=body.url,
        original_pdf_path="",  # will be set by background task
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(score)
    await db.flush()

    background_tasks.add_task(_bg_download_and_process, score_id, body.url, None)

    return {"score_id": score_id, "status": "pending"}


# ---------------------------------------------------------------------------
# File import routes
# ---------------------------------------------------------------------------


@app.post("/api/import/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    title: str = Form(...),
    composer: str = Form(...),
    era: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF score. Creates a Score record and saves the file."""
    import_result = await file_import.save_uploaded_file(file, settings.upload_dir)
    if import_result.file_type != "pdf":
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF")

    score_id = str(uuid.uuid4())
    score = Score(
        id=score_id,
        title=title,
        composer=composer,
        era=era,
        source="upload",
        original_pdf_path=import_result.local_path,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(score)
    await db.flush()

    return ScoreResponse.model_validate(score)


@app.post("/api/import/musicxml")
async def upload_musicxml(
    file: UploadFile = File(...),
    title: str = Form(...),
    composer: str = Form(...),
    era: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a MusicXML file directly (skips OMR step)."""
    import_result = await file_import.save_uploaded_file(file, settings.upload_dir)
    if import_result.file_type != "musicxml":
        raise HTTPException(status_code=400, detail="Uploaded file must be MusicXML")

    score_id = str(uuid.uuid4())
    score = Score(
        id=score_id,
        title=title,
        composer=composer,
        era=era,
        source="upload",
        original_pdf_path="",
        musicxml_path=import_result.local_path,
        status="review",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(score)
    await db.flush()

    return ScoreResponse.model_validate(score)


# ---------------------------------------------------------------------------
# Processing routes
# ---------------------------------------------------------------------------


@app.post("/api/scores/{score_id}/process/omr")
async def run_omr(
    score_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run Audiveris OMR on a score's PDF."""
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    if not score.original_pdf_path:
        raise HTTPException(status_code=400, detail="No PDF available for OMR")

    score.status = "processing"
    await db.flush()

    async def _run_omr():
        from database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Score).where(Score.id == score_id))
            s = res.scalar_one_or_none()
            if s is None:
                return
            try:
                omr = await audiveris_omr.run_audiveris(
                    s.original_pdf_path,
                    os.path.join(settings.upload_dir, score_id),
                )
                s.musicxml_path = omr.musicxml_path or s.musicxml_path
                s.status = "review" if omr.musicxml_path else "error"
                if omr.error_message:
                    s.metadata_json = {"omr_error": omr.error_message}
            except Exception as exc:
                s.status = "error"
                s.metadata_json = {"error": str(exc)}
            s.updated_at = datetime.utcnow()
            await session.commit()

    background_tasks.add_task(_run_omr)
    return {"score_id": score_id, "status": "processing"}


@app.post("/api/scores/{score_id}/process/compare")
async def run_comparison(
    score_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run Claude Vision comparison. Requires payment (or admin bypass)."""
    from routers.payments import user_has_vision_access

    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    if not score.musicxml_path:
        raise HTTPException(status_code=400, detail="No MusicXML available – run OMR first")

    if not await user_has_vision_access(current_user, score_id, db):
        raise HTTPException(
            status_code=402,
            detail="Payment required for Vision AI comparison",
        )

    score.status = "processing"
    await db.flush()

    async def _run_compare():
        from database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Score).where(Score.id == score_id))
            s = res.scalar_one_or_none()
            if s is None:
                return
            try:
                metadata = {
                    "title": s.title,
                    "composer": s.composer,
                    "era": s.era,
                }
                diffs = await claude_vision.compare_score_measures(
                    s.original_pdf_path, s.musicxml_path, metadata
                )
                for d in diffs:
                    fd = FlaggedDifference(
                        id=str(uuid.uuid4()),
                        score_id=score_id,
                        measure_number=d.measure_number,
                        instrument=d.instrument,
                        time_signature="4/4",
                        key_signature="C major",
                        difference_type=d.difference_type,
                        description=d.description,
                        pdf_snippet_path="",
                        musicxml_snippet_path="",
                        audiveris_confidence=0.5,
                        claude_vision_confidence=d.confidence,
                        created_at=datetime.utcnow(),
                    )
                    session.add(fd)
                s.status = "review"
                s.updated_at = datetime.utcnow()
            except Exception as exc:
                s.status = "error"
                s.metadata_json = {"compare_error": str(exc)}
                s.updated_at = datetime.utcnow()
            await session.commit()

    background_tasks.add_task(_run_compare)
    return {"score_id": score_id, "status": "processing"}


@app.get("/api/scores/{score_id}/status")
async def get_score_status(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current processing status of a score."""
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"score_id": score_id, "status": score.status, "updated_at": score.updated_at}


# ---------------------------------------------------------------------------
# Score CRUD routes
# ---------------------------------------------------------------------------


@app.get("/api/scores", response_model=list[ScoreResponse])
async def list_scores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all scores."""
    result = await db.execute(select(Score).order_by(Score.created_at.desc()))
    return [ScoreResponse.model_validate(s) for s in result.scalars().all()]


@app.get("/api/scores/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get score details by ID."""
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    return ScoreResponse.model_validate(score)


@app.delete("/api/scores/{score_id}")
async def delete_score(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a score and its associated files."""
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")

    await db.delete(score)
    await db.flush()

    return {"deleted": score_id}


# ---------------------------------------------------------------------------
# Review routes
# ---------------------------------------------------------------------------


@app.get("/api/scores/{score_id}/diffs", response_model=list[FlaggedDiffResponse])
async def list_diffs(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all flagged differences for a score."""
    result = await db.execute(
        select(FlaggedDifference)
        .where(FlaggedDifference.score_id == score_id)
        .order_by(FlaggedDifference.measure_number)
    )
    return [FlaggedDiffResponse.model_validate(d) for d in result.scalars().all()]


@app.patch("/api/diffs/{diff_id}/decision")
async def record_decision(
    diff_id: str,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a human decision (accept/reject/edit) for a flagged difference."""
    if body.decision not in ("accept", "reject", "edit"):
        raise HTTPException(status_code=400, detail="decision must be accept, reject, or edit")
    if body.decision == "edit" and not body.edit_value:
        raise HTTPException(status_code=400, detail="edit_value required for edit decision")

    result = await db.execute(
        select(FlaggedDifference).where(FlaggedDifference.id == diff_id)
    )
    diff = result.scalar_one_or_none()
    if diff is None:
        raise HTTPException(status_code=404, detail="Difference not found")

    diff.human_decision = body.decision
    diff.human_edit_value = body.edit_value
    diff.human_reviewed_at = datetime.utcnow()
    await db.flush()

    return FlaggedDiffResponse.model_validate(diff)


@app.post("/api/scores/{score_id}/diffs/bulk-decide")
async def bulk_decide(
    score_id: str,
    body: BulkDecideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk accept or reject multiple flagged differences."""
    if body.decision not in ("accept", "reject"):
        raise HTTPException(status_code=400, detail="decision must be accept or reject")

    updated = 0
    for diff_id in body.diff_ids:
        result = await db.execute(
            select(FlaggedDifference).where(
                FlaggedDifference.id == diff_id,
                FlaggedDifference.score_id == score_id,
            )
        )
        diff = result.scalar_one_or_none()
        if diff is not None:
            diff.human_decision = body.decision
            diff.human_reviewed_at = datetime.utcnow()
            updated += 1

    await db.flush()
    return {"updated": updated}


# ---------------------------------------------------------------------------
# Export routes
# ---------------------------------------------------------------------------


@app.get("/api/scores/{score_id}/export")
async def export_score(
    score_id: str,
    format: str = Query("pdf", regex="^(pdf|musicxml|lilypond)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger score export and return the file as a download."""
    try:
        fmt = ExportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}")

    export_subdir = os.path.join(settings.export_dir, score_id)
    try:
        file_path = await export_module.export_score(score_id, fmt, export_subdir, db)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream",
    )


@app.get("/api/scores/{score_id}/export/status")
async def export_status(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return export job status."""
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")

    return {"score_id": score_id, "export_status": "ready" if score.status == "complete" else score.status}


# ---------------------------------------------------------------------------
# Analytics routes
# ---------------------------------------------------------------------------


@app.get("/api/analytics/report")
async def get_analytics_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the learning report with stats and suggestions."""
    return await analytics.generate_learning_report(db)


@app.get("/api/analytics/patterns", response_model=list[KnowledgePatternResponse])
async def get_patterns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all knowledge patterns."""
    result = await db.execute(
        select(KnowledgePattern).order_by(KnowledgePattern.occurrence_count.desc())
    )
    return [KnowledgePatternResponse.model_validate(p) for p in result.scalars().all()]


@app.post("/api/analytics/update")
async def trigger_analytics_update(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger a full pattern analysis update."""
    await analytics.update_knowledge_base(db)
    await analytics.evaluate_auto_accept_rules(db)
    return {"status": "updated"}


@app.get("/api/analytics/finetuning-export")
async def trigger_finetuning_export(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger fine-tuning dataset export."""
    output_path = await analytics.export_finetuning_dataset(
        db, os.path.join(settings.export_dir, "finetuning")
    )
    return {"status": "exported", "path": output_path}


@app.get("/api/analytics/auto-rules", response_model=list[AutoAcceptRuleResponse])
async def get_auto_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active auto-accept rules."""
    result = await db.execute(
        select(AutoAcceptRule).where(AutoAcceptRule.is_active.is_(True))
    )
    return [AutoAcceptRuleResponse.model_validate(r) for r in result.scalars().all()]


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}
