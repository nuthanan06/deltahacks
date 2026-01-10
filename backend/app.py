from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URI, DB_NAME, CONFIDENCE_THRESHOLD, FLASK_DEBUG
import qrcode
import io
import base64
import uuid
from webcam import CartTrackerWebcam 
from firebase import FirebaseCartManager


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
sessions = db.sessions
prices = db.prices  # Product price catalog


def now():
    return datetime.utcnow()


# ============================================================================
# SESSION UTILITIES
# ============================================================================

def cleanup_expired_sessions():
    """Clean up old sessions (optional cleanup function)"""
    # Clean up active sessions older than 24 hours
    expired_cutoff = now() - timedelta(hours=24)
    sessions.update_many(
        {
            "status": "active"
        },
        {"$set": {"status": "expired"}}
    )


# ============================================================================
# SESSIONS API
# ============================================================================

@app.route("/api/sessions/", methods=["POST"])
def create_session():
    """Create a new shopping session"""
    # Generate unique session ID
    session_id = f"session_{uuid.uuid4().hex[:12]}"

    FirebaseCartManager().create_cart(session_id)
    
    # Create session - only session_id and status
    session_doc = {
        "session_id": session_id,
        "status": "active",
    }
    sessions.insert_one(session_doc)
    
    return jsonify({
        "status": "created",
        "session_id": session_id,
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
    
    query = {}
    if status:
        query["status"] = status
    
    session_list = list(sessions.find(query, {"_id": 0}).limit(100))
    return jsonify({"sessions": session_list, "count": len(session_list)}), 200


@app.route("/api/carts/<cart_id>/session", methods=["GET"])
def get_current_session_for_cart(cart_id):
    """Return the most recent active session for a given cart_id"""
    session = sessions.find_one(
        {"cart_id": cart_id, "status": "active"},
        sort=[("created_at", -1)]  # latest active session
    )

    if not session:
        return jsonify({"error": "No active session for this cart"}), 404

    session.pop("_id", None)
    return jsonify(session), 200


@app.route("/api/sessions/<session_id>/checkout", methods=["PUT"])
def checkout_session(session_id):
    """Checkout a session (mark as completed)"""
    result = sessions.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed"}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({"status": "checked_out", "session_id": session_id}), 200


# ============================================================================
# PAIRING API
# ============================================================================

@app.route("/api/pair", methods=["POST"])
def pair_phone():
    """Pair a phone with a cart session using session_id"""
    data = request.json
    session_id = data.get("session_id")
    
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    
    # Find session with this session_id
    session = sessions.find_one({"session_id": session_id})
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    # Session exists, pairing successful (no data to store)
    return jsonify({
        "status": "paired",
        "session_id": session_id,
    }), 200


@app.route("/api/sessions/<session_id>/pairing-status", methods=["GET"])
def get_pairing_status(session_id):
    """Get pairing status for a session (for cart device to check)"""
    session = sessions.find_one({"session_id": session_id}, {"_id": 0})
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "session_id": session_id,
        "status": session.get("status"),
    }), 200


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
    """Generate a QR code with session_id for a session"""
    session = sessions.find_one({"session_id": session_id})
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    # Get optional parameters
    size = int(request.args.get("size", 10))
    border = int(request.args.get("border", 4))
    format_type = request.args.get("format", "base64")  # Default to base64 for API
    
    # Create QR code with session_id
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(session_id)
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
            "qr_code": f"data:image/png;base64,{img_base64}"
        }), 200
    else:
        # Return as image file
        img_buffer.seek(0)
        return send_file(img_buffer, mimetype="image/png"), 200

# ============================================================================
# CART ITEMS API
# ============================================================================

@app.route("/api/carts/<session_id>/items", methods=["GET"])
def get_cart_items(session_id):
    """Get all items in a cart by session_id"""
    try:
        manager = FirebaseCartManager()
        items = manager.get_cart_items(session_id)
        return jsonify({
            "status": "success",
            "session_id": session_id,
            "items": items,
            "count": len(items)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# RUN WEBCAM API 
# ============================================================================
@app.route("/api/webcam/<session_id>", methods=["GET"])
def run_webcam(session_id):
    """Run the webcam object detection for a given session"""

    detector = CartTrackerWebcam(sessionId=session_id)
    detector.run()

    return jsonify({"status": "webcam started", "session_id": session_id}), 200



if __name__ == "__main__":
    # Use host='0.0.0.0' to allow connections from other devices on the network
    # This is necessary when testing on physical devices
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=5001)
