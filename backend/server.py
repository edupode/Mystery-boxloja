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
    image_url: str
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
            "from": "Mystery Box Store <noreply@mysteryboxstore.com>",
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
        <meta charset="utf-8">
        <title>Bem-vindo à Mystery Box Store!</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #0f0f10; color: white; }
            .container { background: linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899); padding: 40px; border-radius: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .content { background: rgba(0,0,0,0.3); padding: 30px; border-radius: 15px; }
            .button { display: inline-block; background: linear-gradient(45deg, #fbbf24, #f59e0b); color: black; padding: 15px 30px; text-decoration: none; border-radius: 10px; font-weight: bold; margin: 20px 0; }
            .footer { text-align: center; margin-top: 30px; font-size: 14px; color: #ccc; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎁 Bem-vindo à Mystery Box Store!</h1>
                <div style="font-size: 48px;">🔮 ⚡ 👻</div>
            </div>
            <div class="content">
                <h2>Olá {{ user_name }}! 🎉</h2>
                <p>Bem-vindo ao mundo dos mistérios! Estamos muito felizes por se ter juntado à nossa comunidade de exploradores.</p>
                <p>Na Mystery Box Store, cada caixa é uma aventura única cheia de surpresas incríveis, desde produtos geek e terror até cuidados para pets e muito mais!</p>
                
                <div style="text-align: center;">
                    <a href="https://mysteryboxstore.com/produtos" class="button">🔍 Explorar Mistérios</a>
                </div>
                
                <h3>O que pode esperar:</h3>
                <ul>
                    <li>🎭 Caixas temáticas únicas</li>
                    <li>🎯 Opções de assinatura com desconto</li>
                    <li>📦 Produtos de alta qualidade</li>
                    <li>🎉 Surpresas em cada entrega</li>
                </ul>
                
                <p>Prepare-se para descobrir o inesperado!</p>
            </div>
            <div class="footer">
                <p>Mystery Box Store - Descobre o Inesperado! 🚀</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    template = Template(html_template)
    html_content = template.render(user_name=user_name)
    
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
        <meta charset="utf-8">
        <title>Confirmação de Pedido</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #0f0f10; color: white; }
            .container { background: linear-gradient(135deg, #059669, #0d9488); padding: 40px; border-radius: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .content { background: rgba(0,0,0,0.3); padding: 30px; border-radius: 15px; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #374151; }
            th { background-color: rgba(0,0,0,0.3); }
            .total-row { font-weight: bold; background-color: rgba(0,0,0,0.2); }
            .footer { text-align: center; margin-top: 30px; font-size: 14px; color: #ccc; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Pedido Confirmado!</h1>
                <div style="font-size: 48px;">🎉</div>
            </div>
            <div class="content">
                <h2>Obrigado pelo seu pedido!</h2>
                <p><strong>Número do Pedido:</strong> {{ order_id }}</p>
                <p><strong>Data:</strong> {{ order_date }}</p>
                
                <h3>📦 Itens do Pedido:</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Produto</th>
                            <th>Quantidade</th>
                            <th>Preço</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in items %}
                        <tr>
                            <td>{{ item.name }}</td>
                            <td>{{ item.quantity }}</td>
                            <td>€{{ item.total_price }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                
                <table>
                    <tr><td>Subtotal:</td><td>€{{ subtotal }}</td></tr>
                    {% if discount_amount > 0 %}
                    <tr><td>Desconto{% if coupon_code %} ({{ coupon_code }}){% endif %}:</td><td>-€{{ discount_amount }}</td></tr>
                    {% endif %}
                    <tr><td>IVA (23%):</td><td>€{{ vat_amount }}</td></tr>
                    <tr><td>Envio:</td><td>€{{ shipping_cost }}</td></tr>
                    <tr class="total-row"><td><strong>Total:</strong></td><td><strong>€{{ total_amount }}</strong></td></tr>
                </table>
                
                <h3>📍 Informações de Entrega:</h3>
                <p>{{ shipping_address }}</p>
                <p><strong>Telemóvel:</strong> {{ phone }}</p>
                {% if nif %}
                <p><strong>NIF:</strong> {{ nif }}</p>
                {% endif %}
                
                <p>Receberá em breve informações sobre o envio do seu pedido!</p>
            </div>
            <div class="footer">
                <p>Mystery Box Store - Os seus mistérios estão a caminho! 🚀</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Prepare order items for template
    order_items = []
    for item in order.items:
        product = next((p for p in products if p["id"] == item.product_id), None)
        if product:
            price = item.subscription_type and product["subscription_prices"].get(item.subscription_type) or product["price"]
            order_items.append({
                "name": product["name"],
                "quantity": item.quantity,
                "total_price": f"{price * item.quantity:.2f}"
            })
    
    template = Template(html_template)
    html_content = template.render(
        order_id=order.id,
        order_date=order.created_at.strftime("%d/%m/%Y %H:%M"),
        items=order_items,
        subtotal=f"{order.subtotal:.2f}",
        discount_amount=f"{order.discount_amount:.2f}",
        coupon_code=order.coupon_code,
        vat_amount=f"{order.vat_amount:.2f}",
        shipping_cost=f"{order.shipping_cost:.2f}",
        total_amount=f"{order.total_amount:.2f}",
        shipping_address=order.shipping_address,
        phone=order.phone,
        nif=order.nif
    )
    
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
                    <a href="https://mysteryboxstore.com/produtos" class="button">🛒 Usar Desconto</a>
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
                    <a href="https://mysteryboxstore.com/produtos" class="button">🎁 Celebrar com Compras</a>
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
        query["category_id"] = category
    if featured is not None:
        query["is_featured"] = featured

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
    return orders

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

@api_router.post("/admin/products", response_model=Product)
async def create_product(product_data: ProductCreate, admin_user: User = Depends(get_admin_user)):
    # Prioritize base64 image over URL if both are provided
    image_url = product_data.image_base64 if product_data.image_base64 else product_data.image_url
    
    product_dict = product_data.dict()
    product_dict["image_url"] = image_url
    # Remove image_base64 from the final product data
    if "image_base64" in product_dict:
        del product_dict["image_base64"]
    
    product = Product(**product_dict)
    await db.products.insert_one(product.dict())
    return product

@api_router.put("/admin/products/{product_id}")
async def update_product(product_id: str, product_data: ProductCreate, admin_user: User = Depends(get_admin_user)):
    # Prioritize base64 image over URL if both are provided
    update_data = product_data.dict()
    if update_data.get("image_base64"):
        update_data["image_url"] = update_data["image_base64"]
    
    # Remove image_base64 from the final product data
    if "image_base64" in update_data:
        del update_data["image_base64"]
    
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
            resend.emails.send({
                "from": "noreply@mysteryboxstore.com",
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

# Include router
app.include_router(api_router)

# Add root route to avoid 404
@app.get("/")
async def root():
    return {"message": "Mystery Box Store API", "version": "2.0.0", "status": "running"}

@app.get("/api")
async def api_root():
    return {"message": "Mystery Box Store API", "version": "2.0.0", "status": "running"}

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()