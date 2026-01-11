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
  const frameIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastFrameTimeRef = useRef<number>(0);
  const frameCountRef = useRef<number>(0);
  const isCapturingRef = useRef<boolean>(false);
  const isMountedRef = useRef<boolean>(true);
  const isStreamingRef = useRef<boolean>(false); // Use ref to avoid stale closure

  // Frame capture rate: Cap to realistic max to avoid queueing promises
  const TARGET_FPS = 12;
  const FRAME_INTERVAL_MS = 1000 / TARGET_FPS;

  useEffect(() => {
    isMountedRef.current = true;
    
    if (sessionId && permission?.granted && cameraReady) {
      // Try to ensure webcam is started, but don't block on it
      // The backend will auto-start when frames arrive if needed
      ensureWebcamStarted().catch((err) => {
        console.warn('Webcam start check failed, will rely on auto-start:', err);
      });
      
      // Start streaming after a short delay regardless
      // The backend auto-starts webcam when frames arrive
      setTimeout(() => {
        if (isMountedRef.current) {
          startStreaming();
        }
      }, 500);
    }

    return () => {
      isMountedRef.current = false;
      stopStreaming();
    };
  }, [sessionId, permission?.granted, cameraReady]);

  const ensureWebcamStarted = async (): Promise<void> => {
    if (!sessionId) {
      return;
    }
    
    // Try to start webcam, but don't fail if it doesn't work
    // The backend will auto-start when frames arrive
    try {
      const startResponse = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/start-webcam`, {
        method: 'POST',
      });
      
      if (startResponse.ok) {
        const contentType = startResponse.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const startData = await startResponse.json().catch(() => ({}));
          console.log('Webcam start response:', startData);
        } else {
          console.log('Webcam start request succeeded (non-JSON response)');
        }
      } else {
        // Not a critical error - backend will auto-start when frames arrive
        console.log('Webcam start request returned:', startResponse.status, '(will rely on auto-start)');
      }
    } catch (err) {
      // Not a critical error - backend will auto-start when frames arrive
      console.log('Webcam start request failed (will rely on auto-start):', err);
    }
  };

  const startStreaming = () => {
    if (!sessionId) {
      setError('No session ID available');
      return;
    }

    if (!permission?.granted) {
      setError('Camera permission not granted');
      return;
    }

    if (!cameraReady) {
      console.log('Camera not ready, waiting...');
      return;
    }

    console.log('Starting frame streaming...');
    setIsStreaming(true);
    isStreamingRef.current = true; // Update ref immediately
    setError(null);
    frameCountRef.current = 0;
    lastFrameTimeRef.current = Date.now();

    // Start capturing frames periodically
    console.log('Calling captureAndSendFrame to start loop...');
    captureAndSendFrame();
  };

  const stopStreaming = () => {
    console.log('Stopping frame streaming...');
    setIsStreaming(false);
    isStreamingRef.current = false; // Update ref
    isCapturingRef.current = false;
    if (frameIntervalRef.current) {
      clearTimeout(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  };

  const captureAndSendFrame = async () => {
    // Check if component is still mounted
    if (!isMountedRef.current) {
      console.log('Component unmounted, stopping frame capture');
      return;
    }

    // Use ref for isStreaming to avoid stale closure issues
    if (!isStreamingRef.current || !sessionId || !cameraRef.current || isCapturingRef.current || !cameraReady) {
      if (!isStreamingRef.current) {
        console.log('Streaming not active, stopping capture loop');
        return;
      }
      if (!cameraReady) {
        console.log('Camera not ready yet, retrying in', FRAME_INTERVAL_MS, 'ms...');
      }
      if (isCapturingRef.current) {
        console.log('Already capturing, skipping this cycle');
      }
      // Schedule retry with frame interval
      if (isMountedRef.current && isStreamingRef.current) {
        frameIntervalRef.current = setTimeout(captureAndSendFrame, FRAME_INTERVAL_MS) as ReturnType<typeof setTimeout>;
      }
      return;
    }

    try {
      const now = Date.now();
      const timeSinceLastFrame = now - lastFrameTimeRef.current;

      // Skip the time check for faster capture - just capture immediately
      // The interval will naturally throttle if capture takes too long
      // Update last frame time to current time
      lastFrameTimeRef.current = now;

      // Double-check camera ref is still valid
      if (!cameraRef.current || !isMountedRef.current) {
        console.log('Camera ref invalid or component unmounted, stopping');
        return;
      }

      isCapturingRef.current = true;

      // Take a picture using the camera ref
      // CameraView in expo-camera v17 exposes takePictureAsync through the ref
      let photo = null;
      const camera = cameraRef.current as any;
      
      // Check again if camera is still valid
      if (!camera || !isMountedRef.current) {
        isCapturingRef.current = false;
        return;
      }
      
      // Try accessing takePictureAsync - CameraView exposes it directly
      let captureMethod = null;
      
      if (camera && typeof camera.takePictureAsync === 'function') {
        captureMethod = camera.takePictureAsync.bind(camera);
      } 
      // Try accessing through _cameraRef if it exists
      else if (camera && camera._cameraRef) {
        const nativeRef = camera._cameraRef.current || camera._cameraRef;
        if (nativeRef && typeof nativeRef.takePictureAsync === 'function') {
          captureMethod = nativeRef.takePictureAsync.bind(nativeRef);
        }
      }
      
      if (!captureMethod) {
        console.error('takePictureAsync not found on camera ref');
        console.log('Camera ref keys:', camera ? Object.keys(camera) : 'null');
        throw new Error('takePictureAsync not available on camera ref');
      }
      
      // Capture photo without base64 - much faster! Get URI for binary JPEG
      photo = await captureMethod({
        quality: 0.15, // Lower quality for speed
        base64: false, // No base64 encoding - much faster!
        skipProcessing: true, // Skip processing for speed
      });

      isCapturingRef.current = false;

      // Send binary JPEG immediately if we have URI
      if (photo?.uri && isMountedRef.current && isStreamingRef.current) {
        // Fire and forget - don't await for maximum speed
        sendFrameToBackend(photo.uri).catch(() => {});
        frameCountRef.current += 1;
        lastFrameTimeRef.current = Date.now();
      }

      // Schedule next frame capture with frame interval
      if (isMountedRef.current && isStreamingRef.current) {
        frameIntervalRef.current = setTimeout(captureAndSendFrame, FRAME_INTERVAL_MS) as ReturnType<typeof setTimeout>;
      } else {
        console.log('Stopping capture loop - mounted:', isMountedRef.current, 'streaming:', isStreamingRef.current);
      }
    } catch (err) {
      isCapturingRef.current = false;
      const errorMessage = err instanceof Error ? err.message : String(err);
      
      // Don't log "camera unmounted" as an error - it's expected during navigation
      if (errorMessage.includes('unmounted') || errorMessage.includes('unmount')) {
        console.log('Camera unmounted during capture (expected during navigation)');
        return;
      }
      
      console.error('Error capturing frame:', errorMessage);
      if (isMountedRef.current && isStreamingRef.current) {
        setError(`Capture error: ${errorMessage}`);
        // Continue with frame interval on error
        frameIntervalRef.current = setTimeout(captureAndSendFrame, FRAME_INTERVAL_MS) as ReturnType<typeof setTimeout>;
      } else {
        console.log('Stopping capture loop after error - mounted:', isMountedRef.current, 'streaming:', isStreamingRef.current);
      }
    }
  };

  const sendFrameToBackend = async (imageUri: string) => {
    // Send binary JPEG - much faster than base64!
    if (!sessionId) return;
    
    // In React Native, use FormData for binary upload
    // React Native will automatically set Content-Type with boundary
    const formData = new FormData();
    formData.append('image', {
      uri: imageUri,
      type: 'image/jpeg',
      name: 'frame.jpg',
    } as any);
    
    // Send binary JPEG via FormData - React Native handles binary encoding
    // Don't set Content-Type header - React Native sets it automatically with boundary
    fetch(`${API_BASE_URL}/api/sessions/${sessionId}/frame`, {
      method: 'POST',
      body: formData,
    } as any).catch(() => {}); // Ignore errors for speed
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
        <TouchableOpacity style={styles.button} onPress={() => router.push('/(tabs)' as any)}>
          <ThemedText style={styles.buttonText}>Go to Pairing</ThemedText>
        </TouchableOpacity>
      </ThemedView>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView

        ratio="16:9"
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
              if (camera._cameraRef) {
                console.log('_cameraRef exists:', !!camera._cameraRef);
                console.log('_cameraRef.current:', camera._cameraRef.current ? 'exists' : 'null');
              }
            }
          }, 1000);
        }}>
        {/* Use absolute positioning to avoid children warning */}
        <View style={StyleSheet.absoluteFill}>
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
                if (!isMountedRef.current || !cameraRef.current) {
                  setError('Camera not ready');
                  return;
                }
                
                try {
                  const camera = cameraRef.current as any;
                  
                  if (!camera) {
                    setError('Camera ref is null');
                    return;
                  }
                  
                  let captureMethod = camera?.takePictureAsync || camera?._cameraRef?.current?.takePictureAsync || camera?._cameraRef?.takePictureAsync;
                  
                  if (!captureMethod || typeof captureMethod !== 'function') {
                    setError('takePictureAsync not available');
                    return;
                  }
                  
                  // Capture without base64 for speed
                  const photo = await captureMethod({ quality: 0.15, base64: false, skipProcessing: true });
                  
                  if (!isMountedRef.current) {
                    return;
                  }
                  
                  if (photo?.uri) {
                    console.log('Test capture successful, sending binary frame...');
                    await sendFrameToBackend(photo.uri);
                    frameCountRef.current += 1;
                  } else {
                    setError('Photo captured but no URI');
                  }
                } catch (err) {
                  const errorMessage = err instanceof Error ? err.message : String(err);
                  if (!errorMessage.includes('unmounted') && isMountedRef.current) {
                    setError(`Test error: ${errorMessage}`);
                  }
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
