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

def admin_login():
    """Login as admin and return token"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            logger.info("Admin login successful")
            return response_data["access_token"]
        else:
            logger.error(f"Failed to login as admin: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception during admin login: {str(e)}")
        return None

def test_delete_category(admin_token):
    """Test DELETE /api/admin/categories/{category_id}"""
    logger.info("Testing DELETE /api/admin/categories/{category_id}")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a test category
    category_data = {
        "name": f"Test Category {uuid.uuid4().hex[:8]}",
        "description": "Test category for deletion",
        "emoji": "🧪",
        "color": "#FF5733"
    }
    
    logger.info(f"Creating test category: {category_data['name']}")
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to create test category: {response.text}")
        return False
    
    category = response.json()
    category_id = category["id"]
    logger.info(f"Created category with ID: {category_id}")
    
    # Test 1: Try to delete non-existent category
    logger.info("Testing deletion of non-existent category")
    response = requests.delete(f"{API_URL}/admin/categories/non_existent_id", headers=headers)
    if response.status_code != 404:
        logger.error(f"Expected 404, got {response.status_code}: {response.text}")
        return False
    logger.info("Successfully verified 404 for non-existent category")
    
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
    
    logger.info(f"Creating test product with category: {category_id}")
    response = requests.post(f"{API_URL}/admin/products", json=product_data, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to create test product: {response.text}")
        return False
    
    product = response.json()
    product_id = product["id"]
    logger.info(f"Created product with ID: {product_id}")
    
    # Try to delete category with associated product
    logger.info("Testing deletion of category with associated products")
    response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
    if response.status_code != 400:
        logger.error(f"Expected 400, got {response.status_code}: {response.text}")
        return False
    logger.info("Successfully verified prevention of deleting category with products")
    
    # Delete the product
    logger.info(f"Deleting test product: {product_id}")
    response = requests.delete(f"{API_URL}/admin/products/{product_id}", headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to delete test product: {response.text}")
        return False
    
    # Test 3: Delete the category (should succeed now)
    logger.info(f"Testing deletion of category without products: {category_id}")
    response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to delete category: {response.status_code} - {response.text}")
        return False
    logger.info("Successfully deleted category")
    
    return True

def test_chat_assign(admin_token):
    """Test PUT /api/admin/chat/sessions/{session_id}/assign"""
    logger.info("Testing PUT /api/admin/chat/sessions/{session_id}/assign")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a test user
    test_user = {
        "email": f"test_user_{uuid.uuid4()}@example.com",
        "name": "Test User",
        "password": "Test@123"
    }
    
    logger.info(f"Creating test user: {test_user['email']}")
    response = requests.post(f"{API_URL}/auth/register", json=test_user)
    if response.status_code != 200:
        logger.error(f"Failed to create test user: {response.text}")
        return False
    
    user_data = response.json()
    user_token = user_data["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    # Create a chat session
    session_data = {"subject": "Test Chat Session"}
    logger.info("Creating test chat session")
    response = requests.post(f"{API_URL}/chat/sessions", json=session_data, headers=user_headers)
    if response.status_code != 200:
        logger.error(f"Failed to create chat session: {response.text}")
        return False
    
    session = response.json()
    session_id = session["id"]
    logger.info(f"Created chat session with ID: {session_id}")
    
    # Send a message
    message_data = {"message": "This is a test message"}
    logger.info("Sending test message to chat session")
    response = requests.post(f"{API_URL}/chat/sessions/{session_id}/messages", json=message_data, headers=user_headers)
    if response.status_code != 200:
        logger.error(f"Failed to send chat message: {response.text}")
        return False
    
    # Test assign session to admin
    logger.info(f"Assigning chat session to admin: {session_id}")
    response = requests.put(f"{API_URL}/admin/chat/sessions/{session_id}/assign", headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to assign chat session: {response.status_code} - {response.text}")
        return False
    
    # Get messages to check for automatic message
    logger.info("Getting chat messages to check for automatic message")
    response = requests.get(f"{API_URL}/chat/sessions/{session_id}/messages", headers=user_headers)
    if response.status_code != 200:
        logger.error(f"Failed to get chat messages: {response.text}")
        return False
    
    messages = response.json()
    
    # Check if there's an automatic message from admin
    auto_message_found = False
    expected_message = f"Olá {test_user['name']}, estou a verificar a mensagem e já darei apoio."
    
    for message in messages:
        if message["sender_type"] == "agent" and message["message"] == expected_message:
            auto_message_found = True
            break
    
    if auto_message_found:
        logger.info(f"Found automatic message: '{expected_message}'")
    else:
        logger.error("Automatic message not found")
        return False
    
    # Check if session is assigned to admin
    logger.info("Checking if session is assigned to admin")
    response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to get admin chat sessions: {response.text}")
        return False
    
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
        logger.info("Session correctly assigned to admin")
    else:
        logger.error("Session not found or not assigned to admin")
        return False
    
    return True

def test_other_endpoints(admin_token):
    """Test other endpoints to ensure they still work"""
    logger.info("Testing other endpoints")
    
    # Test GET /api/categories
    logger.info("Testing GET /api/categories")
    response = requests.get(f"{API_URL}/categories")
    if response.status_code != 200:
        logger.error(f"Failed to list categories: {response.status_code} - {response.text}")
        return False
    
    categories = response.json()
    if not categories or not isinstance(categories, list):
        logger.error("No categories returned or invalid format")
        return False
    
    logger.info(f"Found {len(categories)} categories")
    
    # Test POST /api/admin/categories
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    category_data = {
        "name": f"Test Category {uuid.uuid4().hex[:8]}",
        "description": "Test category creation",
        "emoji": "🧪",
        "color": "#3366FF"
    }
    
    logger.info(f"Testing POST /api/admin/categories with {category_data['name']}")
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to create category: {response.status_code} - {response.text}")
        return False
    
    category = response.json()
    if not category or not category.get("id"):
        logger.error("Invalid category data returned")
        return False
    
    logger.info(f"Created category: {category['name']}")
    
    # Test GET /api/admin/chat/sessions
    logger.info("Testing GET /api/admin/chat/sessions")
    response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to list chat sessions: {response.status_code} - {response.text}")
        return False
    
    sessions = response.json()
    if not isinstance(sessions, list):
        logger.error("Invalid sessions data returned")
        return False
    
    logger.info(f"Found {len(sessions)} chat sessions")
    
    return True

def run_tests():
    """Run all tests"""
    logger.info("Starting tests for corrected functionality")
    
    # Login as admin
    admin_token = admin_login()
    if not admin_token:
        logger.error("Admin login failed, cannot proceed with tests")
        return False
    
    # Test category deletion
    category_test_result = test_delete_category(admin_token)
    
    # Test chat session assignment with automatic message
    chat_test_result = test_chat_assign(admin_token)
    
    # Test other endpoints
    other_endpoints_result = test_other_endpoints(admin_token)
    
    # Print summary
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"Category Deletion Tests: {'PASSED' if category_test_result else 'FAILED'}")
    logger.info(f"Chat Assignment Tests: {'PASSED' if chat_test_result else 'FAILED'}")
    logger.info(f"Other Endpoints Tests: {'PASSED' if other_endpoints_result else 'FAILED'}")
    
    return category_test_result and chat_test_result and other_endpoints_result

if __name__ == "__main__":
    run_tests()