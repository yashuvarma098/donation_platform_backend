# System Architecture — Donation & Reuse Platform

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │   Donor UI   │  │   NGO UI     │  │   Admin UI   │        │
│   │  (React)     │  │  (React)     │  │  (React)     │        │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│          │                 │                  │                 │
│          └─────────────────┼──────────────────┘                │
│                            │ HTTP/JSON                          │
│                            │ (Axios + JWT Bearer Token)         │
└────────────────────────────┼────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    API LAYER (FastAPI)                           │
│                            │                                    │
│   ┌─────────────────────────▼──────────────────────────────┐   │
│   │                    main.py                              │   │
│   │   Rate Limiting → Security Headers → CORS → Routers    │   │
│   └──────┬──────────────────────────────────────────┬──────┘   │
│          │                                          │           │
│   ┌──────▼──────┐                          ┌───────▼──────┐    │
│   │  JWT Auth   │                          │   Routers    │    │
│   │ Middleware  │                          │              │    │
│   │             │                          │ /auth        │    │
│   │ get_current │                          │ /donations   │    │
│   │ _user()     │                          │ /ngos        │    │
│   │             │                          │ /admin       │    │
│   │ require_    │                          │ /notifs      │    │
│   │ role()      │                          │ /complaints  │    │
│   └──────┬──────┘                          │ /ratings     │    │
│          │                                 └───────┬──────┘    │
│          └─────────────────┬───────────────────────┘           │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │ Motor (Async)
┌────────────────────────────┼────────────────────────────────────┐
│                   DATABASE LAYER                                 │
│                            │                                    │
│   ┌─────────────────────────▼──────────────────────────────┐   │
│   │               MongoDB Atlas (Cloud)                     │   │
│   │                                                         │   │
│   │  users          donations       notifications           │   │
│   │  ngo_profiles   complaints      ratings                 │   │
│   │  categories                                             │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flow

```
User                  Frontend              Backend               MongoDB
 │                       │                     │                     │
 │── Enter email/pwd ───>│                     │                     │
 │                       │── POST /auth/login ─>│                    │
 │                       │                     │── find user ──────>│
 │                       │                     │<── user doc ───────│
 │                       │                     │── verify bcrypt     │
 │                       │                     │── create JWT token  │
 │                       │<── {access_token} ──│                     │
 │                       │── store in          │                     │
 │                       │   localStorage      │                     │
 │<── redirect to ───────│                     │                     │
 │   dashboard           │                     │                     │
 │                       │                     │                     │
 │── access protected ──>│                     │                     │
 │   page                │── GET /auth/me ─────>                    │
 │                       │   Authorization:    │                     │
 │                       │   Bearer <token>    │                     │
 │                       │                     │── decode JWT        │
 │                       │                     │── find user ──────>│
 │                       │<── user data ───────│                     │
 │<── show page ─────────│                     │                     │
```

---

## Donation Lifecycle

```
DONOR                    PLATFORM              NGO                ADMIN
  │                         │                   │                   │
  │── Create Donation ─────>│                   │                   │
  │   (items + NGO +        │── Save to DB      │                   │
  │    pickup details)      │   status:         │                   │
  │                         │   "requested"     │                   │
  │<── Notification ────────│                   │                   │
  │   "Submitted!"          │── Notification ──>│                   │
  │                         │   "New Request!"  │                   │
  │                         │                   │── View request    │
  │                         │                   │── Accept ────────>│
  │                         │<─────────────────── status:          │
  │                         │                      "accepted"       │
  │<── Notification ────────│                                       │
  │   "Accepted!"           │                                       │
  │                         │                   │── Schedule ──────>│
  │                         │<─────────────────── status:          │
  │                         │                      "scheduled"      │
  │<── Notification ────────│                                       │
  │   "Scheduled!"          │                                       │
  │                         │                   │── Collect ───────>│
  │<── Notification ────────│<─────────────────── status:          │
  │   "Collected!"          │                      "collected"      │
  │                         │                   │── Complete ──────>│
  │<── Notification ────────│<─────────────────── status:          │
  │   "Completed!"          │                      "completed"      │
  │                         │                                       │
  │── Rate Experience ─────>│                                       │
  │   (1-5 stars)           │── Save to ratings                    │
  │                         │── Update avg KPI                     │
```

---

## Database Schema

```
USERS Collection:
{
  _id: ObjectId,
  name: String,
  email: String (unique, indexed),
  password_hash: String,
  role: "donor" | "ngo" | "admin",
  phone: String,
  address: { street, city, state, pincode },
  is_verified: Boolean,
  created_at: DateTime
}

DONATIONS Collection:
{
  _id: ObjectId,
  donor_id: String (indexed),
  ngo_id: String (indexed),
  items: [{
    category: String,
    item_type: String,
    quantity: Number,
    condition: "new"|"good"|"fair",
    description: String
  }],
  pickup_address: { street, city, state, pincode },
  scheduled_time: DateTime,
  status: "requested"|"accepted"|"scheduled"
          |"collected"|"completed"|"cancelled",
  status_history: [{
    status: String,
    timestamp: DateTime,
    note: String
  }],
  created_at: DateTime,
  updated_at: DateTime
}

NOTIFICATIONS Collection:
{
  _id: ObjectId,
  user_id: String (indexed),
  message: String,
  type: String,
  is_read: Boolean,
  created_at: DateTime
}

RATINGS Collection:
{
  _id: ObjectId,
  donation_id: String,
  donor_id: String,
  ngo_id: String,
  rating: Number (1-5),
  feedback: String,
  created_at: DateTime
}

COMPLAINTS Collection:
{
  _id: ObjectId,
  raised_by: String,
  raised_by_name: String,
  raised_by_role: String,
  donation_id: String,
  subject: String,
  description: String,
  status: "open" | "resolved",
  resolution: String,
  created_at: DateTime,
  updated_at: DateTime
}
```

---

## Security Architecture

```
Request
   │
   ▼
Rate Limiter (60 req/min global, 30 req/min auth)
   │
   ▼
Security Headers Middleware
(X-Frame-Options, X-XSS-Protection, etc.)
   │
   ▼
CORS Middleware
(whitelist: localhost:3000, vercel.app)
   │
   ▼
Route Handler
   │
   ▼
JWT Verification (get_current_user)
   │
   ▼
Role Check (require_role)
   │
   ▼
Input Validation (Pydantic v2)
   │
   ▼
Business Logic
   │
   ▼
MongoDB (Motor async)
```

---

## Deployment Architecture

```
Internet
   │
   ├──> Vercel (Frontend)
   │    React App
   │    URL: donation-platform.vercel.app
   │    Build: npm run build
   │    Env: REACT_APP_API_URL
   │
   └──> Render (Backend)
        FastAPI App
        URL: donation-platform-api.onrender.com
        Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
        Env: MONGO_URI, JWT_SECRET
             │
             └──> MongoDB Atlas (Database)
                  Cloud: cluster0.xxxxx.mongodb.net
                  DB: donation_platform
                  Collections: 7
```