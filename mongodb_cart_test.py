import requests
import json
import uuid
import time
import random
import logging
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] == "ok":
                return log_test_result("Health Endpoint", True, "API is healthy")
            else:
                return log_test_result("Health Endpoint", False, f"Unexpected response: {data}")
        else:
            return log_test_result("Health Endpoint", False, f"Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        return log_test_result("Health Endpoint", False, f"Exception: {str(e)}")

def test_cart_creation(session_id):
    """Test cart creation with a specific session ID"""
    try:
        response = requests.get(f"{API_URL}/cart/{session_id}")
        if response.status_code == 200:
            cart = response.json()
            if cart and "session_id" in cart and cart["session_id"] == session_id:
                return log_test_result(f"Cart Creation ({session_id[:8]})", True, f"Cart created successfully")
            else:
                return log_test_result(f"Cart Creation ({session_id[:8]})", False, f"Invalid cart data: {cart}")
        else:
            return log_test_result(f"Cart Creation ({session_id[:8]})", False, f"Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        return log_test_result(f"Cart Creation ({session_id[:8]})", False, f"Exception: {str(e)}")

def test_cart_operations(session_id):
    """Test adding and removing products from a cart"""
    try:
        # First, get products to have a valid product ID
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result(f"Cart Operations ({session_id[:8]})", False, "Failed to get products")
        
        products = response.json()
        if not products or not isinstance(products, list) or len(products) == 0:
            return log_test_result(f"Cart Operations ({session_id[:8]})", False, "No products available for testing")
        
        # Select a random product
        product = random.choice(products)
        product_id = product["id"]
        
        # Add product to cart
        cart_item = {
            "product_id": product_id,
            "quantity": 2
        }
        
        response = requests.post(f"{API_URL}/cart/{session_id}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result(f"Add to Cart ({session_id[:8]})", False, f"Failed: {response.text}")
        
        updated_cart = response.json()
        if not updated_cart or not updated_cart.get("items"):
            return log_test_result(f"Add to Cart ({session_id[:8]})", False, "Product not added to cart")
        
        # Check if product was added
        product_in_cart = False
        for item in updated_cart["items"]:
            if item["product_id"] == product_id:
                product_in_cart = True
                break
        
        if not product_in_cart:
            return log_test_result(f"Add to Cart ({session_id[:8]})", False, "Product not found in cart after adding")
        
        # Remove product from cart
        response = requests.delete(f"{API_URL}/cart/{session_id}/remove/{product_id}")
        if response.status_code != 200:
            return log_test_result(f"Remove from Cart ({session_id[:8]})", False, f"Failed: {response.text}")
        
        cart_after_remove = response.json()
        if any(item["product_id"] == product_id for item in cart_after_remove.get("items", [])):
            return log_test_result(f"Remove from Cart ({session_id[:8]})", False, "Product still in cart after removal")
        
        return log_test_result(f"Cart Operations ({session_id[:8]})", True, "Successfully added and removed products")
    except Exception as e:
        return log_test_result(f"Cart Operations ({session_id[:8]})", False, f"Exception: {str(e)}")

def test_list_products():
    """Test listing products"""
    try:
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("List Products", False, f"Failed: {response.text}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("List Products", False, "No products returned or invalid format")
        
        return log_test_result("List Products", True, f"Found {len(products)} products")
    except Exception as e:
        return log_test_result("List Products", False, f"Exception: {str(e)}")

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

def test_concurrent_cart_creation(num_carts=10):
    """Test creating multiple carts concurrently to check for duplicate key errors"""
    session_ids = [str(uuid.uuid4()) for _ in range(num_carts)]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(test_cart_creation, session_id) for session_id in session_ids]
        
        results = []
        for future in as_completed(futures):
            results.append(future.result())
    
    success_count = sum(1 for result in results if result)
    if success_count == num_carts:
        return log_test_result("Concurrent Cart Creation", True, f"Successfully created {success_count}/{num_carts} carts")
    else:
        return log_test_result("Concurrent Cart Creation", False, f"Only {success_count}/{num_carts} carts created successfully")

def test_cart_operations_multiple_sessions(num_carts=5):
    """Test cart operations on multiple carts to verify no duplicate key errors"""
    session_ids = [str(uuid.uuid4()) for _ in range(num_carts)]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(test_cart_operations, session_id) for session_id in session_ids]
        
        results = []
        for future in as_completed(futures):
            results.append(future.result())
    
    success_count = sum(1 for result in results if result)
    if success_count == num_carts:
        return log_test_result("Multiple Cart Operations", True, f"Successfully performed operations on {success_count}/{num_carts} carts")
    else:
        return log_test_result("Multiple Cart Operations", False, f"Only {success_count}/{num_carts} cart operations completed successfully")

def run_mongodb_cart_tests():
    """Run tests focused on MongoDB duplicate key error and cart functionality"""
    logger.info("Starting MongoDB cart tests for Mystery Box Store")
    
    # Test health endpoint
    test_health_endpoint()
    
    # Test basic endpoints
    test_list_products()
    test_list_categories()
    
    # Test single cart creation and operations
    single_session_id = str(uuid.uuid4())
    test_cart_creation(single_session_id)
    test_cart_operations(single_session_id)
    
    # Test concurrent cart creation (to check for duplicate key errors)
    test_concurrent_cart_creation(10)
    
    # Test cart operations on multiple sessions
    test_cart_operations_multiple_sessions(5)
    
    # Print summary
    logger.info("\n=== TEST SUMMARY ===")
    passed = sum(1 for result in test_results.values() if result.get("success"))
    failed = sum(1 for result in test_results.values() if not result.get("success"))
    logger.info(f"PASSED: {passed}, FAILED: {failed}")
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
        if result.get("message"):
            logger.info(f"  - {result['message']}")
    
    return test_results

if __name__ == "__main__":
    run_mongodb_cart_tests()