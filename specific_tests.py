import requests
import json
import uuid
import base64
from datetime import datetime
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

def test_chat_session_rejection():
    """Test chat session rejection"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Chat Session Rejection", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Get all chat sessions
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Get Chat Sessions", False, f"Failed: {response.text}")
        
        sessions = response.json()
        if not sessions:
            return log_test_result("Chat Session Rejection", False, "No chat sessions available for testing")
        
        # Use the first active session for testing
        active_sessions = [s for s in sessions if s["status"] == "active" or s["status"] == "waiting"]
        if not active_sessions:
            return log_test_result("Chat Session Rejection", False, "No active chat sessions available for testing")
        
        session_id = active_sessions[0]["id"]
        
        # Test reject session
        response = requests.put(f"{API_URL}/admin/chat/sessions/{session_id}/reject", headers=headers)
        if response.status_code != 200:
            return log_test_result("Chat Session Rejection", False, f"Failed: {response.text}")
        
        # Verify session was rejected
        response = requests.get(f"{API_URL}/admin/chat/sessions", headers=headers)
        if response.status_code != 200:
            return log_test_result("Verify Chat Session Rejection", False, f"Failed: {response.text}")
        
        sessions = response.json()
        rejected_session = next((s for s in sessions if s["id"] == session_id), None)
        
        if not rejected_session:
            return log_test_result("Verify Chat Session Rejection", False, "Session not found after rejection")
        
        if rejected_session["status"] != "rejected":
            return log_test_result("Verify Chat Session Rejection", False, f"Session status is {rejected_session['status']}, expected 'rejected'")
        
        return log_test_result("Chat Session Rejection", True, "Successfully rejected chat session")
    except Exception as e:
        return log_test_result("Chat Session Rejection", False, f"Exception: {str(e)}")

def test_product_image_upload():
    """Test product image upload with base64"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Product Image Upload", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Create a sample base64 image (very small transparent pixel)
        sample_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        
        # Create a new product with base64 image
        new_product = {
            "name": f"Test Product with Base64 {uuid.uuid4().hex[:8]}",
            "description": "This is a test product with base64 image",
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
        if response.status_code != 200:
            return log_test_result("Create Product with Base64 Image", False, f"Failed: {response.text}")
        
        created_product = response.json()
        if "id" not in created_product:
            return log_test_result("Create Product with Base64 Image", False, "No product ID in response")
        
        product_id = created_product["id"]
        
        # Verify the image was saved
        response = requests.get(f"{API_URL}/products/{product_id}")
        if response.status_code != 200:
            return log_test_result("Verify Product Image", False, f"Failed to get product: {response.text}")
        
        product = response.json()
        
        # Check if base64 was prioritized over image_url
        if product["image_url"] == new_product["image_url"]:
            return log_test_result("Verify Product Image", False, "Base64 image was not prioritized over image_url")
        
        if product["image_url"] == sample_base64:
            return log_test_result("Verify Product Image", True, "Base64 image was correctly saved and prioritized")
        
        return log_test_result("Product Image Upload", True, "Successfully tested product image upload with base64")
    except Exception as e:
        return log_test_result("Product Image Upload", False, f"Exception: {str(e)}")

def test_checkout_order_id():
    """Test checkout process and verify order_id is returned"""
    try:
        # Get a product for testing
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Get Products for Checkout", False, f"Failed: {response.text}")
        
        products = response.json()
        if not products:
            return log_test_result("Get Products for Checkout", False, "No products available for testing")
        
        product_id = products[0]["id"]
        
        # Create a new session ID for this test
        checkout_session_id = str(uuid.uuid4())
        
        # Add product to cart
        cart_item = {
            "product_id": product_id,
            "quantity": 1
        }
        
        response = requests.post(f"{API_URL}/cart/{checkout_session_id}/add", json=cart_item)
        if response.status_code != 200:
            return log_test_result("Add to Cart for Checkout", False, f"Failed: {response.text}")
        
        # Create checkout with bank transfer payment
        checkout_data = {
            "cart_id": checkout_session_id,
            "shipping_address": "Rua de Teste, 123, Lisboa",
            "phone": "+351912345678",
            "nif": "501964843",  # Valid Portuguese NIF
            "payment_method": "bank_transfer",
            "shipping_method": "standard",
            "origin_url": BACKEND_URL
        }
        
        response = requests.post(f"{API_URL}/checkout", json=checkout_data)
        if response.status_code != 200:
            return log_test_result("Checkout Order ID", False, f"Failed: {response.text}")
        
        checkout_result = response.json()
        if "order_id" not in checkout_result:
            return log_test_result("Checkout Order ID", False, "No order_id in response")
        
        order_id = checkout_result["order_id"]
        
        # Check if cart was cleared after checkout
        response = requests.get(f"{API_URL}/cart/{checkout_session_id}")
        if response.status_code != 200:
            return log_test_result("Cart Cleared After Checkout", False, f"Failed to get cart: {response.text}")
        
        cart_after_checkout = response.json()
        if cart_after_checkout.get("items") and len(cart_after_checkout["items"]) > 0:
            return log_test_result("Cart Cleared After Checkout", False, "Cart not cleared after checkout")
        
        log_test_result("Cart Cleared After Checkout", True, "Cart was cleared after checkout")
        
        return log_test_result("Checkout Order ID", True, f"Order created with ID: {order_id}")
    except Exception as e:
        return log_test_result("Checkout Order ID", False, f"Exception: {str(e)}")

def test_admin_order_status_update():
    """Test admin order status update"""
    if "admin_token" not in test_results:
        test_admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Admin Order Status Update", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Get all orders
        response = requests.get(f"{API_URL}/admin/orders", headers=headers)
        if response.status_code != 200:
            return log_test_result("Get Orders", False, f"Failed: {response.text}")
        
        orders = response.json()
        if not orders:
            return log_test_result("Admin Order Status Update", False, "No orders available for testing")
        
        order_id = orders[0]["id"]
        
        # Test valid status update
        valid_statuses = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
        
        for status in valid_statuses:
            response = requests.put(
                f"{API_URL}/admin/orders/{order_id}/status?status={status}", 
                headers=headers
            )
            
            if response.status_code != 200:
                log_test_result(f"Update Order Status to {status}", False, f"Failed: {response.text}")
                continue
            
            # Verify status was updated in the database
            response = requests.get(f"{API_URL}/admin/orders", headers=headers)
            if response.status_code != 200:
                log_test_result(f"Get Orders After Status Update to {status}", False, f"Failed: {response.text}")
                continue
            
            orders = response.json()
            updated_order = next((o for o in orders if o["id"] == order_id), None)
            
            if not updated_order:
                log_test_result(f"Update Order Status to {status}", False, "Order not found after update")
                continue
                
            if updated_order.get("order_status") != status:
                log_test_result(f"Update Order Status to {status}", False, f"Order status not updated to {status}")
                continue
            
            log_test_result(f"Update Order Status to {status}", True, f"Successfully updated order status to {status}")
        
        # Test invalid status update
        response = requests.put(
            f"{API_URL}/admin/orders/{order_id}/status?status=invalid_status", 
            headers=headers
        )
        
        if response.status_code == 400:
            log_test_result("Update Order Status with Invalid Status", True, "Correctly rejected invalid status")
        else:
            log_test_result("Update Order Status with Invalid Status", False, f"Did not reject invalid status: {response.status_code}, {response.text}")
        
        return log_test_result("Admin Order Status Update", True, "Successfully tested order status updates")
    except Exception as e:
        return log_test_result("Admin Order Status Update", False, f"Exception: {str(e)}")

def run_specific_tests():
    """Run specific tests for Phase 3 issues"""
    logger.info("Starting specific tests for Phase 3 issues")
    
    # Admin login
    test_admin_login()
    
    # Test 1: Checkout - Order ID
    test_checkout_order_id()
    
    # Test 2: Admin - Order Status Update
    test_admin_order_status_update()
    
    # Test 3: Chat Session Rejection
    test_chat_session_rejection()
    
    # Test 4: Product Image Upload
    test_product_image_upload()
    
    # Print summary
    logger.info("\n=== SPECIFIC TESTS SUMMARY ===")
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