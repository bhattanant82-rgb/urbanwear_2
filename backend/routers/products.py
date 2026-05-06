"""
routers/products.py
Product routes — identical to Node.js products.routes.js + products.controller.js
"""
import re
from datetime import datetime, timezone, timedelta
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from database import products_col, reviews_col, orders_col
from models.schemas import ProductIn, ReviewIn
from routers.auth import get_current_user, require_admin
from services.serializer import mongo_to_dict

router = APIRouter(prefix="/products", tags=["products"])


def _serialize(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict (handles ObjectId, datetime, nested)."""
    return mongo_to_dict(doc)


# ─── GET /api/v1/products ────────────────────────────────────────────────────

@router.get("")
def get_products(
    category: str = Query(None),
    minPrice: float = Query(None, alias="min_price"),
    maxPrice: float = Query(None, alias="max_price"),
    minDiscount: float = Query(None),
    size: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=1000),
):
    filt: dict = {}
    if category:
        filt["category"] = {"$regex": f"^{re.escape(category)}$", "$options": "i"}
    
    if size:
        # sizes is an array in the DB: e.g. ["S", "M", "L"]
        filt["sizes"] = {"$in": [size]}

    if minDiscount is not None:
        filt["discount_percentage"] = {"$gte": minDiscount}
    
    if minPrice is not None or maxPrice is not None:
        price_filt = {}
        if minPrice is not None:
            price_filt["$gte"] = minPrice
        if maxPrice is not None:
            price_filt["$lte"] = maxPrice
        filt["price"] = price_filt

    skip = (page - 1) * limit
    cursor = products_col.find(filt).sort("createdAt", -1).skip(skip).limit(limit)
    items = [_serialize(p) for p in cursor]
    total = products_col.count_documents(filt)

    return {
        "success": True,
        "message": "Products retrieved",
        "data": items,
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": ceil(total / limit) if limit else 1
        }
    }


# ─── GET /api/v1/products/trending ───────────────────────────────────────────

@router.get("/trending")
def trending_products(limit: int = Query(10, ge=1, le=50)):
    now = datetime.now(timezone.utc)
    date7 = now - timedelta(days=7)
    date30 = now - timedelta(days=30)

    pipeline = [
        {"$lookup": {
            "from": "orders",
            "let": {"pid": "$_id"},
            "pipeline": [
                {"$unwind": "$products"},
                {"$match": {"$expr": {"$eq": ["$products.productId", "$$pid"]}}},
                {"$project": {"quantity": "$products.quantity", "createdAt": 1}}
            ],
            "as": "sales"
        }},
        {"$addFields": {
            "totalSales": {"$sum": "$sales.quantity"},
            "sales7": {"$sum": {"$map": {
                "input": "$sales", "as": "s",
                "in": {"$cond": [{"$gte": ["$$s.createdAt", date7]}, "$$s.quantity", 0]}
            }}},
            "sales30": {"$sum": {"$map": {
                "input": "$sales", "as": "s",
                "in": {"$cond": [{"$gte": ["$$s.createdAt", date30]}, "$$s.quantity", 0]}
            }}}
        }},
        {"$lookup": {
            "from": "productreviews",
            "let": {"pid": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$productId", "$$pid"]}}},
                {"$group": {"_id": None, "avgRating": {"$avg": "$rating"}, "reviewCount": {"$sum": 1}}}
            ],
            "as": "reviewStats"
        }},
        {"$addFields": {
            "avgRating": {"$ifNull": [{"$arrayElemAt": ["$reviewStats.avgRating", 0]}, 0]},
            "reviewCount": {"$ifNull": [{"$arrayElemAt": ["$reviewStats.reviewCount", 0]}, 0]}
        }},
        {"$addFields": {
            "trendingScore": {"$add": [
                {"$multiply": ["$sales30", 0.5]},
                {"$multiply": ["$sales7", 0.3]},
                {"$multiply": ["$avgRating", 2]}
            ]}
        }},
        {"$sort": {"trendingScore": -1, "sales30": -1, "reviewCount": -1}},
        {"$project": {"title": 1, "price": 1, "images": 1, "category": 1, "stock": 1,
                       "totalSales": 1, "sales7": 1, "sales30": 1, "avgRating": 1,
                       "reviewCount": 1, "trendingScore": 1}},
        {"$limit": limit}
    ]

    results = list(products_col.aggregate(pipeline))
    for r in results:
        r["_id"] = str(r["_id"])

    return {"success": True, "message": "Trending products", "data": results}


# ─── GET /api/v1/products/search/autocomplete ────────────────────────────────

@router.get("/search/autocomplete")
def autocomplete_search(q: str = Query(None)):
    if not q or len(q) < 2:
        return {"success": True, "data": []}
    regex = {"$regex": q, "$options": "i"}
    cursor = products_col.find(
        {"$or": [{"title": regex}, {"category": regex}]},
        {"title": 1, "price": 1, "images": 1, "category": 1}
    ).limit(5)
    return {"success": True, "data": [_serialize(p) for p in cursor]}


# ─── GET /api/v1/products/analytics/{filter} ─────────────────────────────────

@router.get("/analytics/{filter}")
def get_product_analytics(
    filter: str = None,
    category: str = Query(None),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get products filtered by analytics criteria:
    - bestsellers: Top selling products
    - trending: Recently trending products 
    - timeless: High-rated products
    """
    
    filt: dict = {}
    if category:
        filt["category"] = {"$regex": f"^{re.escape(category)}$", "$options": "i"}
    
    filter = filter.lower() if filter else 'bestsellers'
    now = datetime.now(timezone.utc)
    date7 = now - timedelta(days=7)
    date30 = now - timedelta(days=30)
    
    if filter in ['bestsellers', 'trending', 'timeless']:
        pipeline = [
            {"$match": filt} if filt else None,
            {"$lookup": {
                "from": "orders",
                "let": {"pid": "$_id"},
                "pipeline": [
                    {"$unwind": "$products"},
                    {"$match": {"$expr": {"$eq": ["$products.productId", "$$pid"]}}},
                    {"$project": {"quantity": "$products.quantity", "createdAt": 1}}
                ],
                "as": "sales"
            }},
            {"$lookup": {
                "from": "productreviews",
                "let": {"pid": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$productId", "$$pid"]}}},
                    {"$group": {"_id": None, "avgRating": {"$avg": "$rating"}, "reviewCount": {"$sum": 1}}}
                ],
                "as": "review_stats"
            }},
            {"$addFields": {
                "totalSales": {"$sum": "$sales.quantity"},
                "sales7": {"$sum": {"$map": {
                    "input": "$sales", "as": "s",
                    "in": {"$cond": [{"$gte": ["$$s.createdAt", date7]}, "$$s.quantity", 0]}
                }}},
                "sales30": {"$sum": {"$map": {
                    "input": "$sales", "as": "s",
                    "in": {"$cond": [{"$gte": ["$$s.createdAt", date30]}, "$$s.quantity", 0]}
                }}},
                "avgRating": {"$ifNull": [{"$arrayElemAt": ["$review_stats.avgRating", 0]}, 0]},
                "reviewCount": {"$ifNull": [{"$arrayElemAt": ["$review_stats.reviewCount", 0]}, 0]}
            }}
        ]
        
        # Add filter stage and remove None
        pipeline = [p for p in pipeline if p is not None]
        
        # Sort by filter type
        if filter == 'bestsellers':
            pipeline.append({"$sort": {"totalSales": -1}})
        elif filter == 'trending':
            pipeline.append({"$sort": {"sales7": -1}})
        else:  # timeless
            pipeline.append({"$sort": {"avgRating": -1, "reviewCount": -1}})
        
        # FINAL PROJECTION TO MATCH FRONTEND (category-analytics.js)
        # Expected keys: productId, name, totalSales, trendingScore, avgRating
        pipeline.append({
            "$project": {
                "_id": 1,
                "productId": "$_id",
                "name": "$title",
                "title": 1,
                "price": 1,
                "images": 1,
                "category": 1,
                "totalSales": 1,
                "sales7": 1,
                "sales30": 1,
                "avgRating": 1,
                "reviewCount": 1,
                "trendingScore": 1
            }
        })
        
        pipeline.append({"$limit": limit})
        
        items = [_serialize(p) for p in products_col.aggregate(pipeline)]
        return {
            "success": True,
            "message": f"Products retrieved (filter: {filter})",
            "data": items,
            "filter": filter,
            "category": category or "all"
        }
    
    return {"success": False, "message": "Invalid filter. Use: bestsellers, trending, or timeless"}


# ─── GET /api/v1/products/:id/reviews ────────────────────────────────────────

@router.get("/{product_id}/reviews")
def get_product_reviews(product_id: str):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    cursor = reviews_col.find({"productId": oid}).sort("createdAt", -1)
    reviews = []
    from database import users_col
    for r in cursor:
        r["_id"] = str(r["_id"])
        r["productId"] = str(r["productId"])
        r["orderId"] = str(r.get("orderId", ""))
        uid = r.get("userId")
        if isinstance(uid, ObjectId):
            u = users_col.find_one({"_id": uid}, {"name": 1, "email": 1})
            r["userId"] = {"_id": str(uid), "name": u["name"] if u else "", "email": u["email"] if u else ""}
        reviews.append(r)

    product = products_col.find_one({"_id": oid}, {"title": 1})
    return {
        "success": True,
        "message": "Reviews retrieved",
        "data": reviews,
        "product": {"_id": product_id, "title": product["title"]} if product else None
    }


# ─── GET /api/v1/products/:id ────────────────────────────────────────────────

@router.get("/{product_id}")
def get_product_by_id(product_id: str):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    product = products_col.find_one({"_id": oid})
    if not product:
        raise HTTPException(404, "Product not found")

    return {"success": True, "message": "Product retrieved", "data": _serialize(product)}


# ─── POST /api/v1/products/:id/reviews ───────────────────────────────────────

@router.post("/{product_id}/reviews", status_code=201)
def add_product_review(
    product_id: str,
    body: ReviewIn,
    current_user: dict = Depends(get_current_user)
):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    if not body.rating:
        raise HTTPException(400, "Rating is required")

    product = products_col.find_one({"_id": oid})
    if not product:
        raise HTTPException(404, "Product not found")

    user_id_str = current_user["_id"]
    user_oid = ObjectId(user_id_str)

    # Check if user already reviewed this product (embedded reviews)
    existing = next(
        (r for r in product.get("reviews", []) if str(r.get("user")) == user_id_str),
        None
    )
    if existing:
        raise HTTPException(400, "Product already reviewed")

    new_review = {
        "user": user_oid,
        "rating": int(body.rating),
        "comment": body.comment or "",
        "createdAt": datetime.now(timezone.utc)
    }

    all_reviews = product.get("reviews", []) + [new_review]
    avg_rating = sum(r["rating"] for r in all_reviews) / len(all_reviews)

    products_col.update_one(
        {"_id": oid},
        {
            "$push": {"reviews": new_review},
            "$set": {
                "numReviews": len(all_reviews),
                "rating": round(avg_rating, 2)
            }
        }
    )

    return {"success": True, "message": "Review submitted successfully"}


# ─── POST /api/v1/products (admin) ───────────────────────────────────────────

@router.post("", status_code=201)
def add_product(body: ProductIn, current_user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    doc = body.model_dump()
    doc["createdAt"] = now
    doc["updatedAt"] = now
    doc["rating"] = 0
    doc["numReviews"] = 0
    doc["reviews"] = []

    result = products_col.insert_one(doc)
    product = products_col.find_one({"_id": result.inserted_id})
    return {"success": True, "message": "Product added successfully", "data": _serialize(product)}


# ─── PUT /api/v1/products/:id (admin) ────────────────────────────────────────

@router.put("/{product_id}")
def update_product(product_id: str, body: ProductIn, current_user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updatedAt"] = datetime.now(timezone.utc)

    product = products_col.find_one_and_update(
        {"_id": oid}, {"$set": updates}, return_document=True
    )
    if not product:
        raise HTTPException(404, "Product not found")

    return {"success": True, "message": "Product updated successfully", "data": _serialize(product)}


# ─── DELETE /api/v1/products/:id (admin) ─────────────────────────────────────

@router.delete("/{product_id}")
def delete_product(product_id: str, current_user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    result = products_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(404, "Product not found")

    return {"success": True, "message": "Product deleted successfully"}
