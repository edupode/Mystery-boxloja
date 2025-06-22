import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

# Load environment variables
load_dotenv('/app/backend/.env')
MONGO_URL = os.getenv('MONGO_URL')
DB_NAME = os.getenv('DB_NAME')

# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Check products
print("=== PRODUCTS ===")
products = list(db.products.find())
print(f"Total products: {len(products)}")

# Print product names and check if they have image_url or image_base64
for product in products:
    print(f"Product: {product.get('name')}")
    print(f"  - ID: {product.get('id')}")
    
    # Check for image fields
    if 'image_url' in product:
        image_url = product['image_url']
        is_base64 = image_url.startswith('data:image') if image_url else False
        print(f"  - image_url: {'Base64 image' if is_base64 else image_url[:50] + '...' if image_url and len(image_url) > 50 else image_url}")
    else:
        print("  - image_url: Not found")
    
    if 'image_base64' in product:
        print(f"  - image_base64: {'Present (too long to display)' if product['image_base64'] else 'Empty'}")
    else:
        print("  - image_base64: Not found")
    
    # Check for images array
    if 'images' in product:
        images = product['images']
        print(f"  - images: {len(images)} images")
        for i, img in enumerate(images[:2]):  # Show only first 2 images
            is_base64 = img.startswith('data:image') if img else False
            print(f"    - Image {i+1}: {'Base64 image' if is_base64 else img[:50] + '...' if img and len(img) > 50 else img}")
        if len(images) > 2:
            print(f"    - ... and {len(images) - 2} more")
    else:
        print("  - images: Not found")
    
    print()

# Check coupons
print("\n=== COUPONS ===")
coupons = list(db.coupons.find())
print(f"Total coupons: {len(coupons)}")

for coupon in coupons:
    print(f"Coupon: {coupon.get('code')}")
    print(f"  - Description: {coupon.get('description')}")
    print(f"  - Discount: {coupon.get('discount_type')} {coupon.get('discount_value')}")
    print(f"  - Min order value: {coupon.get('min_order_value')}")
    print(f"  - Active: {coupon.get('is_active')}")
    print()