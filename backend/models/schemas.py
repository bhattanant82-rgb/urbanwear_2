"""
models/schemas.py
Pydantic models for request body validation.
These mirror the Node.js Mongoose schema fields used in request handlers.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List


# ─── AUTH ────────────────────────────────────────────────────────────────────

class RegisterIn(BaseModel):
    name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str




# ─── PRODUCTS ────────────────────────────────────────────────────────────────

class ProductIn(BaseModel):
    title: str
    description: str
    price: float
    category: str          # 'men' | 'women' | 'kids'
    stock: int
    discount_percentage: Optional[float] = 0
    sizes: Optional[List[str]] = ['S', 'M', 'L', 'XL', 'XXL']
    images: Optional[List[str]] = []
    videoUrl: Optional[str] = ''
    color: Optional[List[str]] = []


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    discount_percentage: Optional[float] = None
    sizes: Optional[List[str]] = None


class ReviewIn(BaseModel):
    rating: int
    comment: Optional[str] = ''


# ─── ORDERS ──────────────────────────────────────────────────────────────────

class ShippingIn(BaseModel):
    name: str
    mobile: str
    email: Optional[str] = ''
    address: str
    city: Optional[str] = ''
    state: Optional[str] = ''
    pincode: Optional[str] = ''


class OrderProductIn(BaseModel):
    productId: str
    productName: Optional[str] = ''
    quantity: int
    size: Optional[str] = ''
    color: Optional[str] = ''


class PaymentInfoIn(BaseModel):
    status: Optional[str] = ''
    paymentId: Optional[str] = ''
    transactionTime: Optional[str] = ''


class OrderIn(BaseModel):
    shipping: Optional[ShippingIn] = None
    shippingAddress: Optional[ShippingIn] = None
    products: Optional[List[OrderProductIn]] = []
    paymentMethod: Optional[str] = 'COD'
    paymentInfo: Optional[PaymentInfoIn] = None


class CancelOrderIn(BaseModel):
    reason: Optional[str] = ''


# ─── REVIEWS ─────────────────────────────────────────────────────────────────

class StandaloneReviewIn(BaseModel):
    productId: str
    orderId: str
    rating: int
    reviewText: Optional[str] = ''


# ─── CART ────────────────────────────────────────────────────────────────────

class CartItemIn(BaseModel):
    productId: str
    quantity: Optional[int] = 1
    size: Optional[str] = ''
    color: Optional[str] = ''
    imageUrl: Optional[str] = ''


class CartUpdateIn(BaseModel):
    quantity: Optional[int] = None
    size: Optional[str] = None
    color: Optional[str] = None


# ─── ADMIN ───────────────────────────────────────────────────────────────────

class RoleUpdateIn(BaseModel):
    role: str   # 'user' | 'admin'


class OrderStatusIn(BaseModel):
    orderStatus: str


class CategoryIn(BaseModel):
    name: str
    slug: str
    order: Optional[int] = 0
    isActive: Optional[bool] = True
    bannerType: Optional[str] = 'image'
    bannerImage: Optional[str] = ''
    bannerVideo: Optional[str] = ''
    category_banner: Optional[str] = ''



# ─── ADDRESSES ───────────────────────────────────────────────────────────────

class AddressIn(BaseModel):
    name: str
    mobile: str
    email: Optional[str] = ''
    address: str
    city: Optional[str] = ''
    state: Optional[str] = ''
    pincode: Optional[str] = ''
    isDefault: Optional[bool] = False


# ─── HOME BANNER ─────────────────────────────────────────────────────────────

class HomeBannerIn(BaseModel):
    title: Optional[str] = ''
    subtitle: Optional[str] = ''
    button_text: Optional[str] = ''
    banner_image: Optional[str] = ''
    banner_video: Optional[str] = ''

class HomeBannerUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    button_text: Optional[str] = None
    banner_image: Optional[str] = None
    banner_video: Optional[str] = None

