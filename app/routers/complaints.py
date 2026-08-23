from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, require_role
from app.database import db, notifications_collection
from app.models.user import UserRole

router = APIRouter(prefix="/complaints", tags=["Complaints"])
complaints_collection = db["complaints"]


# ─── USER: Complaint Raise Karo ───────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def raise_complaint(
    data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Donor ya NGO complaint raise kar sakta hai."""
    if "subject" not in data or "description" not in data:
        raise HTTPException(status_code=400, detail="subject and description required")

    complaint = {
        "raised_by": str(current_user["_id"]),
        "raised_by_name": current_user["name"],
        "raised_by_role": current_user["role"],
        "donation_id": data.get("donation_id", None),
        "subject": data["subject"],
        "description": data["description"],
        "status": "open",
        "resolution": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await complaints_collection.insert_one(complaint)
    return {
        "message": "Complaint raised successfully! Admin will review it soon.",
        "complaint_id": str(result.inserted_id)
    }


# ─── USER: Apni Complaints Dekho ─────────────────────────────────────────────

@router.get("/my")
async def get_my_complaints(current_user: dict = Depends(get_current_user)):
    complaints = []
    cursor = complaints_collection.find(
        {"raised_by": str(current_user["_id"])}
    ).sort("created_at", -1)

    async for doc in cursor:
        complaints.append({
            "id": str(doc["_id"]),
            "subject": doc["subject"],
            "description": doc["description"],
            "status": doc["status"],
            "resolution": doc.get("resolution"),
            "donation_id": doc.get("donation_id"),
            "created_at": doc["created_at"],
        })
    return {"complaints": complaints, "total": len(complaints)}


# ─── ADMIN: Saari Complaints Dekho ───────────────────────────────────────────

@router.get("/all")
async def get_all_complaints(
    current_user: dict = Depends(require_role(UserRole.admin))
):
    complaints = []
    cursor = complaints_collection.find({}).sort("created_at", -1)
    async for doc in cursor:
        complaints.append({
            "id": str(doc["_id"]),
            "raised_by_name": doc["raised_by_name"],
            "raised_by_role": doc["raised_by_role"],
            "subject": doc["subject"],
            "description": doc["description"],
            "status": doc["status"],
            "resolution": doc.get("resolution"),
            "donation_id": doc.get("donation_id"),
            "created_at": doc["created_at"],
        })
    return {"complaints": complaints, "total": len(complaints)}


# ─── ADMIN: Complaint Resolve Karo ───────────────────────────────────────────

@router.patch("/{complaint_id}/resolve")
async def resolve_complaint(
    complaint_id: str,
    data: dict,
    current_user: dict = Depends(require_role(UserRole.admin))
):
    if "resolution" not in data:
        raise HTTPException(status_code=400, detail="resolution text required")

    try:
        complaint = await complaints_collection.find_one({"_id": ObjectId(complaint_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid complaint ID")

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    await complaints_collection.update_one(
        {"_id": ObjectId(complaint_id)},
        {"$set": {
            "status": "resolved",
            "resolution": data["resolution"],
            "updated_at": datetime.utcnow()
        }}
    )

    # User ko notification bhejo
    await notifications_collection.insert_one({
        "user_id": complaint["raised_by"],
        "message": f"Your complaint '{complaint['subject']}' has been resolved: {data['resolution']}",
        "type": "complaint_resolved",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    return {"message": "Complaint resolved successfully!"}