from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.database import ping_database
from app.routers import auth, donations, ngos, admin, notifications

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify MongoDB is reachable before accepting requests
    is_connected = await ping_database()
    if is_connected:
        print("MongoDB connected successfully.")
    else:
        print("WARNING: MongoDB connection failed. Check your MONGO_URI in .env")
    yield
    # Shutdown: nothing to clean up yet (Motor closes connections automatically)


app = FastAPI(title="Donation & Reuse Platform API", lifespan=lifespan)

#Allow the React frontend (running on different port ) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

app.include_router(auth.router)
app.include_router(donations.router)
app.include_router(ngos.router)
app.include_router(admin.router)
app.include_router(notifications.router)


@app.get("/")
async def root():
    return {"message": "Donation Platform API is running"}


@app.get("/health/db")
async def db_health_check():
    is_connected = await ping_database()
    return {"mongodb_connected": is_connected}