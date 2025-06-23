import requests
import json
import base64
import re
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

# Test results
test_results = {}

def log_test_result(test_name, success, message=""):
    """Log test result and store in results dictionary"""
    status = "PASSED" if success else "FAILED"
    logger.info(f"{test_name}: {status} {message}")
    test_results[test_name] = {"success": success, "message": message}
    return success

def is_valid_base64(s):
    """Check if a string is valid base64 encoded"""
    try:
        # Check if the string has valid base64 format
        if not re.match(r'^[A-Za-z0-9+/]+={0,2}$', s):
            return False
        
        # Try to decode
        base64.b64decode(s)
        return True
    except Exception:
        return False

def test_products_images():
    """Test if all products have valid image_url"""
    try:
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Products Images", False, f"Failed to get products: {response.text}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("Products Images", False, "No products returned or invalid format")
        
        missing_images = []
        invalid_images = []
        
        for product in products:
            # Check if image_url exists
            if not product.get("image_url"):
                missing_images.append(product.get("id", "unknown"))
                continue
            
            # Check if image_url is a base64 string
            image_url = product.get("image_url", "")
            if image_url.startswith("data:image"):
                # Extract the base64 part
                try:
                    base64_part = image_url.split(",")[1]
                    if not is_valid_base64(base64_part):
                        invalid_images.append(product.get("id", "unknown"))
                except IndexError:
                    invalid_images.append(product.get("id", "unknown"))
        
        if missing_images:
            return log_test_result("Products Images", False, f"{len(missing_images)} products missing image_url: {missing_images[:3]}...")
        
        if invalid_images:
            return log_test_result("Products Images", False, f"{len(invalid_images)} products with invalid base64 image: {invalid_images[:3]}...")
        
        return log_test_result("Products Images", True, f"All {len(products)} products have valid image_url")
    except Exception as e:
        return log_test_result("Products Images", False, f"Exception: {str(e)}")

def test_featured_products_images():
    """Test if featured products have valid image_url"""
    try:
        response = requests.get(f"{API_URL}/products?featured=true")
        if response.status_code != 200:
            return log_test_result("Featured Products Images", False, f"Failed to get featured products: {response.text}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("Featured Products Images", False, "No featured products returned or invalid format")
        
        missing_images = []
        invalid_images = []
        
        for product in products:
            # Check if image_url exists
            if not product.get("image_url"):
                missing_images.append(product.get("id", "unknown"))
                continue
            
            # Check if image_url is a base64 string
            image_url = product.get("image_url", "")
            if image_url.startswith("data:image"):
                # Extract the base64 part
                try:
                    base64_part = image_url.split(",")[1]
                    if not is_valid_base64(base64_part):
                        invalid_images.append(product.get("id", "unknown"))
                except IndexError:
                    invalid_images.append(product.get("id", "unknown"))
        
        if missing_images:
            return log_test_result("Featured Products Images", False, f"{len(missing_images)} featured products missing image_url: {missing_images[:3]}...")
        
        if invalid_images:
            return log_test_result("Featured Products Images", False, f"{len(invalid_images)} featured products with invalid base64 image: {invalid_images[:3]}...")
        
        return log_test_result("Featured Products Images", True, f"All {len(products)} featured products have valid image_url")
    except Exception as e:
        return log_test_result("Featured Products Images", False, f"Exception: {str(e)}")

def test_product_detail_images():
    """Test if individual product details have valid image_url"""
    try:
        # First get a list of products to test
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Product Detail Images", False, f"Failed to get products: {response.text}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("Product Detail Images", False, "No products returned or invalid format")
        
        # Test the first 3 products
        test_products = products[:3]
        missing_images = []
        invalid_images = []
        
        for product in test_products:
            product_id = product.get("id")
            if not product_id:
                continue
            
            # Get product details
            detail_response = requests.get(f"{API_URL}/products/{product_id}")
            if detail_response.status_code != 200:
                log_test_result(f"Product Detail {product_id}", False, f"Failed to get product details: {detail_response.text}")
                continue
            
            product_detail = detail_response.json()
            
            # Check if image_url exists
            if not product_detail.get("image_url"):
                missing_images.append(product_id)
                continue
            
            # Check if image_url is a base64 string
            image_url = product_detail.get("image_url", "")
            if image_url.startswith("data:image"):
                # Extract the base64 part
                try:
                    base64_part = image_url.split(",")[1]
                    if not is_valid_base64(base64_part):
                        invalid_images.append(product_id)
                except IndexError:
                    invalid_images.append(product_id)
        
        if missing_images:
            return log_test_result("Product Detail Images", False, f"{len(missing_images)} product details missing image_url: {missing_images}")
        
        if invalid_images:
            return log_test_result("Product Detail Images", False, f"{len(invalid_images)} product details with invalid base64 image: {invalid_images}")
        
        return log_test_result("Product Detail Images", True, f"All tested product details have valid image_url")
    except Exception as e:
        return log_test_result("Product Detail Images", False, f"Exception: {str(e)}")

def test_products_by_category():
    """Test if products filtered by category have valid image_url"""
    try:
        # First get categories
        response = requests.get(f"{API_URL}/categories")
        if response.status_code != 200:
            return log_test_result("Products by Category Images", False, f"Failed to get categories: {response.text}")
        
        categories = response.json()
        if not categories or not isinstance(categories, list):
            return log_test_result("Products by Category Images", False, "No categories returned or invalid format")
        
        # Test the first 2 categories
        test_categories = categories[:2]
        category_results = {}
        
        for category in test_categories:
            category_id = category.get("id")
            if not category_id:
                continue
            
            # Get products by category
            response = requests.get(f"{API_URL}/products?category={category_id}")
            if response.status_code != 200:
                category_results[category_id] = {"success": False, "message": f"Failed to get products: {response.text}"}
                continue
            
            products = response.json()
            if not products or not isinstance(products, list):
                category_results[category_id] = {"success": False, "message": "No products returned or invalid format"}
                continue
            
            missing_images = []
            invalid_images = []
            
            for product in products:
                # Check if image_url exists
                if not product.get("image_url"):
                    missing_images.append(product.get("id", "unknown"))
                    continue
                
                # Check if image_url is a base64 string
                image_url = product.get("image_url", "")
                if image_url.startswith("data:image"):
                    # Extract the base64 part
                    try:
                        base64_part = image_url.split(",")[1]
                        if not is_valid_base64(base64_part):
                            invalid_images.append(product.get("id", "unknown"))
                    except IndexError:
                        invalid_images.append(product.get("id", "unknown"))
            
            if missing_images or invalid_images:
                category_results[category_id] = {
                    "success": False, 
                    "message": f"Missing images: {len(missing_images)}, Invalid images: {len(invalid_images)}"
                }
            else:
                category_results[category_id] = {
                    "success": True, 
                    "message": f"All {len(products)} products have valid image_url"
                }
        
        # Check if all categories passed
        all_passed = all(result.get("success") for result in category_results.values())
        
        if all_passed:
            return log_test_result("Products by Category Images", True, "All tested categories have products with valid images")
        else:
            failed_categories = [cat_id for cat_id, result in category_results.items() if not result.get("success")]
            return log_test_result("Products by Category Images", False, f"Issues with images in categories: {failed_categories}")
    except Exception as e:
        return log_test_result("Products by Category Images", False, f"Exception: {str(e)}")

def check_image_field_names():
    """Check if the backend is using the correct field names for images"""
    try:
        # Get a product
        response = requests.get(f"{API_URL}/products")
        if response.status_code != 200:
            return log_test_result("Image Field Names", False, f"Failed to get products: {response.text}")
        
        products = response.json()
        if not products or not isinstance(products, list):
            return log_test_result("Image Field Names", False, "No products returned or invalid format")
        
        # Check the first product
        product = products[0]
        
        # Check which fields are present
        has_image_url = "image_url" in product
        has_images = "images" in product
        
        field_info = f"Fields present - image_url: {has_image_url}, images: {has_images}"
        
        # Check if both fields have values
        if has_image_url and has_images:
            image_url_value = bool(product.get("image_url"))
            images_value = bool(product.get("images"))
            field_info += f", image_url has value: {image_url_value}, images has value: {images_value}"
        
        return log_test_result("Image Field Names", True, field_info)
    except Exception as e:
        return log_test_result("Image Field Names", False, f"Exception: {str(e)}")

def run_all_tests():
    """Run all tests and return results"""
    logger.info("Starting image tests for Mystery Box Store products")
    
    # Check field names first
    check_image_field_names()
    
    # Test all products
    test_products_images()
    
    # Test featured products
    test_featured_products_images()
    
    # Test individual product details
    test_product_detail_images()
    
    # Test products by category
    test_products_by_category()
    
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
    run_all_tests()