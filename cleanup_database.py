#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv('backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

async def clean_test_products():
    """Remove test products and keep only the main mystery boxes"""
    try:
        # List of main product names to keep
        main_products = [
            "Mystery Box Geek 🤓",
            "Mystery Box Terror 👻", 
            "Mystery Box Pets 🐾",
            "Mystery Box Harry Potter ⚡",
            "Mystery Box Marvel 🦸‍♂️",
            "Mystery Box Livros 📚",
            "Mystery Box Auto-cuidado 🧘‍♀️",
            "Mystery Box Stitch 🌺"
        ]
        
        # Delete products that are not in the main list
        result = await db.products.delete_many({
            "name": {"$nin": main_products}
        })
        
        print(f"✅ Removed {result.deleted_count} test products")
        
        # List remaining products
        products = await db.products.find({}).to_list(None)
        print(f"\nRemaining products ({len(products)}):")
        for product in products:
            print(f"- {product['name']} (Category: {product['category']})")
        
    except Exception as e:
        print(f"Error cleaning products: {e}")

async def fix_coupons():
    """Fix coupon codes that are not working"""
    try:
        # List current coupons
        coupons = await db.coupons.find({}).to_list(None)
        print(f"\nCurrent coupons ({len(coupons)}):")
        for coupon in coupons:
            print(f"- {coupon['code']}: {coupon['discount_value']}% off (Active: {coupon['is_active']})")
        
        # Update WELCOME10 and SAVE5 coupons to make sure they are active
        from datetime import datetime, timedelta
        
        # Update WELCOME10
        await db.coupons.update_one(
            {"code": "WELCOME10"},
            {
                "$set": {
                    "is_active": True,
                    "valid_from": datetime.utcnow() - timedelta(days=1),
                    "valid_until": datetime.utcnow() + timedelta(days=365),
                    "current_uses": 0
                }
            }
        )
        
        # Update SAVE5  
        await db.coupons.update_one(
            {"code": "SAVE5"},
            {
                "$set": {
                    "is_active": True,
                    "valid_from": datetime.utcnow() - timedelta(days=1),
                    "valid_until": datetime.utcnow() + timedelta(days=365),
                    "current_uses": 0
                }
            }
        )
        
        print("✅ Updated coupon validity dates and activation status")
        
    except Exception as e:
        print(f"Error fixing coupons: {e}")

async def main():
    """Main cleanup function"""
    print("🧹 Starting cleanup process...\n")
    
    await clean_test_products()
    await fix_coupons()
    
    print("\n🎉 Cleanup completed!")
    
    # Close the connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main())