"""
routers/addresses.py — User Address Management

Endpoints for authenticated users to:
- GET /api/v1/addresses → List their addresses
- POST /api/v1/addresses → Add a new address
- PUT /api/v1/addresses/:id → Update address
- DELETE /api/v1/addresses/:id → Delete address
"""

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime
from database import addresses_col
from models.schemas import AddressIn
from routers.auth import get_current_user

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("")
def get_addresses(current_user: dict = Depends(get_current_user)):
    """Get all addresses for the authenticated user"""
    user_id = ObjectId(current_user["_id"])
    
    addresses = list(addresses_col.find({"userId": user_id}, sort=[("isDefault", -1)]))
    
    # Convert ObjectId to string for JSON serialization
    for addr in addresses:
        addr["id"] = str(addr["_id"])
    
    return {"success": True, "data": addresses}


@router.post("")
def create_address(body: AddressIn, current_user: dict = Depends(get_current_user)):
    """Create a new address for the authenticated user"""
    user_id = ObjectId(current_user["_id"])
    
    # If this is marked as default, unset previous defaults
    if body.isDefault:
        addresses_col.update_many(
            {"userId": user_id},
            {"$set": {"isDefault": False}}
        )
    
    address_doc = {
        "userId": user_id,
        "name": body.name,
        "mobile": body.mobile,
        "email": body.email or '',
        "address": body.address,
        "city": body.city or '',
        "state": body.state or '',
        "pincode": body.pincode or '',
        "isDefault": body.isDefault or False,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    
    result = addresses_col.insert_one(address_doc)
    address_doc["id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "message": "Address added successfully",
        "data": address_doc
    }


@router.put("/{addressId}")
def update_address(addressId: str, body: AddressIn, current_user: dict = Depends(get_current_user)):
    """Update an existing address"""
    user_id = ObjectId(current_user["_id"])
    address_id = ObjectId(addressId)
    
    # Verify ownership
    existing = addresses_col.find_one({"_id": address_id, "userId": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # If this is marked as default, unset previous defaults
    if body.isDefault:
        addresses_col.update_many(
            {"userId": user_id, "_id": {"$ne": address_id}},
            {"$set": {"isDefault": False}}
        )
    
    update_data = {
        "name": body.name,
        "mobile": body.mobile,
        "email": body.email or '',
        "address": body.address,
        "city": body.city or '',
        "state": body.state or '',
        "pincode": body.pincode or '',
        "isDefault": body.isDefault or False,
        "updatedAt": datetime.utcnow()
    }
    
    result = addresses_col.update_one(
        {"_id": address_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update address")
    
    updated_doc = addresses_col.find_one({"_id": address_id})
    updated_doc["id"] = str(updated_doc["_id"])
    
    return {
        "success": True,
        "message": "Address updated successfully",
        "data": updated_doc
    }


@router.delete("/{addressId}")
def delete_address(addressId: str, current_user: dict = Depends(get_current_user)):
    """Delete an address"""
    user_id = ObjectId(current_user["_id"])
    address_id = ObjectId(addressId)
    
    result = addresses_col.delete_one({"_id": address_id, "userId": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Address not found")
    
    return {"success": True, "message": "Address deleted successfully"}
