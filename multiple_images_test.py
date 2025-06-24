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

# Test data
TEST_ADMIN = {
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
    """Login as admin to get token for protected endpoints"""
    try:
        response = requests.post(f"{API_URL}/auth/login", json=TEST_ADMIN)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            logger.error(f"Admin login failed: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Admin login exception: {str(e)}")
        return None

def test_get_products_with_images():
    """Test GET /api/products to verify images field is populated"""
    try:
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("GET /api/products", False, f"Failed with status {response.status_code}: {response.text}")
        
        products = response.json()
        if not products:
            return log_test_result("GET /api/products", False, "No products returned")
        
        # Check if at least one product has images field
        has_images = any("images" in product and isinstance(product["images"], list) for product in products)
        
        if has_images:
            # Store a product ID with images for later tests
            for product in products:
                if "images" in product and product["images"]:
                    test_results["product_id_with_images"] = product["id"]
                    break
            
            return log_test_result("GET /api/products", True, f"Found {len(products)} products with images field properly populated")
        else:
            return log_test_result("GET /api/products", False, "No products have images field populated")
    
    except Exception as e:
        return log_test_result("GET /api/products", False, f"Exception: {str(e)}")

def test_get_product_details_with_images():
    """Test GET /api/products/{product_id} to verify images field is included"""
    if "product_id_with_images" not in test_results:
        # If we don't have a product with images, try to get any product
        try:
            response = requests.get(f"{API_URL}/products")
            if response.status_code == 200:
                products = response.json()
                if products:
                    test_results["product_id_with_images"] = products[0]["id"]
        except:
            pass
    
    if "product_id_with_images" not in test_results:
        return log_test_result("GET /api/products/{product_id}", False, "No product ID available for testing")
    
    try:
        product_id = test_results["product_id_with_images"]
        response = requests.get(f"{API_URL}/products/{product_id}")
        
        if response.status_code != 200:
            return log_test_result("GET /api/products/{product_id}", False, f"Failed with status {response.status_code}: {response.text}")
        
        product = response.json()
        
        if "images" not in product:
            return log_test_result("GET /api/products/{product_id}", False, "Product does not have images field")
        
        if not isinstance(product["images"], list):
            return log_test_result("GET /api/products/{product_id}", False, "Product images field is not a list")
        
        return log_test_result("GET /api/products/{product_id}", True, 
                              f"Product has images field with {len(product['images'])} images")
    
    except Exception as e:
        return log_test_result("GET /api/products/{product_id}", False, f"Exception: {str(e)}")

def test_create_product_with_images():
    """Test POST /api/admin/products to create a product with multiple images"""
    admin_token = admin_login()
    if not admin_token:
        return log_test_result("POST /api/admin/products", False, "Admin login failed")
    
    # Sample base64 image (1x1 pixel transparent PNG)
    sample_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    # Create test product with multiple images
    product_data = {
        "name": "Test Multiple Images Product",
        "description": "Testing multiple images functionality",
        "category": "test_category",
        "price": 25.99,
        "subscription_prices": {
            "3_months": 22.99,
            "6_months": 19.99,
            "12_months": 16.99
        },
        "image_url": "https://via.placeholder.com/400x300/blue/white?text=Main+Image",
        "images": [
            "https://via.placeholder.com/400x300/green/white?text=Gallery+1",
            "https://via.placeholder.com/400x300/red/white?text=Gallery+2"
        ],
        "stock_quantity": 100,
        "featured": False
    }
    
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{API_URL}/admin/products", json=product_data, headers=headers)
        
        if response.status_code != 200:
            return log_test_result("POST /api/admin/products", False, f"Failed with status {response.status_code}: {response.text}")
        
        created_product = response.json()
        test_results["created_product_id"] = created_product["id"]
        
        # Verify images field in response
        if "images" not in created_product:
            return log_test_result("POST /api/admin/products", False, "Created product does not have images field")
        
        if not isinstance(created_product["images"], list):
            return log_test_result("POST /api/admin/products", False, "Created product images field is not a list")
        
        if len(created_product["images"]) != 2:
            return log_test_result("POST /api/admin/products", False, f"Expected 2 images, got {len(created_product['images'])}")
        
        return log_test_result("POST /api/admin/products", True, 
                              f"Successfully created product with {len(created_product['images'])} images")
    
    except Exception as e:
        return log_test_result("POST /api/admin/products", False, f"Exception: {str(e)}")

def test_create_product_with_base64_images():
    """Test POST /api/admin/products to create a product with base64 images"""
    admin_token = admin_login()
    if not admin_token:
        return log_test_result("POST /api/admin/products (base64)", False, "Admin login failed")
    
    # Sample base64 image (1x1 pixel transparent PNG)
    sample_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    # Create test product with base64 images
    product_data = {
        "name": "Test Base64 Images Product",
        "description": "Testing base64 images functionality",
        "category": "test_category",
        "price": 29.99,
        "subscription_prices": {
            "3_months": 26.99,
            "6_months": 23.99,
            "12_months": 20.99
        },
        "image_url": "https://via.placeholder.com/400x300/purple/white?text=Main+Image",
        "image_base64": f"data:image/png;base64,{sample_base64}",
        "images_base64": [
            f"data:image/png;base64,{sample_base64}",
            f"data:image/png;base64,{sample_base64}"
        ],
        "stock_quantity": 100,
        "featured": False
    }
    
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{API_URL}/admin/products", json=product_data, headers=headers)
        
        if response.status_code != 200:
            return log_test_result("POST /api/admin/products (base64)", False, f"Failed with status {response.status_code}: {response.text}")
        
        created_product = response.json()
        test_results["created_product_base64_id"] = created_product["id"]
        
        # Verify images field in response
        if "images" not in created_product:
            return log_test_result("POST /api/admin/products (base64)", False, "Created product does not have images field")
        
        if not isinstance(created_product["images"], list):
            return log_test_result("POST /api/admin/products (base64)", False, "Created product images field is not a list")
        
        if len(created_product["images"]) != 2:
            return log_test_result("POST /api/admin/products (base64)", False, f"Expected 2 images, got {len(created_product['images'])}")
        
        # Verify image_url is set to the base64 image
        if not created_product["image_url"].startswith("data:image/png;base64,"):
            return log_test_result("POST /api/admin/products (base64)", False, "image_url was not set to the base64 image")
        
        return log_test_result("POST /api/admin/products (base64)", True, 
                              f"Successfully created product with base64 images")
    
    except Exception as e:
        return log_test_result("POST /api/admin/products (base64)", False, f"Exception: {str(e)}")

def test_update_product_with_images():
    """Test PUT /api/admin/products/{product_id} to update a product with multiple images"""
    if "created_product_id" not in test_results:
        return log_test_result("PUT /api/admin/products/{product_id}", False, "No product ID available for testing")
    
    admin_token = admin_login()
    if not admin_token:
        return log_test_result("PUT /api/admin/products/{product_id}", False, "Admin login failed")
    
    # Update product with new images
    product_data = {
        "name": "Updated Multiple Images Product",
        "description": "Testing updated multiple images functionality",
        "category": "test_category",
        "price": 27.99,
        "subscription_prices": {
            "3_months": 24.99,
            "6_months": 21.99,
            "12_months": 18.99
        },
        "image_url": "https://via.placeholder.com/400x300/yellow/black?text=Updated+Main+Image",
        "images": [
            "https://via.placeholder.com/400x300/orange/black?text=Updated+Gallery+1",
            "https://via.placeholder.com/400x300/pink/black?text=Updated+Gallery+2",
            "https://via.placeholder.com/400x300/cyan/black?text=Updated+Gallery+3"
        ],
        "stock_quantity": 150,
        "featured": True
    }
    
    try:
        product_id = test_results["created_product_id"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.put(f"{API_URL}/admin/products/{product_id}", json=product_data, headers=headers)
        
        if response.status_code != 200:
            return log_test_result("PUT /api/admin/products/{product_id}", False, f"Failed with status {response.status_code}: {response.text}")
        
        # Verify the update by getting the product
        response = requests.get(f"{API_URL}/products/{product_id}")
        if response.status_code != 200:
            return log_test_result("PUT /api/admin/products/{product_id}", False, "Failed to get updated product")
        
        updated_product = response.json()
        
        # Verify images field in response
        if "images" not in updated_product:
            return log_test_result("PUT /api/admin/products/{product_id}", False, "Updated product does not have images field")
        
        if not isinstance(updated_product["images"], list):
            return log_test_result("PUT /api/admin/products/{product_id}", False, "Updated product images field is not a list")
        
        if len(updated_product["images"]) != 3:
            return log_test_result("PUT /api/admin/products/{product_id}", False, f"Expected 3 images, got {len(updated_product['images'])}")
        
        return log_test_result("PUT /api/admin/products/{product_id}", True, 
                              f"Successfully updated product with {len(updated_product['images'])} images")
    
    except Exception as e:
        return log_test_result("PUT /api/admin/products/{product_id}", False, f"Exception: {str(e)}")

def test_update_product_with_base64_images():
    """Test PUT /api/admin/products/{product_id} to update a product with base64 images"""
    if "created_product_base64_id" not in test_results:
        return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, "No product ID available for testing")
    
    admin_token = admin_login()
    if not admin_token:
        return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, "Admin login failed")
    
    # Sample base64 image (1x1 pixel transparent PNG)
    sample_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    # Update product with new base64 images
    product_data = {
        "name": "Updated Base64 Images Product",
        "description": "Testing updated base64 images functionality",
        "category": "test_category",
        "price": 31.99,
        "subscription_prices": {
            "3_months": 28.99,
            "6_months": 25.99,
            "12_months": 22.99
        },
        "image_url": "https://via.placeholder.com/400x300/gray/white?text=Updated+Main+Image",
        "image_base64": f"data:image/png;base64,{sample_base64}",
        "images_base64": [
            f"data:image/png;base64,{sample_base64}",
            f"data:image/png;base64,{sample_base64}",
            f"data:image/png;base64,{sample_base64}"
        ],
        "stock_quantity": 200,
        "featured": True
    }
    
    try:
        product_id = test_results["created_product_base64_id"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.put(f"{API_URL}/admin/products/{product_id}", json=product_data, headers=headers)
        
        if response.status_code != 200:
            return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, f"Failed with status {response.status_code}: {response.text}")
        
        # Verify the update by getting the product
        response = requests.get(f"{API_URL}/products/{product_id}")
        if response.status_code != 200:
            return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, "Failed to get updated product")
        
        updated_product = response.json()
        
        # Verify images field in response
        if "images" not in updated_product:
            return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, "Updated product does not have images field")
        
        if not isinstance(updated_product["images"], list):
            return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, "Updated product images field is not a list")
        
        if len(updated_product["images"]) != 3:
            return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, f"Expected 3 images, got {len(updated_product['images'])}")
        
        # Verify image_url is set to the base64 image
        if not updated_product["image_url"].startswith("data:image/png;base64,"):
            return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, "image_url was not set to the base64 image")
        
        return log_test_result("PUT /api/admin/products/{product_id} (base64)", True, 
                              f"Successfully updated product with base64 images")
    
    except Exception as e:
        return log_test_result("PUT /api/admin/products/{product_id} (base64)", False, f"Exception: {str(e)}")

def cleanup_test_products():
    """Clean up test products created during testing"""
    admin_token = admin_login()
    if not admin_token:
        logger.error("Admin login failed during cleanup")
        return
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Delete products created during testing
    for key in ["created_product_id", "created_product_base64_id"]:
        if key in test_results:
            try:
                product_id = test_results[key]
                response = requests.delete(f"{API_URL}/admin/products/{product_id}", headers=headers)
                if response.status_code == 200:
                    logger.info(f"Successfully deleted test product {product_id}")
                else:
                    logger.warning(f"Failed to delete test product {product_id}: {response.text}")
            except Exception as e:
                logger.error(f"Exception during cleanup: {str(e)}")

def run_tests():
    """Run all tests for multiple images functionality"""
    logger.info("Starting tests for multiple images functionality")
    
    # Test GET endpoints
    test_get_products_with_images()
    test_get_product_details_with_images()
    
    # Test POST endpoints
    test_create_product_with_images()
    test_create_product_with_base64_images()
    
    # Test PUT endpoints
    test_update_product_with_images()
    test_update_product_with_base64_images()
    
    # Clean up test data
    cleanup_test_products()
    
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