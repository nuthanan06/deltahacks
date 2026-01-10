import { StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useState } from 'react';
import { useRouter } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';

/**
 * NFC Scan Start Screen
 * 
 * This is the entry screen where users can tap a button to scan an NFC chip.
 * When the scan succeeds, the app navigates to the scanned products screen.
 * 
 * TODO: Replace mockNfcScan with actual NFC scanning implementation:
 * - Use expo-nfc-manager or similar library
 * - Handle NFC permissions
 * - Process NFC tag data
 * - Trigger product recognition via backend API
 */
export default function NFCScanScreen() {
  const router = useRouter();
  const { addProduct } = useCart();
  const [isScanning, setIsScanning] = useState(false);

  /**
   * Mock NFC scan function
   * 
   * TODO: Replace with real NFC scanning logic
   * 1. Request NFC permissions
   * 2. Start NFC scan session
   * 3. Read NFC tag data
   * 4. Send tag data to backend for product recognition
   * 5. Backend returns product info (name, price, etc.)
   */
  const mockNfcScan = async (): Promise<void> => {
    setIsScanning(true);
    
    // Simulate NFC scan delay (1-2 seconds)
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Mock NFC scan result - in real app, this would come from:
    // 1. NFC tag read
    // 2. Backend API call for product recognition
    // 3. Firebase lookup for pricing
    const mockProductData = {
      id: `product-${Date.now()}`,
      name: 'Organic Bananas',
      price: 4.99,
      quantity: 1,
    };

    // Add product to cart (would come from Firebase/backend in real app)
    addProduct(mockProductData);

    setIsScanning(false);
    
    // Navigate to scanned products screen
    router.push('/(tabs)/products');
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedView style={styles.content}>
        <ThemedText type="title" style={styles.title}>
          NFC Scanner
        </ThemedText>
        
        <ThemedText style={styles.description}>
          Tap the button below to scan an NFC chip and add products to your cart.
        </ThemedText>

        <TouchableOpacity
          style={[styles.scanButton, isScanning && styles.scanButtonDisabled]}
          onPress={mockNfcScan}
          disabled={isScanning}
          activeOpacity={0.7}>
          {isScanning ? (
            <>
              <ActivityIndicator color="#fff" style={styles.loader} />
              <ThemedText style={styles.scanButtonText}>Scanning...</ThemedText>
            </>
          ) : (
            <ThemedText style={styles.scanButtonText}>Scan NFC Chip</ThemedText>
          )}
        </TouchableOpacity>

        <ThemedText style={styles.note}>
          Note: This is a mock implementation. Real NFC scanning will be integrated here.
        </ThemedText>
      </ThemedView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  title: {
    marginBottom: 20,
    textAlign: 'center',
  },
  description: {
    textAlign: 'center',
    marginBottom: 40,
    paddingHorizontal: 20,
    fontSize: 16,
    lineHeight: 24,
  },
  scanButton: {
    backgroundColor: '#0a7ea4',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 8,
    minWidth: 200,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  scanButtonDisabled: {
    opacity: 0.6,
  },
  scanButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  loader: {
    marginRight: 10,
  },
  note: {
    marginTop: 30,
    fontSize: 12,
    opacity: 0.6,
    textAlign: 'center',
    paddingHorizontal: 20,
  },
});

