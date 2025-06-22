#!/usr/bin/env python3

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables
load_dotenv('backend/.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

async def create_missing_coupons():
    """Create the missing WELCOME10 and SAVE5 coupons"""
    try:
        # Define the coupons to create
        coupons_to_create = [
            {
                "id": str(uuid.uuid4()),
                "code": "WELCOME10",
                "description": "Desconto de boas-vindas de 10%",
                "discount_type": "percentage",
                "discount_value": 10.0,
                "min_order_value": None,
                "max_uses": None,
                "current_uses": 0,
                "valid_from": datetime.utcnow() - timedelta(days=1),
                "valid_until": datetime.utcnow() + timedelta(days=365),
                "applicable_categories": [],
                "applicable_products": [],
                "is_active": True,
                "created_by": "admin",
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "code": "SAVE5",
                "description": "Desconto de 5% para clientes frequentes",
                "discount_type": "percentage", 
                "discount_value": 5.0,
                "min_order_value": 20.0,
                "max_uses": None,
                "current_uses": 0,
                "valid_from": datetime.utcnow() - timedelta(days=1),
                "valid_until": datetime.utcnow() + timedelta(days=365),
                "applicable_categories": [],
                "applicable_products": [],
                "is_active": True,
                "created_by": "admin", 
                "created_at": datetime.utcnow()
            },
            {
                "id": str(uuid.uuid4()),
                "code": "PREMIUM20",
                "description": "Desconto premium de 20%",
                "discount_type": "percentage",
                "discount_value": 20.0,
                "min_order_value": 50.0,
                "max_uses": None,
                "current_uses": 0,
                "valid_from": datetime.utcnow() - timedelta(days=1),
                "valid_until": datetime.utcnow() + timedelta(days=365),
                "applicable_categories": [],
                "applicable_products": [],
                "is_active": True,
                "created_by": "admin",
                "created_at": datetime.utcnow()
            }
        ]
        
        for coupon_data in coupons_to_create:
            # Check if coupon already exists
            existing = await db.coupons.find_one({"code": coupon_data["code"]})
            if existing:
                print(f"Coupon {coupon_data['code']} already exists, updating...")
                await db.coupons.update_one(
                    {"code": coupon_data["code"]},
                    {"$set": {
                        "is_active": True,
                        "valid_from": coupon_data["valid_from"],
                        "valid_until": coupon_data["valid_until"],
                        "current_uses": 0
                    }}
                )
            else:
                print(f"Creating coupon {coupon_data['code']}...")
                await db.coupons.insert_one(coupon_data)
        
        # List all coupons
        coupons = await db.coupons.find({}).to_list(None)
        print(f"\n✅ All coupons ({len(coupons)}):")
        for coupon in coupons:
            print(f"- {coupon['code']}: {coupon['discount_value']}% off")
            print(f"  Description: {coupon['description']}")
            print(f"  Active: {coupon['is_active']}")
            if coupon.get('min_order_value'):
                print(f"  Min order: €{coupon['min_order_value']}")
            print()
        
    except Exception as e:
        print(f"Error creating coupons: {e}")

async def main():
    """Main function"""
    print("🎫 Creating missing coupons...\n")
    
    await create_missing_coupons()
    
    print("🎉 Coupon creation completed!")
    
    # Close the connection
    client.close()

if __name__ == "__main__":
    asyncio.run(main())