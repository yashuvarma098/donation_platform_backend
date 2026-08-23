from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.core.dependencies import require_role
from app.database import users_collection, donations_collection, notifications_collection, db
from app.models.user import UserRole
import csv
import io

router = APIRouter(prefix="/admin", tags=["Admin"])

categories_collection = db["categories"]


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
    cancelled_donations = await donations_collection.count_documents({"status": "cancelled"})

# ── KPI 1: Repeat Donation Rate ──────────────────────────────────────────
    # Donors jo ek se zyada donation kar chuke hain
    repeat_donors = 0
    if total_donors > 0:
        pipeline = [
            {"$group": {"_id": "$donor_id", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}},
            {"$count": "repeat_donors"}
        ]
        result = await donations_collection.aggregate(pipeline).to_list(length=1)
        repeat_donors = result[0]["repeat_donors"] if result else 0
        repeat_donation_rate = round((repeat_donors / total_donors) * 100, 1)
    else:
        repeat_donation_rate = 0.0

# ── KPI 2: Average Collection Time ───────────────────────────────────────
    # Completed donations ki created_at se completed status tak ka time
    avg_collection_hours = 0
    completed_cursor = donations_collection.find({"status": "completed"})
    times = []
    async for doc in completed_cursor:
        created = doc.get("created_at")
        history = doc.get("status_history", [])
        # status_history mein "completed" entry dhundho
        for h in history:
            if h.get("status") == "completed" and created:
                completed_at = h.get("timestamp")
                if completed_at and isinstance(completed_at, datetime):
                    diff = (completed_at - created).total_seconds() / 3600
                    if diff > 0:
                        times.append(diff)
                break
 
    if times:
        avg_collection_hours = round(sum(times) / len(times), 1) 

    # ── KPI 3: Average Satisfaction Rating ───────────────────────────────────
    ratings_collection = db["ratings"]
    ratings_cursor = ratings_collection.find({})
    all_ratings = []
    async for r in ratings_cursor:
        all_ratings.append(r.get("rating", 0))
 
    avg_rating = round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else 0.0
    total_ratings = len(all_ratings)

    return {
        "total_donors": total_donors,
        "total_ngos": total_ngos,
        "pending_ngos": pending_ngos,
        "verified_ngos": verified_ngos,
        "total_donations": total_donations,
        "completed_donations": completed_donations,
        "pending_donations": pending_donations,
        "cancelled_donations": cancelled_donations,

        # KPIs
        "repeat_donors": repeat_donors,
        "repeat_donation_rate": repeat_donation_rate,
        "avg_collection_hours": avg_collection_hours,
        "avg_satisfaction_rating": avg_rating,
        "total_ratings": total_ratings,
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

# ─── CATEGORIES MANAGEMENT ───────────────────────────────────────────────────
 
 
 
@router.get("/categories")
async def get_categories(
    current_user: dict = Depends(require_role(UserRole.admin))
):
    """Saari categories dekho."""
    cats = []
    async for doc in categories_collection.find({}):
        cats.append({
            "id": str(doc["_id"]),
            "name": doc["name"],
            "item_types": doc.get("item_types", []),
            "created_at": doc.get("created_at"),
        })
    return {"categories": cats}
 
 
@router.post("/categories")
async def add_category(
    data: dict,
    current_user: dict = Depends(require_role(UserRole.admin))
):
    """Naya category add karo."""
    if "name" not in data:
        raise HTTPException(status_code=400, detail="name is required")
 
    existing = await categories_collection.find_one({"name": data["name"]})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
 
    result = await categories_collection.insert_one({
        "name": data["name"],
        "item_types": data.get("item_types", []),
        "created_at": datetime.utcnow(),
    })
    return {"message": f"Category '{data['name']}' added!", "id": str(result.inserted_id)}
 
 
@router.patch("/categories/{category_id}")
async def update_category(
    category_id: str,
    data: dict,
    current_user: dict = Depends(require_role(UserRole.admin))
):
    """Category update karo — item types add/remove karo."""
    try:
        await categories_collection.update_one(
            {"_id": ObjectId(category_id)},
            {"$set": {
                "name": data.get("name"),
                "item_types": data.get("item_types", []),
            }}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID")
    return {"message": "Category updated!"}
 
 
@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user: dict = Depends(require_role(UserRole.admin))
):
    """Category delete karo."""
    try:
        await categories_collection.delete_one({"_id": ObjectId(category_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID")
    return {"message": "Category deleted!"}

# ─── REPORTS: CSV Export ─────────────────────────────────────────────────────
 
@router.get("/reports/donations")
async def export_donations_csv(current_user: dict = Depends(require_role(UserRole.admin))):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Donation ID", "Donor Name", "NGO Name", "Status",
                     "Items Count", "City", "State", "Scheduled Time", "Created At"])
    cursor = donations_collection.find({}).sort("created_at", -1)
    async for doc in cursor:
        donor = await users_collection.find_one({"_id": ObjectId(doc["donor_id"])})
        ngo = await users_collection.find_one({"_id": ObjectId(doc["ngo_id"])})
        writer.writerow([
            str(doc["_id"]),
            donor["name"] if donor else "Unknown",
            ngo["name"] if ngo else "Unknown",
            doc["status"],
            sum(i["quantity"] for i in doc["items"]),
            doc["pickup_address"].get("city", ""),
            doc["pickup_address"].get("state", ""),
            str(doc.get("scheduled_time", "")),
            str(doc.get("created_at", "")),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=donations_report.csv"}
    )
 
 
@router.get("/reports/donors")
async def export_donors_csv(current_user: dict = Depends(require_role(UserRole.admin))):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Donor ID", "Name", "Email", "Phone", "City", "State",
                     "Total Donations", "Joined At"])
    cursor = users_collection.find({"role": "donor"}).sort("created_at", -1)
    async for user in cursor:
        donation_count = await donations_collection.count_documents({"donor_id": str(user["_id"])})
        writer.writerow([
            str(user["_id"]), user["name"], user["email"],
            user.get("phone", ""),
            user.get("address", {}).get("city", ""),
            user.get("address", {}).get("state", ""),
            donation_count, str(user.get("created_at", "")),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=donors_report.csv"}
    )
 
 
@router.get("/reports/ngos")
async def export_ngos_csv(current_user: dict = Depends(require_role(UserRole.admin))):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["NGO ID", "Name", "Email", "Phone", "City", "State",
                     "Verified", "Joined At"])
    cursor = users_collection.find({"role": "ngo"}).sort("created_at", -1)
    async for user in cursor:
        writer.writerow([
            str(user["_id"]), user["name"], user["email"],
            user.get("phone", ""),
            user.get("address", {}).get("city", ""),
            user.get("address", {}).get("state", ""),
            "Yes" if user.get("is_verified") else "No",
            str(user.get("created_at", "")),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ngos_report.csv"}
    )
 