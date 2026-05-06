"""
routers/cart.py
Cart routes — mirrors Node.js cart.routes.js + cart.controller.js
All routes require authentication.
GET    /api/v1/cart
POST   /api/v1/cart
PATCH  /api/v1/cart/:productId
DELETE /api/v1/cart/:productId
DELETE /api/v1/cart
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from bson import ObjectId

from database import carts_col, products_col
from models.schemas import CartItemIn, CartUpdateIn
from routers.auth import get_current_user

router = APIRouter(prefix="/cart", tags=["cart"])

DELIVERY_FEE = 49


def _summarize_cart(cart_doc: dict) -> dict:
    """
    Compute cart summary: totalMRP, totalDiscount, subtotal, totalGST, deliveryFee, grandTotal.
    Mirrors the Node.js summarizeCart() helper.
    """
    total_mrp = 0.0
    total_discount = 0.0
    items_out = []

    for item in cart_doc.get("items", []):
        product = item.get("_product")   # injected after population
        qty = item.get("quantity", 1)
        price = product["price"] if product else item.get("price", 0)
        discount = product.get("discount_percentage", 0) if product else 0

        item_mrp = price * qty
        discount_amount = item_mrp * (discount / 100)
        taxable_value = item_mrp - discount_amount

        total_mrp += item_mrp
        total_discount += discount_amount

        item_out = {
            "productId": str(item.get("productId", "")),
            "productName": item.get("productName", product["title"] if product else ""),
            "price": price,
            "discount_percentage": discount,
            "quantity": qty,
            "size": item.get("size", ""),
            "color": item.get("color", ""),
            "imageUrl": item.get("imageUrl", (product.get("images")[0] if product and product.get("images") and len(product.get("images")) > 0 else "")),
            "taxableValue": round(taxable_value, 2)
        }
        # Include _id of cart item if available
        if "_id" in item:
            item_out["_id"] = str(item["_id"])
        items_out.append(item_out)

    subtotal = total_mrp - total_discount
    gst_rate = 0.12 if subtotal > 1000 else 0.05
    total_gst = subtotal * gst_rate
    grand_total = round(subtotal + total_gst + DELIVERY_FEE)

    return {
        "items": items_out,
        "summary": {
            "totalMRP": round(total_mrp, 2),
            "totalDiscount": round(total_discount, 2),
            "subtotal": round(subtotal, 2),
            "totalGST": round(total_gst, 2),
            "deliveryFee": DELIVERY_FEE,
            "grandTotal": grand_total
        }
    }


def _populate_cart(cart_doc: dict) -> dict:
    """Fetch product details for each cart item and attach as _product."""
    for item in cart_doc.get("items", []):
        pid = item.get("productId")
        if pid:
            product = products_col.find_one({"_id": ObjectId(str(pid))})
            item["_product"] = product
        else:
            item["_product"] = None
    return cart_doc


def _get_or_create_cart(user_oid: ObjectId) -> dict:
    cart = carts_col.find_one({"userId": user_oid})
    if not cart:
        now = datetime.now(timezone.utc)
        result = carts_col.insert_one({"userId": user_oid, "items": [], "locked": False,
                                       "createdAt": now, "updatedAt": now})
        cart = carts_col.find_one({"_id": result.inserted_id})
    return cart


# ─── GET /api/v1/cart ────────────────────────────────────────────────────────

@router.get("")
def get_cart(current_user: dict = Depends(get_current_user)):
    user_oid = ObjectId(current_user["_id"])
    cart = _get_or_create_cart(user_oid)

    # Filter orphaned items
    valid_items = []
    for item in cart.get("items", []):
        pid = item.get("productId")
        if pid and products_col.find_one({"_id": ObjectId(str(pid))}, {"_id": 1}):
            valid_items.append(item)
    if len(valid_items) != len(cart.get("items", [])):
        carts_col.update_one({"userId": user_oid}, {"$set": {"items": valid_items}})
        cart["items"] = valid_items

    cart = _populate_cart(cart)
    return {"success": True, "data": _summarize_cart(cart)}


# ─── POST /api/v1/cart ───────────────────────────────────────────────────────

@router.post("")
def add_or_update_cart_item(body: CartItemIn, current_user: dict = Depends(get_current_user)):
    user_oid = ObjectId(current_user["_id"])

    print(f"[CART] Add request from user {current_user.get('email')} - Body: {body.model_dump()}", flush=True)
    try:
        product_oid = ObjectId(body.productId)
    except Exception:
        print(f"[CART] ERROR: Invalid productId: {body.productId}", flush=True)
        raise HTTPException(400, "Invalid productId")

    product = products_col.find_one({"_id": product_oid})
    if not product:
        raise HTTPException(404, "Product not found")

    cart = _get_or_create_cart(user_oid)
    if cart.get("locked"):
        raise HTTPException(400, "Cart is locked")

    items = cart.get("items", [])
    match_index = next(
        (i for i, x in enumerate(items)
         if str(x.get("productId", "")) == body.productId
         and (x.get("size", "") == (body.size or ""))
         and (x.get("color", "") == (body.color or ""))),
        None
    )

    if match_index is not None:
        items[match_index]["quantity"] = body.quantity
    else:
        items.append({
            "productId": product_oid,
            "productName": product["title"],
            "price": product["price"],
            "quantity": body.quantity,
            "size": body.size or "",
            "color": body.color or "",
            "imageUrl": body.imageUrl or (product.get("images")[0] if product.get("images") and len(product.get("images")) > 0 else "")
        })

    carts_col.update_one({"userId": user_oid}, {"$set": {"items": items, "updatedAt": datetime.now(timezone.utc)}})
    updated_cart = _populate_cart(carts_col.find_one({"userId": user_oid}))
    return {"success": True, "message": "Cart updated", "data": _summarize_cart(updated_cart)}


# ─── PATCH /api/v1/cart/:productId ───────────────────────────────────────────

@router.patch("/{product_id}")
def update_cart_item_by_product(
    product_id: str,
    body: CartUpdateIn,
    size: str = Query(None),
    color: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    user_oid = ObjectId(current_user["_id"])
    cart = carts_col.find_one({"userId": user_oid})
    if not cart:
        raise HTTPException(404, "Cart not found")

    items = cart.get("items", [])
    # Find matching item
    item = next(
        (x for x in items
         if str(x.get("productId", "")) == product_id
         and (size is None or x.get("size", "") == size)
         and (color is None or x.get("color", "") == color)),
        None
    )
    if not item:
        raise HTTPException(404, "Cart item not found")

    if body.quantity is not None:
        item["quantity"] = int(body.quantity)
    if body.size is not None:
        item["size"] = body.size
    if body.color is not None:
        item["color"] = body.color

    carts_col.update_one({"userId": user_oid}, {"$set": {"items": items, "updatedAt": datetime.now(timezone.utc)}})
    updated_cart = _populate_cart(carts_col.find_one({"userId": user_oid}))
    return {"success": True, "data": _summarize_cart(updated_cart)}


# ─── DELETE /api/v1/cart/:productId ──────────────────────────────────────────

@router.delete("/{product_id}")
def remove_cart_item_by_product(
    product_id: str,
    size: str = Query(None),
    color: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    user_oid = ObjectId(current_user["_id"])
    cart = carts_col.find_one({"userId": user_oid})
    if not cart:
        raise HTTPException(404, "Cart not found")

    items = cart.get("items", [])
    if not size and not color:
        items = [x for x in items if str(x.get("productId", "")) != product_id]
    else:
        items = [x for x in items if not (
            str(x.get("productId", "")) == product_id
            and (size is None or x.get("size", "") == size)
            and (color is None or x.get("color", "") == color)
        )]

    carts_col.update_one({"userId": user_oid}, {"$set": {"items": items, "updatedAt": datetime.now(timezone.utc)}})
    updated_cart = _populate_cart(carts_col.find_one({"userId": user_oid}))
    return {"success": True, "data": _summarize_cart(updated_cart)}


# ─── DELETE /api/v1/cart (clear all) ─────────────────────────────────────────

@router.delete("")
def clear_cart(current_user: dict = Depends(get_current_user)):
    user_oid = ObjectId(current_user["_id"])
    carts_col.update_one(
        {"userId": user_oid},
        {"$set": {"items": [], "updatedAt": datetime.now(timezone.utc)}}
    )
    return {"success": True, "data": {"items": [], "summary": {}}}
