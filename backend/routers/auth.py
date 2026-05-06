"""
routers/auth.py
Authentication routes — identical to the Node.js auth.routes.js + auth.controller.js
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import users_col
from models.schemas import RegisterIn, LoginIn
from services.auth_service import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Dependency: get current user from Bearer token ──────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authorized, no token")
    payload = decode_token(credentials.credentials)
    user_id = payload.get("userId")
    from bson import ObjectId
    user = users_col.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user["_id"] = str(user["_id"])
    return user


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _serialize_user(user: dict) -> dict:
    """Return safe user dict with string _id."""
    return {
        "_id": str(user["_id"]),
        "id":  str(user["_id"]),
        "name":  user.get("name", ""),
        "email": user.get("email", ""),
        "role":  user.get("role", "user"),
    }


# ─── POST /api/v1/auth/register ──────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(body: RegisterIn):
    name, email, password = body.name.strip(), body.email.strip().lower(), body.password

    if len(name) < 2:
        raise HTTPException(400, "Name must be at least 2 characters")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    if users_col.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")

    hashed = hash_password(password)
    now = datetime.now(timezone.utc)
    result = users_col.insert_one({
        "name": name,
        "email": email,
        "password": hashed,
        "role": "user",
        "addresses": [],
        "createdAt": now,
        "updatedAt": now,
    })
    user = users_col.find_one({"_id": result.inserted_id})
    token = create_token({"userId": str(user["_id"]), "email": user["email"], "role": user["role"]})

    return {
        "success": True,
        "message": "User registered successfully",
        "data": {
            "token": token,
            "user": _serialize_user(user)
        }
    }


# ─── POST /api/v1/auth/login ─────────────────────────────────────────────────

@router.post("/login")
def login(body: LoginIn):
    email, password = body.email.strip().lower(), body.password

    if not email or not password:
        raise HTTPException(400, "Email and password are required")

    user = users_col.find_one({"email": email})
    if not user:
        raise HTTPException(401, "Invalid email or password")

    if not verify_password(password, user.get("password", "")):
        raise HTTPException(401, "Invalid email or password")

    token = create_token({"userId": str(user["_id"]), "email": user["email"], "role": user["role"]})

    return {
        "success": True,
        "data": {
            "token": token,
            "user": _serialize_user(user)
        }
    }


# ─── GET /api/v1/auth/me ─────────────────────────────────────────────────────

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {"success": True, "data": _serialize_user(current_user)}


