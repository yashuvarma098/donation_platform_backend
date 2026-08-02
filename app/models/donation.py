from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.user import Address


class DonationStatus(str, Enum):
    requested = "requested"
    accepted = "accepted"
    scheduled = "scheduled"
    collected = "collected"
    completed = "completed"
    cancelled = "cancelled"


class ItemCondition(str, Enum):
    new = "new"
    good = "good"
    fair = "fair"


class DonationItem(BaseModel):
    category: str  # "clothes" | "household_items" (kept as str for flexibility, not enum)
    item_type: str  # e.g. "shirt", "blanket", "utensils"
    quantity: int = Field(gt=0)
    condition: ItemCondition
    description: Optional[str] = None


class StatusHistoryEntry(BaseModel):
    status: DonationStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    note: Optional[str] = None


# ---- What the donor sends to create a donation ----
class DonationCreate(BaseModel):
    ngo_id: str
    items: List[DonationItem]
    pickup_address: Address
    scheduled_time: datetime


# ---- What's stored in MongoDB ----
class DonationInDB(BaseModel):
    donor_id: str
    ngo_id: str
    items: List[DonationItem]
    pickup_address: Address
    scheduled_time: datetime
    status: DonationStatus = DonationStatus.requested
    status_history: List[StatusHistoryEntry] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---- What's returned to the client ----
class DonationOut(BaseModel):
    id: str
    donor_id: str
    ngo_id: str
    items: List[DonationItem]
    pickup_address: Address
    scheduled_time: datetime
    status: DonationStatus
    status_history: List[StatusHistoryEntry]
    created_at: datetime
    updated_at: datetime


# ---- For NGO/Admin updating status ----
class DonationStatusUpdate(BaseModel):
    status: DonationStatus
    note: Optional[str] = None