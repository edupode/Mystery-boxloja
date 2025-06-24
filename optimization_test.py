import requests
import json
import uuid
import time
import statistics
from datetime import datetime
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

def measure_response_time(endpoint, method="GET", headers=None, params=None, json_data=None, num_requests=5):
    """Measure response time for an endpoint"""
    url = f"{API_URL}/{endpoint}"
    response_times = []
    
    for i in range(num_requests):
        start_time = time.time()
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, params=params, json=json_data)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        response_times.append(response_time)
        
        # Small delay between requests
        time.sleep(0.2)
    
    # Calculate statistics
    avg_time = statistics.mean(response_times)
    min_time = min(response_times)
    max_time = max(response_times)
    
    return {
        "avg_ms": avg_time,
        "min_ms": min_time,
        "max_ms": max_time,
        "status_code": response.status_code,
        "response": response.json() if response.status_code == 200 else None
    }

def test_health_endpoint():
    """Test health endpoint with keep-alive"""
    try:
        # First request
        session = requests.Session()
        start_time = time.time()
        response = session.get(f"{API_URL}/health")
        first_request_time = (time.time() - start_time) * 1000
        
        # Second request with keep-alive
        time.sleep(0.5)
        start_time = time.time()
        response = session.get(f"{API_URL}/health")
        second_request_time = (time.time() - start_time) * 1000
        
        # Check if second request is faster (keep-alive working)
        keep_alive_working = second_request_time < first_request_time
        
        return log_test_result(
            "Health Endpoint (Keep-Alive)", 
            keep_alive_working, 
            f"First request: {first_request_time:.2f}ms, Second request: {second_request_time:.2f}ms"
        )
    except Exception as e:
        return log_test_result("Health Endpoint (Keep-Alive)", False, f"Exception: {str(e)}")

def test_products_endpoint_performance():
    """Test products endpoint performance"""
    try:
        # Measure response time
        results = measure_response_time("products")
        
        # Check if response time is acceptable (under 500ms)
        is_fast = results["avg_ms"] < 500
        
        return log_test_result(
            "Products Endpoint Performance", 
            is_fast, 
            f"Avg: {results['avg_ms']:.2f}ms, Min: {results['min_ms']:.2f}ms, Max: {results['max_ms']:.2f}ms"
        )
    except Exception as e:
        return log_test_result("Products Endpoint Performance", False, f"Exception: {str(e)}")

def test_categories_endpoint_performance():
    """Test categories endpoint performance"""
    try:
        # Measure response time
        results = measure_response_time("categories")
        
        # Check if response time is acceptable (under 300ms)
        is_fast = results["avg_ms"] < 300
        
        return log_test_result(
            "Categories Endpoint Performance", 
            is_fast, 
            f"Avg: {results['avg_ms']:.2f}ms, Min: {results['min_ms']:.2f}ms, Max: {results['max_ms']:.2f}ms"
        )
    except Exception as e:
        return log_test_result("Categories Endpoint Performance", False, f"Exception: {str(e)}")

def test_auth_me_endpoint_performance():
    """Test auth/me endpoint performance"""
    # First login to get token
    try:
        login_response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        if login_response.status_code != 200:
            return log_test_result("Auth/Me Endpoint Performance", False, "Failed to login")
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Measure response time
        results = measure_response_time("auth/me", headers=headers)
        
        # Check if response time is acceptable (under 300ms)
        is_fast = results["avg_ms"] < 300
        
        return log_test_result(
            "Auth/Me Endpoint Performance", 
            is_fast, 
            f"Avg: {results['avg_ms']:.2f}ms, Min: {results['min_ms']:.2f}ms, Max: {results['max_ms']:.2f}ms"
        )
    except Exception as e:
        return log_test_result("Auth/Me Endpoint Performance", False, f"Exception: {str(e)}")

def test_cart_endpoint_performance():
    """Test cart endpoint performance"""
    try:
        # Measure response time
        results = measure_response_time(f"cart/{SESSION_ID}")
        
        # Check if response time is acceptable (under 300ms)
        is_fast = results["avg_ms"] < 300
        
        return log_test_result(
            "Cart Endpoint Performance", 
            is_fast, 
            f"Avg: {results['avg_ms']:.2f}ms, Min: {results['min_ms']:.2f}ms, Max: {results['max_ms']:.2f}ms"
        )
    except Exception as e:
        return log_test_result("Cart Endpoint Performance", False, f"Exception: {str(e)}")

def test_cache_effectiveness():
    """Test if caching is working by measuring repeated requests"""
    try:
        # First request
        start_time = time.time()
        first_response = requests.get(f"{API_URL}/products")
        first_request_time = (time.time() - start_time) * 1000
        
        # Second request (should be cached)
        time.sleep(0.5)
        start_time = time.time()
        second_response = requests.get(f"{API_URL}/products")
        second_request_time = (time.time() - start_time) * 1000
        
        # Check if second request is significantly faster (cache working)
        cache_working = second_request_time < first_request_time * 0.8
        
        return log_test_result(
            "Cache Effectiveness", 
            cache_working, 
            f"First request: {first_request_time:.2f}ms, Second request: {second_request_time:.2f}ms"
        )
    except Exception as e:
        return log_test_result("Cache Effectiveness", False, f"Exception: {str(e)}")

def test_database_indexes():
    """Test database indexes by measuring filtered queries"""
    try:
        # Get all products first to find a category
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Database Indexes", False, "Failed to get products")
        
        products = response.json()
        if not products:
            return log_test_result("Database Indexes", False, "No products found")
        
        # Get a category to filter by
        category = products[0].get("category")
        if not category:
            return log_test_result("Database Indexes", False, "No category found in products")
        
        # Measure response time for filtered query
        results = measure_response_time(f"products?category={category}")
        
        # Check if response time is acceptable (under 300ms)
        is_fast = results["avg_ms"] < 300
        
        return log_test_result(
            "Database Indexes", 
            is_fast, 
            f"Category filter query: Avg: {results['avg_ms']:.2f}ms, Min: {results['min_ms']:.2f}ms, Max: {results['max_ms']:.2f}ms"
        )
    except Exception as e:
        return log_test_result("Database Indexes", False, f"Exception: {str(e)}")

def test_gzip_compression():
    """Test if GZIP compression is enabled"""
    try:
        headers = {"Accept-Encoding": "gzip, deflate"}
        response = requests.get(f"{API_URL}/products", headers=headers)
        
        # Check if Content-Encoding header is present
        is_compressed = "Content-Encoding" in response.headers and response.headers["Content-Encoding"] == "gzip"
        
        return log_test_result(
            "GZIP Compression", 
            is_compressed, 
            f"Content-Encoding: {response.headers.get('Content-Encoding', 'Not enabled')}"
        )
    except Exception as e:
        return log_test_result("GZIP Compression", False, f"Exception: {str(e)}")

def run_optimization_tests():
    """Run all optimization tests and return results"""
    logger.info("Starting backend optimization tests for Mystery Box Store")
    
    # Test keep-alive
    test_health_endpoint()
    
    # Test endpoint performance
    test_products_endpoint_performance()
    test_categories_endpoint_performance()
    test_auth_me_endpoint_performance()
    test_cart_endpoint_performance()
    
    # Test caching
    test_cache_effectiveness()
    
    # Test database indexes
    test_database_indexes()
    
    # Test compression
    test_gzip_compression()
    
    # Print summary
    logger.info("\n=== OPTIMIZATION TEST SUMMARY ===")
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
    run_optimization_tests()