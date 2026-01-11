from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
from config import MONGO_URI, DB_NAME, CONFIDENCE_THRESHOLD, FLASK_DEBUG
import qrcode
import io
import base64
import uuid
import threading
import numpy as np
import cv2
from webcam import CartTrackerWebcam 
from firebase import FirebaseCartManager
import certifi
import stripe
import os


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_YOUR_SECRET_KEY')

# Track active webcam threads by session_id
active_webcams = {}

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client[DB_NAME]
sessions = db.sessions
prices = db.prices  # Product price catalog


def now():
    return datetime.utcnow()


# ============================================================================
# WEBCAM UTILITIES
# ============================================================================

def start_webcam_for_session(session_id, use_phone_camera=True):
    """Start the webcam detector in a background thread
    
    Args:
        session_id: The session ID to track
        use_phone_camera: If True, use phone camera mode (receive frames via API). 
                         If False, use local webcam.
    """
    # Check if webcam already exists for this session
    if session_id in active_webcams:
        print(f"Webcam already exists for session: {session_id}, skipping start")
        return
    
    # Create detector BEFORE starting thread to avoid race condition
    # This ensures frames can be received immediately
    try:
        print(f"Creating webcam detector for session: {session_id} (phone_camera={use_phone_camera})")
        detector = CartTrackerWebcam(sessionId=session_id, use_phone_camera=use_phone_camera)
        # Store the detector instance immediately so frames can be received
        active_webcams[session_id] = detector
        print(f"✓ Webcam detector created and added to active_webcams for session: {session_id}")
        print(f"✓ Active webcams now: {list(active_webcams.keys())}")
        print(f"✓ Detector use_phone_camera: {detector.use_phone_camera}")
        print(f"✓ Detector frame_queue exists: {detector.frame_queue is not None}")
    except Exception as e:
        print(f"✗ ERROR: Failed to create webcam detector for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        # Don't return silently - raise the exception so caller knows it failed
        raise
    
    def detector_thread():
        try:
            print(f"Starting detection loop for session: {session_id}")
            detector.run()
        except Exception as e:
            print(f"ERROR: Webcam detection loop failed for session {session_id}: {e}")
            import traceback
            traceback.print_exc()
            # Don't restart on error - just clean up and exit
        finally:
            # Clean up from active list when done
            if session_id in active_webcams:
                del active_webcams[session_id]
                print(f"Cleaned up webcam for session: {session_id}")
            # Delete the cart from Firebase and mark session as completed
            try:
                FirebaseCartManager().delete_cart(session_id)
                print(f"Deleted Firebase cart for failed/stopped session: {session_id}")
                # Mark session as completed so it won't restart
                sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": "completed", "paired": False}}
                )
                print(f"Marked session as completed: {session_id}")
            except Exception as cleanup_error:
                print(f"Error cleaning up Firebase cart: {cleanup_error}")
    
    # Run webcam in background thread so API responds immediately
    thread = threading.Thread(target=detector_thread, daemon=True)
    thread.start()
    print(f"Webcam thread started for session: {session_id}")


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
        "device_type": "cart",  # This session was created by a cart
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
    """Checkout a session (mark as completed and clean up Firebase)"""
    print(f"\n=== CHECKOUT REQUEST for session: {session_id} ===")
    
    # Delete the cart from Firebase - this signals the webcam to stop
    # The webcam checks every 30 frames if the session exists, and stops if not
    delete_success = False
    try:
        firebase_manager = FirebaseCartManager()
        delete_success = firebase_manager.delete_cart(session_id)
        print(f"✓ Deleted Firebase cart for session: {session_id} (success={delete_success})")
    except Exception as e:
        print(f"✗ Error deleting Firebase cart: {e}")
        import traceback
        traceback.print_exc()
    
    # Mark session as completed in MongoDB
    try:
        result = sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "completed"}}
        )
        print(f"✓ Updated MongoDB session status: matched={result.matched_count}, modified={result.modified_count}")
        
        if result.matched_count == 0:
            print(f"✗ Session not found in MongoDB: {session_id}")
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        print(f"✗ Error updating MongoDB session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    print(f"=== CHECKOUT COMPLETE for session: {session_id} ===\n")
    return jsonify({"status": "checked_out", "session_id": session_id, "firebase_deleted": delete_success}), 200


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
    
    # Only allow pairing if the session was created by a cart device
    if session.get("device_type") != "cart":
        return jsonify({"error": "This session was not created by a cart device"}), 403
    
    # Mark the session as paired (phone has scanned the QR code)
    sessions.update_one(
        {"session_id": session_id},
        {"$set": {"paired": True, "paired_at": now()}}
    )
    
    # Start the webcam for this session (using phone camera mode)
    start_webcam_for_session(session_id, use_phone_camera=True)
    
    # Session exists, pairing successful
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
        "paired": session.get("paired", False),
        "device_type": session.get("device_type"),
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


@app.route("/api/prices/by-label/<label>", methods=["GET"])
def get_price_by_label(label):
    """Get price by product name or label (case-insensitive partial match)"""
    # Try exact match first (case-insensitive)
    price_doc = prices.find_one(
        {"product_name": {"$regex": f"^{label}$", "$options": "i"}}, 
        {"_id": 0}
    )
    # If not found, try partial match
    if not price_doc:
        price_doc = prices.find_one(
            {"product_name": {"$regex": label, "$options": "i"}}, 
            {"_id": 0}
        )
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
# PHONE CAMERA FRAME API
# ============================================================================

@app.route("/api/sessions/<session_id>/webcam-status", methods=["GET"])
def get_webcam_status(session_id):
    """Check if webcam is active for a session."""
    is_active = session_id in active_webcams
    detector = active_webcams.get(session_id)
    
    return jsonify({
        "session_id": session_id,
        "is_active": is_active,
        "use_phone_camera": detector.use_phone_camera if detector else None,
        "active_sessions": list(active_webcams.keys())
    }), 200


@app.route("/api/sessions/<session_id>/start-webcam", methods=["POST"])
def start_webcam_manual(session_id):
    """Manually start webcam for a session (useful for debugging)."""
    try:
        if session_id in active_webcams:
            return jsonify({
                "status": "already_running",
                "session_id": session_id
            }), 200
        
        start_webcam_for_session(session_id, use_phone_camera=True)
        return jsonify({
            "status": "started",
            "session_id": session_id
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>/frame", methods=["POST"])
def receive_frame(session_id):
    """Receive a frame from phone camera and add it to the webcam processing queue."""
    try:
        # Check if webcam is active for this session
        if session_id not in active_webcams:
            print(f"WARNING: No active webcam for session {session_id}")
            print(f"Active webcams: {list(active_webcams.keys())}")
            
            # Check if session is completed - don't restart if it is
            session = sessions.find_one({"session_id": session_id})
            if session and session.get("status") == "completed":
                print(f"Session {session_id} is completed - not auto-starting webcam")
                return jsonify({
                    "error": "Session is completed",
                    "session_id": session_id
                }), 410  # 410 Gone - resource is no longer available
            
            # Try to start it automatically (no pairing required)
            print(f"Attempting to auto-start webcam for session {session_id}")
            
            # Ensure session exists in MongoDB (create if it doesn't)
            if not session:
                print(f"Session {session_id} not found in MongoDB, creating it...")
                try:
                    # Create session if it doesn't exist
                    FirebaseCartManager().create_cart(session_id)
                    session_doc = {
                        "session_id": session_id,
                        "status": "active",
                        "device_type": "phone",  # Created by phone when auto-starting
                    }
                    sessions.insert_one(session_doc)
                    print(f"✓ Created session {session_id} in MongoDB")
                except Exception as e:
                    print(f"Warning: Failed to create session in MongoDB: {e}")
                    # Continue anyway - webcam can work without MongoDB session
            
            try:
                start_webcam_for_session(session_id, use_phone_camera=True)
                # Wait a moment for detector to be created (synchronously)
                import time
                # Wait up to 2 seconds for detector to be created (YOLO model loading can take time)
                for i in range(20):
                    time.sleep(0.1)
                    if session_id in active_webcams:
                        print(f"✓ Webcam auto-started successfully for session {session_id} (after {i*0.1:.1f}s)")
                        break
                else:
                    # Still not in active_webcams after waiting
                    print(f"✗ Webcam auto-start failed - detector not created after 2 seconds")
                    print(f"Active webcams after attempt: {list(active_webcams.keys())}")
                    return jsonify({
                        "error": "No active webcam for this session (auto-start failed - check backend logs for YOLO/Firebase errors)",
                        "active_sessions": list(active_webcams.keys())
                    }), 404
            except Exception as e:
                print(f"✗ Exception during auto-start webcam: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    "error": f"No active webcam for this session (auto-start exception: {str(e)})",
                    "active_sessions": list(active_webcams.keys())
                }), 404
        
        detector = active_webcams[session_id]
        print(f"Received frame for session: {session_id}")
        
        # Check if detector is in phone camera mode
        if not detector.use_phone_camera:
            return jsonify({"error": "Webcam is not in phone camera mode"}), 400
        
        # Get image data from request
        # Priority: binary JPEG > multipart/form-data > base64 JSON (for backwards compatibility)
        
        # First, try to get binary JPEG data directly from request body
        content_type = request.content_type or ''
        if 'image/jpeg' in content_type or 'image/jpg' in content_type:
            # Binary JPEG data in request body
            image_bytes = request.data
            if image_bytes:
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    detector.add_frame_from_phone(frame)
                    return jsonify({"status": "frame_received"}), 200
                else:
                    return jsonify({"error": "Failed to decode binary JPEG"}), 400
        
        # Handle multipart/form-data file upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                image_bytes = file.read()
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    detector.add_frame_from_phone(frame)
                    return jsonify({"status": "frame_received"}), 200
        
        # Fallback: Try base64 JSON (for backwards compatibility)
        data = request.get_json(silent=True)
        if data and 'image' in data:
            image_data = data['image']
            if isinstance(image_data, str):
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                try:
                    image_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        detector.add_frame_from_phone(frame)
                        return jsonify({"status": "frame_received"}), 200
                except Exception as e:
                    print(f"Error decoding base64: {e}")
        
        return jsonify({"error": "No image data provided"}), 400
        
    except Exception as e:
        print(f"Error receiving frame: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================================================
# STRIPE PAYMENT API
# ============================================================================

@app.route("/api/create-payment-intent", methods=["POST"])
def create_payment_intent():
    """Create a Stripe payment intent for the checkout"""
    try:
        data = request.json
        amount = data.get('amount')  # Amount in cents
        session_id = data.get('session_id')
        
        if not amount or amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400
        
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(amount),
            currency='usd',
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'session_id': session_id,
            }
        )
        
        return jsonify({
            'clientSecret': intent['client_secret'],
            'paymentIntentId': intent['id']
        }), 200
        
    except Exception as e:
        print(f"Error creating payment intent: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# RUN WEBCAM API (DISABLED - webcam now starts when phone pairs via /api/pair)
# ============================================================================
# @app.route("/api/webcam/<session_id>", methods=["GET"])
# def run_webcam_endpoint(session_id):
#     """DEPRECATED: Use /api/pair endpoint instead"""
#     pass


if __name__ == "__main__":
    # Use host='0.0.0.0' to allow connections from other devices on the network
    # This is necessary when testing on physical devices
    app.run(debug=FLASK_DEBUG, host='0.0.0.0', port=5001)
