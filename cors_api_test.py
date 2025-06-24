import requests
import json
import time
import logging
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from statistics import mean, median

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"
FRONTEND_ORIGIN = "https://mystery-box-loja.vercel.app"

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

def test_cors_headers(endpoint):
    """Test CORS headers for a specific endpoint"""
    try:
        # Send OPTIONS request with Origin header to simulate preflight request
        headers = {
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type, Authorization"
        }
        
        response = requests.options(f"{API_URL}/{endpoint}", headers=headers)
        
        # Check CORS headers
        cors_headers = {
            "Access-Control-Allow-Origin": FRONTEND_ORIGIN,
            "Access-Control-Allow-Methods": None,  # We'll just check if it exists
            "Access-Control-Allow-Headers": None,  # We'll just check if it exists
        }
        
        missing_headers = []
        for header, expected_value in cors_headers.items():
            if header not in response.headers:
                missing_headers.append(header)
            elif expected_value and response.headers[header] != expected_value:
                missing_headers.append(f"{header} (expected: {expected_value}, got: {response.headers[header]})")
        
        if missing_headers:
            return log_test_result(f"CORS Headers - {endpoint}", False, 
                                  f"Missing or incorrect headers: {', '.join(missing_headers)}")
        
        # Also test with actual GET request
        headers = {"Origin": FRONTEND_ORIGIN}
        response = requests.get(f"{API_URL}/{endpoint}", headers=headers)
        
        if "Access-Control-Allow-Origin" not in response.headers:
            return log_test_result(f"CORS Headers - {endpoint}", False, 
                                  "Missing Access-Control-Allow-Origin in GET response")
        
        if response.headers["Access-Control-Allow-Origin"] != FRONTEND_ORIGIN:
            return log_test_result(f"CORS Headers - {endpoint}", False, 
                                  f"Incorrect Access-Control-Allow-Origin: {response.headers['Access-Control-Allow-Origin']}")
        
        return log_test_result(f"CORS Headers - {endpoint}", True, 
                              f"All CORS headers present and correct")
    except Exception as e:
        return log_test_result(f"CORS Headers - {endpoint}", False, f"Exception: {str(e)}")

def test_endpoint_performance(endpoint, params=None, num_requests=5):
    """Test endpoint performance"""
    try:
        url = f"{API_URL}/{endpoint}"
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{param_str}"
        
        response_times = []
        errors = 0
        
        for _ in range(num_requests):
            start_time = time.time()
            response = requests.get(url)
            end_time = time.time()
            
            if response.status_code == 200:
                response_times.append((end_time - start_time) * 1000)  # Convert to ms
            else:
                errors += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.2)
        
        if errors == num_requests:
            return log_test_result(f"Performance - {endpoint}", False, 
                                  f"All {num_requests} requests failed")
        
        avg_time = mean(response_times)
        med_time = median(response_times)
        max_time = max(response_times)
        success_rate = ((num_requests - errors) / num_requests) * 100
        
        # Check if performance is acceptable
        is_acceptable = avg_time < 2000 and success_rate >= 90  # Less than 2s avg and 90% success
        
        result_message = (
            f"Avg: {avg_time:.2f}ms, Median: {med_time:.2f}ms, Max: {max_time:.2f}ms, "
            f"Success rate: {success_rate:.1f}%"
        )
        
        return log_test_result(f"Performance - {endpoint}", is_acceptable, result_message)
    except Exception as e:
        return log_test_result(f"Performance - {endpoint}", False, f"Exception: {str(e)}")

def test_endpoint_response(endpoint, params=None, expected_status=200, expected_content_type="application/json"):
    """Test endpoint response format and status code"""
    try:
        url = f"{API_URL}/{endpoint}"
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{param_str}"
        
        response = requests.get(url)
        
        # Check status code
        if response.status_code != expected_status:
            return log_test_result(f"Response - {endpoint}", False, 
                                  f"Expected status {expected_status}, got {response.status_code}")
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if expected_content_type not in content_type:
            return log_test_result(f"Response - {endpoint}", False, 
                                  f"Expected content type {expected_content_type}, got {content_type}")
        
        # For JSON responses, check if it's valid JSON
        if expected_content_type == "application/json":
            try:
                data = response.json()
                
                # Check if it's empty
                if not data and not isinstance(data, (dict, list)):
                    return log_test_result(f"Response - {endpoint}", False, "Empty or invalid JSON response")
                
                # For lists, check if it has items
                if isinstance(data, list):
                    result_message = f"Valid JSON response with {len(data)} items"
                else:
                    result_message = "Valid JSON response"
                
                return log_test_result(f"Response - {endpoint}", True, result_message)
            except json.JSONDecodeError:
                return log_test_result(f"Response - {endpoint}", False, "Invalid JSON response")
        
        return log_test_result(f"Response - {endpoint}", True, "Valid response")
    except Exception as e:
        return log_test_result(f"Response - {endpoint}", False, f"Exception: {str(e)}")

def test_concurrent_requests(endpoint, num_concurrent=10):
    """Test endpoint under concurrent load"""
    try:
        url = f"{API_URL}/{endpoint}"
        
        success_count = 0
        response_times = []
        
        def make_request():
            try:
                start_time = time.time()
                response = requests.get(url)
                end_time = time.time()
                
                if response.status_code == 200:
                    return True, (end_time - start_time) * 1000  # Convert to ms
                return False, 0
            except Exception:
                return False, 0
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            results = list(executor.map(lambda _: make_request(), range(num_concurrent)))
        
        for success, time_ms in results:
            if success:
                success_count += 1
                response_times.append(time_ms)
        
        success_rate = (success_count / num_concurrent) * 100
        
        if not response_times:
            return log_test_result(f"Concurrent - {endpoint}", False, "All requests failed")
        
        avg_time = mean(response_times)
        max_time = max(response_times)
        
        # Check if performance under load is acceptable
        is_acceptable = avg_time < 5000 and success_rate >= 80  # Less than 5s avg and 80% success under load
        
        result_message = (
            f"{success_count}/{num_concurrent} successful ({success_rate:.1f}%), "
            f"Avg: {avg_time:.2f}ms, Max: {max_time:.2f}ms"
        )
        
        return log_test_result(f"Concurrent - {endpoint}", is_acceptable, result_message)
    except Exception as e:
        return log_test_result(f"Concurrent - {endpoint}", False, f"Exception: {str(e)}")

def test_cache_effectiveness(endpoint, params=None, num_requests=3):
    """Test if endpoint uses caching effectively"""
    try:
        url = f"{API_URL}/{endpoint}"
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{param_str}"
        
        # First request (cold cache)
        start_time = time.time()
        response = requests.get(url)
        cold_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code != 200:
            return log_test_result(f"Cache - {endpoint}", False, f"Initial request failed with status {response.status_code}")
        
        # Subsequent requests (warm cache)
        warm_times = []
        for _ in range(num_requests):
            start_time = time.time()
            response = requests.get(url)
            warm_times.append((time.time() - start_time) * 1000)  # Convert to ms
            
            if response.status_code != 200:
                return log_test_result(f"Cache - {endpoint}", False, f"Subsequent request failed with status {response.status_code}")
            
            # Small delay
            time.sleep(0.1)
        
        avg_warm_time = mean(warm_times)
        
        # Calculate speedup
        speedup = cold_time / avg_warm_time if avg_warm_time > 0 else 0
        
        # Check if caching is effective
        is_effective = speedup > 1.2  # At least 20% speedup
        
        result_message = (
            f"Cold: {cold_time:.2f}ms, Warm avg: {avg_warm_time:.2f}ms, "
            f"Speedup: {speedup:.2f}x"
        )
        
        return log_test_result(f"Cache - {endpoint}", is_effective, result_message)
    except Exception as e:
        return log_test_result(f"Cache - {endpoint}", False, f"Exception: {str(e)}")

def run_all_tests():
    """Run all tests and return results"""
    logger.info("Starting CORS and API endpoint tests for Mystery Box Store")
    
    # Endpoints to test
    endpoints = [
        "products",
        "products?featured=true",
        "categories",
        "health"
    ]
    
    # Test CORS headers for each endpoint
    for endpoint in endpoints:
        test_cors_headers(endpoint)
    
    # Test response format and content for each endpoint
    for endpoint in endpoints:
        test_endpoint_response(endpoint)
    
    # Test performance for each endpoint
    for endpoint in endpoints:
        test_endpoint_performance(endpoint)
    
    # Test cache effectiveness for key endpoints
    test_cache_effectiveness("products")
    test_cache_effectiveness("categories")
    
    # Test concurrent requests for key endpoints
    test_concurrent_requests("products")
    test_concurrent_requests("categories")
    
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
    run_all_tests()