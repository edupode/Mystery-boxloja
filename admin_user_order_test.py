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

# Test data
TEST_USER = {
    "email": f"test_user_{uuid.uuid4()}@example.com",
    "name": "Test User",
    "password": "Test@123"
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

def test_register_user():
    """Register a test user for admin operations"""
    try:
        response = requests.post(f"{API_URL}/auth/register", json=TEST_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store token and user ID for later tests
            test_results["user_token"] = response_data["access_token"]
            test_results["user_id"] = response_data["user"]["id"]
            return log_test_result("User Registration", True, f"Created user: {TEST_USER['email']}")
        else:
            return log_test_result("User Registration", False, f"Failed to register user: {response.text}")
    except Exception as e:
        return log_test_result("User Registration", False, f"Exception: {str(e)}")

def test_admin_list_users():
    """Test GET /api/admin/users endpoint"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin List Users", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        
        if response.status_code != 200:
            return log_test_result("Admin List Users", False, f"Failed: {response.text}")
        
        users = response.json()
        if not isinstance(users, list):
            return log_test_result("Admin List Users", False, "Invalid users data")
        
        # Check if our test user is in the list
        if "user_id" in test_results:
            user_found = any(u["id"] == test_results["user_id"] for u in users)
            if not user_found:
                return log_test_result("Admin List Users", False, "Test user not found in user list")
        
        return log_test_result("Admin List Users", True, f"Successfully listed {len(users)} users")
    except Exception as e:
        return log_test_result("Admin List Users", False, f"Exception: {str(e)}")

def test_admin_change_user_password():
    """Test PUT /api/admin/users/{user_id}/password endpoint"""
    if "admin_token" not in test_results or "user_id" not in test_results:
        if "admin_token" not in test_results:
            test_admin_login()
        if "user_id" not in test_results:
            test_register_user()
        if "admin_token" not in test_results or "user_id" not in test_results:
            return log_test_result("Admin Change User Password", False, "Admin login and test user required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        new_password = "NewPassword123"
        
        response = requests.put(
            f"{API_URL}/admin/users/{test_results['user_id']}/password", 
            json={"new_password": new_password},
            headers=headers
        )
        
        if response.status_code != 200:
            return log_test_result("Admin Change User Password", False, f"Failed: {response.text}")
        
        # Verify password change by trying to login with new password
        login_response = requests.post(f"{API_URL}/auth/login", json={
            "email": TEST_USER["email"],
            "password": new_password
        })
        
        if login_response.status_code != 200 or "access_token" not in login_response.json():
            return log_test_result("Admin Change User Password", False, "Password change verification failed")
        
        return log_test_result("Admin Change User Password", True, "Successfully changed user password")
    except Exception as e:
        return log_test_result("Admin Change User Password", False, f"Exception: {str(e)}")

def test_admin_delete_user():
    """Test DELETE /api/admin/users/{user_id} endpoint"""
    if "admin_token" not in test_results or "user_id" not in test_results:
        if "admin_token" not in test_results:
            test_admin_login()
        if "user_id" not in test_results:
            test_register_user()
        if "admin_token" not in test_results or "user_id" not in test_results:
            return log_test_result("Admin Delete User", False, "Admin login and test user required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        response = requests.delete(
            f"{API_URL}/admin/users/{test_results['user_id']}", 
            headers=headers
        )
        
        if response.status_code != 200:
            return log_test_result("Admin Delete User", False, f"Failed: {response.text}")
        
        # Verify user deletion by trying to get user list and checking if user is gone
        list_response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if list_response.status_code != 200:
            return log_test_result("Admin Delete User Verification", False, f"Failed to get user list: {list_response.text}")
        
        users = list_response.json()
        if any(u["id"] == test_results["user_id"] for u in users):
            return log_test_result("Admin Delete User", False, "User still exists after deletion")
        
        return log_test_result("Admin Delete User", True, "Successfully deleted user")
    except Exception as e:
        return log_test_result("Admin Delete User", False, f"Exception: {str(e)}")

def test_admin_bulk_make_admin():
    """Test POST /api/admin/users/bulk-make-admin endpoint"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Bulk Make Admin", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Create multiple test users
        test_users = []
        for i in range(3):
            user_data = {
                "email": f"test_admin_bulk_{uuid.uuid4()}@example.com",
                "name": f"Test Bulk User {i+1}",
                "password": "Test@123"
            }
            
            response = requests.post(f"{API_URL}/auth/register", json=user_data)
            if response.status_code == 200:
                user_id = response.json()["user"]["id"]
                test_users.append({"id": user_id, "email": user_data["email"]})
        
        if not test_users:
            return log_test_result("Admin Bulk Make Admin", False, "Failed to create test users")
        
        # Get user IDs for bulk operation
        user_ids = [user["id"] for user in test_users]
        
        # Make users admin in bulk
        response = requests.post(
            f"{API_URL}/admin/users/bulk-make-admin", 
            json={"user_ids": user_ids},
            headers=headers
        )
        
        if response.status_code != 200:
            return log_test_result("Admin Bulk Make Admin", False, f"Failed: {response.text}")
        
        # Verify users are now admins
        list_response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if list_response.status_code != 200:
            return log_test_result("Admin Bulk Make Admin Verification", False, f"Failed to get user list: {list_response.text}")
        
        users = list_response.json()
        for test_user in test_users:
            user = next((u for u in users if u["id"] == test_user["id"]), None)
            if not user or not user.get("is_admin"):
                return log_test_result("Admin Bulk Make Admin", False, f"User {test_user['email']} not made admin")
        
        return log_test_result("Admin Bulk Make Admin", True, f"Successfully made {len(test_users)} users admin")
    except Exception as e:
        return log_test_result("Admin Bulk Make Admin", False, f"Exception: {str(e)}")

def test_admin_orders_list():
    """Test GET /api/admin/orders endpoint with order prioritization"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Orders List", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        response = requests.get(f"{API_URL}/admin/orders", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Orders List", False, f"Failed: {response.text}")
        
        orders = response.json()
        if not isinstance(orders, list):
            return log_test_result("Admin Orders List", False, "Invalid orders data")
        
        # Check order prioritization logic
        # 1. Cancelled/delivered orders should be hidden
        # 2. Shipped orders should be at the bottom
        # 3. Processing/pending/confirmed orders should be at the top
        
        # Check if cancelled/delivered orders are hidden
        cancelled_delivered = [o for o in orders if o.get("order_status") in ["cancelled", "delivered"]]
        if cancelled_delivered:
            return log_test_result("Admin Orders List", False, "Cancelled/delivered orders are not hidden")
        
        # Check if processing/pending/confirmed orders are before shipped orders
        top_priority_statuses = ["pending", "processing", "confirmed"]
        bottom_priority_status = "shipped"
        
        # Find first shipped order index
        shipped_index = next((i for i, o in enumerate(orders) if o.get("order_status") == bottom_priority_status), len(orders))
        
        # Check if any top priority order appears after a shipped order
        for i in range(shipped_index, len(orders)):
            if orders[i].get("order_status") in top_priority_statuses:
                return log_test_result("Admin Orders List", False, "Top priority order found after shipped order")
        
        return log_test_result("Admin Orders List", True, f"Successfully listed {len(orders)} orders with correct prioritization")
    except Exception as e:
        return log_test_result("Admin Orders List", False, f"Exception: {str(e)}")

def test_email_system():
    """Test if email sending functionality works with Resend API"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Email System", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Test discount email
        discount_params = {
            "user_email": "test@example.com",
            "user_name": "Test User",
            "coupon_code": "TESTDISCOUNT",
            "discount_value": 15.0,
            "discount_type": "percentage",
            "expiry_date": "31/12/2024"
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-discount", params=discount_params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Email System - Discount", False, f"Failed: {response.text}")
        
        # Test birthday email
        birthday_params = {
            "user_email": "test@example.com",
            "user_name": "Test User",
            "coupon_code": "BIRTHDAY2024",
            "discount_value": 20.0
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-birthday", params=birthday_params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Email System - Birthday", False, f"Failed: {response.text}")
        
        return log_test_result("Email System", True, "Successfully sent test emails using Resend API")
    except Exception as e:
        return log_test_result("Email System", False, f"Exception: {str(e)}")

def run_admin_user_order_tests():
    """Run all admin user and order management tests"""
    logger.info("Starting admin user and order management tests")
    
    # Admin authentication
    test_admin_login()
    
    # User management tests
    test_register_user()
    test_admin_list_users()
    test_admin_change_user_password()
    test_admin_bulk_make_admin()
    test_admin_delete_user()
    
    # Order management tests
    test_admin_orders_list()
    
    # Email system test
    test_email_system()
    
    # Print summary
    logger.info("\n=== ADMIN USER & ORDER MANAGEMENT TEST SUMMARY ===")
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
    run_admin_user_order_tests()