import { StyleSheet, TouchableOpacity, ScrollView, View, Alert } from 'react-native';
import { useRouter } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';
import { useStripe } from '@stripe/stripe-react-native';
import { initializeStripe, processPaymentWithSheet, dollarsToCents } from '@/services/stripe';
import { useEffect } from 'react';
const { initPaymentSheet, presentPaymentSheet } = useStripe();


useEffect(() => {
  initializeStripe().catch((err) => console.error('Stripe init error:', err));
}, []);

export default function CheckoutScreen() {
  const router = useRouter();
  const {
    products,
    getSubtotal,
    getTax,
    getTotal,
    clearCart,
    sessionId,
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
    if (products.length === 0) {
      Alert.alert('Cart Empty', 'Please add products before checking out.');
      return;
    }
  
    try {
      // Convert total to cents for Stripe
      const amountInCents = dollarsToCents(getTotal());
  
      // Process payment using Stripe Payment Sheet
      const result = await processPaymentWithSheet(
        { initPaymentSheet, presentPaymentSheet },
        amountInCents,
        'cad', // or 'cad' depending on your backend
        'QuickCart' // merchant display name
      );
  
      if (result.success) {
        Alert.alert(
          'Payment Successful!',
          `Your order total of $${getTotal().toFixed(2)} has been processed.`,
          [
            {
              text: 'OK',
              onPress: () => {
                clearCart();
                router.push('/(tabs)'); // navigate to home or success page
              },
            },
          ]
        );
      } else {
        Alert.alert('Payment Failed', result.error || 'Something went wrong. Please try again.');
      }
  
      // Call backend to stop webcam and mark session as completed
      if (sessionId) {
        try {
          console.warn(`🟡 handlePayment: Calling checkout endpoint for sessionId: ${sessionId}`);
          const API_BASE_URL = 'http://localhost:5001';
          const checkoutUrl = `${API_BASE_URL}/api/sessions/${sessionId}/checkout`;
          console.warn(`🟡 handlePayment: URL: ${checkoutUrl}`);
          
          const response = await fetch(checkoutUrl, {
            method: 'PUT',
          });
          console.warn(`🟡 handlePayment: Response status: ${response.status}`);
          
          const data = await response.json();
          console.warn('✅ handlePayment: Session checkout complete, response:', data);
        } catch (error) {
          console.error('❌ handlePayment: Error calling checkout endpoint:', error);
        }
      } else {
        console.warn('⚠️ handlePayment: No sessionId available');
      }
    } catch (error) {
      console.error('Payment error:', error);
      Alert.alert(
        'Payment Error',
        error instanceof Error ? error.message : 'An unexpected error occurred.'
      );
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <ThemedText type="title" style={styles.title}>
          Checkout
        </ThemedText>
        {sessionId && (
          <ThemedText style={styles.sessionId}>
            Session: {sessionId}
          </ThemedText>
        )}
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.section}>
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
        </View>

        <View style={styles.section}>
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
        </View>

        <View style={styles.noteSection}>
          <ThemedText style={styles.note}>
            Note: Payment processing is mocked. Stripe integration will be added here.
          </ThemedText>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={styles.paymentButton}
          onPress={handlePayment}
          activeOpacity={0.7}>
          <ThemedText style={styles.paymentButtonText}>
            Proceed with Payment
          </ThemedText>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#505066', //BASE COLOR
  },
  header: {
    padding: 20,
    paddingTop: 80,
    borderBottomWidth: 1,
    backgroundColor: '#069e66',
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  title: {
    marginBottom: 4,
  },
  sessionId: {
    fontSize: 12,
    opacity: 0.7,
    fontFamily: 'monospace',
    marginTop: 4,
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
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
    backgroundColor: '#eda70e',
  },
  paymentButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});

