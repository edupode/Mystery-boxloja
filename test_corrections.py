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

def admin_login():
    """Login as admin and return token"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store admin token
            test_results["admin_token"] = response_data["access_token"]
            log_test_result("Admin Login", True)
            return response_data["access_token"]
        else:
            log_test_result("Admin Login", False, f"Failed to login as admin: {response.text}")
            return None
    except Exception as e:
        log_test_result("Admin Login", False, f"Exception: {str(e)}")
        return None

def test_delete_category():
    """Test DELETE /api/admin/categories/{category_id}"""
    admin_token = test_results.get("admin_token") or admin_login()
    if not admin_token:
        return log_test_result("Delete Category", False, "Admin login required")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        # First, create a test category
        category_data = {
            "name": f"Test Category {uuid.uuid4().hex[:8]}",
            "description": "Test category for deletion",
            "emoji": "🧪",
            "color": "#FF5733"
        }
        
        response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Test Category", False, f"Failed: {response.text}")
        
        category = response.json()
        category_id = category["id"]
        
        # Test 1: Try to delete non-existent category
        response = requests.delete(f"{API_URL}/admin/categories/non_existent_id", headers=headers)
        if response.status_code != 404:
            return log_test_result("Delete Non-existent Category", False, 
                                  f"Expected 404, got {response.status_code}: {response.text}")
        else:
            log_test_result("Delete Non-existent Category", True, "Correctly returned 404")
        
        # Test 2: Create a product with the category and try to delete the category
        product_data = {
            "name": f"Test Product {uuid.uuid4().hex[:8]}",
            "description": "Test product for category deletion test",
            "category": category_id,
            "price": 19.99,
            "subscription_prices": {
                "3_months": 17.99,
                "6_months": 16.99,
                "12_months": 15.99
            },
            "image_url": "https://example.com/test.jpg",
            "stock_quantity": 10,
            "featured": False
        }
        
        response = requests.post(f"{API_URL}/admin/products", json=product_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Test Product", False, f"Failed: {response.text}")
        
        product = response.json()
        product_id = product["id"]
        
        # Try to delete category with associated product
        response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
        if response.status_code != 400:
            return log_test_result("Delete Category with Products", False, 
                                  f"Expected 400, got {response.status_code}: {response.text}")
        else:
            log_test_result("Delete Category with Products", True, "Correctly prevented deletion of category with products")
        
        # Delete the product
        response = requests.delete(f"{API_URL}/admin/products/{product_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Delete Test Product", False, f"Failed: {response.text}")
        
        # Test 3: Delete the category (should succeed now)
        response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Delete Category", False, f"Failed: {response.status_code} - {response.text}")
        else:
            log_test_result("Delete Category", True, "Successfully deleted category")
        
        return log_test_result("Category Deletion Tests", True, "All category deletion tests passed")
    except Exception as e:
        return log_test_result("Category Deletion Tests", False, f"Exception: {str(e)}")

def test_chat_assign():
    """Test PUT /api/admin/chat/sessions/{session_id}/assign"""
    admin_token = test_results.get("admin_token") or admin_login()
    if not admin_token:
        return log_test_result("Chat Assign", False, "Admin login required")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    try:
        # Create a test user
        test_user = {
            "email": f"test_user_{uuid.uuid4()}@example.com",
            "name": "Test User",
            "password": "Test@123"
        }
        
        response = requests.post(f"{API_URL}/auth/register", json=test_user)
        if response.status_code != 200:
            return log_test_result("Create Test User", False, f"Failed: {response.text}")
        
        user_data = response.json()
        user_token = user_data["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Create a chat session
        session_data = {"subject": "Test Chat Session"}
        response = requests.post(f"{API_URL}/chat/sessions", json=session_data, headers=user_headers)
        if response.status_code != 200:
            return log_test_result("Create Chat Session", False, f"Failed: {response.text}")
        
        session = response.json()
        session_id = session["id"]
        
        # Send a message
        message_data = {"message": "This is a test message"}
        response = requests.post(f"{API_URL}/chat/sessions/{session_id}/messages", json=message_data, headers=user_headers)
        if response.status_code != 200:
            return log_test_result("Send Chat Message", False, f"Failed: {response.text}")
        
        # Test assign session to admin
        response = requests.put(f"{API_URL}/admin/chat/sessions/{session_id}/assign", headers=headers)
        if response.status_code != 200:
            return log_test_result("Assign Chat Session", False, f"Failed: {response.status_code} - {response.text}")
        
        # Get messages to check for automatic message
        response = requests.get(f"{API_URL}/chat/sessions/{session_id}/messages", headers=user_headers)
        if response.status_code != 200:
            return log_test_result("Get Chat Messages", False, f"Failed: {response.text}")
        
        messages = response.json()
        
        # Check if there's an automatic message from admin
        auto_message_found = False
        expected_message = f"Olá {test_user['name']}, estou a verificar a mensagem e já darei apoio."
        
        for message in messages:
            if message["sender_type"] == "agent" and message["message"] == expected_message:
                auto_message_found = True
                break
        
        if auto_message_found:
            log_test_result("Automatic Chat Message", True, f"Found automatic message: '{expected_message}'")
        else:
            log_test_result("Automatic Chat Message", False, "Automatic message not found")
        
        # Check if session is assigned to admin
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Get Admin Chat Sessions", False, f"Failed: {response.text}")
        
        sessions = response.json()
        session_found = False
        session_assigned = False
        
        for s in sessions:
            if s["id"] == session_id:
                session_found = True
                if s["agent_id"]:
                    session_assigned = True
                break
        
        if session_found and session_assigned:
            log_test_result("Chat Session Assignment", True, "Session correctly assigned to admin")
        else:
            log_test_result("Chat Session Assignment", False, "Session not found or not assigned to admin")
        
        return log_test_result("Chat Assign Tests", auto_message_found and session_assigned, 
                              "Chat session assignment and automatic message tests completed")
    except Exception as e:
        return log_test_result("Chat Assign Tests", False, f"Exception: {str(e)}")

def test_other_endpoints():
    """Test other endpoints to ensure they still work"""
    try:
        # Test GET /api/categories
        response = requests.get(f"{API_URL}/categories")
        if response.status_code != 200:
            return log_test_result("List Categories", False, f"Failed: {response.status_code} - {response.text}")
        
        categories = response.json()
        if not categories or not isinstance(categories, list):
            return log_test_result("List Categories", False, "No categories returned or invalid format")
        
        log_test_result("List Categories", True, f"Found {len(categories)} categories")
        
        # Test POST /api/admin/categories
        admin_token = test_results.get("admin_token") or admin_login()
        if not admin_token:
            return log_test_result("Create Category", False, "Admin login required")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        category_data = {
            "name": f"Test Category {uuid.uuid4().hex[:8]}",
            "description": "Test category creation",
            "emoji": "🧪",
            "color": "#3366FF"
        }
        
        response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Category", False, f"Failed: {response.status_code} - {response.text}")
        
        category = response.json()
        if not category or not category.get("id"):
            return log_test_result("Create Category", False, "Invalid category data returned")
        
        log_test_result("Create Category", True, f"Created category: {category['name']}")
        
        # Test GET /api/admin/chat/sessions
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("List Chat Sessions", False, f"Failed: {response.status_code} - {response.text}")
        
        sessions = response.json()
        if not isinstance(sessions, list):
            return log_test_result("List Chat Sessions", False, "Invalid sessions data returned")
        
        log_test_result("List Chat Sessions", True, f"Found {len(sessions)} chat sessions")
        
        return log_test_result("Other Endpoints", True, "All other endpoints are working correctly")
    except Exception as e:
        return log_test_result("Other Endpoints", False, f"Exception: {str(e)}")

def run_tests():
    """Run all tests and return results"""
    logger.info("Starting tests for corrected functionality")
    
    # Login as admin first
    admin_login()
    
    # Test category deletion
    test_delete_category()
    
    # Test chat session assignment with automatic message
    test_chat_assign()
    
    # Test other endpoints
    test_other_endpoints()
    
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