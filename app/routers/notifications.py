from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.database import notifications_collection

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/my")
async def get_my_notifications(
    current_user: dict = Depends(get_current_user)
):
    """User ki saari notifications — newest pehle."""
    notifications = []
    cursor = notifications_collection.find(
        {"user_id": str(current_user["_id"])}
    ).sort("created_at", -1).limit(20)

    async for doc in cursor:
        notifications.append({
            "id": str(doc["_id"]),
            "message": doc["message"],
            "type": doc.get("type", "general"),
            "is_read": doc.get("is_read", False),
            "created_at": doc["created_at"],
        })

    unread_count = await notifications_collection.count_documents({
        "user_id": str(current_user["_id"]),
        "is_read": False
    })

    return {
        "notifications": notifications,
        "total": len(notifications),
        "unread_count": unread_count
    }


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Ek notification read mark karo."""
    await notifications_collection.update_one(
        {
            "_id": ObjectId(notification_id),
            "user_id": str(current_user["_id"])
        },
        {"$set": {"is_read": True}}
    )
    return {"message": "Marked as read"}


@router.patch("/read-all")
async def mark_all_as_read(
    current_user: dict = Depends(get_current_user)
):
    """Saari notifications ek saath read mark karo."""
    result = await notifications_collection.update_many(
        {
            "user_id": str(current_user["_id"]),
            "is_read": False
        },
        {"$set": {"is_read": True}}
    )
    return {"message": f"{result.modified_count} notifications marked as read"}