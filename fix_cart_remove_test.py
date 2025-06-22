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

# Test data
TEST_USER = {
    "email": f"test_user_{uuid.uuid4()}@example.com",
    "name": "Test User",
    "password": "Test@123"
}

# Test session ID
SESSION_ID = str(uuid.uuid4())

def test_cart_remove_issue():
    """Test the cart removal issue specifically"""
    logger.info("Testing cart removal issue...")
    
    # First, get a product
    response = requests.get(f"{API_URL}/products")
    if response.status_code != 200:
        logger.error(f"Failed to get products: {response.text}")
        return
    
    products = response.json()
    if not products:
        logger.error("No products found")
        return
    
    product_id = products[0]["id"]
    logger.info(f"Using product ID: {product_id}")
    
    # Add product to cart
    cart_item = {
        "product_id": product_id,
        "quantity": 1
    }
    
    response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
    if response.status_code != 200:
        logger.error(f"Failed to add product to cart: {response.text}")
        return
    
    logger.info("Product added to cart")
    
    # Get cart to verify
    response = requests.get(f"{API_URL}/cart/{SESSION_ID}")
    if response.status_code != 200:
        logger.error(f"Failed to get cart: {response.text}")
        return
    
    cart = response.json()
    logger.info(f"Cart before removal: {json.dumps(cart, indent=2)}")
    
    # Try to remove product with subscription_type=None
    response = requests.delete(f"{API_URL}/cart/{SESSION_ID}/remove/{product_id}")
    if response.status_code != 200:
        logger.error(f"Failed to remove product from cart: {response.text}")
        return
    
    # Get cart again to verify removal
    response = requests.get(f"{API_URL}/cart/{SESSION_ID}")
    if response.status_code != 200:
        logger.error(f"Failed to get cart after removal: {response.text}")
        return
    
    cart_after_remove = response.json()
    logger.info(f"Cart after removal: {json.dumps(cart_after_remove, indent=2)}")
    
    # Check if product was removed
    product_still_in_cart = False
    for item in cart_after_remove.get("items", []):
        if item["product_id"] == product_id:
            product_still_in_cart = True
            break
    
    if product_still_in_cart:
        logger.error("Product still in cart after removal")
    else:
        logger.info("Product successfully removed from cart")

if __name__ == "__main__":
    test_cart_remove_issue()