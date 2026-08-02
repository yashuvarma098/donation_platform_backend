from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import require_role
from app.database import users_collection, donations_collection, notifications_collection
from app.models.user import UserRole

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
async def get_platform_stats(
    current_user: dict = Depends(require_role(UserRole.admin))
):
    total_donors = await users_collection.count_documents({"role": "donor"})
    total_ngos = await users_collection.count_documents({"role": "ngo"})
    pending_ngos = await users_collection.count_documents({"role": "ngo", "is_verified": False})
    verified_ngos = await users_collection.count_documents({"role": "ngo", "is_verified": True})
    total_donations = await donations_collection.count_documents({})
    completed_donations = await donations_collection.count_documents({"status": "completed"})
    pending_donations = await donations_collection.count_documents({"status": "requested"})

    return {
        "total_donors": total_donors,
        "total_ngos": total_ngos,
        "pending_ngos": pending_ngos,
        "verified_ngos": verified_ngos,
        "total_donations": total_donations,
        "completed_donations": completed_donations,
        "pending_donations": pending_donations,
    }


@router.get("/ngos")
async def get_all_ngos(
    current_user: dict = Depends(require_role(UserRole.admin))
):
    ngos = []
    cursor = users_collection.find({"role": "ngo"}).sort("created_at", -1)
    async for user in cursor:
        ngos.append({
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "city": user.get("address", {}).get("city", ""),
            "state": user.get("address", {}).get("state", ""),
            "is_verified": user["is_verified"],
            "created_at": user["created_at"],
        })
    return {"ngos": ngos, "total": len(ngos)}


@router.patch("/ngos/{ngo_id}/verify")
async def verify_ngo(
    ngo_id: str,
    current_user: dict = Depends(require_role(UserRole.admin))
):
    try:
        ngo = await users_collection.find_one({"_id": ObjectId(ngo_id), "role": "ngo"})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid NGO ID")

    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found")

    await users_collection.update_one(
        {"_id": ObjectId(ngo_id)},
        {"$set": {"is_verified": True}}
    )

    await notifications_collection.insert_one({
        "user_id": ngo_id,
        "message": "Congratulations! Your NGO has been verified. You can now accept donation requests.",
        "type": "ngo_verified",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    return {"message": f"NGO '{ngo['name']}' has been verified successfully!"}


@router.patch("/ngos/{ngo_id}/reject")
async def reject_ngo(
    ngo_id: str,
    current_user: dict = Depends(require_role(UserRole.admin))
):
    try:
        ngo = await users_collection.find_one({"_id": ObjectId(ngo_id), "role": "ngo"})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid NGO ID")

    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found")

    await users_collection.update_one(
        {"_id": ObjectId(ngo_id)},
        {"$set": {"is_verified": False}}
    )

    await notifications_collection.insert_one({
        "user_id": ngo_id,
        "message": "Your NGO verification request has been rejected. Please contact support.",
        "type": "ngo_rejected",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    return {"message": f"NGO '{ngo['name']}' has been rejected."}


@router.get("/donations")
async def get_all_donations(
    current_user: dict = Depends(require_role(UserRole.admin))
):
    donations = []
    cursor = donations_collection.find({}).sort("created_at", -1)
    async for doc in cursor:
        donor = await users_collection.find_one({"_id": ObjectId(doc["donor_id"])})
        ngo = await users_collection.find_one({"_id": ObjectId(doc["ngo_id"])})
        donations.append({
            "id": str(doc["_id"]),
            "donor_name": donor["name"] if donor else "Unknown",
            "ngo_name": ngo["name"] if ngo else "Unknown",
            "status": doc["status"],
            "items_count": sum(i["quantity"] for i in doc["items"]),
            "city": doc["pickup_address"].get("city", ""),
            "scheduled_time": doc["scheduled_time"],
            "created_at": doc["created_at"],
        })
    return {"donations": donations, "total": len(donations)}


@router.get("/donors")
async def get_all_donors(
    current_user: dict = Depends(require_role(UserRole.admin))
):
    donors = []
    cursor = users_collection.find({"role": "donor"}).sort("created_at", -1)
    async for user in cursor:
        donation_count = await donations_collection.count_documents(
            {"donor_id": str(user["_id"])}
        )
        donors.append({
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "phone": user.get("phone", ""),
            "city": user.get("address", {}).get("city", ""),
            "donation_count": donation_count,
            "created_at": user["created_at"],
        })
    return {"donors": donors, "total": len(donors)}