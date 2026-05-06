
import sys
import os
sys.path.append(os.path.join(os.getcwd(), "urbanwear-fastapi"))

from database import users_col
from services.auth_service import hash_password
from datetime import datetime, timezone

def create_test_admin():
    email = "testadmin@example.com"
    password = "admin123"
    
    # Check if exists
    if users_col.find_one({"email": email}):
        print(f"User {email} already exists. Updating password.")
        users_col.update_one({"email": email}, {"$set": {"password": hash_password(password), "role": "admin"}})
    else:
        users_col.insert_one({
            "name": "Test Admin",
            "email": email,
            "password": hash_password(password),
            "role": "admin",
            "createdAt": datetime.now(timezone.utc)
        })
        print(f"Created test admin: {email}")

if __name__ == "__main__":
    create_test_admin()
