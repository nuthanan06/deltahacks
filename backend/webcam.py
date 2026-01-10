from ultralytics import YOLO
import cv2
from collections import defaultdict, deque
import os
from datetime import datetime
from urllib.parse import quote
from firebase import FirebaseCartManager
from firebase_admin import storage


class CartTrackerWebcam:
    """Tracks objects being added/removed from a shopping cart using YOLO detection and motion tracking."""
    
    def __init__(
        self,
        sessionId,
        model_path="yolov8n.pt",
        camera_index=0,
        output_folder="detected_items",
        frame_threshold=10,
        direction_threshold=30,
        history_size=50,
        recent_frames=19,
        approved_labels=None
    ):
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(camera_index)
        self.sessionId = sessionId
        
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
        
        # State tracking
        self.frame_counts = defaultdict(int)
        self.confirmed = []
        self.last_y = {}
        self.direction_score = defaultdict(int)
        self.frame_history = deque(maxlen=self.HISTORY_SIZE)
        self.manager = FirebaseCartManager(credentials_path="credentials.json")
        self.ensure_cart_exists()

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
            
            if label not in self.APPROVED_LABELS:
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
                            self.add_item_to_firebase(label, image_url=image_url)
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
    def add_item_to_firebase(self, label, image_url=None):
        """Add confirmed item to Firebase cart."""
        item_id = self.manager.add_item(
            session_id=self.sessionId,
            label=label,
            image_url=image_url,
            price=0.0,  # Price can be set later
            product_name=label.capitalize(),
            confidence=1.0  # Placeholder confidence
        )
        print(f"✓ Item added to Firebase: {item_id} ({label})")
    
    def remove_item_from_firebase(self, label, image_url=None):
        """Remove item from Firebase cart."""
        self.manager.remove_item(session_id=self.sessionId, label=label)


    def run(self):
        """Main loop to process video frames."""
        print(f"Starting cart tracker. Output folder: {self.output_folder}")
        print("Press 'q' to quit")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            detected_this_frame, detected_labels, results = self.process_frame(frame)
            self.update_tracking(detected_this_frame, detected_labels)
            
            annotated = results.plot()
            cv2.imshow("YOLOv8", annotated)
            
            print("CONFIRMED", self.confirmed)
            print("DIRECTION SCORE", dict(self.direction_score))
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        
        self.cleanup()
    
    def cleanup(self):
        """Release resources."""
        self.cap.release()
        cv2.destroyAllWindows()
        print(f"\nFinal cart contents: {self.confirmed}")


if __name__ == "__main__":
    tracker = CartTrackerWebcam(sessionId="demo_cart_001")
    tracker.run()
