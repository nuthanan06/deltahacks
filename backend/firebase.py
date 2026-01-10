import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime
from typing import List, Dict, Optional
import os
import uuid
from urllib.parse import quote


class FirebaseCartManager:
    """CRUD operations for cart tracking application using Firebase Firestore."""
    
    def __init__(self, credentials_path: str = "credentials.json"):
        """
        Initialize Firebase connection.
        
        Args:
            credentials_path: Path to Firebase service account JSON file.
                            If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        if not firebase_admin._apps:
            if credentials_path:
                cred = credentials.Certificate(credentials_path)
                # Use env var to set storage bucket, fallback to project-specific default
                bucket = os.getenv('FIREBASE_STORAGE_BUCKET', 'deltahacks-b18a7')
                firebase_admin.initialize_app(cred, {
                    'storageBucket': bucket
                })
            else:
                # Use default credentials from environment
                firebase_admin.initialize_app()
        
        self.db = firestore.client()
        self.carts_collection = 'carts'
    
    # ==================== CART OPERATIONS ====================
    
    def create_cart(self, session_id: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Create a new cart in the database.
        
        Args:
            session_id: Unique identifier for the cart
            camera_index: Camera index associated with this cart
            metadata: Additional metadata (e.g., location, store_id)
        
        Returns:
            Created cart document
        """
        cart_data = {
            'session_id': session_id,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'status': 'active',
            'total_items': 0,
            'total_price': 0.0,
            'items': [],  # List of current items in cart
            'metadata': metadata or {}
        }
        
        self.db.collection(self.carts_collection).document(session_id).set(cart_data)
        return cart_data
    
    def get_cart(self, session_id: str) -> Optional[Dict]:
        """
        Get cart information by session_id.
        
        Args:
            session_id: Unique identifier for the cart
        
        Returns:
            Cart document or None if not found
        """
        doc = self.db.collection(self.carts_collection).document(session_id).get()
        return doc.to_dict() if doc.exists else None
    
    def update_cart(self, session_id: str, updates: Dict) -> bool:
        """
        Update cart information.
        
        Args:
            session_id: Unique identifier for the cart
            updates: Dictionary of fields to update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            updates['updated_at'] = firestore.SERVER_TIMESTAMP
            self.db.collection(self.carts_collection).document(session_id).update(updates)
            return True
        except Exception as e:
            print(f"Error updating cart: {e}")
            return False
    
    def delete_cart(self, session_id: str) -> bool:
        """
        Delete a cart and all its items.
        
        Args:
            session_id: Unique identifier for the cart
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the cart
            self.db.collection(self.carts_collection).document(session_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting cart: {e}")
            return False
    
    def list_carts(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all carts, optionally filtered by status.
        
        Args:
            status: Filter by status ('active', 'inactive', etc.)
        
        Returns:
            List of cart documents
        """
        query = self.db.collection(self.carts_collection)
        
        if status:
            query = query.where('status', '==', status)
        
        return [doc.to_dict() for doc in query.stream()]
    
    # ==================== CART ITEMS OPERATIONS ====================
    
    def get_product_info(self, label: str) -> Dict:
        """
        Get product name and price from label.
        You can customize this to query a products database.
        
        Args:
            label: Item label from YOLO detection
        
        Returns:
            Dictionary with product_name and price
        """
        # Default product mapping - replace with database lookup
        product_database = {
            'apple': {'product_name': 'Red Apple', 'price': 0.99},
            'banana': {'product_name': 'Banana', 'price': 0.50},
            'orange': {'product_name': 'Orange', 'price': 0.75},
            'broccoli': {'product_name': 'Fresh Broccoli', 'price': 2.49},
            'carrot': {'product_name': 'Carrot', 'price': 0.89},
            'bottle': {'product_name': 'Water Bottle', 'price': 1.99},
            'cup': {'product_name': 'Disposable Cup', 'price': 0.25},
            'bowl': {'product_name': 'Bowl', 'price': 3.99},
            'book': {'product_name': 'Book', 'price': 12.99},
        }
        
        return product_database.get(label.lower(), {
            'product_name': label.title(),
            'price': 0.0
        })
    
    # ==================== CART ITEMS OPERATIONS ====================
    
    def add_item(self, session_id: str, label: str, image_path: Optional[str] = None, image_url: Optional[str] = None,
                 confidence: float = 1.0, product_name: Optional[str] = None, 
                 price: Optional[float] = None, metadata: Optional[Dict] = None) -> str:
        """
        Add an item to a cart.
        
        Args:
            session_id: Unique identifier for the cart
            label: Item label/name detected by YOLO (e.g., 'banana', 'apple')
            image_path: Path to saved crop image (will be uploaded to Firebase Storage)
            image_url: Precomputed image URL (skip upload if provided)
            confidence: Detection confidence score
            product_name: Human-readable product name (e.g., 'Organic Banana')
            price: Price of the item
            metadata: Additional item metadata
        
        Returns:
            Document ID of the created item
        """
        # Determine image URL: prefer provided URL, else upload from path
        final_image_url = image_url
        if not final_image_url and image_path and os.path.exists(image_path):
            filename = os.path.basename(image_path)
            final_image_url = self.upload_image_to_storage(image_path, session_id, filename)
        
        # Update cart: increment totals and add item to items list
        cart_ref = self.db.collection(self.carts_collection).document(session_id)
        cart_ref.update({
            'total_items': firestore.Increment(1),
            'total_price': firestore.Increment(price or 0.0),
            'items': firestore.ArrayUnion([{
                'item_id': f"{label}_{datetime.now().timestamp()}",
                'label': label,
                'product_name': product_name or label.title(),
                'price': price or 0.0,
                'confidence': confidence,
                'image_url': final_image_url,
                'timestamp': datetime.now().isoformat(),
                'action': 'add'
            }]),
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return f"{label}_{datetime.now().timestamp()}"
    
    def remove_item(self, session_id: str, label: str, image_path: Optional[str] = None,
                   product_name: Optional[str] = None, price: Optional[float] = None,
                   metadata: Optional[Dict] = None) -> str:
        """
        Remove the first occurrence of an item from a cart.
        
        Args:
            session_id: Unique identifier for the cart
            label: Item label/name to remove
            image_path: Path to saved crop image
            product_name: Human-readable product name
            price: Price of the item being removed
            metadata: Additional metadata
        
        Returns:
            Success message
        """
        # Update cart total and price
        self._update_cart_total(session_id, increment=-1, price_increment=-(price or 0.0))
        
        # Remove first occurrence of the item from the items array
        cart = self.get_cart(session_id)
        if cart and 'items' in cart:
            items = cart['items']
            for i, item in enumerate(items):
                if item['label'] == label:
                    items.pop(i)
                    break
            self.db.collection(self.carts_collection).document(session_id).update({
                'items': items,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        
        return f"{label}_removed"
    
    def get_cart_items(self, session_id: str) -> List[Dict]:
        """
        Get all items currently in a specific cart.
        
        Args:
            session_id: Unique identifier for the cart
        
        Returns:
            List of item dictionaries in the cart
        """
        cart = self.get_cart(session_id)
        return cart.get('items', []) if cart else []
    
    def clear_cart_items(self, session_id: str) -> int:
        """
        Clear all items from a cart.
        
        Args:
            session_id: Unique identifier for the cart
        
        Returns:
            Number of items deleted
        """
        cart = self.get_cart(session_id)
        count = len(cart.get('items', [])) if cart else 0
        
        # Reset cart total
        self._update_cart_total(session_id, set_value=0)
        
        return count
    
    # ==================== HELPER METHODS ====================
    
    def _update_cart_total(self, session_id: str, increment: int = 0, 
                          set_value: Optional[int] = None, price_increment: float = 0.0):
        """Update the total items count and price in a cart."""
        cart_ref = self.db.collection(self.carts_collection).document(session_id)
        
        if set_value is not None:
            cart_ref.update({
                'total_items': set_value,
                'total_price': 0.0,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
        else:
            cart_ref.update({
                'total_items': firestore.Increment(increment),
                'total_price': firestore.Increment(price_increment),
                'updated_at': firestore.SERVER_TIMESTAMP
            })
    
    def upload_image_to_storage(self, local_path: str, session_id: str, filename: str) -> str:
        """
        Upload an image to Firebase Storage.
        
        Args:
            local_path: Local file path
            session_id: Cart identifier (used for organizing storage)
            filename: Filename to use in storage
        
        Returns:
            Firebase download URL with access token
        """
        bucket = storage.bucket()
        blob = bucket.blob(f'carts/{session_id}/{filename}')
        # Generate a download token and set metadata as Firebase expects
        download_token = uuid.uuid4().hex
        blob.metadata = {"firebaseStorageDownloadTokens": download_token}
        # Infer content type (default to image/jpeg)
        content_type = "image/jpeg"
        if filename.lower().endswith(".png"):
            content_type = "image/png"
        blob.upload_from_filename(local_path, content_type=content_type)
        # Build Firebase-style download URL
        encoded_path = quote(blob.name, safe="")
        base_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{encoded_path}"
        return f"{base_url}?alt=media&token={download_token}"

if __name__ == "__main__":
    # Example usage
    manager = FirebaseCartManager()
    cart = manager.create_cart(session_id="cart123", camera_index=1, metadata={"store_id": "store456"})
    manager.add_item(session_id="cart123", label="banana", price=0.50)
    print("Created Cart:", cart)