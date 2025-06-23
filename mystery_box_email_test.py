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
    "email": "edupodeptptpt@gmail.com",  # Using the provided test email
    "name": "Teste Utilizador",
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
    test_results[test_name] = {"success": success, "message": message, "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
    return success

def test_direct_email_endpoint():
    """Test the direct email endpoint"""
    try:
        # First, login as admin to get token
        admin_login_data = {
            "email": "eduardocorreia3344@gmail.com",
            "password": "admin123"
        }
        login_response = requests.post(f"{API_URL}/auth/login", json=admin_login_data)
        if login_response.status_code != 200:
            return log_test_result("Direct Email Test", False, f"Admin login failed: {login_response.text}")
        
        admin_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Try the admin discount email endpoint
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
            return log_test_result("Direct Email Test", False, f"Failed to send discount email: {response.text}")
        
        # Record the timestamp when the email was sent
        email_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        return log_test_result("Direct Email Test", True, f"Discount email sent at: {email_timestamp}")
    except Exception as e:
        return log_test_result("Direct Email Test", False, f"Exception: {str(e)}")

def test_register_welcome_email():
    """Test welcome email sent during registration"""
    try:
        # Generate a unique email to avoid conflicts with existing users
        unique_email = f"test_{int(time.time())}_{TEST_USER['email']}"
        
        # Register a new user
        user_data = {
            "email": unique_email,
            "name": TEST_USER["name"],
            "password": TEST_USER["password"]
        }
        
        response = requests.post(f"{API_URL}/auth/register", json=user_data)
        if response.status_code != 200:
            return log_test_result("Registration Welcome Email", False, f"Failed to register: {response.text}")
        
        result = response.json()
        if "access_token" not in result:
            return log_test_result("Registration Welcome Email", False, "Registration failed, no token received")
        
        # Store token for later tests
        test_results["auth_token"] = result["access_token"]
        
        return log_test_result("Registration Welcome Email", True, 
                              f"User registered successfully, welcome email should be sent to {unique_email}")
    except Exception as e:
        return log_test_result("Registration Welcome Email", False, f"Exception: {str(e)}")

def test_checkout_confirmation_email():
    """Test order confirmation email sent during checkout"""
    if "auth_token" not in test_results:
        # Register a new user if not already done
        test_register_welcome_email()
        if "auth_token" not in test_results:
            return log_test_result("Checkout Confirmation Email", False, "User registration required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Get a product to add to cart
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Checkout Confirmation Email", False, "Failed to get products")
        
        products = response.json()
        if not products:
            return log_test_result("Checkout Confirmation Email", False, "No products available")
        
        product_id = products[0]["id"]
        
        # Add product to cart
        cart_item = {
            "product_id": product_id,
            "quantity": 1
        }
        
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Checkout Confirmation Email", False, f"Failed to add product to cart: {response.text}")
        
        # Perform checkout
        checkout_data = {
            "cart_id": SESSION_ID,
            "shipping_address": "Rua de Teste, 123, Lisboa",
            "phone": "+351912345678",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "card",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Checkout Confirmation Email", False, f"Checkout failed: {response.text}")
        
        checkout_result = response.json()
        if "order_id" not in checkout_result:
            return log_test_result("Checkout Confirmation Email", False, "No order ID in response")
        
        order_id = checkout_result["order_id"]
        checkout_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        return log_test_result("Checkout Confirmation Email", True, 
                              f"Order {order_id} created at {checkout_timestamp}, confirmation email should be sent")
    except Exception as e:
        return log_test_result("Checkout Confirmation Email", False, f"Exception: {str(e)}")

def run_email_tests():
    """Run all email tests and return results"""
    logger.info("Starting email system tests for Mystery Box Store")
    
    # Test direct email endpoint
    test_direct_email_endpoint()
    
    # Test welcome email during registration
    test_register_welcome_email()
    
    # Test order confirmation email during checkout
    test_checkout_confirmation_email()
    
    # Print summary
    logger.info("\n=== EMAIL TEST SUMMARY ===")
    passed = sum(1 for result in test_results.values() if isinstance(result, dict) and result.get("success"))
    failed = sum(1 for result in test_results.values() if isinstance(result, dict) and not result.get("success"))
    logger.info(f"PASSED: {passed}, FAILED: {failed}")
    
    for test_name, result in test_results.items():
        if isinstance(result, dict) and "success" in result:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            logger.info(f"{status}: {test_name}")
            if result.get("message"):
                logger.info(f"  - {result['message']}")
            if result.get("timestamp"):
                logger.info(f"  - Timestamp: {result['timestamp']}")
    
    return test_results

if __name__ == "__main__":
    run_email_tests()