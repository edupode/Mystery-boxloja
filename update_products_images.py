#!/usr/bin/env python3

import asyncio
import base64
import io
import os
import sys
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import requests
from PIL import Image

# Load environment variables
load_dotenv('backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Product image mappings - tema -> URL da imagem
PRODUCT_IMAGES = {
    "geek": "https://images.pexels.com/photos/8885012/pexels-photo-8885012.jpeg",
    "terror": "https://images.unsplash.com/photo-1633555690973-b736f84f3c1b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2NDF8MHwxfHNlYXJjaHwxfHxob3Jyb3J8ZW58MHx8fHwxNzUwNjIwNDA5fDA&ixlib=rb-4.1.0&q=85",
    "pets": "https://images.pexels.com/photos/406014/pexels-photo-406014.jpeg",
    "harry_potter": "https://images.pexels.com/photos/28747036/pexels-photo-28747036.jpeg",
    "marvel": "https://images.pexels.com/photos/1181266/pexels-photo-1181266.jpeg",
    "livros": "https://images.unsplash.com/photo-1604866830893-c13cafa515d5?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzl8MHwxfHNlYXJjaHwxfHxib29rc3xlbnwwfHx8fDE3NTA2MTg2MDB8MA&ixlib=rb-4.1.0&q=85",
    "auto_cuidado": "https://images.pexels.com/photos/846975/pexels-photo-846975.jpeg",
    "stitch": "https://images.pexels.com/photos/7658146/pexels-photo-7658146.jpeg"
}

def url_to_base64(image_url):
    """Convert image URL to base64 string"""
    try:
        print(f"Downloading image from: {image_url}")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Open image with PIL and resize if needed
        image = Image.open(io.BytesIO(response.content))
        
        # Resize image to a reasonable size (max 800x600) to reduce base64 size
        max_size = (800, 600)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed (removes alpha channel)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Save to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='JPEG', quality=85, optimize=True)
        img_buffer.seek(0)
        
        # Convert to base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{img_base64}"
        
    except Exception as e:
        print(f"Error converting {image_url} to base64: {e}")
        return None

async def update_products_with_images():
    """Update all products with new base64 images"""
    try:
        # Get all products
        products = await db.products.find({}).to_list(None)
        print(f"Found {len(products)} products to update")
        
        for product in products:
            print(f"\nUpdating product: {product['name']}")
            category = product['category']
            
            # Get the appropriate image URL for this category
            image_url = PRODUCT_IMAGES.get(category)
            if not image_url:
                print(f"No image URL found for category: {category}")
                continue
            
            # Convert URL to base64
            base64_image = url_to_base64(image_url)
            if not base64_image:
                print(f"Failed to convert image for product: {product['name']}")
                continue
            
            # Update product with base64 image
            update_result = await db.products.update_one(
                {"id": product["id"]},
                {
                    "$set": {
                        "image_url": base64_image,  # Store base64 in image_url field
                        "updated_at": "2025-01-22T15:00:00"
                    }
                }
            )
            
            if update_result.modified_count > 0:
                print(f"✅ Updated {product['name']} with new image")
            else:
                print(f"❌ Failed to update {product['name']}")
        
        print(f"\n🎉 Image update process completed!")
        
    except Exception as e:
        print(f"Error updating products: {e}")

async def list_products():
    """List all products and their current images"""
    try:
        products = await db.products.find({}).to_list(None)
        print(f"\nTotal products: {len(products)}")
        
        for product in products:
            print(f"\nProduct: {product['name']}")
            print(f"Category: {product['category']}")
            print(f"Price: €{product['price']}")
            
            current_image = product.get('image_url', 'No image')
            if current_image.startswith('data:image'):
                print(f"Image: Base64 image present ({len(current_image)} chars)")
            elif current_image.startswith('http'):
                print(f"Image: URL - {current_image}")
            else:
                print(f"Image: {current_image}")
        
    except Exception as e:
        print(f"Error listing products: {e}")

async def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        await list_products()
    else:
        await update_products_with_images()
    
    # Close the connection
    client.close()

if __name__ == "__main__":
    # Install required packages if not available
    try:
        import requests
        from PIL import Image
    except ImportError:
        print("Installing required packages...")
        os.system("pip install requests pillow")
        import requests
        from PIL import Image
    
    asyncio.run(main())