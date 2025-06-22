import requests
import json
import uuid
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
GOOGLE_CLIENT_ID = os.getenv('REACT_APP_GOOGLE_CLIENT_ID')

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

def test_login():
    """Test user login with email/password"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        })
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Update token
            test_results["auth_token"] = response_data["access_token"]
            return log_test_result("User Login", True)
        else:
            return log_test_result("User Login", False, f"Failed to login: {response.text}")
    except Exception as e:
        return log_test_result("User Login", False, f"Exception: {str(e)}")

def test_admin_login():
    """Test admin login"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store admin token
            test_results["admin_token"] = response_data["access_token"]
            return log_test_result("Admin Login", True)
        else:
            return log_test_result("Admin Login", False, f"Failed to login as admin: {response.text}")
    except Exception as e:
        return log_test_result("Admin Login", False, f"Exception: {str(e)}")

def test_verify_token():
    """Test JWT token verification"""
    if "auth_token" not in test_results:
        return log_test_result("Verify Token", False, "No auth token available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        response_data = response.json()
        
        if response.status_code == 200 and "email" in response_data:
            return log_test_result("Verify Token", True)
        else:
            return log_test_result("Verify Token", False, f"Failed to verify token: {response.text}")
    except Exception as e:
        return log_test_result("Verify Token", False, f"Exception: {str(e)}")

def test_google_oauth_endpoint_accessibility():
    """Test if the Google OAuth endpoint is accessible"""
    try:
        # Test with empty request (should fail but confirm endpoint exists)
        response = requests.post(f"{API_URL}/auth/google", json={})
        
        # We expect a 422 Unprocessable Entity because we're not providing a token
        # This confirms the endpoint exists and is processing requests
        if response.status_code == 422:
            return log_test_result(
                "Google OAuth Endpoint Accessibility", 
                True, 
                "Endpoint exists and correctly rejects empty requests"
            )
        else:
            return log_test_result(
                "Google OAuth Endpoint Accessibility", 
                False, 
                f"Unexpected status code: {response.status_code}, expected 422"
            )
    except Exception as e:
        return log_test_result(
            "Google OAuth Endpoint Accessibility", 
            False, 
            f"Exception: {str(e)}"
        )

def test_google_oauth_invalid_token():
    """Test Google OAuth with invalid token"""
    try:
        # Test with invalid token
        response = requests.post(f"{API_URL}/auth/google", json={"token": "invalid_token"})
        
        # We expect a 400 Bad Request for invalid token
        if response.status_code == 400 and "Invalid Google token" in response.text:
            return log_test_result(
                "Google OAuth Invalid Token", 
                True, 
                "Correctly rejects invalid token"
            )
        else:
            return log_test_result(
                "Google OAuth Invalid Token", 
                False, 
                f"Unexpected response: {response.status_code} - {response.text}"
            )
    except Exception as e:
        return log_test_result(
            "Google OAuth Invalid Token", 
            False, 
            f"Exception: {str(e)}"
        )

def test_google_client_id_configured():
    """Test if Google Client ID is properly configured"""
    try:
        if GOOGLE_CLIENT_ID:
            return log_test_result(
                "Google Client ID Configuration", 
                True, 
                f"Google Client ID is configured: {GOOGLE_CLIENT_ID[:10]}..."
            )
        else:
            return log_test_result(
                "Google Client ID Configuration", 
                False, 
                "Google Client ID is not configured in frontend/.env"
            )
    except Exception as e:
        return log_test_result(
            "Google Client ID Configuration", 
            False, 
            f"Exception: {str(e)}"
        )

def run_auth_tests():
    """Run all authentication tests"""
    logger.info("Starting authentication endpoint tests")
    
    # Test registration and login
    test_register()
    test_login()
    test_admin_login()
    test_verify_token()
    
    # Test Google OAuth
    test_google_oauth_endpoint_accessibility()
    test_google_oauth_invalid_token()
    test_google_client_id_configured()
    
    # Print summary
    logger.info("\n=== AUTHENTICATION TEST SUMMARY ===")
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
    run_auth_tests()