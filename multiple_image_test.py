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
    """Login as admin and get token"""
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

def generate_sample_base64_image():
    """Generate a simple base64 encoded 1x1 pixel image for testing"""
    # 1x1 pixel red PNG image
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def test_create_product_with_multiple_images():
    """Test creating a product with multiple images"""
    if "admin_token" not in test_results:
        admin_login()
        if "admin_token" not in test_results:
            return log_test_result("Create Product with Multiple Images", False, "Admin login required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Generate unique product name
        product_name = f"Test Product {uuid.uuid4().hex[:8]}"
        
        # Create product with both image_base64 and images_base64
        product_data = {
            "name": product_name,
            "description": "Test product with multiple images",
            "category": "test",
            "price": 29.99,
            "subscription_prices": {
                "3_months": 26.99,
                "6_months": 25.49,
                "12_months": 23.99
            },
            "image_url": "https://example.com/placeholder.jpg",
            "image_base64": generate_sample_base64_image(),  # Primary image
            "images": ["https://example.com/gallery1.jpg", "https://example.com/gallery2.jpg"],
            "images_base64": [
                generate_sample_base64_image(),  # Gallery image 1
                generate_sample_base64_image()   # Gallery image 2
            ],
            "stock_quantity": 100,
            "featured": True
        }
        
        response = requests.post(f"{API_URL}/admin/products", json=product_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Create Product with Multiple Images", False, f"Failed: {response.text}")
        
        created_product = response.json()
        if not created_product or "id" not in created_product:
            return log_test_result("Create Product with Multiple Images", False, "Invalid product data in response")
        
        # Store product ID for later tests
        test_results["product_id"] = created_product["id"]
        
        # Verify primary image (should be the base64 image, not the URL)
        if created_product["image_url"] != product_data["image_base64"]:
            return log_test_result("Create Product with Multiple Images", False, "Primary image not set correctly")
        
        # Verify gallery images
        if len(created_product["images"]) != 4:  # 2 URLs + 2 base64 images
            return log_test_result("Create Product with Multiple Images", False, 
                                  f"Expected 4 gallery images, got {len(created_product['images'])}")
        
        return log_test_result("Create Product with Multiple Images", True, 
                              f"Product created with ID: {created_product['id']} and {len(created_product['images'])} gallery images")
    except Exception as e:
        return log_test_result("Create Product with Multiple Images", False, f"Exception: {str(e)}")

def test_get_product_with_multiple_images():
    """Test retrieving a product with multiple images"""
    if "product_id" not in test_results:
        return log_test_result("Get Product with Multiple Images", False, "No product ID available")
    
    try:
        response = requests.get(f"{API_URL}/products/{test_results['product_id']}")
        if response.status_code != 200:
            return log_test_result("Get Product with Multiple Images", False, f"Failed: {response.text}")
        
        product = response.json()
        if not product or "id" not in product:
            return log_test_result("Get Product with Multiple Images", False, "Invalid product data")
        
        # Verify image_url field
        if not product.get("image_url"):
            return log_test_result("Get Product with Multiple Images", False, "No primary image (image_url) found")
        
        # Verify images field
        if not product.get("images") or not isinstance(product["images"], list):
            return log_test_result("Get Product with Multiple Images", False, "No gallery images found or invalid format")
        
        # Verify subscription_prices field
        if not product.get("subscription_prices") or not isinstance(product["subscription_prices"], dict):
            return log_test_result("Get Product with Multiple Images", False, "No subscription prices found or invalid format")
        
        return log_test_result("Get Product with Multiple Images", True, 
                              f"Product retrieved with {len(product['images'])} gallery images")
    except Exception as e:
        return log_test_result("Get Product with Multiple Images", False, f"Exception: {str(e)}")

def test_update_product_with_multiple_images():
    """Test updating a product with multiple images"""
    if "product_id" not in test_results or "admin_token" not in test_results:
        return log_test_result("Update Product with Multiple Images", False, "Product ID and admin token required")
    
    try:
        headers = {"Authorization": f"Bearer {test_results['admin_token']}"}
        
        # Update product with new images
        product_data = {
            "name": f"Updated Test Product {uuid.uuid4().hex[:8]}",
            "description": "Updated test product with multiple images",
            "category": "test_updated",
            "price": 39.99,
            "subscription_prices": {
                "3_months": 35.99,
                "6_months": 33.99,
                "12_months": 31.99
            },
            "image_url": "https://example.com/updated_placeholder.jpg",
            "image_base64": generate_sample_base64_image(),  # New primary image
            "images": ["https://example.com/updated_gallery1.jpg"],
            "images_base64": [
                generate_sample_base64_image(),  # New gallery image 1
                generate_sample_base64_image(),  # New gallery image 2
                generate_sample_base64_image()   # New gallery image 3
            ],
            "stock_quantity": 200,
            "featured": False
        }
        
        response = requests.put(f"{API_URL}/admin/products/{test_results['product_id']}", json=product_data, headers=headers)
        if response.status_code != 200:
            return log_test_result("Update Product with Multiple Images", False, f"Failed: {response.text}")
        
        # Verify the update by retrieving the product
        response = requests.get(f"{API_URL}/products/{test_results['product_id']}")
        if response.status_code != 200:
            return log_test_result("Update Product with Multiple Images", False, f"Failed to retrieve updated product: {response.text}")
        
        updated_product = response.json()
        
        # Verify primary image (should be the base64 image, not the URL)
        if updated_product["image_url"] != product_data["image_base64"]:
            return log_test_result("Update Product with Multiple Images", False, "Primary image not updated correctly")
        
        # Verify gallery images
        if len(updated_product["images"]) != 4:  # 1 URL + 3 base64 images
            return log_test_result("Update Product with Multiple Images", False, 
                                  f"Expected 4 gallery images, got {len(updated_product['images'])}")
        
        # Verify subscription prices
        if not updated_product.get("subscription_prices") or not isinstance(updated_product["subscription_prices"], dict):
            return log_test_result("Update Product with Multiple Images", False, "Subscription prices not updated correctly")
        
        return log_test_result("Update Product with Multiple Images", True, 
                              f"Product updated with {len(updated_product['images'])} gallery images")
    except Exception as e:
        return log_test_result("Update Product with Multiple Images", False, f"Exception: {str(e)}")

def run_tests():
    """Run all tests and return results"""
    logger.info("Starting multiple image functionality tests for AdminProducts")
    
    # Create product with multiple images
    test_create_product_with_multiple_images()
    
    # Get product with multiple images
    test_get_product_with_multiple_images()
    
    # Update product with multiple images
    test_update_product_with_multiple_images()
    
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
    run_tests()