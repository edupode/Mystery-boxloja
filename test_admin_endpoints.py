import requests
import json
import uuid
import time
import base64
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

def test_admin_endpoints():
    """Test the admin endpoints that returned Method Not Allowed"""
    logger.info("Testing admin endpoints...")
    
    # Login as admin
    response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
    if response.status_code != 200:
        logger.error(f"Failed to login as admin: {response.text}")
        return
    
    admin_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test GET /api/admin/products
    logger.info("Testing GET /api/admin/products...")
    response = requests.get(f"{API_URL}/admin/products", headers=headers)
    logger.info(f"Status code: {response.status_code}")
    logger.info(f"Response: {response.text}")
    
    # Test GET /api/admin/categories
    logger.info("Testing GET /api/admin/categories...")
    response = requests.get(f"{API_URL}/admin/categories", headers=headers)
    logger.info(f"Status code: {response.status_code}")
    logger.info(f"Response: {response.text}")
    
    # Test GET /api/products
    logger.info("Testing GET /api/products (for comparison)...")
    response = requests.get(f"{API_URL}/products")
    logger.info(f"Status code: {response.status_code}")
    
    # Test POST /api/admin/products
    logger.info("Testing POST /api/admin/products...")
    
    # Create a sample base64 image (very small transparent pixel)
    sample_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    
    new_product = {
        "name": f"Test Product {uuid.uuid4().hex[:8]}",
        "description": "This is a test product",
        "category": "geek",
        "price": 29.99,
        "subscription_prices": {
            "1_month": 29.99,
            "3_months": 26.99,
            "6_months": 24.99,
            "12_months": 22.99
        },
        "image_url": "https://example.com/fallback-image.jpg",
        "image_base64": sample_base64,
        "stock_quantity": 50,
        "featured": True
    }
    
    response = requests.post(f"{API_URL}/admin/products", json=new_product, headers=headers)
    logger.info(f"Status code: {response.status_code}")
    logger.info(f"Response: {response.text}")
    
    # Test POST /api/admin/categories
    logger.info("Testing POST /api/admin/categories...")
    
    category_data = {
        "name": f"Test Category {uuid.uuid4().hex[:8]}",
        "description": "Test Category",
        "emoji": "🧪",
        "color": "#FF5733"
    }
    
    response = requests.post(f"{API_URL}/admin/categories", json=category_data, headers=headers)
    logger.info(f"Status code: {response.status_code}")
    logger.info(f"Response: {response.text}")

if __name__ == "__main__":
    test_admin_endpoints()