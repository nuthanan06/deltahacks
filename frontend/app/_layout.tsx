import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import 'react-native-reanimated';
import { StripeProvider } from '@stripe/stripe-react-native';

import { useColorScheme } from '@/hooks/use-color-scheme';
import { CartProvider } from '@/contexts/CartContext';
import { playTestSound } from '@/utilities/sounds';

const STRIPE_PUBLISHABLE_KEY = 'pk_test_51SnSBdPEKM5aIKrc9DYxvLZCQ3GEOdyRF2ORR1oBJwnVpRzrOMyTM1vleN7SDsf7pnpqI6fm8QEl3mabuCq9g0DI00c1YVMEwT';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  const colorScheme = useColorScheme();

  // Play test sound when app launches
  useEffect(() => {
    // Small delay to ensure app is fully loaded
    const timer = setTimeout(() => {
      playTestSound();
    }, 1000);
    
    return () => clearTimeout(timer);
  }, []);

  return (
    <StripeProvider publishableKey={STRIPE_PUBLISHABLE_KEY}>
      <CartProvider>
        <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
          <Stack>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
          </Stack>
          <StatusBar style="auto" />
        </ThemeProvider>
      </CartProvider>
    </StripeProvider>
  );
}
