"""
services/auth_service.py
Handles password hashing (bcrypt) and JWT creation/verification.
Mirrors the Node.js bcryptjs + jsonwebtoken logic.
"""
import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status

JWT_SECRET = os.getenv("JWT_SECRET", "urbanwear-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt (salt=10)."""
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Compare a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_token(payload: dict) -> str:
    """Create a JWT token. payload should contain userId, email, role."""
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS)
    data["exp"] = expire
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises 401 HTTPException on failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
