import {
  StyleSheet,
  FlatList,
  TouchableOpacity,
  View,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';
import type { Product } from '@/contexts/CartContext';

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
  const { products, updateProductQuantity, removeProduct, getSubtotal, sessionId } = useCart();

  const handleCheckout = () => {
    if (products.length === 0) {
      Alert.alert('Empty Cart', 'Please scan some products before checkout.');
      return;
    }
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
    paddingTop: 60,
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

