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

# Admin credentials
ADMIN_USER = {
    "email": "eduardocorreia3344@gmail.com",
    "password": "admin123"
}

def test_category_deletion():
    """Test DELETE /api/admin/categories/{category_id}"""
    logger.info("Testing category deletion endpoint")
    
    # Login as admin
    response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
    if response.status_code != 200:
        logger.error(f"Admin login failed: {response.text}")
        return False
    
    admin_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a test category
    category_name = f"Test Category {uuid.uuid4().hex[:6]}"
    category_data = {
        "name": category_name,
        "description": "Test category for deletion",
        "emoji": "🧪",
        "color": "#FF5733"
    }
    
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to create test category: {response.text}")
        return False
    
    category_id = response.json()["id"]
    logger.info(f"Created test category: {category_name} with ID: {category_id}")
    
    # Test 1: Try to delete non-existent category
    response = requests.delete(f"{API_URL}/admin/categories/non_existent_id", headers=headers)
    if response.status_code == 404:
        logger.info("✅ Successfully verified 404 for non-existent category")
    else:
        logger.error(f"❌ Expected 404, got {response.status_code}: {response.text}")
        return False
    
    # Test 2: Create a product with the category
    product_name = f"Test Product {uuid.uuid4().hex[:6]}"
    product_data = {
        "name": product_name,
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
        logger.error(f"Failed to create test product: {response.text}")
        return False
    
    product_id = response.json()["id"]
    logger.info(f"Created test product: {product_name} with ID: {product_id}")
    
    # Try to delete category with associated product
    response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
    if response.status_code == 400:
        logger.info("✅ Successfully verified prevention of deleting category with products")
    else:
        logger.error(f"❌ Expected 400, got {response.status_code}: {response.text}")
        return False
    
    # Delete the product
    response = requests.delete(f"{API_URL}/admin/products/{product_id}", headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to delete test product: {response.text}")
        return False
    
    logger.info(f"Deleted test product: {product_id}")
    
    # Now try to delete the category (should succeed)
    response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
    if response.status_code == 200:
        logger.info("✅ Successfully deleted category after removing associated products")
    else:
        logger.error(f"❌ Failed to delete category: {response.status_code} - {response.text}")
        return False
    
    logger.info("✅ All category deletion tests passed")
    return True

def test_chat_assign():
    """Test PUT /api/admin/chat/sessions/{session_id}/assign"""
    logger.info("Testing chat session assignment with automatic message")
    
    # Login as admin
    response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
    if response.status_code != 200:
        logger.error(f"Admin login failed: {response.text}")
        return False
    
    admin_token = response.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a test user
    test_user = {
        "email": f"test_user_{uuid.uuid4().hex[:8]}@example.com",
        "name": "Test User",
        "password": "Test@123"
    }
    
    response = requests.post(f"{API_URL}/auth/register", json=test_user)
    if response.status_code != 200:
        logger.error(f"Failed to create test user: {response.text}")
        return False
    
    user_token = response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    # Create a chat session
    session_data = {"subject": "Test Chat Session"}
    response = requests.post(f"{API_URL}/chat/sessions", json=session_data, headers=user_headers)
    if response.status_code != 200:
        logger.error(f"Failed to create chat session: {response.text}")
        return False
    
    session_id = response.json()["id"]
    logger.info(f"Created test chat session with ID: {session_id}")
    
    # Send a test message
    message_data = {"message": "This is a test message"}
    response = requests.post(f"{API_URL}/chat/sessions/{session_id}/messages", json=message_data, headers=user_headers)
    if response.status_code != 200:
        logger.error(f"Failed to send test message: {response.text}")
        return False
    
    # Assign the session to admin
    response = requests.put(f"{API_URL}/admin/chat/sessions/{session_id}/assign", headers=admin_headers)
    if response.status_code != 200:
        logger.error(f"Failed to assign chat session: {response.status_code} - {response.text}")
        return False
    
    logger.info("Chat session assigned to admin")
    
    # Get messages to check for automatic message
    response = requests.get(f"{API_URL}/chat/sessions/{session_id}/messages", headers=user_headers)
    if response.status_code != 200:
        logger.error(f"Failed to get chat messages: {response.text}")
        return False
    
    messages = response.json()
    
    # Check for automatic message
    expected_message = f"Olá {test_user['name']}, estou a verificar a mensagem e já darei apoio."
    auto_message_found = False
    
    for message in messages:
        if message["sender_type"] == "agent" and message["message"] == expected_message:
            auto_message_found = True
            break
    
    if auto_message_found:
        logger.info(f"✅ Found automatic message: '{expected_message}'")
    else:
        logger.error(f"❌ Automatic message not found. Messages: {json.dumps(messages, indent=2)}")
        return False
    
    # Check if session is assigned to admin
    response = requests.get(f"{API_URL}/admin/chat/sessions", headers=admin_headers)
    if response.status_code != 200:
        logger.error(f"Failed to get admin chat sessions: {response.text}")
        return False
    
    sessions = response.json()
    session_assigned = False
    
    for session in sessions:
        if session["id"] == session_id and session["agent_id"]:
            session_assigned = True
            break
    
    if session_assigned:
        logger.info("✅ Session correctly assigned to admin")
    else:
        logger.error("❌ Session not assigned to admin")
        return False
    
    logger.info("✅ All chat assignment tests passed")
    return True

def test_other_endpoints():
    """Test other endpoints to ensure they still work"""
    logger.info("Testing other endpoints")
    
    # Test GET /api/categories
    response = requests.get(f"{API_URL}/categories")
    if response.status_code == 200:
        categories = response.json()
        logger.info(f"✅ GET /api/categories working - found {len(categories)} categories")
    else:
        logger.error(f"❌ GET /api/categories failed: {response.status_code} - {response.text}")
        return False
    
    # Test POST /api/admin/categories (login as admin first)
    response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
    if response.status_code != 200:
        logger.error(f"Admin login failed: {response.text}")
        return False
    
    admin_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    category_data = {
        "name": f"Test Category {uuid.uuid4().hex[:6]}",
        "description": "Test category creation",
        "emoji": "🧪",
        "color": "#3366FF"
    }
    
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    if response.status_code == 200:
        logger.info(f"✅ POST /api/admin/categories working - created {response.json()['name']}")
    else:
        logger.error(f"❌ POST /api/admin/categories failed: {response.status_code} - {response.text}")
        return False
    
    # Test GET /api/admin/chat/sessions
    response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
    if response.status_code == 200:
        logger.info(f"✅ GET /api/admin/chat/sessions working - found {len(response.json())} sessions")
    else:
        logger.error(f"❌ GET /api/admin/chat/sessions failed: {response.status_code} - {response.text}")
        return False
    
    logger.info("✅ All other endpoints tests passed")
    return True

def run_tests():
    """Run all tests"""
    logger.info("=== STARTING TESTS FOR CORRECTED FUNCTIONALITY ===")
    
    category_result = test_category_deletion()
    chat_result = test_chat_assign()
    other_result = test_other_endpoints()
    
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"Category Deletion Tests: {'✅ PASSED' if category_result else '❌ FAILED'}")
    logger.info(f"Chat Assignment Tests: {'✅ PASSED' if chat_result else '❌ FAILED'}")
    logger.info(f"Other Endpoints Tests: {'✅ PASSED' if other_result else '❌ FAILED'}")
    
    if category_result and chat_result and other_result:
        logger.info("✅ ALL TESTS PASSED")
    else:
        logger.info("❌ SOME TESTS FAILED")

if __name__ == "__main__":
    run_tests()