from pydantic import BaseModel
from typing import Dict

class SubscriptionCreate(BaseModel):
    subscription: Dict

    class Config:
        from_attributes = True
