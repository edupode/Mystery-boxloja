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
import matplotlib.pyplot as plt
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
performance_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

def measure_response_time(func, *args, **kwargs):
    """Measure response time of a function call"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
    return result, response_time

def test_endpoint_performance(endpoint_name, url, method="GET", headers=None, json_data=None, params=None, num_requests=10):
    """Test endpoint performance by making multiple requests and measuring response times"""
    response_times = []
    success_count = 0
    
    logger.info(f"Testing performance of {endpoint_name} ({url})")
    
    for i in range(num_requests):
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=json_data, params=params)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=json_data, params=params)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code < 400:
                success_count += 1
                response_times.append(response_time)
                logger.debug(f"Request {i+1}/{num_requests}: {response_time:.2f}ms")
            else:
                logger.warning(f"Request {i+1}/{num_requests} failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Request {i+1}/{num_requests} error: {str(e)}")
    
    if response_times:
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        median_time = statistics.median(response_times)
        p95_time = np.percentile(response_times, 95)
        
        performance_results[endpoint_name] = {
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "median_time": median_time,
            "p95_time": p95_time,
            "success_rate": (success_count / num_requests) * 100,
            "response_times": response_times
        }
        
        logger.info(f"Performance results for {endpoint_name}:")
        logger.info(f"  Success rate: {(success_count / num_requests) * 100:.2f}%")
        logger.info(f"  Avg response time: {avg_time:.2f}ms")
        logger.info(f"  Min response time: {min_time:.2f}ms")
        logger.info(f"  Max response time: {max_time:.2f}ms")
        logger.info(f"  Median response time: {median_time:.2f}ms")
        logger.info(f"  95th percentile: {p95_time:.2f}ms")
        
        return True
    else:
        logger.error(f"No successful requests for {endpoint_name}")
        return False

def test_concurrent_requests(endpoint_name, url, method="GET", headers=None, json_data=None, params=None, num_workers=5, num_requests=10):
    """Test endpoint performance with concurrent requests"""
    logger.info(f"Testing concurrent performance of {endpoint_name} with {num_workers} workers")
    
    all_response_times = []
    success_count = 0
    
    def make_request(_):
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=json_data, params=params)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=json_data, params=params)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code < 400:
                return True, response_time
            else:
                return False, None
        
        except Exception as e:
            logger.error(f"Concurrent request error: {str(e)}")
            return False, None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(make_request, range(num_requests)))
    
    for success, response_time in results:
        if success:
            success_count += 1
            all_response_times.append(response_time)
    
    if all_response_times:
        avg_time = statistics.mean(all_response_times)
        min_time = min(all_response_times)
        max_time = max(all_response_times)
        median_time = statistics.median(all_response_times)
        p95_time = np.percentile(all_response_times, 95)
        
        performance_results[f"{endpoint_name}_concurrent"] = {
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "median_time": median_time,
            "p95_time": p95_time,
            "success_rate": (success_count / num_requests) * 100,
            "response_times": all_response_times
        }
        
        logger.info(f"Concurrent performance results for {endpoint_name}:")
        logger.info(f"  Success rate: {(success_count / num_requests) * 100:.2f}%")
        logger.info(f"  Avg response time: {avg_time:.2f}ms")
        logger.info(f"  Min response time: {min_time:.2f}ms")
        logger.info(f"  Max response time: {max_time:.2f}ms")
        logger.info(f"  Median response time: {median_time:.2f}ms")
        logger.info(f"  95th percentile: {p95_time:.2f}ms")
        
        return True
    else:
        logger.error(f"No successful concurrent requests for {endpoint_name}")
        return False

def test_cache_effectiveness(endpoint_name, url, method="GET", headers=None, json_data=None, params=None, num_requests=10):
    """Test cache effectiveness by making repeated requests and measuring response times"""
    logger.info(f"Testing cache effectiveness for {endpoint_name}")
    
    # First request (uncached)
    try:
        start_time = time.time()
        
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data, params=params)
        
        end_time = time.time()
        uncached_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code >= 400:
            logger.error(f"Initial request failed: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        logger.error(f"Initial request error: {str(e)}")
        return False
    
    # Subsequent requests (potentially cached)
    cached_times = []
    
    for i in range(num_requests):
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=json_data, params=params)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code < 400:
                cached_times.append(response_time)
                logger.debug(f"Cached request {i+1}/{num_requests}: {response_time:.2f}ms")
            else:
                logger.warning(f"Cached request {i+1}/{num_requests} failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Cached request {i+1}/{num_requests} error: {str(e)}")
    
    if cached_times:
        avg_cached_time = statistics.mean(cached_times)
        
        # Calculate cache effectiveness
        if uncached_time > 0:
            cache_speedup = uncached_time / avg_cached_time
            cache_reduction_percent = ((uncached_time - avg_cached_time) / uncached_time) * 100
        else:
            cache_speedup = 0
            cache_reduction_percent = 0
        
        performance_results[f"{endpoint_name}_cache"] = {
            "uncached_time": uncached_time,
            "avg_cached_time": avg_cached_time,
            "cache_speedup": cache_speedup,
            "cache_reduction_percent": cache_reduction_percent
        }
        
        logger.info(f"Cache effectiveness for {endpoint_name}:")
        logger.info(f"  Uncached response time: {uncached_time:.2f}ms")
        logger.info(f"  Avg cached response time: {avg_cached_time:.2f}ms")
        logger.info(f"  Cache speedup: {cache_speedup:.2f}x")
        logger.info(f"  Response time reduction: {cache_reduction_percent:.2f}%")
        
        return True
    else:
        logger.error(f"No successful cached requests for {endpoint_name}")
        return False

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

def test_products_endpoint_performance():
    """Test performance of GET /api/products endpoint"""
    # Test without filters
    test_endpoint_performance(
        "GET /api/products",
        f"{API_URL}/products",
        method="GET"
    )
    
    # Test with category filter
    test_endpoint_performance(
        "GET /api/products?category=geek",
        f"{API_URL}/products",
        method="GET",
        params={"category": "geek"}
    )
    
    # Test with featured filter
    test_endpoint_performance(
        "GET /api/products?featured=true",
        f"{API_URL}/products",
        method="GET",
        params={"featured": "true"}
    )
    
    # Test cache effectiveness
    test_cache_effectiveness(
        "GET /api/products",
        f"{API_URL}/products",
        method="GET"
    )
    
    # Test concurrent requests
    test_concurrent_requests(
        "GET /api/products",
        f"{API_URL}/products",
        method="GET",
        num_workers=10,
        num_requests=50
    )

def test_categories_endpoint_performance():
    """Test performance of GET /api/categories endpoint"""
    test_endpoint_performance(
        "GET /api/categories",
        f"{API_URL}/categories",
        method="GET"
    )
    
    # Test cache effectiveness
    test_cache_effectiveness(
        "GET /api/categories",
        f"{API_URL}/categories",
        method="GET"
    )
    
    # Test concurrent requests
    test_concurrent_requests(
        "GET /api/categories",
        f"{API_URL}/categories",
        method="GET",
        num_workers=10,
        num_requests=50
    )

def test_auth_me_endpoint_performance():
    """Test performance of GET /api/auth/me endpoint"""
    # Get auth token
    auth_token = register_and_login()
    if not auth_token:
        logger.error("Failed to get auth token for testing /api/auth/me")
        return
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    test_endpoint_performance(
        "GET /api/auth/me",
        f"{API_URL}/auth/me",
        method="GET",
        headers=headers
    )
    
    # Test cache effectiveness
    test_cache_effectiveness(
        "GET /api/auth/me",
        f"{API_URL}/auth/me",
        method="GET",
        headers=headers
    )
    
    # Test concurrent requests
    test_concurrent_requests(
        "GET /api/auth/me",
        f"{API_URL}/auth/me",
        method="GET",
        headers=headers,
        num_workers=5,
        num_requests=20
    )

def test_cart_endpoint_performance():
    """Test performance of GET /api/cart/{session_id} endpoint"""
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    
    # Add a product to the cart first
    product_response = requests.get(f"{API_URL}/products")
    if product_response.status_code != 200:
        logger.error("Failed to get products for cart test")
        return
    
    products = product_response.json()
    if not products:
        logger.error("No products available for cart test")
        return
    
    product_id = products[0]["id"]
    
    # Add product to cart
    cart_item = {
        "product_id": product_id,
        "quantity": 1
    }
    
    add_response = requests.post(f"{API_URL}/cart/{session_id}/add", json=cart_item)
    if add_response.status_code != 200:
        logger.error(f"Failed to add product to cart: {add_response.text}")
        return
    
    # Test cart endpoint performance
    test_endpoint_performance(
        "GET /api/cart/{session_id}",
        f"{API_URL}/cart/{session_id}",
        method="GET"
    )
    
    # Test cache effectiveness
    test_cache_effectiveness(
        "GET /api/cart/{session_id}",
        f"{API_URL}/cart/{session_id}",
        method="GET"
    )
    
    # Test concurrent requests
    test_concurrent_requests(
        "GET /api/cart/{session_id}",
        f"{API_URL}/cart/{session_id}",
        method="GET",
        num_workers=5,
        num_requests=20
    )

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
        logger.info("Rate limiting is working correctly")
        return True
    else:
        logger.warning("No requests were rate limited - rate limiting may not be working")
        return False

def test_error_handling():
    """Test error handling for optimized endpoints"""
    logger.info("Testing error handling for optimized endpoints")
    
    # Test invalid product ID
    invalid_product_id = "invalid_id_12345"
    response = requests.get(f"{API_URL}/products/{invalid_product_id}")
    
    if response.status_code == 404:
        logger.info("Error handling for invalid product ID works correctly")
    else:
        logger.warning(f"Unexpected response for invalid product ID: {response.status_code} - {response.text}")
    
    # Test invalid category
    invalid_category = "nonexistent_category"
    response = requests.get(f"{API_URL}/products?category={invalid_category}")
    
    if response.status_code == 200:
        products = response.json()
        if len(products) == 0:
            logger.info("Error handling for invalid category works correctly (returns empty list)")
        else:
            logger.warning(f"Unexpected response for invalid category: returned {len(products)} products")
    else:
        logger.warning(f"Unexpected response code for invalid category: {response.status_code} - {response.text}")
    
    # Test invalid session ID for cart
    invalid_session_id = "invalid_session_12345"
    response = requests.get(f"{API_URL}/cart/{invalid_session_id}")
    
    if response.status_code == 200:
        # Should create a new cart with the invalid session ID
        logger.info("Error handling for invalid cart session ID works correctly (creates new cart)")
    else:
        logger.warning(f"Unexpected response for invalid cart session ID: {response.status_code} - {response.text}")
    
    # Test invalid auth token
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkQGV4YW1wbGUuY29tIiwiZXhwIjoxNjkzNTg3Mzk1fQ.invalid_signature"
    headers = {"Authorization": f"Bearer {invalid_token}"}
    response = requests.get(f"{API_URL}/auth/me", headers=headers)
    
    if response.status_code == 401:
        logger.info("Error handling for invalid auth token works correctly")
    else:
        logger.warning(f"Unexpected response for invalid auth token: {response.status_code} - {response.text}")

def run_performance_tests():
    """Run all performance tests"""
    logger.info("Starting performance tests for Mystery Box Store backend API")
    
    # Test critical endpoints
    test_products_endpoint_performance()
    test_categories_endpoint_performance()
    test_auth_me_endpoint_performance()
    test_cart_endpoint_performance()
    
    # Test rate limiting
    test_rate_limiting()
    
    # Test error handling
    test_error_handling()
    
    # Print summary
    logger.info("\n=== PERFORMANCE TEST SUMMARY ===")
    
    for endpoint, results in performance_results.items():
        if "avg_time" in results:
            logger.info(f"{endpoint}:")
            logger.info(f"  Avg response time: {results['avg_time']:.2f}ms")
            logger.info(f"  95th percentile: {results['p95_time']:.2f}ms")
            logger.info(f"  Success rate: {results['success_rate']:.2f}%")
        elif "cache_speedup" in results:
            logger.info(f"{endpoint}:")
            logger.info(f"  Cache speedup: {results['cache_speedup']:.2f}x")
            logger.info(f"  Response time reduction: {results['cache_reduction_percent']:.2f}%")
    
    return performance_results

if __name__ == "__main__":
    run_performance_tests()