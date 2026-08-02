from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class NGOProfileCreate(BaseModel):
    org_name: str
    registration_number: str
    categories_accepted: List[str] = []  # e.g. ["clothes", "household_items"]


class NGOProfileInDB(BaseModel):
    user_id: str  # references users._id
    org_name: str
    registration_number: str
    categories_accepted: List[str] = []
    verification_status: VerificationStatus = VerificationStatus.pending
    verified_by: Optional[str] = None  # admin user_id
    verified_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NGOProfileOut(BaseModel):
    id: str
    user_id: str
    org_name: str
    registration_number: str
    categories_accepted: List[str]
    verification_status: VerificationStatus
    created_at: datetime