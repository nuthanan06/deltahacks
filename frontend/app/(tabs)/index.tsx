import { StyleSheet, TouchableOpacity, Modal, View, Alert, Text, ActivityIndicator, Platform } from 'react-native';
import { useState, useRef } from 'react';
import { useRouter } from 'expo-router';
import { Image } from 'expo-image';
import { CameraView, useCameraPermissions } from 'expo-camera';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';
import { API_BASE_URL } from '@/config/api';

/**
 * QR Code Cart Pairing Screen
 * 
 * Users can either:
 * - "I'm a cart" - Generate a QR code for pairing
 * - "I'm a phone" - Scan a QR code to pair with a cart
 * 
 * Note: Requires the following packages to be installed:
 * - expo-camera (for QR code scanning)
 * - react-native-svg (for QR code display)
 * - react-native-qrcode-svg (optional, for better QR code generation)
 * 
 * Install with: npx expo install expo-camera react-native-svg
 */
export default function QRCodeScreen() {
  const router = useRouter();
  const { addProduct, sessionId, setSessionId } = useCart();
  const [isScanning, setIsScanning] = useState(false);
  const [showQRCode, setShowQRCode] = useState(false);
  const [qrCodeData, setQrCodeData] = useState<string>('');
  const [qrCodeImageUri, setQrCodeImageUri] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessingScan, setIsProcessingScan] = useState(false);
  const [lastScannedId, setLastScannedId] = useState<string>('');
  const alertShownRef = useRef<string>(''); // Track which session ID we've shown alert for
  const [permission, requestPermission] = useCameraPermissions();

  const handleImACart = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Step 1: Create a new session
      const createResponse = await fetch(`${API_BASE_URL}/api/sessions/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

      if (!createResponse.ok) {
        throw new Error(`Failed to create session: ${createResponse.statusText}`);
      }

      const sessionData = await createResponse.json() as { session_id: string };
      const newSessionId = sessionData.session_id;
      setSessionId(newSessionId); // Store in context

      // Step 2: Fetch the QR code for this session
      const qrResponse = await fetch(
        `${API_BASE_URL}/api/sessions/${newSessionId}/qrcode?format=base64`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!qrResponse.ok) {
        throw new Error(`Failed to generate QR code: ${qrResponse.statusText}`);
      }

      const qrData = await qrResponse.json() as { qr_code: string; session_id: string };
      
      // The API returns the QR code as a base64 data URL
      setQrCodeImageUri(qrData.qr_code);
      setQrCodeData(newSessionId);
      setShowQRCode(true);

      // Webcam will be started by the cart device after phone pairs
    } catch (error) {
      console.error('Error creating session or fetching QR code:', error);
      Alert.alert(
        'Error',
        `Failed to generate QR code: ${error instanceof Error ? error.message : 'Unknown error'}\n\nMake sure the backend server is running on ${API_BASE_URL}`,
        [{ text: 'OK' }]
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleImAPhone = async (): Promise<void> => {
    // Check camera permissions
    if (!permission) {
      // Permission status is still loading
      return;
    }

    if (!permission.granted) {
      // Request camera permission
      const { granted } = await requestPermission();
      if (!granted) {
        Alert.alert(
          'Camera Permission Required',
          'Please allow camera access to scan QR codes.',
          [{ text: 'OK' }]
        );
        return;
      }
    }

    // Permission granted, start scanning
    setIsScanning(true);
  };


  const handleBarCodeScanned = async ({ data }: { data: string }): Promise<void> => {
    // Prevent multiple scans of the same QR code
    const scannedSessionId = data.trim();
    
    if (!scannedSessionId) {
      return;
    }

    // If we're already processing, ignore all scans
    if (isProcessingScan) {
      return;
    }

    // If this is the same session ID we just scanned, ignore it
    if (lastScannedId === scannedSessionId) {
      return;
    }

    // If we've already shown an alert for this session ID, ignore it
    if (alertShownRef.current === scannedSessionId) {
      return;
    }

    // Mark as processing IMMEDIATELY to prevent duplicate calls
    setIsProcessingScan(true);
    setLastScannedId(scannedSessionId);
    alertShownRef.current = scannedSessionId; // Mark that we're processing this ID
    setIsScanning(false);

    try {
      // Pair with the cart session using session_id
      const pairResponse = await fetch(`${API_BASE_URL}/api/pair`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: scannedSessionId,
        }),
      });

      if (!pairResponse.ok) {
        const errorData = await pairResponse.json().catch(() => ({})) as { error?: string };
        throw new Error(errorData.error || `Pairing failed: ${pairResponse.statusText}`);
      }

      const pairData = await pairResponse.json() as {
        status: string;
        session_id: string;
      };

      // Success! Show confirmation and navigate
      // The alertShownRef ensures we only show this once per session ID
      Alert.alert(
        'Successfully Paired!',
        `Connected to cart session: ${pairData.session_id}\n\nYou can now add items to your cart.`,
        [
          {
            text: 'OK',
            onPress: () => {
              console.log('Paired session:', pairData);
              // Set sessionId RIGHT BEFORE navigation to ensure it's in state
              console.log('handleBarCodeScanned: Setting sessionId to:', pairData.session_id);
              setSessionId(pairData.session_id);
              // Small delay to allow state to update before navigation
              setTimeout(() => {
                // Navigate to camera screen to start streaming frames
                router.push(`/(tabs)/camera?sessionId=${pairData.session_id}`);
              }, 100);
              // Reset processing state after navigation
              setTimeout(() => {
                setIsProcessingScan(false);
                // Keep the ref for a bit longer to prevent re-scanning
                setTimeout(() => {
                  alertShownRef.current = '';
                  setLastScannedId('');
                }, 5000);
              }, 1000);
            },
          },
        ]
      );
    } catch (error) {
      console.error('Error pairing with cart:', error);
      // Reset ref on error so user can retry
      alertShownRef.current = '';
      Alert.alert(
        'Pairing Failed',
        error instanceof Error ? error.message : 'Failed to pair with cart. Please try again.',
        [
          {
            text: 'OK',
            onPress: () => {
              // Reset processing state so user can try again
              setIsProcessingScan(false);
              setLastScannedId('');
            },
          },
        ]
      );
    }
  };

  // Render QR code from API (base64 image)
  const renderQRCode = () => {
    if (isLoading) {
      return (
        <View style={styles.qrCodeContainer}>
          <ActivityIndicator size="large" color="#0a7ea4" />
          <ThemedText style={styles.loadingText}>Generating QR code...</ThemedText>
        </View>
      );
    }

    if (qrCodeImageUri) {
      return (
        <Image
          source={{ uri: qrCodeImageUri }}
          style={styles.qrCodeImage}
          contentFit="contain"
        />
      );
    }

    // Fallback if no QR code available
    return (
      <View style={styles.qrCodeFallback}>
        <Text style={styles.qrCodeFallbackText} selectable>
          {sessionId || qrCodeData}
        </Text>
        <ThemedText style={styles.fallbackNote}>
          QR code not available
        </ThemedText>
      </View>
    );
  };

  // Render camera scanner
  const renderScanner = () => {
    if (!permission) {
      // Permission status is still loading
      return (
        <View style={styles.cameraFallback}>
          <ActivityIndicator size="large" color="#fff" />
          <ThemedText style={styles.cameraFallbackText}>
            Checking camera permissions...
          </ThemedText>
        </View>
      );
    }

    if (!permission.granted) {
      return (
        <View style={styles.cameraFallback}>
          <ThemedText style={styles.cameraFallbackText}>
            Camera permission is required to scan QR codes.
          </ThemedText>
          <TouchableOpacity
            style={styles.permissionButton}
            onPress={requestPermission}>
            <ThemedText style={styles.permissionButtonText}>
              Grant Camera Permission
            </ThemedText>
          </TouchableOpacity>
        </View>
      );
    }

    return (
      <CameraView
        style={styles.camera}
        facing="back"
        onBarcodeScanned={isScanning && !isProcessingScan ? handleBarCodeScanned : undefined}
        barcodeScannerSettings={{
          barcodeTypes: ['qr'],
        }}>
        <View style={styles.scannerOverlay}>
          <ThemedText style={styles.scannerText}>
            {isProcessingScan ? 'Processing...' : 'Point your camera at the QR code'}
          </ThemedText>
          <View style={styles.scannerFrame} />
        </View>
      </CameraView>
    );
  };

  return (
    <ThemedView style={styles.container}>
      <ThemedView style={styles.content}>
        <ThemedText type="title" style={styles.title}>
          Cart Pairing
        </ThemedText>
        
        <ThemedText style={styles.description}>
          Choose your role to pair a phone with a shopping cart using QR codes.
        </ThemedText>

        <TouchableOpacity
          style={[styles.button, styles.cartButton, isLoading && styles.buttonDisabled]}
          onPress={handleImACart}
          disabled={isLoading}
          activeOpacity={0.7}>
          {isLoading ? (
            <>
              <ActivityIndicator color="#fff" style={styles.buttonLoader} />
              <ThemedText style={styles.buttonText}>Generating...</ThemedText>
            </>
          ) : (
            <ThemedText style={styles.buttonText}>I&apos;m a cart</ThemedText>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.phoneButton]}
          onPress={handleImAPhone}
          activeOpacity={0.7}>
          <ThemedText style={styles.buttonText}>I&apos;m a phone</ThemedText>
        </TouchableOpacity>
      </ThemedView>

      {/* QR Code Display Modal */}
      <Modal
        visible={showQRCode}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowQRCode(false)}>
        <View style={styles.modalContainer}>
          <ThemedView style={styles.modalContent}>
            <ThemedText type="title" style={styles.modalTitle}>
              Scan this QR code
            </ThemedText>
            <View style={styles.qrCodeContainer}>
              {renderQRCode()}
            </View>
            <ThemedText style={styles.qrCodeText}>
              Session ID: {sessionId || qrCodeData || 'N/A'}
            </ThemedText>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setShowQRCode(false)}>
              <ThemedText style={styles.closeButtonText}>Close</ThemedText>
            </TouchableOpacity>
          </ThemedView>
        </View>
      </Modal>

      {/* QR Code Scanner Modal */}
      <Modal
        visible={isScanning}
        animationType="slide"
        onRequestClose={() => setIsScanning(false)}>
        <View style={styles.scannerContainer}>
          {renderScanner()}
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={() => setIsScanning(false)}>
            <ThemedText style={styles.cancelButtonText}>Cancel</ThemedText>
          </TouchableOpacity>
        </View>
      </Modal>
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
    backgroundColor: '#505066', //BASE COLOR
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
  button: {
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 8,
    minWidth: 200,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 10,
  },
  cartButton: {
    backgroundColor: '#069e66',
  },
  phoneButton: {
    backgroundColor: '#eda70e',
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonLoader: {
    marginRight: 10,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 24,
    alignItems: 'center',
    minWidth: 300,
    maxWidth: '90%',
  },
  modalTitle: {
    marginBottom: 20,
    textAlign: 'center',
  },
  qrCodeContainer: {
    backgroundColor: '#fff',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 200,
    minWidth: 200,
  },
  qrCodeImage: {
    width: 300,
    height: 300,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 14,
    color: '#666',
  },
  qrCodeFallback: {
    padding: 20,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    alignItems: 'center',
  },
  qrCodeFallbackText: {
    fontSize: 14,
    fontFamily: 'monospace',
    textAlign: 'center',
    marginBottom: 10,
  },
  fallbackNote: {
    fontSize: 10,
    color: '#666',
    fontStyle: 'italic',
  },
  qrCodeText: {
    marginTop: 10,
    fontSize: 12,
    textAlign: 'center',
    color: '#666',
  },
  closeButton: {
    marginTop: 20,
    paddingVertical: 12,
    paddingHorizontal: 24,
    backgroundColor: '#0a7ea4',
    borderRadius: 8,
  },
  closeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  scannerContainer: {
    flex: 1,
  },
  camera: {
    flex: 1,
  },
  cameraFallback: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000',
    padding: 20,
  },
  cameraFallbackText: {
    color: '#fff',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
  cameraFallbackCommand: {
    color: '#0a7ea4',
    fontSize: 14,
    fontFamily: 'monospace',
    textAlign: 'center',
  },
  permissionButton: {
    marginTop: 20,
    paddingVertical: 12,
    paddingHorizontal: 24,
    backgroundColor: '#0a7ea4',
    borderRadius: 8,
  },
  permissionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  scannerOverlay: {
    flex: 1,
    backgroundColor: 'transparent',
    justifyContent: 'center',
    alignItems: 'center',
  },
  scannerText: {
    color: '#fff',
    fontSize: 18,
    marginBottom: 30,
    textAlign: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    padding: 10,
    borderRadius: 8,
  },
  scannerFrame: {
    width: 250,
    height: 250,
    borderWidth: 2,
    borderColor: '#0a7ea4',
    borderRadius: 10,
  },
  cancelButton: {
    position: 'absolute',
    bottom: 40,
    left: '50%',
    marginLeft: -75,
    paddingVertical: 12,
    paddingHorizontal: 24,
    backgroundColor: '#dc3545',
    borderRadius: 8,
    minWidth: 150,
    alignItems: 'center',
  },
  cancelButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
