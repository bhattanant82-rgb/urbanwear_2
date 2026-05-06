"""
routers/orders.py
Order routes — mirrors Node.js orders.routes.js + orders.controller.js
All routes require authentication (JWT Bearer token).
POST /api/v1/orders
GET  /api/v1/orders
GET  /api/v1/orders/:id
PUT  /api/v1/orders/:id/cancel
GET  /api/v1/orders/:id/receipt  (stub — returns 501)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId

from database import orders_col, products_col, carts_col, users_col
from models.schemas import OrderIn, CancelOrderIn
from routers.auth import get_current_user
from services.pdf_service import generate_order_receipt
from services.email_service import send_order_confirmation

router = APIRouter(prefix="/orders", tags=["orders"])


from datetime import datetime, date

def deep_serialize(obj):
    if isinstance(obj, dict):
        return {k: deep_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_serialize(v) for v in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj

def _serialize_order(order: dict) -> dict:
    return deep_serialize(order)


# ─── POST /api/v1/orders ─────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_order(body: OrderIn, current_user: dict = Depends(get_current_user)):
    user_id_str = current_user["_id"]
    user_oid = ObjectId(user_id_str)

    # Resolve shipping address
    shipping_data = body.shipping or body.shippingAddress
    products_input = body.products or []
    payment_method = (body.paymentMethod or "COD").upper()
    payment_info = body.paymentInfo

    # If no products in body, pull from cart
    if not products_input:
        cart = carts_col.find_one({"userId": user_oid})
        if not cart or not cart.get("items"):
            raise HTTPException(400, "No products in cart")
        if cart.get("locked"):
            raise HTTPException(400, "Cart is locked")

        products_input = [
            OrderIn.model_validate({"products": [{"productId": str(i["productId"]), "quantity": i["quantity"],
                                                   "size": i.get("size"), "color": i.get("color"),
                                                   "productName": i.get("productName", "")}]}).products[0]
            for i in cart["items"]
        ]
        carts_col.update_one({"userId": user_oid}, {"$set": {"locked": True}})

    if not shipping_data or not shipping_data.name or not shipping_data.mobile or not shipping_data.address:
        raise HTTPException(400, "Shipping name, mobile and address are required")

    total_amount = 0.0
    order_products = []

    for item in products_input:
        try:
            pid = ObjectId(item.productId)
        except Exception:
            raise HTTPException(400, f"Invalid productId: {item.productId}")

        product = products_col.find_one({"_id": pid})
        if not product:
            raise HTTPException(404, "Product not found")
        if product["stock"] < item.quantity:
            raise HTTPException(400, f"Insufficient stock for {product['title']}")

        # Reduce stock
        products_col.update_one({"_id": pid}, {"$inc": {"stock": -item.quantity}})

        qty = item.quantity
        price = product["price"]
        discount = product.get("discount_percentage", 0)

        item_mrp = price * qty
        discount_amount = item_mrp * (discount / 100)
        taxable_value = item_mrp - discount_amount
        unit_taxable = price - (price * discount / 100)
        gst_rate = 0.12 if unit_taxable > 1000 else 0.05
        gst_amount = taxable_value * gst_rate
        line_total = taxable_value + gst_amount

        total_amount += line_total
        # Pydantic model — use attribute access, not .get()
        item_size  = getattr(item, "size", "") or ""
        item_color = getattr(item, "color", "") or ""
        item_name  = getattr(item, "productName", "") or product.get("title", "")

        # Convert pid to ObjectId if it's a string, to ensure consistency in DB
        product_oid = pid if isinstance(pid, ObjectId) else ObjectId(pid)

        order_products.append({
            "productId": product_oid,
            "productName": item_name,
            "quantity": qty,
            "price": price,
            "discount": discount,
            "size": item_size,
            "color": item_color
        })

    total_amount += 49  # Fixed delivery fee

    now = datetime.now(timezone.utc)
    order_doc = {
        "userId": user_oid,
        "products": order_products,
        "totalAmount": round(total_amount, 2),
        "paymentMethod": "COD" if payment_method == "COD" else payment_method,
        "shipping": shipping_data.model_dump(),
        "createdAt": now,
        "updatedAt": now,
    }

    if payment_method == "COD":
        order_doc["paymentStatus"] = "Pending"
        order_doc["orderStatus"] = "Placed"
    else:
        pi_status = payment_info.status.upper() if payment_info and payment_info.status else ""
        order_doc["paymentStatus"] = "Completed" if pi_status == "SUCCESS" else ("Failed" if pi_status == "FAILED" else "Pending")
        order_doc["paymentId"] = payment_info.paymentId if payment_info else None
        order_doc["orderStatus"] = "Pending"

    result = orders_col.insert_one(order_doc)
    print(f"[ORDERS] ✓ insert_one result: {result.inserted_id}", flush=True)

    # Clear cart
    carts_col.update_one({"userId": user_oid}, {"$set": {"items": [], "locked": False}})

    order_doc["_id"] = result.inserted_id
    order_doc["userId"] = user_oid

    # Send confirmation email (non-blocking)
    try:
        user_doc = users_col.find_one({"_id": user_oid})
        user_email = current_user.get("email") or (user_doc.get("email") if user_doc else None)
        user_name  = current_user.get("name")  or (user_doc.get("name")  if user_doc else "Valued Customer")
        
        if user_email:
            print(f"[ORDERS-EMAIL] 📤 Initiating confirmation email to: {user_email}", flush=True)
            success = send_order_confirmation(user_email, user_name, deep_serialize(order_doc))
            if success:
                print(f"[ORDERS-EMAIL] ✅ Email process completed (SMTP or Fallback)", flush=True)
            else:
                print(f"[ORDERS-EMAIL] ❌ Email process failed completely", flush=True)
        else:
            print("[ORDERS-EMAIL] ⚠️ No email found for user — skipping email", flush=True)
    except Exception as mail_err:
        print(f"[ORDERS-EMAIL] ❌ Unexpected mail error (non-fatal): {mail_err}", flush=True)
        import traceback
        traceback.print_exc()

    return {"success": True, "message": "Order created successfully", "data": deep_serialize(order_doc)}


# ─── GET /api/v1/orders ──────────────────────────────────────────────────────

@router.get("")
def get_user_orders(current_user: dict = Depends(get_current_user)):
    user_oid = ObjectId(current_user["_id"])
    cursor = orders_col.find({"userId": user_oid}).sort("createdAt", -1)
    return {"success": True, "data": [_serialize_order(o) for o in cursor]}


# ─── GET /api/v1/orders/:id ──────────────────────────────────────────────────

@router.get("/{order_id}")
def get_order_by_id(order_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(400, "Invalid order ID")

    order = orders_col.find_one({"_id": oid})
    if not order:
        raise HTTPException(404, "Order not found")

    # Auth check: owner or admin
    if current_user.get("role") != "admin" and str(order.get("userId", "")) != current_user["_id"]:
        raise HTTPException(403, "Unauthorized")

    return {"success": True, "data": _serialize_order(order)}


# ─── PUT /api/v1/orders/:id/cancel ───────────────────────────────────────────

@router.put("/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelOrderIn = None, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(400, "Invalid order ID")

    order = orders_col.find_one({"_id": oid})
    if not order:
        raise HTTPException(404, "Order not found")

    if str(order.get("userId", "")) != current_user["_id"]:
        raise HTTPException(403, "Not authorized")

    allowed_statuses = ["Pending", "Processing", "Placed", "CONFIRMED"]
    if order.get("orderStatus") not in allowed_statuses:
        raise HTTPException(400, f"Orders in {order.get('orderStatus')} status cannot be cancelled")

    # Restore stock
    for item in order.get("products", []):
        pid = item.get("productId")
        if pid:
            products_col.update_one({"_id": pid}, {"$inc": {"stock": item.get("quantity", 0)}})

    update = {
        "orderStatus": "Cancelled",
        "paymentStatus": "Cancelled",
        "cancelledAt": datetime.now(timezone.utc)
    }
    if body and body.reason:
        update["cancellationReason"] = body.reason

    orders_col.update_one({"_id": oid}, {"$set": update})

    return {"success": True, "message": "Order cancelled successfully"}


# ─── POST /api/v1/orders/cancel/:id ──────────────────────────────────────────

@router.post("/cancel/{order_id}")
def cancel_order_post(order_id: str, body: CancelOrderIn = None, current_user: dict = Depends(get_current_user)):
    """
    Explicit POST endpoint for order cancellation as requested.
    """
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(400, "Invalid order ID")

    order = orders_col.find_one({"_id": oid})
    if not order:
        raise HTTPException(404, "Order not found")

    # Security check: User can only cancel their own orders
    if str(order.get("userId", "")) != current_user["_id"]:
        raise HTTPException(403, "Not authorized to cancel this order")

    # Validation: Only Placed or Processing orders can be cancelled
    cancellable_statuses = ["Placed", "Processing", "Pending"]
    current_status = order.get("orderStatus")
    if current_status not in cancellable_statuses:
        raise HTTPException(400, f"Order cannot be cancelled. Current status: {current_status}")

    # Restore stock
    for item in order.get("products", []):
        pid = item.get("productId")
        if pid:
            products_col.update_one({"_id": pid}, {"$inc": {"stock": item.get("quantity", 0)}})

    # Update order
    now = datetime.now(timezone.utc)
    update = {
        "orderStatus": "Cancelled",
        "paymentStatus": "Cancelled",
        "cancelledAt": now,
        "updatedAt": now
    }
    if body and body.reason:
        update["cancelReason"] = body.reason

    orders_col.update_one({"_id": oid}, {"$set": update})

    return {"success": True, "message": "Order cancelled successfully"}


# ─── GET /api/v1/orders/:id/receipt (stub) ───────────────────────────────────

@router.get("/{order_id}/receipt")
def get_receipt(order_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(400, "Invalid order ID")

    order = orders_col.find_one({"_id": oid})
    if not order:
        raise HTTPException(404, "Order not found")

    # Auth check: owner or admin
    if current_user.get("role") != "admin" and str(order.get("userId", "")) != current_user["_id"]:
        raise HTTPException(403, "Unauthorized")

    # Generate PDF
    pdf_buffer = generate_order_receipt(order)
    
    filename = f"urbanwear_receipt_{order_id}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
