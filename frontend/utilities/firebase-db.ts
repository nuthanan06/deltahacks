import { initializeApp } from 'firebase/app';
import { getFirestore, collection, onSnapshot, query, where, doc } from 'firebase/firestore';
import { getStorage, ref, getBytes } from 'firebase/storage';
import firebaseConfig from '../firebaseConfig.json';

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const storage = getStorage(app);

/**
 * Listen to real-time updates of a cart's items with images
 * @param sessionId - The cart document ID
 * @param onItemsUpdate - Callback when items change
 */
export function listenToCartItems(
  sessionId: string,
  onItemsUpdate: (items: CartItem[]) => void
) {
  const cartsRef = collection(db, 'carts');
  
  const unsubscribe = onSnapshot(
    query(cartsRef, where('session_id', '==', sessionId)),
    (snapshot) => {
      if (!snapshot.empty) {
        const cartDoc = snapshot.docs[0].data();
        const items: CartItem[] = (cartDoc.items || []).map((item: any) => ({
          id: item.item_id,
          label: item.label,
          name: item.product_name,
          price: item.price,
          imageUrl: item.image_url,
          timestamp: item.timestamp,
          confidence: item.confidence,
        }));
        onItemsUpdate(items);
      }
    },
    (error) => {
      console.error('Error listening to cart items:', error);
    }
  );

  return unsubscribe; // Return unsubscribe function to cleanup
}

/**
 * Listen to all carts in real-time
 * @param onCartsUpdate - Callback when carts change
 */
export function listenToAllCarts(
  onCartsUpdate: (carts: Cart[]) => void
) {
  const cartsRef = collection(db, 'carts');
  
  const unsubscribe = onSnapshot(
    cartsRef,
    (snapshot) => {
      const carts: Cart[] = snapshot.docs.map((doc) => {
        const data = doc.data();
        return {
          id: doc.id,
          sessionId: data.session_id,
          items: (data.items || []).map((item: any) => ({
            id: item.item_id,
            label: item.label,
            name: item.product_name,
            price: item.price,
            imageUrl: item.image_url,
            timestamp: item.timestamp,
            confidence: item.confidence,
          })),
          totalItems: data.total_items,
          totalPrice: data.total_price,
          createdAt: data.created_at?.toDate(),
        };
      });
      onCartsUpdate(carts);
    },
    (error) => {
      console.error('Error listening to carts:', error);
    }
  );

  return unsubscribe;
}

/**
 * Listen to a specific cart by session ID (document ID)
 * @param sessionId - The cart document ID (e.g., "demo_cart_003")
 * @param onCartUpdate - Callback when cart changes
 */
export function listenToCart(
  sessionId: string,
  onCartUpdate: (cart: Cart | null) => void
) {
  // Query by document ID, not session_id field
  const cartDocRef = doc(db, 'carts', sessionId);
  
  const unsubscribe = onSnapshot(
    cartDocRef,
    (docSnapshot) => {
      if (docSnapshot.exists()) {
        const data = docSnapshot.data();
        const cart: Cart = {
          id: docSnapshot.id,
          sessionId: data.session_id || sessionId, // Fallback to document ID
          items: (data.items || []).map((item: any) => ({
            id: item.item_id,
            label: item.label,
            name: item.product_name,
            price: item.price,
            imageUrl: item.image_url,
            timestamp: item.timestamp,
            confidence: item.confidence,
          })),
          totalItems: data.total_items,
          totalPrice: data.total_price,
          createdAt: data.created_at?.toDate(),
        };
        console.log('Firebase cart updated:', cart); // Debug log
        onCartUpdate(cart);
      } else {
        console.log('Cart document does not exist:', sessionId); // Debug log
        onCartUpdate(null);
      }
    },
    (error) => {
      console.error('Error listening to cart:', error);
      onCartUpdate(null);
    }
  );

  return unsubscribe;
}

// Type definitions
export interface CartItem {
  id: string;
  label: string;
  name: string;
  price: number;
  imageUrl?: string;
  timestamp?: string;
  confidence?: number;
}

export interface Cart {
  id: string;
  sessionId: string;
  items: CartItem[];
  totalItems: number;
  totalPrice: number;
  createdAt?: Date;
}
