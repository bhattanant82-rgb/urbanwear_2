"""
services/upload_service.py
Handles file uploads to Cloudinary.
Mirrors the Node.js cloudinary-multer-storage middleware.
"""
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


def upload_to_cloudinary(file_bytes: bytes, filename: str, folder: str = "urbanwear") -> str:
    """
    Upload raw file bytes to Cloudinary and return the secure URL.
    folder: Cloudinary folder name (e.g. 'urbanwear/products')
    """
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=folder,
        resource_type="auto",   # handles images AND videos
        public_id=filename
    )
    return result.get("secure_url", "")
