from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URI, DB_NAME, CONFIDENCE_THRESHOLD, FLASK_DEBUG
import qrcode
import io
import base64
import secrets
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
inventory = db.inventory
sessions = db.sessions
prices = db.prices  # Product price catalog


def now():
    return datetime.utcnow()


# ============================================================================
# PAIRING TOKEN UTILITIES
# ============================================================================

PAIRING_TOKEN_EXPIRY_MINUTES = 10  # Tokens expire after 10 minutes

def generate_pairing_token():
    """Generate a secure, short-lived pairing token"""
    return secrets.token_urlsafe(16)  # 16 bytes = 22 character URL-safe token

def is_token_valid(token, expires_at):
    """Check if a pairing token is still valid"""
    if not expires_at:
        return False
    return datetime.utcnow() < expires_at

def cleanup_expired_sessions():
    """Clean up sessions with expired tokens that were never paired"""
    expired_cutoff = now() - timedelta(minutes=PAIRING_TOKEN_EXPIRY_MINUTES)
    sessions.update_many(
        {
            "status": "active",
            "paired_at": {"$exists": False},
            "token_expires_at": {"$lt": now()}
        },
        {"$set": {"status": "expired"}}
    )


# ============================================================================
# SESSIONS API
# ============================================================================

@app.route("/api/sessions/", methods=["POST"])
def create_session():
    """Create a new shopping session and return pairing token for cart device"""
    data = request.json or {}
    cart_id = data.get("cart_id")
    
    # Generate session ID if not provided
    if not cart_id:
        cart_id = f"cart_{uuid.uuid4().hex[:12]}"
    
    # Generate unique session ID
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    
    # Generate pairing token
    pairing_token = generate_pairing_token()
    token_expires_at = now() + timedelta(minutes=PAIRING_TOKEN_EXPIRY_MINUTES)
    
    # Create session
    session_doc = {
        "session_id": session_id,
        "cart_id": cart_id,
        "pairing_token": pairing_token,
        "token_expires_at": token_expires_at,
        "status": "active",
        "created_at": now(),
        # Phone pairing fields (set when paired)
        "phone_id": None,
        "paired_at": None,
    }
    sessions.insert_one(session_doc)
    
    # Create corresponding inventory
    inventory.insert_one({
        "session_id": session_id,
        "items": [],
        "total": 0.0,
        "updated_at": now(),
    })
    
    return jsonify({
        "status": "created",
        "session_id": session_id,
        "pairing_token": pairing_token,
        "token_expires_at": token_expires_at.isoformat(),
        "cart_id": cart_id
    }), 201


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    """Get a session by ID"""
    session = sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session), 200


@app.route("/api/sessions/", methods=["GET"])
def list_sessions():
    """List all sessions (with optional filters)"""
    status = request.args.get("status")
    user_id = request.args.get("user_id")
    
    query = {}
    if status:
        query["status"] = status
    if user_id:
        query["user_id"] = user_id
    
    session_list = list(sessions.find(query, {"_id": 0}).limit(100))
    return jsonify({"sessions": session_list, "count": len(session_list)}), 200


@app.route("/api/sessions/<session_id>/checkout", methods=["PUT"])
def checkout_session(session_id):
    """Checkout a session (mark as completed)"""
    result = sessions.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed", "completed_at": now()}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({"status": "checked_out", "session_id": session_id}), 200


# ============================================================================
# PAIRING API
# ============================================================================

@app.route("/api/pair", methods=["POST"])
def pair_phone():
    """Pair a phone with a cart session using pairing token"""
    data = request.json
    pairing_token = data.get("pairing_token")
    phone_id = data.get("phone_id")  # Optional: identifier for the phone
    
    if not pairing_token:
        return jsonify({"error": "pairing_token is required"}), 400
    
    # Find session with this token
    session = sessions.find_one({"pairing_token": pairing_token})
    
    if not session:
        return jsonify({"error": "Invalid pairing token"}), 404
    
    # Check if token is expired
    if not is_token_valid(pairing_token, session.get("token_expires_at")):
        return jsonify({"error": "Pairing token has expired"}), 410
    
    # Check if already paired
    if session.get("paired_at"):
        return jsonify({"error": "Session already paired"}), 409
    
    # Pair the phone to the session
    sessions.update_one(
        {"session_id": session["session_id"]},
        {
            "$set": {
                "phone_id": phone_id or f"phone_{uuid.uuid4().hex[:12]}",
                "paired_at": now()
            }
        }
    )
    
    return jsonify({
        "status": "paired",
        "session_id": session["session_id"],
        "cart_id": session.get("cart_id")
    }), 200


@app.route("/api/sessions/<session_id>/pairing-status", methods=["GET"])
def get_pairing_status(session_id):
    """Get pairing status for a session (for cart device to check)"""
    session = sessions.find_one({"session_id": session_id}, {"_id": 0})
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    is_paired = session.get("paired_at") is not None
    token_valid = is_token_valid(session.get("pairing_token"), session.get("token_expires_at"))
    
    return jsonify({
        "session_id": session_id,
        "is_paired": is_paired,
        "token_valid": token_valid,
        "paired_at": session.get("paired_at").isoformat() if session.get("paired_at") else None,
        "phone_id": session.get("phone_id")
    }), 200


# ============================================================================
# INVENTORY API
# ============================================================================

@app.route("/api/inventory/<session_id>", methods=["GET"])
def get_inventory(session_id):
    """Get inventory for a session"""
    inv = inventory.find_one({"session_id": session_id}, {"_id": 0})
    if not inv:
        return jsonify({"error": "Inventory not found"}), 404
    return jsonify(inv), 200


@app.route("/api/inventory/<session_id>/items", methods=["POST"])
def add_item_to_inventory(session_id):
    """Add an item to inventory"""
    data = request.json
    
    if data.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
        return jsonify({"status": "needs_confirmation"}), 200
    
    barcode = data.get("barcode")
    if not barcode:
        return jsonify({"error": "barcode is required"}), 400
    
    # Lookup price if not provided
    item_price = data.get("price")
    if not item_price:
        price_doc = prices.find_one({"barcode": barcode})
        if price_doc:
            item_price = price_doc.get("price", 0.0)
        else:
            item_price = 0.0
    
    # Try to increment quantity if item exists
    result = inventory.update_one(
        {"session_id": session_id, "items.barcode": barcode},
        {
            "$inc": {"items.$.qty": 1},
            "$set": {"updated_at": now()}
        }
    )
    
    # If item doesn't exist, add it
    if result.matched_count == 0:
        inventory.update_one(
            {"session_id": session_id},
            {
                "$push": {
                    "items": {
                        "barcode": barcode,
                        "name": data.get("name"),
                        "qty": 1,
                        "price": item_price,
                    }
                },
                "$set": {"updated_at": now()}
            }
        )
    
    # Recalculate total
    inv = inventory.find_one({"session_id": session_id})
    if inv:
        total = sum(item.get("price", 0) * item.get("qty", 0) for item in inv.get("items", []))
        inventory.update_one(
            {"session_id": session_id},
            {"$set": {"total": total, "updated_at": now()}}
        )
    
    return jsonify({"status": "added", "session_id": session_id}), 200


@app.route("/api/inventory/<session_id>/items/<barcode>", methods=["PUT"])
def update_inventory_item(session_id, barcode):
    """Update an item in inventory (quantity, price, etc.)"""
    data = request.json
    
    update_fields = {}
    if "qty" in data:
        update_fields["items.$.qty"] = data["qty"]
    if "price" in data:
        update_fields["items.$.price"] = data["price"]
    if "name" in data:
        update_fields["items.$.name"] = data["name"]
    
    if not update_fields:
        return jsonify({"error": "No fields to update"}), 400
    
    update_fields["updated_at"] = now()
    
    result = inventory.update_one(
        {"session_id": session_id, "items.barcode": barcode},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Item not found"}), 404
    
    # Recalculate total
    inv = inventory.find_one({"session_id": session_id})
    if inv:
        total = sum(item.get("price", 0) * item.get("qty", 0) for item in inv.get("items", []))
        inventory.update_one(
            {"session_id": session_id},
            {"$set": {"total": total, "updated_at": now()}}
        )
    
    return jsonify({"status": "updated", "session_id": session_id, "barcode": barcode}), 200


@app.route("/api/inventory/<session_id>/items/<barcode>", methods=["DELETE"])
def remove_inventory_item(session_id, barcode):
    """Remove an item from inventory"""
    result = inventory.update_one(
        {"session_id": session_id},
        {
            "$pull": {"items": {"barcode": barcode}},
            "$set": {"updated_at": now()}
        }
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Inventory not found"}), 404
    
    # Recalculate total
    inv = inventory.find_one({"session_id": session_id})
    if inv:
        total = sum(item.get("price", 0) * item.get("qty", 0) for item in inv.get("items", []))
        inventory.update_one(
            {"session_id": session_id},
            {"$set": {"total": total, "updated_at": now()}}
        )
    
    return jsonify({"status": "removed", "session_id": session_id, "barcode": barcode}), 200


# ============================================================================
# PRICES API
# ============================================================================

@app.route("/api/prices/", methods=["GET"])
def list_prices():
    """List all prices (with optional filters)"""
    barcode = request.args.get("barcode")
    limit = int(request.args.get("limit", 100))
    
    query = {}
    if barcode:
        query["barcode"] = barcode
    
    price_list = list(prices.find(query, {"_id": 0}).limit(limit))
    return jsonify({"prices": price_list, "count": len(price_list)}), 200


@app.route("/api/prices/<barcode>", methods=["GET"])
def get_price(barcode):
    """Get price by barcode"""
    price_doc = prices.find_one({"barcode": barcode}, {"_id": 0})
    if not price_doc:
        return jsonify({"error": "Price not found"}), 404
    return jsonify(price_doc), 200


@app.route("/api/prices/", methods=["POST"])
def create_price():
    """Create or update a price"""
    data = request.json
    barcode = data.get("barcode")
    
    if not barcode:
        return jsonify({"error": "barcode is required"}), 400
    if "price" not in data:
        return jsonify({"error": "price is required"}), 400
    
    price_doc = {
        "barcode": barcode,
        "price": float(data["price"]),
        "currency": data.get("currency", "USD"),
        "last_updated": now(),
        "product_name": data.get("product_name", "")
    }
    
    result = prices.update_one(
        {"barcode": barcode},
        {"$set": price_doc},
        upsert=True
    )
    
    if result.upserted_id:
        return jsonify({"status": "created", "barcode": barcode}), 201
    else:
        return jsonify({"status": "updated", "barcode": barcode}), 200


@app.route("/api/prices/<barcode>", methods=["PUT"])
def update_price(barcode):
    """Update a price"""
    data = request.json
    
    update_fields = {"last_updated": now()}
    if "price" in data:
        update_fields["price"] = float(data["price"])
    if "currency" in data:
        update_fields["currency"] = data["currency"]
    if "product_name" in data:
        update_fields["product_name"] = data["product_name"]
    
    result = prices.update_one(
        {"barcode": barcode},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Price not found"}), 404
    
    return jsonify({"status": "updated", "barcode": barcode}), 200


@app.route("/api/prices/<barcode>", methods=["DELETE"])
def delete_price(barcode):
    """Delete a price"""
    result = prices.delete_one({"barcode": barcode})
    
    if result.deleted_count == 0:
        return jsonify({"error": "Price not found"}), 404
    
    return jsonify({"status": "deleted", "barcode": barcode}), 200


# ============================================================================
# QR CODE API
# ============================================================================


@app.route("/api/sessions/<session_id>/qrcode", methods=["GET"])
def generate_pairing_qrcode(session_id):
    """Generate a QR code with pairing token for a session"""
    session = sessions.find_one({"session_id": session_id})
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    pairing_token = session.get("pairing_token")
    if not pairing_token:
        return jsonify({"error": "Session has no pairing token"}), 400
    
    # Check if already paired
    if session.get("paired_at"):
        return jsonify({"error": "Session already paired"}), 409
    
    # Check if token expired
    if not is_token_valid(pairing_token, session.get("token_expires_at")):
        return jsonify({"error": "Pairing token has expired"}), 410
    
    # Get optional parameters
    size = int(request.args.get("size", 10))
    border = int(request.args.get("border", 4))
    format_type = request.args.get("format", "base64")  # Default to base64 for API
    
    # Create QR code with pairing token
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(pairing_token)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes buffer
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    
    # Return based on format
    if format_type == "base64":
        # Return as base64 encoded string in JSON
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
        return jsonify({
            "session_id": session_id,
            "pairing_token": pairing_token,
            "token_expires_at": session.get("token_expires_at").isoformat(),
            "qr_code": f"data:image/png;base64,{img_base64}"
        }), 200
    else:
        # Return as image file
        img_buffer.seek(0)
        return send_file(img_buffer, mimetype="image/png"), 200


if __name__ == "__main__":
    app.run(debug=FLASK_DEBUG, port=5001)
