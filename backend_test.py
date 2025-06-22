import requests
import json
import uuid
import time
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"

# Test data
TEST_USER = {
    "email": f"test_user_{uuid.uuid4()}@example.com",
    "name": "Test User",
    "password": "Test@123"
}

ADMIN_USER = {
    "email": "eduardocorreia3344@gmail.com",
    "password": "admin123"
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

def test_admin_login():
    """Test admin login"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store admin token
            test_results["admin_token"] = response_data["access_token"]
            return log_test_result("Admin Login", True)
        else:
            return log_test_result("Admin Login", False, f"Failed to login as admin: {response.text}")
    except Exception as e:
        return log_test_result("Admin Login", False, f"Exception: {str(e)}")

def test_verify_token():
    """Test JWT token verification"""
    if "auth_token" not in test_results:
        return log_test_result("Verify Token", False, "No auth token available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        response_data = response.json()
        
        if response.status_code == 200 and "email" in response_data:
            return log_test_result("Verify Token", True)
        else:
            return log_test_result("Verify Token", False, f"Failed to verify token: {response.text}")
    except Exception as e:
        return log_test_result("Verify Token", False, f"Exception: {str(e)}")

def test_list_products():
    """Test listing products"""
    try:
        # Test without filters
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("List Products", False, f"Failed to list products: {response.text}")
        
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
        
        return log_test_result("List Categories", True, f"Found {len(categories)} categories")
    except Exception as e:
        return log_test_result("List Categories", False, f"Exception: {str(e)}")

def test_cart_operations():
    """Test cart operations"""
    if "product_id" not in test_results:
        return log_test_result("Cart Operations", False, "No product ID available")
    
    try:
        # Get cart
        response = requests.get(f"{API_URL}/cart/{SESSION_ID}")
        if response.status_code != 200:
            return log_test_result("Get Cart", False, f"Failed: {response.text}")
        
        cart = response.json()
        if not cart or not isinstance(cart, dict) or "session_id" not in cart:
            return log_test_result("Get Cart", False, "Invalid cart data")
        
        # Add product to cart
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
        
        # Remove product from cart
        response = requests.delete(
            f"{API_URL}/cart/{SESSION_ID}/remove/{test_results['product_id']}?subscription_type=1_month"
        )
        if response.status_code != 200:
            return log_test_result("Remove from Cart", False, f"Failed: {response.text}")
        
        cart_after_remove = response.json()
        if any(item["product_id"] == test_results["product_id"] for item in cart_after_remove.get("items", [])):
            return log_test_result("Remove from Cart", False, "Product still in cart after removal")
        
        # Add product back for coupon tests
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Re-add to Cart", False, f"Failed: {response.text}")
        
        return log_test_result("Cart Operations", True)
    except Exception as e:
        return log_test_result("Cart Operations", False, f"Exception: {str(e)}")

def test_coupon_operations():
    """Test coupon operations"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Coupon Operations", False, "Admin login required")
    
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
            return log_test_result("Create Coupon", False, f"Failed: {response.text}")
        
        # Validate coupon
        response = requests.get(f"{API_URL}/coupons/validate/{coupon_code}")
        if response.status_code != 200:
            return log_test_result("Validate Coupon", False, f"Failed: {response.text}")
        
        # Apply coupon to cart
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code={coupon_code}")
        if response.status_code != 200:
            return log_test_result("Apply Coupon", False, f"Failed: {response.text}")
        
        cart_with_coupon = response.json()
        if not cart_with_coupon.get("coupon_code"):
            return log_test_result("Apply Coupon", False, "Coupon not applied to cart")
        
        # Remove coupon from cart
        response = requests.delete(f"{API_URL}/cart/{SESSION_ID}/remove-coupon")
        if response.status_code != 200:
            return log_test_result("Remove Coupon", False, f"Failed: {response.text}")
        
        cart_without_coupon = response.json()
        if cart_without_coupon.get("coupon_code"):
            return log_test_result("Remove Coupon", False, "Coupon still applied after removal")
        
        return log_test_result("Coupon Operations", True)
    except Exception as e:
        return log_test_result("Coupon Operations", False, f"Exception: {str(e)}")

def test_checkout():
    """Test checkout process"""
    if "product_id" not in test_results:
        return log_test_result("Checkout", False, "No product ID available")
    
    try:
        # Ensure cart has items
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 1
        }
        
        requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        
        # Create checkout
        checkout_data = {
            "cart_id": SESSION_ID,
            "shipping_address": "Rua de Teste, 123, Lisboa",
            "phone": "+351912345678",
            "nif": "PT123456789",  # This is not a valid NIF, testing validation
            "payment_method": "card",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data)
        
        # Test NIF validation
        if response.status_code == 400 and "NIF inválido" in response.text:
            log_test_result("NIF Validation", True, "Correctly rejected invalid NIF")
        else:
            log_test_result("NIF Validation", False, "Failed to validate NIF")
        
        # Try with valid NIF
        checkout_data["nif"] = "PT501964843"  # Valid Portuguese NIF
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data)
        if response.status_code != 200:
            return log_test_result("Checkout", False, f"Failed: {response.text}")
        
        checkout_result = response.json()
        if "order_id" not in checkout_result:
            return log_test_result("Checkout", False, "No order ID in response")
        
        test_results["order_id"] = checkout_result["order_id"]
        
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
        
        return log_test_result("Checkout", True, f"Order created: {test_results.get('order_id')}")
    except Exception as e:
        return log_test_result("Checkout", False, f"Exception: {str(e)}")

def test_admin_features():
    """Test admin features"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Features", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Test dashboard
        response = requests.get(f"{API_URL}/admin/dashboard", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Dashboard", False, f"Failed: {response.text}")
        
        dashboard = response.json()
        if "stats" not in dashboard:
            return log_test_result("Admin Dashboard", False, "No stats in dashboard")
        
        # Test user management
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin User List", False, f"Failed: {response.text}")
        
        # Test coupon management
        response = requests.get(f"{API_URL}/admin/coupons", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Coupon List", False, f"Failed: {response.text}")
        
        # Test promotion management
        response = requests.get(f"{API_URL}/admin/promotions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Promotion List", False, f"Failed: {response.text}")
        
        # Test make user admin (with a temporary user)
        temp_admin = {
            "email": f"temp_admin_{uuid.uuid4()}@example.com",
            "name": "Temporary Admin"
        }
        
        response = requests.post(f"{API_URL}/admin/users/make-admin", json=temp_admin, headers=headers)
        if response.status_code != 200:
            return log_test_result("Make User Admin", False, f"Failed: {response.text}")
        
        # We can't test remove admin without knowing the user ID, but the endpoint exists
        
        return log_test_result("Admin Features", True)
    except Exception as e:
        return log_test_result("Admin Features", False, f"Exception: {str(e)}")

def test_email_endpoints():
    """Test email sending endpoints"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Email Endpoints", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Test discount email
        params = {
            "user_email": TEST_USER["email"],
            "user_name": TEST_USER["name"],
            "coupon_code": "TESTDISCOUNT",
            "discount_value": 15.0,
            "discount_type": "percentage",
            "expiry_date": "31/12/2024"
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-discount", params=params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Send Discount Email", False, f"Failed: {response.text}")
        
        # Test birthday email
        params = {
            "user_email": TEST_USER["email"],
            "user_name": TEST_USER["name"],
            "coupon_code": "BIRTHDAY2024",
            "discount_value": 20.0
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-birthday", params=params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Send Birthday Email", False, f"Failed: {response.text}")
        
        return log_test_result("Email Endpoints", True)
    except Exception as e:
        return log_test_result("Email Endpoints", False, f"Exception: {str(e)}")

def run_all_tests():
    """Run all tests and return results"""
    logger.info("Starting backend tests for Mystery Box Store")
    
    # Authentication tests
    test_register()
    test_login()
    test_admin_login()
    test_verify_token()
    
    # Product and category tests
    test_list_products()
    test_get_product_details()
    test_list_categories()
    
    # Cart tests
    test_cart_operations()
    
    # Coupon tests
    test_coupon_operations()
    
    # Checkout tests
    test_checkout()
    
    # Admin tests
    test_admin_features()
    
    # Email tests
    test_email_endpoints()
    
    # Print summary
    logger.info("\n=== TEST SUMMARY ===")
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
    run_all_tests()