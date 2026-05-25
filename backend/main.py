"""
ReEngrave FastAPI application.
All API routes for file import, OMR processing,
Claude Vision comparison, review, export, and analytics.
"""

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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.limiter import limiter
from database.connection import create_all_tables, get_db
from database.models import (
    AutoAcceptRule,
    ComparisonSession,
    FlaggedDifference,
    GradusScore,
    KnowledgePattern,
    Score,
    AutoAcceptRuleResponse,
    ComparisonSessionResponse,
    FlaggedDiffResponse,
    GradusScoreResponse,
    KnowledgePatternResponse,
    ScoreResponse,
    User,
)
from dependencies import get_current_user
from modules import (
    analytics,
    claude_vision,
    claude_vision_omr,
    export_module,
    file_import,
    local_omr,
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

# Serve uploaded files (snippet images, PDFs) as static assets
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Routers
app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(webhook_router)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class DecisionRequest(BaseModel):
    decision: str  # accept | reject | edit
    edit_value: Optional[str] = None


class BulkDecideRequest(BaseModel):
    diff_ids: list[str]
    decision: str


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
    omr_engine: str = Query("local", regex="^(local|claude_vision)$"),
):
    """Run OMR on a score's PDF.

    Engines:
      - ``local`` (default): in-house YOLOv8 + classical-CV pipeline in
        ``tools/omr`` (see ``backend/modules/local_omr.py``).
      - ``claude_vision``: Claude Vision API reads each page directly
        (slower, costs API tokens, but supports per-page progress).
    """
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    if not score.original_pdf_path:
        raise HTTPException(status_code=400, detail="No PDF available for OMR")

    score.status = "processing"
    score.metadata_json = {"omr_engine": omr_engine, "omr_progress": {
        "total_pages": 0, "current_page": 0, "status": "starting", "failed_pages": [],
    }}
    await db.commit()

    async def _run_omr():
        from database.connection import AsyncSessionLocal

        async def _progress_callback(current_page: int, total_pages: int, failed_pages: list[int]):
            """Update score.metadata_json with progress after each page."""
            async with AsyncSessionLocal() as progress_session:
                res = await progress_session.execute(select(Score).where(Score.id == score_id))
                ps = res.scalar_one_or_none()
                if ps:
                    ps.metadata_json = {
                        "omr_engine": omr_engine,
                        "omr_progress": {
                            "total_pages": total_pages,
                            "current_page": current_page,
                            "status": "processing",
                            "failed_pages": failed_pages,
                        },
                    }
                    ps.updated_at = datetime.utcnow()
                    await progress_session.commit()

        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Score).where(Score.id == score_id))
            s = res.scalar_one_or_none()
            if s is None:
                return
            try:
                output_dir = os.path.join(settings.upload_dir, score_id)
                if omr_engine == "claude_vision":
                    omr = await claude_vision_omr.run_claude_vision_omr(
                        s.original_pdf_path, output_dir,
                        progress_callback=_progress_callback,
                    )
                    s.musicxml_path = omr.musicxml_path or s.musicxml_path
                    s.status = "review" if omr.musicxml_path else "error"
                    meta = {"omr_engine": omr_engine}
                    if omr.error_message:
                        meta["omr_error"] = omr.error_message
                    if omr.measures_count:
                        meta["measures_count"] = omr.measures_count
                    if omr.confidence_score:
                        meta["confidence_score"] = omr.confidence_score
                    s.metadata_json = meta
                else:
                    # local (YOLO) — primary engine. No per-page progress
                    # callback (runs inside asyncio.to_thread); we still
                    # emit a single transition for the UI.
                    omr = await local_omr.run_local_omr(
                        s.original_pdf_path, output_dir,
                    )
                    s.musicxml_path = omr.musicxml_path or s.musicxml_path
                    s.status = "review" if omr.musicxml_path else "error"
                    meta = {"omr_engine": omr_engine}
                    if omr.omr_json_path:
                        meta["omr_json_path"] = omr.omr_json_path
                    if omr.confidence_score:
                        meta["confidence_score"] = omr.confidence_score
                    if omr.measures_count:
                        meta["measures_count"] = omr.measures_count
                    if omr.pages_processed:
                        meta["omr_pages"] = omr.pages_processed
                    if omr.runtime_seconds:
                        meta["omr_runtime_s"] = omr.runtime_seconds
                    if omr.error_message:
                        meta["omr_error"] = omr.error_message
                    s.metadata_json = meta
            except Exception as exc:
                s.status = "error"
                s.metadata_json = {"omr_engine": omr_engine, "error": str(exc)}
            s.updated_at = datetime.utcnow()
            await session.commit()

    background_tasks.add_task(_run_omr)
    return {"score_id": score_id, "status": "processing", "omr_engine": omr_engine}


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
        import json as _json
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

                # Load learned patterns from knowledge base to feed into Claude prompt
                patterns_result = await session.execute(select(KnowledgePattern))
                knowledge_patterns = [
                    {
                        "instrument": p.instrument,
                        "difference_type": p.difference_type,
                        "occurrence_count": p.occurrence_count,
                        "accept_rate": p.accept_count / max(p.occurrence_count, 1),
                    }
                    for p in patterns_result.scalars().all()
                ]

                # Load most recent XML consensus comparison to pre-flag measures
                cs_result = await session.execute(
                    select(ComparisonSession)
                    .where(ComparisonSession.result_json.isnot(None))
                    .order_by(ComparisonSession.created_at.desc())
                    .limit(1)
                )
                comparison_session = cs_result.scalar_one_or_none()
                flagged_measures: dict[int, float] = {}
                if comparison_session and comparison_session.result_json:
                    try:
                        cs_data = _json.loads(comparison_session.result_json)
                        per_measure = cs_data.get("per_measure_agreement", [])
                        for entry in per_measure:
                            agreement_pct = entry.get("agreement_pct", 100.0) / 100.0
                            if agreement_pct < 0.9:
                                flagged_measures[entry["measure_num"]] = agreement_pct
                    except Exception:
                        flagged_measures = {}

                diffs = await claude_vision.compare_score_measures(
                    s.original_pdf_path, s.musicxml_path, metadata,
                    knowledge_patterns=knowledge_patterns,
                    flagged_measures=flagged_measures if flagged_measures else None,
                )
                snippets_dir = os.path.join(settings.upload_dir, score_id, "snippets")
                os.makedirs(snippets_dir, exist_ok=True)

                for d in diffs:
                    diff_id = str(uuid.uuid4())

                    # Save snippet images to disk so the frontend can display them
                    pdf_snippet_path = ""
                    xml_snippet_path = ""
                    if d.pdf_image_b64:
                        pdf_file = os.path.join(snippets_dir, f"{diff_id}_pdf.png")
                        import base64 as _b64
                        with open(pdf_file, "wb") as fh:
                            fh.write(_b64.b64decode(d.pdf_image_b64))
                        pdf_snippet_path = os.path.relpath(pdf_file, settings.upload_dir)
                    if d.xml_image_b64:
                        xml_file = os.path.join(snippets_dir, f"{diff_id}_xml.png")
                        with open(xml_file, "wb") as fh:
                            fh.write(_b64.b64decode(d.xml_image_b64))
                        xml_snippet_path = os.path.relpath(xml_file, settings.upload_dir)

                    fd = FlaggedDifference(
                        id=diff_id,
                        score_id=score_id,
                        measure_number=d.measure_number,
                        instrument=d.instrument,
                        time_signature="4/4",
                        key_signature="C major",
                        difference_type=d.difference_type,
                        description=d.description,
                        pdf_snippet_path=pdf_snippet_path,
                        musicxml_snippet_path=xml_snippet_path,
                        audiveris_confidence=0.5,
                        claude_vision_confidence=d.confidence,
                        created_at=datetime.utcnow(),
                    )
                    session.add(fd)

                    # Apply auto-accept rules to newly created diff
                    diff_dict = {
                        "difference_type": d.difference_type,
                        "instrument": d.instrument,
                        "audiveris_confidence": 0.5,
                        "claude_vision_confidence": d.confidence,
                        "era": s.era,
                    }
                    was_auto_accepted = await analytics.apply_auto_accept(diff_dict, session)
                    if was_auto_accepted:
                        fd.human_decision = "accept"
                        fd.auto_accepted = True

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
# Gradus Library routes
# ---------------------------------------------------------------------------


@app.post("/api/gradus/", response_model=GradusScoreResponse)
async def create_gradus_score(
    xml_file: UploadFile = File(...),
    pdf_file: Optional[UploadFile] = File(None),
    title: str = Form(...),
    composer: str = Form(...),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a MusicXML (or .mxl) file as a Gradus master reference score."""
    score_id = str(uuid.uuid4())
    gradus_dir = os.path.join(settings.upload_dir, "gradus", score_id)
    os.makedirs(gradus_dir, exist_ok=True)

    # Save XML file
    xml_filename = xml_file.filename or "score.xml"
    xml_path = os.path.join(gradus_dir, xml_filename)
    content = await xml_file.read()
    with open(xml_path, "wb") as f:
        f.write(content)

    # Save optional PDF file
    pdf_path: Optional[str] = None
    if pdf_file and pdf_file.filename:
        pdf_filename = pdf_file.filename
        pdf_path = os.path.join(gradus_dir, pdf_filename)
        pdf_content = await pdf_file.read()
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)

    gradus = GradusScore(
        id=score_id,
        title=title,
        composer=composer,
        xml_path=xml_path,
        pdf_path=pdf_path,
        notes=notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(gradus)
    await db.flush()

    return GradusScoreResponse.model_validate(gradus)


@app.get("/api/gradus/", response_model=list[GradusScoreResponse])
async def list_gradus_scores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all Gradus master reference scores."""
    result = await db.execute(
        select(GradusScore).order_by(GradusScore.created_at.desc())
    )
    return [GradusScoreResponse.model_validate(g) for g in result.scalars().all()]


@app.delete("/api/gradus/{gradus_id}")
async def delete_gradus_score(
    gradus_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Gradus score and its uploaded files."""
    result = await db.execute(select(GradusScore).where(GradusScore.id == gradus_id))
    gradus = result.scalar_one_or_none()
    if gradus is None:
        raise HTTPException(status_code=404, detail="Gradus score not found")

    # Remove files on disk
    gradus_dir = os.path.join(settings.upload_dir, "gradus", gradus_id)
    import shutil
    if os.path.isdir(gradus_dir):
        shutil.rmtree(gradus_dir, ignore_errors=True)

    await db.delete(gradus)
    await db.flush()

    return {"deleted": gradus_id}


# ---------------------------------------------------------------------------
# Comparison session routes
# ---------------------------------------------------------------------------


@app.post("/api/compare/", response_model=ComparisonSessionResponse)
async def create_comparison_session(
    xml_files: list[UploadFile] = File(...),
    gradus_score_id: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a comparison session from 2–6 uploaded MusicXML files.

    Optionally pin a Gradus master as the reference source.
    The comparison runs synchronously — allow 10–30s for large scores.
    """
    if len(xml_files) < 2:
        raise HTTPException(status_code=400, detail="Upload at least 2 XML files to compare")
    if len(xml_files) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 XML files per comparison")

    session_id = str(uuid.uuid4())
    compare_dir = os.path.join(settings.upload_dir, "compare", session_id)
    os.makedirs(compare_dir, exist_ok=True)

    # Save uploaded files
    saved_paths: list[str] = []
    for xml_file in xml_files:
        filename = xml_file.filename or f"score_{len(saved_paths)}.xml"
        file_path = os.path.join(compare_dir, filename)
        content = await xml_file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        saved_paths.append(file_path)

    # Resolve optional master path
    master_path: Optional[str] = None
    if gradus_score_id:
        g_result = await db.execute(
            select(GradusScore).where(GradusScore.id == gradus_score_id)
        )
        gradus = g_result.scalar_one_or_none()
        if gradus is None:
            raise HTTPException(status_code=404, detail="Gradus score not found")
        master_path = gradus.xml_path

    # Run comparison (synchronous — music21 parsing is CPU-bound)
    try:
        from modules.score_comparison import compare_multiple
        result = compare_multiple(saved_paths, master_path=master_path)
    except Exception as exc:
        result = {
            "labels": [],
            "matrix": [],
            "per_measure_agreement": [],
            "consensus_issues": [],
            "error": str(exc),
        }

    import json as _json
    session = ComparisonSession(
        id=session_id,
        name=name,
        gradus_score_id=gradus_score_id or None,
        xml_paths_json=_json.dumps(saved_paths),
        result_json=_json.dumps(result),
        created_at=datetime.utcnow(),
    )
    db.add(session)
    await db.flush()

    return ComparisonSessionResponse.model_validate(session)


@app.get("/api/compare/", response_model=list[ComparisonSessionResponse])
async def list_comparison_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent comparison sessions (newest first)."""
    result = await db.execute(
        select(ComparisonSession).order_by(ComparisonSession.created_at.desc()).limit(50)
    )
    return [ComparisonSessionResponse.model_validate(s) for s in result.scalars().all()]


@app.get("/api/compare/{session_id}", response_model=ComparisonSessionResponse)
async def get_comparison_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific comparison session and its results."""
    result = await db.execute(
        select(ComparisonSession).where(ComparisonSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Comparison session not found")
    return ComparisonSessionResponse.model_validate(session)


# ---------------------------------------------------------------------------
# Theory check route
# ---------------------------------------------------------------------------


@app.post("/api/scores/{score_id}/theory-check")
async def theory_check(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run music theory sanity checks (rhythm, range, enharmonic) on a score's MusicXML."""
    result = await db.execute(select(Score).where(Score.id == score_id))
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    if not score.musicxml_path:
        raise HTTPException(status_code=400, detail="No MusicXML available – run OMR first")

    try:
        from modules.score_comparison import run_dual_theory_checks
        dual = run_dual_theory_checks(score.musicxml_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Theory check failed: {exc}")

    # Keep the original response shape for backwards-compat (issues/total
    # reflect music21 — what the existing frontend reads). `maestro` is
    # additive: a structured harmony+rhythm analysis from the maestroAnalyst
    # bridge, or null when the bridge is disabled or failed.
    issues = dual["music21"]
    return {
        "score_id": score_id,
        "issues": issues,
        "total": len(issues),
        "maestro": dual["maestro"],
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}
