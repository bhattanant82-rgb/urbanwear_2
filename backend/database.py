"""
database.py - MongoDB connection using PyMongo
Connects to MongoDB Atlas using the MONGO_URI from .env
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set in .env file")

# Create a single MongoClient instance (reused across requests)
client = MongoClient(MONGO_URI)

# Get the database (name is part of the URI: /urbanwear)
db = client["urbanwear"]

# Collection references — mirrors the Node.js Mongoose models
products_col     = db["products"]
users_col        = db["users"]
orders_col       = db["orders"]
categories_col   = db["categories"]
reviews_col      = db["productreviews"]   # Mongoose auto-lowercases + pluralizes
carts_col        = db["carts"]
addresses_col    = db["addresses"]
home_banners_col = db["home_banners"]
contact_messages_col = db["contact_messages"]

print("[OK] MongoDB connection established")
