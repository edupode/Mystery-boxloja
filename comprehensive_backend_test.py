import requests
import json
import uuid
import time
import base64
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"

# Admin credentials
ADMIN_USER = {
    "email": "eduardocorreia3344@gmail.com",
    "password": "admin123"
}

# Test data
TEST_USER = {
    "email": f"test_user_{uuid.uuid4()}@example.com",
    "name": "Test User",
    "password": "Test@123"
}

# Test session ID
SESSION_ID = str(uuid.uuid4())

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

#=============================================================================
# 1. AUTHENTICATION AND USERS
#=============================================================================

def test_register():
    """Test user registration"""
    try:
        response = requests.post(f"{API_URL}/auth/register", json=TEST_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store token for later tests
            test_results["auth_token"] = response_data["access_token"]
            return log_test_result("User Registration", True, f"Created user: {TEST_USER['email']}")
        else:
            return log_test_result("User Registration", False, f"Failed to register user: {response.text}")
    except Exception as e:
        return log_test_result("User Registration", False, f"Exception: {str(e)}")

def test_login():
    """Test user login with email/password"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        })
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Update token
            test_results["auth_token"] = response_data["access_token"]
            return log_test_result("User Login", True)
        else:
            return log_test_result("User Login", False, f"Failed to login: {response.text}")
    except Exception as e:
        return log_test_result("User Login", False, f"Exception: {str(e)}")

def test_google_auth():
    """Test Google OAuth login (mock test)"""
    try:
        # We can't fully test this without a valid Google token
        # But we can test that the endpoint exists and rejects invalid tokens
        response = requests.post(f"{API_URL}/auth/google", json={"token": "invalid_token"})
        
        if response.status_code == 400 and "Invalid Google token" in response.text:
            return log_test_result("Google OAuth Login", True, "Endpoint correctly rejects invalid tokens")
        else:
            return log_test_result("Google OAuth Login", False, f"Unexpected response: {response.status_code}, {response.text}")
    except Exception as e:
        return log_test_result("Google OAuth Login", False, f"Exception: {str(e)}")

def test_verify_token():
    """Test JWT token verification"""
    if "auth_token" not in test_results:
        return log_test_result("Verify Token", False, "No auth token available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        response_data = response.json()
        
        if response.status_code == 200 and "email" in response_data:
            return log_test_result("Verify Token", True, "Token verification successful")
        else:
            return log_test_result("Verify Token", False, f"Failed to verify token: {response.text}")
    except Exception as e:
        return log_test_result("Verify Token", False, f"Exception: {str(e)}")

def test_update_profile():
    """Test updating user profile"""
    if "auth_token" not in test_results:
        return log_test_result("Update Profile", False, "No auth token available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Test with valid NIF
        profile_data = {
            "name": "Updated Test User",
            "phone": "+351912345678",
            "address": "Rua de Teste, 123",
            "city": "Lisboa",
            "postal_code": "1000-100",
            "nif": "501964843",  # Valid Portuguese NIF
            "birth_date": (datetime.utcnow() - timedelta(days=365*25)).isoformat()
        }
        
        response = requests.put(f"{API_URL}/auth/profile", json=profile_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Update Profile", False, f"Failed: {response.text}")
        
        # Test with invalid NIF
        invalid_profile_data = {
            "nif": "123456789"  # Invalid Portuguese NIF
        }
        
        response = requests.put(f"{API_URL}/auth/profile", json=invalid_profile_data, headers=headers)
        if response.status_code == 400 and "NIF inválido" in response.text:
            log_test_result("Update Profile with Invalid NIF", True, "Correctly rejected invalid NIF")
        else:
            log_test_result("Update Profile with Invalid NIF", False, f"Did not reject invalid NIF: {response.status_code}, {response.text}")
        
        # Verify profile was updated
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        if response.status_code != 200:
            return log_test_result("Get Updated Profile", False, f"Failed: {response.text}")
        
        updated_profile = response.json()
        if updated_profile.get("name") != profile_data["name"]:
            return log_test_result("Get Updated Profile", False, "Profile not updated correctly")
        
        return log_test_result("Update Profile", True, "Profile updated successfully")
    except Exception as e:
        return log_test_result("Update Profile", False, f"Exception: {str(e)}")

def test_get_user_orders():
    """Test getting user order history"""
    if "auth_token" not in test_results:
        return log_test_result("Get User Orders", False, "No auth token available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(f"{API_URL}/auth/orders", headers=headers)
        
        if response.status_code != 200:
            return log_test_result("Get User Orders", False, f"Failed: {response.text}")
        
        orders = response.json()
        if not isinstance(orders, list):
            return log_test_result("Get User Orders", False, "Invalid orders data format")
        
        return log_test_result("Get User Orders", True, f"Found {len(orders)} orders")
    except Exception as e:
        return log_test_result("Get User Orders", False, f"Exception: {str(e)}")

#=============================================================================
# 2. PRODUCTS AND CATEGORIES
#=============================================================================

def test_list_products():
    """Test listing products"""
    try:
        # Test without filters
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("List Products", False, f"Failed: {response.text}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("List Products", False, "No products returned or invalid format")
        
        # Store a product ID for later tests
        if products:
            test_results["product_id"] = products[0]["id"]
        
        # Test with category filter
        if products and "category" in products[0]:
            category = products[0]["category"]
            response = requests.get(f"{API_URL}/products?category={category}")
            if response.status_code != 200:
                return log_test_result("List Products with Category Filter", False, f"Failed: {response.text}")
            
            filtered_products = response.json()
            if not all(p["category"] == category for p in filtered_products):
                return log_test_result("List Products with Category Filter", False, "Filter not working correctly")
        
        # Test with featured filter
        response = requests.get(f"{API_URL}/products?featured=true")
        if response.status_code != 200:
            return log_test_result("List Products with Featured Filter", False, f"Failed: {response.text}")
        
        featured_products = response.json()
        if not all(p.get("featured", False) for p in featured_products):
            return log_test_result("List Products with Featured Filter", False, "Featured filter not working")
        
        return log_test_result("List Products", True, f"Found {len(products)} products")
    except Exception as e:
        return log_test_result("List Products", False, f"Exception: {str(e)}")

def test_get_product_details():
    """Test getting product details"""
    if "product_id" not in test_results:
        return log_test_result("Get Product Details", False, "No product ID available")
    
    try:
        response = requests.get(f"{API_URL}/products/{test_results['product_id']}")
        if response.status_code != 200:
            return log_test_result("Get Product Details", False, f"Failed: {response.text}")
        
        product = response.json()
        if not product or not isinstance(product, dict) or "id" not in product:
            return log_test_result("Get Product Details", False, "Invalid product data")
        
        return log_test_result("Get Product Details", True, f"Product: {product['name']}")
    except Exception as e:
        return log_test_result("Get Product Details", False, f"Exception: {str(e)}")

def test_list_categories():
    """Test listing categories"""
    try:
        response = requests.get(f"{API_URL}/categories")
        if response.status_code != 200:
            return log_test_result("List Categories", False, f"Failed: {response.text}")
        
        categories = response.json()
        if not categories or not isinstance(categories, list):
            return log_test_result("List Categories", False, "No categories returned or invalid format")
        
        # Store a category ID for later tests
        if categories:
            test_results["category_id"] = categories[0]["id"]
        
        return log_test_result("List Categories", True, f"Found {len(categories)} categories")
    except Exception as e:
        return log_test_result("List Categories", False, f"Exception: {str(e)}")

#=============================================================================
# 3. CART SYSTEM
#=============================================================================

def test_get_cart():
    """Test getting cart"""
    try:
        response = requests.get(f"{API_URL}/cart/{SESSION_ID}")
        if response.status_code != 200:
            return log_test_result("Get Cart", False, f"Failed: {response.text}")
        
        cart = response.json()
        if not cart or not isinstance(cart, dict) or "session_id" not in cart:
            return log_test_result("Get Cart", False, "Invalid cart data")
        
        return log_test_result("Get Cart", True, "Successfully retrieved cart")
    except Exception as e:
        return log_test_result("Get Cart", False, f"Exception: {str(e)}")

def test_add_to_cart():
    """Test adding product to cart"""
    if "product_id" not in test_results:
        return log_test_result("Add to Cart", False, "No product ID available")
    
    try:
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 2,
            "subscription_type": "1_month"
        }
        
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Add to Cart", False, f"Failed: {response.text}")
        
        updated_cart = response.json()
        if not updated_cart or not updated_cart.get("items"):
            return log_test_result("Add to Cart", False, "Product not added to cart")
        
        # Check if product was added
        product_in_cart = False
        for item in updated_cart["items"]:
            if item["product_id"] == test_results["product_id"]:
                product_in_cart = True
                break
        
        if not product_in_cart:
            return log_test_result("Add to Cart", False, "Product not found in cart after adding")
        
        return log_test_result("Add to Cart", True, "Product added to cart successfully")
    except Exception as e:
        return log_test_result("Add to Cart", False, f"Exception: {str(e)}")

def test_remove_from_cart():
    """Test removing product from cart"""
    if "product_id" not in test_results:
        return log_test_result("Remove from Cart", False, "No product ID available")
    
    try:
        # First, add a product to cart
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 1
        }
        
        requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        
        # Now remove it
        response = requests.delete(
            f"{API_URL}/cart/{SESSION_ID}/remove/{test_results['product_id']}"
        )
        if response.status_code != 200:
            return log_test_result("Remove from Cart", False, f"Failed: {response.text}")
        
        cart_after_remove = response.json()
        if any(item["product_id"] == test_results["product_id"] for item in cart_after_remove.get("items", [])):
            return log_test_result("Remove from Cart", False, "Product still in cart after removal")
        
        return log_test_result("Remove from Cart", True, "Product removed from cart successfully")
    except Exception as e:
        return log_test_result("Remove from Cart", False, f"Exception: {str(e)}")

def test_apply_coupon():
    """Test applying coupon to cart"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Apply Coupon", False, "Admin login required to create test coupon")
    
    try:
        # Create a test coupon
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        coupon_code = f"TEST{uuid.uuid4().hex[:8].upper()}"
        
        coupon_data = {
            "code": coupon_code,
            "description": "Test Coupon",
            "discount_type": "percentage",
            "discount_value": 10.0,
            "min_order_value": 10.0,
            "max_uses": 10,
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "applicable_categories": [],
            "applicable_products": []
        }
        
        response = requests.post(f"{API_URL}/admin/coupons", json=coupon_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Test Coupon", False, f"Failed: {response.text}")
        
        # Add product to cart
        if "product_id" not in test_results:
            test_list_products()
        
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 2
        }
        
        requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        
        # Apply coupon to cart
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code={coupon_code}")
        if response.status_code != 200:
            return log_test_result("Apply Coupon", False, f"Failed: {response.text}")
        
        cart_with_coupon = response.json()
        if not cart_with_coupon.get("coupon_code"):
            return log_test_result("Apply Coupon", False, "Coupon not applied to cart")
        
        return log_test_result("Apply Coupon", True, f"Coupon {coupon_code} applied successfully")
    except Exception as e:
        return log_test_result("Apply Coupon", False, f"Exception: {str(e)}")

def test_remove_coupon():
    """Test removing coupon from cart"""
    try:
        # First apply a coupon if not already tested
        if "Apply Coupon" not in test_results or not test_results["Apply Coupon"].get("success"):
            test_apply_coupon()
        
        # Remove coupon
        response = requests.delete(f"{API_URL}/cart/{SESSION_ID}/remove-coupon")
        if response.status_code != 200:
            return log_test_result("Remove Coupon", False, f"Failed: {response.text}")
        
        cart_without_coupon = response.json()
        if cart_without_coupon.get("coupon_code"):
            return log_test_result("Remove Coupon", False, "Coupon still applied after removal")
        
        return log_test_result("Remove Coupon", True, "Coupon removed successfully")
    except Exception as e:
        return log_test_result("Remove Coupon", False, f"Exception: {str(e)}")

#=============================================================================
# 4. COUPONS
#=============================================================================

def test_validate_coupon():
    """Test coupon validation"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Validate Coupon", False, "Admin login required to create test coupon")
    
    try:
        # Create a test coupon if not already created
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        coupon_code = f"TEST{uuid.uuid4().hex[:8].upper()}"
        
        coupon_data = {
            "code": coupon_code,
            "description": "Test Coupon for Validation",
            "discount_type": "percentage",
            "discount_value": 15.0,
            "min_order_value": 20.0,
            "max_uses": 5,
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "applicable_categories": [],
            "applicable_products": []
        }
        
        response = requests.post(f"{API_URL}/admin/coupons", json=coupon_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Test Coupon for Validation", False, f"Failed: {response.text}")
        
        # Validate the coupon
        response = requests.get(f"{API_URL}/coupons/validate/{coupon_code}")
        if response.status_code != 200:
            return log_test_result("Validate Coupon", False, f"Failed: {response.text}")
        
        coupon = response.json()
        if not coupon or coupon.get("code") != coupon_code.upper():
            return log_test_result("Validate Coupon", False, "Invalid coupon data in response")
        
        # Test with invalid coupon code
        invalid_code = "INVALID_COUPON_CODE"
        response = requests.get(f"{API_URL}/coupons/validate/{invalid_code}")
        if response.status_code == 404:
            log_test_result("Validate Invalid Coupon", True, "Correctly rejected invalid coupon code")
        else:
            log_test_result("Validate Invalid Coupon", False, f"Did not reject invalid coupon: {response.status_code}, {response.text}")
        
        return log_test_result("Validate Coupon", True, f"Coupon {coupon_code} validated successfully")
    except Exception as e:
        return log_test_result("Validate Coupon", False, f"Exception: {str(e)}")

#=============================================================================
# 5. CHECKOUT AND PAYMENTS
#=============================================================================

def test_checkout_with_card():
    """Test checkout process with card payment"""
    if "product_id" not in test_results:
        return log_test_result("Checkout with Card", False, "No product ID available")
    
    try:
        # Create a new session ID for this test
        card_session_id = str(uuid.uuid4())
        
        # Add product to cart
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 1
        }
        
        response = requests.post(f"{API_URL}/cart/{card_session_id}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Add to Cart for Card Checkout", False, f"Failed: {response.text}")
        
        # Create checkout with card payment
        checkout_data = {
            "cart_id": card_session_id,
            "shipping_address": "Rua de Teste, 123, Lisboa",
            "phone": "+351912345678",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "card",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data)
        if response.status_code != 200:
            return log_test_result("Checkout with Card", False, f"Failed: {response.text}")
        
        checkout_result = response.json()
        if "order_id" not in checkout_result or "checkout_url" not in checkout_result:
            return log_test_result("Checkout with Card", False, "Missing order_id or checkout_url in response")
        
        test_results["order_id_card"] = checkout_result["order_id"]
        
        # Check if cart was cleared after checkout
        response = requests.get(f"{API_URL}/cart/{card_session_id}")
        if response.status_code != 200:
            return log_test_result("Cart Cleared After Card Checkout", False, f"Failed to get cart: {response.text}")
        
        cart_after_checkout = response.json()
        if cart_after_checkout.get("items") and len(cart_after_checkout["items"]) > 0:
            return log_test_result("Cart Cleared After Card Checkout", False, "Cart not cleared after checkout")
        
        log_test_result("Cart Cleared After Card Checkout", True, "Cart was cleared after checkout")
        
        # If we have a Stripe session, test payment status
        if "checkout_url" in checkout_result and "session_id=" in checkout_result["checkout_url"]:
            session_id = checkout_result["checkout_url"].split("session_id=")[1].split("&")[0]
            test_results["stripe_session_id"] = session_id
            
            # Test payment status endpoint
            response = requests.get(f"{API_URL}/payments/checkout/status/{session_id}")
            if response.status_code != 200:
                return log_test_result("Payment Status", False, f"Failed: {response.text}")
            
            payment_status = response.json()
            if "payment_status" not in payment_status:
                return log_test_result("Payment Status", False, "No payment status in response")
            
            log_test_result("Payment Status", True, f"Status: {payment_status['payment_status']}")
        
        return log_test_result("Checkout with Card", True, f"Order created: {test_results.get('order_id_card')}")
    except Exception as e:
        return log_test_result("Checkout with Card", False, f"Exception: {str(e)}")

def test_checkout_with_bank_transfer():
    """Test checkout process with bank transfer payment"""
    if "product_id" not in test_results:
        return log_test_result("Checkout with Bank Transfer", False, "No product ID available")
    
    try:
        # Create a new session ID for this test
        bank_session_id = str(uuid.uuid4())
        
        # Add product to cart
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 1
        }
        
        response = requests.post(f"{API_URL}/cart/{bank_session_id}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Add to Cart for Bank Transfer Checkout", False, f"Failed: {response.text}")
        
        # Create checkout with bank transfer payment
        checkout_data = {
            "cart_id": bank_session_id,
            "shipping_address": "Rua de Teste, 123, Lisboa",
            "phone": "+351912345678",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "bank_transfer",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data)
        if response.status_code != 200:
            return log_test_result("Checkout with Bank Transfer", False, f"Failed: {response.text}")
        
        checkout_result = response.json()
        if "order_id" not in checkout_result:
            return log_test_result("Checkout with Bank Transfer", False, "No order ID in response")
        
        test_results["order_id_bank"] = checkout_result["order_id"]
        
        # Check if cart was cleared after checkout
        response = requests.get(f"{API_URL}/cart/{bank_session_id}")
        if response.status_code != 200:
            return log_test_result("Cart Cleared After Bank Transfer Checkout", False, f"Failed to get cart: {response.text}")
        
        cart_after_checkout = response.json()
        if cart_after_checkout.get("items") and len(cart_after_checkout["items"]) > 0:
            return log_test_result("Cart Cleared After Bank Transfer Checkout", False, "Cart not cleared after checkout")
        
        log_test_result("Cart Cleared After Bank Transfer Checkout", True, "Cart was cleared after bank transfer checkout")
        
        return log_test_result("Checkout with Bank Transfer", True, f"Order created: {test_results.get('order_id_bank')}")
    except Exception as e:
        return log_test_result("Checkout with Bank Transfer", False, f"Exception: {str(e)}")

def test_checkout_with_cash_on_delivery():
    """Test checkout process with cash on delivery payment"""
    if "product_id" not in test_results:
        return log_test_result("Checkout with Cash on Delivery", False, "No product ID available")
    
    try:
        # Create a new session ID for this test
        cod_session_id = str(uuid.uuid4())
        
        # Add product to cart
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 1
        }
        
        response = requests.post(f"{API_URL}/cart/{cod_session_id}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Add to Cart for COD Checkout", False, f"Failed: {response.text}")
        
        # Create checkout with cash on delivery payment
        checkout_data = {
            "cart_id": cod_session_id,
            "shipping_address": "Rua de Teste, 123, Lisboa",
            "phone": "+351912345678",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "cash_on_delivery",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data)
        if response.status_code != 200:
            return log_test_result("Checkout with Cash on Delivery", False, f"Failed: {response.text}")
        
        checkout_result = response.json()
        if "order_id" not in checkout_result:
            return log_test_result("Checkout with Cash on Delivery", False, "No order ID in response")
        
        test_results["order_id_cod"] = checkout_result["order_id"]
        
        # Check if cart was cleared after checkout
        response = requests.get(f"{API_URL}/cart/{cod_session_id}")
        if response.status_code != 200:
            return log_test_result("Cart Cleared After COD Checkout", False, f"Failed to get cart: {response.text}")
        
        cart_after_checkout = response.json()
        if cart_after_checkout.get("items") and len(cart_after_checkout["items"]) > 0:
            return log_test_result("Cart Cleared After COD Checkout", False, "Cart not cleared after checkout")
        
        log_test_result("Cart Cleared After COD Checkout", True, "Cart was cleared after COD checkout")
        
        return log_test_result("Checkout with Cash on Delivery", True, f"Order created: {test_results.get('order_id_cod')}")
    except Exception as e:
        return log_test_result("Checkout with Cash on Delivery", False, f"Exception: {str(e)}")

def test_payment_status():
    """Test payment status endpoint"""
    if "stripe_session_id" not in test_results:
        return log_test_result("Payment Status", False, "No Stripe session ID available")
    
    try:
        response = requests.get(f"{API_URL}/payments/checkout/status/{test_results['stripe_session_id']}")
        if response.status_code != 200:
            return log_test_result("Payment Status", False, f"Failed: {response.text}")
        
        payment_status = response.json()
        if "payment_status" not in payment_status:
            return log_test_result("Payment Status", False, "No payment status in response")
        
        return log_test_result("Payment Status", True, f"Status: {payment_status['payment_status']}")
    except Exception as e:
        return log_test_result("Payment Status", False, f"Exception: {str(e)}")

#=============================================================================
# 6. CHAT SYSTEM
#=============================================================================

def test_create_chat_session():
    """Test creating a chat session"""
    if "auth_token" not in test_results:
        return log_test_result("Create Chat Session", False, "No auth token available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Create chat session
        session_data = {
            "subject": "Test Chat Session"
        }
        
        response = requests.post(f"{API_URL}/chat/sessions", json=session_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Chat Session", False, f"Failed: {response.text}")
        
        session = response.json()
        if not session or "id" not in session:
            return log_test_result("Create Chat Session", False, "Invalid session data")
        
        test_results["chat_session_id"] = session["id"]
        return log_test_result("Create Chat Session", True, f"Created session: {session['id']}")
    except Exception as e:
        return log_test_result("Create Chat Session", False, f"Exception: {str(e)}")

def test_list_chat_sessions():
    """Test listing chat sessions"""
    if "auth_token" not in test_results:
        return log_test_result("List Chat Sessions", False, "No auth token available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Create a session if none exists
        if "chat_session_id" not in test_results:
            test_create_chat_session()
        
        # List sessions
        response = requests.get(f"{API_URL}/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("List Chat Sessions", False, f"Failed: {response.text}")
        
        sessions = response.json()
        if not isinstance(sessions, list):
            return log_test_result("List Chat Sessions", False, "Invalid sessions data")
        
        return log_test_result("List Chat Sessions", True, f"Found {len(sessions)} sessions")
    except Exception as e:
        return log_test_result("List Chat Sessions", False, f"Exception: {str(e)}")

def test_send_chat_message():
    """Test sending a chat message"""
    if "auth_token" not in test_results or "chat_session_id" not in test_results:
        return log_test_result("Send Chat Message", False, "No auth token or chat session ID available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Send message
        message_data = {
            "message": "This is a test message"
        }
        
        response = requests.post(
            f"{API_URL}/chat/sessions/{test_results['chat_session_id']}/messages", 
            json=message_data, 
            headers=headers
        )
        if response.status_code != 200:
            return log_test_result("Send Chat Message", False, f"Failed: {response.text}")
        
        message = response.json()
        if not message or "id" not in message:
            return log_test_result("Send Chat Message", False, "Invalid message data")
        
        test_results["chat_message_id"] = message["id"]
        return log_test_result("Send Chat Message", True, "Message sent successfully")
    except Exception as e:
        return log_test_result("Send Chat Message", False, f"Exception: {str(e)}")

def test_list_chat_messages():
    """Test listing chat messages"""
    if "auth_token" not in test_results or "chat_session_id" not in test_results:
        return log_test_result("List Chat Messages", False, "No auth token or chat session ID available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Send a message if none exists
        if "chat_message_id" not in test_results:
            test_send_chat_message()
        
        # List messages
        response = requests.get(
            f"{API_URL}/chat/sessions/{test_results['chat_session_id']}/messages", 
            headers=headers
        )
        if response.status_code != 200:
            return log_test_result("List Chat Messages", False, f"Failed: {response.text}")
        
        messages = response.json()
        if not isinstance(messages, list):
            return log_test_result("List Chat Messages", False, "Invalid messages data")
        
        return log_test_result("List Chat Messages", True, f"Found {len(messages)} messages")
    except Exception as e:
        return log_test_result("List Chat Messages", False, f"Exception: {str(e)}")

def test_close_chat_session():
    """Test closing a chat session"""
    if "auth_token" not in test_results or "chat_session_id" not in test_results:
        return log_test_result("Close Chat Session", False, "No auth token or chat session ID available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Close session
        response = requests.put(
            f"{API_URL}/chat/sessions/{test_results['chat_session_id']}/close", 
            headers=headers
        )
        if response.status_code != 200:
            return log_test_result("Close Chat Session", False, f"Failed: {response.text}")
        
        # Verify session is closed
        response = requests.get(f"{API_URL}/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Verify Closed Session", False, f"Failed to get sessions: {response.text}")
        
        sessions = response.json()
        closed_session = next((s for s in sessions if s["id"] == test_results["chat_session_id"]), None)
        
        if not closed_session:
            return log_test_result("Verify Closed Session", False, "Session not found after closing")
        
        if closed_session.get("status") != "closed":
            return log_test_result("Verify Closed Session", False, f"Session not marked as closed: {closed_session.get('status')}")
        
        return log_test_result("Close Chat Session", True, "Session closed successfully")
    except Exception as e:
        return log_test_result("Close Chat Session", False, f"Exception: {str(e)}")

#=============================================================================
# 7. ADMIN FEATURES
#=============================================================================

def test_admin_login():
    """Test admin login"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store admin token
            test_results["admin_token"] = response_data["access_token"]
            return log_test_result("Admin Login", True, "Admin login successful")
        else:
            return log_test_result("Admin Login", False, f"Failed to login as admin: {response.text}")
    except Exception as e:
        return log_test_result("Admin Login", False, f"Exception: {str(e)}")

def test_admin_dashboard():
    """Test admin dashboard"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Dashboard", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        response = requests.get(f"{API_URL}/admin/dashboard", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Dashboard", False, f"Failed: {response.text}")
        
        dashboard = response.json()
        if "stats" not in dashboard or "recent_orders" not in dashboard:
            return log_test_result("Admin Dashboard", False, "Invalid dashboard data")
        
        return log_test_result("Admin Dashboard", True, "Dashboard retrieved successfully")
    except Exception as e:
        return log_test_result("Admin Dashboard", False, f"Exception: {str(e)}")

def test_admin_orders():
    """Test admin orders list"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Orders List", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        response = requests.get(f"{API_URL}/admin/orders", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Orders List", False, f"Failed: {response.text}")
        
        orders = response.json()
        if not isinstance(orders, list):
            return log_test_result("Admin Orders List", False, "Invalid orders data")
        
        # Store an order ID for later tests if available
        if orders:
            test_results["admin_order_id"] = orders[0]["id"]
        
        return log_test_result("Admin Orders List", True, f"Found {len(orders)} orders")
    except Exception as e:
        return log_test_result("Admin Orders List", False, f"Exception: {str(e)}")

def test_admin_update_order_status():
    """Test admin order status update"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Order Status Update", False, "Admin login required")
    
    # Get an order ID if not available
    if "admin_order_id" not in test_results:
        test_admin_orders()
        if "admin_order_id" not in test_results:
            # Create an order if none exists
            if "product_id" in test_results:
                # Create a new checkout
                checkout_data = {
                    "cart_id": SESSION_ID,
                    "shipping_address": "Rua de Teste, 123, Lisboa",
                    "phone": "+351912345678",
                    "nif": "501964843",  # Valid Portuguese NIF
                    "payment_method": "bank_transfer",
                    "shipping_method": "standard",
                    "origin_url": BACKEND_URL
                }
                
                # Add product to cart
                cart_item = {
                    "product_id": test_results["product_id"],
                    "quantity": 1
                }
                
                requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
                
                # Create checkout
                response = requests.post(f"{API_URL}/checkout", json=checkout_data)
                if response.status_code == 200:
                    checkout_result = response.json()
                    if "order_id" in checkout_result:
                        test_results["admin_order_id"] = checkout_result["order_id"]
                
                # Get orders again
                test_admin_orders()
    
    if "admin_order_id" not in test_results:
        return log_test_result("Admin Order Status Update", False, "No order ID available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        order_id = test_results["admin_order_id"]
        
        # Test valid status update
        valid_statuses = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
        
        for status in valid_statuses:
            response = requests.put(
                f"{API_URL}/admin/orders/{order_id}/status?status={status}", 
                headers=headers
            )
            
            if response.status_code != 200:
                log_test_result(f"Admin Update Order Status to {status}", False, f"Failed: {response.text}")
                continue
            
            # Verify status was updated
            response = requests.get(f"{API_URL}/admin/orders", headers=headers)
            if response.status_code != 200:
                log_test_result(f"Admin Get Orders After Status Update to {status}", False, f"Failed: {response.text}")
                continue
            
            orders = response.json()
            updated_order = next((o for o in orders if o["id"] == order_id), None)
            
            if not updated_order:
                log_test_result(f"Admin Update Order Status to {status}", False, "Order not found after update")
                continue
                
            if updated_order.get("order_status") != status:
                log_test_result(f"Admin Update Order Status to {status}", False, f"Order status not updated to {status}")
                continue
            
            log_test_result(f"Admin Update Order Status to {status}", True, f"Successfully updated order status to {status}")
        
        # Test invalid status update
        response = requests.put(
            f"{API_URL}/admin/orders/{order_id}/status?status=invalid_status", 
            headers=headers
        )
        
        if response.status_code == 400:
            log_test_result("Admin Update Order Status with Invalid Status", True, "Correctly rejected invalid status")
        else:
            log_test_result("Admin Update Order Status with Invalid Status", False, f"Did not reject invalid status: {response.status_code}, {response.text}")
        
        return log_test_result("Admin Order Status Update", True, "Successfully tested order status updates")
    except Exception as e:
        return log_test_result("Admin Order Status Update", False, f"Exception: {str(e)}")

def test_admin_products():
    """Test admin products management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Products Management", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # List products
        response = requests.get(f"{API_URL}/admin/products", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Products List", False, f"Failed: {response.text}")
        
        products = response.json()
        if not isinstance(products, list):
            return log_test_result("Admin Products List", False, "Invalid products data")
        
        log_test_result("Admin Products List", True, f"Found {len(products)} products")
        
        # Create a new product
        # Create a sample base64 image (very small transparent pixel)
        sample_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        
        new_product = {
            "name": f"Test Product {uuid.uuid4().hex[:8]}",
            "description": "This is a test product",
            "category": "geek",
            "price": 29.99,
            "subscription_prices": {
                "1_month": 29.99,
                "3_months": 26.99,
                "6_months": 24.99,
                "12_months": 22.99
            },
            "image_url": "https://example.com/fallback-image.jpg",
            "image_base64": sample_base64,
            "stock_quantity": 50,
            "featured": True
        }
        
        response = requests.post(f"{API_URL}/admin/products", json=new_product, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Product", False, f"Failed: {response.text}")
        
        created_product = response.json()
        if "id" not in created_product:
            return log_test_result("Admin Create Product", False, "No product ID in response")
        
        product_id = created_product["id"]
        test_results["admin_product_id"] = product_id
        
        log_test_result("Admin Create Product", True, f"Created product: {product_id}")
        
        # Update the product
        updated_product = {
            "name": f"Updated Test Product {uuid.uuid4().hex[:8]}",
            "description": "This is an updated test product",
            "category": "geek",
            "price": 39.99,
            "subscription_prices": {
                "1_month": 39.99,
                "3_months": 36.99,
                "6_months": 34.99,
                "12_months": 32.99
            },
            "image_url": "https://example.com/updated-image.jpg",
            "stock_quantity": 100,
            "featured": False
        }
        
        response = requests.put(f"{API_URL}/admin/products/{product_id}", json=updated_product, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Update Product", False, f"Failed: {response.text}")
        
        log_test_result("Admin Update Product", True, f"Updated product: {product_id}")
        
        # Delete the product
        response = requests.delete(f"{API_URL}/admin/products/{product_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Delete Product", False, f"Failed: {response.text}")
        
        log_test_result("Admin Delete Product", True, f"Deleted product: {product_id}")
        
        return log_test_result("Admin Products Management", True, "Successfully tested products management")
    except Exception as e:
        return log_test_result("Admin Products Management", False, f"Exception: {str(e)}")

def test_admin_coupons():
    """Test admin coupons management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Coupons Management", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # List coupons
        response = requests.get(f"{API_URL}/admin/coupons", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Coupons List", False, f"Failed: {response.text}")
        
        coupons = response.json()
        if not isinstance(coupons, list):
            return log_test_result("Admin Coupons List", False, "Invalid coupons data")
        
        log_test_result("Admin Coupons List", True, f"Found {len(coupons)} coupons")
        
        # Create a new coupon
        coupon_code = f"TEST{uuid.uuid4().hex[:8].upper()}"
        
        coupon_data = {
            "code": coupon_code,
            "description": "Test Coupon for Admin Management",
            "discount_type": "percentage",
            "discount_value": 20.0,
            "min_order_value": 30.0,
            "max_uses": 10,
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "applicable_categories": [],
            "applicable_products": []
        }
        
        response = requests.post(f"{API_URL}/admin/coupons", json=coupon_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Coupon", False, f"Failed: {response.text}")
        
        created_coupon = response.json()
        if "id" not in created_coupon:
            return log_test_result("Admin Create Coupon", False, "No coupon ID in response")
        
        coupon_id = created_coupon["id"]
        test_results["admin_coupon_id"] = coupon_id
        
        log_test_result("Admin Create Coupon", True, f"Created coupon: {coupon_id}")
        
        # Update the coupon
        updated_coupon_data = {
            "code": coupon_code,  # Keep the same code
            "description": "Updated Test Coupon",
            "discount_type": "fixed",
            "discount_value": 10.0,
            "min_order_value": 50.0,
            "max_uses": 5,
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=60)).isoformat(),
            "applicable_categories": [],
            "applicable_products": []
        }
        
        response = requests.put(f"{API_URL}/admin/coupons/{coupon_id}", json=updated_coupon_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Update Coupon", False, f"Failed: {response.text}")
        
        log_test_result("Admin Update Coupon", True, f"Updated coupon: {coupon_id}")
        
        # Deactivate the coupon
        response = requests.delete(f"{API_URL}/admin/coupons/{coupon_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Deactivate Coupon", False, f"Failed: {response.text}")
        
        log_test_result("Admin Deactivate Coupon", True, f"Deactivated coupon: {coupon_id}")
        
        return log_test_result("Admin Coupons Management", True, "Successfully tested coupons management")
    except Exception as e:
        return log_test_result("Admin Coupons Management", False, f"Exception: {str(e)}")

def test_admin_promotions():
    """Test admin promotions management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Promotions Management", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # List promotions
        response = requests.get(f"{API_URL}/admin/promotions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Promotions List", False, f"Failed: {response.text}")
        
        promotions = response.json()
        if not isinstance(promotions, list):
            return log_test_result("Admin Promotions List", False, "Invalid promotions data")
        
        log_test_result("Admin Promotions List", True, f"Found {len(promotions)} promotions")
        
        # Create a new promotion
        promotion_data = {
            "name": f"Test Promotion {uuid.uuid4().hex[:8]}",
            "description": "Test Promotion for Admin Management",
            "discount_type": "percentage",
            "discount_value": 25.0,
            "applicable_categories": [],
            "applicable_products": [],
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        response = requests.post(f"{API_URL}/admin/promotions", json=promotion_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Promotion", False, f"Failed: {response.text}")
        
        created_promotion = response.json()
        if "id" not in created_promotion:
            return log_test_result("Admin Create Promotion", False, "No promotion ID in response")
        
        promotion_id = created_promotion["id"]
        test_results["admin_promotion_id"] = promotion_id
        
        log_test_result("Admin Create Promotion", True, f"Created promotion: {promotion_id}")
        
        # Update the promotion
        updated_promotion_data = {
            "name": f"Updated Test Promotion {uuid.uuid4().hex[:8]}",
            "description": "Updated Test Promotion",
            "discount_type": "fixed",
            "discount_value": 15.0,
            "applicable_categories": [],
            "applicable_products": [],
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=60)).isoformat()
        }
        
        response = requests.put(f"{API_URL}/admin/promotions/{promotion_id}", json=updated_promotion_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Update Promotion", False, f"Failed: {response.text}")
        
        log_test_result("Admin Update Promotion", True, f"Updated promotion: {promotion_id}")
        
        # Deactivate the promotion
        response = requests.delete(f"{API_URL}/admin/promotions/{promotion_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Deactivate Promotion", False, f"Failed: {response.text}")
        
        log_test_result("Admin Deactivate Promotion", True, f"Deactivated promotion: {promotion_id}")
        
        return log_test_result("Admin Promotions Management", True, "Successfully tested promotions management")
    except Exception as e:
        return log_test_result("Admin Promotions Management", False, f"Exception: {str(e)}")

def test_admin_categories():
    """Test admin categories management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Categories Management", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # List categories
        response = requests.get(f"{API_URL}/admin/categories", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Categories List", False, f"Failed: {response.text}")
        
        categories = response.json()
        if not isinstance(categories, list):
            return log_test_result("Admin Categories List", False, "Invalid categories data")
        
        log_test_result("Admin Categories List", True, f"Found {len(categories)} categories")
        
        # Create a new category
        category_data = {
            "name": f"Test Category {uuid.uuid4().hex[:8]}",
            "description": "Test Category for Admin Management",
            "emoji": "🧪",
            "color": "#" + ''.join(random.choices('0123456789ABCDEF', k=6))
        }
        
        response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Category", False, f"Failed: {response.text}")
        
        created_category = response.json()
        if "id" not in created_category:
            return log_test_result("Admin Create Category", False, "No category ID in response")
        
        category_id = created_category["id"]
        test_results["admin_category_id"] = category_id
        
        log_test_result("Admin Create Category", True, f"Created category: {category_id}")
        
        return log_test_result("Admin Categories Management", True, "Successfully tested categories management")
    except Exception as e:
        return log_test_result("Admin Categories Management", False, f"Exception: {str(e)}")

def test_admin_users():
    """Test admin users management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Users Management", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # List users
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Users List", False, f"Failed: {response.text}")
        
        users = response.json()
        if not isinstance(users, list):
            return log_test_result("Admin Users List", False, "Invalid users data")
        
        log_test_result("Admin Users List", True, f"Found {len(users)} users")
        
        # Create a new admin user
        admin_data = {
            "email": f"test_admin_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Test Admin User"
        }
        
        response = requests.post(f"{API_URL}/admin/users/make-admin", json=admin_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Make User Admin", False, f"Failed: {response.text}")
        
        log_test_result("Admin Make User Admin", True, f"Created admin user: {admin_data['email']}")
        
        # Get the user ID of the new admin
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Get Users After Creation", False, f"Failed: {response.text}")
        
        users = response.json()
        new_admin = next((u for u in users if u["email"] == admin_data["email"]), None)
        
        if not new_admin:
            return log_test_result("Admin Find New Admin User", False, "New admin user not found")
        
        admin_user_id = new_admin["id"]
        test_results["admin_user_id"] = admin_user_id
        
        # Remove admin status
        response = requests.delete(f"{API_URL}/admin/users/{admin_user_id}/remove-admin", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Remove Admin Status", False, f"Failed: {response.text}")
        
        log_test_result("Admin Remove Admin Status", True, f"Removed admin status from user: {admin_data['email']}")
        
        return log_test_result("Admin Users Management", True, "Successfully tested users management")
    except Exception as e:
        return log_test_result("Admin Users Management", False, f"Exception: {str(e)}")

def test_admin_chat():
    """Test admin chat management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Chat Management", False, "Admin login required")
    
    # Create a chat session if none exists
    if "chat_session_id" not in test_results:
        if "auth_token" not in test_results:
            test_register()
        test_create_chat_session()
        test_send_chat_message()
    
    if "chat_session_id" not in test_results:
        return log_test_result("Admin Chat Management", False, "No chat session available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # List all chat sessions
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Chat Sessions List", False, f"Failed: {response.text}")
        
        sessions = response.json()
        if not isinstance(sessions, list):
            return log_test_result("Admin Chat Sessions List", False, "Invalid sessions data")
        
        log_test_result("Admin Chat Sessions List", True, f"Found {len(sessions)} sessions")
        
        # Check if user info and subject are included
        if sessions:
            session = sessions[0]
            if "user_name" not in session or "user_email" not in session:
                log_test_result("Admin Chat User Info", False, "User info not included in session data")
            else:
                log_test_result("Admin Chat User Info", True, "User info included in session data")
            
            if "subject" not in session:
                log_test_result("Admin Chat Subject", False, "Subject not included in session data")
            else:
                log_test_result("Admin Chat Subject", True, "Subject included in session data")
        
        # Find our test session
        test_session = next((s for s in sessions if s["id"] == test_results["chat_session_id"]), None)
        
        if not test_session:
            # Try to find any active session
            active_sessions = [s for s in sessions if s["status"] == "active" or s["status"] == "pending"]
            if active_sessions:
                test_session = active_sessions[0]
                test_results["admin_chat_session_id"] = test_session["id"]
        else:
            test_results["admin_chat_session_id"] = test_session["id"]
        
        if "admin_chat_session_id" not in test_results:
            return log_test_result("Admin Chat Session Assignment", False, "No active chat session available")
        
        # Assign session to admin
        response = requests.put(
            f"{API_URL}/admin/chat/sessions/{test_results['admin_chat_session_id']}/assign", 
            headers=headers
        )
        if response.status_code != 200:
            return log_test_result("Admin Assign Chat Session", False, f"Failed: {response.text}")
        
        log_test_result("Admin Assign Chat Session", True, "Session assigned to admin successfully")
        
        # Create another session for reject test
        if "auth_token" in test_results:
            user_headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
            
            session_data = {
                "subject": "Test Chat Session for Rejection"
            }
            
            response = requests.post(f"{API_URL}/chat/sessions", json=session_data, headers=user_headers)
            if response.status_code == 200:
                reject_session = response.json()
                if "id" in reject_session:
                    test_results["reject_chat_session_id"] = reject_session["id"]
                    
                    # Send a message
                    message_data = {
                        "message": "This is a test message for rejection"
                    }
                    
                    requests.post(
                        f"{API_URL}/chat/sessions/{reject_session['id']}/messages", 
                        json=message_data, 
                        headers=user_headers
                    )
        
        # Get sessions again to find the new one
        if "reject_chat_session_id" not in test_results:
            response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
            if response.status_code == 200:
                sessions = response.json()
                # Find a session that's not the one we already assigned
                for session in sessions:
                    if session["id"] != test_results["admin_chat_session_id"] and (session["status"] == "active" or session["status"] == "pending"):
                        test_results["reject_chat_session_id"] = session["id"]
                        break
        
        # Reject a session if we have one to reject
        if "reject_chat_session_id" in test_results:
            response = requests.put(
                f"{API_URL}/admin/chat/sessions/{test_results['reject_chat_session_id']}/reject", 
                headers=headers
            )
            if response.status_code != 200:
                return log_test_result("Admin Reject Chat Session", False, f"Failed: {response.text}")
            
            log_test_result("Admin Reject Chat Session", True, "Session rejected successfully")
        else:
            log_test_result("Admin Reject Chat Session", False, "No session available for rejection test")
        
        return log_test_result("Admin Chat Management", True, "Successfully tested admin chat management")
    except Exception as e:
        return log_test_result("Admin Chat Management", False, f"Exception: {str(e)}")

def test_admin_emails():
    """Test admin email sending"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Email Sending", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Test discount email
        discount_params = {
            "user_email": TEST_USER["email"],
            "user_name": TEST_USER["name"],
            "coupon_code": "TESTDISCOUNT",
            "discount_value": 15.0,
            "discount_type": "percentage",
            "expiry_date": "31/12/2024"
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-discount", params=discount_params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Send Discount Email", False, f"Failed: {response.text}")
        
        log_test_result("Admin Send Discount Email", True, "Discount email sent successfully")
        
        # Test birthday email
        birthday_params = {
            "user_email": TEST_USER["email"],
            "user_name": TEST_USER["name"],
            "coupon_code": "BIRTHDAY2024",
            "discount_value": 20.0
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-birthday", params=birthday_params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Send Birthday Email", False, f"Failed: {response.text}")
        
        log_test_result("Admin Send Birthday Email", True, "Birthday email sent successfully")
        
        return log_test_result("Admin Email Sending", True, "Successfully tested admin email sending")
    except Exception as e:
        return log_test_result("Admin Email Sending", False, f"Exception: {str(e)}")

def run_comprehensive_tests():
    """Run all tests and return results"""
    logger.info("Starting comprehensive backend tests for Mystery Box Store API")
    
    # 1. AUTHENTICATION AND USERS
    logger.info("\n=== TESTING AUTHENTICATION AND USERS ===")
    test_register()
    test_login()
    test_google_auth()
    test_verify_token()
    test_update_profile()
    test_get_user_orders()
    
    # 2. PRODUCTS AND CATEGORIES
    logger.info("\n=== TESTING PRODUCTS AND CATEGORIES ===")
    test_list_products()
    test_get_product_details()
    test_list_categories()
    
    # 3. CART SYSTEM
    logger.info("\n=== TESTING CART SYSTEM ===")
    test_get_cart()
    test_add_to_cart()
    test_remove_from_cart()
    test_apply_coupon()
    test_remove_coupon()
    
    # 4. COUPONS
    logger.info("\n=== TESTING COUPONS ===")
    test_validate_coupon()
    
    # 5. CHECKOUT AND PAYMENTS
    logger.info("\n=== TESTING CHECKOUT AND PAYMENTS ===")
    test_checkout_with_card()
    test_checkout_with_bank_transfer()
    test_checkout_with_cash_on_delivery()
    test_payment_status()
    
    # 6. CHAT SYSTEM
    logger.info("\n=== TESTING CHAT SYSTEM ===")
    test_create_chat_session()
    test_list_chat_sessions()
    test_send_chat_message()
    test_list_chat_messages()
    test_close_chat_session()
    
    # 7. ADMIN FEATURES
    logger.info("\n=== TESTING ADMIN FEATURES ===")
    test_admin_login()
    test_admin_dashboard()
    test_admin_orders()
    test_admin_update_order_status()
    test_admin_products()
    test_admin_coupons()
    test_admin_promotions()
    test_admin_categories()
    test_admin_users()
    test_admin_chat()
    test_admin_emails()
    
    # Print summary
    logger.info("\n=== COMPREHENSIVE TEST SUMMARY ===")
    passed = sum(1 for result in test_results.values() if isinstance(result, dict) and result.get("success"))
    failed = sum(1 for result in test_results.values() if isinstance(result, dict) and not result.get("success"))
    logger.info(f"PASSED: {passed}, FAILED: {failed}")
    
    for test_name, result in test_results.items():
        if isinstance(result, dict) and "success" in result:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            logger.info(f"{status}: {test_name}")
            if result.get("message"):
                logger.info(f"  - {result['message']}")
    
    return test_results

if __name__ == "__main__":
    run_comprehensive_tests()