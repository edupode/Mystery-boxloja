import requests
import json
import logging
import os
from dotenv import load_dotenv
import time

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

def test_backend_connectivity():
    """Test basic backend connectivity"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            return log_test_result("Backend Connectivity", True, f"Backend is responsive: {response.json()}")
        else:
            return log_test_result("Backend Connectivity", False, f"Failed with status code: {response.status_code}")
    except Exception as e:
        return log_test_result("Backend Connectivity", False, f"Exception: {str(e)}")

def test_get_products():
    """Test GET /api/products endpoint"""
    try:
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("GET /api/products", False, f"Failed with status code: {response.status_code}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("GET /api/products", False, "No products returned or invalid format")
        
        # Store a product ID for later tests
        if products:
            test_results["product_id"] = products[0]["id"]
            
        return log_test_result("GET /api/products", True, f"Successfully retrieved {len(products)} products")
    except Exception as e:
        return log_test_result("GET /api/products", False, f"Exception: {str(e)}")

def test_get_featured_products():
    """Test GET /api/products?featured=true endpoint"""
    try:
        response = requests.get(f"{API_URL}/products?featured=true")
        if response.status_code != 200:
            return log_test_result("GET /api/products?featured=true", False, f"Failed with status code: {response.status_code}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("GET /api/products?featured=true", False, "No featured products returned or invalid format")
        
        # Verify all products are featured
        if not all(p.get("featured", False) for p in products):
            return log_test_result("GET /api/products?featured=true", False, "Some products returned are not featured")
            
        return log_test_result("GET /api/products?featured=true", True, f"Successfully retrieved {len(products)} featured products")
    except Exception as e:
        return log_test_result("GET /api/products?featured=true", False, f"Exception: {str(e)}")

def test_get_categories():
    """Test GET /api/categories endpoint"""
    try:
        response = requests.get(f"{API_URL}/categories")
        if response.status_code != 200:
            return log_test_result("GET /api/categories", False, f"Failed with status code: {response.status_code}")
        
        categories = response.json()
        if not categories or not isinstance(categories, list):
            return log_test_result("GET /api/categories", False, "No categories returned or invalid format")
            
        return log_test_result("GET /api/categories", True, f"Successfully retrieved {len(categories)} categories")
    except Exception as e:
        return log_test_result("GET /api/categories", False, f"Exception: {str(e)}")

def test_get_product_detail():
    """Test GET /api/products/{id} endpoint"""
    if "product_id" not in test_results:
        # Try to get a product ID first
        test_get_products()
        
    if "product_id" not in test_results:
        return log_test_result("GET /api/products/{id}", False, "No product ID available for testing")
    
    try:
        product_id = test_results["product_id"]
        response = requests.get(f"{API_URL}/products/{product_id}")
        if response.status_code != 200:
            return log_test_result("GET /api/products/{id}", False, f"Failed with status code: {response.status_code}")
        
        product = response.json()
        if not product or not isinstance(product, dict) or "id" not in product:
            return log_test_result("GET /api/products/{id}", False, "Invalid product data returned")
        
        # Check if the product has all required fields
        required_fields = ["name", "description", "price", "category"]
        missing_fields = [field for field in required_fields if field not in product]
        
        if missing_fields:
            return log_test_result("GET /api/products/{id}", False, f"Product missing required fields: {', '.join(missing_fields)}")
            
        return log_test_result("GET /api/products/{id}", True, f"Successfully retrieved product: {product.get('name', 'Unknown')}")
    except Exception as e:
        return log_test_result("GET /api/products/{id}", False, f"Exception: {str(e)}")

def test_get_cart():
    """Test GET /api/cart/{session_id} endpoint"""
    # Generate a random session ID for testing
    import uuid
    session_id = str(uuid.uuid4())
    test_results["session_id"] = session_id
    
    try:
        response = requests.get(f"{API_URL}/cart/{session_id}")
        if response.status_code != 200:
            return log_test_result("GET /api/cart/{session_id}", False, f"Failed with status code: {response.status_code}")
        
        cart = response.json()
        if not cart or not isinstance(cart, dict) or "session_id" not in cart:
            return log_test_result("GET /api/cart/{session_id}", False, "Invalid cart data returned")
            
        return log_test_result("GET /api/cart/{session_id}", True, f"Successfully retrieved cart for session: {session_id}")
    except Exception as e:
        return log_test_result("GET /api/cart/{session_id}", False, f"Exception: {str(e)}")

def test_cors_headers():
    """Test CORS headers for frontend access"""
    try:
        # Test CORS headers on a few key endpoints
        endpoints = [
            "/products",
            "/categories",
            "/health"
        ]
        
        frontend_url = "https://mystery-box-loja.vercel.app"
        headers = {"Origin": frontend_url}
        
        all_passed = True
        for endpoint in endpoints:
            response = requests.options(f"{API_URL}{endpoint}", headers=headers)
            
            cors_header = response.headers.get("Access-Control-Allow-Origin")
            if not cors_header:
                log_test_result(f"CORS Headers - {endpoint}", False, "No CORS headers present")
                all_passed = False
                continue
                
            if frontend_url not in cors_header and "*" not in cors_header:
                log_test_result(f"CORS Headers - {endpoint}", False, f"Frontend URL not allowed: {cors_header}")
                all_passed = False
                continue
                
            log_test_result(f"CORS Headers - {endpoint}", True, f"CORS properly configured: {cors_header}")
        
        return log_test_result("CORS Headers", all_passed, "CORS headers properly configured for frontend access")
    except Exception as e:
        return log_test_result("CORS Headers", False, f"Exception: {str(e)}")

def run_critical_tests():
    """Run all critical backend tests"""
    logger.info("Starting critical backend tests for Mystery Box Store")
    logger.info(f"Testing backend at: {API_URL}")
    
    # Basic connectivity test
    test_backend_connectivity()
    
    # Product endpoints
    test_get_products()
    test_get_featured_products()
    test_get_product_detail()
    
    # Categories endpoint
    test_get_categories()
    
    # Cart endpoint
    test_get_cart()
    
    # CORS headers
    test_cors_headers()
    
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
    run_critical_tests()