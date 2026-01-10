"""
Setup script for the prices collection
Creates indexes and optionally adds sample data
"""
from pymongo import MongoClient
from datetime import datetime
from config import MONGO_URI, DB_NAME

def setup_prices_collection():
    """Setup the prices collection with proper indexes"""
    print("=" * 60)
    print("Setting up prices collection")
    print("=" * 60)
    
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        prices = db.prices
        
        # Create unique index on barcode
        print("\n1. Creating indexes...")
        prices.create_index("barcode", unique=True)
        print("   ✓ Created unique index on 'barcode'")
        
        prices.create_index("last_updated")
        print("   ✓ Created index on 'last_updated'")
        
        # Check if collection already has data
        count = prices.count_documents({})
        print(f"\n2. Collection status: {count} document(s) found")
        
        if count == 0:
            print("\n3. Collection is empty - ready to use!")
            print("\n   Example usage:")
            print("   ```python")
            print("   prices.insert_one({")
            print("       'barcode': '1234567890',")
            print("       'price': 9.99,")
            print("       'currency': 'USD',")
            print("       'last_updated': datetime.utcnow(),")
            print("       'product_name': 'Sample Product'")
            print("   })")
            print("   ```")
        else:
            print("\n3. Collection already contains data")
            sample = prices.find_one()
            print(f"   Sample document keys: {list(sample.keys())}")
        
        client.close()
        print("\n✓ Prices collection setup complete!")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    setup_prices_collection()

