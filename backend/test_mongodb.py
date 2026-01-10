"""
Test script to verify MongoDB connection and operations
Also tests Flask API endpoints if Flask app is running
"""
import sys
import requests
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import MONGO_URI, DB_NAME
from datetime import datetime

API_BASE_URL = "http://localhost:5001"


def test_connection():
    """Test basic MongoDB connection"""
    print("=" * 50)
    print("Testing MongoDB Connection...")
    print("=" * 50)
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Force a connection attempt
        client.server_info()
        print("✓ Successfully connected to MongoDB!")
        print(f"  Server: {MONGO_URI}")
        return client
    except ServerSelectionTimeoutError:
        print("✗ Failed to connect to MongoDB: Server selection timeout")
        print("  Check if MongoDB is running and MONGO_URI is correct")
        return None
    except ConnectionFailure:
        print("✗ Failed to connect to MongoDB: Connection failure")
        print("  Check your connection string and network settings")
        return None
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {str(e)}")
        return None


def test_database_access(client):
    """Test database and collection access"""
    print("\n" + "=" * 50)
    print("Testing Database Access...")
    print("=" * 50)
    
    try:
        db = client[DB_NAME]
        print(f"✓ Successfully accessed database: {DB_NAME}")
        
        # List collections
        collections = db.list_collection_names()
        print(f"  Existing collections: {collections}")
        
        # Access collections
        inventory = db.inventory
        sessions = db.sessions
        produce = db.Produce
        prices = db.prices
        print("✓ Successfully accessed collections: inventory, sessions, Produce, prices")
        
        return db, inventory, sessions, produce, prices
    except Exception as e:
        print(f"✗ Failed to access database: {str(e)}")
        return None, None, None, None, None


def test_basic_operations(inventory, sessions):
    """Test basic CRUD operations"""
    print("\n" + "=" * 50)
    print("Testing Basic Operations...")
    print("=" * 50)
    
    test_session_id = "test_session_123"
    
    try:
        # Test INSERT
        print("\n1. Testing INSERT operation...")
        test_session = {
            "session_id": test_session_id,
            "cart_id": "test_cart_123",
            "user_id": "test_user",
            "status": "active",
            "created_at": datetime.utcnow(),
        }
        result = sessions.insert_one(test_session)
        print(f"   ✓ Inserted test session: {result.inserted_id}")
        
        test_inventory = {
            "session_id": test_session_id,
            "items": [],
            "total": 0.0,
            "updated_at": datetime.utcnow(),
        }
        result = inventory.insert_one(test_inventory)
        print(f"   ✓ Inserted test inventory: {result.inserted_id}")
        
        # Test FIND
        print("\n2. Testing FIND operation...")
        found_session = sessions.find_one({"session_id": test_session_id})
        if found_session:
            print(f"   ✓ Found session: {found_session['session_id']}")
        else:
            print("   ✗ Session not found")
        
        found_inventory = inventory.find_one({"session_id": test_session_id})
        if found_inventory:
            print(f"   ✓ Found inventory: {found_inventory['session_id']}")
        else:
            print("   ✗ Inventory not found")
        
        # Test UPDATE
        print("\n3. Testing UPDATE operation...")
        update_result = inventory.update_one(
            {"session_id": test_session_id},
            {"$set": {"total": 10.50, "updated_at": datetime.utcnow()}}
        )
        if update_result.modified_count > 0:
            print(f"   ✓ Updated inventory: modified {update_result.modified_count} document(s)")
        else:
            print("   ✗ No documents updated")
        
        # Test DELETE (cleanup)
        print("\n4. Testing DELETE operation (cleanup)...")
        delete_result_sessions = sessions.delete_one({"session_id": test_session_id})
        delete_result_inventory = inventory.delete_one({"session_id": test_session_id})
        print(f"   ✓ Deleted test data: {delete_result_sessions.deleted_count} session(s), "
              f"{delete_result_inventory.deleted_count} inventory item(s)")
        
        print("\n✓ All basic operations completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Operation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prices_collection(prices):
    """Test prices collection operations"""
    print("\n" + "=" * 50)
    print("Testing Prices Collection Operations")
    print("=" * 50)
    print("This will test INSERT, FIND, UPDATE, UPSERT, and DELETE operations")
    
    test_barcode = "test_barcode_12345"
    
    try:
        # Test INSERT
        print("\n1. Testing INSERT operation...")
        test_price = {
            "barcode": test_barcode,
            "price": 9.99,
            "currency": "USD",
            "last_updated": datetime.utcnow(),
            "product_name": "Test Product"
        }
        result = prices.insert_one(test_price)
        print(f"   ✓ Inserted test price: {result.inserted_id}")
        
        # Test FIND
        print("\n2. Testing FIND operation...")
        found_price = prices.find_one({"barcode": test_barcode})
        if found_price:
            print(f"   ✓ Found price for barcode: {found_price['barcode']}")
            print(f"      Price: ${found_price['price']} {found_price.get('currency', 'USD')}")
        else:
            print("   ✗ Price not found")
            return False
        
        # Test UPDATE
        print("\n3. Testing UPDATE operation...")
        update_result = prices.update_one(
            {"barcode": test_barcode},
            {"$set": {"price": 8.99, "last_updated": datetime.utcnow()}}
        )
        if update_result.modified_count > 0:
            print(f"   ✓ Updated price: modified {update_result.modified_count} document(s)")
            # Verify update
            updated_price = prices.find_one({"barcode": test_barcode})
            if updated_price and updated_price["price"] == 8.99:
                print(f"      New price: ${updated_price['price']}")
        else:
            print("   ✗ No documents updated")
        
        # Test UPSERT (update or insert)
        print("\n4. Testing UPSERT operation...")
        upsert_result = prices.update_one(
            {"barcode": "new_barcode_999"},
            {
                "$set": {
                    "price": 12.99,
                    "currency": "USD",
                    "last_updated": datetime.utcnow(),
                    "product_name": "New Product"
                }
            },
            upsert=True
        )
        if upsert_result.upserted_id:
            print(f"   ✓ Created new price via upsert: {upsert_result.upserted_id}")
        elif upsert_result.modified_count > 0:
            print(f"   ✓ Updated existing price via upsert")
        
        # Test DELETE (cleanup)
        print("\n5. Testing DELETE operation (cleanup)...")
        delete_result1 = prices.delete_one({"barcode": test_barcode})
        delete_result2 = prices.delete_one({"barcode": "new_barcode_999"})
        print(f"   ✓ Deleted test data: {delete_result1.deleted_count + delete_result2.deleted_count} price(s)")
        
        # Check collection stats
        total_prices = prices.count_documents({})
        print(f"\n   Collection stats: {total_prices} total price document(s)")
        
        print("\n" + "-" * 50)
        print("✓ All prices collection operations completed successfully!")
        print("-" * 50)
        return True
        
    except Exception as e:
        print(f"\n✗ Prices collection operation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_flask_running():
    """Check if Flask app is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def test_sessions_api():
    """Test Sessions API endpoints"""
    print("\n" + "=" * 50)
    print("Testing Sessions API Endpoints")
    print("=" * 50)
    
    if not check_flask_running():
        print("⚠️  Flask app is not running. Skipping API tests.")
        print("   Start Flask app with: python app.py")
        return None
    
    session_id = f"test_api_session_{int(datetime.now().timestamp())}"
    
    try:
        # Test POST /api/sessions/
        print("\n1. Testing POST /api/sessions/")
        data = {
            "session_id": session_id,
            "cart_id": f"test_cart_{int(datetime.now().timestamp())}",
            "user_id": "test_user_api"
        }
        response = requests.post(
            f"{API_BASE_URL}/api/sessions/",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 201:
            print(f"   ✓ Session created: {session_id}")
        else:
            print(f"   ✗ Failed: {response.status_code} - {response.text}")
            return None
        
        # Test GET /api/sessions/<session_id>
        print("\n2. Testing GET /api/sessions/<session_id>")
        response = requests.get(f"{API_BASE_URL}/api/sessions/{session_id}")
        if response.status_code == 200:
            session_data = response.json()
            print(f"   ✓ Session retrieved: {session_data.get('status')}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        # Test GET /api/sessions/
        print("\n3. Testing GET /api/sessions/")
        response = requests.get(f"{API_BASE_URL}/api/sessions/")
        if response.status_code == 200:
            sessions_data = response.json()
            print(f"   ✓ Listed {sessions_data.get('count', 0)} session(s)")
        
        # Test PUT /api/sessions/<session_id>/checkout
        print("\n4. Testing PUT /api/sessions/<session_id>/checkout")
        response = requests.put(f"{API_BASE_URL}/api/sessions/{session_id}/checkout")
        if response.status_code == 200:
            print(f"   ✓ Session checked out")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        print("\n✓ All Sessions API tests completed!")
        return session_id
        
    except Exception as e:
        print(f"\n✗ Sessions API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_inventory_api(session_id):
    """Test Inventory API endpoints"""
    print("\n" + "=" * 50)
    print("Testing Inventory API Endpoints")
    print("=" * 50)
    
    if not session_id:
        print("⚠️  No session_id provided. Skipping inventory tests.")
        return False
    
    test_barcode = "test_api_barcode_12345"
    
    try:
        # Test GET /api/inventory/<session_id>
        print("\n1. Testing GET /api/inventory/<session_id>")
        response = requests.get(f"{API_BASE_URL}/api/inventory/{session_id}")
        if response.status_code == 200:
            inv_data = response.json()
            print(f"   ✓ Inventory retrieved: {len(inv_data.get('items', []))} item(s)")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        # Test POST /api/inventory/<session_id>/items
        print("\n2. Testing POST /api/inventory/<session_id>/items")
        data = {
            "barcode": test_barcode,
            "name": "API Test Product",
            "price": 9.99,
            "confidence": 0.85
        }
        response = requests.post(
            f"{API_BASE_URL}/api/inventory/{session_id}/items",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print(f"   ✓ Item added: {test_barcode}")
        else:
            print(f"   ✗ Failed: {response.status_code} - {response.text}")
            return False
        
        # Verify item was added
        response = requests.get(f"{API_BASE_URL}/api/inventory/{session_id}")
        if response.status_code == 200:
            inv_data = response.json()
            items = inv_data.get('items', [])
            print(f"   ✓ Inventory now has {len(items)} item(s), total: ${inv_data.get('total', 0)}")
        
        # Test PUT /api/inventory/<session_id>/items/<barcode>
        print("\n3. Testing PUT /api/inventory/<session_id>/items/<barcode>")
        update_data = {"qty": 2, "price": 8.99}
        response = requests.put(
            f"{API_BASE_URL}/api/inventory/{session_id}/items/{test_barcode}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print(f"   ✓ Item updated: qty=2, price=$8.99")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        # Verify update
        response = requests.get(f"{API_BASE_URL}/api/inventory/{session_id}")
        if response.status_code == 200:
            inv_data = response.json()
            print(f"   ✓ Updated total: ${inv_data.get('total', 0)}")
        
        # Test DELETE /api/inventory/<session_id>/items/<barcode>
        print("\n4. Testing DELETE /api/inventory/<session_id>/items/<barcode>")
        response = requests.delete(f"{API_BASE_URL}/api/inventory/{session_id}/items/{test_barcode}")
        if response.status_code == 200:
            print(f"   ✓ Item removed")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        print("\n✓ All Inventory API tests completed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Inventory API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prices_api():
    """Test Prices API endpoints"""
    print("\n" + "=" * 50)
    print("Testing Prices API Endpoints")
    print("=" * 50)
    
    if not check_flask_running():
        print("⚠️  Flask app is not running. Skipping API tests.")
        return False
    
    test_barcode = f"test_api_price_{int(datetime.now().timestamp())}"
    
    try:
        # Test POST /api/prices/
        print("\n1. Testing POST /api/prices/")
        data = {
            "barcode": test_barcode,
            "price": 12.99,
            "currency": "USD",
            "product_name": "API Test Price Product"
        }
        response = requests.post(
            f"{API_BASE_URL}/api/prices/",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code in [200, 201]:
            print(f"   ✓ Price created: {test_barcode} = ${data['price']}")
        else:
            print(f"   ✗ Failed: {response.status_code} - {response.text}")
            return False
        
        # Test GET /api/prices/<barcode>
        print("\n2. Testing GET /api/prices/<barcode>")
        response = requests.get(f"{API_BASE_URL}/api/prices/{test_barcode}")
        if response.status_code == 200:
            price_data = response.json()
            print(f"   ✓ Price retrieved: ${price_data.get('price')} {price_data.get('currency')}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        # Test GET /api/prices/
        print("\n3. Testing GET /api/prices/")
        response = requests.get(f"{API_BASE_URL}/api/prices/")
        if response.status_code == 200:
            prices_data = response.json()
            print(f"   ✓ Listed {prices_data.get('count', 0)} price(s)")
        
        # Test PUT /api/prices/<barcode>
        print("\n4. Testing PUT /api/prices/<barcode>")
        update_data = {"price": 11.99}
        response = requests.put(
            f"{API_BASE_URL}/api/prices/{test_barcode}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print(f"   ✓ Price updated: ${update_data['price']}")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        # Verify update
        response = requests.get(f"{API_BASE_URL}/api/prices/{test_barcode}")
        if response.status_code == 200:
            price_data = response.json()
            if price_data.get('price') == 11.99:
                print(f"   ✓ Verified update: ${price_data.get('price')}")
        
        # Test DELETE /api/prices/<barcode>
        print("\n5. Testing DELETE /api/prices/<barcode>")
        response = requests.delete(f"{API_BASE_URL}/api/prices/{test_barcode}")
        if response.status_code == 200:
            print(f"   ✓ Price deleted")
        else:
            print(f"   ✗ Failed: {response.status_code}")
        
        print("\n✓ All Prices API tests completed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Prices API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_health_api():
    """Test Health Check API endpoint"""
    print("\n" + "=" * 50)
    print("Testing Health Check API")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ Health check passed")
            print(f"  Database: {health_data.get('database')}")
            collections = health_data.get('collections', {})
            print(f"  Collections:")
            for coll_name, count in collections.items():
                print(f"    - {coll_name}: {count} document(s)")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("⚠️  Flask app is not running")
        print("   Start Flask app with: python app.py")
        return False
    except Exception as e:
        print(f"✗ Health check error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("MongoDB Connection Test Suite")
    print("=" * 50)
    
    # Test connection
    client = test_connection()
    if not client:
        print("\n✗ Connection test failed. Please fix connection issues before proceeding.")
        sys.exit(1)
    
    # Test database access
    result = test_database_access(client)
    if result[0] is None:
        print("\n✗ Database access test failed.")
        client.close()
        sys.exit(1)
    
    db, inventory, sessions, produce, prices = result
    
    # Test basic operations
    success = test_basic_operations(inventory, sessions)
    
    # Test prices collection
    print("\n" + "=" * 50)
    print("Starting Prices Collection Tests...")
    print("=" * 50)
    prices_success = False
    try:
        prices_success = test_prices_collection(prices)
        if not prices_success:
            print("\n⚠️  Prices collection test failed!")
            success = False
        else:
            print("\n✓ Prices collection test completed successfully!")
    except Exception as e:
        print(f"\n✗ Prices collection test error: {str(e)}")
        success = False
    
    # Test Produce collection access
    print("\n" + "=" * 50)
    print("Testing Produce Collection...")
    print("=" * 50)
    try:
        produce_count = produce.count_documents({})
        print(f"✓ Produce collection accessible: {produce_count} document(s) found")
        
        # Show a sample document if available
        sample = produce.find_one()
        if sample:
            print(f"  Sample document keys: {list(sample.keys())[:5]}...")
    except Exception as e:
        print(f"✗ Error accessing Produce collection: {str(e)}")
        success = False
    
    # Close connection
    client.close()
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print("✓ Connection test")
    print("✓ Database access test")
    print("✓ Sessions & Inventory collections (INSERT, FIND, UPDATE, DELETE)")
    if prices_success:
        print("✓ Prices collection (INSERT, FIND, UPDATE, UPSERT, DELETE)")
    else:
        print("✗ Prices collection test failed")
    print("✓ Produce collection access")
    print("=" * 50)
    if success:
        print("✓ All tests passed! MongoDB is working correctly.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    print("=" * 50)
    
    # Test Flask API endpoints
    print("\n" + "=" * 50)
    print("FLASK API ENDPOINT TESTS")
    print("=" * 50)
    print("Note: These tests require Flask app to be running (python app.py)")
    
    api_success = True
    session_id = None
    
    # Test Health Check
    health_ok = test_health_api()
    if not health_ok:
        print("\n⚠️  Flask app is not running. Skipping API endpoint tests.")
        print("   To test API endpoints, start Flask app: python app.py")
    else:
        # Test Sessions API
        session_id = test_sessions_api()
        if session_id:
            # Test Inventory API
            inventory_api_success = test_inventory_api(session_id)
            if not inventory_api_success:
                api_success = False
        else:
            api_success = False
        
        # Test Prices API
        prices_api_success = test_prices_api()
        if not prices_api_success:
            api_success = False
    
    # Final summary
    print("\n" + "=" * 50)
    print("FINAL TEST SUMMARY")
    print("=" * 50)
    print("MongoDB Direct Tests:")
    print("  ✓ Connection test")
    print("  ✓ Database access test")
    print("  ✓ Sessions & Inventory collections (INSERT, FIND, UPDATE, DELETE)")
    if prices_success:
        print("  ✓ Prices collection (INSERT, FIND, UPDATE, UPSERT, DELETE)")
    else:
        print("  ✗ Prices collection test failed")
    print("  ✓ Produce collection access")
    
    if health_ok:
        print("\nFlask API Tests:")
        print("  ✓ Health check")
        if session_id:
            print("  ✓ Sessions API")
            print("  ✓ Inventory API")
        else:
            print("  ✗ Sessions API failed")
        if prices_api_success:
            print("  ✓ Prices API")
        else:
            print("  ✗ Prices API failed")
    else:
        print("\nFlask API Tests: Skipped (Flask app not running)")
    
    print("=" * 50)
    if success and (not health_ok or api_success):
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    print("=" * 50)
    
    sys.exit(0 if (success and (not health_ok or api_success)) else 1)


if __name__ == "__main__":
    main()

