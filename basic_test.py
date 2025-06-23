import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"

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

# Test GET /api/categories
def test_get_categories():
    print("\nTesting GET /api/categories")
    response = requests.get(f"{API_URL}/categories")
    if response.status_code == 200:
        categories = response.json()
        print(f"✅ Success - Found {len(categories)} categories")
        return True
    else:
        print(f"❌ Failed - Status: {response.status_code}, Response: {response.text}")
        return False

# Test POST /api/admin/categories
def test_create_category():
    print("\nTesting POST /api/admin/categories")
    admin_token = get_admin_token()
    if not admin_token:
        return False
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    category_data = {
        "name": "Test Category XYZ",
        "description": "Test category creation",
        "emoji": "🧪",
        "color": "#3366FF"
    }
    
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    if response.status_code == 200:
        print(f"✅ Success - Created category: {response.json()['name']}")
        return True
    else:
        print(f"❌ Failed - Status: {response.status_code}, Response: {response.text}")
        return False

# Test GET /api/admin/chat/sessions
def test_get_chat_sessions():
    print("\nTesting GET /api/admin/chat/sessions")
    admin_token = get_admin_token()
    if not admin_token:
        return False
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
    if response.status_code == 200:
        sessions = response.json()
        print(f"✅ Success - Found {len(sessions)} chat sessions")
        return True
    else:
        print(f"❌ Failed - Status: {response.status_code}, Response: {response.text}")
        return False

# Run the tests
if __name__ == "__main__":
    print("=== TESTING BASIC ENDPOINTS ===")
    
    test_get_categories()
    test_create_category()
    test_get_chat_sessions()
    
    print("\n=== TESTS COMPLETED ===")