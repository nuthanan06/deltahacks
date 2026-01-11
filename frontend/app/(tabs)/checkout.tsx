import { StyleSheet, TouchableOpacity, ScrollView, View, Alert, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { useStripe } from '@stripe/stripe-react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';
import { LOCAL_IP } from '@/config/api';
import { listenToCart } from '@/utilities/firebase-db';
import type { Cart } from '@/utilities/firebase-db';

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
  const { initPaymentSheet, presentPaymentSheet } = useStripe();
  const {
    products,
    getSubtotal,
    getTax,
    getTotal,
    clearCart,
    sessionId,
    setSessionId,
  } = useCart();

  // Get total price from Firebase
  const [firebaseCart, setFirebaseCart] = useState<Cart | null>(null);
  const [firebaseTotalPrice, setFirebaseTotalPrice] = useState<number>(0);
  const [isProcessingPayment, setIsProcessingPayment] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      setFirebaseCart(null);
      setFirebaseTotalPrice(0);
      return;
    }

    const unsubscribe = listenToCart(sessionId, (cart: Cart | null) => {
      console.log('Checkout - Firebase cart update:', cart);
      setFirebaseCart(cart);
      if (cart) {
        setFirebaseTotalPrice(cart.totalPrice || 0);
        console.log('Checkout - Firebase totalPrice:', cart.totalPrice);
      } else {
        setFirebaseTotalPrice(0);
      }
    });

    return () => unsubscribe();
  }, [sessionId]);

  const formatPrice = (price: number) => {
    if (isNaN(price) || price === null || price === undefined) {
      return '$0.00';
    }
    return `$${price.toFixed(2)}`;
  };

  // Use Firebase total_price directly (backend calculates sum of item prices)
  // Note: Firebase total_price is the sum of all item prices, not including tax
  const firebaseSubtotal = firebaseTotalPrice > 0 ? firebaseTotalPrice : getSubtotal();
  const firebaseTax = firebaseSubtotal * 0.13; // Calculate 13% tax
  const firebaseTotal = firebaseSubtotal + firebaseTax;
  
  // Use Firebase values if available, otherwise fall back to calculated values
  const displaySubtotal = firebaseSubtotal;
  const displayTax = firebaseTax;
  const displayTotal = firebaseTotal;
  
  console.log('Checkout - Firebase totalPrice:', firebaseTotalPrice);
  console.log('Checkout - Display Subtotal:', displaySubtotal);
  console.log('Checkout - Display Tax:', displayTax);
  console.log('Checkout - Display Total:', displayTotal);

  /**
   * Stripe payment processing with Payment Sheet
   */
  const handlePayment = async () => {
    if (isProcessingPayment) return;
    
    setIsProcessingPayment(true);
    
    try {
      console.warn('🔴 handlePayment: Starting Stripe payment process');
      
      // Calculate amount in cents
      const amountInCents = Math.round(displayTotal * 100);
      
      // Create payment intent on backend
      const paymentIntentResponse = await fetch(`http://${LOCAL_IP}:5001/api/create-payment-intent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount: amountInCents,
          session_id: sessionId,
        }),
      });
      
      if (!paymentIntentResponse.ok) {
        throw new Error('Failed to create payment intent');
      }
      
      const { clientSecret, paymentIntentId } = await paymentIntentResponse.json() as { 
        clientSecret: string; 
        paymentIntentId: string; 
      };
      console.log('Payment intent created:', paymentIntentId);
      
      // Initialize Stripe Payment Sheet
      const { error: initError } = await initPaymentSheet({
        paymentIntentClientSecret: clientSecret,
        merchantDisplayName: 'DeltaHacks Store',
        returnURL: 'deltahacks://payment-success',
      });
      
      if (initError) {
        console.error('Payment sheet init error:', initError);
        Alert.alert('Error', initError.message);
        setIsProcessingPayment(false);
        return;
      }
      
      // Present the Payment Sheet
      const { error: presentError } = await presentPaymentSheet();
      
      if (presentError) {
        console.error('Payment sheet present error:', presentError);
        Alert.alert('Payment Canceled', presentError.message);
        setIsProcessingPayment(false);
        return;
      }
      
      // Payment successful!
      await processPaymentSuccess();
      
    } catch (error) {
      console.error('❌ handlePayment: Error:', error);
      setIsProcessingPayment(false);
      Alert.alert('Payment Error', 'Failed to process payment. Please try again.');
    }
  };
  
  const processPaymentSuccess = async () => {
    try {
      // Call backend to stop webcam and mark session as completed
      if (sessionId) {
        const checkoutUrl = `http://${LOCAL_IP}:5001/api/sessions/${sessionId}/checkout`;
        const response = await fetch(checkoutUrl, { method: 'PUT' });
        if (response.ok) {
          console.warn('✅ Session checkout complete');
        }
      }
      
      // Show success and navigate
      Alert.alert(
        'Payment Successful!',
        `Your order of ${formatPrice(displayTotal)} has been processed.`,
        [
          {
            text: 'OK',
            onPress: () => {
              clearCart();
              setSessionId(null);
              setIsProcessingPayment(false);
              router.push("/(tabs)");
            },
          },
        ]
      );
    } catch (error) {
      console.error('Error:', error);
      setIsProcessingPayment(false);
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

          {products.length === 0 ? (
            <ThemedText style={styles.emptyText}>No items in cart</ThemedText>
          ) : (
            products.map((product) => {
              console.log('Checkout product:', product.name, 'price:', product.price, 'quantity:', product.quantity);
              return (
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
              );
            })
          )}
        </View>

        <View style={styles.section}>
          <View style={styles.summaryRow}>
            <ThemedText>Subtotal:</ThemedText>
            <ThemedText>{formatPrice(displaySubtotal)}</ThemedText>
          </View>

          <View style={styles.summaryRow}>
            <ThemedText>Tax (13%):</ThemedText>
            <ThemedText>{formatPrice(displayTax)}</ThemedText>
          </View>

          <View style={[styles.summaryRow, styles.totalRow]}>
            <ThemedText type="defaultSemiBold" style={styles.totalLabel}>
              Total:
            </ThemedText>
            <ThemedText type="defaultSemiBold" style={styles.totalAmount}>
              {formatPrice(displayTotal)}
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
          style={[styles.paymentButton, isProcessingPayment && styles.paymentButtonDisabled]}
          onPress={handlePayment}
          disabled={isProcessingPayment}
          activeOpacity={0.7}>
          {isProcessingPayment ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <ThemedText style={styles.paymentButtonText}>
              Proceed with Payment
            </ThemedText>
          )}
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
  paymentButtonDisabled: {
    opacity: 0.6,
  },
  paymentButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  emptyText: {
    textAlign: 'center',
    fontSize: 16,
    opacity: 0.6,
    padding: 20,
  },
});

