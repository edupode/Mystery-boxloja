import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL')
API_URL = f"{BACKEND_URL}/api"
LOCAL_API_URL = "http://localhost:8001/api"

# Test admin login
def test_admin_login():
    admin_user = {
        "email": "eduardocorreia3344@gmail.com",
        "password": "admin123"
    }
    
    # Try local API first
    response = requests.post(f"{LOCAL_API_URL}/auth/login", json=admin_user)
    
    # If local API fails, try remote API
    if response.status_code == 404:
        response = requests.post(f"{API_URL}/auth/login", json=admin_user)
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"Admin login failed: {response.text}")
        return None

# Test email sending
def test_email_sending():
    admin_token = test_admin_login()
    if not admin_token:
        print("Cannot test email sending without admin token")
        return False
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test discount email
    params = {
        "user_email": "test@example.com",
        "user_name": "Test User",
        "coupon_code": "TESTDISCOUNT",
        "discount_value": 15.0,
        "discount_type": "percentage",
        "expiry_date": "31/12/2024"
    }
    
    # Try local API first
    response = requests.post(f"{LOCAL_API_URL}/admin/emails/send-discount", params=params, headers=headers)
    
    # If local API fails, try remote API
    if response.status_code == 404:
        response = requests.post(f"{API_URL}/admin/emails/send-discount", params=params, headers=headers)
    
    if response.status_code == 200:
        print("Email system is operational")
        print(response.json())
        return True
    else:
        print(f"Email sending failed: {response.text}")
        return False

if __name__ == "__main__":
    test_email_sending()