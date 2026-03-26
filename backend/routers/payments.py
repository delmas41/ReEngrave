"""
Payments router.
Stripe Checkout for Vision AI comparison ($5/score).
Admin emails bypass payment entirely.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from database.connection import get_db
from database.models import Payment, ScoreAccess, User
from dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])
webhook_router = APIRouter(tags=["webhooks"])

VISION_FEATURE = "vision_comparison"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def user_has_vision_access(user: User, score_id: str, db: AsyncSession) -> bool:
    """Return True if the user has paid for (or is admin for) this score.

    Admin emails always have access. Non-admins require Stripe to be
    configured AND a completed payment. If Stripe is not set up, non-admins
    are blocked to prevent unauthorized use of the Anthropic API key.
    """
    if user.email in settings.admin_email_list:
        return True

    if not settings.stripe_secret_key:
        return False  # Stripe not configured — block non-admins to protect API key costs

    result = await db.execute(
        select(ScoreAccess).where(
            ScoreAccess.user_id == user.id,
            ScoreAccess.score_id == score_id,
            ScoreAccess.feature == VISION_FEATURE,
        )
    )
    return result.scalar_one_or_none() is not None


async def _grant_vision_access(user_id: str, score_id: str, access_type: str, db: AsyncSession) -> None:
    """Insert a ScoreAccess row (idempotent)."""
    existing = await db.execute(
        select(ScoreAccess).where(
            ScoreAccess.user_id == user_id,
            ScoreAccess.score_id == score_id,
            ScoreAccess.feature == VISION_FEATURE,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            ScoreAccess(
                user_id=user_id,
                score_id=score_id,
                feature=VISION_FEATURE,
                access_type=access_type,
            )
        )
        await db.flush()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    score_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/checkout")
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout Session for Vision AI access on a score."""
    # Admin bypass – no payment needed
    if current_user.email in settings.admin_email_list:
        await _grant_vision_access(current_user.id, body.score_id, "admin", db)
        return {"has_access": True, "admin_bypass": True}

    # Already has access
    if await user_has_vision_access(current_user, body.score_id, db):
        return {"has_access": True}

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Payment system not configured")

    try:
        import stripe  # type: ignore
        stripe.api_key = settings.stripe_secret_key

        success_url = (
            f"{settings.frontend_url}/payment-success"
            f"?session_id={{CHECKOUT_SESSION_ID}}&score_id={body.score_id}"
        )
        cancel_url = f"{settings.frontend_url}/scores/{body.score_id}/review"

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": current_user.id,
                "score_id": body.score_id,
                "feature": VISION_FEATURE,
            },
            customer_email=current_user.email,
        )

        # Record pending payment
        db.add(
            Payment(
                user_id=current_user.id,
                score_id=body.score_id,
                stripe_session_id=session.id,
                amount_cents=500,
                currency="usd",
                status="pending",
            )
        )
        await db.flush()

        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as exc:
        logger.exception("Stripe checkout error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/status")
async def payment_status(
    score_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check whether the current user has Vision AI access for a given score."""
    has_access = await user_has_vision_access(current_user, score_id, db)
    is_admin = current_user.email in settings.admin_email_list
    return {
        "has_access": has_access,
        "score_id": score_id,
        "is_admin": is_admin,
        "stripe_publishable_key": settings.stripe_publishable_key or None,
    }


# ---------------------------------------------------------------------------
# Stripe webhook (no auth — verified by signature)
# ---------------------------------------------------------------------------


@webhook_router.post("/api/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events. Verifies signature and grants access on payment."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Payment system not configured")

    try:
        import stripe  # type: ignore
        stripe.api_key = settings.stripe_secret_key

        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            meta = session.get("metadata", {})
            user_id = meta.get("user_id")
            score_id = meta.get("score_id")
            stripe_session_id = session.get("id")
            payment_intent_id = session.get("payment_intent")

            if user_id and score_id:
                # Update payment record
                result = await db.execute(
                    select(Payment).where(Payment.stripe_session_id == stripe_session_id)
                )
                payment = result.scalar_one_or_none()
                if payment:
                    payment.status = "completed"
                    payment.stripe_payment_intent_id = payment_intent_id
                    payment.completed_at = datetime.now(timezone.utc)
                    await db.flush()

                # Grant access
                await _grant_vision_access(user_id, score_id, "payment", db)

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Webhook processing error: %s", exc)
        raise HTTPException(status_code=500, detail="Webhook processing failed")
