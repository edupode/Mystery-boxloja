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

def test_resend_status():
    """Test Resend API status endpoint"""
    try:
        response = requests.get(f"{API_URL}/test/resend-status")
        if response.status_code != 200:
            return log_test_result("Resend API Status", False, f"Failed: {response.text}")
        
        status_data = response.json()
        if not status_data.get("success"):
            return log_test_result("Resend API Status", False, f"API not working: {status_data.get('message', 'No message')}")
        
        return log_test_result("Resend API Status", True, f"API is working: {status_data.get('message', '')}")
    except Exception as e:
        return log_test_result("Resend API Status", False, f"Exception: {str(e)}")

def test_send_test_email():
    """Test sending a test email"""
    try:
        test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        response = requests.post(f"{API_URL}/test/send-email", json={
            "to_email": test_email,
            "subject": "Test Email",
            "html_content": "<h1>Test Email</h1><p>This is a test email from Mystery Box Store.</p>"
        })
        
        if response.status_code != 200:
            return log_test_result("Send Test Email", False, f"Failed: {response.text}")
        
        email_data = response.json()
        if not email_data.get("success"):
            return log_test_result("Send Test Email", False, f"Email not sent: {email_data.get('error', 'No error message')}")
        
        message_id = email_data.get("message_id")
        if not message_id:
            return log_test_result("Send Test Email", False, "No message ID returned")
        
        return log_test_result("Send Test Email", True, f"Email sent successfully with ID: {message_id}")
    except Exception as e:
        return log_test_result("Send Test Email", False, f"Exception: {str(e)}")

def test_welcome_email():
    """Test welcome email by registering a new user"""
    try:
        new_user = {
            "email": f"welcome_test_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Welcome Test User",
            "password": "Welcome@123"
        }
        
        response = requests.post(f"{API_URL}/auth/register", json=new_user)
        if response.status_code != 200:
            return log_test_result("Welcome Email", False, f"Failed to register user: {response.text}")
        
        # We can't directly verify the email was sent, but we can check if registration was successful
        return log_test_result("Welcome Email", True, f"User registered successfully, welcome email should be sent to {new_user['email']}")
    except Exception as e:
        return log_test_result("Welcome Email", False, f"Exception: {str(e)}")

def test_admin_login():
    """Test admin login to get token for other tests"""
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

def test_discount_email():
    """Test sending discount email"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Discount Email", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Test discount email
        params = {
            "user_email": TEST_USER["email"],
            "user_name": TEST_USER["name"],
            "coupon_code": "TESTDISCOUNT",
            "discount_value": 15.0,
            "discount_type": "percentage",
            "expiry_date": "31/12/2024"
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-discount", params=params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Discount Email", False, f"Failed: {response.text}")
        
        email_data = response.json()
        if not email_data.get("success"):
            return log_test_result("Discount Email", False, f"Email not sent: {email_data.get('error', 'No error message')}")
        
        message_id = email_data.get("message_id")
        if not message_id:
            return log_test_result("Discount Email", False, "No message ID returned")
        
        return log_test_result("Discount Email", True, f"Email sent successfully with ID: {message_id}")
    except Exception as e:
        return log_test_result("Discount Email", False, f"Exception: {str(e)}")

def test_birthday_email():
    """Test sending birthday email"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Birthday Email", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Test birthday email
        params = {
            "user_email": TEST_USER["email"],
            "user_name": TEST_USER["name"],
            "coupon_code": "BIRTHDAY2024",
            "discount_value": 20.0
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-birthday", params=params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Birthday Email", False, f"Failed: {response.text}")
        
        email_data = response.json()
        if not email_data.get("success"):
            return log_test_result("Birthday Email", False, f"Email not sent: {email_data.get('error', 'No error message')}")
        
        message_id = email_data.get("message_id")
        if not message_id:
            return log_test_result("Birthday Email", False, "No message ID returned")
        
        return log_test_result("Birthday Email", True, f"Email sent successfully with ID: {message_id}")
    except Exception as e:
        return log_test_result("Birthday Email", False, f"Exception: {str(e)}")

def test_otp_email():
    """Test OTP email for password reset"""
    try:
        # First, check if the endpoint exists
        response = requests.post(f"{API_URL}/auth/request-password-reset", json={
            "email": TEST_USER["email"]
        })
        
        # If the endpoint doesn't exist, it will return 404
        if response.status_code == 404:
            return log_test_result("OTP Email", False, "Password reset endpoint not found")
        
        # If the endpoint exists but returns an error, check if it's because the user doesn't exist
        if response.status_code != 200:
            error_message = response.json().get("detail", "")
            if "user not found" in error_message.lower():
                # This is expected since we're using a test email
                return log_test_result("OTP Email", True, "Endpoint exists and correctly reports user not found")
            else:
                return log_test_result("OTP Email", False, f"Failed: {response.text}")
        
        # If we get here, the endpoint exists and returned success
        return log_test_result("OTP Email", True, "Password reset endpoint exists and is working")
    except Exception as e:
        return log_test_result("OTP Email", False, f"Exception: {str(e)}")

def run_email_tests():
    """Run all email-related tests and return results"""
    logger.info("Starting email system tests for Mystery Box Store")
    
    # Test Resend API status
    test_resend_status()
    
    # Test sending a test email
    test_send_test_email()
    
    # Test welcome email
    test_welcome_email()
    
    # Test admin emails
    test_discount_email()
    test_birthday_email()
    
    # Test OTP email
    test_otp_email()
    
    # Print summary
    logger.info("\n=== EMAIL TESTS SUMMARY ===")
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
    run_email_tests()