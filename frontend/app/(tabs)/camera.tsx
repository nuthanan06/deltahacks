import { StyleSheet, View, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useState, useEffect, useRef } from 'react';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useCart } from '@/contexts/CartContext';
import { API_BASE_URL } from '@/config/api';

/**
 * Camera Screen
 * 
 * Continuously captures frames from phone camera and sends them to backend
 * for object detection and cart tracking.
 */
export default function CameraScreen() {
  const router = useRouter();
  const { sessionId: paramSessionId } = useLocalSearchParams<{ sessionId?: string }>();
  const { sessionId: contextSessionId } = useCart();
  const sessionId = paramSessionId || contextSessionId;
  
  const [permission, requestPermission] = useCameraPermissions();
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const cameraRef = useRef<CameraView>(null);
  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastFrameTimeRef = useRef<number>(0);
  const frameCountRef = useRef<number>(0);
  const isCapturingRef = useRef<boolean>(false);

  // Frame capture rate: send 1 frame every ~200ms (5 FPS to reduce bandwidth)
  const FRAME_INTERVAL_MS = 200;

  useEffect(() => {
    if (sessionId && permission?.granted && cameraReady) {
      startStreaming();
    }

    return () => {
      stopStreaming();
    };
  }, [sessionId, permission?.granted, cameraReady]);

  const startStreaming = () => {
    if (!sessionId) {
      setError('No session ID available');
      return;
    }

    if (!permission?.granted) {
      setError('Camera permission not granted');
      return;
    }

    setIsStreaming(true);
    setError(null);
    frameCountRef.current = 0;
    lastFrameTimeRef.current = Date.now();

    // Start capturing frames periodically
    captureAndSendFrame();
  };

  const stopStreaming = () => {
    setIsStreaming(false);
    if (frameIntervalRef.current) {
      clearTimeout(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  };

  const captureAndSendFrame = async () => {
    if (!isStreaming || !sessionId || !cameraRef.current || isCapturingRef.current || !cameraReady) {
      if (!cameraReady) {
        console.log('Camera not ready yet, waiting...');
      }
      // Schedule retry
      frameIntervalRef.current = setTimeout(captureAndSendFrame, FRAME_INTERVAL_MS);
      return;
    }

    try {
      const now = Date.now();
      const timeSinceLastFrame = now - lastFrameTimeRef.current;

      if (timeSinceLastFrame < FRAME_INTERVAL_MS) {
        // Schedule next frame capture
        frameIntervalRef.current = setTimeout(captureAndSendFrame, FRAME_INTERVAL_MS - timeSinceLastFrame);
        return;
      }

      isCapturingRef.current = true;

      // Take a picture using the camera ref
      // CameraView in expo-camera v17 exposes takePictureAsync through the ref
      let photo = null;
      const camera = cameraRef.current as any;
      
      // Try accessing takePictureAsync directly
      if (camera && typeof camera.takePictureAsync === 'function') {
        console.log('Using takePictureAsync from ref directly');
        photo = await camera.takePictureAsync({
          quality: 0.5,
          base64: true,
          skipProcessing: false,
        });
      } 
      // Try accessing through a method call
      else if (camera && camera.current && typeof camera.current.takePictureAsync === 'function') {
        console.log('Using takePictureAsync from ref.current');
        photo = await camera.current.takePictureAsync({
          quality: 0.5,
          base64: true,
          skipProcessing: false,
        });
      }
      // Try calling as a method if it exists
      else if (camera && 'takePictureAsync' in camera) {
        console.log('Found takePictureAsync property, calling...');
        const takePicture = camera.takePictureAsync;
        if (typeof takePicture === 'function') {
          photo = await takePicture({
            quality: 0.5,
            base64: true,
            skipProcessing: false,
          });
        } else {
          throw new Error('takePictureAsync exists but is not a function');
        }
      } else {
        // Log available methods for debugging
        console.log('Camera ref:', camera);
        console.log('Camera ref type:', typeof camera);
        console.log('Camera ref keys:', camera ? Object.keys(camera) : 'null');
        throw new Error('takePictureAsync not available on camera ref. Available methods: ' + (camera ? Object.keys(camera).join(', ') : 'none'));
      }

      isCapturingRef.current = false;

      if (photo && photo.base64) {
        // Send frame to backend
        await sendFrameToBackend(photo.base64);
        frameCountRef.current += 1;
        lastFrameTimeRef.current = Date.now();
        console.log(`Frame ${frameCountRef.current} sent successfully`);
      } else {
        console.warn('Photo captured but no base64 data');
      }

      // Schedule next frame capture
      frameIntervalRef.current = setTimeout(captureAndSendFrame, FRAME_INTERVAL_MS);
    } catch (err) {
      isCapturingRef.current = false;
      const errorMessage = err instanceof Error ? err.message : String(err);
      console.error('Error capturing frame:', errorMessage);
      setError(`Capture error: ${errorMessage}`);
      // Continue trying even if one frame fails
      frameIntervalRef.current = setTimeout(captureAndSendFrame, FRAME_INTERVAL_MS);
    }
  };

  const sendFrameToBackend = async (base64Image: string) => {
    if (!sessionId) {
      console.warn('No sessionId for sending frame');
      return;
    }

    try {
      const url = `${API_BASE_URL}/api/sessions/${sessionId}/frame`;
      console.log('Sending frame to:', url);
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image: `data:image/jpeg;base64,${base64Image}`,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.warn('Frame send failed:', response.status, errorData);
        setError(`Send failed: ${response.status} - ${JSON.stringify(errorData)}`);
      } else {
        const data = await response.json().catch(() => ({}));
        console.log('Frame sent successfully:', data);
        setError(null); // Clear error on success
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      console.error('Error sending frame to backend:', errorMessage);
      setError(`Network error: ${errorMessage}`);
    }
  };

  const handleBackPress = () => {
    stopStreaming();
    router.back();
  };

  if (!permission) {
    return (
      <ThemedView style={styles.container}>
        <ActivityIndicator size="large" />
        <ThemedText style={styles.statusText}>Checking camera permissions...</ThemedText>
      </ThemedView>
    );
  }

  if (!permission.granted) {
    return (
      <ThemedView style={styles.container}>
        <ThemedText style={styles.statusText}>Camera permission is required</ThemedText>
        <TouchableOpacity style={styles.button} onPress={requestPermission}>
          <ThemedText style={styles.buttonText}>Grant Permission</ThemedText>
        </TouchableOpacity>
      </ThemedView>
    );
  }

  if (!sessionId) {
    return (
      <ThemedView style={styles.container}>
        <ThemedText style={styles.statusText}>No session ID available</ThemedText>
        <TouchableOpacity style={styles.button} onPress={() => router.push('/(tabs)/')}>
          <ThemedText style={styles.buttonText}>Go to Pairing</ThemedText>
        </TouchableOpacity>
      </ThemedView>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing="back"
        onCameraReady={() => {
          console.log('Camera is ready');
          setCameraReady(true);
          // Log camera ref to see what's available
          setTimeout(() => {
            const camera = cameraRef.current as any;
            console.log('Camera ref after ready:', camera);
            console.log('Camera ref methods:', camera ? Object.keys(camera) : 'null');
            if (camera) {
              console.log('takePictureAsync exists:', 'takePictureAsync' in camera);
              console.log('typeof takePictureAsync:', typeof camera.takePictureAsync);
            }
          }, 1000);
        }}>
        <View style={styles.overlay}>
          <View style={styles.header}>
            <ThemedText style={styles.headerText}>
              Cart Tracking Active
            </ThemedText>
            {isStreaming && (
              <ThemedText style={styles.statusText}>
                Frames sent: {frameCountRef.current}
              </ThemedText>
            )}
          </View>
          
          {error && (
            <View style={styles.errorContainer}>
              <ThemedText style={styles.errorText}>{error}</ThemedText>
            </View>
          )}

          <View style={styles.footer}>
            <TouchableOpacity
              style={styles.testButton}
              onPress={async () => {
                console.log('Manual test capture triggered');
                try {
                  const camera = cameraRef.current as any;
                  console.log('Camera ref:', camera);
                  console.log('Camera methods:', camera ? Object.keys(camera) : 'null');
                  if (camera && typeof camera.takePictureAsync === 'function') {
                    const photo = await camera.takePictureAsync({ quality: 0.5, base64: true });
                    console.log('Test capture successful:', photo ? 'yes' : 'no');
                    if (photo?.base64) {
                      await sendFrameToBackend(photo.base64);
                      frameCountRef.current += 1;
                    }
                  } else {
                    console.error('takePictureAsync not available');
                    setError('takePictureAsync not available on camera ref');
                  }
                } catch (err) {
                  console.error('Test capture error:', err);
                  setError(`Test error: ${err instanceof Error ? err.message : String(err)}`);
                }
              }}>
              <ThemedText style={styles.testButtonText}>Test Capture</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.productsButton}
              onPress={() => router.push('/(tabs)/products')}>
              <ThemedText style={styles.productsButtonText}>View Cart</ThemedText>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.backButton}
              onPress={handleBackPress}>
              <ThemedText style={styles.backButtonText}>Back</ThemedText>
            </TouchableOpacity>
          </View>
        </View>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  camera: {
    flex: 1,
  },
  overlay: {
    flex: 1,
    backgroundColor: 'transparent',
    justifyContent: 'space-between',
  },
  header: {
    paddingTop: 60,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  headerText: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
    textAlign: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    padding: 10,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 14,
    color: '#fff',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    padding: 8,
    borderRadius: 6,
  },
  errorContainer: {
    backgroundColor: 'rgba(220, 53, 69, 0.8)',
    padding: 12,
    marginHorizontal: 20,
    borderRadius: 8,
  },
  errorText: {
    color: '#fff',
    textAlign: 'center',
  },
  footer: {
    paddingBottom: 40,
    paddingHorizontal: 20,
    alignItems: 'center',
    gap: 12,
  },
  testButton: {
    backgroundColor: '#eda70e',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    minWidth: 120,
    marginBottom: 8,
  },
  testButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  productsButton: {
    backgroundColor: '#069e66',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    minWidth: 120,
    marginBottom: 8,
  },
  productsButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  backButton: {
    backgroundColor: '#dc3545',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    minWidth: 120,
  },
  backButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  button: {
    backgroundColor: '#0a7ea4',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginTop: 20,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
