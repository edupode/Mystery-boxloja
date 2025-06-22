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

# Admin credentials
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

def test_admin_login():
    """Test admin login"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store admin token
            test_results["admin_token"] = response_data["access_token"]
            return log_test_result("Admin Login", True, "Admin login successful")
        else:
            return log_test_result("Admin Login", False, f"Failed to login as admin: {response.text}")
    except Exception as e:
        return log_test_result("Admin Login", False, f"Exception: {str(e)}")

def test_send_otp():
    """Test sending OTP for password change"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Send OTP", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Send OTP request
        data = {"email": ADMIN_USER["email"]}
        response = requests.post(f"{API_URL}/auth/send-otp", json=data, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"OTP Response: {response_data}")
            return log_test_result("Send OTP", True, "OTP sent successfully")
        else:
            return log_test_result("Send OTP", False, f"Failed to send OTP: {response.text}")
    except Exception as e:
        return log_test_result("Send OTP", False, f"Exception: {str(e)}")

def test_change_password_invalid_otp():
    """Test changing password with invalid OTP"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Change Password (Invalid OTP)", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Try to change password with invalid OTP
        data = {
            "current_password": ADMIN_USER["password"],
            "new_password": "admin123",  # Same password for testing
            "otp_code": "123456"  # Invalid OTP
        }
        
        response = requests.post(f"{API_URL}/auth/change-password", json=data, headers=headers)
        
        # Should fail with 400 status code
        if response.status_code == 400 and "OTP" in response.text:
            return log_test_result("Change Password (Invalid OTP)", True, "Correctly rejected invalid OTP")
        else:
            return log_test_result("Change Password (Invalid OTP)", False, f"Unexpected response: {response.status_code} - {response.text}")
    except Exception as e:
        return log_test_result("Change Password (Invalid OTP)", False, f"Exception: {str(e)}")

def test_change_password_missing_current_password():
    """Test changing password without current password"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Change Password (Missing Current)", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Try to change password without current password
        data = {
            "new_password": "admin123",  # Same password for testing
            "otp_code": "123456"
        }
        
        response = requests.post(f"{API_URL}/auth/change-password", json=data, headers=headers)
        
        # Should fail with 400 status code
        if response.status_code == 400 and "obrigatórios" in response.text:
            return log_test_result("Change Password (Missing Current)", True, "Correctly rejected missing current password")
        else:
            return log_test_result("Change Password (Missing Current)", False, f"Unexpected response: {response.status_code} - {response.text}")
    except Exception as e:
        return log_test_result("Change Password (Missing Current)", False, f"Exception: {str(e)}")

def test_admin_chat_sessions():
    """Test admin chat sessions endpoint"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Chat Sessions", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Get all chat sessions
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        
        if response.status_code == 200:
            sessions = response.json()
            logger.info(f"Found {len(sessions)} chat sessions")
            
            # Store a session ID if available for the next test
            if sessions:
                test_results["chat_session_id"] = sessions[0]["id"]
            
            return log_test_result("Admin Chat Sessions", True, f"Successfully retrieved {len(sessions)} chat sessions")
        else:
            return log_test_result("Admin Chat Sessions", False, f"Failed to get chat sessions: {response.text}")
    except Exception as e:
        return log_test_result("Admin Chat Sessions", False, f"Exception: {str(e)}")

def test_admin_assign_chat_session():
    """Test assigning chat session to admin"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Assign Chat Session", False, "Admin login required")
    
    if "chat_session_id" not in test_results:
        test_admin_chat_sessions()
        if "chat_session_id" not in test_results:
            return log_test_result("Assign Chat Session", False, "No chat sessions available")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        session_id = test_results["chat_session_id"]
        
        # Assign chat session to admin
        response = requests.put(f"{API_URL}/admin/chat/sessions/{session_id}/assign", headers=headers)
        
        if response.status_code == 200:
            return log_test_result("Assign Chat Session", True, f"Successfully assigned session {session_id} to admin")
        else:
            return log_test_result("Assign Chat Session", False, f"Failed to assign chat session: {response.text}")
    except Exception as e:
        return log_test_result("Assign Chat Session", False, f"Exception: {str(e)}")

def run_tests():
    """Run all tests and return results"""
    logger.info("Starting OTP and Chat tests for Mystery Box Store")
    
    # Authentication
    test_admin_login()
    
    # OTP tests
    test_send_otp()
    test_change_password_invalid_otp()
    test_change_password_missing_current_password()
    
    # Chat tests
    test_admin_chat_sessions()
    test_admin_assign_chat_session()
    
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