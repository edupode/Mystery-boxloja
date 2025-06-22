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

# Test session ID
SESSION_ID = str(uuid.uuid4())

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

# Authentication Tests
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

# User Profile Tests
def test_get_user_profile():
    """Test getting user profile information"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("Get User Profile", False, "User registration required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        
        if response.status_code != 200:
            return log_test_result("Get User Profile", False, f"Failed: {response.text}")
        
        profile = response.json()
        if not profile or "id" not in profile or "email" not in profile:
            return log_test_result("Get User Profile", False, "Invalid profile data")
        
        # Store user ID for later tests
        test_results["user_id"] = profile["id"]
        
        return log_test_result("Get User Profile", True, f"Retrieved profile for {profile['email']}")
    except Exception as e:
        return log_test_result("Get User Profile", False, f"Exception: {str(e)}")

def test_update_user_profile():
    """Test updating user profile"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("Update User Profile", False, "User registration required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Update profile data
        profile_data = {
            "name": f"Updated {TEST_USER['name']}",
            "phone": "+351912345678",
            "address": "Rua de Teste, 123",
            "city": "Lisboa",
            "postal_code": "1000-100",
            "nif": "501964843"  # Valid Portuguese NIF
        }
        
        response = requests.put(f"{API_URL}/auth/profile", json=profile_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Update User Profile", False, f"Failed: {response.text}")
        
        # Verify profile was updated
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        if response.status_code != 200:
            return log_test_result("Update User Profile Verification", False, f"Failed: {response.text}")
        
        updated_profile = response.json()
        
        # Check if profile was updated correctly
        for key, value in profile_data.items():
            if key in updated_profile and updated_profile[key] != value:
                return log_test_result("Update User Profile", False, f"Profile field {key} not updated correctly")
        
        return log_test_result("Update User Profile", True, "Profile updated successfully")
    except Exception as e:
        return log_test_result("Update User Profile", False, f"Exception: {str(e)}")

def test_get_user_orders():
    """Test getting user order history"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("Get User Orders", False, "User registration required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(f"{API_URL}/auth/orders", headers=headers)
        
        if response.status_code != 200:
            return log_test_result("Get User Orders", False, f"Failed: {response.text}")
        
        orders = response.json()
        if not isinstance(orders, list):
            return log_test_result("Get User Orders", False, "Invalid orders data format")
        
        # New user likely won't have orders, but endpoint should return an empty list
        return log_test_result("Get User Orders", True, f"Retrieved {len(orders)} orders")
    except Exception as e:
        return log_test_result("Get User Orders", False, f"Exception: {str(e)}")

# Chat Tests
def test_create_chat_session():
    """Test creating a new chat session"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("Create Chat Session", False, "User registration required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Create chat session
        session_data = {
            "subject": "Test Support Request"
        }
        
        response = requests.post(f"{API_URL}/chat/sessions", json=session_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Chat Session", False, f"Failed: {response.text}")
        
        session = response.json()
        if not session or "id" not in session:
            return log_test_result("Create Chat Session", False, "Invalid session data")
        
        # Store session ID for later tests
        test_results["chat_session_id"] = session["id"]
        
        return log_test_result("Create Chat Session", True, f"Created chat session with ID: {session['id']}")
    except Exception as e:
        return log_test_result("Create Chat Session", False, f"Exception: {str(e)}")

def test_list_chat_sessions():
    """Test listing user's chat sessions"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("List Chat Sessions", False, "User registration required")
    
    if "chat_session_id" not in test_results:
        test_create_chat_session()
        if "chat_session_id" not in test_results:
            return log_test_result("List Chat Sessions", False, "Chat session creation required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(f"{API_URL}/chat/sessions", headers=headers)
        
        if response.status_code != 200:
            return log_test_result("List Chat Sessions", False, f"Failed: {response.text}")
        
        sessions = response.json()
        if not isinstance(sessions, list):
            return log_test_result("List Chat Sessions", False, "Invalid sessions data format")
        
        # Check if our created session is in the list
        session_found = False
        for session in sessions:
            if session["id"] == test_results["chat_session_id"]:
                session_found = True
                break
        
        if not session_found:
            return log_test_result("List Chat Sessions", False, "Created session not found in list")
        
        return log_test_result("List Chat Sessions", True, f"Retrieved {len(sessions)} chat sessions")
    except Exception as e:
        return log_test_result("List Chat Sessions", False, f"Exception: {str(e)}")

def test_send_chat_message():
    """Test sending a chat message"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("Send Chat Message", False, "User registration required")
    
    if "chat_session_id" not in test_results:
        test_create_chat_session()
        if "chat_session_id" not in test_results:
            return log_test_result("Send Chat Message", False, "Chat session creation required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        
        # Send message
        message_data = {
            "message": "This is a test message from the user"
        }
        
        response = requests.post(
            f"{API_URL}/chat/sessions/{test_results['chat_session_id']}/messages", 
            json=message_data, 
            headers=headers
        )
        
        if response.status_code != 200:
            return log_test_result("Send Chat Message", False, f"Failed: {response.text}")
        
        message = response.json()
        if not message or "id" not in message:
            return log_test_result("Send Chat Message", False, "Invalid message data")
        
        # Store message ID
        test_results["chat_message_id"] = message["id"]
        
        return log_test_result("Send Chat Message", True, "Message sent successfully")
    except Exception as e:
        return log_test_result("Send Chat Message", False, f"Exception: {str(e)}")

def test_list_chat_messages():
    """Test listing chat messages"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("List Chat Messages", False, "User registration required")
    
    if "chat_session_id" not in test_results:
        test_create_chat_session()
        if "chat_session_id" not in test_results:
            return log_test_result("List Chat Messages", False, "Chat session creation required")
    
    if "chat_message_id" not in test_results:
        test_send_chat_message()
        if "chat_message_id" not in test_results:
            return log_test_result("List Chat Messages", False, "Chat message creation required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.get(
            f"{API_URL}/chat/sessions/{test_results['chat_session_id']}/messages", 
            headers=headers
        )
        
        if response.status_code != 200:
            return log_test_result("List Chat Messages", False, f"Failed: {response.text}")
        
        messages = response.json()
        if not isinstance(messages, list):
            return log_test_result("List Chat Messages", False, "Invalid messages data format")
        
        # Check if our sent message is in the list
        message_found = False
        for message in messages:
            if message["id"] == test_results["chat_message_id"]:
                message_found = True
                break
        
        if not message_found:
            return log_test_result("List Chat Messages", False, "Sent message not found in list")
        
        return log_test_result("List Chat Messages", True, f"Retrieved {len(messages)} chat messages")
    except Exception as e:
        return log_test_result("List Chat Messages", False, f"Exception: {str(e)}")

def test_close_chat_session():
    """Test closing a chat session"""
    if "auth_token" not in test_results:
        test_register()
        if "auth_token" not in test_results:
            return log_test_result("Close Chat Session", False, "User registration required")
    
    if "chat_session_id" not in test_results:
        test_create_chat_session()
        if "chat_session_id" not in test_results:
            return log_test_result("Close Chat Session", False, "Chat session creation required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['auth_token']}"}
        response = requests.put(
            f"{API_URL}/chat/sessions/{test_results['chat_session_id']}/close", 
            headers=headers
        )
        
        if response.status_code != 200:
            return log_test_result("Close Chat Session", False, f"Failed: {response.text}")
        
        # Verify session was closed
        response = requests.get(f"{API_URL}/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Close Chat Session Verification", False, f"Failed: {response.text}")
        
        sessions = response.json()
        for session in sessions:
            if session["id"] == test_results["chat_session_id"]:
                if session["status"] != "closed":
                    return log_test_result("Close Chat Session", False, "Session not marked as closed")
                break
        
        return log_test_result("Close Chat Session", True, "Chat session closed successfully")
    except Exception as e:
        return log_test_result("Close Chat Session", False, f"Exception: {str(e)}")

# Admin Chat Tests
def test_admin_list_chat_sessions():
    """Test admin listing all chat sessions"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin List Chat Sessions", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        
        if response.status_code != 200:
            return log_test_result("Admin List Chat Sessions", False, f"Failed: {response.text}")
        
        sessions = response.json()
        if not isinstance(sessions, list):
            return log_test_result("Admin List Chat Sessions", False, "Invalid sessions data format")
        
        return log_test_result("Admin List Chat Sessions", True, f"Retrieved {len(sessions)} chat sessions as admin")
    except Exception as e:
        return log_test_result("Admin List Chat Sessions", False, f"Exception: {str(e)}")

def test_admin_assign_chat_session():
    """Test admin assigning a chat session"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Assign Chat Session", False, "Admin login required")
    
    if "chat_session_id" not in test_results:
        # Create a new session if we don't have one
        if "auth_token" not in test_results:
            test_register()
        test_create_chat_session()
        if "chat_session_id" not in test_results:
            return log_test_result("Admin Assign Chat Session", False, "Chat session creation required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        response = requests.put(
            f"{API_URL}/admin/chat/sessions/{test_results['chat_session_id']}/assign", 
            headers=headers
        )
        
        if response.status_code != 200:
            return log_test_result("Admin Assign Chat Session", False, f"Failed: {response.text}")
        
        # Verify session was assigned
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Assign Chat Session Verification", False, f"Failed: {response.text}")
        
        sessions = response.json()
        session_assigned = False
        for session in sessions:
            if session["id"] == test_results["chat_session_id"]:
                if session.get("agent_id") and session["status"] == "active":
                    session_assigned = True
                break
        
        if not session_assigned:
            return log_test_result("Admin Assign Chat Session", False, "Session not assigned to admin")
        
        return log_test_result("Admin Assign Chat Session", True, "Chat session assigned to admin successfully")
    except Exception as e:
        return log_test_result("Admin Assign Chat Session", False, f"Exception: {str(e)}")

def run_profile_chat_tests():
    """Run all profile and chat tests and return results"""
    logger.info("Starting profile and chat backend tests for Mystery Box Store")
    
    # Authentication tests
    test_register()
    test_admin_login()
    
    # User profile tests
    test_get_user_profile()
    test_update_user_profile()
    test_get_user_orders()
    
    # Chat tests
    test_create_chat_session()
    test_list_chat_sessions()
    test_send_chat_message()
    test_list_chat_messages()
    test_close_chat_session()
    
    # Admin chat tests
    test_admin_list_chat_sessions()
    test_admin_assign_chat_session()
    
    # Print summary
    logger.info("\n=== PROFILE & CHAT TEST SUMMARY ===")
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
    run_profile_chat_tests()