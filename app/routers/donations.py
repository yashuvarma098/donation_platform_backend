from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_role
from app.database import donations_collection, users_collection, notifications_collection
from app.models.donation import DonationCreate, DonationInDB, DonationOut, DonationStatusUpdate, StatusHistoryEntry
from app.models.user import UserRole

router = APIRouter(prefix="/donations", tags=["Donations"])


def donation_doc_to_out(doc: dict) -> dict:
    """MongoDB document ko clean response mein convert karo."""
    return {
        "id": str(doc["_id"]),
        "donor_id": str(doc["donor_id"]),
        "ngo_id": str(doc["ngo_id"]),
        "items": doc["items"],
        "pickup_address": doc["pickup_address"],
        "scheduled_time": doc["scheduled_time"],
        "status": doc["status"],
        "status_history": doc.get("status_history", []),
        "created_at": doc["created_at"],
        "updated_at": doc["updated_at"],
    }


# ─── DONOR: Donation Create Karo ───────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_donation(
    donation_in: DonationCreate,
    current_user: dict = Depends(require_role(UserRole.donor))
):
    """Donor nayi donation create karta hai."""

    # NGO exist karta hai? Check karo
    try:
        ngo = await users_collection.find_one({
            "_id": ObjectId(donation_in.ngo_id),
            "role": "ngo",
            "is_verified": True
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid NGO ID")

    if not ngo:
        raise HTTPException(status_code=404, detail="Verified NGO not found")

    # Donation document banao
    donation_data = DonationInDB(
        donor_id=str(current_user["_id"]),
        ngo_id=donation_in.ngo_id,
        items=[item.model_dump() for item in donation_in.items],
        pickup_address=donation_in.pickup_address.model_dump(),
        scheduled_time=donation_in.scheduled_time,
        status="requested",
        status_history=[
            StatusHistoryEntry(
                status="requested",
                note="Donation request created by donor"
            ).model_dump()
        ]
    )

    result = await donations_collection.insert_one(donation_data.model_dump())
    created = await donations_collection.find_one({"_id": result.inserted_id})

    #Send notification to donor
    await notifications_collection.insert_one({
        "user_id": str(current_user["_id"]),
        "message": f"Your Doantion request has been submitted successfully!",
        "type": "donation_created",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    #Send notification to NGO
    await notifications_collection.insert_one({
        "user_id": donation_in.ngo_id,
        "message": f"New donation request received from {current_user['name']}!",
        "type": "new_request",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    return {"message": "Donation created successfully!", "donation": donation_doc_to_out(created)}


# ─── DONOR: Apni Saari Donations Dekho ─────────────────────────────────────

@router.get("/my")
async def get_my_donations(
    current_user: dict = Depends(require_role(UserRole.donor))
):
    """Donor ki saari donations — newest pehle."""
    donations = []
    cursor = donations_collection.find(
        {"donor_id": str(current_user["_id"])}
    ).sort("created_at", -1)  # newest first

    async for doc in cursor:
        donations.append(donation_doc_to_out(doc))

    return {"donations": donations, "total": len(donations)}

#-------------NGO: Apne liye Aayi Requests dekho-----------------

@router.get("/ngo/requests")
async def get_ngo_requests(
    current_user:dict = Depends(require_role(UserRole.ngo))
):
    """Ngo k liye aayi saari donation requests"""
    donations = []
    cursor = donations_collection.find(
        {"ngo_id": str(current_user["_id"])}
    ).sort("created_at", -1)

    async for doc in cursor:
        #Donor ka naam bhi include kro
        donor = await users_collection.find_one({"_id": ObjectId(doc["donor_id"])})
        donation = donation_doc_to_out(doc)
        donation["donor_name"] = donor["name"] if donor else "Unknown"
        donation["donor_phone"] = donor.get("phone", "") if donor else ""
        donations.append(donation)

    return {"donations": donations, "total": len(donations)}

#-------------NGO: Doantion Status Update kro --------------------------

@router.patch("/{donation_id}/status")
async def update_donation_status(
    donation_id: str,
    update: DonationStatusUpdate,
    current_user: dict = Depends(require_role(UserRole.ngo))
):
    """NGO donation accept/reject/complete karta hai."""
    try:
        doc = await donations_collection.find_one({"_id": ObjectId(donation_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation Id")
    
    if not doc:
        raise HTTPException(status_code=404, detail="Donation not found")
    
    #Sirf us NGO ka donation update kar sake
    if doc["ngo_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    #Status history mein naya entry add kro
    new_history_entry = StatusHistoryEntry(
        status = update.status,
        note = update.note or f"Status updated to {update.status} by NGO"
    ).model_dump()

    await donations_collection.update_one(
        {"_id": ObjectId(donation_id)},
        {
            "$set": {
                "status": update.status,
                "updated_at": datetime.utcnow()
            },
            "$push": {"status_history": new_history_entry}
        }
    )

    #Donor ko notification bhejo status change pe
    status_messages = {
        "accepted": "Great news! Your donation has been accepted by the NGO.",
        "scheduled": "Your donation pickup has been scheduled!",
        "collected": "Your donation items have been collected!",
        "completed": "Your donation has been successfully completed. Thank You!",
        "cancelled": "Your donation request has been cancelled by the NGO.",
    }

    message = status_messages.get(update.status, f"Your donation status has been updated to {update.status}.")

    await notifications_collection.insert_one({
        "user_id": doc["donor_id"],
        "message": message,
        "type": "status_update",
        "is_read": False,
        "created_at": datetime.utcnow()
    })

    updated = await donations_collection.find_one({"_id": ObjectId(donation_id)})

    return {"message": "Status updated!", "donation": donation_doc_to_out(updated)}


# ─── DONOR: Ek Specific Donation Ki Detail ──────────────────────────────────

@router.get("/{donation_id}")
async def get_donation_detail(
    donation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Ek donation ki poori detail — status history ke saath."""
    try:
        doc = await donations_collection.find_one({"_id": ObjectId(donation_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid donation ID")

    if not doc:
        raise HTTPException(status_code=404, detail="Donation not found")

    # Sirf owner ya NGO ya admin dekh sake
    user_id = str(current_user["_id"])
    role = current_user["role"]
    if role == "donor" and doc["donor_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return donation_doc_to_out(doc)