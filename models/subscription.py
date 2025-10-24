from datetime import datetime
from coffeebreak.db import ModelBase as Base
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.types import JSON as SQLAlchemyJSON


class Subscription(Base):
    __tablename__ = "webpush_notifications_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=True)  # Allow anonymous subscriptions
    subscription = Column(SQLAlchemyJSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
