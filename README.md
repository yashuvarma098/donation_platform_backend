# Donation & Reuse Platform — Backend API

A FastAPI + MongoDB backend for connecting donors with verified NGOs for donating clothes and household items.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python) |
| Database | MongoDB Atlas (Motor async driver) |
| Auth | JWT (python-jose) + bcrypt |
| Server | Uvicorn (ASGI) |

---

## Project Structure

```
donation_platform_backend/
├── app/
│   ├── main.py              # FastAPI app, middleware, routers
│   ├── config.py            # Settings from .env
│   ├── database.py          # MongoDB connection + indexes
│   ├── models/
│   │   ├── user.py          # User schemas (Donor/NGO/Admin)
│   │   └── donation.py      # Donation + Item schemas
│   ├── routers/
│   │   ├── auth.py          # /auth/register, /auth/login, /auth/me
│   │   ├── donations.py     # /donations/ (CRUD + status updates)
│   │   ├── ngos.py          # /ngos/verified, /ngos/profile
│   │   ├── admin.py         # /admin/stats, verify NGOs, reports
│   │   ├── notifications.py # /notifications/my, mark read
│   │   ├── complaints.py    # /complaints/ (raise + resolve)
│   │   └── ratings.py       # /ratings/ (star ratings)
│   └── core/
│       ├── security.py      # JWT + bcrypt utilities
│       └── dependencies.py  # get_current_user, require_role
├── .env                     # Secrets (never commit)
├── .env.example             # Template
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### 1. Clone and create virtual environment
```bash
git clone <your-repo-url>
cd donation_platform_backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create `.env` file
```bash
copy .env.example .env       # Windows
cp .env.example .env         # Mac/Linux
```

Fill in your values:
```
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
MONGO_DB_NAME=donation_platform
JWT_SECRET=your-long-random-secret-key
```

### 4. Run the server
```bash
uvicorn app.main:app --reload
```

Server runs at: `http://127.0.0.1:8000`
API docs at: `http://127.0.0.1:8000/docs`

---

## API Endpoints

### Authentication
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | /auth/register | Register donor/NGO | No |
| POST | /auth/login | Login, get JWT token | No |
| GET | /auth/me | Get current user | Yes |

### Donations
| Method | Endpoint | Description | Role |
|---|---|---|---|
| POST | /donations/ | Create donation | Donor |
| GET | /donations/my | My donations | Donor |
| GET | /donations/ngo/requests | NGO requests | NGO |
| PATCH | /donations/{id}/status | Update status | NGO |
| GET | /donations/{id} | Donation detail | Any |

### NGOs
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /ngos/verified | List verified NGOs | Yes |
| POST | /ngos/profile | Create/update profile | NGO |
| GET | /ngos/profile/me | My NGO profile | NGO |

### Admin
| Method | Endpoint | Description | Role |
|---|---|---|---|
| GET | /admin/stats | Platform KPIs | Admin |
| GET | /admin/ngos | All NGOs | Admin |
| PATCH | /admin/ngos/{id}/verify | Verify NGO | Admin |
| PATCH | /admin/ngos/{id}/reject | Reject NGO | Admin |
| GET | /admin/donations | All donations | Admin |
| GET | /admin/reports/donations | CSV export | Admin |
| GET | /admin/reports/donors | CSV export | Admin |
| GET | /admin/reports/ngos | CSV export | Admin |

### Notifications
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /notifications/my | My notifications | Yes |
| PATCH | /notifications/{id}/read | Mark read | Yes |
| PATCH | /notifications/read-all | Mark all read | Yes |

### Complaints
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | /complaints/ | Raise complaint | Donor/NGO |
| GET | /complaints/my | My complaints | Donor/NGO |
| GET | /complaints/all | All complaints | Admin |
| PATCH | /complaints/{id}/resolve | Resolve | Admin |

### Ratings
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | /ratings/ | Submit rating | Donor |
| GET | /ratings/check/{id} | Check if rated | Donor |

---

## MongoDB Collections

| Collection | Description |
|---|---|
| users | Donors, NGOs, Admins |
| donations | All donation records |
| ngo_profiles | NGO org details |
| notifications | User notifications |
| complaints | Disputes/complaints |
| ratings | Star ratings |
| categories | Item categories |

---

## User Roles

| Role | Can Do |
|---|---|
| Donor | Create donations, view NGOs, rate, complain |
| NGO | Accept/reject/complete donations, manage profile |
| Admin | Verify NGOs, view all data, export reports |

---

## Security Features

- JWT authentication (24hr expiry)
- bcrypt password hashing
- Role-based access control (RBAC)
- Rate limiting (60 req/min global, 30 req/min auth)
- Security headers (XSS, Clickjacking protection)
- Input validation (Pydantic v2)
- MongoDB indexes for performance

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| MONGO_URI | MongoDB connection string | mongodb+srv://... |
| MONGO_DB_NAME | Database name | donation_platform |
| JWT_SECRET | Secret key for JWT | random-32-char-string |
| JWT_ALGORITHM | JWT algorithm | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiry | 1440 |