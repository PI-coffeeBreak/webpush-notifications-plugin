from pydantic import BaseModel, Field
from typing import Dict, Optional


class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]
    expirationTime: Optional[int] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "endpoint": "https://updates.push.services.mozilla.com/wpush/v2/...",
                "keys": {
                    "auth": "auth_key",
                    "p256dh": "public_key"
                },
                "expirationTime": None
            }
        }


class SubscriptionCreate(BaseModel):
    subscription: PushSubscription

    class Config:
        from_attributes = True


class WebPushSubscription(BaseModel):
    subscription: PushSubscription
    user_id: Optional[str] = None  # Optional for anonymous subscriptions

    class Config:
        from_attributes = True


class WebPushSubscriptionResponse(BaseModel):
    id: str
    subscription: PushSubscription
    user_id: Optional[str] = None

    class Config:
        from_attributes = True
