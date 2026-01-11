from ultralytics import YOLO
import cv2
import numpy as np
from collections import defaultdict, deque
import os
import sys
import requests
from datetime import datetime
from urllib.parse import quote
from firebase import FirebaseCartManager
from firebase_admin import storage

# Import query function from data_compilation
query_module_path = os.path.join(os.path.dirname(__file__), "data_ compilation", "query.py")
if os.path.exists(query_module_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("query_module", query_module_path)
    query_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(query_module)
    query_image = query_module.query_image
    print("✓ Loaded query_image function")
else:
    print(f"Warning: query.py not found at {query_module_path}")
    query_image = None


class CartTrackerWebcam:
    """Tracks objects being added/removed from a shopping cart using YOLO detection and motion tracking."""
    
    def __init__(
        self,
        sessionId,
        model_path="yolov8n.pt",
        camera_index=None,
        output_folder="detected_items",
        frame_threshold=5,
        direction_threshold=30,
        history_size=10,
        recent_frames=19,
        approved_labels=None,
        use_phone_camera=False
    ):
        self.model = YOLO(model_path)
        self.use_phone_camera = use_phone_camera
        if not use_phone_camera and camera_index is not None:
            self.cap = cv2.VideoCapture(camera_index)
        else:
            self.cap = None
        self.sessionId = sessionId
        self.frame_queue = None
        if use_phone_camera:
            from queue import Queue
            self.frame_queue = Queue()
        
        # Create output folder if it doesn't exist
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Configuration
        self.FRAME_THRESHOLD = frame_threshold
        self.DIRECTION_THRESHOLD = direction_threshold
        self.HISTORY_SIZE = history_size
        self.RECENT_FRAMES = recent_frames
        
        self.APPROVED_LABELS = approved_labels or {
            "apple", "banana", "orange",
            "broccoli", "carrot",
            "bottle", "cup", "bowl", "book"
        }
        
        # Labels to exclude (humans and body parts)
        self.EXCLUDED_LABELS = {"person", "people", "human", "man", "woman", "child", "face", "hand"}
        
        # State tracking
        self.frame_counts = defaultdict(int)
        self.confirmed = []
        self.last_y = {}
        self.direction_score = defaultdict(int)
        self.frame_history = deque(maxlen=self.HISTORY_SIZE)
        self.manager = FirebaseCartManager(credentials_path="credentials.json")
        self.ensure_cart_exists()
        
        # API base URL for price lookup
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:5001")

    #=============================
    # State management methods
    #=============================
    
    def reset_label_state(self, label):
        """Reset all state for a given label."""
        self.frame_counts[label] = 0
        self.direction_score[label] = 0
        self.last_y.pop(label, None)

    def ensure_cart_exists(self):
        """Ensure the Firebase cart document exists before updates."""
        try:
            cart = self.manager.get_cart(self.sessionId)
            if cart is None:
                self.manager.create_cart(self.sessionId)
                print(f"Initialized Firebase cart: {self.sessionId}")
        except Exception as e:
            print(f"Error ensuring cart exists: {e}")
    

    #=============================
    # Firebase Cloud Storage Uploading
    #=============================

    def save_crop(self, label, crop, action="add"):
        """Save a crop image to the output folder with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{action}_{label}_{timestamp}.jpg"
        filepath = os.path.join(self.output_folder, filename)
        cv2.imwrite(filepath, crop)
        return filepath

    def upload_crop_to_storage(self, filepath) -> str:
        """Upload a saved crop to Firebase Storage and return download URL."""
        try:
            bucket = storage.bucket()
            filename = os.path.basename(filepath)
            blob = bucket.blob(f"carts/{self.sessionId}/{filename}")
            # Generate token and set metadata as expected by Firebase
            token = os.urandom(16).hex()
            blob.metadata = {"firebaseStorageDownloadTokens": token}
            # Infer content type
            content_type = "image/jpeg" if filename.lower().endswith(".jpg") else "image/png"
            blob.upload_from_filename(filepath, content_type=content_type)
            # Build Firebase-style download URL
            encoded_path = quote(blob.name, safe="")
            return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{encoded_path}?alt=media&token={token}"
        except Exception as e:
            print(f"Failed to upload crop: {e}")
            return None
    
    #=============================
    # Frame processing methods
    #=============================
    def process_frame(self, frame):
        """Process a single frame and return detected items."""
        results = self.model(frame)
        r = results[0]
        
        detected_this_frame = []
        detected_labels = set()
        
        for box in r.boxes:
            label = r.names[int(box.cls[0])]
            
            # Exclude human-related labels instead of only allowing specific labels
            if label in self.EXCLUDED_LABELS:
                continue
            
            # bounding box coords
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop = frame[y1:y2, x1:x2].copy()
            
            detected_this_frame.append((label, crop))
            detected_labels.add(label)
            
            # track direction
            center_y = (y1 + y2) // 2
            if label in self.last_y:
                delta = center_y - self.last_y[label]
                self.direction_score[label] += delta
            
            self.last_y[label] = center_y
        
        return detected_this_frame, detected_labels, r
    
    #=============================
    # Tracking update methods
    #=============================
    def update_tracking(self, detected_this_frame, detected_labels):
        """Update frame counts and confirm add/remove actions."""
        # reset counters if label disappears
        for label in list(self.frame_counts.keys()):
            if label not in detected_labels:
                self.reset_label_state(label)
        
        # update frame counts
        for item in detected_this_frame:
            label, crop = item if isinstance(item, tuple) else (item, None)
            self.frame_counts[label] += 1
            
            if self.frame_counts[label] >= self.FRAME_THRESHOLD:
                # Check if this label was NOT detected in frames 11-500 (skip the last 10 frames)
                is_new_detection = all(
                    label not in history_set 
                    for history_set in list(self.frame_history)[:-self.RECENT_FRAMES]
                )
                
                if self.direction_score[label] > self.DIRECTION_THRESHOLD:
                    if is_new_detection:
                        print(f"➕ Added to cart: {label}")
                        self.confirmed.append(label)
                        self.frame_counts[label] = 0
                        
                        if crop is not None:
                            filepath = self.save_crop(label, crop, "add")
                            print(f"   Saved to: {filepath}")
                            # Upload crop to Storage and store URL
                            image_url = self.upload_crop_to_storage(filepath)
                            # Query image for barcode and get price before adding to Firebase
                            self.add_item_to_firebase(label, image_path=filepath, image_url=image_url)
                        else:
                            self.add_item_to_firebase(label)
                
                elif self.direction_score[label] < -self.DIRECTION_THRESHOLD and label in self.confirmed:
                    print(f"➖ Removed from cart: {label}")
                    self.confirmed.pop(self.confirmed.index(label))
                    self.frame_counts[label] = 0
                    
                    if crop is not None:
                        filepath = self.save_crop(label, crop, "remove")
                        print(f"   Saved to: {filepath}")
                        # Upload removal crop (optional audit)
                        image_url = self.upload_crop_to_storage(filepath)
                        self.remove_item_from_firebase(label, image_url=image_url)
                    else:
                        self.remove_item_from_firebase(label)
        
        # Store this frame's detections in history (only labels, not crops)
        self.frame_history.append(detected_labels)
    
    #=============================
    # Firebase interaction methods
    #=============================
    def get_product_from_image(self, image_path: str):
        """Query image to get product info using CLIP similarity search.
        
        Returns:
            dict with keys: barcode, name, brand, score, or None if no match
        """
        if query_image is None:
            print("Warning: query_image not available, skipping product lookup")
            return None
        
        try:
            print(f"Querying image for product: {image_path}")
            results = query_image(image_path, top_k=1)
            if results and len(results) > 0:
                result = results[0]
                barcode = result.get('barcode')
                name = result.get('name', 'Unknown')
                brand = result.get('brand', '')
                score = result.get('score', 0)
                print(f"  Found match: barcode={barcode}, name={name}, brand={brand}, score={score:.3f}")
                return {
                    'barcode': barcode,
                    'name': name,
                    'brand': brand,
                    'score': score
                }
            else:
                print("  No matches found in product database")
                return None
        except Exception as e:
            print(f"Error querying image: {e}")
            return None
    
    def get_barcode_from_image(self, image_path: str):
        """Query image to get barcode using CLIP similarity search (deprecated - use get_product_from_image)."""
        product_info = self.get_product_from_image(image_path)
        return product_info.get('barcode') if product_info else None
    
    def get_price_from_api(self, barcode: str):
        """Get price from API endpoint by barcode."""
        try:
            url = f"{self.api_base_url}/api/prices/{barcode}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                price_doc = response.json()
                price = price_doc.get('price', 0.0)
                product_name = price_doc.get('product_name')
                # Format product name: first letter of each word capitalized, rest lowercase
                if product_name:
                    product_name = product_name.title()
                print(f"  Found price via API: ${price:.2f}, product: {product_name}")
                return float(price), product_name
            elif response.status_code == 404:
                print(f"  No price found for barcode: {barcode}")
                return 0.0, None
            else:
                print(f"  API error ({response.status_code}): {response.text}")
                return 0.0, None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching price from API: {e}")
            return 0.0, None
    
    def get_price_by_label_from_api(self, label: str):
        """Get price from API endpoint by label/product name."""
        try:
            url = f"{self.api_base_url}/api/prices/by-label/{label}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                price_doc = response.json()
                price = price_doc.get('price', 0.0)
                product_name = price_doc.get('product_name')
                # Format product name: first letter of each word capitalized, rest lowercase
                if product_name:
                    product_name = product_name.title()
                print(f"  Found price via API (by label): ${price:.2f}, product: {product_name}")
                return float(price), product_name
            elif response.status_code == 404:
                print(f"  No price found for label: {label}")
                return 0.0, None
            else:
                print(f"  API error ({response.status_code}): {response.text}")
                return 0.0, None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching price from API by label: {e}")
            return 0.0, None
    
    def check_item_exists_in_cart(self, barcode: str):
        """Check if item with barcode already exists in cart and return quantity."""
        try:
            cart = self.manager.get_cart(self.sessionId)
            if not cart or 'items' not in cart:
                return 0
            
            # Count items with matching barcode
            count = 0
            for item in cart.get('items', []):
                # Check if item has barcode field or if label matches
                if item.get('barcode') == barcode:
                    count += 1
            
            return count
        except Exception as e:
            print(f"Error checking cart: {e}")
            return 0
    
    def add_item_to_firebase(self, label, image_path=None, image_url=None):
        """
        Add confirmed item to Firebase cart.
        Uses CLIP embedding to get product name and groups items by product name.
        Queries image for product info, gets price from API, and handles quantity updates.
        """
        barcode = None
        price = 0.0
        product_name = label.title()  # Default fallback: first letter of each word capitalized
        embedding_product_name = None  # Product name from embedding (top match)
        
        # Query image for product info using CLIP embedding if image path is provided
        if image_path and os.path.exists(image_path):
            product_info = self.get_product_from_image(image_path)
            if product_info:
                barcode = product_info.get('barcode')
                embedding_product_name = product_info.get('name')  # Use product name from embedding
                print(f"  Using product name from embedding: {embedding_product_name}")
                
                # Get price and product name from API using barcode
                if barcode:
                    price, api_product_name = self.get_price_from_api(barcode)
                    
                    # Prefer embedding product name, but use API name if embedding name is generic
                    if embedding_product_name and embedding_product_name != 'Unknown':
                        product_name = embedding_product_name
                    elif api_product_name:
                        product_name = api_product_name
        
        # If no barcode found or no price found by barcode, try querying by label
        if price == 0.0 or not barcode:
            label_price, label_product_name = self.get_price_by_label_from_api(label)
            if label_price > 0:
                price = label_price
                # Use label product name only if we don't have embedding name
                if label_product_name and not embedding_product_name:
                    product_name = label_product_name
        
        # Add item to Firebase (will increment quantity if item already exists)
        # Group by product_name from embedding as primary key
        try:
            item_id = self.manager.add_item(
                session_id=self.sessionId,
                label=label,
                image_url=image_url,
                price=price,
                product_name=product_name,  # This will be used for grouping
                confidence=1.0,
                barcode=barcode
            )
            
            # Get updated quantity from cart
            quantity = 1
            try:
                cart = self.manager.get_cart(self.sessionId)
                if cart and 'items' in cart:
                    for item in cart.get('items', []):
                        if barcode and item.get('barcode') == barcode:
                            quantity = item.get('quantity', 1)
                            break
                        elif not barcode and item.get('label') == label:
                            quantity = item.get('quantity', 1)
                            break
            except:
                pass
            
            quantity_info = f" (quantity: {quantity})" if quantity > 1 else ""
            barcode_info = f", barcode: {barcode}" if barcode else ""
            price_info = f", price: ${price:.2f}" if price > 0 else ""
            
            print(f"✓ Item added to Firebase: {item_id} ({label}{barcode_info}{price_info}{quantity_info})")
            return item_id
        except Exception as e:
            print(f"Error adding item to Firebase: {e}")
            return None
    
    def remove_item_from_firebase(self, label, image_url=None):
        """Remove item from Firebase cart. Decrements quantity if item exists."""
        # Try to find barcode from existing cart items for better matching
        barcode = None
        try:
            cart = self.manager.get_cart(self.sessionId)
            if cart and 'items' in cart:
                for item in cart.get('items', []):
                    if item.get('label') == label and item.get('barcode'):
                        barcode = item.get('barcode')
                        break
        except:
            pass
        
        self.manager.remove_item(session_id=self.sessionId, label=label, barcode=barcode)


    def add_frame_from_phone(self, frame_array):
        """Add a frame received from phone camera to the processing queue."""
        if self.frame_queue is not None:
            self.frame_queue.put(frame_array)
        else:
            print("Warning: frame_queue not initialized. Phone camera mode not enabled.")
    
    def run(self, show_window=False):
        """Main loop to process video frames.
        
        Args:
            show_window: If True, display OpenCV window (requires GUI). Default False for Flask background threads.
        """
        self.running = True
        print(f"Starting cart tracker. Output folder: {self.output_folder}")
        if self.use_phone_camera:
            print("Using phone camera mode - waiting for frames from API...")
        if show_window:
            print("Press 'q' to quit")
        
        frame_count = 0
        while self.running:
            # Every 30 frames, check if the session still exists in Firebase
            # If it's been deleted (checkout happened), stop the webcam
            frame_count += 1
            if frame_count % 30 == 0:
                try:
                    cart = self.manager.get_cart(self.sessionId)
                    if cart is None:
                        print(f"Session {self.sessionId} no longer exists in Firebase. Stopping webcam.")
                        self.running = False
                        break
                except Exception as e:
                    print(f"Error checking cart existence: {e}")
            
            # Get frame from either local webcam or phone camera queue
            if self.use_phone_camera:
                # Wait for frame from phone (with timeout to allow checking session)
                try:
                    frame_array = self.frame_queue.get(timeout=0.1)
                    # Convert numpy array to OpenCV format
                    if isinstance(frame_array, bytes):
                        # Decode from bytes if needed
                        frame = cv2.imdecode(np.frombuffer(frame_array, np.uint8), cv2.IMREAD_COLOR)
                    elif isinstance(frame_array, np.ndarray):
                        frame = frame_array
                    else:
                        print(f"Warning: Unexpected frame type: {type(frame_array)}")
                        continue
                except:
                    # Timeout or empty queue - continue loop to check session
                    continue
            else:
                # Use local webcam
                if self.cap is None:
                    print("Error: No camera available")
                    break
                ret, frame = self.cap.read()
                if not ret:
                    break
            
            detected_this_frame, detected_labels, results = self.process_frame(frame)
            self.update_tracking(detected_this_frame, detected_labels)
            
            print("CONFIRMED", self.confirmed)
            print("DIRECTION SCORE", dict(self.direction_score))
            
            # Only show window if explicitly requested (for manual testing)
            if show_window:
                annotated = results.plot()
                cv2.imshow("YOLOv8", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        
        self.cleanup()
    
    def stop(self):
        """Stop the webcam loop."""
        print(f"Stopping cart tracker for session: {self.sessionId}")
        self.running = False
    
    def cleanup(self):
        """Release resources."""
        if self.cap is not None:
            self.cap.release()
        try:
            if cv2.getWindowProperty("YOLOv8", cv2.WND_PROP_VISIBLE) >= 0:
                cv2.destroyAllWindows()
        except cv2.error:
            # Window doesn't exist, ignore
            pass
        print(f"\nFinal cart contents: {self.confirmed}")


if __name__ == "__main__":
    tracker = CartTrackerWebcam(sessionId="demo_cart_001")
    tracker.run()
