"""
routers/reviews.py
Review routes — mirrors Node.js reviews.routes.js + reviews.controller.js
POST /api/v1/reviews             (auth)
GET  /api/v1/reviews/stats       (admin)
GET  /api/v1/reviews/summary/:productId  (public)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId
from datetime import datetime, timezone

from database import reviews_col, products_col, orders_col
from models.schemas import StandaloneReviewIn
from routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/reviews", tags=["reviews"])


# ─── POST /api/v1/reviews ────────────────────────────────────────────────────

@router.post("/", status_code=201)
def post_review(body: StandaloneReviewIn, current_user: dict = Depends(get_current_user)):
    user_oid = ObjectId(current_user["_id"])

    try:
        product_oid = ObjectId(body.productId)
        order_oid = ObjectId(body.orderId)
    except Exception:
        raise HTTPException(400, "Invalid productId or orderId")

    if not products_col.find_one({"_id": product_oid}):
        raise HTTPException(404, "Product not found")

    order = orders_col.find_one({"_id": order_oid})
    if not order:
        raise HTTPException(404, "Order not found")

    if str(order.get("userId", "")) != current_user["_id"]:
        raise HTTPException(403, "This order does not belong to you")

    # Verify product is in the order
    product_in_order = any(
        str(p.get("productId", "")) == body.productId
        for p in order.get("products", [])
    )
    if not product_in_order:
        raise HTTPException(400, "This product is not in the specified order")

    # Check for duplicate review
    if reviews_col.find_one({"orderId": order_oid, "productId": product_oid}):
        raise HTTPException(400, "You have already reviewed this product for this order")

    now = datetime.now(timezone.utc)
    review_doc = {
        "productId": product_oid,
        "userId": user_oid,
        "orderId": order_oid,
        "rating": int(body.rating),
        "reviewText": body.reviewText or "",
        "verifiedBuyer": True,
        "createdAt": now,
        "updatedAt": now,
    }

    result = reviews_col.insert_one(review_doc)
    review_doc["_id"] = str(result.inserted_id)
    review_doc["productId"] = body.productId
    review_doc["userId"] = current_user["_id"]
    review_doc["orderId"] = body.orderId

    return {"success": True, "message": "Review added successfully", "data": review_doc}


# ─── GET /api/v1/reviews/stats (admin) ───────────────────────────────────────

@router.get("/stats")
def get_review_stats(
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(require_admin)
):
    pipeline = [
        {"$group": {"_id": "$productId", "averageRating": {"$avg": "$rating"}, "reviewCount": {"$sum": 1}}},
        {"$lookup": {"from": "products", "localField": "_id", "foreignField": "_id", "as": "product"}},
        {"$unwind": "$product"},
        {"$project": {"_id": 0, "productId": "$product._id", "title": "$product.title",
                       "averageRating": 1, "reviewCount": 1}},
        {"$sort": {"reviewCount": -1, "averageRating": -1}},
        {"$limit": limit}
    ]
    results = list(reviews_col.aggregate(pipeline))
    for r in results:
        if "productId" in r:
            r["productId"] = str(r["productId"])
    return {"success": True, "message": "Review stats", "data": results}


# ─── GET /api/v1/reviews/summary/:productId (public) ─────────────────────────

@router.get("/summary/{product_id}")
def get_review_summary(product_id: str):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    pipeline = [
        {"$match": {"productId": oid}},
        {"$facet": {
            "distribution": [{"$group": {"_id": "$rating", "count": {"$sum": 1}}}],
            "stats": [{"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}]
        }}
    ]
    result = list(reviews_col.aggregate(pipeline))
    data = result[0] if result else {"distribution": [], "stats": []}

    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for dist in data.get("distribution", []):
        distribution[dist["_id"]] = dist["count"]

    stats = data.get("stats", [])
    average_rating = stats[0]["avg"] if stats else 0
    total_count = stats[0]["count"] if stats else 0

    return {
        "success": True,
        "data": {
            "averageRating": average_rating,
            "totalCount": total_count,
            "distribution": distribution
        }
    }
