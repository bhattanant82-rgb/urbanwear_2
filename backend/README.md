# UrbanWear — Backend

This folder contains the **Python FastAPI backend** for UrbanWear.

## Stack
- Python 3.10+
- FastAPI + Uvicorn
- PyMongo (MongoDB Atlas)
- Cloudinary (image/video uploads)

## Structure

```
backend/
├── main.py             ← FastAPI app entry point
├── database.py         ← MongoDB connection + collection references
├── requirements.txt    ← Python dependencies
├── .env                ← Environment variables (secret keys, DB URI, SMTP)
├── models/
│   └── schemas.py      ← Pydantic request/response models
├── routers/            ← API route handlers
│   ├── auth.py         ← Login, signup, JWT, OTP
│   ├── products.py     ← Product CRUD + search + filters
│   ├── categories.py   ← Category management
│   ├── orders.py       ← Order placement + tracking
│   ├── cart.py         ← Shopping cart
│   ├── addresses.py    ← User addresses
│   ├── reviews.py      ← Product reviews
│   ├── admin.py        ← Admin dashboard + analytics
│   └── contact.py      ← Contact form
├── services/           ← Business logic / utilities
│   ├── auth_service.py     ← JWT + bcrypt helpers
│   ├── email_service.py    ← SMTP email (order confirmations, OTP)
│   ├── otp_service.py      ← OTP generation + verification
│   ├── pdf_service.py      ← Order invoice PDF generation
│   ├── upload_service.py   ← Cloudinary file upload helper
│   └── serializer.py       ← MongoDB document serializer
├── scripts/
│   └── ui_add_products.ps1 ← PowerShell script for bulk product seeding
└── tests/                  ← Utility + test scripts
    ├── create_test_admin.py
    ├── test_db.py
    ├── test_smtp.py
    └── ...
```

## Running

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
Edit `.env` with your MongoDB URI, SMTP credentials, and Cloudinary keys.

### 3. Start the server
```bash
uvicorn main:app --reload --port 5000
```

### API Access
- **Base URL**: http://127.0.0.1:5000
- **API Docs**: http://127.0.0.1:5000/docs
- **Health Check**: http://127.0.0.1:5000/health

## Notes
- Uploaded files (banners, categories) are saved to `../frontend/uploads/`
- FastAPI serves them at `/uploads/*` via StaticFiles mount
