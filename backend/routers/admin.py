"""
routers/admin.py
Admin routes — mirrors Node.js admin.routes.js + admin.controller.js
All routes require authentication + admin role.
"""
import io
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from bson import ObjectId

from database import users_col, products_col, orders_col, categories_col, reviews_col, home_banners_col
from models.schemas import RoleUpdateIn, ProductIn, ProductUpdate, OrderStatusIn, CategoryIn, HomeBannerIn
from routers.auth import get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


def deep_serialize(obj):
    """Recursively convert MongoDB objects (ObjectId, datetime) to JSON-safe types."""
    if isinstance(obj, dict):
        return {k: deep_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_serialize(v) for v in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


# ─── GET /api/v1/admin/dashboard ─────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard_stats(current_user: dict = Depends(require_admin)):
    total_users = users_col.count_documents({})
    total_products = products_col.count_documents({})
    total_orders = orders_col.count_documents({})
    orders = list(orders_col.find())

    total_sales = sum(o.get("totalAmount", o.get("total", 0)) for o in orders)
    low_stock_count = products_col.count_documents({"stock": {"$lte": 5}})

    # Category distribution
    category_stats = {"men": 0, "women": 0, "kids": 0}
    for p in products_col.find({}, {"category": 1}):
        cat = p.get("category", "")
        if cat in category_stats:
            category_stats[cat] += 1

    # Orders by status
    status_stats = {"Placed": 0, "Processing": 0, "Shipped": 0, "Delivered": 0, "Cancelled": 0}
    for o in orders:
        status = o.get("orderStatus", "Placed")
        if status in status_stats:
            status_stats[status] += 1
        elif status in ("CONFIRMED", "PAID"):
            status_stats["Placed"] += 1

    # Orders last 7 days
    today = datetime.now(timezone.utc)
    last7 = {}
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        last7[d.strftime("%Y-%m-%d")] = 0
    for o in orders:
        if o.get("createdAt"):
            ds = o["createdAt"].strftime("%Y-%m-%d") if hasattr(o["createdAt"], "strftime") else str(o["createdAt"])[:10]
            if ds in last7:
                last7[ds] += 1

    return {
        "success": True,
        "message": "Dashboard stats retrieved",
        "stats": {
            "totalUsers": total_users,
            "totalProducts": total_products,
            "totalOrders": total_orders,
            "totalSales": total_sales,
            "lowStockCount": low_stock_count,
            "categoryStats": category_stats,
            "statusStats": status_stats,
            "salesOrderTrend": last7
        }
    }


# ─── GET /api/v1/admin/users ─────────────────────────────────────────────────

@router.get("/users")
def get_all_users(current_user: dict = Depends(require_admin)):
    users = [deep_serialize({k: v for k, v in u.items() if k != "password"})
             for u in users_col.find()]
    return {"success": True, "message": "All users retrieved", "data": users}


# ─── PUT /api/v1/admin/users/:id/role ────────────────────────────────────────

@router.put("/users/{user_id}/role")
def change_user_role(user_id: str, body: RoleUpdateIn, current_user: dict = Depends(require_admin)):
    if body.role not in ("user", "admin"):
        raise HTTPException(400, "Invalid role")
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid user ID")

    user = users_col.find_one_and_update(
        {"_id": oid}, {"$set": {"role": body.role}}, return_document=True
    )
    if not user:
        raise HTTPException(404, "User not found")
    return {"success": True, "message": "Role changed",
            "data": deep_serialize({k: v for k, v in user.items() if k != "password"})}


# ─── DELETE /api/v1/admin/users/:id ──────────────────────────────────────────

@router.delete("/users/{user_id}")
def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "Invalid user ID")
    result = users_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(404, "User not found")
    return {"success": True, "message": "User deleted"}


# ─── GET /api/v1/admin/products ──────────────────────────────────────────────

@router.get("/products")
def get_all_products(current_user: dict = Depends(require_admin)):
    products = [deep_serialize(p) for p in products_col.find()]
    return {"success": True, "message": "All products retrieved", "data": products}


# ─── POST /api/v1/admin/products (with optional file uploads) ─────────────────

@router.post("/products", status_code=201)
async def admin_add_product(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    stock: int = Form(...),
    discount_percentage: float = Form(0),
    sizes: str = Form("S,M,L,XL,XXL"),
    videoUrl: str = Form(""),
    image: list[UploadFile] = File(None),
    bannerVideo: UploadFile = File(None),
    current_user: dict = Depends(require_admin)
):
    image_urls = []
    video_url = videoUrl

    from services.upload_service import upload_to_cloudinary
    if image:
        for f in image:
            if f and f.filename:
                file_bytes = await f.read()
                url = upload_to_cloudinary(file_bytes, f.filename, folder="urbanwear/products")
                image_urls.append(url)

    if bannerVideo and bannerVideo.filename:
        file_bytes = await bannerVideo.read()
        video_url = upload_to_cloudinary(file_bytes, bannerVideo.filename, folder="urbanwear/videos")

    now = datetime.now(timezone.utc)
    doc = {
        "title": title, "description": description,
        "price": price, "category": category, "stock": stock,
        "discount_percentage": discount_percentage,
        "sizes": [s.strip() for s in sizes.split(",") if s.strip()],
        "images": image_urls, "videoUrl": video_url,
        "color": [], "rating": 0, "numReviews": 0, "reviews": [],
        "createdAt": now, "updatedAt": now
    }
    result = products_col.insert_one(doc)
    product = products_col.find_one({"_id": result.inserted_id})
    return {"success": True, "message": "Product added successfully", "data": deep_serialize(product)}


# ─── PUT /api/v1/admin/products/:id ──────────────────────────────────────────

@router.put("/products/{product_id}")
async def admin_update_product(
    product_id: str,
    update: ProductUpdate,
    current_user: dict = Depends(require_admin)
):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    # Get only the fields that were provided (not None)
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if not update_data:
        # Graceful handling of empty requests
        return {
            "success": False,
            "message": "No fields provided to update"
        }

    update_data["updatedAt"] = datetime.now(timezone.utc)
    print("Admin update payload:", update_data, flush=True)
    
    product = products_col.find_one_and_update(
        {"_id": oid}, 
        {"$set": update_data}, 
        return_document=True
    )
    
    if not product:
        raise HTTPException(404, "Product not found")
        
    return {
        "success": True,
        "message": "Product updated successfully",
        "data": deep_serialize(product)
    }


# ─── PATCH /api/v1/admin/products/:id (JSON body — for PHP/JS clients) ────────

@router.patch("/products/{product_id}")
def admin_patch_product(product_id: str, body: dict, current_user: dict = Depends(require_admin)):
    """JSON-body product update. Accepts any subset of product fields."""
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")

    allowed = {"title", "description", "price", "category", "stock",
               "discount_percentage", "sizes", "videoUrl", "color", "images"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, "No valid fields provided for update")

    # Type coercion for safety
    if "price" in updates: updates["price"] = float(updates["price"])
    if "stock" in updates: updates["stock"] = int(updates["stock"])
    if "discount_percentage" in updates: updates["discount_percentage"] = float(updates["discount_percentage"])
    if "sizes" in updates and isinstance(updates["sizes"], str):
        updates["sizes"] = [s.strip() for s in updates["sizes"].split(",") if s.strip()]

    updates["updatedAt"] = datetime.now(timezone.utc)
    print(f"[ADMIN] Product PATCH {product_id}: fields={list(updates.keys())}", flush=True)

    result = products_col.update_one({"_id": oid}, {"$set": updates})
    print(f"[ADMIN] MongoDB modified_count: {result.modified_count}", flush=True)
    if result.matched_count == 0:
        raise HTTPException(404, "Product not found")

    product = products_col.find_one({"_id": oid})
    return {"success": True, "message": "Product updated successfully", "data": deep_serialize(product)}


# ─── DELETE /api/v1/admin/products/:id ───────────────────────────────────────

@router.delete("/products/{product_id}")
def admin_delete_product(product_id: str, current_user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "Invalid product ID")
    result = products_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(404, "Product not found")
    return {"success": True, "message": "Product deleted"}


# ─── GET /api/v1/admin/orders ────────────────────────────────────────────────

from bson import ObjectId
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

@router.get("/orders")
def get_all_orders(current_user: dict = Depends(require_admin)):
    cursor = orders_col.find().sort("createdAt", -1)
    orders = deep_serialize(list(cursor))
    return {
        "success": True,
        "message": "All orders retrieved",
        "orders": orders,
        "data": orders
    }


# ─── PUT /api/v1/admin/orders/:id/status ─────────────────────────────────────

@router.put("/orders/{order_id}/status")
def update_order_status(order_id: str, body: OrderStatusIn, current_user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(400, "Invalid order ID")

    order = orders_col.find_one({"_id": oid})
    if not order:
        raise HTTPException(404, "Order not found")

    new_status = body.orderStatus

    # Restore stock on cancellation
    if new_status == "Cancelled" and order.get("orderStatus") != "Cancelled":
        for item in order.get("products", order.get("items", [])):
            pid = item.get("productId") or item.get("id") or item.get("_id")
            qty = item.get("quantity", item.get("qty", 0))
            if pid and qty > 0:
                products_col.update_one({"_id": pid}, {"$inc": {"stock": qty}})

    update = {"orderStatus": new_status, "updatedAt": datetime.now(timezone.utc)}
    if new_status == "Delivered":
        update["paymentStatus"] = "Completed"
    if new_status == "Cancelled":
        update["paymentStatus"] = "Cancelled"

    order = orders_col.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    order["_id"] = str(order["_id"])
    order["userId"] = str(order.get("userId", ""))
    for item in order.get("products", []):
        if isinstance(item.get("productId"), ObjectId):
            item["productId"] = str(item["productId"])
    return {"success": True, "message": "Order status updated", "data": order}


# ─── CATEGORY MANAGEMENT ─────────────────────────────────────────────────────

@router.get("/categories")
def get_all_categories_admin(current_user: dict = Depends(require_admin)):
    return {"success": True, "message": "Categories retrieved",
            "data": [deep_serialize(c) for c in categories_col.find().sort([("order", 1), ("name", 1)])]}


@router.post("/categories", status_code=201)
async def admin_add_category(
    name: str = Form(...),
    slug: str = Form(...),
    order: int = Form(0),
    isActive: bool = Form(True),
    bannerType: str = Form("image"),
    bannerVideoFile: UploadFile = File(None),
    bannerImageFile: UploadFile = File(None),
    category_banner: UploadFile = File(None),
    bannerImageUrl: str = Form(""),
    bannerVideoUrl: str = Form(""),
    current_user: dict = Depends(require_admin)
):
    from services.upload_service import upload_to_cloudinary
    media_url = ""
    if bannerVideoFile and bannerVideoFile.filename:
        file_bytes = await bannerVideoFile.read()
        media_url = upload_to_cloudinary(file_bytes, bannerVideoFile.filename, folder="urbanwear/categories")
    elif bannerImageFile and bannerImageFile.filename:
        file_bytes = await bannerImageFile.read()
        media_url = upload_to_cloudinary(file_bytes, bannerImageFile.filename, folder="urbanwear/categories")

    banner_img = media_url or bannerImageUrl
    banner_vid = media_url if bannerType == "video" else bannerVideoUrl
    
    # Handle home page category banner (local storage)
    category_banner_path = ""
    if category_banner and category_banner.filename:
        import os
        import shutil
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(base_dir, "..", "frontend", "uploads", "categories")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
            
        file_ext = os.path.splitext(category_banner.filename)[1]
        file_name = f"cat_banner_{slug}{file_ext}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(category_banner.file, buffer)
        category_banner_path = f"uploads/categories/{file_name}"

    now = datetime.now(timezone.utc)

    # Upsert by slug
    existing = categories_col.find_one({"slug": slug})
    if existing:
        updates = {"name": name, "order": order, "isActive": isActive,
                   "bannerType": bannerType, "updatedAt": now}
        updates["bannerImage"] = banner_img or existing.get("bannerImage", "")
        if category_banner_path:
            updates["category_banner"] = category_banner_path
        if bannerType == "video":
            updates["bannerVideo"] = media_url or existing.get("bannerVideo", "")
        cat = categories_col.find_one_and_update({"_id": existing["_id"]}, {"$set": updates}, return_document=True)
        return {"success": True, "message": "Category updated (slug existed)", "data": deep_serialize(cat)}

    doc = {"name": name, "slug": slug, "order": order, "isActive": isActive,
           "bannerType": bannerType, "bannerImage": banner_img,
           "bannerVideo": banner_vid,
           "category_banner": category_banner_path,
           "createdAt": now, "updatedAt": now}
    result = categories_col.insert_one(doc)
    cat = categories_col.find_one({"_id": result.inserted_id})
    return {"success": True, "message": "Category added successfully", "data": deep_serialize(cat)}


@router.put("/categories/{category_id}")
async def admin_update_category(
    category_id: str,
    name: str = Form(None),
    slug: str = Form(None),
    order: int = Form(None),
    isActive: bool = Form(None),
    bannerType: str = Form(None),
    bannerVideoFile: UploadFile = File(None),
    bannerImageFile: UploadFile = File(None),
    bannerImageUrl: str = Form(None),
    bannerVideoUrl: str = Form(None),
    category_banner: UploadFile = File(None),
    current_user: dict = Depends(require_admin)
):
    try:
        oid = ObjectId(category_id)
    except Exception:
        raise HTTPException(400, "Invalid category ID")

    existing = categories_col.find_one({"_id": oid})
    if not existing:
        raise HTTPException(404, f"Category {category_id} not found")

    updates = {}
    if name is not None and name != existing.get("name"): updates["name"] = name
    if slug is not None and slug != existing.get("slug"): updates["slug"] = slug
    if order is not None: updates["order"] = order
    if isActive is not None: updates["isActive"] = isActive
    if bannerType is not None: updates["bannerType"] = bannerType

    from services.upload_service import upload_to_cloudinary
    if bannerVideoFile and bannerVideoFile.filename:
        file_bytes = await bannerVideoFile.read()
        media_url = upload_to_cloudinary(file_bytes, bannerVideoFile.filename, folder="urbanwear/categories")
        updates["bannerVideo"] = media_url
        updates["bannerImage"] = media_url
    elif bannerVideoUrl:
        updates["bannerVideo"] = bannerVideoUrl
        if bannerType == "video":
            updates["bannerImage"] = bannerVideoUrl

    if bannerImageFile and bannerImageFile.filename:
        file_bytes = await bannerImageFile.read()
        media_url = upload_to_cloudinary(file_bytes, bannerImageFile.filename, folder="urbanwear/categories")
        updates["bannerImage"] = media_url
    elif bannerImageUrl:
        updates["bannerImage"] = bannerImageUrl

    # Handle category_banner (local)
    if category_banner and category_banner.filename:
        import os
        import shutil
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(base_dir, "..", "frontend", "uploads", "categories")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
            
        use_slug = slug or existing.get("slug")
        file_ext = os.path.splitext(category_banner.filename)[1]
        file_name = f"cat_banner_{use_slug}{file_ext}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(category_banner.file, buffer)
        updates["category_banner"] = f"uploads/categories/{file_name}"

    updates["updatedAt"] = datetime.now(timezone.utc)
    cat = categories_col.find_one_and_update({"_id": oid}, {"$set": updates}, return_document=True)
    return {"success": True, "message": "Category updated successfully", "data": deep_serialize(cat)}


@router.patch("/categories/{category_id}")
def admin_patch_category(category_id: str, body: dict, current_user: dict = Depends(require_admin)):
    """JSON-body category update. Accepts any subset of category fields."""
    try:
        oid = ObjectId(category_id)
    except Exception:
        raise HTTPException(400, "Invalid category ID")

    allowed = {"name", "slug", "order", "isActive", "bannerType", "bannerImage", "bannerVideo", "category_banner"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, "No valid fields provided for update")

    # Type coercion for safety
    if "order" in updates: updates["order"] = int(updates["order"])
    if "isActive" in updates: 
        val = updates["isActive"]
        updates["isActive"] = bool(val) if not isinstance(val, str) else (val.lower() == 'true' or val == '1')

    updates["updatedAt"] = datetime.now(timezone.utc)
    print(f"[ADMIN] Category PATCH {category_id}: fields={list(updates.keys())}", flush=True)

    result = categories_col.update_one({"_id": oid}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(404, "Category not found")

    category = categories_col.find_one({"_id": oid})
    return {"success": True, "message": "Category updated successfully", "data": deep_serialize(category)}


@router.delete("/categories/{category_id}")
def admin_delete_category(category_id: str, current_user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(category_id)
    except Exception:
        raise HTTPException(400, "Invalid category ID")
    result = categories_col.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(404, "Category not found")
    return {"success": True, "message": "Category deleted successfully"}


# ─── ANALYTICS ───────────────────────────────────────────────────────────────

@router.get("/analytics/top-selling-products")
def get_top_selling_products(current_user: dict = Depends(require_admin)):
    orders = list(orders_col.find())
    counts: dict = {}
    for o in orders:
        items = o.get("products") or o.get("items", [])
        for item in items:
            pid = item.get("productId") or item.get("id") or item.get("_id")
            if pid:
                # Handle both ObjectId and string
                key = str(pid)
                counts[key] = counts.get(key, 0) + (item.get("quantity") or item.get("qty") or 1)

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    result = []
    for pid_str, qty in sorted_items:
        try:
            p = products_col.find_one({"_id": ObjectId(pid_str)})
            if p:
                result.append({"title": p["title"], "quantity": qty, "revenue": p["price"] * qty})
        except Exception:
            pass

    return {"success": True, "message": "Top selling products", "data": result}


@router.get("/analytics/sales")
def get_sales_analytics(current_user: dict = Depends(require_admin)):
    orders = list(orders_col.find())
    total_revenue = sum(o.get("totalAmount", o.get("total", 0)) for o in orders)
    return {"success": True, "message": "Sales analytics",
            "data": {"totalOrders": len(orders), "totalRevenue": total_revenue}}


@router.get("/analytics/visual")
def get_visual_analytics(current_user: dict = Depends(require_admin)):
    orders = list(orders_col.find())

    # Gather all productIds first, then do a SINGLE batch lookup
    pid_to_info: dict = {}
    product_sales: dict = {}
    for o in orders:
        items = o.get("products") or o.get("items", [])
        for item in items:
            qty = item.get("quantity") or item.get("qty") or 0
            pid = item.get("productId") or item.get("id")
            if pid:
                key = str(pid)
                product_sales[key] = product_sales.get(key, 0) + qty
                try:
                    pid_to_info[key] = ObjectId(pid) if not isinstance(pid, ObjectId) else pid
                except:
                    continue

    # Single batch product lookup instead of N queries
    category_demand = {"men": 0, "women": 0, "kids": 0}
    if pid_to_info:
        oids = list(pid_to_info.values())
        for p in products_col.find({"_id": {"$in": oids}}, {"category": 1, "title": 1, "price": 1}):
            key = str(p["_id"])
            cat = p.get("category", "")
            if cat in category_demand:
                category_demand[cat] += product_sales.get(key, 0)

    top_products = sorted(
        [{"title": str(k), "quantity": v} for k, v in product_sales.items()],
        key=lambda x: x["quantity"], reverse=True
    )[:10]

    # Orders over last 30 days
    today = datetime.now(timezone.utc)
    last30: dict = {}
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        last30[d.strftime("%Y-%m-%d")] = 0
    for o in orders:
        if o.get("createdAt"):
            ds = o["createdAt"].strftime("%Y-%m-%d") if hasattr(o["createdAt"], "strftime") else str(o["createdAt"])[:10]
            if ds in last30:
                last30[ds] += 1

    low_stock = [deep_serialize(p) for p in products_col.find({"stock": {"$lte": 10}}).sort("stock", 1).limit(10)]

    return {"success": True, "data": {
        "categoryDemand": category_demand,
        "topSellingProducts": top_products,
        "ordersOverTime": last30,
        "lowStockProducts": low_stock
    }}


@router.get("/analytics/advanced-dss")
def get_advanced_dss(current_user: dict = Depends(require_admin)):
    orders = list(orders_col.find())
    products = list(products_col.find())

    # Overstock logic
    product_sales_map: dict = {}
    for o in orders:
        items = o.get("products") or o.get("items", [])
        for item in items:
            pid = str(item.get("productId") or item.get("id") or item.get("_id") or "")
            if pid:
                product_sales_map[pid] = product_sales_map.get(pid, 0) + (item.get("quantity") or item.get("qty") or 1)

    overstock = [
        {"title": p["title"], "stock": p["stock"], "sales": product_sales_map.get(str(p["_id"]), 0)}
        for p in products
        if p["stock"] > 20 and product_sales_map.get(str(p["_id"]), 0) < 5
    ]

    # Review behavior
    behavior = {"mostReviewed": [], "lowRated": [], "mostRated": []}
    review_stats = list(reviews_col.aggregate([
        {"$group": {"_id": "$productId", "avgRating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]))
    for stat in review_stats:
        p = next((x for x in products if x["_id"] == stat["_id"]), None)
        if p:
            insight = {"title": p["title"], "avgRating": round(stat["avgRating"], 1), "count": stat["count"]}
            if len(behavior["mostReviewed"]) < 5: behavior["mostReviewed"].append(insight)
            if stat["avgRating"] < 3 and len(behavior["lowRated"]) < 5: behavior["lowRated"].append(insight)
            if stat["avgRating"] >= 4.5 and len(behavior["mostRated"]) < 5: behavior["mostRated"].append(insight)

    # Order summary
    cancelled = sum(1 for o in orders if o.get("orderStatus") == "Cancelled")
    recent = [{"id": str(o["_id"])[-6:], "status": o.get("orderStatus"), "amount": o.get("totalAmount", o.get("total", 0)), "date": o.get("createdAt")}
              for o in sorted(orders, key=lambda x: x.get("createdAt") or datetime.min, reverse=True)[:5]]

    return {"success": True, "data": {
        "overstockInsights": overstock,
        "customerBehavior": behavior,
        "orderSummary": {"totalOrders": len(orders), "cancelledOrders": cancelled, "recentOrders": recent}
    }}


@router.get("/analytics/reviews")
def get_analytics_reviews(
    limit: int = Query(10),
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


@router.get("/analytics/rating-insights")
def get_rating_insights(current_user: dict = Depends(require_admin)):
    pipeline = [
        {"$group": {"_id": "$productId", "avgRating": {"$avg": "$rating"}, "reviewCount": {"$sum": 1}}},
        {"$lookup": {"from": "products", "localField": "_id", "foreignField": "_id", "as": "product"}},
        {"$unwind": "$product"},
        {"$project": {
            "productId": "$product._id", "title": "$product.title",
            "category": "$product.category",
            "avgRating": {"$round": ["$avgRating", 1]},
            "reviewCount": 1
        }}
    ]
    stats = list(reviews_col.aggregate(pipeline))
    for s in stats:
        if "productId" in s:
            s["productId"] = str(s["productId"])

    top_rated = sorted([s for s in stats if s["avgRating"] >= 4],
                        key=lambda x: (-x["avgRating"], -x["reviewCount"]))[:10]
    low_rated = sorted([s for s in stats if s["avgRating"] < 3],
                        key=lambda x: x["avgRating"])[:10]

    return {"success": True, "data": {
        "topRated": top_rated,
        "lowRated": low_rated,
        "totalReviewedProducts": len(stats)
    }}


# ─── HOME BANNER MANAGEMENT ──────────────────────────────────────────────────

@router.get("/home-banner")
def get_home_banner(current_user: dict = Depends(require_admin)):
    banner = home_banners_col.find_one({}, sort=[("updated_at", -1)])
    if not banner:
        # Return default structure if none exists
        return {
            "success": True,
            "data": {
                "title": "Wear the Earth. Own the Street.",
                "subtitle": "Essentials 2026",
                "button_text": "Explore Collection",
                "button_link": "#drop",
                "button_enabled": True,
                "banner_image": "",
                "banner_video": ""
            }
        }
    return {"success": True, "data": deep_serialize(banner)}

@router.post("/home-banner")
async def update_home_banner(
    title: str = Form(None),
    subtitle: str = Form(None),
    button_text: str = Form(None),
    button_link: str = Form(None),
    button_enabled: bool = Form(None),
    banner_image: UploadFile = File(None),
    banner_video: UploadFile = File(None),
    current_user: dict = Depends(require_admin)
):
    import os
    import shutil
    
    # Target directory for banners (lives in frontend/uploads/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    upload_dir = os.path.join(base_dir, "..", "frontend", "uploads", "banners")
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)

    updates = {}
    if title is not None: updates["title"] = title
    if subtitle is not None: updates["subtitle"] = subtitle
    if button_text is not None: updates["button_text"] = button_text
    if button_link is not None: updates["button_link"] = button_link
    if button_enabled is not None: updates["button_enabled"] = button_enabled

    # Handle image upload
    if banner_image and banner_image.filename:
        file_ext = os.path.splitext(banner_image.filename)[1]
        file_name = f"banner_image{file_ext}"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(banner_image.file, buffer)
        updates["banner_image"] = f"uploads/banners/{file_name}"

    # Handle video upload
    if banner_video and banner_video.filename:
        file_ext = os.path.splitext(banner_video.filename)[1]
        # Check restrictions
        if file_ext.lower() not in [".mp4", ".webm"]:
             raise HTTPException(400, "Invalid video format. Only MP4 and WebM are allowed.")
        
        # Check size (20MB limit)
        # We can't easily check size before reading if it's a SpooledTemporaryFile
        # But we can check after reading or use a limit
        
        file_name = f"banner_video{file_ext}"
        file_path = os.path.join(upload_dir, file_name)
        
        # Read file to check size
        content = await banner_video.read()
        if len(content) > 20 * 1024 * 1024:
             raise HTTPException(400, "Video file too large. Maximum size is 20MB.")
             
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        updates["banner_video"] = f"uploads/banners/{file_name}"

    updates["updated_at"] = datetime.now(timezone.utc)

    # We only keep ONE home banner record
    result = home_banners_col.find_one_and_update(
        {}, 
        {"$set": updates}, 
        upsert=True, 
        return_document=True
    )
    
    return {"success": True, "message": "Home banner updated successfully", "data": deep_serialize(result)}

@router.delete("/home-banner/video")
def delete_banner_video(current_user: dict = Depends(require_admin)):
    banner = home_banners_col.find_one({})
    if banner and banner.get("banner_video"):
        # We don't necessarily delete the physical file for now to avoid complexity, 
        # but we clear the path in DB
        home_banners_col.update_one({}, {"$set": {"banner_video": ""}})
        return {"success": True, "message": "Banner video removed"}
    return {"success": False, "message": "No video found to delete"}
