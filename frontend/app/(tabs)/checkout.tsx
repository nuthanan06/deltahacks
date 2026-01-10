import { StyleSheet, TouchableOpacity, ScrollView, View, Alert } from 'react-native';
import { useRouter } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';

/**
 * Checkout Screen
 * 
 * Displays a summary of scanned products, subtotal, tax, and total.
 * Includes a button to proceed with payment.
 * 
 * TODO: Integrate Stripe payment processing:
 * - Install @stripe/stripe-react-native
 * - Initialize Stripe with publishable key
 * - Create payment intent via backend API
 * - Use Stripe Payment Sheet or similar component
 * - Handle payment success/failure callbacks
 * - Update order status in Firebase
 */
export default function CheckoutScreen() {
  const router = useRouter();
  const {
    products,
    getSubtotal,
    getTax,
    getTotal,
    clearCart,
  } = useCart();

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}`;
  };

  /**
   * Mock Stripe payment function
   * 
   * TODO: Replace with real Stripe integration:
   * 1. Call backend API to create payment intent
   * 2. Initialize Stripe Payment Sheet with payment intent
   * 3. Present payment sheet to user
   * 4. Handle payment confirmation
   * 5. On success:
   *    - Save order to Firebase
   *    - Clear cart
   *    - Navigate to success screen
   * 6. On failure:
   *    - Show error message
   *    - Allow retry
   */
  const handlePayment = async () => {
    try {
      // Mock payment processing delay
      Alert.alert(
        'Processing Payment',
        'This is a placeholder. Real Stripe integration will be added here.',
        [
          {
            text: 'Simulate Success',
            onPress: () => {
              // Mock successful payment
              Alert.alert(
                'Payment Successful!',
                `Your order total of ${formatPrice(getTotal())} has been processed.`,
                [
                  {
                    text: 'OK',
                    onPress: () => {
                      clearCart();
                      router.push('/(tabs)/index');
                    },
                  },
                ]
              );
            },
          },
          {
            text: 'Cancel',
            style: 'cancel',
          },
        ]
      );
    } catch (error) {
      Alert.alert('Payment Error', 'An error occurred during payment processing.');
    }
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedView style={styles.header}>
        <ThemedText type="title" style={styles.title}>
          Checkout
        </ThemedText>
      </ThemedView>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <ThemedView style={styles.section}>
          <ThemedText type="subtitle" style={styles.sectionTitle}>
            Order Summary
          </ThemedText>

          {products.map((product) => (
            <View key={product.id} style={styles.orderItem}>
              <View style={styles.orderItemInfo}>
                <ThemedText type="defaultSemiBold">{product.name}</ThemedText>
                <ThemedText style={styles.orderItemQuantity}>
                  Qty: {product.quantity} × {formatPrice(product.price)}
                </ThemedText>
              </View>
              <ThemedText type="defaultSemiBold">
                {formatPrice(product.price * product.quantity)}
              </ThemedText>
            </View>
          ))}
        </ThemedView>

        <ThemedView style={styles.section}>
          <View style={styles.summaryRow}>
            <ThemedText>Subtotal:</ThemedText>
            <ThemedText>{formatPrice(getSubtotal())}</ThemedText>
          </View>

          <View style={styles.summaryRow}>
            <ThemedText>Tax (13%):</ThemedText>
            <ThemedText>{formatPrice(getTax())}</ThemedText>
          </View>

          <View style={[styles.summaryRow, styles.totalRow]}>
            <ThemedText type="defaultSemiBold" style={styles.totalLabel}>
              Total:
            </ThemedText>
            <ThemedText type="defaultSemiBold" style={styles.totalAmount}>
              {formatPrice(getTotal())}
            </ThemedText>
          </View>
        </ThemedView>

        <ThemedView style={styles.noteSection}>
          <ThemedText style={styles.note}>
            Note: Payment processing is mocked. Stripe integration will be added here.
          </ThemedText>
        </ThemedView>
      </ScrollView>

      <ThemedView style={styles.footer}>
        <TouchableOpacity
          style={styles.paymentButton}
          onPress={handlePayment}
          activeOpacity={0.7}>
          <ThemedText style={styles.paymentButtonText}>
            Proceed with Payment
          </ThemedText>
        </TouchableOpacity>
      </ThemedView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    padding: 20,
    paddingTop: 60,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  title: {
    marginBottom: 4,
  },
  content: {
    flex: 1,
  },
  section: {
    padding: 20,
    marginBottom: 16,
  },
  sectionTitle: {
    marginBottom: 16,
  },
  orderItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  orderItemInfo: {
    flex: 1,
    marginRight: 16,
  },
  orderItemQuantity: {
    fontSize: 14,
    opacity: 0.6,
    marginTop: 4,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  totalRow: {
    marginTop: 8,
    paddingTop: 16,
    borderTopWidth: 2,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  totalLabel: {
    fontSize: 18,
  },
  totalAmount: {
    fontSize: 18,
  },
  noteSection: {
    padding: 20,
    paddingTop: 0,
  },
  note: {
    fontSize: 12,
    opacity: 0.6,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  footer: {
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.1)',
  },
  paymentButton: {
    backgroundColor: '#0a7ea4',
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  paymentButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});

