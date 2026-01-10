import { Platform } from 'react-native';

/**
 * API Configuration
 * 
 * For local development:
 * - On iOS Simulator/Android Emulator: Use localhost
 * - On physical device: Use your computer's local IP address
 * 
 * To find your local IP:
 * - Mac/Linux: ifconfig | grep "inet " | grep -v 127.0.0.1
 * - Windows: ipconfig (look for IPv4 Address)
 * 
 * IMPORTANT: Update LOCAL_IP below with your machine's IP address
 * when testing on a physical device!
 * 
 * For production, set EXPO_PUBLIC_API_URL environment variable
 */

// YOUR LOCAL IP ADDRESS - Update this with your machine's IP
// Find it with: ifconfig (Mac/Linux) or ipconfig (Windows)
// Example: '192.168.1.100' or '172.17.75.141'
const LOCAL_IP = '172.17.75.141'; // Update this!

// Get API URL from environment variable or use defaults
const getApiUrl = (): string => {
  // Check for environment variable first (for production)
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }

  // Development defaults
  if (__DEV__) {
    // For web, localhost works
    if (Platform.OS === 'web') {
      return 'http://localhost:5001';
    }

    // For iOS
    if (Platform.OS === 'ios') {
      // Toggle this based on whether you're using simulator or physical device
      // Set to true when testing on a physical iPhone/iPad
      const USE_PHYSICAL_DEVICE = true; // CHANGE THIS: true for physical device, false for simulator
      
      if (USE_PHYSICAL_DEVICE) {
        const url = `http://${LOCAL_IP}:5001`;
        console.log('📱 Using iOS Physical Device - API URL:', url);
        return url;
      } else {
        console.log('📱 Using iOS Simulator - API URL: http://localhost:5001');
        return 'http://localhost:5001'; // iOS Simulator
      }
    }

    // For Android
    if (Platform.OS === 'android') {
      // Toggle this based on whether you're using emulator or physical device
      // Set to true when testing on a physical Android device
      const USE_PHYSICAL_DEVICE = true; // CHANGE THIS: true for physical device, false for emulator
      
      if (USE_PHYSICAL_DEVICE) {
        const url = `http://${LOCAL_IP}:5001`;
        console.log('🤖 Using Android Physical Device - API URL:', url);
        return url;
      } else {
        console.log('🤖 Using Android Emulator - API URL: http://10.0.2.2:5001');
        return 'http://10.0.2.2:5001'; // Android Emulator (maps to host's localhost)
      }
    }

    return 'http://localhost:5001';
  }

  // Production fallback
  return 'https://your-production-api.com';
};

export const API_BASE_URL = getApiUrl();

// Log the API URL for debugging
if (__DEV__) {
  console.log('🔧 API Base URL:', API_BASE_URL);
  console.log('🔧 Local IP:', LOCAL_IP);
}

// Export LOCAL_IP for manual configuration if needed
export { LOCAL_IP };

