import {
  StyleSheet,
  FlatList,
  TouchableOpacity,
  View,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useRef } from 'react';
import * as Haptics from 'expo-haptics';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';
import type { Product } from '@/contexts/CartContext';
import { listenToCart } from '@/utilities/firebase-db';
import type { Cart } from '@/utilities/firebase-db';
import { LOCAL_IP } from '@/config/api';
import { initializeSounds, playIncreaseSound, playDecreaseSound, cleanupSounds, playBeep } from '@/utilities/sounds';

/**
 * Scanned Products Screen
 * 
 * Displays a list of products the user has scanned.
 * Products include name, price, and quantity.
 * 
 * TODO: Replace mock data with real Firebase integration:
 * - Listen to Firebase Realtime Database or Firestore
 * - Update products list in real-time as new items are scanned
 * - Handle product updates from backend
 * - Sync cart state with Firebase
 */
export default function ProductsScreen() {
  const router = useRouter();
  const { products, setProducts, updateProductQuantity, removeProduct, getSubtotal, sessionId } = useCart();
  const previousQuantitiesRef = useRef<Map<string, number>>(new Map());

  console.warn('🔴🔴🔴 ProductsScreen RENDERED with sessionId:', sessionId);

  // Initialize sound effects
  useEffect(() => {
    initializeSounds();

    return () => {
      cleanupSounds();
    };
  }, []);

  // Set up Firebase listener for real-time cart updates
  useEffect(() => {
    console.warn('🟡 ProductsScreen useEffect running, sessionId:', sessionId);
    
    if (!sessionId) {
      console.log('ProductsScreen: No sessionId, clearing products');
      setProducts([]);
      previousQuantitiesRef.current.clear();
      return;
    }

    console.log('ProductsScreen: Setting up Firebase listener for session:', sessionId);

    // Listen to cart updates in real-time
    const unsubscribe = listenToCart(sessionId, (cart: Cart | null) => {
      console.log('ProductsScreen: Firebase callback triggered');
      console.log('ProductsScreen: Firebase update received:', cart);
      console.log('ProductsScreen: Cart items count:', cart?.items?.length || 0);
      
      if (!cart || !cart.items) {
        setProducts([]);
        previousQuantitiesRef.current.clear();
        return;
      }

      // Transform Firebase items to Product format
      // Each Firebase item becomes a separate frontend item with its quantity
      const productsArray: Product[] = cart.items.map((item: any) => ({
        id: item.id || `${item.name || item.label}_${Date.now()}`,
        name: item.name || item.label || 'Unknown Product',
        price: item.price || 0,
        quantity: item.quantity || 1, // Use the quantity field from Firebase
      }));
      
      // Detect quantity changes and play sounds
      const currentQuantities = new Map<string, number>();
      productsArray.forEach(product => {
        const prevQuantity = previousQuantitiesRef.current.get(product.id) || 0;
        const currentQuantity = product.quantity;
        currentQuantities.set(product.id, currentQuantity);
        
        if (prevQuantity > 0 && currentQuantity !== prevQuantity) {
          // Quantity changed - play sound
          if (currentQuantity > prevQuantity) {
            // Quantity increased
            playBeep(800); // Higher pitch
            console.log(`🔊 Quantity increased for ${product.name}: ${prevQuantity} -> ${currentQuantity}`);
          } else if (currentQuantity < prevQuantity) {
            // Quantity decreased
            playBeep(400); // Lower pitch
            console.log(`🔊 Quantity decreased for ${product.name}: ${prevQuantity} -> ${currentQuantity}`);
          }
        }
      });
      
      // Update previous quantities
      previousQuantitiesRef.current = currentQuantities;
      
      console.log('ProductsScreen: Updated products:', productsArray);
      setProducts(productsArray);
    });

    // Cleanup listener when sessionId changes or component unmounts
    return () => {
      console.log('ProductsScreen: Cleaning up Firebase listener');
      unsubscribe();
    };
  }, [sessionId, setProducts]);

  const handleCheckout = async () => {
    if (products.length === 0) {
      Alert.alert('Empty Cart', 'Please scan some products before checkout.');
      return;
    }
    
    console.warn('🔴 handleCheckout: Starting checkout process');
    
    // Call backend to mark session as completed and stop webcam
    if (sessionId) {
      try {
        console.warn(`🟡 handleCheckout: Calling checkout endpoint for sessionId: ${sessionId}`);
        const checkoutUrl = `http://${LOCAL_IP}:5001/api/sessions/${sessionId}/checkout`;
        console.warn(`🟡 handleCheckout: URL: ${checkoutUrl}`);
        
        const response = await fetch(checkoutUrl, {
          method: 'PUT',
        });
        console.warn(`🟡 handleCheckout: Response status: ${response.status}`);
        
        const data = await response.json();
        console.warn('✅ handleCheckout: Webcam stopped for session:', data);
      } catch (error) {
        console.error('❌ handleCheckout: Error stopping webcam:', error);
      }
    } else {
      console.warn('⚠️ handleCheckout: No sessionId available');
    }
    
    console.warn('🟡 handleCheckout: Navigating to checkout screen');
    router.push('/(tabs)/checkout');
  };

  const handleQuantityChange = (product: Product, change: number) => {
    const newQuantity = product.quantity + change;
    if (newQuantity <= 0) {
      Alert.alert(
        'Remove Product',
        `Remove ${product.name} from cart?`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Remove',
            style: 'destructive',
            onPress: () => removeProduct(product.id),
          },
        ]
      );
    } else {
      // Play sound and haptic feedback based on change direction
      if (change > 0) {
        // Increase: Higher pitch ding + light haptic
        playIncreaseSound();
      } else {
        // Decrease: Lower pitch + medium haptic
        playDecreaseSound();
      }
      updateProductQuantity(product.id, newQuantity);
    }
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}`;
  };

  const renderProduct = ({ item }: { item: Product }) => (
    <View style={styles.productCard}>
      <View style={styles.productInfo}>
        <ThemedText type="defaultSemiBold" style={styles.productName}>
          {item.name}
        </ThemedText>
        <ThemedText style={styles.productPrice}>
          {formatPrice(item.price)} each
        </ThemedText>
      </View>

      <View style={styles.quantityControls}>
        <TouchableOpacity
          style={styles.quantityButton}
          onPress={() => handleQuantityChange(item, -1)}
          activeOpacity={0.7}>
          <ThemedText style={styles.quantityButtonText}>-</ThemedText>
        </TouchableOpacity>

        <ThemedText style={styles.quantityText}>{item.quantity}</ThemedText>

        <TouchableOpacity
          style={styles.quantityButton}
          onPress={() => handleQuantityChange(item, 1)}
          activeOpacity={0.7}>
          <ThemedText style={styles.quantityButtonText}>+</ThemedText>
        </TouchableOpacity>
      </View>

      <ThemedText style={styles.productTotal}>
        {formatPrice(item.price * item.quantity)}
      </ThemedText>
    </View>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <ThemedText type="title" style={styles.title}>
          Your Cart
        </ThemedText>
        {sessionId && (
          <ThemedText style={styles.sessionId}>
            Session: {sessionId}
          </ThemedText>
        )}
        <ThemedText style={styles.subtitle}>
          {products.length} {products.length === 1 ? 'item' : 'items'}
        </ThemedText>
      </View>

      {products.length === 0 ? (
        <View style={styles.emptyContainer}>
          <ThemedText style={styles.emptyText}>
            Your cart is empty. Scan an NFC chip to add products.
          </ThemedText>
        </View>
      ) : (
        <>
          <FlatList
            data={products}
            renderItem={renderProduct}
            keyExtractor={(item) => item.id}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          />

          <View style={styles.footer}>
            <View style={styles.subtotalRow}>
              <ThemedText type="defaultSemiBold">Subtotal:</ThemedText>
              <ThemedText type="defaultSemiBold">
                {formatPrice(getSubtotal())}
              </ThemedText>
            </View>

            <TouchableOpacity
              style={styles.checkoutButton}
              onPress={handleCheckout}
              activeOpacity={0.7}>
              <ThemedText style={styles.checkoutButtonText}>
                Proceed to Checkout
              </ThemedText>
            </TouchableOpacity>
          </View>
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#505066', //BASE COLOR
  },
  header: {
    backgroundColor: '#069e66',
    padding: 20,
    paddingTop: 80,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  title: {
    marginBottom: 4,
  },
  sessionId: {
    fontSize: 12,
    opacity: 0.7,
    fontFamily: 'monospace',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    opacity: 0.6,
  },
  listContent: {
    padding: 16,
  },
  productCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    marginBottom: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.1)',
  },
  productInfo: {
    flex: 1,
    marginRight: 12,
  },
  productName: {
    fontSize: 16,
    marginBottom: 4,
  },
  productPrice: {
    fontSize: 14,
    opacity: 0.6,
  },
  quantityControls: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
  },
  quantityButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#0a7ea4',
    justifyContent: 'center',
    alignItems: 'center',
  },
  quantityButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  quantityText: {
    marginHorizontal: 16,
    fontSize: 16,
    fontWeight: '600',
    minWidth: 30,
    textAlign: 'center',
  },
  productTotal: {
    fontSize: 16,
    fontWeight: '600',
    minWidth: 60,
    textAlign: 'right',
  },
  footer: {
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  subtotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  checkoutButton: {
    backgroundColor: '#0a7ea4',
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  checkoutButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    textAlign: 'center',
    fontSize: 16,
    opacity: 0.6,
  },
});

