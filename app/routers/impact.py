from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.database import donations_collection, users_collection

router = APIRouter(prefix="/impact", tags=["Impact"])

# Average weight estimates (kg per item)
ITEM_WEIGHTS = {
    "clothes": 0.5,
    "household_items": 2.0,
    "books": 0.8,
    "electronics": 1.5,
    "toys": 0.6,
    "furniture": 15.0,
}

# CO2 saved per kg of textile (EPA estimate: 3.6 kg CO2 per kg textile diverted)
CO2_PER_KG = 3.6


@router.get("/platform")
async def get_platform_impact(
    current_user: dict = Depends(get_current_user)
):
    """Platform-wide environmental + social impact stats."""

    # All completed donations
    total_donations = await donations_collection.count_documents({})
    completed_donations = await donations_collection.count_documents({"status": "completed"})
    total_donors = await users_collection.count_documents({"role": "donor"})
    total_ngos = await users_collection.count_documents({"role": "ngo", "is_verified": True})

    # Calculate total items and weight from completed donations
    total_items = 0
    total_weight_kg = 0.0
    categories_count = {}

    cursor = donations_collection.find({"status": "completed"})
    async for doc in cursor:
        for item in doc.get("items", []):
            qty = item.get("quantity", 1)
            cat = item.get("category", "household_items")
            total_items += qty
            weight = ITEM_WEIGHTS.get(cat, 1.0) * qty
            total_weight_kg += weight
            categories_count[cat] = categories_count.get(cat, 0) + qty

    # Environmental calculations
    co2_saved_kg = round(total_weight_kg * CO2_PER_KG, 1)
    co2_saved_tonnes = round(co2_saved_kg / 1000, 2)
    landfill_diverted_kg = round(total_weight_kg, 1)

    return {
        # Social impact
        "total_donations": total_donations,
        "completed_donations": completed_donations,
        "total_donors": total_donors,
        "total_ngos": total_ngos,
        "total_items_donated": total_items,

        # Environmental impact
        "landfill_diverted_kg": landfill_diverted_kg,
        "co2_saved_kg": co2_saved_kg,
        "co2_saved_tonnes": co2_saved_tonnes,

        # Category breakdown
        "categories_breakdown": categories_count,
    }


@router.get("/personal")
async def get_personal_impact(
    current_user: dict = Depends(get_current_user)
):
    """Personal impact for logged in donor."""
    user_id = str(current_user["_id"])

    total_items = 0
    total_weight_kg = 0.0
    categories = {}
    completed = 0
    total = 0

    cursor = donations_collection.find({"donor_id": user_id})
    async for doc in cursor:
        total += 1
        if doc.get("status") == "completed":
            completed += 1
            for item in doc.get("items", []):
                qty = item.get("quantity", 1)
                cat = item.get("category", "household_items")
                total_items += qty
                total_weight_kg += ITEM_WEIGHTS.get(cat, 1.0) * qty
                categories[cat] = categories.get(cat, 0) + qty

    co2_saved_kg = round(total_weight_kg * CO2_PER_KG, 1)

    return {
        "total_donations": total,
        "completed_donations": completed,
        "total_items": total_items,
        "weight_diverted_kg": round(total_weight_kg, 1),
        "co2_saved_kg": co2_saved_kg,
        "categories": categories,
    }