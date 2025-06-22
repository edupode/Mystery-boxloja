import requests
import json
import uuid
import base64
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

# Test session ID
SESSION_ID = str(uuid.uuid4())

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
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            logger.error(f"Admin login failed: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Admin login exception: {str(e)}")
        return None

def test_products_with_images():
    """Test if all 8 main products have valid base64 images"""
    try:
        # First, check the database directly to verify the images are stored correctly
        admin_token = admin_login()
        if not admin_token:
            return log_test_result("Products with Images", False, "Failed to login as admin")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{API_URL}/admin/products", headers=headers)
        
        if response.status_code != 200:
            # If admin endpoint fails, try the regular products endpoint
            response = requests.get(f"{API_URL}/products")
            if response.status_code != 200:
                return log_test_result("Products with Images", False, f"Failed to get products: {response.text}")
        
        products = response.json()
        
        # Check if we have exactly 8 products
        if len(products) != 8:
            return log_test_result("Products with Images", False, f"Expected 8 products, found {len(products)}")
        
        # Check if all expected products are present
        expected_products = [
            "Mystery Box Geek 🤓",
            "Mystery Box Terror 👻",
            "Mystery Box Pets 🐾",
            "Mystery Box Harry Potter ⚡",
            "Mystery Box Marvel 🦸‍♂️",
            "Mystery Box Livros 📚",
            "Mystery Box Auto-cuidado 🧘‍♀️",
            "Mystery Box Stitch 🌺"
        ]
        
        found_products = [p["name"] for p in products]
        missing_products = [p for p in expected_products if p not in found_products]
        
        if missing_products:
            return log_test_result("Products with Images", False, f"Missing expected products: {', '.join(missing_products)}")
        
        # Connect directly to the database to check for base64 images
        import os
        from pymongo import MongoClient
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv('/app/backend/.env')
        MONGO_URL = os.getenv('MONGO_URL')
        DB_NAME = os.getenv('DB_NAME')
        
        # Connect to MongoDB
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Check products in the database
        db_products = list(db.products.find())
        
        # Check if all products have base64 images in image_url field
        products_without_base64 = []
        for product in db_products:
            image_url = product.get('image_url', '')
            if not image_url or not image_url.startswith('data:image'):
                products_without_base64.append(product.get('name', 'Unknown'))
        
        if products_without_base64:
            return log_test_result("Products with Images", False, 
                                  f"Products without base64 images: {', '.join(products_without_base64)}")
        
        return log_test_result("Products with Images", True, 
                              f"All 8 products have valid base64 images in the database")
    except Exception as e:
        return log_test_result("Products with Images", False, f"Exception: {str(e)}")

def test_coupon_validation():
    """Test validation of the corrected coupons"""
    try:
        # Test WELCOME10 coupon
        response = requests.get(f"{API_URL}/coupons/validate/WELCOME10")
        if response.status_code != 200:
            return log_test_result("Coupon Validation - WELCOME10", False, f"Failed: {response.text}")
        
        welcome_coupon = response.json()
        if welcome_coupon["discount_type"] != "percentage" or welcome_coupon["discount_value"] != 10:
            return log_test_result("Coupon Validation - WELCOME10", False, 
                                  f"Incorrect discount: {welcome_coupon['discount_type']} {welcome_coupon['discount_value']}%")
        
        # Test SAVE5 coupon
        response = requests.get(f"{API_URL}/coupons/validate/SAVE5")
        if response.status_code != 200:
            return log_test_result("Coupon Validation - SAVE5", False, f"Failed: {response.text}")
        
        save5_coupon = response.json()
        if save5_coupon["discount_type"] != "percentage" or save5_coupon["discount_value"] != 5:
            return log_test_result("Coupon Validation - SAVE5", False, 
                                  f"Incorrect discount: {save5_coupon['discount_type']} {save5_coupon['discount_value']}%")
        
        if not save5_coupon.get("min_order_value") or save5_coupon["min_order_value"] < 20:
            return log_test_result("Coupon Validation - SAVE5", False, 
                                  f"Incorrect minimum order value: {save5_coupon.get('min_order_value')}")
        
        # Test PREMIUM20 coupon
        response = requests.get(f"{API_URL}/coupons/validate/PREMIUM20")
        if response.status_code != 200:
            return log_test_result("Coupon Validation - PREMIUM20", False, f"Failed: {response.text}")
        
        premium_coupon = response.json()
        if premium_coupon["discount_type"] != "percentage" or premium_coupon["discount_value"] != 20:
            return log_test_result("Coupon Validation - PREMIUM20", False, 
                                  f"Incorrect discount: {premium_coupon['discount_type']} {premium_coupon['discount_value']}%")
        
        if not premium_coupon.get("min_order_value") or premium_coupon["min_order_value"] < 50:
            return log_test_result("Coupon Validation - PREMIUM20", False, 
                                  f"Incorrect minimum order value: {premium_coupon.get('min_order_value')}")
        
        return log_test_result("Coupon Validation", True, "All coupons validated successfully")
    except Exception as e:
        return log_test_result("Coupon Validation", False, f"Exception: {str(e)}")

def test_cart_with_coupons():
    """Test applying coupons to cart"""
    try:
        # Get a product to add to cart
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200 or not response.json():
            return log_test_result("Cart with Coupons", False, "Failed to get products")
        
        product = response.json()[0]
        product_id = product["id"]
        
        # Add product to cart
        cart_item = {
            "product_id": product_id,
            "quantity": 3  # Ensure cart value is high enough for all coupons
        }
        
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Cart with Coupons", False, f"Failed to add product to cart: {response.text}")
        
        # Test WELCOME10 coupon
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code=WELCOME10")
        if response.status_code != 200:
            return log_test_result("Cart with Coupons - WELCOME10", False, f"Failed to apply WELCOME10: {response.text}")
        
        cart = response.json()
        if cart.get("coupon_code") != "WELCOME10":
            return log_test_result("Cart with Coupons - WELCOME10", False, "WELCOME10 not applied to cart")
        
        # Remove coupon
        response = requests.delete(f"{API_URL}/cart/{SESSION_ID}/remove-coupon")
        if response.status_code != 200:
            return log_test_result("Cart with Coupons", False, f"Failed to remove coupon: {response.text}")
        
        # Test SAVE5 coupon
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code=SAVE5")
        if response.status_code != 200:
            return log_test_result("Cart with Coupons - SAVE5", False, f"Failed to apply SAVE5: {response.text}")
        
        cart = response.json()
        if cart.get("coupon_code") != "SAVE5":
            return log_test_result("Cart with Coupons - SAVE5", False, "SAVE5 not applied to cart")
        
        # Remove coupon
        response = requests.delete(f"{API_URL}/cart/{SESSION_ID}/remove-coupon")
        if response.status_code != 200:
            return log_test_result("Cart with Coupons", False, f"Failed to remove coupon: {response.text}")
        
        # Test PREMIUM20 coupon
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code=PREMIUM20")
        if response.status_code != 200:
            return log_test_result("Cart with Coupons - PREMIUM20", False, f"Failed to apply PREMIUM20: {response.text}")
        
        cart = response.json()
        if cart.get("coupon_code") != "PREMIUM20":
            return log_test_result("Cart with Coupons - PREMIUM20", False, "PREMIUM20 not applied to cart")
        
        return log_test_result("Cart with Coupons", True, "All coupons applied successfully to cart")
    except Exception as e:
        return log_test_result("Cart with Coupons", False, f"Exception: {str(e)}")

def run_tests():
    """Run all tests and return results"""
    logger.info("Starting tests for Mystery Box Store bug fixes")
    
    # Test products with images
    test_products_with_images()
    
    # Test coupon validation
    test_coupon_validation()
    
    # Test cart with coupons
    test_cart_with_coupons()
    
    # Print summary
    logger.info("\n=== TEST SUMMARY ===")
    passed = sum(1 for result in test_results.values() if result.get("success"))
    failed = sum(1 for result in test_results.values() if not result.get("success"))
    logger.info(f"PASSED: {passed}, FAILED: {failed}")
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        logger.info(f"{status}: {test_name}")
        if result.get("message"):
            logger.info(f"  - {result['message']}")
    
    return test_results

if __name__ == "__main__":
    run_tests()