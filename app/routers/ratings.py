from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user, require_role
from app.database import db, donations_collection
from app.models.user import UserRole

router = APIRouter(prefix="/ratings", tags=["Ratings"])
ratings_collection = db["ratings"]


# ─── DONOR: Completed donation ko rate karo ───────────────────────────────────

@router.post("/")
async def submit_rating(
    data: dict,
    current_user: dict = Depends(require_role(UserRole.donor))
):
    """Donor completed donation ko 1-5 star rating deta hai."""
    if "donation_id" not in data or "rating" not in data:
        raise HTTPException(status_code=400, detail="donation_id and rating required")

    rating = int(data["rating"])
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Donation exist karti hai aur completed hai?
    try:
        donation = await donations_collection.find_one({
            "_id": ObjectId(data["donation_id"]),
            "donor_id": str(current_user["_id"]),
            "status": "completed"
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation ID")

    if not donation:
        raise HTTPException(
            status_code=404,
            detail="Completed donation not found. Only completed donations can be rated."
        )

    # Already rated?
    existing = await ratings_collection.find_one({
        "donation_id": data["donation_id"],
        "donor_id": str(current_user["_id"])
    })
    if existing:
        # Update existing rating
        await ratings_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "rating": rating,
                "feedback": data.get("feedback", ""),
                "updated_at": datetime.utcnow()
            }}
        )
        return {"message": "Rating updated successfully!"}

    # New rating
    await ratings_collection.insert_one({
        "donation_id": data["donation_id"],
        "donor_id": str(current_user["_id"]),
        "ngo_id": donation["ngo_id"],
        "rating": rating,
        "feedback": data.get("feedback", ""),
        "created_at": datetime.utcnow(),
    })

    return {"message": "Thank you for your rating! ⭐"}


# ─── Check if already rated ───────────────────────────────────────────────────

@router.get("/check/{donation_id}")
async def check_rating(
    donation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Check if donation already rated."""
    existing = await ratings_collection.find_one({
        "donation_id": donation_id,
        "donor_id": str(current_user["_id"])
    })
    if existing:
        return {
            "rated": True,
            "rating": existing["rating"],
            "feedback": existing.get("feedback", "")
        }
    return {"rated": False}