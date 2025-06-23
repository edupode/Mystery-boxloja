from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json

# Custom JSON encoder to handle ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import stripe
import hashlib
import secrets
from google.auth.transport import requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from passlib.context import CryptContext
import json
import resend
import re
from jinja2 import Template

# Define Stripe checkout models
class CheckoutSessionRequest(BaseModel):
    amount: float
    currency: str = "eur"
    success_url: str
    cancel_url: str
    metadata: Dict[str, str] = {}

class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str

class CheckoutStatusResponse(BaseModel):
    payment_status: str
    customer_email: Optional[str] = None
    amount_total: Optional[float] = None
    metadata: Dict[str, Any] = {}

# Stripe subscription models
class SubscriptionRequest(BaseModel):
    customer_id: Optional[str] = None
    customer_email: str
    price_id: str
    success_url: str
    cancel_url: str
    metadata: Dict[str, str] = {}

class SubscriptionResponse(BaseModel):
    session_id: str
    url: str
    customer_id: str

class SubscriptionStatusResponse(BaseModel):
    subscription_id: Optional[str] = None
    status: str
    current_period_start: Optional[int] = None
    current_period_end: Optional[int] = None
    customer_id: Optional[str] = None

class CustomerPortalRequest(BaseModel):
    customer_id: str
    return_url: str

class CustomerPortalResponse(BaseModel):
    url: str

# Stripe subscription implementation
class StripeSubscription:
    def __init__(self, api_key: str):
        self.api_key = api_key
        stripe.api_key = api_key

    async def create_subscription_checkout(self, request: SubscriptionRequest) -> SubscriptionResponse:
        try:
            # Create or retrieve customer
            if request.customer_id:
                customer = stripe.Customer.retrieve(request.customer_id)
            else:
                customer = stripe.Customer.create(
                    email=request.customer_email,
                    metadata={"source": "mystery_box_subscription"}
                )

            # Create subscription checkout session
            session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=["card"],
                line_items=[{
                    "price": request.price_id,
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                metadata=request.metadata
            )
            
            return SubscriptionResponse(
                session_id=session.id,
                url=session.url,
                customer_id=customer.id
            )
        except Exception as e:
            print(f"Error creating subscription checkout: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def get_subscription_status(self, session_id: str) -> SubscriptionStatusResponse:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.subscription:
                subscription = stripe.Subscription.retrieve(session.subscription)
                return SubscriptionStatusResponse(
                    subscription_id=subscription.id,
                    status=subscription.status,
                    current_period_start=subscription.current_period_start,
                    current_period_end=subscription.current_period_end,
                    customer_id=subscription.customer
                )
            else:
                return SubscriptionStatusResponse(
                    status="incomplete" if session.payment_status == "unpaid" else "processing"
                )
        except Exception as e:
            print(f"Error retrieving subscription status: {str(e)}")
            return SubscriptionStatusResponse(status="error")

    async def create_customer_portal(self, request: CustomerPortalRequest) -> CustomerPortalResponse:
        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=request.customer_id,
                return_url=request.return_url
            )
            
            return CustomerPortalResponse(url=portal_session.url)
        except Exception as e:
            print(f"Error creating customer portal: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

    async def list_customer_subscriptions(self, customer_id: str):
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status="all"
            )
            
            return {
                "subscriptions": [
                    {
                        "id": sub.id,
                        "status": sub.status,
                        "current_period_start": sub.current_period_start,
                        "current_period_end": sub.current_period_end,
                        "items": [
                            {
                                "price_id": item.price.id,
                                "product_name": stripe.Product.retrieve(item.price.product).name,
                                "quantity": item.quantity
                            } for item in sub.items.data
                        ]
                    } for sub in subscriptions.data
                ]
            }
        except Exception as e:
            print(f"Error listing customer subscriptions: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

# Stripe checkout implementation
class StripeCheckout:
    def __init__(self, api_key: str):
        self.api_key = api_key
        stripe.api_key = api_key

    async def create_checkout_session(self, request: CheckoutSessionRequest) -> CheckoutSessionResponse:
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": request.currency,
                        "product_data": {
                            "name": "Mystery Box Order",
                        },
                        "unit_amount": int(request.amount * 100),  # Convert to cents
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                metadata=request.metadata
            )
            
            return CheckoutSessionResponse(
                session_id=session.id,
                url=session.url
            )
        except Exception as e:
            # In a real implementation, we would handle errors more gracefully
            print(f"Error creating checkout session: {str(e)}")
            raise

    async def get_checkout_status(self, session_id: str) -> CheckoutStatusResponse:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            return CheckoutStatusResponse(
                payment_status=session.payment_status,
                customer_email=session.customer_details.email if hasattr(session, 'customer_details') else None,
                amount_total=session.amount_total / 100 if session.amount_total else None,
                metadata=session.metadata
            )
        except Exception as e:
            # In a real implementation, we would handle errors more gracefully
            print(f"Error retrieving checkout status: {str(e)}")
            return CheckoutStatusResponse(payment_status="error")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe setup
stripe_secret = os.environ['STRIPE_SECRET_KEY']
stripe_checkout = StripeCheckout(api_key=stripe_secret)
stripe_subscription = StripeSubscription(api_key=stripe_secret)

# Google OAuth setup
GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']

# Resend setup
resend.api_key = os.environ['RESEND_API_KEY']

# JWT setup
SECRET_KEY = os.environ.get('JWT_SECRET', 'mystery_box_super_secret_key_2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create the main app
app = FastAPI(title="Mystery Box Store API", version="2.0.0")
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint to verify API is running"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Admin email
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'eduardocorreia3344@gmail.com')

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    nif: Optional[str] = None
    birth_date: Optional[datetime] = None
    password_hash: Optional[str] = None
    google_id: Optional[str] = None
    facebook_id: Optional[str] = None
    is_admin: bool = False
    is_super_admin: bool = False
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleAuthRequest(BaseModel):
    token: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str
    price: float
    subscription_prices: Dict[str, float] = {
        "1_month": 0.0,
        "3_months": 0.0,
        "6_months": 0.0,
        "12_months": 0.0
    }
    image_url: str  # Primary image for backwards compatibility
    images: List[str] = []  # Additional images for gallery
    is_active: bool = True
    stock_quantity: int = 100
    featured: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    description: str
    category: str
    price: float
    subscription_prices: Optional[Dict[str, float]] = None
    image_url: str
    image_base64: Optional[str] = None  # For base64 image uploads
    images: Optional[List[str]] = []  # Additional images for gallery
    images_base64: Optional[List[str]] = []  # Additional base64 images
    stock_quantity: Optional[int] = 100
    featured: Optional[bool] = False

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    emoji: str
    color: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CategoryCreate(BaseModel):
    name: str
    description: str
    emoji: str
    color: str

class CouponCode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    description: str
    discount_type: str  # "percentage" or "fixed"
    discount_value: float
    min_order_value: Optional[float] = None
    max_uses: Optional[int] = None
    current_uses: int = 0
    valid_from: datetime
    valid_until: datetime
    applicable_categories: List[str] = []  # Empty means all categories
    applicable_products: List[str] = []   # Empty means all products
    is_active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CouponCreate(BaseModel):
    code: str
    description: str
    discount_type: str
    discount_value: float
    min_order_value: Optional[float] = None
    max_uses: Optional[int] = None
    valid_from: datetime
    valid_until: datetime
    applicable_categories: List[str] = []
    applicable_products: List[str] = []

class CartItem(BaseModel):
    product_id: str
    quantity: int = 1
    subscription_type: Optional[str] = None

class Cart(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str
    items: List[CartItem] = []
    coupon_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str
    items: List[CartItem]
    subtotal: float
    discount_amount: float = 0.0
    vat_amount: float
    shipping_cost: float
    total_amount: float
    coupon_code: Optional[str] = None
    shipping_address: str
    phone: str
    nif: Optional[str] = None
    payment_method: str
    payment_status: str = "pending"
    order_status: str = "pending"
    shipping_method: str = "standard"
    stripe_session_id: Optional[str] = None
    tracking_number: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CheckoutRequest(BaseModel):
    cart_id: str
    shipping_address: str
    phone: str
    nif: Optional[str] = None
    payment_method: str
    shipping_method: str = "standard"
    origin_url: str

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    payment_id: str
    amount: float
    currency: str = "eur"
    metadata: Dict = {}
    payment_status: str = "pending"
    user_id: Optional[str] = None
    order_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AdminUser(BaseModel):
    email: EmailStr
    name: str

class Promotion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    discount_type: str  # "percentage" or "fixed"
    discount_value: float
    applicable_categories: List[str] = []
    applicable_products: List[str] = []
    valid_from: datetime
    valid_until: datetime
    is_active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PromotionCreate(BaseModel):
    name: str
    description: str
    discount_type: str
    discount_value: float
    applicable_categories: List[str] = []
    applicable_products: List[str] = []
    valid_from: datetime
    valid_until: datetime

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    nif: Optional[str] = None
    birth_date: Optional[datetime] = None
    avatar_base64: Optional[str] = None

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chat_session_id: str
    sender_id: str
    sender_type: str  # "user" or "agent"
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False

class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    agent_id: Optional[str] = None
    status: str = "active"  # "active", "closed", "waiting"
    subject: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ChatMessageCreate(BaseModel):
    message: str
    chat_session_id: Optional[str] = None

class ChatSessionCreate(BaseModel):
    subject: Optional[str] = None

# Utility functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def validate_nif(nif: str) -> bool:
    """Validate Portuguese NIF (Número de Identificação Fiscal)"""
    if not nif:
        return False
    
    # Remove 'PT' prefix if present
    if nif.startswith('PT'):
        nif_numbers = nif[2:]
    else:
        nif_numbers = nif
    
    # Check if it has exactly 9 digits
    if not re.match(r'^\d{9}$', nif_numbers):
        return False
    
    # Calculate check digit
    digits = [int(d) for d in nif_numbers[:8]]
    check_sum = sum(digit * (9 - i) for i, digit in enumerate(digits))
    remainder = check_sum % 11
    
    if remainder < 2:
        check_digit = 0
    else:
        check_digit = 11 - remainder
    
    return int(nif_numbers[8]) == check_digit

async def send_email(to_email: str, subject: str, html_content: str, text_content: Optional[str] = None):
    """Send email using Resend"""
    try:
        params = {
            "from": "Mystery Box Store <noreply@mysteryboxes.pt>",
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        
        if text_content:
            params["text"] = text_content
        
        response = resend.Emails.send(params)
        return {"success": True, "message_id": response.get("id")}
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return {"success": False, "error": str(e)}

async def send_welcome_email(user_email: str, user_name: str):
    """Send welcome email to new users"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bem-vindo à Mystery Box Store!</title>
        <style>
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 40px 20px; }
            .header h1 { margin: 0; font-size: 28px; font-weight: bold; }
            .mystery-box { font-size: 60px; margin: 20px 0; animation: bounce 2s infinite; }
            @keyframes bounce { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-10px); } }
            .content { padding: 40px 20px; text-align: center; }
            .welcome-text { font-size: 18px; color: #333; margin-bottom: 30px; line-height: 1.6; }
            .features { display: flex; justify-content: space-around; margin: 30px 0; flex-wrap: wrap; }
            .feature { flex: 1; min-width: 150px; margin: 10px; text-align: center; }
            .feature-icon { font-size: 40px; margin-bottom: 10px; }
            .feature-text { font-size: 14px; color: #666; }
            .cta-button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 16px; display: inline-block; margin: 20px 0; transition: transform 0.3s ease; }
            .cta-button:hover { transform: translateY(-2px); }
            .footer { background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }
            .stars { color: #FFD700; font-size: 20px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="mystery-box">🎁</div>
                <h1>Bem-vindo à Mystery Box Store!</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Sua aventura misteriosa começa aqui</p>
            </div>
            
            <div class="content">
                <p class="welcome-text">
                    Olá <strong>{{ user_name }}</strong>! 👋<br>
                    Seja bem-vindo à nossa loja de mistérios e surpresas!
                </p>
                
                <div class="stars">⭐ ⭐ ⭐ ⭐ ⭐</div>
                
                <div class="features">
                    <div class="feature">
                        <div class="feature-icon">🎯</div>
                        <div class="feature-text">Produtos Exclusivos</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🚀</div>
                        <div class="feature-text">Entregas Rápidas</div>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">💎</div>
                        <div class="feature-text">Qualidade Premium</div>
                    </div>
                </div>
                
                <p style="color: #666; margin: 20px 0;">
                    Descubra produtos incríveis com descontos especiais e ofertas exclusivas para membros!
                </p>
                
                <a href="https://mystery-box-loja.vercel.app" class="cta-button">
                    🛍️ Explorar Produtos
                </a>
                
                <p style="color: #888; font-size: 14px; margin-top: 30px;">
                    Use o código <strong style="color: #667eea;">WELCOME10</strong> e ganhe 10% de desconto na sua primeira compra!
                </p>
            </div>
            
            <div class="footer">
                <p>Mystery Box Store - Sua loja de mistérios e surpresas</p>
                <p>© 2024 Mystery Box Store. Todos os direitos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    html_content = html_template.replace("{{ user_name }}", user_name)
    
    return await send_email(
        to_email=user_email,
        subject="🎁 Bem-vindo à Mystery Box Store!",
        html_content=html_content
    )

async def send_order_confirmation_email(user_email: str, order: Order, products: List[dict]):
    """Send order confirmation email"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Confirmação do Seu Pedido</title>
        <style>
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.1); }
            .header { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; text-align: center; padding: 40px 20px; }
            .header h1 { margin: 0; font-size: 28px; font-weight: bold; }
            .check-icon { font-size: 60px; margin: 20px 0; animation: pulse 2s infinite; }
            @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
            .content { padding: 40px 20px; }
            .order-info { background: #f8f9fa; padding: 20px; border-radius: 15px; margin: 20px 0; }
            .order-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
            .order-number { font-size: 18px; font-weight: bold; color: #333; }
            .order-status { background: #28a745; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; }
            .product-item { display: flex; align-items: center; padding: 15px 0; border-bottom: 1px solid #eee; }
            .product-item:last-child { border-bottom: none; }
            .product-info { flex: 1; margin-left: 15px; }
            .product-name { font-weight: bold; color: #333; }
            .product-price { color: #28a745; font-weight: bold; }
            .product-emoji { font-size: 40px; }
            .total-section { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 15px; margin: 20px 0; text-align: center; }
            .total-amount { font-size: 24px; font-weight: bold; }
            .shipping-info { background: #e3f2fd; padding: 20px; border-radius: 15px; margin: 20px 0; }
            .cta-button { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 16px; display: inline-block; margin: 20px auto; transition: transform 0.3s ease; text-align: center; }
            .cta-button:hover { transform: translateY(-2px); }
            .footer { background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="check-icon">✅</div>
                <h1>Pedido Confirmado!</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Obrigado pela sua compra</p>
            </div>
            
            <div class="content">
                <div class="order-info">
                    <div class="order-header">
                        <span class="order-number">Pedido #{{ order_id }}</span>
                        <span class="order-status">{{ order_status }}</span>
                    </div>
                    <p style="color: #666; margin: 0;">
                        📅 Realizado em: {{ order_date }}<br>
                        💳 Método de pagamento: {{ payment_method }}<br>
                        🚚 Método de entrega: {{ shipping_method }}
                    </p>
                </div>
                
                <h3 style="color: #333; margin: 30px 0 15px 0;">📦 Produtos Comprados:</h3>
                
                {{ products_list }}
                
                <div class="total-section">
                    <p style="margin: 0 0 10px 0; font-size: 16px;">Total do Pedido</p>
                    <div class="total-amount">€{{ total_amount }}</div>
                </div>
                
                <div class="shipping-info">
                    <h4 style="color: #1976d2; margin: 0 0 10px 0;">🚚 Informações de Entrega</h4>
                    <p style="color: #666; margin: 0;">
                        <strong>{{ customer_name }}</strong><br>
                        {{ customer_address }}<br>
                        {{ customer_postal_code }} {{ customer_city }}
                    </p>
                </div>
                
                <div style="text-align: center;">
                    <a href="https://mystery-box-loja.vercel.app/profile" class="cta-button">
                        📋 Acompanhar Pedido
                    </a>
                </div>
                
                <p style="color: #888; font-size: 14px; text-align: center; margin-top: 30px;">
                    Receberá um email com o código de rastreamento assim que o pedido for enviado.
                </p>
            </div>
            
            <div class="footer">
                <p>Mystery Box Store - Sua loja de mistérios e surpresas</p>
                <p>© 2024 Mystery Box Store. Todos os direitos reservados.</p>
                <p>Precisa de ajuda? Contacte-nos através do chat no website.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Build products list HTML
    products_html = ""
    for item in order.items:
        # Find product in the products list
        product = next((p for p in products if p["id"] == item.product_id), None)
        if product:
            price = item.subscription_type and product.get("subscription_prices", {}).get(item.subscription_type) or product.get("price", 0)
            total_price = price * item.quantity
            
            # Map categories to emojis
            category_emojis = {
                "mistery_box": "🎁",
                "geek": "🎮",
                "terror": "👻",
                "pets": "🐕",
                "lifestyle": "✨",
                "tech": "📱",
                "fashion": "👕",
                "home": "🏠"
            }
            emoji = category_emojis.get(product.get("category", ""), "📦")
            
            products_html += f"""
            <div class="product-item">
                <div class="product-emoji">{emoji}</div>
                <div class="product-info">
                    <div class="product-name">{product.get("name", "Produto")}</div>
                    <div style="color: #666; font-size: 14px;">{product.get("description", "")}</div>
                    <div style="margin-top: 5px;">
                        <span style="color: #666;">Quantidade: {item.quantity}</span>
                        <span class="product-price" style="float: right;">€{total_price:.2f}</span>
                    </div>
                </div>
            </div>
            """
    
    # Replace placeholders
    html_content = html_template.replace("{{ order_id }}", order.id[:8])
    html_content = html_content.replace("{{ order_status }}", order.order_status.title())
    html_content = html_content.replace("{{ order_date }}", order.created_at.strftime("%d/%m/%Y às %H:%M"))
    html_content = html_content.replace("{{ payment_method }}", order.payment_method.title())
    html_content = html_content.replace("{{ shipping_method }}", order.shipping_method.title())
    html_content = html_content.replace("{{ products_list }}", products_html)
    html_content = html_content.replace("{{ total_amount }}", f"{order.total_amount:.2f}")
    html_content = html_content.replace("{{ customer_name }}", order.customer_name)
    html_content = html_content.replace("{{ customer_address }}", order.customer_address)
    html_content = html_content.replace("{{ customer_postal_code }}", order.customer_postal_code)
    html_content = html_content.replace("{{ customer_city }}", order.customer_city)
    
    return await send_email(
        to_email=user_email,
        subject=f"✅ Confirmação de Pedido #{order.id[:8]}",
        html_content=html_content
    )

async def send_discount_email(user_email: str, user_name: str, coupon_code: str, discount_value: float, discount_type: str, expiry_date: str):
    """Send discount notification email"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Desconto Especial!</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #0f0f10; color: white; }
            .container { background: linear-gradient(135deg, #f59e0b, #d97706); padding: 40px; border-radius: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .content { background: rgba(0,0,0,0.3); padding: 30px; border-radius: 15px; }
            .coupon { background: linear-gradient(45deg, #fbbf24, #f59e0b); color: black; padding: 20px; border-radius: 15px; text-align: center; margin: 20px 0; border: 3px dashed #92400e; }
            .button { display: inline-block; background: linear-gradient(45deg, #8b5cf6, #6366f1); color: white; padding: 15px 30px; text-decoration: none; border-radius: 10px; font-weight: bold; margin: 20px 0; }
            .footer { text-align: center; margin-top: 30px; font-size: 14px; color: #ccc; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Desconto Especial Para Si!</h1>
                <div style="font-size: 48px;">💰 🎁</div>
            </div>
            <div class="content">
                <h2>Olá {{ user_name }}! 🌟</h2>
                <p>Temos uma surpresa especial para si! Aproveite este desconto exclusivo nas nossas mystery boxes.</p>
                
                <div class="coupon">
                    <h2 style="margin: 0; color: black;">{{ discount_text }}</h2>
                    <div style="font-size: 28px; font-weight: bold; margin: 15px 0; color: #92400e;">{{ coupon_code }}</div>
                    <p style="margin: 0; color: black;">Código promocional</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="https://mysteryboxes.pt/produtos" class="button">🛒 Usar Desconto</a>
                </div>
                
                <p><strong>Válido até:</strong> {{ expiry_date }}</p>
                <p>Não perca esta oportunidade de descobrir mistérios incríveis com desconto!</p>
            </div>
            <div class="footer">
                <p>Mystery Box Store - Descontos misteriosos! 🔮</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    discount_text = f"{discount_value}% OFF" if discount_type == "percentage" else f"€{discount_value} OFF"
    
    template = Template(html_template)
    html_content = template.render(
        user_name=user_name,
        discount_text=discount_text,
        coupon_code=coupon_code,
        expiry_date=expiry_date
    )
    
    return await send_email(
        to_email=user_email,
        subject=f"🎉 {discount_text} - Desconto Especial!",
        html_content=html_content
    )

async def send_birthday_email(user_email: str, user_name: str, coupon_code: str, discount_value: float):
    """Send birthday discount email"""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Feliz Aniversário!</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #0f0f10; color: white; }
            .container { background: linear-gradient(135deg, #ec4899, #be185d); padding: 40px; border-radius: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .content { background: rgba(0,0,0,0.3); padding: 30px; border-radius: 15px; }
            .coupon { background: linear-gradient(45deg, #fbbf24, #f59e0b); color: black; padding: 20px; border-radius: 15px; text-align: center; margin: 20px 0; border: 3px dashed #92400e; }
            .button { display: inline-block; background: linear-gradient(45deg, #8b5cf6, #6366f1); color: white; padding: 15px 30px; text-decoration: none; border-radius: 10px; font-weight: bold; margin: 20px 0; }
            .footer { text-align: center; margin-top: 30px; font-size: 14px; color: #ccc; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎂 Feliz Aniversário!</h1>
                <div style="font-size: 48px;">🎉 🎁 🎈</div>
            </div>
            <div class="content">
                <h2>Parabéns {{ user_name }}! 🥳</h2>
                <p>É o seu dia especial e nós temos um presente especial para si! Celebre com desconto nas nossas mystery boxes.</p>
                
                <div class="coupon">
                    <h2 style="margin: 0; color: black;">🎂 {{ discount_value }}% OFF 🎂</h2>
                    <div style="font-size: 28px; font-weight: bold; margin: 15px 0; color: #92400e;">{{ coupon_code }}</div>
                    <p style="margin: 0; color: black;">Desconto de Aniversário</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="https://mysteryboxes.pt/produtos" class="button">🎁 Celebrar com Compras</a>
                </div>
                
                <p>Este desconto especial é válido por 7 dias. Aproveite o seu aniversário para descobrir mistérios incríveis!</p>
                
                <p style="text-align: center; font-size: 18px;">🎊 Que tenha um aniversário cheio de surpresas! 🎊</p>
            </div>
            <div class="footer">
                <p>Mystery Box Store - Celebrando os seus momentos especiais! 💜</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    template = Template(html_template)
    html_content = template.render(
        user_name=user_name,
        discount_value=discount_value,
        coupon_code=coupon_code
    )
    
    return await send_email(
        to_email=user_email,
        subject=f"🎂 Feliz Aniversário {user_name}! Desconto especial para si!",
        html_content=html_content
    )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None

    user = await db.users.find_one({"email": email})
    if user:
        return User(**user)
    return None

async def get_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user or not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Sample data initialization
SAMPLE_PRODUCTS = [
    {
        "name": "Mystery Box Geek 🤓",
        "description": "Uma caixa recheada de produtos geek: camisetas temáticas, canecas de filmes/séries, gadgets tecnológicos e muito mais! Perfeito para os amantes da cultura pop.",
        "category": "geek",
        "price": 29.99,
        "subscription_prices": {
            "1_month": 29.99,
            "3_months": 26.99,
            "6_months": 24.99,
            "12_months": 22.99
        },
        "image_url": "https://images.unsplash.com/photo-1580234811497-9df7fd2f357e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwxfHxnYW1pbmd8ZW58MHx8fGJsdWV8MTc1MDU5NzA1OXww&ixlib=rb-4.1.0&q=85",
        "images": [
            "https://images.pexels.com/photos/12304526/pexels-photo-12304526.jpeg",
            "https://images.unsplash.com/photo-1679538642399-323a55485780?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzh8MHwxfHNlYXJjaHwyfHxnZWVrJTIwcHJvZHVjdHN8ZW58MHx8fHwxNzUwNjI0NTg1fDA&ixlib=rb-4.1.0&q=85",
            "https://images.pexels.com/photos/5556281/pexels-photo-5556281.jpeg"
        ],
        "featured": True
    },
    {
        "name": "Mystery Box Terror 👻",
        "description": "Para os amantes do terror: produtos de filmes clássicos, livros de horror, decorações assombradas e muito mais! Prepare-se para ser surpreendido.",
        "category": "terror",
        "price": 34.99,
        "subscription_prices": {
            "1_month": 34.99,
            "3_months": 31.99,
            "6_months": 29.99,
            "12_months": 27.99
        },
        "image_url": "https://images.unsplash.com/photo-1633555690973-b736f84f3c1b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwxfHxob3Jyb3J8ZW58MHx8fHwxNzUwNTk5MzA0fDA&ixlib=rb-4.1.0&q=85",
        "images": [
            "https://images.pexels.com/photos/6868409/pexels-photo-6868409.jpeg",
            "https://images.unsplash.com/photo-1725912634654-384cec97447f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHwzfHxob3Jyb3IlMjBjb2xsZWN0aWJsZXN8ZW58MHx8fHwxNzUwNjI0NTkxfDA&ixlib=rb-4.1.0&q=85",
            "https://images.unsplash.com/photo-1573376670774-4427757f7963?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzZ8MHwxfHNlYXJjaHwxfHxteXN0ZXJ5JTIwYm94fGVufDB8fHx8MTc1MDYyNDU3OHww&ixlib=rb-4.1.0&q=85"
        ],
        "featured": True
    },
    {
        "name": "Mystery Box Pets 🐾",
        "description": "Tudo para o seu melhor amigo: brinquedos, petiscos, acessórios e produtos de cuidado para cães e gatos! Mime o seu pet.",
        "category": "pets",
        "price": 24.99,
        "subscription_prices": {
            "1_month": 24.99,
            "3_months": 22.99,
            "6_months": 21.99,
            "12_months": 19.99
        },
        "image_url": "https://images.pexels.com/photos/1739093/pexels-photo-1739093.jpeg",
        "featured": True
    },
    {
        "name": "Mystery Box Harry Potter ⚡",
        "description": "Magia em cada caixa: varinhas, cachecóis das casas, canecas de Hogwarts e produtos oficiais do mundo bruxo! Accio mystery box!",
        "category": "harry_potter",
        "price": 39.99,
        "subscription_prices": {
            "1_month": 39.99,
            "3_months": 36.99,
            "6_months": 34.99,
            "12_months": 32.99
        },
        "image_url": "https://images.unsplash.com/photo-1647221597996-54f3d0f73809?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODF8MHwxfHNlYXJjaHwxfHxteXN0ZXJ5JTIwYm94fGVufDB8fHxibHVlfDE3NTA1OTkyNTR8MA&ixlib=rb-4.1.0&q=85"
    },
    {
        "name": "Mystery Box Marvel 🦸‍♂️",
        "description": "Heróis da Marvel: camisetas oficiais, Funko Pops, canecas dos Vingadores e produtos licenciados! Assemble your collection!",
        "category": "marvel",
        "price": 42.99,
        "subscription_prices": {
            "1_month": 42.99,
            "3_months": 39.99,
            "6_months": 37.99,
            "12_months": 35.99
        },
        "image_url": "https://images.unsplash.com/photo-1635404617144-8e262a622e41?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODF8MHwxfHNlYXJjaHwyfHxteXN0ZXJ5JTIwYm94fGVufDB8fHxibHVlfDE3NTA1OTkyNTR8MA&ixlib=rb-4.1.0&q=85"
    },
    {
        "name": "Mystery Box Livros 📚",
        "description": "Para os amantes da leitura: livros selecionados, marcadores artesanais, cadernos e acessórios literários! Alimente sua mente.",
        "category": "livros",
        "price": 27.99,
        "subscription_prices": {
            "1_month": 27.99,
            "3_months": 25.99,
            "6_months": 23.99,
            "12_months": 21.99
        },
        "image_url": "https://images.unsplash.com/photo-1604866830893-c13cafa515d5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwxfHxib29rc3xlbnwwfHx8fDE3NTA1OTkzMTZ8MA&ixlib=rb-4.1.0&q=85"
    },
    {
        "name": "Mystery Box Auto-cuidado 🧘‍♀️",
        "description": "Produtos de bem-estar e relaxamento: velas aromáticas, óleos essenciais, produtos spa, máscaras faciais e muito mais! Cuide de si mesmo.",
        "category": "auto_cuidado",
        "price": 32.99,
        "subscription_prices": {
            "1_month": 32.99,
            "3_months": 29.99,
            "6_months": 27.99,
            "12_months": 25.99
        },
        "image_url": "https://images.pexels.com/photos/289586/pexels-photo-289586.jpeg"
    },
    {
        "name": "Mystery Box Stitch 🌺",
        "description": "Produtos do adorável alienígena azul: pelúcias, acessórios, produtos oficiais Disney e muito mais! Ohana significa família.",
        "category": "stitch",
        "price": 36.99,
        "subscription_prices": {
            "1_month": 36.99,
            "3_months": 33.99,
            "6_months": 31.99,
            "12_months": 29.99
        },
        "image_url": "https://images.unsplash.com/photo-1504370164829-8c6ef0c41d06?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwyfHxnYW1pbmd8ZW58MHx8fGJsdWV8MTc1MDU5NzA1OXww&ixlib=rb-4.1.0&q=85"
    }
]

SAMPLE_CATEGORIES = [
    {"name": "Geek", "emoji": "🤓", "color": "#8B5CF6", "description": "Cultura pop, tecnologia e universo nerd"},
    {"name": "Terror", "emoji": "👻", "color": "#DC2626", "description": "Horror, suspense e filmes assombrados"},
    {"name": "Pets", "emoji": "🐾", "color": "#059669", "description": "Tudo para cães, gatos e outros pets"},
    {"name": "Harry Potter", "emoji": "⚡", "color": "#FBBF24", "description": "Mundo mágico de Hogwarts"},
    {"name": "Marvel", "emoji": "🦸‍♂️", "color": "#EF4444", "description": "Super-heróis e universo Marvel"},
    {"name": "Livros", "emoji": "📚", "color": "#6366F1", "description": "Literatura e acessórios de leitura"},
    {"name": "Auto-cuidado", "emoji": "🧘‍♀️", "color": "#EC4899", "description": "Spa, relaxamento e bem-estar"},
    {"name": "Stitch", "emoji": "👽", "color": "#06B6D4", "description": "Produtos do adorável alienígena"}
]

# Initialize sample data
@api_router.on_event("startup")
async def startup_event():
    # Check if admin user exists
    admin_user = await db.users.find_one({"email": ADMIN_EMAIL})
    if not admin_user:
        admin = User(
            email=ADMIN_EMAIL,
            name="Admin Principal",
            is_admin=True,
            is_super_admin=True,
            password_hash=hash_password("admin123")
        )
        await db.users.insert_one(admin.dict())
        print(f"Created super admin: {ADMIN_EMAIL}")

    # Check if products exist
    existing_products = await db.products.count_documents({})
    if existing_products == 0:
        for product_data in SAMPLE_PRODUCTS:
            product = Product(**product_data)
            await db.products.insert_one(product.dict())
        print("Created sample products")

    # Check if categories exist
    existing_categories = await db.categories.count_documents({})
    if existing_categories == 0:
        for cat_data in SAMPLE_CATEGORIES:
            category = Category(
                id=cat_data["name"].lower().replace(" ", "_").replace("-", "_"),
                **cat_data
            )
            await db.categories.insert_one(category.dict())
        print("Created sample categories")

# Auth endpoints
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email já está registrado")

    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password),
        is_admin=user_data.email == ADMIN_EMAIL,
        is_super_admin=user_data.email == ADMIN_EMAIL
    )
    await db.users.insert_one(user.dict())
    
    # Send welcome email
    await send_welcome_email(user.email, user.name)

    access_token = create_access_token(data={"sub": user.email})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user={"id": user.id, "name": user.name, "email": user.email, "is_admin": user.is_admin}
    )

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    access_token = create_access_token(data={"sub": user["email"]})
    return Token(
        access_token=access_token,
        token_type="bearer",
        user={"id": user["id"], "name": user["name"], "email": user["email"], "is_admin": user.get("is_admin", False)}
    )

@api_router.post("/auth/google", response_model=Token)
async def google_auth(auth_request: GoogleAuthRequest):
    try:
        idinfo = id_token.verify_oauth2_token(auth_request.token, requests.Request(), GOOGLE_CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        email = idinfo['email']
        name = idinfo['name']
        google_id = idinfo['sub']
        avatar_url = idinfo.get('picture', '')

        # Check if user exists
        user = await db.users.find_one({"email": email})
        if not user:
            # Create new user
            new_user = User(
                email=email,
                name=name,
                google_id=google_id,
                avatar_url=avatar_url,
                is_admin=email == ADMIN_EMAIL,
                is_super_admin=email == ADMIN_EMAIL
            )
            await db.users.insert_one(new_user.dict())
            user = new_user.dict()
            
            # Send welcome email for new Google users
            await send_welcome_email(email, name)
        else:
            # Update existing user with Google info
            await db.users.update_one(
                {"email": email},
                {"$set": {"google_id": google_id, "avatar_url": avatar_url}}
            )

        access_token = create_access_token(data={"sub": email})
        return Token(
            access_token=access_token,
            token_type="bearer",
            user={"id": user["id"], "name": user["name"], "email": user["email"], "is_admin": user.get("is_admin", False)}
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid Google token")

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "address": current_user.address,
        "city": current_user.city,
        "postal_code": current_user.postal_code,
        "nif": current_user.nif,
        "birth_date": current_user.birth_date,
        "is_admin": current_user.is_admin,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at
    }

@api_router.put("/auth/profile")
async def update_user_profile(profile_data: UserProfileUpdate, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    update_data = {}
    if profile_data.name is not None:
        update_data["name"] = profile_data.name
    if profile_data.phone is not None:
        update_data["phone"] = profile_data.phone
    if profile_data.address is not None:
        update_data["address"] = profile_data.address
    if profile_data.city is not None:
        update_data["city"] = profile_data.city
    if profile_data.postal_code is not None:
        update_data["postal_code"] = profile_data.postal_code
    if profile_data.nif is not None:
        if profile_data.nif and not validate_nif(profile_data.nif):
            raise HTTPException(status_code=400, detail="NIF inválido")
        update_data["nif"] = profile_data.nif
    if profile_data.birth_date is not None:
        update_data["birth_date"] = profile_data.birth_date
    if profile_data.avatar_base64 is not None:
        update_data["avatar_url"] = profile_data.avatar_base64

    if update_data:
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": update_data}
        )
    
    return {"message": "Perfil atualizado com sucesso"}

@api_router.get("/auth/orders")
async def get_user_orders(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get orders for the current user
    orders = await db.orders.find({"user_id": current_user.id}).sort("created_at", -1).to_list(1000)
    
    # Convert ObjectId to string and prepare order data
    result = []
    for order in orders:
        if "_id" in order:
            order["_id"] = str(order["_id"])
        
        # Get product details for each order item
        order_items_with_details = []
        for item in order.get("items", []):
            product = await db.products.find_one({"id": item["product_id"]})
            if product:
                price = item.get("subscription_type") and product["subscription_prices"].get(item["subscription_type"]) or product["price"]
                order_items_with_details.append({
                    "product_id": item["product_id"],
                    "product_name": product["name"],
                    "quantity": item["quantity"],
                    "subscription_type": item.get("subscription_type"),
                    "unit_price": price,
                    "total_price": price * item["quantity"]
                })
        
        order_data = {
            "id": order.get("id"),
            "created_at": order.get("created_at"),
            "items": order_items_with_details,
            "subtotal": order.get("subtotal", 0),
            "discount_amount": order.get("discount_amount", 0),
            "vat_amount": order.get("vat_amount", 0),
            "shipping_cost": order.get("shipping_cost", 0),
            "total_amount": order.get("total_amount", 0),
            "coupon_code": order.get("coupon_code"),
            "payment_status": order.get("payment_status", "pending"),
            "order_status": order.get("order_status", "pending"),
            "shipping_address": order.get("shipping_address"),
            "phone": order.get("phone"),
            "nif": order.get("nif"),
            "tracking_number": order.get("tracking_number")
        }
        result.append(order_data)
    
    return result

# Product endpoints
@api_router.get("/products")
async def get_products(category: Optional[str] = None, featured: Optional[bool] = None):
    query = {"is_active": True}
    if category:
        query["category"] = category
    if featured is not None:
        query["featured"] = featured

    products = await db.products.find(query).sort("created_at", -1).to_list(1000)
    # Convert ObjectId to string and prepare product data
    result = []
    for product in products:
        if "_id" in product:
            product["_id"] = str(product["_id"])
        
        # Map database fields to Product model fields
        product_data = {
            "id": product.get("id"),
            "name": product.get("name"),
            "description": product.get("description"),
            "category": product.get("category", ""),
            "price": product.get("price", 0.0),
            "subscription_prices": product.get("subscription_prices", {
                "1_month": 0.0,
                "3_months": 0.0,
                "6_months": 0.0,
                "12_months": 0.0
            }),
            "image_url": product.get("image_url", ""),
            "is_active": product.get("is_active", True),
            "stock_quantity": product.get("stock_quantity", 100),
            "featured": product.get("featured", False),
            "created_at": product.get("created_at", datetime.utcnow())
        }
        result.append(product_data)
    
    return result

@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Convert ObjectId to string
    if "_id" in product:
        product["_id"] = str(product["_id"])
    
    # Map database fields to Product model fields
    product_data = {
        "id": product.get("id"),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category_id", ""),  # Use category_id as category
        "price": product.get("price", 0.0),
        "subscription_prices": product.get("subscription_prices", {
            "1_month": 0.0,
            "3_months": 0.0,
            "6_months": 0.0,
            "12_months": 0.0
        }),
        "image_url": product.get("images", [""])[0] if product.get("images") else "",
        "is_active": product.get("is_active", True),
        "stock_quantity": product.get("stock", 100),
        "featured": product.get("is_featured", False),
        "created_at": product.get("created_at", datetime.utcnow())
    }
    
    return product_data

@api_router.get("/categories")
async def get_categories():
    categories = await db.categories.find({"is_active": True}).to_list(1000)
    # Convert ObjectId to string
    for category in categories:
        if "_id" in category:
            category["_id"] = str(category["_id"])
    return categories

# Coupon endpoints
@api_router.get("/coupons/validate/{code}")
async def validate_coupon(code: str):
    coupon = await db.coupons.find_one({"code": code.upper(), "is_active": True})
    if not coupon:
        raise HTTPException(status_code=404, detail="Cupão não encontrado")
    
    coupon = CouponCode(**coupon)
    now = datetime.utcnow()
    
    if now < coupon.valid_from or now > coupon.valid_until:
        raise HTTPException(status_code=400, detail="Cupão expirado")
    
    if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
        raise HTTPException(status_code=400, detail="Cupão esgotado")
    
    return coupon

@api_router.post("/cart/{session_id}/apply-coupon")
async def apply_coupon_to_cart(session_id: str, coupon_code: str):
    # Validate coupon
    coupon = await validate_coupon(coupon_code)
    
    # Update cart with coupon
    await db.carts.update_one(
        {"session_id": session_id},
        {"$set": {"coupon_code": coupon_code.upper(), "updated_at": datetime.utcnow()}}
    )
    
    cart = await db.carts.find_one({"session_id": session_id})
    if not cart:
        # Create a new cart if it doesn't exist
        new_cart = Cart(session_id=session_id, coupon_code=coupon_code.upper())
        await db.carts.insert_one(new_cart.dict())
        return new_cart
    
    # Convert ObjectId to string
    if "_id" in cart:
        cart["_id"] = str(cart["_id"])
    
    return Cart(**cart)

@api_router.delete("/cart/{session_id}/remove-coupon")
async def remove_coupon_from_cart(session_id: str):
    await db.carts.update_one(
        {"session_id": session_id},
        {"$unset": {"coupon_code": ""}, "$set": {"updated_at": datetime.utcnow()}}
    )
    
    cart = await db.carts.find_one({"session_id": session_id})
    if not cart:
        # Create a new cart if it doesn't exist
        new_cart = Cart(session_id=session_id)
        await db.carts.insert_one(new_cart.dict())
        return new_cart
    
    # Convert ObjectId to string
    if "_id" in cart:
        cart["_id"] = str(cart["_id"])
    
    return Cart(**cart)

# Cart endpoints
@api_router.get("/cart/{session_id}")
async def get_cart(session_id: str):
    cart = await db.carts.find_one({"session_id": session_id})
    if not cart:
        new_cart = Cart(session_id=session_id)
        await db.carts.insert_one(new_cart.dict())
        return new_cart
    # Convert ObjectId to string
    if "_id" in cart:
        cart["_id"] = str(cart["_id"])
    return Cart(**cart)

@api_router.post("/cart/{session_id}/add")
async def add_to_cart(session_id: str, item: CartItem):
    cart = await db.carts.find_one({"session_id": session_id})
    if not cart:
        cart = Cart(session_id=session_id)
    else:
        cart = Cart(**cart)

    # Check if item already exists
    existing_item = None
    for i, cart_item in enumerate(cart.items):
        if (cart_item.product_id == item.product_id and
            cart_item.subscription_type == item.subscription_type):
            existing_item = i
            break

    if existing_item is not None:
        cart.items[existing_item].quantity += item.quantity
    else:
        cart.items.append(item)

    cart.updated_at = datetime.utcnow()
    await db.carts.replace_one({"session_id": session_id}, cart.dict(), upsert=True)
    return cart

@api_router.delete("/cart/{session_id}/remove/{product_id}")
async def remove_from_cart(session_id: str, product_id: str, subscription_type: Optional[str] = None):
    cart = await db.carts.find_one({"session_id": session_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")

    cart = Cart(**cart)
    cart.items = [item for item in cart.items
                 if not (item.product_id == product_id and item.subscription_type == subscription_type)]

    cart.updated_at = datetime.utcnow()
    await db.carts.replace_one({"session_id": session_id}, cart.dict())
    return cart

# Shipping methods
@api_router.get("/shipping-methods")
async def get_shipping_methods():
    return [
        {"id": "standard", "name": "Envio Standard (2-3 dias)", "price": 3.99},
        {"id": "express", "name": "Envio Expresso (24h)", "price": 7.99},
        {"id": "free", "name": "Envio Grátis (5-7 dias)", "price": 0.0, "min_order": 50.0}
    ]

# Checkout and payment
@api_router.post("/checkout")
async def create_checkout(checkout_data: CheckoutRequest):
    cart = await db.carts.find_one({"session_id": checkout_data.cart_id})
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Carrinho vazio")

    cart = Cart(**cart)
    
    # Validate NIF if provided
    if checkout_data.nif and not validate_nif(checkout_data.nif):
        raise HTTPException(status_code=400, detail="NIF inválido. Deve ter 9 dígitos válidos, com ou sem prefixo 'PT'.")

    # Calculate subtotal
    subtotal = 0.0
    products = []
    for item in cart.items:
        product = await db.products.find_one({"id": item.product_id})
        if not product:
            continue
        products.append(product)

        # Handle subscription prices if they exist
        price = product.get("price", 0.0)
        if item.subscription_type and "subscription_prices" in product:
            price = product["subscription_prices"].get(item.subscription_type, price)

        subtotal += price * item.quantity

    # Apply coupon discount
    discount_amount = 0.0
    if cart.coupon_code:
        try:
            coupon = await validate_coupon(cart.coupon_code)
            
            # Check if coupon applies to cart items
            applies = False
            if not coupon.applicable_categories and not coupon.applicable_products:
                applies = True  # Applies to all
            else:
                for item in cart.items:
                    product = next((p for p in products if p["id"] == item.product_id), None)
                    if product:
                        if (product["category"] in coupon.applicable_categories or
                            product["id"] in coupon.applicable_products):
                            applies = True
                            break
            
            if applies and (not coupon.min_order_value or subtotal >= coupon.min_order_value):
                if coupon.discount_type == "percentage":
                    discount_amount = subtotal * (coupon.discount_value / 100)
                else:
                    discount_amount = min(coupon.discount_value, subtotal)
        except:
            pass  # Invalid coupon, ignore discount

    # Calculate shipping
    shipping_methods = await get_shipping_methods()
    shipping_method = next((sm for sm in shipping_methods if sm["id"] == checkout_data.shipping_method), shipping_methods[0])
    shipping_cost = shipping_method["price"]

    # Apply free shipping if applicable
    if shipping_method.get("min_order") and (subtotal - discount_amount) >= shipping_method["min_order"]:
        shipping_cost = 0.0

    # Add VAT (23%)
    vat_amount = (subtotal - discount_amount) * 0.23
    total_amount = subtotal - discount_amount + vat_amount + shipping_cost

    # Create order
    order = Order(
        session_id=cart.session_id,
        items=cart.items,
        subtotal=subtotal,
        discount_amount=discount_amount,
        vat_amount=vat_amount,
        shipping_cost=shipping_cost,
        total_amount=total_amount,
        coupon_code=cart.coupon_code,
        shipping_address=checkout_data.shipping_address,
        phone=checkout_data.phone,
        nif=checkout_data.nif,
        payment_method=checkout_data.payment_method,
        shipping_method=checkout_data.shipping_method
    )

    if checkout_data.payment_method == "card":
        # Create Stripe checkout session
        success_url = f"{checkout_data.origin_url}/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{checkout_data.origin_url}/cart"

        checkout_request = CheckoutSessionRequest(
            amount=total_amount,
            currency="eur",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "order_id": order.id,
                "session_id": cart.session_id
            }
        )

        session = await stripe_checkout.create_checkout_session(checkout_request)
        order.stripe_session_id = session.session_id

        # Create payment transaction
        payment_transaction = PaymentTransaction(
            session_id=session.session_id,
            payment_id=order.id,
            amount=total_amount,
            currency="eur",
            metadata={"order_id": order.id},
            order_id=order.id
        )
        await db.payment_transactions.insert_one(payment_transaction.dict())

        await db.orders.insert_one(order.dict())
        
        # Update coupon usage if applicable
        if cart.coupon_code:
            await db.coupons.update_one(
                {"code": cart.coupon_code},
                {"$inc": {"current_uses": 1}}
            )
        
        # Clear the cart after successful order creation
        await db.carts.update_one(
            {"session_id": cart.session_id},
            {"$set": {"items": [], "coupon_code": None, "updated_at": datetime.utcnow()}}
        )
        
        return {"checkout_url": session.url, "order_id": order.id}

    else:
        # For other payment methods
        order.payment_status = "pending"
        await db.orders.insert_one(order.dict())
        
        # Update coupon usage if applicable
        if cart.coupon_code:
            await db.coupons.update_one(
                {"code": cart.coupon_code},
                {"$inc": {"current_uses": 1}}
            )
        
        # Clear the cart after successful order creation
        await db.carts.update_one(
            {"session_id": cart.session_id},
            {"$set": {"items": [], "coupon_code": None, "updated_at": datetime.utcnow()}}
        )
        
        return {"order_id": order.id, "message": "Pedido criado com sucesso"}

@api_router.get("/payments/checkout/status/{session_id}")
async def get_payment_status(session_id: str):
    status = await stripe_checkout.get_checkout_status(session_id)

    payment_transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if payment_transaction:
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": status.payment_status}}
        )

        if status.payment_status == "paid" and payment_transaction.get("order_id"):
            order = await db.orders.find_one({"id": payment_transaction["order_id"]})
            if order:
                await db.orders.update_one(
                    {"id": payment_transaction["order_id"]},
                    {"$set": {"payment_status": "paid", "order_status": "confirmed", "updated_at": datetime.utcnow()}}
                )
                
                # Clear the cart after successful payment
                if order.get("session_id"):
                    await db.carts.update_one(
                        {"session_id": order["session_id"]},
                        {"$set": {"items": [], "coupon_code": None, "updated_at": datetime.utcnow()}}
                    )
                
                # Send order confirmation email
                user = await db.users.find_one({"id": order.get("user_id")})
                if user:
                    products = []
                    for item in order["items"]:
                        product = await db.products.find_one({"id": item["product_id"]})
                        if product:
                            products.append(product)
                    
                    await send_order_confirmation_email(user["email"], Order(**order), products)

    return status

# Subscription endpoints
@api_router.post("/subscriptions/create")
async def create_subscription_checkout(request: SubscriptionRequest):
    """Create a subscription checkout session"""
    try:
        result = await stripe_subscription.create_subscription_checkout(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/subscriptions/status/{session_id}")
async def get_subscription_status(session_id: str):
    """Get subscription status from checkout session"""
    try:
        status = await stripe_subscription.get_subscription_status(session_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/subscriptions/customer-portal")
async def create_customer_portal(request: CustomerPortalRequest):
    """Create customer portal session for subscription management"""
    try:
        result = await stripe_subscription.create_customer_portal(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/subscriptions/customer/{customer_id}")
async def list_customer_subscriptions(customer_id: str):
    """List all subscriptions for a customer"""
    try:
        result = await stripe_subscription.list_customer_subscriptions(customer_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/subscriptions/webhook")
async def handle_subscription_webhook(request: Request):
    """Handle Stripe subscription webhooks"""
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # In production, you should verify the webhook signature
        # event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        
        # For now, just parse the payload directly
        event = json.loads(payload)
        
        if event['type'] == 'customer.subscription.created':
            subscription = event['data']['object']
            # Handle subscription created
            print(f"Subscription created: {subscription['id']}")
            
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            # Handle subscription updated
            print(f"Subscription updated: {subscription['id']}")
            
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            # Handle subscription cancelled
            print(f"Subscription cancelled: {subscription['id']}")
            
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            # Handle successful payment
            print(f"Payment succeeded for subscription: {invoice['subscription']}")
            
        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            # Handle failed payment
            print(f"Payment failed for subscription: {invoice['subscription']}")
        
        return {"status": "success"}
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Admin endpoints
@api_router.get("/admin/dashboard")
async def admin_dashboard(admin_user: User = Depends(get_admin_user)):
    total_orders = await db.orders.count_documents({})
    total_users = await db.users.count_documents({})
    total_products = await db.products.count_documents({"is_active": True})

    # Calculate total revenue (only paid orders)
    paid_orders = await db.orders.find({"payment_status": "paid"}).to_list(1000)
    total_revenue = sum(order.get("total_amount", 0) for order in paid_orders)

    # Get recent orders
    recent_orders = await db.orders.find().sort("created_at", -1).limit(10).to_list(10)
    # Convert ObjectId to string
    for order in recent_orders:
        if "_id" in order:
            order["_id"] = str(order["_id"])

    return {
        "stats": {
            "total_orders": total_orders,
            "total_users": total_users,
            "total_products": total_products,
            "total_revenue": total_revenue
        },
        "recent_orders": recent_orders
    }

@api_router.get("/admin/orders")
async def get_all_orders(admin_user: User = Depends(get_admin_user)):
    orders = await db.orders.find().sort("created_at", -1).to_list(1000)
    
    # Convert ObjectId to string
    for order in orders:
        if "_id" in order:
            order["_id"] = str(order["_id"])
    
    # Separate orders by status and priority
    # Top priority: processing, pending, confirmed
    # Bottom priority: shipped
    # Hidden: cancelled, delivered
    
    top_priority_orders = []
    bottom_priority_orders = []
    
    for order in orders:
        status = order.get("order_status", "pending")
        
        # Skip cancelled and delivered orders (hide them)
        if status in ["cancelled", "delivered"]:
            continue
        
        # Top priority orders (new and processing)
        if status in ["pending", "processing", "confirmed"]:
            top_priority_orders.append(order)
        # Bottom priority orders (shipped)
        elif status == "shipped":
            bottom_priority_orders.append(order)
        else:
            # Any other status goes to top by default
            top_priority_orders.append(order)
    
    # Combine: top priority first, then bottom priority
    organized_orders = top_priority_orders + bottom_priority_orders
    
    return organized_orders

@api_router.put("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, status: str, admin_user: User = Depends(get_admin_user)):
    # Validate status
    valid_statuses = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Status inválido")
    
    # Update order status
    result = await db.orders.update_one(
        {"id": order_id},
        {"$set": {"order_status": status, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    return {"message": "Status atualizado com sucesso", "status": status}

@api_router.get("/admin/users")
async def get_all_users(admin_user: User = Depends(get_admin_user)):
    users = await db.users.find().sort("created_at", -1).to_list(1000)
    # Convert ObjectId to string and prepare user data
    user_list = []
    for u in users:
        if "_id" in u:
            u["_id"] = str(u["_id"])
        user_list.append({
            "id": u["id"], 
            "name": u["name"], 
            "email": u["email"], 
            "is_admin": u.get("is_admin", False), 
            "created_at": u["created_at"]
        })
    return user_list

@api_router.post("/admin/users/make-admin")
async def make_user_admin(admin_data: AdminUser, admin_user: User = Depends(get_admin_user)):
    if not admin_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")

    user = await db.users.find_one({"email": admin_data.email})
    if not user:
        # Create new admin user
        new_admin = User(
            email=admin_data.email,
            name=admin_data.name,
            is_admin=True,
            password_hash=hash_password("admin123")  # Default password
        )
        await db.users.insert_one(new_admin.dict())
        return {"message": f"Novo admin criado: {admin_data.email} (senha: admin123)"}
    else:
        # Make existing user admin
        await db.users.update_one(
            {"email": admin_data.email},
            {"$set": {"is_admin": True}}
        )
        return {"message": f"Usuário {admin_data.email} agora é admin"}

@api_router.delete("/admin/users/{user_id}/remove-admin")
async def remove_admin(user_id: str, admin_user: User = Depends(get_admin_user)):
    if not admin_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")

    # Cannot remove super admin
    user = await db.users.find_one({"id": user_id})
    if user and user.get("is_super_admin"):
        raise HTTPException(status_code=400, detail="Cannot remove super admin")

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_admin": False}}
    )
    return {"message": "Admin removido"}

# New admin user management endpoints
@api_router.put("/admin/users/{user_id}/password")
async def change_user_password(user_id: str, request: dict, admin_user: User = Depends(get_admin_user)):
    """Admin endpoint to change any user's password"""
    if not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    new_password = request.get("new_password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter pelo menos 6 caracteres")
    
    # Find user
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Update password
    hashed_password = hash_password(new_password)
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": hashed_password, "updated_at": datetime.utcnow()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {"message": f"Senha do usuário alterada com sucesso"}

@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin_user: User = Depends(get_admin_user)):
    """Admin endpoint to delete a user"""
    if not admin_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Find user to check if it's super admin
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Cannot delete super admin
    if user.get("is_super_admin"):
        raise HTTPException(status_code=400, detail="Não é possível deletar super admin")
    
    # Cannot delete yourself
    if user["email"] == admin_user.email:
        raise HTTPException(status_code=400, detail="Não é possível deletar sua própria conta")
    
    # Delete user
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {"message": f"Usuário {user['name']} ({user['email']}) deletado com sucesso"}

@api_router.post("/admin/users/bulk-make-admin")
async def bulk_make_admin(request: dict, admin_user: User = Depends(get_admin_user)):
    """Admin endpoint to make multiple users admin at once"""
    if not admin_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    user_ids = request.get("user_ids", [])
    if not user_ids or not isinstance(user_ids, list):
        raise HTTPException(status_code=400, detail="Lista de IDs de usuários é obrigatória")
    
    # Update multiple users to admin
    result = await db.users.update_many(
        {"id": {"$in": user_ids}},
        {"$set": {"is_admin": True, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": f"{result.modified_count} usuários promovidos a admin com sucesso"}

# Coupon management endpoints
@api_router.get("/admin/coupons")
async def get_all_coupons(admin_user: User = Depends(get_admin_user)):
    coupons = await db.coupons.find().sort("created_at", -1).to_list(1000)
    # Convert ObjectId to string
    for coupon in coupons:
        if "_id" in coupon:
            coupon["_id"] = str(coupon["_id"])
    return coupons

@api_router.post("/admin/coupons")
async def create_coupon(coupon_data: CouponCreate, admin_user: User = Depends(get_admin_user)):
    # Check if coupon code already exists
    existing = await db.coupons.find_one({"code": coupon_data.code.upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Código de cupão já existe")
    
    coupon_dict = coupon_data.dict()
    coupon_dict["code"] = coupon_data.code.upper()
    coupon_dict["created_by"] = admin_user.id
    
    coupon = CouponCode(**coupon_dict)
    await db.coupons.insert_one(coupon.dict())
    return coupon

@api_router.put("/admin/coupons/{coupon_id}")
async def update_coupon(coupon_id: str, coupon_data: CouponCreate, admin_user: User = Depends(get_admin_user)):
    await db.coupons.update_one(
        {"id": coupon_id},
        {"$set": coupon_data.dict()}
    )
    return {"message": "Cupão atualizado"}

@api_router.delete("/admin/coupons/{coupon_id}")
async def delete_coupon(coupon_id: str, admin_user: User = Depends(get_admin_user)):
    await db.coupons.update_one(
        {"id": coupon_id},
        {"$set": {"is_active": False}}
    )
    return {"message": "Cupão desativado"}

# Promotion management endpoints
@api_router.get("/admin/promotions")
async def get_all_promotions(admin_user: User = Depends(get_admin_user)):
    promotions = await db.promotions.find().sort("created_at", -1).to_list(1000)
    # Convert ObjectId to string
    for promotion in promotions:
        if "_id" in promotion:
            promotion["_id"] = str(promotion["_id"])
    return promotions

@api_router.post("/admin/promotions")
async def create_promotion(promotion_data: PromotionCreate, admin_user: User = Depends(get_admin_user)):
    promotion = Promotion(
        **promotion_data.dict(),
        created_by=admin_user.id
    )
    await db.promotions.insert_one(promotion.dict())
    return promotion

@api_router.put("/admin/promotions/{promotion_id}")
async def update_promotion(promotion_id: str, promotion_data: PromotionCreate, admin_user: User = Depends(get_admin_user)):
    await db.promotions.update_one(
        {"id": promotion_id},
        {"$set": promotion_data.dict()}
    )
    return {"message": "Promoção atualizada"}

@api_router.delete("/admin/promotions/{promotion_id}")
async def delete_promotion(promotion_id: str, admin_user: User = Depends(get_admin_user)):
    await db.promotions.update_one(
        {"id": promotion_id},
        {"$set": {"is_active": False}}
    )
    return {"message": "Promoção desativada"}

# Email management endpoints
@api_router.post("/admin/emails/send-discount")
async def send_discount_email_admin(
    user_email: str,
    user_name: str,
    coupon_code: str,
    discount_value: float,
    discount_type: str,
    expiry_date: str,
    admin_user: User = Depends(get_admin_user)
):
    result = await send_discount_email(user_email, user_name, coupon_code, discount_value, discount_type, expiry_date)
    return result

@api_router.post("/admin/emails/send-birthday")
async def send_birthday_email_admin(
    user_email: str,
    user_name: str,
    coupon_code: str,
    discount_value: float,
    admin_user: User = Depends(get_admin_user)
):
    result = await send_birthday_email(user_email, user_name, coupon_code, discount_value)
    return result

# Test email endpoint
@api_router.post("/admin/emails/test-welcome")
async def test_welcome_email(admin_user: User = Depends(get_admin_user)):
    """Send a test welcome email to demonstrate new template"""
    result = await send_welcome_email("eduardocorreia3344@gmail.com", "Eduardo")
    return {"message": "Test welcome email sent", "result": result}

@api_router.post("/admin/products", response_model=Product)
async def create_product(product_data: ProductCreate, admin_user: User = Depends(get_admin_user)):
    # Prioritize base64 image over URL if both are provided
    image_url = product_data.image_base64 if product_data.image_base64 else product_data.image_url
    
    # Handle multiple images
    images = []
    if product_data.images_base64:
        images.extend(product_data.images_base64)
    if product_data.images:
        images.extend(product_data.images)
    
    product_dict = product_data.dict()
    product_dict["image_url"] = image_url
    product_dict["images"] = images
    
    # Remove temporary fields from the final product data
    for field in ["image_base64", "images_base64"]:
        if field in product_dict:
            del product_dict[field]
    
    product = Product(**product_dict)
    await db.products.insert_one(product.dict())
    return product

@api_router.put("/admin/products/{product_id}")
async def update_product(product_id: str, product_data: ProductCreate, admin_user: User = Depends(get_admin_user)):
    # Prioritize base64 image over URL if both are provided
    update_data = product_data.dict()
    if update_data.get("image_base64"):
        update_data["image_url"] = update_data["image_base64"]
    
    # Handle multiple images
    images = []
    if product_data.images_base64:
        images.extend(product_data.images_base64)
    if product_data.images:
        images.extend(product_data.images)
    
    if images:
        update_data["images"] = images
    
    # Remove temporary fields from the final product data
    for field in ["image_base64", "images_base64"]:
        if field in update_data:
            del update_data[field]
    
    # Add updated timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    return {"message": "Produto atualizado com sucesso"}

@api_router.delete("/admin/products/{product_id}")
async def delete_product(product_id: str, admin_user: User = Depends(get_admin_user)):
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"is_active": False}}
    )
    return {"message": "Produto removido"}

@api_router.post("/admin/categories")
async def create_category(category_data: CategoryCreate, admin_user: User = Depends(get_admin_user)):
    category = Category(
        id=category_data.name.lower().replace(" ", "_").replace("-", "_"),
        **category_data.dict()
    )
    await db.categories.insert_one(category.dict())
    return category

# Chat System Endpoints
@api_router.post("/chat/sessions")
async def create_chat_session(session_data: ChatSessionCreate, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    chat_session = ChatSession(
        user_id=current_user.id,
        subject=session_data.subject
    )
    await db.chat_sessions.insert_one(chat_session.dict())
    return chat_session

@api_router.get("/chat/sessions")
async def get_user_chat_sessions(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    sessions = await db.chat_sessions.find({"user_id": current_user.id}).sort("updated_at", -1).to_list(1000)
    # Convert ObjectId to string
    for session in sessions:
        if "_id" in session:
            session["_id"] = str(session["_id"])
    return sessions

@api_router.get("/chat/sessions/{session_id}/messages")
async def get_chat_messages(session_id: str, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify user owns this session or is admin
    session = await db.chat_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")
    
    if session["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    messages = await db.chat_messages.find({"chat_session_id": session_id}).sort("timestamp", 1).to_list(1000)
    # Convert ObjectId to string
    for message in messages:
        if "_id" in message:
            message["_id"] = str(message["_id"])
    return messages

@api_router.post("/chat/sessions/{session_id}/messages")
async def send_chat_message(session_id: str, message_data: ChatMessageCreate, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify user owns this session or is admin
    session = await db.chat_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")
    
    if session["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Determine sender type
    sender_type = "agent" if current_user.is_admin else "user"
    
    chat_message = ChatMessage(
        chat_session_id=session_id,
        sender_id=current_user.id,
        sender_type=sender_type,
        message=message_data.message
    )
    
    await db.chat_messages.insert_one(chat_message.dict())
    
    # Update session updated_at
    await db.chat_sessions.update_one(
        {"id": session_id},
        {"$set": {"updated_at": datetime.utcnow()}}
    )
    
    # If user is admin, assign themselves as agent
    if current_user.is_admin and not session.get("agent_id"):
        await db.chat_sessions.update_one(
            {"id": session_id},
            {"$set": {"agent_id": current_user.id}}
        )
    
    return chat_message

@api_router.put("/chat/sessions/{session_id}/close")
async def close_chat_session(session_id: str, current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify user owns this session or is admin
    session = await db.chat_sessions.find_one({"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Sessão de chat não encontrada")
    
    if session["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    await db.chat_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "closed", "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Sessão de chat encerrada"}

# Admin Chat Endpoints
@api_router.get("/admin/chat/sessions")
async def get_all_chat_sessions(admin_user: User = Depends(get_admin_user)):
    # Auto-close sessions inactive for more than 10 minutes
    inactive_threshold = datetime.utcnow() - timedelta(minutes=10)
    await db.chat_sessions.update_many(
        {
            "status": {"$in": ["pending", "active"]},
            "updated_at": {"$lt": inactive_threshold}
        },
        {"$set": {"status": "auto_closed", "updated_at": datetime.utcnow()}}
    )
    
    sessions = await db.chat_sessions.find().sort("updated_at", -1).to_list(1000)
    
    # Get user info for each session
    result = []
    for session in sessions:
        if "_id" in session:
            session["_id"] = str(session["_id"])
        
        user = await db.users.find_one({"id": session["user_id"]})
        session["user_name"] = user["name"] if user else "Usuário desconhecido"
        session["user_email"] = user["email"] if user else ""
        
        # Get first message (subject/initial request)
        first_message = await db.chat_messages.find_one(
            {"chat_session_id": session["id"]},
            sort=[("timestamp", 1)]
        )
        session["subject"] = first_message["message"][:100] + "..." if first_message and len(first_message["message"]) > 100 else (first_message["message"] if first_message else "Sem mensagem inicial")
        
        # Get last message
        last_message = await db.chat_messages.find_one(
            {"chat_session_id": session["id"]},
            sort=[("timestamp", -1)]
        )
        session["last_message"] = last_message["message"] if last_message else ""
        session["last_message_time"] = last_message["timestamp"] if last_message else session["created_at"]
        
        result.append(session)
    
    return result

@api_router.put("/admin/chat/sessions/{session_id}/assign")
async def assign_chat_session(session_id: str, admin_user: User = Depends(get_admin_user)):
    await db.chat_sessions.update_one(
        {"id": session_id},
        {"$set": {"agent_id": admin_user.id, "status": "active", "updated_at": datetime.utcnow()}}
    )
    return {"message": "Sessão atribuída"}

@api_router.put("/admin/chat/sessions/{session_id}/reject")
async def reject_chat_session(session_id: str, admin_user: User = Depends(get_admin_user)):
    await db.chat_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "rejected", "updated_at": datetime.utcnow()}}
    )
    return {"message": "Sessão rejeitada"}

# OTP and password change endpoints
@api_router.post("/auth/send-otp")
async def send_otp(request: dict, current_user: User = Depends(get_current_user)):
    """Send OTP to user's email for password change"""
    try:
        email = request.get("email")
        if not email or email != current_user.email:
            raise HTTPException(status_code=400, detail="Email inválido")
        
        # Generate 6-digit OTP
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Store OTP in database with expiration (10 minutes)
        expiry_time = datetime.utcnow() + timedelta(minutes=10)
        
        # Create encrypted OTP (store hash, not plain text)
        otp_hash = pwd_context.hash(otp_code)
        
        await db.otps.insert_one({
            "user_id": current_user.id,
            "otp_hash": otp_hash,
            "created_at": datetime.utcnow(),
            "expires_at": expiry_time,
            "used": False
        })
        
        # Send OTP via email
        subject = "Código de Verificação - Mystery Box Store"
        html_content = f"""
        <h2>Código de Verificação</h2>
        <p>Olá {current_user.name},</p>
        <p>Seu código de verificação para alterar a senha é:</p>
        <h1 style="color: #8B5CF6; font-size: 2em; text-align: center; letter-spacing: 0.5em;">{otp_code}</h1>
        <p>Este código expira em 10 minutos.</p>
        <p>Se não solicitou esta alteração, ignore este email.</p>
        """
        
        try:
            resend.Emails.send({
                "from": "Mystery Box Store <noreply@mysteryboxes.pt>",
                "to": [email],
                "subject": subject,
                "html": html_content
            })
        except Exception as e:
            logger.warning(f"Email send failed: {str(e)}")
            # Continue anyway - user might still have OTP for testing
            
        return {"message": "Código OTP enviado para seu email"}
        
    except Exception as e:
        logger.error(f"Send OTP error: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@api_router.post("/auth/change-password")
async def change_password(request: dict, current_user: User = Depends(get_current_user)):
    """Change user password with OTP verification"""
    try:
        current_password = request.get("current_password")
        new_password = request.get("new_password")
        otp_code = request.get("otp_code")
        
        if not all([current_password, new_password, otp_code]):
            raise HTTPException(status_code=400, detail="Todos os campos são obrigatórios")
        
        # Verify current password
        if not pwd_context.verify(current_password, current_user.password):
            raise HTTPException(status_code=400, detail="Senha atual incorreta")
        
        # Find and verify OTP
        otp_record = await db.otps.find_one({
            "user_id": current_user.id,
            "used": False,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if not otp_record:
            raise HTTPException(status_code=400, detail="Código OTP inválido ou expirado")
        
        # Verify OTP code
        if not pwd_context.verify(otp_code, otp_record["otp_hash"]):
            raise HTTPException(status_code=400, detail="Código OTP incorreto")
        
        # Mark OTP as used
        await db.otps.update_one(
            {"_id": otp_record["_id"]},
            {"$set": {"used": True}}
        )
        
        # Update password
        new_password_hash = pwd_context.hash(new_password)
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": {"password": new_password_hash, "updated_at": datetime.utcnow()}}
        )
        
        return {"message": "Senha alterada com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# Test email endpoint
class TestEmailRequest(BaseModel):
    to_email: str
    subject: str = "Teste de Email - Mystery Box Store"
    message: str = "Este é um email de teste do sistema Mystery Box Store."

@api_router.post("/test/send-email")
async def test_send_email(request: TestEmailRequest):
    """Test endpoint to send emails through Resend"""
    try:
        to_email = request.to_email
        subject = request.subject
        custom_message = request.message
        
        if not to_email:
            raise HTTPException(status_code=400, detail="Email de destino é obrigatório")
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 14px; }}
                .test-info {{ background-color: #e0e7ff; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎁 Mystery Box Store</h1>
                    <p>Teste de Sistema de Emails</p>
                </div>
                <div class="content">
                    <h2>Email de Teste Enviado com Sucesso! ✅</h2>
                    <p>{custom_message}</p>
                    
                    <div class="test-info">
                        <h3>Informações do Teste:</h3>
                        <ul>
                            <li><strong>Serviço:</strong> Resend API</li>
                            <li><strong>Data/Hora:</strong> {datetime.utcnow().strftime('%d/%m/%Y às %H:%M:%S')} UTC</li>
                            <li><strong>Email de Destino:</strong> {to_email}</li>
                            <li><strong>Status:</strong> Enviado com sucesso</li>
                        </ul>
                    </div>
                    
                    <p>Se você recebeu este email, significa que o sistema de emails da Mystery Box Store está funcionando corretamente através do Resend! 🎉</p>
                    
                    <p>Este é um email automatizado de teste. Por favor, não responda a este email.</p>
                </div>
                <div class="footer">
                    <p>© 2024 Mystery Box Store - Sistema de Teste de Emails</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email using existing send_email function
        result = await send_email(to_email, subject, html_content)
        
        return {
            "success": True,
            "message": f"Email de teste enviado com sucesso para {to_email}",
            "timestamp": datetime.utcnow().isoformat(),
            "email_result": result
        }
        
    except Exception as e:
        logger.error(f"Test email sending error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar email de teste: {str(e)}")

@api_router.get("/test/resend-status")
async def test_resend_status():
    """Test endpoint to check Resend API status"""
    try:
        # Check if Resend API key is set
        api_key = os.environ.get('RESEND_API_KEY')
        if not api_key:
            return {"status": "error", "message": "Resend API key not set"}
        
        # Check Resend module
        resend_version = getattr(resend, "__version__", "unknown")
        
        # Try to send a test email to a test address
        test_email = "test@example.com"
        params = {
            "from": "Mystery Box Store <noreply@mysteryboxes.pt>",
            "to": [test_email],
            "subject": "Test Email",
            "html": "<p>This is a test email.</p>"
        }
        
        try:
            # Try to access the Emails class
            emails_class = getattr(resend, "Emails", None)
            if emails_class is None:
                return {
                    "status": "error", 
                    "message": "Resend.Emails class not found",
                    "resend_version": resend_version,
                    "api_key_set": bool(api_key),
                    "api_key_prefix": api_key[:5] + "..." if api_key else None
                }
            
            # Try to access the send method
            send_method = getattr(emails_class, "send", None)
            if send_method is None:
                return {
                    "status": "error", 
                    "message": "Resend.Emails.send method not found",
                    "resend_version": resend_version,
                    "api_key_set": bool(api_key),
                    "api_key_prefix": api_key[:5] + "..." if api_key else None
                }
            
            # Don't actually send the email to avoid unnecessary API calls
            return {
                "status": "ok",
                "message": "Resend API is properly configured",
                "resend_version": resend_version,
                "api_key_set": bool(api_key),
                "api_key_prefix": api_key[:5] + "..." if api_key else None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error accessing Resend API: {str(e)}",
                "resend_version": resend_version,
                "api_key_set": bool(api_key),
                "api_key_prefix": api_key[:5] + "..." if api_key else None
            }
    except Exception as e:
        logger.error(f"Resend status check error: {str(e)}")
        return {"status": "error", "message": f"Error checking Resend status: {str(e)}"}

# Include router
app.include_router(api_router)

# Add root route to avoid 404
@app.get("/")
async def root():
    return {"message": "Mystery Box Store API", "version": "2.0.0", "status": "running"}

@app.get("/api")
async def api_root():
    return {"message": "Mystery Box Store API", "version": "2.0.0", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify API is running"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Configure CORS based on environment
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://localhost:3000", 
    FRONTEND_URL,
    "*"  # Allow all origins for testing
]

# Add any additional origins from environment variable
additional_origins = os.environ.get('ADDITIONAL_CORS_ORIGINS', '')
if additional_origins:
    CORS_ORIGINS.extend([origin.strip() for origin in additional_origins.split(',')])

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],  # Allow all origins for testing
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test email endpoint
class TestEmailRequest(BaseModel):
    to_email: str
    subject: str = "Teste de Email - Mystery Box Store"
    message: str = "Este é um email de teste do sistema Mystery Box Store."

@api_router.post("/test/send-email")
async def test_send_email(request: TestEmailRequest):
    """Test endpoint to send emails through Resend"""
    try:
        to_email = request.to_email
        subject = request.subject
        custom_message = request.message
        
        if not to_email:
            raise HTTPException(status_code=400, detail="Email de destino é obrigatório")
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{subject}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 14px; }}
                .test-info {{ background-color: #e0e7ff; padding: 15px; border-radius: 6px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎁 Mystery Box Store</h1>
                    <p>Teste de Sistema de Emails</p>
                </div>
                <div class="content">
                    <h2>Email de Teste Enviado com Sucesso! ✅</h2>
                    <p>{custom_message}</p>
                    
                    <div class="test-info">
                        <h3>Informações do Teste:</h3>
                        <ul>
                            <li><strong>Serviço:</strong> Resend API</li>
                            <li><strong>Data/Hora:</strong> {datetime.utcnow().strftime('%d/%m/%Y às %H:%M:%S')} UTC</li>
                            <li><strong>Email de Destino:</strong> {to_email}</li>
                            <li><strong>Status:</strong> Enviado com sucesso</li>
                        </ul>
                    </div>
                    
                    <p>Se você recebeu este email, significa que o sistema de emails da Mystery Box Store está funcionando corretamente através do Resend! 🎉</p>
                    
                    <p>Este é um email automatizado de teste. Por favor, não responda a este email.</p>
                </div>
                <div class="footer">
                    <p>© 2024 Mystery Box Store - Sistema de Teste de Emails</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email using existing send_email function
        result = await send_email(to_email, subject, html_content)
        
        return {
            "success": True,
            "message": f"Email de teste enviado com sucesso para {to_email}",
            "timestamp": datetime.utcnow().isoformat(),
            "email_result": result
        }
        
    except Exception as e:
        logger.error(f"Test email sending error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar email de teste: {str(e)}")

@api_router.get("/test/resend-status")
async def test_resend_status():
    """Test endpoint to check Resend API status"""
    try:
        # Check if Resend API key is set
        api_key = os.environ.get('RESEND_API_KEY')
        if not api_key:
            return {"status": "error", "message": "Resend API key not set"}
        
        # Check Resend module
        resend_version = getattr(resend, "__version__", "unknown")
        
        # Try to send a test email to a test address
        test_email = "test@example.com"
        params = {
            "from": "Mystery Box Store <noreply@mysteryboxes.pt>",
            "to": [test_email],
            "subject": "Test Email",
            "html": "<p>This is a test email.</p>"
        }
        
        try:
            # Try to access the Emails class
            emails_class = getattr(resend, "Emails", None)
            if emails_class is None:
                return {
                    "status": "error", 
                    "message": "Resend.Emails class not found",
                    "resend_version": resend_version,
                    "api_key_set": bool(api_key),
                    "api_key_prefix": api_key[:5] + "..." if api_key else None
                }
            
            # Try to access the send method
            send_method = getattr(emails_class, "send", None)
            if send_method is None:
                return {
                    "status": "error", 
                    "message": "Resend.Emails.send method not found",
                    "resend_version": resend_version,
                    "api_key_set": bool(api_key),
                    "api_key_prefix": api_key[:5] + "..." if api_key else None
                }
            
            # Don't actually send the email to avoid unnecessary API calls
            return {
                "status": "ok",
                "message": "Resend API is properly configured",
                "resend_version": resend_version,
                "api_key_set": bool(api_key),
                "api_key_prefix": api_key[:5] + "..." if api_key else None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error accessing Resend API: {str(e)}",
                "resend_version": resend_version,
                "api_key_set": bool(api_key),
                "api_key_prefix": api_key[:5] + "..." if api_key else None
            }
    except Exception as e:
        logger.error(f"Resend status check error: {str(e)}")
        return {"status": "error", "message": f"Error checking Resend status: {str(e)}"}

# Health check endpoint for Railway
@app.get("/api/health")
async def health_check():
    try:
        # Test database connection
        await db.command("ping")
        return {
            "status": "healthy", 
            "timestamp": datetime.utcnow().isoformat(),
            "service": "Mystery Box Store API",
            "version": "2.0.0",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()