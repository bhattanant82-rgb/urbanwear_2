"""
main.py — UrbanWear FastAPI Backend Entry Point

Start with:
    uvicorn main:app --reload --port 5000

API base: http://127.0.0.1:5000/api/v1/
Auto docs: http://127.0.0.1:5000/docs
"""
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime, date
import traceback
import sys
import logging

# --- Suppress [WinError 10054] Log Noise on Windows -----------------------------
# This error occurs when a browser abruptly closes a connection (common during
# video streaming/range requests). It is harmless but noisy.
if sys.platform == "win32":
    class WinErrorFilter(logging.Filter):
        def filter(self, record):
            # Suppress specific ConnectionResetError message from asyncio
            return "ConnectionResetError: [WinError 10054]" not in record.getMessage()

    logging.getLogger("asyncio").addFilter(WinErrorFilter())

# Load environment variables from .env FIRST (before importing routers/database)
load_dotenv()

# --- Custom JSON encoder to handle MongoDB ObjectId and datetime ---------------
class MongoJSONResponse(JSONResponse):
    """
    Drop-in replacement for JSONResponse that automatically converts:
      - ObjectId  → str
      - datetime  → ISO 8601 string
    This means every router can just return a plain Python dict and it
    will be serialized correctly — no manual .str() calls needed.
    """
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self._default_encoder
        ).encode("utf-8")

    @staticmethod
    def _default_encoder(obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return str(obj)


# Import routers after dotenv is loaded
from routers import auth, products, categories, orders, reviews, cart, admin, addresses, contact

# Create FastAPI app — use MongoJSONResponse as the default for all routes
app = FastAPI(
    title="UrbanWear API",
    description="FastAPI backend for UrbanWear e-commerce — replacing Node.js/Express",
    version="2.0.0",
    default_response_class=MongoJSONResponse,
    debug=True,
    redirect_slashes=True,
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardize validation errors (422) for the PHP frontend"""
    details = exc.errors()
    # Extract a user-friendly message from the first error
    msg = "Validation Error"
    if details:
        err = details[0]
        field = ".".join(str(p) for p in err.get("loc", []))
        msg = f"Invalid {field}: {err.get('msg')}"
    
    return MongoJSONResponse(
        status_code=422,
        content={"success": False, "message": msg, "details": details}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardize HTTP exceptions (404, 401, etc.) for the PHP frontend"""
    return MongoJSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for internal server errors (500)"""
    print("EXCEPTION:", exc, file=sys.stderr)
    traceback.print_exc()
    return MongoJSONResponse(
        status_code=500,
        content={
            "success": False, 
            "message": "Internal Server Error", 
            "error": str(exc),
            "trace": traceback.format_exc() if app.debug else None
        }
    )

# --- CORS --------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC FILES -------------------------------------------------------------
import os
# uploads/ now lives in frontend/ after restructuring
uploads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "uploads")
if not os.path.exists(uploads_path):
    os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")


# --- HEALTH CHECK -------------------------------------------------------------
@app.get("/health", tags=["health"])
def health_check():
    return {"success": True, "message": "Server is running"}

# --- PUBLIC ROUTES ------------------------------------------------------------
@app.get("/api/v1/home-banner", tags=["public"])
def get_public_home_banner():
    from database import home_banners_col
    banner = home_banners_col.find_one({}, sort=[("updated_at", -1)])
    if not banner:
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
    banner["_id"] = str(banner["_id"])
    return {"success": True, "data": banner}

# --- ROUTERS ------------------------------------------------------------------
API_V1 = "/api/v1"

app.include_router(auth.router,       prefix=API_V1)
app.include_router(products.router,   prefix=API_V1)
app.include_router(categories.router, prefix=API_V1)
app.include_router(orders.router,     prefix=API_V1)
app.include_router(reviews.router,    prefix=API_V1)
app.include_router(cart.router,       prefix=API_V1)
app.include_router(addresses.router,  prefix=API_V1)
app.include_router(admin.router,      prefix=API_V1)
app.include_router(contact.router,    prefix=API_V1)

# Also mount admin routes under /api/admin (matches Node.js server.js line 82)
app.include_router(admin.router,      prefix="/api")


# --- STARTUP LOG --------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    print("-" * 50)
    print("      URBANWEAR FASTAPI SERVER STARTED")
    print(f"  Server:  http://127.0.0.1:5000")
    print(f"  Docs:    http://127.0.0.1:5000/docs")
    print("  Backend: Python FastAPI + PyMongo")
    print("-" * 50)

