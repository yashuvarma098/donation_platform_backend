from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    donor = "donor"
    ngo = "ngo"
    admin = "admin"


class Address(BaseModel):
    street: str
    city: str
    state: str
    pincode: str


# ---- What comes IN from the client during registration ----
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole
    phone: str
    address: Address


# ---- What's actually stored in MongoDB (note: password_hash, not password) ----
class UserInDB(BaseModel):
    name: str
    email: EmailStr
    password_hash: str
    role: UserRole
    phone: str
    address: Address
    is_verified: bool = False  # relevant mainly for NGOs; donors can default True later if needed
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---- What we SEND BACK to the client (never include password_hash) ----
class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: UserRole
    phone: str
    address: Address
    is_verified: bool
    created_at: datetime


# ---- Login request ----
class UserLogin(BaseModel):
    email: EmailStr
    password: str