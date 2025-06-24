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

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

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

def test_database_indexes():
    """Test database indexes by comparing query performance with and without filters"""
    logger.info("Testing database indexes effectiveness")
    
    # Test products with category filter vs no filter
    start_time = time.time()
    response = requests.get(f"{API_URL}/products")
    all_products_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("Database Indexes - Products", False, f"Failed to get products: {response.text}")
    
    products = response.json()
    if not products:
        return log_test_result("Database Indexes - Products", False, "No products returned")
    
    # Get a category from the first product
    category = products[0].get("category")
    if not category:
        return log_test_result("Database Indexes - Products", False, "No category found in products")
    
    # Test with category filter
    start_time = time.time()
    response = requests.get(f"{API_URL}/products?category={category}")
    filtered_products_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("Database Indexes - Products", False, f"Failed to get filtered products: {response.text}")
    
    # Calculate speedup
    if all_products_time > 0:
        index_speedup = all_products_time / filtered_products_time
    else:
        index_speedup = 0
    
    logger.info(f"Products query times:")
    logger.info(f"  All products: {all_products_time:.2f}ms")
    logger.info(f"  Filtered by category: {filtered_products_time:.2f}ms")
    logger.info(f"  Index speedup: {index_speedup:.2f}x")
    
    # Test orders with user_id filter (requires admin token)
    admin_token = admin_login()
    if not admin_token:
        return log_test_result("Database Indexes - Orders", False, "Failed to login as admin")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get all orders
    start_time = time.time()
    response = requests.get(f"{API_URL}/admin/orders", headers=headers)
    all_orders_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("Database Indexes - Orders", False, f"Failed to get orders: {response.text}")
    
    # Test with status filter
    start_time = time.time()
    response = requests.get(f"{API_URL}/admin/orders?status=pending", headers=headers)
    filtered_orders_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("Database Indexes - Orders", False, f"Failed to get filtered orders: {response.text}")
    
    # Calculate speedup
    if all_orders_time > 0:
        orders_index_speedup = all_orders_time / filtered_orders_time
    else:
        orders_index_speedup = 0
    
    logger.info(f"Orders query times:")
    logger.info(f"  All orders: {all_orders_time:.2f}ms")
    logger.info(f"  Filtered by status: {filtered_orders_time:.2f}ms")
    logger.info(f"  Index speedup: {orders_index_speedup:.2f}x")
    
    # Overall assessment
    if index_speedup >= 1.0 or orders_index_speedup >= 1.0:
        return log_test_result("Database Indexes", True, f"Indexes are effective. Products speedup: {index_speedup:.2f}x, Orders speedup: {orders_index_speedup:.2f}x")
    else:
        return log_test_result("Database Indexes", False, f"Indexes may not be effective. Products speedup: {index_speedup:.2f}x, Orders speedup: {orders_index_speedup:.2f}x")

def test_connection_pooling():
    """Test MongoDB connection pooling by making concurrent requests"""
    logger.info("Testing MongoDB connection pooling")
    
    # Make concurrent requests to test connection pooling
    num_concurrent = 20
    num_requests = 50
    
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
    
    logger.info(f"Making {num_requests} concurrent requests with {num_concurrent} workers")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        results = list(executor.map(make_request, range(num_requests)))
    
    success_count = 0
    response_times = []
    
    for success, time_ms in results:
        if success and time_ms is not None:
            success_count += 1
            response_times.append(time_ms)
    
    if not response_times:
        return log_test_result("Connection Pooling", False, "No successful requests")
    
    # Calculate statistics
    avg_time = statistics.mean(response_times)
    min_time = min(response_times)
    max_time = max(response_times)
    p95_time = np.percentile(response_times, 95)
    
    logger.info(f"Connection pooling test results:")
    logger.info(f"  Success rate: {(success_count / num_requests) * 100:.2f}%")
    logger.info(f"  Avg response time: {avg_time:.2f}ms")
    logger.info(f"  Min response time: {min_time:.2f}ms")
    logger.info(f"  Max response time: {max_time:.2f}ms")
    logger.info(f"  95th percentile: {p95_time:.2f}ms")
    
    # Connection pooling is working if we have a high success rate and reasonable response times
    if success_count >= num_requests * 0.9 and max_time < 2000:
        return log_test_result("Connection Pooling", True, f"Connection pooling appears to be working. Avg time: {avg_time:.2f}ms, Success rate: {(success_count / num_requests) * 100:.2f}%")
    else:
        return log_test_result("Connection Pooling", False, f"Connection pooling may not be effective. Avg time: {avg_time:.2f}ms, Success rate: {(success_count / num_requests) * 100:.2f}%")

def test_ttl_cache():
    """Test TTL cache by making repeated requests and checking response times"""
    logger.info("Testing TTL cache effectiveness")
    
    # Make initial request
    start_time = time.time()
    response = requests.get(f"{API_URL}/products")
    first_request_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("TTL Cache", False, f"Failed to make initial request: {response.text}")
    
    # Make several immediate requests
    immediate_times = []
    for i in range(5):
        start_time = time.time()
        response = requests.get(f"{API_URL}/products")
        request_time = (time.time() - start_time) * 1000
        immediate_times.append(request_time)
        
        if response.status_code != 200:
            return log_test_result("TTL Cache", False, f"Failed to make immediate request {i+1}: {response.text}")
    
    avg_immediate_time = statistics.mean(immediate_times)
    
    # Wait for cache to potentially expire (6 minutes to be safe)
    logger.info("Waiting for 10 seconds to test partial cache expiration...")
    time.sleep(10)
    
    # Make request after waiting
    start_time = time.time()
    response = requests.get(f"{API_URL}/products")
    after_wait_time = (time.time() - start_time) * 1000
    
    if response.status_code != 200:
        return log_test_result("TTL Cache", False, f"Failed to make request after waiting: {response.text}")
    
    logger.info(f"TTL cache test results:")
    logger.info(f"  First request time: {first_request_time:.2f}ms")
    logger.info(f"  Avg immediate request time: {avg_immediate_time:.2f}ms")
    logger.info(f"  Request time after 10s wait: {after_wait_time:.2f}ms")
    
    # Calculate cache effectiveness
    if first_request_time > 0:
        immediate_speedup = first_request_time / avg_immediate_time
    else:
        immediate_speedup = 0
    
    # TTL cache is working if immediate requests are faster than the first request
    if immediate_speedup > 1.0:
        return log_test_result("TTL Cache", True, f"TTL cache appears to be working. Speedup: {immediate_speedup:.2f}x")
    else:
        return log_test_result("TTL Cache", False, f"TTL cache may not be effective. Speedup: {immediate_speedup:.2f}x")

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

def run_optimization_tests():
    """Run tests for database optimizations and performance features"""
    logger.info("Starting optimization tests for Mystery Box Store backend API")
    
    # Test database indexes
    test_database_indexes()
    
    # Test connection pooling
    test_connection_pooling()
    
    # Test TTL cache
    test_ttl_cache()
    
    # Test rate limiting
    test_rate_limiting()
    
    # Print summary
    logger.info("\n=== OPTIMIZATION TEST SUMMARY ===")
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
        if result.get("message"):
            logger.info(f"  - {result['message']}")
    
    return test_results

if __name__ == "__main__":
    run_optimization_tests()