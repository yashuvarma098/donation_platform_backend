from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.dependencies import get_current_user, require_role
from app.database import users_collection, ngo_profiles_collection
from app.models.user import UserRole

router = APIRouter(prefix="/ngos", tags=["NGOs"])


# ─── PUBLIC: Verified NGOs List (city filter ke saath) ───────────────────────

@router.get("/verified")
async def get_verified_ngos(
    current_user: dict = Depends(get_current_user),
    city: str = Query(None, description="Filter by city"),
    category: str = Query(None, description="Filter by category")
):
    """
    Verified NGOs ki list.
    Optional filters: ?city=Pune  or  ?category=clothes
    """
    query = {"role": "ngo", "is_verified": True}

    # City filter
    if city:
        query["address.city"] = {"$regex": city, "$options": "i"}  # case-insensitive

    ngos = []
    cursor = users_collection.find(query)
    async for user in cursor:
        profile = await ngo_profiles_collection.find_one({"user_id": str(user["_id"])})
        categories = profile["categories_accepted"] if profile else []

        # Category filter
        if category and category not in categories:
            continue

        ngos.append({
            "user_id": str(user["_id"]),
            "org_name": profile["org_name"] if profile else user["name"],
            "city": user.get("address", {}).get("city", ""),
            "state": user.get("address", {}).get("state", ""),
            "phone": user.get("phone", ""),
            "categories_accepted": categories,
        })

    return {"ngos": ngos, "total": len(ngos)}


# ─── NGO: Profile Create/Update ──────────────────────────────────────────────

@router.post("/profile", status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(
    data: dict,
    current_user: dict = Depends(require_role(UserRole.ngo))
):
    required = ["org_name", "registration_number", "categories_accepted"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"'{field}' is required")

    user_id = str(current_user["_id"])
    existing = await ngo_profiles_collection.find_one({"user_id": user_id})

    profile_data = {
        "user_id": user_id,
        "org_name": data["org_name"],
        "registration_number": data["registration_number"],
        "categories_accepted": data["categories_accepted"],
        "description": data.get("description", ""),
        "updated_at": datetime.utcnow(),
    }

    if existing:
        await ngo_profiles_collection.update_one(
            {"user_id": user_id}, {"$set": profile_data}
        )
        msg = "Profile updated successfully!"
    else:
        profile_data["created_at"] = datetime.utcnow()
        profile_data["verification_status"] = "pending"
        await ngo_profiles_collection.insert_one(profile_data)
        msg = "Profile created successfully!"

    profile = await ngo_profiles_collection.find_one({"user_id": user_id})
    return {
        "message": msg,
        "profile": {
            "id": str(profile["_id"]),
            "org_name": profile["org_name"],
            "registration_number": profile["registration_number"],
            "categories_accepted": profile["categories_accepted"],
            "description": profile.get("description", ""),
            "verification_status": profile.get("verification_status", "pending"),
        }
    }


# ─── NGO: Apna Profile Dekho ─────────────────────────────────────────────────

@router.get("/profile/me")
async def get_my_profile(
    current_user: dict = Depends(require_role(UserRole.ngo))
):
    profile = await ngo_profiles_collection.find_one({"user_id": str(current_user["_id"])})
    if not profile:
        return {"profile": None, "message": "Profile not created yet"}
    return {
        "profile": {
            "id": str(profile["_id"]),
            "org_name": profile["org_name"],
            "registration_number": profile["registration_number"],
            "categories_accepted": profile["categories_accepted"],
            "description": profile.get("description", ""),
            "verification_status": profile.get("verification_status", "pending"),
            "updated_at": profile.get("updated_at"),
        }
    }