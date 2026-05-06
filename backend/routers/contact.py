"""
routers/contact.py
Handles Contact Us submissions and admin retrieval
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, EmailStr
from bson import ObjectId
import traceback

from database import contact_messages_col
from routers.auth import require_admin
from services.email_service import send_contact_notification

router = APIRouter(tags=["contact"])

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    subject: str
    message: str

def _serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc

# --- POST /contact (Public) ---
@router.post("/contact")
def submit_contact(msg: ContactMessage):
    try:
        doc = msg.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        doc["is_read"] = False
        
        result = contact_messages_col.insert_one(doc)
        doc["_id"] = str(result.inserted_id)

        # email admin notification
        send_contact_notification(doc)
            
        return {"success": True, "message": "Your message has been sent successfully", "data": doc}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

# --- GET /admin/contact-messages (Admin Protected) ---
@router.get("/admin/contact-messages")
def get_contact_messages(current_user: dict = Depends(require_admin)):
    cursor = contact_messages_col.find().sort("created_at", -1)
    messages = [_serialize(doc) for doc in cursor]
    return {"success": True, "data": messages}

# --- PUT /admin/contact-messages/{message_id}/read (Admin Protected) ---
@router.put("/admin/contact-messages/{message_id}/read")
def toggle_message_read(message_id: str, payload: dict = Body(...), current_user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(message_id)
        is_read = payload.get("is_read", True)
        updated = contact_messages_col.find_one_and_update(
            {"_id": oid},
            {"$set": {"is_read": is_read}},
            return_document=True
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"success": True, "message": "Status updated", "data": _serialize(updated)}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid message ID")
