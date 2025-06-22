from pydantic import BaseModel
from typing import Dict, Optional, Any
import stripe
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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