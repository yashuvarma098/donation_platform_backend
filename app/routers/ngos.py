from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.database import users_collection

router = APIRouter(prefix="/ngos", tags=["NGOs"])


@router.get("/verified")
async def get_verified_ngos(current_user: dict = Depends(get_current_user)):
    """
    Verified NGOs ki list — seedha users collection se.
    Donor donation create karte waqt yahan se NGO select karega.
    """
    ngos = []

    cursor = users_collection.find({
        "role": "ngo",
        "is_verified": True
    })

    async for user in cursor:
        ngos.append({
            "user_id": str(user["_id"]),
            "org_name": user.get("name", ""),
            "city": user.get("address", {}).get("city", ""),
            "state": user.get("address", {}).get("state", ""),
            "phone": user.get("phone", ""),
        })

    return {"ngos": ngos, "total": len(ngos)}