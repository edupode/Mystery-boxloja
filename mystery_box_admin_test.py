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

def test_admin_login():
    """Test admin login"""
    try:
        logger.info("Testing admin login with credentials: %s", ADMIN_USER["email"])
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

def test_admin_orders():
    """Test admin orders management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Orders", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. Get all orders
        logger.info("Testing GET /api/admin/orders endpoint")
        response = requests.get(f"{API_URL}/admin/orders", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Get Orders", False, f"Failed: {response.text}")
        
        orders = response.json()
        if not isinstance(orders, list):
            return log_test_result("Admin Get Orders", False, "Invalid orders data")
        
        logger.info(f"Found {len(orders)} orders")
        
        # 2. If there are orders, test updating order status
        if orders:
            order_id = orders[0]["id"]
            test_results["order_id"] = order_id
            
            # Update order status
            logger.info(f"Testing PUT /api/admin/orders/{order_id}/status endpoint")
            new_status = "shipped"
            response = requests.put(
                f"{API_URL}/admin/orders/{order_id}/status?status={new_status}", 
                headers=headers
            )
            
            if response.status_code != 200:
                return log_test_result("Admin Update Order Status", False, f"Failed: {response.text}")
            
            # Verify status was updated
            response = requests.get(f"{API_URL}/admin/orders", headers=headers)
            updated_orders = response.json()
            updated_order = next((o for o in updated_orders if o["id"] == order_id), None)
            
            if not updated_order or updated_order.get("order_status") != new_status:
                return log_test_result("Admin Update Order Status", False, "Order status not updated")
            
            return log_test_result("Admin Orders", True, f"Successfully managed {len(orders)} orders and updated status to '{new_status}'")
        else:
            return log_test_result("Admin Orders", True, "No orders to test with, but endpoints work correctly")
    except Exception as e:
        return log_test_result("Admin Orders", False, f"Exception: {str(e)}")

def test_admin_products():
    """Test admin product management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Products", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. List products
        logger.info("Testing GET /api/products endpoint")
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("List Products", False, f"Failed: {response.text}")
        
        products = response.json()
        if not isinstance(products, list):
            return log_test_result("List Products", False, "Invalid products data")
        
        logger.info(f"Found {len(products)} products")
        
        # 2. Create a new product
        logger.info("Testing POST /api/admin/products endpoint")
        new_product = {
            "name": f"Test Product {uuid.uuid4().hex[:8]}",
            "description": "This is a test product created by automated testing",
            "category": "geek",
            "price": 19.99,
            "subscription_prices": {
                "1_month": 19.99,
                "3_months": 17.99,
                "6_months": 15.99,
                "12_months": 13.99
            },
            "image_url": "https://example.com/test-product.jpg",
            "stock_quantity": 50,
            "featured": True
        }
        
        response = requests.post(f"{API_URL}/admin/products", json=new_product, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Product", False, f"Failed: {response.text}")
        
        created_product = response.json()
        if "id" not in created_product:
            return log_test_result("Admin Create Product", False, "No product ID in response")
        
        product_id = created_product["id"]
        test_results["created_product_id"] = product_id
        logger.info(f"Created product with ID: {product_id}")
        
        # 3. Update the product
        logger.info(f"Testing PUT /api/admin/products/{product_id} endpoint")
        updated_product = new_product.copy()
        updated_product["name"] = f"Updated {new_product['name']}"
        updated_product["price"] = 24.99
        
        response = requests.put(f"{API_URL}/admin/products/{product_id}", json=updated_product, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Update Product", False, f"Failed: {response.text}")
        
        # Verify the update
        response = requests.get(f"{API_URL}/products/{product_id}")
        if response.status_code != 200:
            return log_test_result("Admin Update Product Verification", False, f"Failed: {response.text}")
        
        updated_product_data = response.json()
        if updated_product_data["name"] != updated_product["name"] or updated_product_data["price"] != updated_product["price"]:
            return log_test_result("Admin Update Product", False, "Product not updated correctly")
        
        logger.info(f"Successfully updated product: {updated_product_data['name']}")
        
        # 4. Delete the product
        logger.info(f"Testing DELETE /api/admin/products/{product_id} endpoint")
        response = requests.delete(f"{API_URL}/admin/products/{product_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Delete Product", False, f"Failed: {response.text}")
        
        # Verify deletion (product should be marked as inactive)
        response = requests.get(f"{API_URL}/products/{product_id}")
        if response.status_code == 200:
            product_after_delete = response.json()
            if product_after_delete.get("is_active", True):
                return log_test_result("Admin Delete Product", False, "Product not marked as inactive")
        
        logger.info("Product successfully deleted (marked as inactive)")
        return log_test_result("Admin Products", True, "Successfully managed products (create, update, delete)")
    except Exception as e:
        return log_test_result("Admin Products", False, f"Exception: {str(e)}")

def test_admin_coupons():
    """Test admin coupon management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Coupons", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. List coupons
        logger.info("Testing GET /api/admin/coupons endpoint")
        response = requests.get(f"{API_URL}/admin/coupons", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin List Coupons", False, f"Failed: {response.text}")
        
        coupons = response.json()
        if not isinstance(coupons, list):
            return log_test_result("Admin List Coupons", False, "Invalid coupons data")
        
        logger.info(f"Found {len(coupons)} coupons")
        
        # 2. Create a new coupon
        logger.info("Testing POST /api/admin/coupons endpoint")
        coupon_code = f"TEST{uuid.uuid4().hex[:8].upper()}"
        new_coupon = {
            "code": coupon_code,
            "description": "Test Coupon",
            "discount_type": "percentage",
            "discount_value": 15.0,
            "min_order_value": 20.0,
            "max_uses": 50,
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "applicable_categories": [],
            "applicable_products": []
        }
        
        response = requests.post(f"{API_URL}/admin/coupons", json=new_coupon, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Coupon", False, f"Failed: {response.text}")
        
        created_coupon = response.json()
        if "id" not in created_coupon:
            return log_test_result("Admin Create Coupon", False, "No coupon ID in response")
        
        coupon_id = created_coupon["id"]
        test_results["created_coupon_id"] = coupon_id
        logger.info(f"Created coupon with code: {coupon_code} and ID: {coupon_id}")
        
        # 3. Update the coupon
        logger.info(f"Testing PUT /api/admin/coupons/{coupon_id} endpoint")
        updated_coupon = new_coupon.copy()
        updated_coupon["description"] = "Updated Test Coupon"
        updated_coupon["discount_value"] = 20.0
        
        response = requests.put(f"{API_URL}/admin/coupons/{coupon_id}", json=updated_coupon, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Update Coupon", False, f"Failed: {response.text}")
        
        logger.info(f"Successfully updated coupon: {coupon_id}")
        
        # 4. Delete (deactivate) the coupon
        logger.info(f"Testing DELETE /api/admin/coupons/{coupon_id} endpoint")
        response = requests.delete(f"{API_URL}/admin/coupons/{coupon_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Delete Coupon", False, f"Failed: {response.text}")
        
        # Verify coupon is deactivated by trying to validate it
        response = requests.get(f"{API_URL}/coupons/validate/{coupon_code}")
        if response.status_code != 404:
            return log_test_result("Admin Delete Coupon Verification", False, "Coupon still active after deletion")
        
        logger.info("Coupon successfully deactivated")
        return log_test_result("Admin Coupons", True, "Successfully managed coupons (list, create, update, delete)")
    except Exception as e:
        return log_test_result("Admin Coupons", False, f"Exception: {str(e)}")

def test_admin_promotions():
    """Test admin promotion management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Promotions", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. List promotions
        logger.info("Testing GET /api/admin/promotions endpoint")
        response = requests.get(f"{API_URL}/admin/promotions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin List Promotions", False, f"Failed: {response.text}")
        
        promotions = response.json()
        if not isinstance(promotions, list):
            return log_test_result("Admin List Promotions", False, "Invalid promotions data")
        
        logger.info(f"Found {len(promotions)} promotions")
        
        # 2. Create a new promotion
        logger.info("Testing POST /api/admin/promotions endpoint")
        new_promotion = {
            "name": f"Test Promotion {uuid.uuid4().hex[:8]}",
            "description": "Test Promotion Description",
            "discount_type": "percentage",
            "discount_value": 25.0,
            "applicable_categories": ["geek"],
            "applicable_products": [],
            "valid_from": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "valid_until": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        response = requests.post(f"{API_URL}/admin/promotions", json=new_promotion, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Promotion", False, f"Failed: {response.text}")
        
        created_promotion = response.json()
        if "id" not in created_promotion:
            return log_test_result("Admin Create Promotion", False, "No promotion ID in response")
        
        promotion_id = created_promotion["id"]
        test_results["created_promotion_id"] = promotion_id
        logger.info(f"Created promotion with ID: {promotion_id}")
        
        # 3. Update the promotion
        logger.info(f"Testing PUT /api/admin/promotions/{promotion_id} endpoint")
        updated_promotion = new_promotion.copy()
        updated_promotion["name"] = f"Updated {new_promotion['name']}"
        updated_promotion["discount_value"] = 30.0
        
        response = requests.put(f"{API_URL}/admin/promotions/{promotion_id}", json=updated_promotion, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Update Promotion", False, f"Failed: {response.text}")
        
        logger.info(f"Successfully updated promotion: {promotion_id}")
        
        # 4. Delete (deactivate) the promotion
        logger.info(f"Testing DELETE /api/admin/promotions/{promotion_id} endpoint")
        response = requests.delete(f"{API_URL}/admin/promotions/{promotion_id}", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Delete Promotion", False, f"Failed: {response.text}")
        
        logger.info("Promotion successfully deactivated")
        return log_test_result("Admin Promotions", True, "Successfully managed promotions (list, create, update, delete)")
    except Exception as e:
        return log_test_result("Admin Promotions", False, f"Exception: {str(e)}")

def test_admin_categories():
    """Test admin category management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Categories", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. List categories
        logger.info("Testing GET /api/categories endpoint")
        response = requests.get(f"{API_URL}/categories")
        if response.status_code != 200:
            return log_test_result("List Categories", False, f"Failed: {response.text}")
        
        categories = response.json()
        logger.info(f"Found {len(categories)} categories")
        
        # 2. Create a new category
        logger.info("Testing POST /api/admin/categories endpoint")
        new_category = {
            "name": f"Test Category {uuid.uuid4().hex[:8]}",
            "description": "Test Category Description",
            "emoji": "🧪",
            "color": "#3B82F6"
        }
        
        response = requests.post(f"{API_URL}/admin/categories", json=new_category, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Category", False, f"Failed: {response.text}")
        
        created_category = response.json()
        if "id" not in created_category:
            return log_test_result("Admin Create Category", False, "No category ID in response")
        
        logger.info(f"Created category: {created_category['name']} with ID: {created_category['id']}")
        
        # Verify category was created
        response = requests.get(f"{API_URL}/categories")
        if response.status_code != 200:
            return log_test_result("Admin Create Category Verification", False, f"Failed: {response.text}")
        
        updated_categories = response.json()
        if not any(c["name"] == new_category["name"] for c in updated_categories):
            return log_test_result("Admin Create Category", False, "Category not found after creation")
        
        return log_test_result("Admin Categories", True, "Successfully managed categories (list, create)")
    except Exception as e:
        return log_test_result("Admin Categories", False, f"Exception: {str(e)}")

def test_admin_users():
    """Test admin user management"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Users", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. List users
        logger.info("Testing GET /api/admin/users endpoint")
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin List Users", False, f"Failed: {response.text}")
        
        users = response.json()
        if not isinstance(users, list):
            return log_test_result("Admin List Users", False, "Invalid users data")
        
        logger.info(f"Found {len(users)} users")
        
        # 2. Create a new admin user
        logger.info("Testing POST /api/admin/users/make-admin endpoint")
        new_admin = {
            "email": f"test_admin_{uuid.uuid4()}@example.com",
            "name": "Test Admin User"
        }
        
        response = requests.post(f"{API_URL}/admin/users/make-admin", json=new_admin, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Admin User", False, f"Failed: {response.text}")
        
        logger.info(f"Created new admin user: {new_admin['email']}")
        
        # Get the user list again to find the new admin
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Create Admin Verification", False, f"Failed: {response.text}")
        
        updated_users = response.json()
        new_admin_user = next((u for u in updated_users if u["email"] == new_admin["email"]), None)
        
        if not new_admin_user:
            return log_test_result("Admin Create Admin", False, "New admin not found in user list")
        
        if not new_admin_user.get("is_admin"):
            return log_test_result("Admin Create Admin", False, "User not marked as admin")
        
        # 3. Remove admin privileges
        logger.info(f"Testing DELETE /api/admin/users/{new_admin_user['id']}/remove-admin endpoint")
        response = requests.delete(f"{API_URL}/admin/users/{new_admin_user['id']}/remove-admin", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Remove Admin", False, f"Failed: {response.text}")
        
        logger.info(f"Removed admin privileges from user: {new_admin_user['id']}")
        
        # Verify admin was removed
        response = requests.get(f"{API_URL}/admin/users", headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Remove Admin Verification", False, f"Failed: {response.text}")
        
        final_users = response.json()
        updated_user = next((u for u in final_users if u["id"] == new_admin_user["id"]), None)
        
        if updated_user and updated_user.get("is_admin"):
            return log_test_result("Admin Remove Admin", False, "User still has admin privileges")
        
        return log_test_result("Admin Users", True, "Successfully managed admin users (list, create, remove)")
    except Exception as e:
        return log_test_result("Admin Users", False, f"Exception: {str(e)}")

def test_admin_emails():
    """Test admin email sending"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Emails", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # 1. Test discount email
        logger.info("Testing POST /api/admin/emails/send-discount endpoint")
        discount_params = {
            "user_email": "test@example.com",
            "user_name": "Test User",
            "coupon_code": "TESTADMIN",
            "discount_value": 25.0,
            "discount_type": "percentage",
            "expiry_date": "31/12/2024"
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-discount", params=discount_params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Send Discount Email", False, f"Failed: {response.text}")
        
        logger.info("Successfully sent discount email")
        
        # 2. Test birthday email
        logger.info("Testing POST /api/admin/emails/send-birthday endpoint")
        birthday_params = {
            "user_email": "test@example.com",
            "user_name": "Test User",
            "coupon_code": "BIRTHDAYADMIN",
            "discount_value": 30.0
        }
        
        response = requests.post(f"{API_URL}/admin/emails/send-birthday", params=birthday_params, headers=headers)
        if response.status_code != 200:
            return log_test_result("Admin Send Birthday Email", False, f"Failed: {response.text}")
        
        logger.info("Successfully sent birthday email")
        return log_test_result("Admin Emails", True, "Successfully sent admin emails (discount, birthday)")
    except Exception as e:
        return log_test_result("Admin Emails", False, f"Exception: {str(e)}")

def test_admin_dashboard():
    """Test admin dashboard endpoint"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Dashboard", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        logger.info("Testing GET /api/admin/dashboard endpoint")
        response = requests.get(f"{API_URL}/admin/dashboard", headers=headers)
        
        if response.status_code != 200:
            return log_test_result("Admin Dashboard", False, f"Failed: {response.text}")
        
        dashboard = response.json()
        if "stats" not in dashboard or "recent_orders" not in dashboard:
            return log_test_result("Admin Dashboard", False, "Invalid dashboard data")
        
        stats = dashboard["stats"]
        logger.info(f"Dashboard stats: {json.dumps(stats, indent=2)}")
        
        return log_test_result("Admin Dashboard", True, f"Dashboard retrieved with {len(dashboard['recent_orders'])} recent orders")
    except Exception as e:
        return log_test_result("Admin Dashboard", False, f"Exception: {str(e)}")

def run_admin_tests():
    """Run all admin tests and return results"""
    logger.info("Starting admin backend tests for Mystery Box Store")
    logger.info(f"Using backend URL: {API_URL}")
    
    # Admin authentication
    test_admin_login()
    
    # Admin dashboard
    test_admin_dashboard()
    
    # Admin order management
    test_admin_orders()
    
    # Admin product management
    test_admin_products()
    
    # Admin coupon management
    test_admin_coupons()
    
    # Admin promotion management
    test_admin_promotions()
    
    # Admin category management
    test_admin_categories()
    
    # Admin user management
    test_admin_users()
    
    # Admin email sending
    test_admin_emails()
    
    # Print summary
    logger.info("\n=== ADMIN TEST SUMMARY ===")
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
    run_admin_tests()