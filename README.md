## **QuickCart**

### **What It Does**

**QuickCart** is a mobile grocery shopping app that uses your phone’s camera to automatically track items as you add or remove them from your cart. Simply point your phone at items in your cart, and the app:

- **Automatically detects items** using real-time computer vision (**YOLO object detection**)
- **Identifies products** using **CLIP embeddings** to match items to a product database
- **Manages your cart** by tracking quantities and grouping similar products
- **Calculates prices in real time** from a product database
- **Provides audio feedback** with beep sounds when items are added or removed
- **Syncs across devices** using **Firebase** for real-time cart updates
- **Streamlines checkout** with an integrated payment flow via the **Stripe API**

The app eliminates the need to manually scan barcodes or wait in checkout lines, making grocery shopping faster and more accessible.

---

### **How We Built It**

#### **Frontend (React Native / Expo)**

- Built with **React Native** and **Expo Router** for cross-platform mobile support
- Integrated **react-native-vision-camera** for high-performance camera capture
- Real-time **Firebase listeners** for cart synchronization
- **Programmatic audio generation** for quantity change feedback
- **TypeScript** for type safety

#### **Backend (Flask / Python)**

- **Flask REST API** handling image processing and cart management
- **YOLOv8** for real-time object detection from camera frames
- **CLIP (OpenAI ViT-B-32)** embeddings with **FAISS** for product similarity search
- **Motion tracking** to detect when items enter or exit the cart
- **MongoDB** for product price catalog lookup
- **Firebase Admin SDK** for cart persistence and real-time updates
- **Stripe API** for secure and fast payment processing

---

### **Architecture**

- Phone camera captures frames at **12 FPS** and sends **JPEG images** to the backend
- Backend processes frames through:
  **YOLO detection → CLIP embedding → product matching**
- Items are grouped by **normalized product names from embeddings**, not just class labels
- **Firebase Firestore** stores cart state with real-time listeners on the frontend
- **QR code pairing** connects mobile devices to shopping sessions

---

### **Key Integrations**

- **Firebase Firestore** for cart state management
- **Firebase Cloud Storage** for item image storage
- **MongoDB** for product price database
- **Stripe API** for payment processing
- **FAISS vector database** for fast similarity search

---

**QuickCart** processes camera frames in real time, identifies products using semantic matching, and maintains an accurate cart with automatic price calculation.
