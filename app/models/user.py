from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRole(str, Enum):
    donor = "donor"
    ngo = "ngo"
    admin = "admin"


class Address(BaseModel):
    street: str = Field(min_length=3, max_length=200)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(min_length=6, max_length=6)

    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        if not v.isdigit():
            raise ValueError('Pincode must be 6 digits')
        return v


# ---- What comes IN from the client during registration ----
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    role: UserRole
    phone: str = Field(min_length=10, max_length=10)
    address: Address

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if not v.isdigit():
            raise ValueError('Phone must be 10 digits only')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z\s.]+$', v):
            raise ValueError('Name can only contain letters, spaces and dots')
        return v.strip()


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