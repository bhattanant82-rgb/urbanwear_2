
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv("urbanwear-fastapi/.env")
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["urbanwear"]
admin = db["users"].find_one({"role": "admin"})

if admin:
    print(f"Admin Email: {admin.get('email')}")
else:
    print("No admin found.")
