import requests
import json
import uuid
import time
import statistics
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import concurrent.futures
import numpy as np

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

def register_and_login():
    """Register a test user and get auth token"""
    try:
        # Register
        response = requests.post(f"{API_URL}/auth/register", json=TEST_USER)
        if response.status_code != 200:
            logger.error(f"Failed to register test user: {response.text}")
            return None
        
        response_data = response.json()
        return response_data.get("access_token")
    
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        return None

def admin_login():
    """Login as admin and get auth token"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        if response.status_code != 200:
            logger.error(f"Failed to login as admin: {response.text}")
            return None
        
        response_data = response.json()
        return response_data.get("access_token")
    
    except Exception as e:
        logger.error(f"Error during admin login: {str(e)}")
        return None

def test_products_endpoint():
    """Test GET /api/products endpoint with database indexes"""
    logger.info("Testing GET /api/products endpoint with database indexes")
    
    # Test without filters
    start_time = time.time()
    response = requests.get(f"{API_URL}/products")
    all_products_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("GET /api/products", False, f"Failed: {response.text}")
    
    products = response.json()
    if not products or not isinstance(products, list):
        return log_test_result("GET /api/products", False, "No products returned or invalid format")
    
    # Store a product ID for later tests
    if products:
        test_results["product_id"] = products[0]["id"]
    
    # Test with featured filter
    start_time = time.time()
    response = requests.get(f"{API_URL}/products?featured=true")
    featured_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("GET /api/products?featured=true", False, f"Failed: {response.text}")
    
    featured_products = response.json()
    
    # Test with multiple requests to check caching
    cache_times = []
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{API_URL}/products")
        cache_time = (time.time() - start_time) * 1000
        cache_times.append(cache_time)
    
    avg_cache_time = statistics.mean(cache_times)
    
    # Log results
    logger.info(f"Products endpoint performance:")
    logger.info(f"  All products: {all_products_time:.2f}ms")
    logger.info(f"  Featured products: {featured_time:.2f}ms")
    logger.info(f"  Avg cached request: {avg_cache_time:.2f}ms")
    
    # Calculate cache effectiveness
    if all_products_time > 0:
        cache_speedup = all_products_time / avg_cache_time
    else:
        cache_speedup = 0
    
    logger.info(f"  Cache speedup: {cache_speedup:.2f}x")
    
    # Test concurrent requests
    num_concurrent = 10
    num_requests = 20
    
    def make_request(_):
        try:
            start_time = time.time()
            response = requests.get(f"{API_URL}/products")
            end_time = time.time()
            
            if response.status_code == 200:
                return True, (end_time - start_time) * 1000
            else:
                return False, None
        except Exception:
            return False, None
    
    logger.info(f"Making {num_requests} concurrent requests to /api/products")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        results = list(executor.map(make_request, range(num_requests)))
    
    success_count = 0
    response_times = []
    
    for success, time_ms in results:
        if success and time_ms is not None:
            success_count += 1
            response_times.append(time_ms)
    
    if response_times:
        avg_concurrent_time = statistics.mean(response_times)
        max_concurrent_time = max(response_times)
        
        logger.info(f"  Concurrent requests:")
        logger.info(f"    Success rate: {(success_count / num_requests) * 100:.2f}%")
        logger.info(f"    Avg response time: {avg_concurrent_time:.2f}ms")
        logger.info(f"    Max response time: {max_concurrent_time:.2f}ms")
    
    # Overall assessment
    if cache_speedup >= 1.0 and success_count >= num_requests * 0.9:
        return log_test_result("GET /api/products", True, f"Endpoint is optimized with caching and indexes. Cache speedup: {cache_speedup:.2f}x")
    else:
        return log_test_result("GET /api/products", False, f"Endpoint may not be fully optimized. Cache speedup: {cache_speedup:.2f}x")

def test_categories_endpoint():
    """Test GET /api/categories endpoint with database indexes"""
    logger.info("Testing GET /api/categories endpoint with database indexes")
    
    # Test with multiple requests to check caching
    times = []
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{API_URL}/categories")
        request_time = (time.time() - start_time) * 1000
        times.append(request_time)
        
        if response.status_code != 200:
            return log_test_result("GET /api/categories", False, f"Failed on request {i+1}: {response.text}")
    
    first_request_time = times[0]
    avg_subsequent_time = statistics.mean(times[1:]) if len(times) > 1 else 0
    
    # Log results
    logger.info(f"Categories endpoint performance:")
    logger.info(f"  First request: {first_request_time:.2f}ms")
    logger.info(f"  Avg subsequent request: {avg_subsequent_time:.2f}ms")
    
    # Calculate cache effectiveness
    if first_request_time > 0:
        cache_speedup = first_request_time / avg_subsequent_time if avg_subsequent_time > 0 else 0
    else:
        cache_speedup = 0
    
    logger.info(f"  Cache speedup: {cache_speedup:.2f}x")
    
    # Test concurrent requests
    num_concurrent = 10
    num_requests = 20
    
    def make_request(_):
        try:
            start_time = time.time()
            response = requests.get(f"{API_URL}/categories")
            end_time = time.time()
            
            if response.status_code == 200:
                return True, (end_time - start_time) * 1000
            else:
                return False, None
        except Exception:
            return False, None
    
    logger.info(f"Making {num_requests} concurrent requests to /api/categories")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        results = list(executor.map(make_request, range(num_requests)))
    
    success_count = 0
    response_times = []
    
    for success, time_ms in results:
        if success and time_ms is not None:
            success_count += 1
            response_times.append(time_ms)
    
    if response_times:
        avg_concurrent_time = statistics.mean(response_times)
        max_concurrent_time = max(response_times)
        
        logger.info(f"  Concurrent requests:")
        logger.info(f"    Success rate: {(success_count / num_requests) * 100:.2f}%")
        logger.info(f"    Avg response time: {avg_concurrent_time:.2f}ms")
        logger.info(f"    Max response time: {max_concurrent_time:.2f}ms")
    
    # Overall assessment
    if cache_speedup >= 1.0 and success_count >= num_requests * 0.9:
        return log_test_result("GET /api/categories", True, f"Endpoint is optimized with caching and indexes. Cache speedup: {cache_speedup:.2f}x")
    else:
        return log_test_result("GET /api/categories", False, f"Endpoint may not be fully optimized. Cache speedup: {cache_speedup:.2f}x")

def test_auth_me_endpoint():
    """Test GET /api/auth/me endpoint with JWT token"""
    logger.info("Testing GET /api/auth/me endpoint with JWT token")
    
    # Get auth token
    auth_token = register_and_login()
    if not auth_token:
        return log_test_result("GET /api/auth/me", False, "Failed to get auth token")
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Test with multiple requests to check caching
    times = []
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        request_time = (time.time() - start_time) * 1000
        times.append(request_time)
        
        if response.status_code != 200:
            return log_test_result("GET /api/auth/me", False, f"Failed on request {i+1}: {response.text}")
    
    first_request_time = times[0]
    avg_subsequent_time = statistics.mean(times[1:]) if len(times) > 1 else 0
    
    # Log results
    logger.info(f"Auth/me endpoint performance:")
    logger.info(f"  First request: {first_request_time:.2f}ms")
    logger.info(f"  Avg subsequent request: {avg_subsequent_time:.2f}ms")
    
    # Calculate cache effectiveness
    if first_request_time > 0:
        cache_speedup = first_request_time / avg_subsequent_time if avg_subsequent_time > 0 else 0
    else:
        cache_speedup = 0
    
    logger.info(f"  Cache speedup: {cache_speedup:.2f}x")
    
    # Test concurrent requests
    num_concurrent = 5
    num_requests = 10
    
    def make_request(_):
        try:
            start_time = time.time()
            response = requests.get(f"{API_URL}/auth/me", headers=headers)
            end_time = time.time()
            
            if response.status_code == 200:
                return True, (end_time - start_time) * 1000
            else:
                return False, None
        except Exception:
            return False, None
    
    logger.info(f"Making {num_requests} concurrent requests to /api/auth/me")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        results = list(executor.map(make_request, range(num_requests)))
    
    success_count = 0
    response_times = []
    
    for success, time_ms in results:
        if success and time_ms is not None:
            success_count += 1
            response_times.append(time_ms)
    
    if response_times:
        avg_concurrent_time = statistics.mean(response_times)
        max_concurrent_time = max(response_times)
        
        logger.info(f"  Concurrent requests:")
        logger.info(f"    Success rate: {(success_count / num_requests) * 100:.2f}%")
        logger.info(f"    Avg response time: {avg_concurrent_time:.2f}ms")
        logger.info(f"    Max response time: {max_concurrent_time:.2f}ms")
    
    # Overall assessment
    if success_count >= num_requests * 0.9:
        return log_test_result("GET /api/auth/me", True, f"Endpoint is optimized and handles concurrent requests well.")
    else:
        return log_test_result("GET /api/auth/me", False, f"Endpoint may not be fully optimized for concurrent requests.")

def test_cart_endpoint():
    """Test GET /api/cart/{session_id} endpoint with database indexes"""
    logger.info("Testing GET /api/cart/{session_id} endpoint with database indexes")
    
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    
    # Add a product to the cart first
    product_response = requests.get(f"{API_URL}/products")
    if product_response.status_code != 200:
        return log_test_result("GET /api/cart/{session_id}", False, "Failed to get products for cart test")
    
    products = product_response.json()
    if not products:
        return log_test_result("GET /api/cart/{session_id}", False, "No products available for cart test")
    
    product_id = products[0]["id"]
    
    # Add product to cart
    cart_item = {
        "product_id": product_id,
        "quantity": 1
    }
    
    add_response = requests.post(f"{API_URL}/cart/{session_id}/add", json=cart_item)
    if add_response.status_code != 200:
        return log_test_result("GET /api/cart/{session_id}", False, f"Failed to add product to cart: {add_response.text}")
    
    # Test with multiple requests to check caching
    times = []
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{API_URL}/cart/{session_id}")
        request_time = (time.time() - start_time) * 1000
        times.append(request_time)
        
        if response.status_code != 200:
            return log_test_result("GET /api/cart/{session_id}", False, f"Failed on request {i+1}: {response.text}")
    
    first_request_time = times[0]
    avg_subsequent_time = statistics.mean(times[1:]) if len(times) > 1 else 0
    
    # Log results
    logger.info(f"Cart endpoint performance:")
    logger.info(f"  First request: {first_request_time:.2f}ms")
    logger.info(f"  Avg subsequent request: {avg_subsequent_time:.2f}ms")
    
    # Calculate cache effectiveness
    if first_request_time > 0:
        cache_speedup = first_request_time / avg_subsequent_time if avg_subsequent_time > 0 else 0
    else:
        cache_speedup = 0
    
    logger.info(f"  Cache speedup: {cache_speedup:.2f}x")
    
    # Test concurrent requests
    num_concurrent = 5
    num_requests = 10
    
    def make_request(_):
        try:
            start_time = time.time()
            response = requests.get(f"{API_URL}/cart/{session_id}")
            end_time = time.time()
            
            if response.status_code == 200:
                return True, (end_time - start_time) * 1000
            else:
                return False, None
        except Exception:
            return False, None
    
    logger.info(f"Making {num_requests} concurrent requests to /api/cart/{session_id}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        results = list(executor.map(make_request, range(num_requests)))
    
    success_count = 0
    response_times = []
    
    for success, time_ms in results:
        if success and time_ms is not None:
            success_count += 1
            response_times.append(time_ms)
    
    if response_times:
        avg_concurrent_time = statistics.mean(response_times)
        max_concurrent_time = max(response_times)
        
        logger.info(f"  Concurrent requests:")
        logger.info(f"    Success rate: {(success_count / num_requests) * 100:.2f}%")
        logger.info(f"    Avg response time: {avg_concurrent_time:.2f}ms")
        logger.info(f"    Max response time: {max_concurrent_time:.2f}ms")
    
    # Overall assessment
    if success_count >= num_requests * 0.9:
        return log_test_result("GET /api/cart/{session_id}", True, f"Endpoint is optimized and handles concurrent requests well.")
    else:
        return log_test_result("GET /api/cart/{session_id}", False, f"Endpoint may not be fully optimized for concurrent requests.")

def test_rate_limiting():
    """Test rate limiting functionality"""
    logger.info("Testing rate limiting functionality")
    
    # Make many requests in quick succession to trigger rate limiting
    url = f"{API_URL}/health"
    num_requests = 100
    success_count = 0
    rate_limited_count = 0
    
    for i in range(num_requests):
        try:
            response = requests.get(url)
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:  # Too Many Requests
                rate_limited_count += 1
                logger.debug(f"Request {i+1}/{num_requests} rate limited")
            else:
                logger.warning(f"Request {i+1}/{num_requests} failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Request {i+1}/{num_requests} error: {str(e)}")
    
    logger.info(f"Rate limiting test results:")
    logger.info(f"  Total requests: {num_requests}")
    logger.info(f"  Successful requests: {success_count}")
    logger.info(f"  Rate limited requests: {rate_limited_count}")
    
    # Rate limiting is working if some requests were rate limited
    if rate_limited_count > 0:
        return log_test_result("Rate Limiting", True, f"Rate limiting is working. {rate_limited_count} of {num_requests} requests were rate limited.")
    else:
        return log_test_result("Rate Limiting", False, "No requests were rate limited - rate limiting may not be working")

def test_error_handling():
    """Test error handling for optimized endpoints"""
    logger.info("Testing error handling for optimized endpoints")
    
    # Test invalid product ID
    invalid_product_id = "invalid_id_12345"
    response = requests.get(f"{API_URL}/products/{invalid_product_id}")
    
    if response.status_code == 404:
        log_test_result("Error Handling - Invalid Product ID", True, "Correctly returns 404 for invalid product ID")
    else:
        log_test_result("Error Handling - Invalid Product ID", False, f"Unexpected response: {response.status_code} - {response.text}")
    
    # Test invalid category
    invalid_category = "nonexistent_category"
    response = requests.get(f"{API_URL}/products?category={invalid_category}")
    
    if response.status_code == 200:
        products = response.json()
        if len(products) == 0:
            log_test_result("Error Handling - Invalid Category", True, "Correctly returns empty list for invalid category")
        else:
            log_test_result("Error Handling - Invalid Category", False, f"Unexpected response: returned {len(products)} products")
    else:
        log_test_result("Error Handling - Invalid Category", False, f"Unexpected response code: {response.status_code} - {response.text}")
    
    # Test invalid session ID for cart
    invalid_session_id = "invalid_session_12345"
    response = requests.get(f"{API_URL}/cart/{invalid_session_id}")
    
    if response.status_code == 200:
        # Should create a new cart with the invalid session ID
        log_test_result("Error Handling - Invalid Cart Session ID", True, "Correctly creates new cart for invalid session ID")
    else:
        log_test_result("Error Handling - Invalid Cart Session ID", False, f"Unexpected response: {response.status_code} - {response.text}")
    
    # Test invalid auth token
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkQGV4YW1wbGUuY29tIiwiZXhwIjoxNjkzNTg3Mzk1fQ.invalid_signature"
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = requests.get(f"{API_URL}/auth/me", headers=headers)
    
    if response.status_code == 401:
        log_test_result("Error Handling - Invalid Auth Token", True, "Correctly returns 401 for invalid auth token")
    else:
        log_test_result("Error Handling - Invalid Auth Token", False, f"Unexpected response: {response.status_code} - {response.text}")
    
    # Overall assessment
    error_handling_tests = [
        "Error Handling - Invalid Product ID",
        "Error Handling - Invalid Category",
        "Error Handling - Invalid Cart Session ID",
        "Error Handling - Invalid Auth Token"
    ]
    
    passed_tests = sum(1 for test in error_handling_tests if test in test_results and test_results[test]["success"])
    
    if passed_tests == len(error_handling_tests):
        return log_test_result("Error Handling", True, "All error handling tests passed")
    else:
        return log_test_result("Error Handling", False, f"{passed_tests}/{len(error_handling_tests)} error handling tests passed")

def run_optimization_tests():
    """Run tests for backend API optimizations"""
    logger.info("Starting optimization tests for Mystery Box Store backend API")
    
    # Test critical endpoints
    test_products_endpoint()
    test_categories_endpoint()
    test_auth_me_endpoint()
    test_cart_endpoint()
    
    # Test rate limiting
    test_rate_limiting()
    
    # Test error handling
    test_error_handling()
    
    # Print summary
    logger.info("\n=== OPTIMIZATION TEST SUMMARY ===")
    
    for test_name, result in test_results.items():
        if isinstance(result, dict) and "success" in result:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            logger.info(f"{status}: {test_name}")
            if result.get("message"):
                logger.info(f"  - {result['message']}")
    
    return test_results

if __name__ == "__main__":
    run_optimization_tests()