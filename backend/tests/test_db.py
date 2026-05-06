
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv("urbanwear-fastapi/.env")
MONGO_URI = os.getenv("MONGO_URI")

print(f"Connecting to: {MONGO_URI}")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["urbanwear"]
    users_count = db["users"].count_documents({})
    print(f"Success! Found {users_count} users.")
except Exception as e:
    print(f"Error connecting: {e}")
