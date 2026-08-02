from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

# A single client instance, reused across the app (Motor handles connection pooling internally)
client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.mongo_db_name]

# Collection handles — import these wherever you need to query a collection
users_collection = db["users"]
ngo_profiles_collection = db["ngo_profiles"]
donations_collection = db["donations"]
notifications_collection = db["notifications"]


async def ping_database() -> bool:
    """Quick connectivity check — call this on startup to fail fast if Mongo is unreachable."""
    try:
        await client.admin.command("ping")
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False