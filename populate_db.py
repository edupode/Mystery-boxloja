import asyncio
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'mystery_box_store')

async def populate_database():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("🚀 Iniciando população da base de dados...")
    
    # Clear existing data
    await db.categories.delete_many({})
    await db.products.delete_many({})
    await db.coupons.delete_many({})
    print("✅ Dados existentes limpos")
    
    # Categories
    categories = [
        {
            "id": str(uuid.uuid4()),
            "name": "Mystery Boxes",
            "description": "Caixas mistério com surpresas incríveis",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Gaming",
            "description": "Produtos e acessórios para gamers",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Tech",
            "description": "Tecnologia e gadgets modernos",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Fashion",
            "description": "Moda e acessórios trendy",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.categories.insert_many(categories)
    print(f"✅ {len(categories)} categorias inseridas")
    
    # Products
    products = [
        {
            "id": str(uuid.uuid4()),
            "name": "Mystery Box Gaming Premium",
            "description": "Uma caixa mistério com produtos gaming de alta qualidade. Valor mínimo garantido de 100€!",
            "price": 49.99,
            "category_id": categories[1]["id"],
            "images": [
                "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMUYyOTM3Ii8+CjxyZWN0IHg9IjUwIiB5PSI1MCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiM0QjVTNjMiIHJ4PSIxMCIvPgo8dGV4dCB4PSIyMDAiIHk9IjE2MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE4IiBmaWxsPSIjRkZGRkZGIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5HYW1pbmcgQm94PC90ZXh0Pgo8L3N2Zz4="
            ],
            "is_featured": True,
            "is_active": True,
            "stock": 50,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mystery Box Tech Essentials",
            "description": "Gadgets e acessórios tecnológicos surpreendentes. Perfeito para entusiastas da tecnologia!",
            "price": 39.99,
            "category_id": categories[2]["id"],
            "images": [
                "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMUIyNTM5Ii8+CjxyZWN0IHg9IjUwIiB5PSI1MCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiMzNzQxNTEiIHJ4PSIxMCIvPgo8dGV4dCB4PSIyMDAiIHk9IjE2MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE4IiBmaWxsPSIjRkZGRkZGIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5UZWNoIEJveDwvdGV4dD4KPC9zdmc+"
            ],
            "is_featured": True,
            "is_active": True,
            "stock": 75,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mystery Box Fashion Style",
            "description": "Acessórios de moda únicos e estilosos. Descobre o teu novo look favorito!",
            "price": 29.99,
            "category_id": categories[3]["id"],
            "images": [
                "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjNzMxODQzIi8+CjxyZWN0IHg9IjUwIiB5PSI1MCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiM5MzI1NEQiIHJ4PSIxMCIvPgo8dGV4dCB4PSIyMDAiIHk9IjE2MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE4IiBmaWxsPSIjRkZGRkZGIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5GYXNoaW9uIEJveDwvdGV4dD4KPC9zdmc+"
            ],
            "is_featured": False,
            "is_active": True,
            "stock": 30,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mystery Box Mega Surprise",
            "description": "A nossa mystery box premium com produtos de todas as categorias. Valor garantido de 150€!",
            "price": 79.99,
            "category_id": categories[0]["id"],
            "images": [
                "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjRkY2QjAwIi8+CjxyZWN0IHg9IjUwIiB5PSI1MCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiNGRjg1MDAiIHJ4PSIxMCIvPgo8dGV4dCB4PSIyMDAiIHk9IjE2MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE2IiBmaWxsPSIjRkZGRkZGIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5NZWdhIFN1cnByaXNlPC90ZXh0Pgo8L3N2Zz4="
            ],
            "is_featured": True,
            "is_active": True,
            "stock": 20,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mystery Box Starter",
            "description": "Perfeita para quem está a começar no mundo das mystery boxes. Ótima qualidade-preço!",
            "price": 19.99,
            "category_id": categories[0]["id"],
            "images": [
                "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMDU5NjY5Ii8+CjxyZWN0IHg9IjUwIiB5PSI1MCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiMwNzk5ODUiIHJ4PSIxMCIvPgo8dGV4dCB4PSIyMDAiIHk9IjE2MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE4IiBmaWxsPSIjRkZGRkZGIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5TdGFydGVyIEJveDwvdGV4dD4KPC9zdmc+"
            ],
            "is_featured": False,
            "is_active": True,
            "stock": 100,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mystery Box Collector Edition",
            "description": "Edição limitada para colecionadores. Produtos raros e exclusivos incluídos!",
            "price": 99.99,
            "category_id": categories[0]["id"],
            "images": [
                "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDQwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI0MDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjNzMxODQzIi8+CjxyZWN0IHg9IjUwIiB5PSI1MCIgd2lkdGg9IjMwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiM5MDI1NEEiIHJ4PSIxMCIvPgo8dGV4dCB4PSIyMDAiIHk9IjE1MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjE2IiBmaWxsPSIjRkZGRkZGIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj5Db2xsZWN0b3I8L3RleHQ+Cjx0ZXh0IHg9IjIwMCIgeT0iMTcwIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiNGRkZGRkYiIHRleHQtYW5jaG9yPSJtaWRkbGUiPkVkaXRpb248L3RleHQ+Cjwvc3ZnPg=="
            ],
            "is_featured": True,
            "is_active": True,
            "stock": 15,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.products.insert_many(products)
    print(f"✅ {len(products)} produtos inseridos")
    
    # Coupons
    coupons = [
        {
            "id": str(uuid.uuid4()),
            "code": "WELCOME10",
            "description": "10% de desconto para novos clientes",
            "discount_type": "percentage",
            "discount_value": 10.0,
            "min_order_value": 20.0,
            "max_uses": 1000,
            "current_uses": 0,
            "valid_from": datetime.utcnow(),
            "valid_until": datetime(2025, 12, 31),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "code": "SAVE5",
            "description": "5€ de desconto em qualquer compra",
            "discount_type": "fixed",
            "discount_value": 5.0,
            "min_order_value": 25.0,
            "max_uses": 500,
            "current_uses": 0,
            "valid_from": datetime.utcnow(),
            "valid_until": datetime(2025, 6, 30),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "code": "PREMIUM20",
            "description": "20% de desconto para compras acima de 50€",
            "discount_type": "percentage",
            "discount_value": 20.0,
            "min_order_value": 50.0,
            "max_uses": 200,
            "current_uses": 0,
            "valid_from": datetime.utcnow(),
            "valid_until": datetime(2025, 9, 30),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.coupons.insert_many(coupons)
    print(f"✅ {len(coupons)} cupões inseridos")
    
    print("\n🎉 Base de dados populada com sucesso!")
    print(f"📦 {len(categories)} categorias")
    print(f"🛍️ {len(products)} produtos")
    print(f"🎫 {len(coupons)} cupões")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(populate_database())