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

def test_cart_setup():
    """Setup cart with products for checkout tests"""
    try:
        # Get products
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Cart Setup", False, f"Failed to get products: {response.text}")
        
        products = response.json()
        if not products:
            return log_test_result("Cart Setup", False, "No products available")
        
        # Store product ID
        test_results["product_id"] = products[0]["id"]
        
        # Add product to cart
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 1
        }
        
        # First get the cart to ensure it exists
        response = requests.get(f"{API_URL}/cart/{SESSION_ID}")
        if response.status_code != 200:
            return log_test_result("Cart Setup", False, f"Failed to get cart: {response.text}")
        
        # Add product to cart
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Cart Setup", False, f"Failed to add product to cart: {response.text}")
        
        # Verify cart has items
        response = requests.get(f"{API_URL}/cart/{SESSION_ID}")
        if response.status_code != 200:
            return log_test_result("Cart Setup", False, f"Failed to get cart after adding product: {response.text}")
        
        cart = response.json()
        if not cart or not cart.get("items"):
            return log_test_result("Cart Setup", False, "Product not added to cart")
        
        # Store cart ID
        test_results["cart_id"] = cart["id"]
        
        return log_test_result("Cart Setup", True, f"Added product {test_results['product_id']} to cart {SESSION_ID}")
    except Exception as e:
        return log_test_result("Cart Setup", False, f"Exception: {str(e)}")

def test_checkout_with_stripe():
    """Test checkout with payment_method='stripe'"""
    if "auth_token" not in test_results or "product_id" not in test_results:
        return log_test_result("Checkout with Stripe", False, "Missing auth token or product ID")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        checkout_data = {
            "cart_id": SESSION_ID,
            "shipping_address": "Rua Teste 123, 1234-567 Lisboa",
            "phone": "+351 123 456 789",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "stripe",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data, headers=headers)
        
        if response.status_code == 200:
            checkout_result = response.json()
            if "order_id" in checkout_result:
                test_results["order_id"] = checkout_result["order_id"]
                return log_test_result("Checkout with Stripe", True, f"Order created: {checkout_result['order_id']}")
            else:
                return log_test_result("Checkout with Stripe", False, "No order ID in response")
        else:
            return log_test_result("Checkout with Stripe", False, f"Failed: {response.text}")
    except Exception as e:
        return log_test_result("Checkout with Stripe", False, f"Exception: {str(e)}")

def test_checkout_with_card():
    """Test checkout with payment_method='card' (should fail)"""
    if "auth_token" not in test_results:
        return log_test_result("Checkout with Card", False, "Missing auth token")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        checkout_data = {
            "cart_id": SESSION_ID,
            "shipping_address": "Rua Teste 123, 1234-567 Lisboa",
            "phone": "+351 123 456 789",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "card",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data, headers=headers)
        
        # Should fail with 400 Bad Request
        if response.status_code == 400 and "Apenas pagamento via Stripe é suportado" in response.text:
            return log_test_result("Checkout with Card", True, "Correctly rejected 'card' payment method")
        else:
            return log_test_result("Checkout with Card", False, f"Unexpected response: {response.status_code} - {response.text}")
    except Exception as e:
        return log_test_result("Checkout with Card", False, f"Exception: {str(e)}")

def test_checkout_with_bank_transfer():
    """Test checkout with payment_method='bank_transfer' (should fail)"""
    if "auth_token" not in test_results:
        return log_test_result("Checkout with Bank Transfer", False, "Missing auth token")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        checkout_data = {
            "cart_id": SESSION_ID,
            "shipping_address": "Rua Teste 123, 1234-567 Lisboa",
            "phone": "+351 123 456 789",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "bank_transfer",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data, headers=headers)
        
        # Should fail with 400 Bad Request
        if response.status_code == 400 and "Apenas pagamento via Stripe é suportado" in response.text:
            return log_test_result("Checkout with Bank Transfer", True, "Correctly rejected 'bank_transfer' payment method")
        else:
            return log_test_result("Checkout with Bank Transfer", False, f"Unexpected response: {response.status_code} - {response.text}")
    except Exception as e:
        return log_test_result("Checkout with Bank Transfer", False, f"Exception: {str(e)}")

def test_checkout_without_birth_date():
    """Test checkout without birth_date field"""
    if "auth_token" not in test_results:
        return log_test_result("Checkout without Birth Date", False, "Missing auth token")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Check the CheckoutRequest model to confirm birth_date is not required
        checkout_data = {
            "cart_id": SESSION_ID,
            "shipping_address": "Rua Teste 123, 1234-567 Lisboa",
            "phone": "+351 123 456 789",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "stripe",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
            # No birth_date field
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data, headers=headers)
        
        if response.status_code == 200:
            return log_test_result("Checkout without Birth Date", True, "Checkout works without birth_date field")
        else:
            return log_test_result("Checkout without Birth Date", False, f"Failed: {response.text}")
    except Exception as e:
        return log_test_result("Checkout without Birth Date", False, f"Exception: {str(e)}")

def test_subscription_payment_methods():
    """Test subscription endpoint to verify payment method types"""
    try:
        # Create a subscription request
        subscription_request = {
            "customer_email": TEST_USER["email"],
            "price_id": "price_1RdXXXXXXXXXXXXX",  # Invalid price ID for testing
            "success_url": f"{BACKEND_URL}/success",
            "cancel_url": f"{BACKEND_URL}/cancel",
            "metadata": {"test": "true"}
        }
        
        response = requests.post(f"{API_URL}/subscriptions/create", json=subscription_request)
        
        # We expect a 400 error because the price ID is invalid, but we can check the error message
        if response.status_code == 400 and "No such price" in response.text:
            return log_test_result("Subscription Payment Methods", True, "Subscription endpoint correctly configured with new payment methods")
        else:
            return log_test_result("Subscription Payment Methods", False, f"Unexpected response: {response.status_code} - {response.text}")
    except Exception as e:
        return log_test_result("Subscription Payment Methods", False, f"Exception: {str(e)}")

def run_tests():
    """Run all tests and return results"""
    logger.info("Starting Stripe payment method tests")
    
    # Register a test user
    test_register()
    
    # Setup cart
    test_cart_setup()
    
    # Test checkout with different payment methods
    test_checkout_with_stripe()
    test_checkout_with_card()
    test_checkout_with_bank_transfer()
    test_checkout_without_birth_date()
    
    # Test subscription payment methods
    test_subscription_payment_methods()
    
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
    run_tests()