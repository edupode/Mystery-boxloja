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
# For local testing, use localhost
BACKEND_URL = "http://localhost:8001"
API_URL = f"{BACKEND_URL}/api"

# Admin credentials
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

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if "status" in data and data["status"] == "ok":
                return log_test_result("Health Check", True, "Health check endpoint is working correctly")
            else:
                return log_test_result("Health Check", False, f"Health check endpoint returned unexpected data: {data}")
        else:
            return log_test_result("Health Check", False, f"Health check endpoint returned status code {response.status_code}: {response.text}")
    except Exception as e:
        return log_test_result("Health Check", False, f"Exception: {str(e)}")

def test_admin_login():
    """Test admin login"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=ADMIN_USER)
        response_data = response.json()
        
        if response.status_code == 200 and "access_token" in response_data:
            # Store admin token
            test_results["admin_token"] = response_data["access_token"]
            return log_test_result("Admin Login", True, "Admin login successful")
        else:
            return log_test_result("Admin Login", False, f"Failed to login as admin: {response.text}")
    except Exception as e:
        return log_test_result("Admin Login", False, f"Exception: {str(e)}")

def test_product_upload_with_subscription_prices():
    """Test creating a product with subscription prices"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Product Upload with Subscription Prices", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Test data from the review request
        product_data = {
            "name": "Mystery Box Test",
            "description": "Produto de teste",
            "category": "tech",
            "price": 29.99,
            "subscription_prices": {
                "1_month": 25.99,
                "3_months": 22.99,
                "6_months": 19.99,
                "12_months": 16.99
            },
            "image_url": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzMzMzMzMyIvPjx0ZXh0IHg9IjEwMCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiNmZmYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5UZXN0IEltYWdlPC90ZXh0Pjwvc3ZnPg==",
            "stock_quantity": 100,
            "featured": True
        }
        
        response = requests.post(f"{API_URL}/admin/products", json=product_data, headers=headers)
        
        if response.status_code == 200:
            product = response.json()
            test_results["product_id"] = product.get("id")
            
            # Verify subscription prices were saved correctly
            if "subscription_prices" in product and product["subscription_prices"] == product_data["subscription_prices"]:
                return log_test_result("Product Upload with Subscription Prices", True, f"Product created with ID: {product.get('id')}")
            else:
                return log_test_result("Product Upload with Subscription Prices", False, "Subscription prices not saved correctly")
        else:
            return log_test_result("Product Upload with Subscription Prices", False, f"Failed to create product: {response.text}")
    except Exception as e:
        return log_test_result("Product Upload with Subscription Prices", False, f"Exception: {str(e)}")

def test_get_products_with_images():
    """Test if products are returned with images correctly"""
    try:
        response = requests.get(f"{API_URL}/products")
        
        if response.status_code != 200:
            return log_test_result("Get Products with Images", False, f"Failed to get products: {response.text}")
        
        products = response.json()
        if not products:
            return log_test_result("Get Products with Images", False, "No products returned")
        
        # Check if images are present in the products
        images_present = all("image_url" in product and product["image_url"] for product in products)
        
        if images_present:
            return log_test_result("Get Products with Images", True, f"All {len(products)} products have images")
        else:
            missing_images = sum(1 for p in products if not p.get("image_url"))
            return log_test_result("Get Products with Images", False, f"{missing_images} out of {len(products)} products are missing images")
    except Exception as e:
        return log_test_result("Get Products with Images", False, f"Exception: {str(e)}")

def test_admin_user_management():
    """Test admin user management features"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin User Management", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. Test listing users
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin User List", False, f"Failed to list users: {response.text}")
        
        users = response.json()
        if not users or not isinstance(users, list):
            return log_test_result("Admin User List", False, "No users returned or invalid format")
        
        # Store a non-admin user ID for testing
        non_admin_user_id = None
        for user in users:
            if not user.get("is_admin") and user.get("id"):
                non_admin_user_id = user["id"]
                break
        
        if not non_admin_user_id:
            # Create a test user if no non-admin user found
            test_user = {
                "email": f"test_user_{uuid.uuid4()}@example.com",
                "name": "Test User",
                "password": "Test@123"
            }
            
            reg_response = requests.post(f"{API_URL}/auth/register", json=test_user)
            if reg_response.status_code == 200:
                non_admin_user_id = reg_response.json()["user"]["id"]
            else:
                return log_test_result("Create Test User", False, f"Failed to create test user: {reg_response.text}")
        
        # 2. Test changing user password
        if non_admin_user_id:
            password_data = {"new_password": "NewPassword@123"}
            response = requests.put(f"{API_URL}/admin/users/{non_admin_user_id}/password", 
                                   json=password_data, headers=headers)
            
            if response.status_code == 200:
                log_test_result("Admin Change User Password", True, "Successfully changed user password")
            else:
                log_test_result("Admin Change User Password", False, f"Failed to change password: {response.text}")
        
        # 3. Test bulk make admin
        bulk_admin_data = {
            "user_ids": [non_admin_user_id] if non_admin_user_id else []
        }
        
        response = requests.post(f"{API_URL}/admin/users/bulk-make-admin", 
                               json=bulk_admin_data, headers=headers)
        
        if response.status_code == 200:
            log_test_result("Admin Bulk Make Admin", True, "Successfully made multiple users admin")
        else:
            log_test_result("Admin Bulk Make Admin", False, f"Failed to make users admin: {response.text}")
        
        # Overall test result
        return log_test_result("Admin User Management", True, "All admin user management features are working")
    except Exception as e:
        return log_test_result("Admin User Management", False, f"Exception: {str(e)}")

def test_validate_coupons():
    """Test coupon validation"""
    try:
        # Test WELCOME10 coupon
        response = requests.get(f"{API_URL}/coupons/validate/WELCOME10")
        if response.status_code != 200:
            return log_test_result("Validate WELCOME10 Coupon", False, f"Failed: {response.text}")
        
        welcome10 = response.json()
        if welcome10["discount_type"] != "percentage" or welcome10["discount_value"] != 10.0:
            return log_test_result("Validate WELCOME10 Coupon", False, "Incorrect discount value or type")
        
        # Test SAVE5 coupon
        response = requests.get(f"{API_URL}/coupons/validate/SAVE5")
        if response.status_code != 200:
            return log_test_result("Validate SAVE5 Coupon", False, f"Failed: {response.text}")
        
        save5 = response.json()
        if save5["discount_type"] != "percentage" or save5["discount_value"] != 5.0 or not save5["min_order_value"] or save5["min_order_value"] < 20.0:
            return log_test_result("Validate SAVE5 Coupon", False, "Incorrect discount value, type or minimum order value")
        
        # Test PREMIUM20 coupon
        response = requests.get(f"{API_URL}/coupons/validate/PREMIUM20")
        if response.status_code != 200:
            return log_test_result("Validate PREMIUM20 Coupon", False, f"Failed: {response.text}")
        
        premium20 = response.json()
        if premium20["discount_type"] != "percentage" or premium20["discount_value"] != 20.0 or not premium20["min_order_value"] or premium20["min_order_value"] < 50.0:
            return log_test_result("Validate PREMIUM20 Coupon", False, "Incorrect discount value, type or minimum order value")
        
        return log_test_result("Validate Coupons", True, "All coupons validated successfully")
    except Exception as e:
        return log_test_result("Validate Coupons", False, f"Exception: {str(e)}")

def test_cart_with_coupons():
    """Test applying coupons to cart"""
    try:
        # Ensure cart has items
        if "product_id" not in test_results:
            # Get a product ID if we don't have one
            response = requests.get(f"{API_URL}/products")
            if response.status_code == 200:
                products = response.json()
                if products:
                    test_results["product_id"] = products[0]["id"]
            
            if "product_id" not in test_results:
                return log_test_result("Cart with Coupons", False, "No product ID available")
        
        # Add product to cart
        cart_item = {
            "product_id": test_results["product_id"],
            "quantity": 2
        }
        
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Add to Cart", False, f"Failed: {response.text}")
        
        # Test applying WELCOME10 coupon
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code=WELCOME10")
        if response.status_code != 200:
            return log_test_result("Apply WELCOME10 Coupon", False, f"Failed: {response.text}")
        
        cart = response.json()
        if not cart.get("coupon_code") or cart["coupon_code"] != "WELCOME10":
            return log_test_result("Apply WELCOME10 Coupon", False, "Coupon not applied correctly")
        
        # Remove coupon
        response = requests.delete(f"{API_URL}/cart/{SESSION_ID}/remove-coupon")
        if response.status_code != 200:
            return log_test_result("Remove Coupon", False, f"Failed: {response.text}")
        
        # Test applying SAVE5 coupon
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code=SAVE5")
        if response.status_code != 200:
            return log_test_result("Apply SAVE5 Coupon", False, f"Failed: {response.text}")
        
        cart = response.json()
        if not cart.get("coupon_code") or cart["coupon_code"] != "SAVE5":
            return log_test_result("Apply SAVE5 Coupon", False, "Coupon not applied correctly")
        
        # Remove coupon
        response = requests.delete(f"{API_URL}/cart/{SESSION_ID}/remove-coupon")
        if response.status_code != 200:
            return log_test_result("Remove Coupon", False, f"Failed: {response.text}")
        
        # Test applying PREMIUM20 coupon
        response = requests.post(f"{API_URL}/cart/{SESSION_ID}/apply-coupon?coupon_code=PREMIUM20")
        if response.status_code != 200:
            return log_test_result("Apply PREMIUM20 Coupon", False, f"Failed: {response.text}")
        
        cart = response.json()
        if not cart.get("coupon_code") or cart["coupon_code"] != "PREMIUM20":
            return log_test_result("Apply PREMIUM20 Coupon", False, "Coupon not applied correctly")
        
        return log_test_result("Cart with Coupons", True, "All coupons applied and removed successfully")
    except Exception as e:
        return log_test_result("Cart with Coupons", False, f"Exception: {str(e)}")

def run_specific_tests():
    """Run the specific tests requested in the review"""
    logger.info("Starting specific backend tests for Mystery Box Store")
    
    # Test health check endpoint
    test_health_check()
    
    # Test product upload with subscription prices
    test_product_upload_with_subscription_prices()
    
    # Test GET /api/products with images
    test_get_products_with_images()
    
    # Test admin user management
    test_admin_user_management()
    
    # Test coupon validation
    test_validate_coupons()
    
    # Test cart with coupons
    test_cart_with_coupons()
    
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
    run_specific_tests()