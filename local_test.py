import requests
import json
import uuid
import os

# Use local backend URL
API_URL = "http://localhost:8001/api"

# Admin credentials
ADMIN_USER = {
    "email": "eduardocorreia3344@gmail.com",
    "password": "admin123"
}

# Get admin token
def get_admin_token():
    response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Admin login failed: {response.text}")
        return None

# Test DELETE /api/admin/categories/{category_id}
def test_delete_category():
    print("\n=== Testing DELETE /api/admin/categories/{category_id} ===")
    admin_token = get_admin_token()
    if not admin_token:
        return False
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a test category
    category_name = f"Test Category {uuid.uuid4().hex[:6]}"
    category_data = {
        "name": category_name,
        "description": "Test category for deletion",
        "emoji": "🧪",
        "color": "#FF5733"
    }
    
    print(f"Creating test category: {category_name}")
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to create test category: {response.text}")
        return False
    
    category_id = response.json()["id"]
    print(f"✅ Created test category with ID: {category_id}")
    
    # Test 1: Try to delete non-existent category
    print("Testing deletion of non-existent category")
    response = requests.delete(f"{API_URL}/admin/categories/non_existent_id", headers=headers)
    if response.status_code == 404:
        print("✅ Successfully verified 404 for non-existent category")
    else:
        print(f"❌ Expected 404, got {response.status_code}: {response.text}")
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
    
    print(f"Creating test product: {product_name}")
    response = requests.post(f"{API_URL}/admin/products", json=product_data, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to create test product: {response.text}")
        return False
    
    product_id = response.json()["id"]
    print(f"✅ Created test product with ID: {product_id}")
    
    # Try to delete category with associated product
    print("Testing deletion of category with associated products")
    response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
    if response.status_code == 400:
        print("✅ Successfully verified prevention of deleting category with products")
    else:
        print(f"❌ Expected 400, got {response.status_code}: {response.text}")
        return False
    
    # Delete the product
    print(f"Deleting test product: {product_id}")
    response = requests.delete(f"{API_URL}/admin/products/{product_id}", headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to delete test product: {response.text}")
        return False
    
    # Now try to delete the category (should succeed)
    print(f"Testing deletion of category without products: {category_id}")
    response = requests.delete(f"{API_URL}/admin/categories/{category_id}", headers=headers)
    if response.status_code == 200:
        print("✅ Successfully deleted category after removing associated products")
    else:
        print(f"❌ Failed to delete category: {response.status_code} - {response.text}")
        return False
    
    print("✅ All category deletion tests passed")
    return True

# Test PUT /api/admin/chat/sessions/{session_id}/assign
def test_chat_assign():
    print("\n=== Testing PUT /api/admin/chat/sessions/{session_id}/assign ===")
    admin_token = get_admin_token()
    if not admin_token:
        return False
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create a test user
    test_user = {
        "email": f"test_user_{uuid.uuid4().hex[:8]}@example.com",
        "name": "Test User",
        "password": "Test@123"
    }
    
    print(f"Creating test user: {test_user['email']}")
    response = requests.post(f"{API_URL}/auth/register", json=test_user)
    if response.status_code != 200:
        print(f"❌ Failed to create test user: {response.text}")
        return False
    
    user_token = response.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    
    # Create a chat session
    session_data = {"subject": "Test Chat Session"}
    print("Creating test chat session")
    response = requests.post(f"{API_URL}/chat/sessions", json=session_data, headers=user_headers)
    if response.status_code != 200:
        print(f"❌ Failed to create chat session: {response.text}")
        return False
    
    session_id = response.json()["id"]
    print(f"✅ Created test chat session with ID: {session_id}")
    
    # Send a test message
    message_data = {"message": "This is a test message"}
    print("Sending test message to chat session")
    response = requests.post(f"{API_URL}/chat/sessions/{session_id}/messages", json=message_data, headers=user_headers)
    if response.status_code != 200:
        print(f"❌ Failed to send test message: {response.text}")
        return False
    
    # Assign the session to admin
    print(f"Assigning chat session to admin: {session_id}")
    response = requests.put(f"{API_URL}/admin/chat/sessions/{session_id}/assign", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Failed to assign chat session: {response.status_code} - {response.text}")
        return False
    
    print("✅ Chat session assigned to admin")
    
    # Get messages to check for automatic message
    print("Checking for automatic message")
    response = requests.get(f"{API_URL}/chat/sessions/{session_id}/messages", headers=user_headers)
    if response.status_code != 200:
        print(f"❌ Failed to get chat messages: {response.text}")
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
        print(f"✅ Found automatic message: '{expected_message}'")
    else:
        print(f"❌ Automatic message not found. Messages: {json.dumps(messages, indent=2)}")
        return False
    
    # Check if session is assigned to admin
    print("Checking if session is assigned to admin")
    response = requests.get(f"{API_URL}/admin/chat/sessions", headers=admin_headers)
    if response.status_code != 200:
        print(f"❌ Failed to get admin chat sessions: {response.text}")
        return False
    
    sessions = response.json()
    session_assigned = False
    
    for session in sessions:
        if session["id"] == session_id and session["agent_id"]:
            session_assigned = True
            break
    
    if session_assigned:
        print("✅ Session correctly assigned to admin")
    else:
        print("❌ Session not assigned to admin")
        return False
    
    print("✅ All chat assignment tests passed")
    return True

# Test other endpoints
def test_other_endpoints():
    print("\n=== Testing other endpoints ===")
    
    # Test GET /api/categories
    print("Testing GET /api/categories")
    response = requests.get(f"{API_URL}/categories")
    if response.status_code == 200:
        categories = response.json()
        print(f"✅ GET /api/categories working - found {len(categories)} categories")
    else:
        print(f"❌ GET /api/categories failed: {response.status_code} - {response.text}")
        return False
    
    # Test POST /api/admin/categories
    admin_token = get_admin_token()
    if not admin_token:
        return False
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    category_data = {
        "name": f"Test Category {uuid.uuid4().hex[:6]}",
        "description": "Test category creation",
        "emoji": "🧪",
        "color": "#3366FF"
    }
    
    print(f"Testing POST /api/admin/categories with {category_data['name']}")
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    if response.status_code == 200:
        print(f"✅ POST /api/admin/categories working - created {response.json()['name']}")
    else:
        print(f"❌ POST /api/admin/categories failed: {response.status_code} - {response.text}")
        return False
    
    # Test GET /api/admin/chat/sessions
    print("Testing GET /api/admin/chat/sessions")
    response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
    if response.status_code == 200:
        print(f"✅ GET /api/admin/chat/sessions working - found {len(response.json())} sessions")
    else:
        print(f"❌ GET /api/admin/chat/sessions failed: {response.status_code} - {response.text}")
        return False
    
    print("✅ All other endpoints tests passed")
    return True

# Run the tests
if __name__ == "__main__":
    print("=== STARTING TESTS FOR CORRECTED FUNCTIONALITY ===")
    
    category_result = test_delete_category()
    chat_result = test_chat_assign()
    other_result = test_other_endpoints()
    
    print("\n=== TEST SUMMARY ===")
    print(f"Category Deletion Tests: {'✅ PASSED' if category_result else '❌ FAILED'}")
    print(f"Chat Assignment Tests: {'✅ PASSED' if chat_result else '❌ FAILED'}")
    print(f"Other Endpoints Tests: {'✅ PASSED' if other_result else '❌ FAILED'}")
    
    if category_result and chat_result and other_result:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")