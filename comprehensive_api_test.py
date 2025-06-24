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

def test_cors_headers(endpoint, method="GET"):
    """Test CORS headers for a specific endpoint"""
    try:
        # Send OPTIONS request with Origin header to simulate preflight request
        headers = {
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": method,
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
        
        # Also test with actual request
        headers = {"Origin": FRONTEND_ORIGIN}
        
        if method == "GET":
            response = requests.get(f"{API_URL}/{endpoint}", headers=headers)
        elif method == "POST":
            response = requests.post(f"{API_URL}/{endpoint}", headers=headers, json={})
        
        if "Access-Control-Allow-Origin" not in response.headers:
            return log_test_result(f"CORS Headers - {endpoint}", False, 
                                  f"Missing Access-Control-Allow-Origin in {method} response")
        
        if response.headers["Access-Control-Allow-Origin"] != FRONTEND_ORIGIN:
            return log_test_result(f"CORS Headers - {endpoint}", False, 
                                  f"Incorrect Access-Control-Allow-Origin: {response.headers['Access-Control-Allow-Origin']}")
        
        return log_test_result(f"CORS Headers - {endpoint}", True, 
                              f"All CORS headers present and correct")
    except Exception as e:
        return log_test_result(f"CORS Headers - {endpoint}", False, f"Exception: {str(e)}")

def test_endpoint_performance(endpoint, params=None, method="GET", data=None, num_requests=5):
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
            
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data or {})
            
            end_time = time.time()
            
            if response.status_code in [200, 201, 204]:
                response_times.append((end_time - start_time) * 1000)  # Convert to ms
            else:
                errors += 1
                logger.warning(f"Request to {url} failed with status {response.status_code}: {response.text}")
            
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

def test_endpoint_response(endpoint, params=None, method="GET", data=None, expected_status=200):
    """Test endpoint response format and status code"""
    try:
        url = f"{API_URL}/{endpoint}"
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{param_str}"
        
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data or {})
        
        # Check status code
        if response.status_code != expected_status:
            return log_test_result(f"Response - {endpoint}", False, 
                                  f"Expected status {expected_status}, got {response.status_code}: {response.text}")
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type and response.status_code != 204:
            return log_test_result(f"Response - {endpoint}", False, 
                                  f"Expected JSON content type, got {content_type}")
        
        # For JSON responses, check if it's valid JSON
        if response.status_code != 204:  # Skip for 204 No Content
            try:
                data = response.json()
                
                # Check if it's empty when it shouldn't be
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

def test_concurrent_requests(endpoint, params=None, num_concurrent=10):
    """Test endpoint under concurrent load"""
    try:
        url = f"{API_URL}/{endpoint}"
        if params:
            param_str = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{param_str}"
        
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

def run_all_tests():
    """Run all tests and return results"""
    logger.info("Starting comprehensive API endpoint tests for Mystery Box Store")
    
    # Test CORS headers for key endpoints
    test_cors_headers("products")
    test_cors_headers("products?featured=true")
    test_cors_headers("categories")
    test_cors_headers("health")
    
    # Test response format for key endpoints
    test_endpoint_response("products")
    test_endpoint_response("products?featured=true")
    test_endpoint_response("categories")
    test_endpoint_response("health")
    
    # Test performance for key endpoints
    test_endpoint_performance("products")
    test_endpoint_performance("products?featured=true")
    test_endpoint_performance("categories")
    test_endpoint_performance("health")
    
    # Test concurrent requests for key endpoints
    test_concurrent_requests("products")
    test_concurrent_requests("products?featured=true")
    test_concurrent_requests("categories")
    test_concurrent_requests("health")
    
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