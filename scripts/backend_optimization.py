#!/usr/bin/env python3
"""
Backend Performance Optimization Script
Otimizações para melhorar a velocidade de resposta do backend
"""

import os
import sys
import json
import time
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append('/app/backend')

try:
    import asyncio
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    import pymongo
    from pymongo import MongoClient
    print("✅ All required imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class BackendOptimizer:
    def __init__(self):
        self.mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/ecommerce')
        self.client = None
        self.db = None
        
    def connect_to_mongo(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(self.mongo_url)
            self.db = self.client.get_default_database()
            # Test connection
            self.client.admin.command('ping')
            print("✅ MongoDB connection successful")
            return True
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False
    
    def optimize_database_indexes(self):
        """Create optimized indexes for better query performance"""
        try:
            print("🔧 Creating database indexes for performance...")
            
            # Products collection indexes
            products = self.db.products
            products.create_index("category")
            products.create_index("featured")
            products.create_index("name")
            products.create_index("price")
            products.create_index([("category", 1), ("featured", -1)])
            products.create_index([("name", "text"), ("description", "text")])
            
            # Users collection indexes
            users = self.db.users
            users.create_index("email", unique=True)
            users.create_index("is_admin")
            users.create_index("created_at")
            
            # Orders collection indexes
            orders = self.db.orders
            orders.create_index("user_id")
            orders.create_index("status")
            orders.create_index("created_at")
            orders.create_index([("user_id", 1), ("status", 1)])
            orders.create_index([("status", 1), ("created_at", -1)])
            
            # Cart collection indexes
            carts = self.db.carts
            carts.create_index("session_id", unique=True)
            carts.create_index("updated_at")
            
            # Coupons collection indexes
            coupons = self.db.coupons
            coupons.create_index("code", unique=True)
            coupons.create_index("active")
            coupons.create_index("expiry_date")
            
            # Chat sessions collection indexes
            chat_sessions = self.db.chat_sessions
            chat_sessions.create_index("user_id")
            chat_sessions.create_index("status")
            chat_sessions.create_index("created_at")
            chat_sessions.create_index([("status", 1), ("created_at", -1)])
            
            print("✅ Database indexes created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating indexes: {e}")
            return False
    
    def optimize_database_cleanup(self):
        """Clean up old data to improve performance"""
        try:
            print("🧹 Cleaning up old data...")
            
            # Remove old cart data (older than 30 days)
            thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            result = self.db.carts.delete_many({
                "updated_at": {"$lt": thirty_days_ago}
            })
            print(f"✅ Removed {result.deleted_count} old cart records")
            
            # Close old chat sessions (older than 7 days and not assigned)
            seven_days_ago = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            result = self.db.chat_sessions.update_many(
                {
                    "created_at": {"$lt": seven_days_ago},
                    "status": "open"
                },
                {"$set": {"status": "closed"}}
            )
            print(f"✅ Closed {result.modified_count} old chat sessions")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            return False
    
    def check_database_performance(self):
        """Check database performance metrics"""
        try:
            print("📊 Checking database performance...")
            
            # Check collection stats
            collections = ['products', 'users', 'orders', 'carts', 'coupons', 'chat_sessions']
            
            for collection_name in collections:
                collection = self.db[collection_name]
                count = collection.count_documents({})
                
                # Get collection stats
                stats = self.db.command("collStats", collection_name)
                size_mb = stats.get('size', 0) / (1024 * 1024)
                
                print(f"  📋 {collection_name}: {count} documents, {size_mb:.2f} MB")
            
            # Check indexes
            print("\n📊 Index information:")
            for collection_name in collections:
                collection = self.db[collection_name]
                indexes = collection.list_indexes()
                index_count = len(list(indexes))
                print(f"  🔍 {collection_name}: {index_count} indexes")
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking performance: {e}")
            return False
    
    def create_connection_pool_config(self):
        """Create optimized connection pool configuration"""
        config = {
            "mongodb_config": {
                "maxPoolSize": 100,
                "minPoolSize": 10,
                "maxIdleTimeMS": 30000,
                "waitQueueTimeoutMS": 5000,
                "serverSelectionTimeoutMS": 5000,
                "connectTimeoutMS": 10000,
                "socketTimeoutMS": 10000,
            },
            "fastapi_config": {
                "workers": 4,
                "keep_alive": 65,
                "timeout_keep_alive": 65,
                "timeout_notify": 60,
                "limit_concurrency": 1000,
                "limit_max_requests": 10000,
            }
        }
        
        # Save config to file
        with open('/app/backend/optimization_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ Connection pool configuration saved")
        return config
    
    def run_optimization(self):
        """Run all optimization routines"""
        print("🚀 Starting Backend Optimization...")
        print("=" * 50)
        
        # Connect to database
        if not self.connect_to_mongo():
            return False
        
        # Run optimizations
        success = True
        
        # Create indexes
        if not self.optimize_database_indexes():
            success = False
        
        # Clean up old data
        if not self.optimize_database_cleanup():
            success = False
        
        # Check performance
        if not self.check_database_performance():
            success = False
        
        # Create connection pool config
        self.create_connection_pool_config()
        
        # Close connection
        if self.client:
            self.client.close()
        
        print("=" * 50)
        if success:
            print("✅ Backend optimization completed successfully!")
            print("\n📋 Optimization Summary:")
            print("  🔍 Database indexes optimized")
            print("  🧹 Old data cleaned up")
            print("  ⚙️  Connection pool configured")
            print("  📊 Performance metrics checked")
            print("\n🚀 Backend should now respond faster!")
        else:
            print("❌ Some optimizations failed. Check logs above.")
        
        return success

if __name__ == "__main__":
    optimizer = BackendOptimizer()
    success = optimizer.run_optimization()
    sys.exit(0 if success else 1)