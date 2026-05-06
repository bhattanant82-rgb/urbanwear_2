"""
routers/categories.py
Category routes — mirrors Node.js categories.routes.js logic
GET   /api/v1/categories
PATCH /api/v1/categories/:id
POST  /api/v1/categories/:id/banner  (file upload)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from bson import ObjectId

from database import categories_col
from routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/categories", tags=["categories"])


def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    if "category_banner" not in doc:
        doc["category_banner"] = ""
    return doc


# ─── GET /api/v1/categories ──────────────────────────────────────────────────

@router.get("")
def get_categories():
    cursor = categories_col.find({"isActive": True}).sort([("order", 1), ("name", 1)])
    return {
        "success": True,
        "message": "Categories retrieved",
        "data": [_serialize(c) for c in cursor]
    }


# ─── PATCH /api/v1/categories/:id ────────────────────────────────────────────

@router.patch("/{category_id}")
def update_category_details(
    category_id: str,
    updates: dict,
    current_user: dict = Depends(require_admin)
):
    try:
        oid = ObjectId(category_id)
    except Exception:
        raise HTTPException(400, "Invalid category ID")

    updates["updatedAt"] = datetime.now(timezone.utc)
    category = categories_col.find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True
    )
    if not category:
        raise HTTPException(404, "Category not found")

    return {"success": True, "message": "Category updated", "data": _serialize(category)}


# ─── POST /api/v1/categories/:id/banner ──────────────────────────────────────

@router.post("/{category_id}/banner")
async def upload_category_banner(
    category_id: str,
    bannerFile: UploadFile = File(...),
    bannerType: str = Form("image"),
    current_user: dict = Depends(require_admin)
):
    try:
        oid = ObjectId(category_id)
    except Exception:
        raise HTTPException(400, "Invalid category ID")

    file_bytes = await bannerFile.read()
    from services.upload_service import upload_to_cloudinary
    media_url = upload_to_cloudinary(file_bytes, bannerFile.filename, folder="urbanwear/categories")

    update_data = {"bannerType": bannerType, "updatedAt": datetime.now(timezone.utc)}
    if bannerType == "video":
        update_data["bannerVideo"] = media_url
        update_data["bannerImage"] = media_url
    else:
        update_data["bannerImage"] = media_url

    category = categories_col.find_one_and_update(
        {"_id": oid},
        {"$set": update_data},
        return_document=True
    )
    if not category:
        raise HTTPException(404, "Category not found")

    return {
        "success": True,
        "message": "Banner uploaded successfully",
        "bannerUrl": media_url,
        "bannerType": bannerType,
        "data": _serialize(category)
    }
