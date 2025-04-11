from utils.api import Router, Depends, HTTPException
from dependencies.auth import get_current_user
from sqlalchemy.orm import Session
from dependencies.database import get_db
from ..models.subscription import Subscription
from ..schemas import SubscriptionCreate, WebPushSubscription
import logging

logger = logging.getLogger("coffeebreak.webpush")
router = Router()


@router.post("/", response_model=WebPushSubscription)
async def subscribe(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db),
    user: dict | None = Depends(lambda: get_current_user(force_auth=False))
):
    """Create a new subscription. Works for both authenticated and anonymous users."""
    try:
        subscription_dict = subscription.subscription.model_dump()

        # Validate subscription data
        if not subscription_dict.get("endpoint") or not subscription_dict.get("keys"):
            raise HTTPException(
                status_code=400,
                detail="Invalid subscription format. Must include endpoint and keys."
            )

        new_subscription = Subscription(
            user_id=user.get("sub") if user else None,
            subscription=subscription_dict
        )

        try:
            db.add(new_subscription)
            db.commit()
            db.refresh(new_subscription)
            logger.info(
                f"New subscription created for user: {new_subscription.user_id}")
            return new_subscription
        except Exception as db_error:
            db.rollback()
            logger.error(
                f"Database error while creating subscription: {str(db_error)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save subscription. Please try again."
            )

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error in subscribe endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        )
