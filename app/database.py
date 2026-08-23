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

async def create_indexes():
    #Users
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("role")
    await users_collection.create_index([("role",1), ("is_verified", 1)])
    await users_collection.create_index("address.city")

    #Donaions
    await donations_collection.create_index("donor_id")
    await donations_collection.create_index("donor_id")
    await donations_collection.create_index("ngo_id")
    await donations_collection.create_index("status")
    await donations_collection.create_index([("donor_id", 1), ("status", 1)])
    await donations_collection.create_index([("ngo_id", 1), ("status", 1)])
    await donations_collection.create_index("created_at")
 
    # Notifications
    await notifications_collection.create_index("user_id")
    await notifications_collection.create_index([("user_id", 1), ("is_read", 1)])
    await notifications_collection.create_index("created_at")
 
    # NGO Profiles
    await ngo_profiles_collection.create_index("user_id", unique=True)
    await ngo_profiles_collection.create_index("verification_status")

    print("MongoDB indexes created successfully.")


async def ping_database() -> bool:
    """Quick connectivity check — call this on startup to fail fast if Mongo is unreachable."""
    try:
        await client.admin.command("ping")
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False