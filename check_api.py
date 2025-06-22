import requests
import json

# API URL
BACKEND_URL = "https://mystery-boxloja.onrender.com"
API_URL = f"{BACKEND_URL}/api"

# Get products
print("=== PRODUCTS API RESPONSE ===")
response = requests.get(f"{API_URL}/products")
if response.status_code == 200:
    products = response.json()
    print(f"Total products: {len(products)}")
    
    for product in products:
        print(f"Product: {product.get('name')}")
        print(f"  - ID: {product.get('id')}")
        
        # Check image_url
        if 'image_url' in product:
            image_url = product['image_url']
            is_base64 = image_url.startswith('data:image') if image_url else False
            print(f"  - image_url: {'Base64 image' if is_base64 else image_url[:50] + '...' if image_url and len(image_url) > 50 else image_url}")
        else:
            print("  - image_url: Not found")
        
        print()
else:
    print(f"Failed to get products: {response.status_code} - {response.text}")

# Get coupons
print("\n=== COUPONS API RESPONSES ===")
for code in ["WELCOME10", "SAVE5", "PREMIUM20"]:
    print(f"Validating coupon: {code}")
    response = requests.get(f"{API_URL}/coupons/validate/{code}")
    if response.status_code == 200:
        coupon = response.json()
        print(f"  - Description: {coupon.get('description')}")
        print(f"  - Discount: {coupon.get('discount_type')} {coupon.get('discount_value')}")
        print(f"  - Min order value: {coupon.get('min_order_value')}")
        print(f"  - Active: {coupon.get('is_active')}")
    else:
        print(f"  - Failed: {response.status_code} - {response.text}")
    print()