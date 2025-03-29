from utils.api import Router, Depends
from dependencies.auth import get_current_user
from sqlalchemy.orm import Session
from dependencies.database import get_db
from ..models.subscription import Subscription
from ..schemas import SubscriptionCreate

router = Router()

@router.post("/")
def subscribe(subscription: SubscriptionCreate, userdata: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    new_subscription = Subscription(
        user_id=userdata["sub"],
        subscription=subscription.subscription
    )
    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)
    return new_subscription
