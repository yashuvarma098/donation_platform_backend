# Deployment Guide — Donation & Reuse Platform

## Prerequisites
- GitHub account
- MongoDB Atlas account (free tier)
- Render.com account (free tier)
- Vercel account (free tier)

---

## Step 1: MongoDB Atlas Setup

1. Go to [mongodb.com/cloud/atlas](https://mongodb.com/cloud/atlas)
2. Create free M0 cluster
3. Database Access → Add user with username/password
4. Network Access → Add IP → Allow from Anywhere (0.0.0.0/0)
5. Connect → Drivers → Copy connection string:
   ```
   mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/
   ```

---

## Step 2: Deploy Backend to Render

### 2a. Push backend to GitHub
```bash
cd donation_platform_backend
git init
git add .
git commit -m "Initial backend"
git branch -M main
git remote add origin https://github.com/<username>/donation-platform-backend.git
git push -u origin main
```

### 2b. Create Render Web Service
1. Go to [render.com](https://render.com) → New → Web Service
2. Connect GitHub → Select `donation-platform-backend`
3. Configure:
   ```
   Name:          donation-platform-api
   Runtime:       Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add Environment Variables:
   ```
   MONGO_URI     = mongodb+srv://...
   MONGO_DB_NAME = donation_platform
   JWT_SECRET    = your-random-32-char-secret
   ```
5. Click "Create Web Service"
6. Wait 3-5 minutes → Note your URL:
   ```
   https://donation-platform-api.onrender.com
   ```

### 2c. Verify backend is live
Open: `https://donation-platform-api.onrender.com/health/db`
Should return: `{"mongodb_connected": true}`

---

## Step 3: Deploy Frontend to Vercel

### 3a. Update frontend .env for production
In `donation-platform-frontend/.env`:
```
REACT_APP_API_URL=https://donation-platform-api.onrender.com
```

### 3b. Push frontend to GitHub
```bash
cd donation-platform-frontend
git init
git add .
git commit -m "Initial frontend"
git branch -M main
git remote add origin https://github.com/<username>/donation-platform-frontend.git
git push -u origin main
```

### 3c. Deploy to Vercel
1. Go to [vercel.com](https://vercel.com) → New Project
2. Import `donation-platform-frontend` from GitHub
3. Framework: Create React App (auto-detected)
4. Add Environment Variable:
   ```
   REACT_APP_API_URL = https://donation-platform-api.onrender.com
   ```
5. Click Deploy
6. Wait 2 minutes → Note your URL:
   ```
   https://donation-platform-frontend.vercel.app
   ```

---

## Step 4: Update CORS for Production

In `app/main.py`, add your Vercel URL to allowed origins:
```python
allow_origins=[
    "http://localhost:3000",
    "https://donation-platform-frontend.vercel.app",  # your URL
]
```
Commit and push → Render auto-redeploys.

---

## Step 5: Create Admin Account

In MongoDB Atlas → Browse Collections → users → INSERT DOCUMENT:
```json
{
  "name": "Admin User",
  "email": "admin@yourdomain.com",
  "password_hash": "$2b$12$ZoJ7MpF21WktbeIcQuqNqOf8Vu6xKfYvhkQrOyqI5enTNw/iC1oDe",
  "role": "admin",
  "phone": "9000000000",
  "address": {
    "street": "Admin Office",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001"
  },
  "is_verified": true,
  "created_at": {"$date": {"$numberLong": "1700000000000"}}
}
```
Password: `admin123`
(Generate new hash: `python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('yourpassword'))"`)

---

## Step 6: Verify Full Deployment

| Check | URL | Expected |
|---|---|---|
| Backend health | /health/db | `{"mongodb_connected": true}` |
| API docs | /docs | Swagger UI loads |
| Frontend | vercel URL | Login page loads |
| Register | /register | Form submits successfully |
| Login | /login | Dashboard loads |
| Admin | /dashboard/admin | Admin panel loads |

---

## Troubleshooting

### Backend not connecting to MongoDB
- Check MONGO_URI has correct username/password
- Check Atlas Network Access allows 0.0.0.0/0
- Check MONGO_DB_NAME matches

### Frontend CORS error
- Add Vercel URL to `allow_origins` in main.py
- Redeploy backend

### Render cold start (slow first request)
- Free tier sleeps after 15min inactivity
- First request takes 30-60 seconds to wake up
- Upgrade to paid plan to avoid this

### Admin login fails
- Regenerate password hash locally
- Re-insert admin document in Atlas