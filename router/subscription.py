from coffeebreak import Router
from fastapi import Depends, HTTPException
from coffeebreak.auth import get_current_user, is_anonymous
from sqlalchemy.orm import Session
from coffeebreak.db import DB as get_db
from ..models.subscription import Subscription
from ..schemas import SubscriptionCreate, WebPushSubscription
import logging

logger = logging.getLogger("coffeebreak.webpush")
router = Router()


@router.post("/", response_model=WebPushSubscription)
async def subscribe(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db),
    user: dict | None = Depends(get_current_user(force_auth=False)),
):
    """Create a new subscription. Works for both authenticated and anonymous users."""
    subscription_dict = subscription.subscription.model_dump()

    # Validate subscription data
    endpoint = str(subscription_dict.get("endpoint") or "").strip()
    if not endpoint or not subscription_dict.get("keys"):
        raise HTTPException(
            status_code=400,
            detail="Invalid subscription format. Must include endpoint and keys.",
        )

    user_sub = None
    if user and not is_anonymous(user):
        user_sub = str(user.get("sub") or "").strip() or None

    existing_subscription = next(
        (
            row
            for row in db.query(Subscription).all()
            if isinstance(row.subscription, dict)
            and str(row.subscription.get("endpoint") or "").strip() == endpoint
        ),
        None,
    )

    if existing_subscription is not None:
        existing_subscription.subscription = subscription_dict
        if user_sub:
            existing_subscription.user_id = user_sub

        try:
            db.commit()
            db.refresh(existing_subscription)
            logger.info(
                f"Subscription refreshed for user: {existing_subscription.user_id}"
            )
            return existing_subscription
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error while updating subscription: {str(db_error)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update subscription. Please try again.",
            )

    new_subscription = Subscription(user_id=user_sub, subscription=subscription_dict)

    try:
        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)
        logger.info(f"New subscription created for user: {new_subscription.user_id}")
        return new_subscription
    except Exception as db_error:
        db.rollback()
        logger.error(f"Database error while creating subscription: {str(db_error)}")
        raise HTTPException(
            status_code=500, detail="Failed to save subscription. Please try again."
        )
