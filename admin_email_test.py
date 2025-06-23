import requests
import json
import logging
import os
from dotenv import load_dotenv
from datetime import datetime

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

# Test data as specified by the user
TEST_EMAIL = "edupodeptptpt@gmail.com"
TEST_NAME = "Eduardo Teste"
TEST_COUPON = "ADMIN10"
TEST_DISCOUNT = 15
TEST_DISCOUNT_TYPE = "percentage"
TEST_EXPIRY_DATE = "2025-07-01"

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    return success

def test_admin_login():
    """Test admin login and return the admin token"""
    try:
        logger.info(f"Attempting admin login with email: {ADMIN_USER['email']}")
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            admin_token = response_data["access_token"]
            log_test_result("Admin Login", True, "Successfully logged in as admin")
            return admin_token
        else:
            log_test_result("Admin Login", False, f"Failed to login as admin: {response.text}")
            return None
    except Exception as e:
        log_test_result("Admin Login", False, f"Exception during admin login: {str(e)}")
        return None

def test_send_discount_email(admin_token):
    """Test sending discount email using JSON body instead of query parameters"""
    if not admin_token:
        return log_test_result("Send Discount Email", False, "No admin token available")
    
    try:
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        # Using JSON body instead of query parameters
        discount_data = {
            "user_email": TEST_EMAIL,
            "user_name": TEST_NAME,
            "coupon_code": "ADMIN10",
            "discount_value": 10.0,
            "discount_type": "percentage",
            "expiry_date": "31/12/2024"
        }
        
        # Try with JSON body
        logger.info(f"Sending discount email to {TEST_EMAIL} with JSON body: {json.dumps(discount_data)}")
        response = requests.post(
            f"{API_URL}/admin/emails/send-discount", 
            json=discount_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            timestamp = result.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
            return log_test_result(
                "Send Discount Email", 
                True, 
                f"Email sent successfully to {TEST_EMAIL} at {timestamp}"
            )
        else:
            return log_test_result(
                "Send Discount Email", 
                False, 
                f"Failed to send discount email: Status {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        return log_test_result("Send Discount Email", False, f"Exception: {str(e)}")

def test_send_birthday_email(admin_token):
    """Test sending birthday email using JSON body instead of query parameters"""
    if not admin_token:
        return log_test_result("Send Birthday Email", False, "No admin token available")
    
    try:
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        # Using JSON body instead of query parameters
        birthday_data = {
            "user_email": TEST_EMAIL,
            "user_name": TEST_NAME,
            "coupon_code": "BIRTHDAY15",
            "discount_value": 15.0
        }
        
        # Try with JSON body
        logger.info(f"Sending birthday email to {TEST_EMAIL} with JSON body: {json.dumps(birthday_data)}")
        response = requests.post(
            f"{API_URL}/admin/emails/send-birthday", 
            json=birthday_data,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            timestamp = result.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
            return log_test_result(
                "Send Birthday Email", 
                True, 
                f"Email sent successfully to {TEST_EMAIL} at {timestamp}"
            )
        else:
            return log_test_result(
                "Send Birthday Email", 
                False, 
                f"Failed to send birthday email: Status {response.status_code}, Response: {response.text}"
            )
    except Exception as e:
        return log_test_result("Send Birthday Email", False, f"Exception: {str(e)}")

def run_tests():
    """Run all admin email tests"""
    logger.info("Starting admin email endpoint tests")
    
    # Login as admin
    admin_token = test_admin_login()
    if not admin_token:
        logger.error("Cannot proceed with tests: Admin login failed")
        return
    
    # Test discount email endpoint
    test_send_discount_email(admin_token)
    
    # Test birthday email endpoint
    test_send_birthday_email(admin_token)
    
    logger.info("Admin email endpoint tests completed")

if __name__ == "__main__":
    run_tests()