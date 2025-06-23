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

def test_add_subscription_products_to_cart():
    """Test adding subscription products to cart"""
    try:
        # Get a product
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Add Subscription Products to Cart", False, f"Failed to get products: {response.text}")
        
        products = response.json()
        if not products:
            return log_test_result("Add Subscription Products to Cart", False, "No products returned")
        
        product_id = products[0]["id"]
        
        # Add subscription product to cart for each subscription type
        subscription_types = ["monthly_3", "monthly_6", "monthly_12"]
        
        for subscription_type in subscription_types:
            cart_item = {
                "product_id": product_id,
                "quantity": 1,
                "subscription_type": subscription_type
            }
            
            response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
            if response.status_code != 200:
                return log_test_result(f"Add {subscription_type} to Cart", False, f"Failed: {response.text}")
            
            cart = response.json()
            
            # Check if product was added with correct subscription type
            product_in_cart = False
            for item in cart.get("items", []):
                if item["product_id"] == product_id and item["subscription_type"] == subscription_type:
                    product_in_cart = True
                    break
            
            if not product_in_cart:
                return log_test_result(f"Add {subscription_type} to Cart", False, f"Product with {subscription_type} not found in cart after adding")
            
            log_test_result(f"Add {subscription_type} to Cart", True, f"Successfully added {subscription_type} subscription to cart")
        
        # Get the cart to verify all items are there
        response = requests.get(f"{API_URL}/cart/{SESSION_ID}")
        if response.status_code != 200:
            return log_test_result("Get Cart with Subscriptions", False, f"Failed to get cart: {response.text}")
        
        cart = response.json()
        
        # Check if all subscription types are in the cart
        subscription_types_in_cart = set()
        for item in cart.get("items", []):
            if item["product_id"] == product_id and item["subscription_type"] in subscription_types:
                subscription_types_in_cart.add(item["subscription_type"])
        
        if len(subscription_types_in_cart) != len(subscription_types):
            return log_test_result("Get Cart with Subscriptions", False, f"Not all subscription types found in cart. Found: {subscription_types_in_cart}")
        
        return log_test_result("Add Subscription Products to Cart", True, f"Successfully added all subscription types to cart")
    
    except Exception as e:
        return log_test_result("Add Subscription Products to Cart", False, f"Exception: {str(e)}")

def run_tests():
    """Run all tests"""
    logger.info("Starting subscription cart tests")
    
    # Test adding subscription products to cart
    test_add_subscription_products_to_cart()
    
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