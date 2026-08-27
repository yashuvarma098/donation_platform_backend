from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
import time

from app.database import ping_database, create_indexes
from app.routers import auth, donations, ngos, admin, notifications, complaints, ratings, impact



# ─── RATE LIMITER ─────────────────────────────────────────────────────────────
# Simple in-memory rate limiter
# Max 60 requests per minute per IP

request_counts = defaultdict(list)
RATE_LIMIT = 60       # max requests
WINDOW = 60           # per 60 seconds


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    # Remove old requests outside the window
    request_counts[ip] = [t for t in request_counts[ip] if now - t < WINDOW]
    if len(request_counts[ip]) >= RATE_LIMIT:
        return True
    request_counts[ip].append(now)
    return False


# ─── LIFESPAN ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    is_connected = await ping_database()
    if is_connected:
        print("MongoDB connected successfully.")
        await create_indexes()
    else:
        print("WARNING: MongoDB connection failed. Check your MONGO_URI in .env")
    yield
    # Shutdown — nothing needed


# ─── APP ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Donation & Reuse Platform API",
    description="API for connecting donors with verified NGOs",
    version="1.0.0",
    lifespan=lifespan
)


# ─── MIDDLEWARE: Rate Limiting ────────────────────────────────────────────────

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Auth endpoints pe strict rate limiting (30 req/min)
    ip = request.client.host
    if request.url.path.startswith("/auth"):
        auth_counts = request_counts.get(f"auth_{ip}", [])
        now = time.time()
        auth_counts = [t for t in auth_counts if now - t < WINDOW]
        if len(auth_counts) >= 30:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait a minute."}
            )
        auth_counts.append(now)
        request_counts[f"auth_{ip}"] = auth_counts

    # Global rate limit
    if is_rate_limited(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."}
        )

    response = await call_next(request)
    return response


# ─── MIDDLEWARE: Security Headers ─────────────────────────────────────────────

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://donation-platform-frontend-umber.vercel.app/",  # production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# ─── ROUTERS ──────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(donations.router)
app.include_router(ngos.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(complaints.router)
app.include_router(ratings.router)
app.include_router(impact.router)


# ─── HEALTH CHECKS ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Donation Platform API is running", "version": "1.0.0"}


@app.get("/health/db")
async def db_health_check():
    is_connected = await ping_database()
    return {"mongodb_connected": is_connected, "status": "ok" if is_connected else "error"}