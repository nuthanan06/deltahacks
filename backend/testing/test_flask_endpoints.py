"""
Test script for Flask endpoints
Make sure Flask app is running before executing this script:
    python app.py
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5001"


def print_response(response, success_msg="Success"):
    """Helper to print response details"""
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except (ValueError, json.JSONDecodeError):
        print(f"Response (raw): {response.text}")
    
    if response.status_code in [200, 201]:
        print(f"✓ {success_msg}")
        return True
    else:
        print(f"✗ Failed (Status: {response.status_code})")
        return False


# ============================================================================
# SESSIONS API TESTS
# ============================================================================

def test_create_session():
    """Test POST /api/sessions/ (new version with pairing token)"""
    print("\n" + "=" * 50)
    print("Testing POST /api/sessions/ (Cart Device)")
    print("=" * 50)
    
    # Cart device creates session - no session_id needed
    data = {
        "cart_id": f"test_cart_{int(datetime.now().timestamp())}"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/sessions/",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if print_response(response, "Session created with pairing token!"):
            response_data = response.json()
            # Return tuple: (session_id, pairing_token)
            return (response_data.get("session_id"), response_data.get("pairing_token"))
        return None
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Flask server")
        print("  Make sure Flask app is running: python app.py")
        return None
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_get_session(session_id):
    """Test GET /api/sessions/<session_id>"""
    print("\n" + "=" * 50)
    print(f"Testing GET /api/sessions/{session_id}")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}")
        return print_response(response, "Session retrieved successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_list_sessions():
    """Test GET /api/sessions/"""
    print("\n" + "=" * 50)
    print("Testing GET /api/sessions/")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/")
        return print_response(response, "Sessions listed successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_checkout_session(session_id):
    """Test PUT /api/sessions/<session_id>/checkout"""
    print("\n" + "=" * 50)
    print(f"Testing PUT /api/sessions/{session_id}/checkout")
    print("=" * 50)
    
    try:
        response = requests.put(f"{BASE_URL}/api/sessions/{session_id}/checkout")
        return print_response(response, "Session checked out successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


# ============================================================================
# INVENTORY API TESTS
# ============================================================================

def test_get_inventory(session_id):
    """Test GET /api/inventory/<session_id>"""
    print("\n" + "=" * 50)
    print(f"Testing GET /api/inventory/{session_id}")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/inventory/{session_id}")
        return print_response(response, "Inventory retrieved successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_add_item_to_inventory(session_id):
    """Test POST /api/inventory/<session_id>/items"""
    print("\n" + "=" * 50)
    print(f"Testing POST /api/inventory/{session_id}/items")
    print("=" * 50)
    
    data = {
        "barcode": "1234567890",
        "name": "Test Product",
        "price": 9.99,
        "confidence": 0.85
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/inventory/{session_id}/items",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        return print_response(response, "Item added successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_update_inventory_item(session_id, barcode):
    """Test PUT /api/inventory/<session_id>/items/<barcode>"""
    print("\n" + "=" * 50)
    print(f"Testing PUT /api/inventory/{session_id}/items/{barcode}")
    print("=" * 50)
    
    data = {
        "qty": 2,
        "price": 8.99
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/inventory/{session_id}/items/{barcode}",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        return print_response(response, "Item updated successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_remove_inventory_item(session_id, barcode):
    """Test DELETE /api/inventory/<session_id>/items/<barcode>"""
    print("\n" + "=" * 50)
    print(f"Testing DELETE /api/inventory/{session_id}/items/{barcode}")
    print("=" * 50)
    
    try:
        response = requests.delete(f"{BASE_URL}/api/inventory/{session_id}/items/{barcode}")
        return print_response(response, "Item removed successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


# ============================================================================
# PRICES API TESTS
# ============================================================================

def test_create_price():
    """Test POST /api/prices/"""
    print("\n" + "=" * 50)
    print("Testing POST /api/prices/")
    print("=" * 50)
    
    data = {
        "barcode": "9876543210",
        "price": 12.99,
        "currency": "USD",
        "product_name": "Test Price Product"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/prices/",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        return print_response(response, "Price created successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_get_price(barcode):
    """Test GET /api/prices/<barcode>"""
    print("\n" + "=" * 50)
    print(f"Testing GET /api/prices/{barcode}")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/prices/{barcode}")
        return print_response(response, "Price retrieved successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_list_prices():
    """Test GET /api/prices/"""
    print("\n" + "=" * 50)
    print("Testing GET /api/prices/")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/prices/")
        return print_response(response, "Prices listed successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_update_price(barcode):
    """Test PUT /api/prices/<barcode>"""
    print("\n" + "=" * 50)
    print(f"Testing PUT /api/prices/{barcode}")
    print("=" * 50)
    
    data = {
        "price": 11.99
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/prices/{barcode}",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        return print_response(response, "Price updated successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_delete_price(barcode):
    """Test DELETE /api/prices/<barcode>"""
    print("\n" + "=" * 50)
    print(f"Testing DELETE /api/prices/{barcode}")
    print("=" * 50)
    
    try:
        response = requests.delete(f"{BASE_URL}/api/prices/{barcode}")
        return print_response(response, "Price deleted successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


# ============================================================================
# PAIRING API TESTS
# ============================================================================

def test_generate_pairing_qrcode(session_id):
    """Test GET /api/sessions/<session_id>/qrcode"""
    print("\n" + "=" * 50)
    print(f"Testing GET /api/sessions/{session_id}/qrcode")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}/qrcode?format=base64")
        if print_response(response, "QR code generated successfully!"):
            response_data = response.json()
            # Verify response contains QR code data
            if "qr_code" in response_data and "pairing_token" in response_data:
                print(f"  ✓ QR code contains pairing token: {response_data['pairing_token'][:20]}...")
                return True
            return False
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_pair_phone(pairing_token, phone_id=None):
    """Test POST /api/pair (Phone pairing)"""
    print("\n" + "=" * 50)
    print("Testing POST /api/pair (Phone)")
    print("=" * 50)
    
    data = {
        "pairing_token": pairing_token
    }
    if phone_id:
        data["phone_id"] = phone_id
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pair",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if print_response(response, "Phone paired successfully!"):
            response_data = response.json()
            return response_data.get("session_id")
        return None
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_pairing_status(session_id):
    """Test GET /api/sessions/<session_id>/pairing-status"""
    print("\n" + "=" * 50)
    print(f"Testing GET /api/sessions/{session_id}/pairing-status")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/{session_id}/pairing-status")
        return print_response(response, "Pairing status retrieved successfully!")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_pair_invalid_token():
    """Test POST /api/pair with invalid token"""
    print("\n" + "=" * 50)
    print("Testing POST /api/pair with invalid token")
    print("=" * 50)
    
    data = {
        "pairing_token": "invalid_token_12345"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pair",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 404:
            print(f"✓ Correctly rejected invalid token (Status: {response.status_code})")
            return True
        else:
            print(f"✗ Expected 404, got {response.status_code}")
            print_response(response)
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_pair_missing_token():
    """Test POST /api/pair with missing token"""
    print("\n" + "=" * 50)
    print("Testing POST /api/pair with missing token")
    print("=" * 50)
    
    data = {}
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pair",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 400:
            print(f"✓ Correctly rejected missing token (Status: {response.status_code})")
            return True
        else:
            print(f"✗ Expected 400, got {response.status_code}")
            print_response(response)
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_pair_already_paired(pairing_token):
    """Test POST /api/pair with already paired token"""
    print("\n" + "=" * 50)
    print("Testing POST /api/pair with already paired token")
    print("=" * 50)
    
    data = {
        "pairing_token": pairing_token
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/pair",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 409:
            print(f"✓ Correctly rejected already paired token (Status: {response.status_code})")
            return True
        else:
            print(f"✗ Expected 409, got {response.status_code}")
            print_response(response)
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


# ============================================================================
# HEALTH CHECK TEST
# ============================================================================

def test_health_check():
    """Test connection to Flask server"""
    print("\n" + "=" * 50)
    print("Testing Flask Server Connection")
    print("=" * 50)
    
    try:
        # Try to list sessions as a health check
        response = requests.get(f"{BASE_URL}/api/sessions/", timeout=2)
        if response.status_code in [200, 201]:
            print("✓ Flask server is running and responding")
            return True
        else:
            print(f"⚠ Flask server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Flask server")
        print("  Make sure Flask app is running: python app.py")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all endpoint tests"""
    print("\n" + "=" * 60)
    print("Flask API Test Suite")
    print("=" * 60)
    print("Make sure Flask app is running: python app.py")
    print("(Flask will run on port 5001 to avoid macOS AirPlay conflict)")
    
    # Health check first
    test_health_check()
    
    # Test Pairing Flow (NEW)
    print("\n" + "=" * 60)
    print("PAIRING API TESTS")
    print("=" * 60)
    
    # Step 1: Cart creates session and gets pairing token
    result = test_create_session()
    if not result:
        print("\n✗ Cannot proceed without a valid session")
        return
    
    session_id, pairing_token = result
    print(f"\n  Session ID: {session_id}")
    print(f"  Pairing Token: {pairing_token[:30]}...")
    
    # Step 2: Cart generates QR code
    test_generate_pairing_qrcode(session_id)
    
    # Step 3: Check pairing status (should be unpaired)
    test_pairing_status(session_id)
    
    # Step 4: Test error cases
    test_pair_missing_token()
    test_pair_invalid_token()
    
    # Step 5: Phone pairs with cart
    paired_session_id = test_pair_phone(pairing_token, phone_id="test_phone_123")
    if paired_session_id:
        print(f"  ✓ Phone paired with session: {paired_session_id}")
    
    # Step 6: Check pairing status (should be paired now)
    if paired_session_id:
        test_pairing_status(paired_session_id)
    
    # Step 7: Test double pairing (should fail)
    test_pair_already_paired(pairing_token)
    
    # Test Sessions API
    print("\n" + "=" * 60)
    print("SESSIONS API TESTS")
    print("=" * 60)
    if paired_session_id:
        test_get_session(paired_session_id)
    test_list_sessions()
    
    # Test Inventory API
    print("\n" + "=" * 60)
    print("INVENTORY API TESTS")
    print("=" * 60)
    if paired_session_id:
        test_get_inventory(paired_session_id)
        test_add_item_to_inventory(paired_session_id)
        test_get_inventory(paired_session_id)  # Check updated inventory
        test_update_inventory_item(paired_session_id, "1234567890")
        test_get_inventory(paired_session_id)  # Check updated inventory
    
    # Test Prices API
    print("\n" + "=" * 60)
    print("PRICES API TESTS")
    print("=" * 60)
    test_create_price()
    test_get_price("9876543210")
    test_list_prices()
    test_update_price("9876543210")
    test_get_price("9876543210")  # Verify update
    
    # Test removing item
    print("\n" + "=" * 60)
    print("CLEANUP TESTS")
    print("=" * 60)
    if paired_session_id:
        test_remove_inventory_item(paired_session_id, "1234567890")
        test_get_inventory(paired_session_id)  # Check inventory after removal
        
        # Checkout session
        test_checkout_session(paired_session_id)
        test_get_session(paired_session_id)  # Verify checkout status
    
    # Cleanup prices test data
    test_delete_price("9876543210")
    
    print("\n" + "=" * 60)
    print("All API tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
