import { StyleSheet, TouchableOpacity, ScrollView, View, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { useStripe } from '@stripe/stripe-react-native';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';
import { processPaymentWithSheet, dollarsToCents } from '@/services/stripe';
import { useState } from 'react';

/**
 * Checkout Screen with Stripe Payment Integration
 * 
 * Displays order summary and processes payments using Stripe Payment Sheet.
 * 
 * Features:
 * - Shows scanned products with quantities and prices
 * - Calculates subtotal, tax (13%), and total
 * - Integrates Stripe Payment Sheet for secure payments
 * - Handles payment success/failure
 * - Clears cart and navigates on successful payment
 */
export default function CheckoutScreen() {
  const router = useRouter();
  const stripe = useStripe();
  const {
    products,
    getSubtotal,
    getTax,
    getTotal,
    clearCart,
    sessionId,
  } = useCart();
  
  const [isProcessing, setIsProcessing] = useState(false);

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}`;
  };

  /**
   * Handle Stripe payment processing
   * 
   * Flow:
   * 1. Convert total amount to cents
   * 2. Create payment metadata with session and product info
   * 3. Initialize and present Stripe Payment Sheet
   * 4. On success: clear cart and navigate to home
   * 5. On failure: show error message
   */
  const handlePayment = async () => {
    if (products.length === 0) {
      Alert.alert('Empty Cart', 'Please add items to your cart before checking out.');
      return;
    }

    setIsProcessing(true);

    try {
      const totalAmount = getTotal();
      const amountInCents = dollarsToCents(totalAmount);

      // Create metadata for the payment
      const metadata: Record<string, string> = {
        sessionId: sessionId || 'unknown',
        itemCount: products.length.toString(),
        subtotal: getSubtotal().toFixed(2),
        tax: getTax().toFixed(2),
        total: totalAmount.toFixed(2),
        // Add product details (limited by Stripe's metadata size limits)
        products: JSON.stringify(
          products.map(p => ({
            name: p.name,
            quantity: p.quantity,
            price: p.price,
          }))
        ).substring(0, 500), // Stripe metadata value limit
      };

      // Process payment using Stripe Payment Sheet
      const result = await processPaymentWithSheet(
        stripe,
        amountInCents,
        'cad',
        metadata,
        'DeltaHacks Self-Checkout'
      );

      if (result.success) {
        // Payment succeeded
        Alert.alert(
          'Payment Successful! 🎉',
          `Your order of ${formatPrice(totalAmount)} has been processed.\n\nPayment ID: ${result.paymentIntentId}`,
          [
            {
              text: 'Done',
              onPress: () => {
                clearCart();
                router.push('/(tabs)');
              },
            },
          ]
        );
      } else {
        // Payment failed or was cancelled
        Alert.alert(
          'Payment Failed',
          result.error || 'The payment could not be processed. Please try again.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      console.error('Payment error:', error);
      Alert.alert(
        'Payment Error',
        error instanceof Error ? error.message : 'An unexpected error occurred during payment processing.'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedView style={styles.header}>
        <ThemedText type="title" style={styles.title}>
          Checkout
        </ThemedText>
        {sessionId && (
          <ThemedText style={styles.sessionId}>
            Session: {sessionId}
          </ThemedText>
        )}
      </ThemedView>

      <ScrollView style={styles.content}>
        <ThemedView style={styles.section}>
          <ThemedText type="subtitle" style={styles.sectionTitle}>
            Order Summary
          </ThemedText>

          {products.length === 0 ? (
            <ThemedText style={styles.emptyCart}>
              Your cart is empty
            </ThemedText>
          ) : (
            products.map((product, index) => (
              <View key={`${product.name}-${index}`} style={styles.orderItem}>
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
            ))
          )}

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
            💳 Secure payment powered by Stripe
          </ThemedText>
        </ThemedView>
      </ScrollView>

      <ThemedView style={styles.footer}>
        <TouchableOpacity
          style={[
            styles.paymentButton,
            (isProcessing || products.length === 0) && styles.paymentButtonDisabled,
          ]}
          onPress={handlePayment}
          disabled={isProcessing || products.length === 0}
        >
          <ThemedText style={styles.paymentButtonText}>
            {isProcessing ? 'Processing...' : `Pay ${formatPrice(getTotal())}`}
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
  emptyCart: {
    textAlign: 'center',
    opacity: 0.6,
    paddingVertical: 20,
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
  paymentButtonDisabled: {
    backgroundColor: '#ccc',
    opacity: 0.6,
  },
  paymentButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
});