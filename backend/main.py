"""
ReEngrave FastAPI application.
All API routes for file import, OMR processing,
Claude Vision comparison, review, export, and analytics.
"""

import logging
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

from core import signed_urls
from core.config import check_startup_secret, settings
from core.limiter import limiter, setting_limit
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
    staged_omr,
)
from modules.export_module import ExportFormat
from routers.auth import router as auth_router
from routers.payments import router as payments_router, webhook_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Refuse the default secret, then create DB tables on startup."""
    check_startup_secret(settings)
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


class DecisionRequest(BaseModel):
    decision: str  # accept | reject | edit
    edit_value: Optional[str] = None


class BulkDecideRequest(BaseModel):
    diff_ids: list[str]
    decision: str


# ---------------------------------------------------------------------------
# Ownership / upload helpers
# ---------------------------------------------------------------------------


async def _owned_score(db: AsyncSession, score_id: str, user: User) -> Score:
    """The score if *user* owns it; 404 otherwise (never 403, so another
    user's score id is indistinguishable from a missing one)."""
    result = await db.execute(
        select(Score).where(Score.id == score_id, Score.user_id == user.id)
    )
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(status_code=404, detail="Score not found")
    return score


def _is_admin(user: User) -> bool:
    return user.role == "admin" or (user.email or "").lower() in settings.admin_email_list


def _upload_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, file_import.UploadTooLargeError):
        return HTTPException(status_code=413, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


async def _save_named_upload(
    upload: UploadFile, dest_dir: str, allowed_exts: tuple[str, ...], default: str,
) -> str:
    """Write a client upload under *dest_dir* as `<uuid>_<basename>` after
    the extension allowlist and the size cap; return the path."""
    try:
        stored = file_import.safe_stored_name(upload.filename, allowed_exts, default)
        content = await file_import.read_upload_capped(upload, settings.max_upload_bytes)
    except ValueError as exc:
        raise _upload_http_error(exc)
    path = os.path.join(dest_dir, stored)
    with open(path, "wb") as f:
        f.write(content)
    return path


# ---------------------------------------------------------------------------
# Signed file route (replaces the unauthenticated StaticFiles mount)
# ---------------------------------------------------------------------------


@app.get("/uploads/{path:path}")
async def serve_upload(path: str, t: Optional[str] = Query(None)):
    """Serve a file under upload_dir only with a valid `?t=<exp>.<sig>`
    (core/signed_urls.py). Missing, expired or forged token, a path that
    resolves outside upload_dir, or no such file: 404 for all of them."""
    if not signed_urls.verify_token(path, t):
        raise HTTPException(status_code=404, detail="Not found")
    target = signed_urls.resolve_inside_uploads(path)
    if target is None:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path=str(target), headers={"X-Content-Type-Options": "nosniff"})


# ---------------------------------------------------------------------------
# File import routes
# ---------------------------------------------------------------------------


@app.post("/api/import/upload")
@limiter.limit(setting_limit("rate_limit_upload"))
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    composer: str = Form(...),
    era: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PDF score. Creates a Score record and saves the file."""
    try:
        import_result = await file_import.save_uploaded_file(
            file, settings.upload_dir, max_bytes=settings.max_upload_bytes)
    except ValueError as exc:
        raise _upload_http_error(exc)
    if import_result.file_type != "pdf":
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF")

    score_id = str(uuid.uuid4())
    score = Score(
        id=score_id,
        user_id=current_user.id,
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
@limiter.limit(setting_limit("rate_limit_musicxml"))
async def upload_musicxml(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    composer: str = Form(...),
    era: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a MusicXML file directly (skips OMR step)."""
    try:
        import_result = await file_import.save_uploaded_file(
            file, settings.upload_dir, max_bytes=settings.max_upload_bytes)
    except ValueError as exc:
        raise _upload_http_error(exc)
    if import_result.file_type != "musicxml":
        raise HTTPException(status_code=400, detail="Uploaded file must be MusicXML")

    score_id = str(uuid.uuid4())
    score = Score(
        id=score_id,
        user_id=current_user.id,
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
@limiter.limit(setting_limit("rate_limit_process_omr"))
async def run_omr(
    request: Request,
    score_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    omr_engine: str = Query("local", regex="^(local|claude_vision|staged)$"),
    pages: Optional[str] = Query(
        None,
        description="STAGED ENGINE ONLY (ROADMAP 3.3): a page range for a "
                    "whole movement, e.g. '0-26' or '0,2,4-6' (same syntax "
                    "as the staged CLI's --pages). Omitted keeps the "
                    "existing OMR_MAX_PAGES cap — nothing changes for a "
                    "caller that sends none.",
    ),
):
    """Run OMR on a score's PDF.

    Engines:
      - ``local`` (default): in-house YOLOv8 + classical-CV pipeline in
        ``tools/omr`` (see ``backend/modules/local_omr.py``). This is the
        LEGACY reader (CLAUDE.md §3) and stays the default until Phase 3.
      - ``claude_vision``: Claude Vision API reads each page directly
        (slower, costs API tokens, but supports per-page progress).
      - ``staged`` (experimental, ROADMAP 3.3): the STAGED pipeline in
        ``tools/omr/staged`` (see ``backend/modules/staged_omr.py``). The
        product path per CLAUDE.md §3, but not yet the web app's default —
        it does not yet carry the legacy filters or the LilyPond default
        this route's ``local`` engine gets from ``export_module``. Accepts
        an optional ``pages`` range (a whole movement); the estimated cost
        (``tools.omr.staged.budget``) is refused up front, with the
        estimate in the error, when it exceeds ``OMR_JOB_BUDGET_S``.
    """
    score = await _owned_score(db, score_id, current_user)
    if not score.original_pdf_path:
        raise HTTPException(status_code=400, detail="No PDF available for OMR")

    if pages is not None and omr_engine != "staged":
        raise HTTPException(
            status_code=400,
            detail=f"pages={pages!r} is only supported for "
                  f"omr_engine=staged (got omr_engine={omr_engine!r})",
        )

    # ⚠️⚠️ ROADMAP 3.3, second half: THE JOB BUDGET, CHECKED BEFORE
    # `score.status = "processing"` IS EVEN SET — a request whose estimate
    # exceeds the server limit is refused up front, with the estimate in
    # the error, never silently truncated to OMR_MAX_PAGES and never left
    # to fail hours into a background task. `pages=None` (no whole-movement
    # range requested) skips this entirely: the existing OMR_MAX_PAGES cap
    # is cheap enough that CLAUDE.md's own budget constants were never
    # meant to gate it, and a caller that sends nothing sees no behaviour
    # change at all.
    page_list: Optional[list[int]] = None
    budget: Optional[dict] = None
    if omr_engine == "staged" and pages is not None:
        try:
            page_list = staged_omr.parse_page_range(pages)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"could not parse pages={pages!r}: {exc}",
            )
        if not page_list:
            raise HTTPException(
                status_code=400, detail=f"pages={pages!r} names no pages")

        budget = staged_omr.estimate_budget_s(len(page_list))
        logger.info(
            "staged OMR job budget for score %s, %d pages: expected %.0fs "
            "(~%.1fh), upper bound %.0fs (~%.1fh) -- %s",
            score_id, len(page_list),
            budget["total_s_expected"], budget["total_s_expected"] / 3600,
            budget["total_s_upper_bound"], budget["total_s_upper_bound"] / 3600,
            budget["caveat"],
        )
        # ⚠️ THE UPPER BOUND, NOT THE EXPECTED FIGURE — the same
        # conservative choice CLAUDE.md rule 5 asks for ("no default flips
        # on agreement with our own reading"): refusing on the smaller
        # number would let a request through whose real cost, if the
        # direction-text scan gate never fires, exceeds the limit anyway.
        if budget["total_s_upper_bound"] > settings.omr_job_budget_s:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"staged job over budget: {len(page_list)} pages "
                    f"estimated at {budget['total_s_upper_bound']:.0f}s "
                    f"(~{budget['total_s_upper_bound'] / 3600:.1f}h, upper "
                    f"bound) against a server limit of "
                    f"{settings.omr_job_budget_s:.0f}s "
                    f"(~{settings.omr_job_budget_s / 3600:.1f}h). "
                    f"Expected (with the direction-text scan gate): "
                    f"{budget['total_s_expected']:.0f}s. Data point: "
                    f"{budget['data_point']}. Request fewer pages, or raise "
                    f"OMR_JOB_BUDGET_S."
                ),
            )

    score.status = "processing"
    score.metadata_json = {"omr_engine": omr_engine, "omr_progress": {
        "total_pages": 0, "current_page": 0, "status": "starting", "failed_pages": [],
    }}
    if budget is not None:
        # ⚠️ STORED, NOT JUST LOGGED — CLAUDE.md §1: the user must be able
        # to see how many pages this run priced and what it cost.
        score.metadata_json["omr_budget"] = budget
        score.metadata_json["omr_pages_requested"] = page_list
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
                elif omr_engine == "staged":
                    # STAGED (ROADMAP 3.3, experimental) — no per-page
                    # progress callback (runs inside asyncio.to_thread),
                    # same as `local` below. `page_list` (closed over from
                    # the outer request handler) is the exact whole-movement
                    # range already priced and approved above; `None` (no
                    # `pages` query param) keeps the OMR_MAX_PAGES cap.
                    omr = await staged_omr.run_staged_omr(
                        s.original_pdf_path, output_dir, pages=page_list,
                    )
                    s.musicxml_path = omr.musicxml_path or s.musicxml_path
                    s.status = "review" if omr.musicxml_path else "error"
                    meta = {"omr_engine": omr_engine}
                    # ⚠️ CARRIED THROUGH TO THE FINAL metadata_json, not just
                    # the transient "starting" one above (which this
                    # assignment replaces wholesale) — CLAUDE.md §1: the user
                    # must still be able to see what a finished whole-
                    # movement job was priced and approved at.
                    if budget is not None:
                        meta["omr_budget"] = budget
                        meta["omr_pages_requested"] = page_list
                    if omr.record_path:
                        meta["omr_record_path"] = omr.record_path
                    if omr.pages_processed:
                        meta["omr_pages"] = omr.pages_processed
                    # ⚠️ Straight off `staged.export.to_musicxml`'s own
                    # coverage report (CLAUDE.md §4d) — never recomputed —
                    # so the review UI can show "N staves held out / N bars
                    # unread" without re-deriving the accounting.
                    #
                    # ⚠️ ROADMAP 3.3c: `staged_unread_bars` now reads the
                    # BARS-WE-READ-NOTHING-IN count (report's own
                    # `unread_bar_marks["unread"]`) — a fix from 3.3's first
                    # half, which stored `bars_held_out_sum["bars"]` (the
                    # DOES-NOT-ADD-UP count, now `staged_held_out_bars`)
                    # under this name. Both reasons are surfaced separately
                    # so the web app never conflates "we read nothing" with
                    # "we read it, but it does not add up" — CLAUDE.md §1's
                    # "every bar the reader could not read is MARKED as
                    # unread" is two different marks for two different
                    # reasons (roadmap 3.5), and the accounting panel needs
                    # both, not their sum silently relabelled.
                    if omr.held_out_staves is not None:
                        meta["staged_held_out_staves"] = omr.held_out_staves
                    if omr.unread_bars is not None:
                        meta["staged_unread_bars"] = omr.unread_bars
                    if omr.held_out_bars is not None:
                        meta["staged_held_out_bars"] = omr.held_out_bars
                    if omr.bars_total is not None:
                        meta["staged_bars_total"] = omr.bars_total
                    if omr.held_out_bars_by_page is not None:
                        meta["staged_held_out_bars_by_page"] = omr.held_out_bars_by_page
                    if omr.status_census is not None:
                        meta["staged_status_census"] = omr.status_census
                    if omr.error_message:
                        # ⚠️ Includes `staged.export.Unbalanced` — surfaced
                        # here with its own message, never swallowed. See
                        # staged_omr.py's module docstring.
                        meta["omr_error"] = omr.error_message
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


def _mean_omr_confidence_for_page(score: "Score", page_number: int) -> float:
    """Best-effort mean YOLO detection confidence for one page of a local-OMR
    run. `page_number` is 1-based (matches the PDF/Verovio page pairing used
    by claude_vision.compare_score_measures).

    Falls back to 0.5 when the score used Vision OMR (no omr_json_path),
    the JSON is missing/unreadable, or the page has no detections — this
    mirrors the previous hardcoded default so behavior degrades gracefully.
    """
    try:
        omr_json_path = (score.metadata_json or {}).get("omr_json_path")
        if not omr_json_path or not os.path.isfile(omr_json_path):
            return 0.5

        import json as _json
        with open(omr_json_path, "r", encoding="utf-8") as f:
            omr_data = _json.load(f)

        page_index = page_number - 1
        for page in omr_data.get("pages", []):
            if page.get("page_index") != page_index:
                continue
            confidences: list[float] = []
            for system in page.get("systems", []):
                for staff in system.get("staves", []):
                    for measure in staff.get("measures", []):
                        for det in measure.get("detections", []):
                            conf = det.get("confidence")
                            if isinstance(conf, (int, float)):
                                confidences.append(float(conf))
            return (sum(confidences) / len(confidences)) if confidences else 0.5

        return 0.5
    except Exception:
        return 0.5


@app.post("/api/scores/{score_id}/process/compare")
@limiter.limit(setting_limit("rate_limit_process_compare"))
async def run_comparison(
    request: Request,
    score_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run Claude Vision comparison. Requires payment (or admin bypass)."""
    from routers.payments import user_has_vision_access

    score = await _owned_score(db, score_id, current_user)
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

                # NOTE: this used to pre-flag measures from the most recently
                # created ComparisonSession, but ComparisonSession has no
                # association to a Score (it's a standalone multi-XML-upload
                # workspace — see /api/compare/), so that was injecting
                # whatever score was most recently compared in the Gradus
                # Library into this score's Vision prompt. There's no
                # reliable way to tie a session back to this score without a
                # schema change, so the injection is dropped rather than
                # feeding in wrong-score data.
                diffs = await claude_vision.compare_score_measures(
                    s.original_pdf_path, s.musicxml_path, metadata,
                    knowledge_patterns=knowledge_patterns,
                )
                snippets_dir = os.path.join(settings.upload_dir, score_id, "snippets")
                os.makedirs(snippets_dir, exist_ok=True)

                # d.measure_number is really the page index (1-based) —
                # compare_score_measures pairs PDF pages to XML pages 1:1.
                # Cache the per-page mean OMR confidence so multiple diffs
                # on the same page don't reload the JSON file each time.
                omr_confidence_cache: dict[int, float] = {}

                for d in diffs:
                    diff_id = str(uuid.uuid4())

                    if d.measure_number not in omr_confidence_cache:
                        omr_confidence_cache[d.measure_number] = (
                            _mean_omr_confidence_for_page(s, d.measure_number)
                        )
                    omr_confidence = omr_confidence_cache[d.measure_number]

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
                        omr_confidence=omr_confidence,
                        claude_vision_confidence=d.confidence,
                        created_at=datetime.utcnow(),
                    )
                    session.add(fd)

                    # Apply auto-accept rules to newly created diff
                    diff_dict = {
                        "difference_type": d.difference_type,
                        "instrument": d.instrument,
                        "omr_confidence": omr_confidence,
                        "claude_vision_confidence": d.confidence,
                        "era": s.era,
                    }
                    matched_rule_id = await analytics.apply_auto_accept(diff_dict, session)
                    if matched_rule_id:
                        fd.human_decision = "accept"
                        fd.auto_accepted = True
                        fd.auto_accept_rule_id = matched_rule_id

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
    score = await _owned_score(db, score_id, current_user)
    return {"score_id": score_id, "status": score.status, "updated_at": score.updated_at}


# ---------------------------------------------------------------------------
# Score CRUD routes
# ---------------------------------------------------------------------------


@app.get("/api/scores", response_model=list[ScoreResponse])
async def list_scores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's scores."""
    result = await db.execute(
        select(Score)
        .where(Score.user_id == current_user.id)
        .order_by(Score.created_at.desc())
    )
    return [ScoreResponse.model_validate(s) for s in result.scalars().all()]


@app.get("/api/scores/{score_id}", response_model=ScoreResponse)
async def get_score(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get score details by ID."""
    score = await _owned_score(db, score_id, current_user)
    return ScoreResponse.model_validate(score)


@app.delete("/api/scores/{score_id}")
async def delete_score(
    score_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a score and its associated files."""
    score = await _owned_score(db, score_id, current_user)

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
    await _owned_score(db, score_id, current_user)
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
        select(FlaggedDifference)
        .join(Score, FlaggedDifference.score_id == Score.id)
        .where(FlaggedDifference.id == diff_id, Score.user_id == current_user.id)
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
    await _owned_score(db, score_id, current_user)

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
    await _owned_score(db, score_id, current_user)

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
    score = await _owned_score(db, score_id, current_user)

    return {"score_id": score_id, "export_status": "ready" if score.status == "complete" else score.status}


# ---------------------------------------------------------------------------
# Analytics routes
# ---------------------------------------------------------------------------


@app.get("/api/analytics/report")
async def get_analytics_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the learning report. Score and correction counts are the
    current user's; the knowledge base (patterns, auto-accept rules) is
    shared across users, as it is when auto-accept is applied."""
    return await analytics.generate_learning_report(db, user_id=current_user.id)


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
    """Trigger fine-tuning dataset export (admin only: it reads every
    user's reviewed differences)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin only")
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
@limiter.limit(setting_limit("rate_limit_gradus"))
async def create_gradus_score(
    request: Request,
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

    # Client filenames are reduced to a basename, checked against an
    # extension allowlist and prefixed with a uuid (as /api/import does).
    try:
        xml_path = await _save_named_upload(
            xml_file, gradus_dir, file_import.XML_EXTENSIONS, "score.xml")

        pdf_path: Optional[str] = None
        if pdf_file and pdf_file.filename:
            pdf_path = await _save_named_upload(
                pdf_file, gradus_dir, file_import.PDF_EXTENSIONS, "score.pdf")
    except HTTPException:
        import shutil
        shutil.rmtree(gradus_dir, ignore_errors=True)
        raise

    gradus = GradusScore(
        id=score_id,
        user_id=current_user.id,
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
        select(GradusScore)
        .where(GradusScore.user_id == current_user.id)
        .order_by(GradusScore.created_at.desc())
    )
    return [GradusScoreResponse.model_validate(g) for g in result.scalars().all()]


@app.delete("/api/gradus/{gradus_id}")
async def delete_gradus_score(
    gradus_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Gradus score and its uploaded files."""
    result = await db.execute(
        select(GradusScore).where(
            GradusScore.id == gradus_id, GradusScore.user_id == current_user.id)
    )
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
@limiter.limit(setting_limit("rate_limit_compare"))
async def create_comparison_session(
    request: Request,
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

    # Resolve optional master path (the caller's own Gradus scores only)
    master_path: Optional[str] = None
    if gradus_score_id:
        g_result = await db.execute(
            select(GradusScore).where(
                GradusScore.id == gradus_score_id,
                GradusScore.user_id == current_user.id,
            )
        )
        gradus = g_result.scalar_one_or_none()
        if gradus is None:
            raise HTTPException(status_code=404, detail="Gradus score not found")
        master_path = gradus.xml_path

    session_id = str(uuid.uuid4())
    compare_dir = os.path.join(settings.upload_dir, "compare", session_id)
    os.makedirs(compare_dir, exist_ok=True)

    # Save uploaded files: basename + extension allowlist + uuid prefix
    saved_paths: list[str] = []
    try:
        for xml_file in xml_files:
            saved_paths.append(await _save_named_upload(
                xml_file, compare_dir, file_import.XML_EXTENSIONS,
                f"score_{len(saved_paths)}.xml"))
    except HTTPException:
        import shutil
        shutil.rmtree(compare_dir, ignore_errors=True)
        raise

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
        user_id=current_user.id,
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
        select(ComparisonSession)
        .where(ComparisonSession.user_id == current_user.id)
        .order_by(ComparisonSession.created_at.desc())
        .limit(50)
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
        select(ComparisonSession).where(
            ComparisonSession.id == session_id,
            ComparisonSession.user_id == current_user.id,
        )
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
    score = await _owned_score(db, score_id, current_user)
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
