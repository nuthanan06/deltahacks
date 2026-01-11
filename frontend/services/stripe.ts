import { initStripe, useStripe } from '@stripe/stripe-react-native';

type StripeInstance = ReturnType<typeof useStripe>;
const STRIPE_PUBLISHABLE_KEY = process.env.EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY;

if (!STRIPE_PUBLISHABLE_KEY) {
  throw new Error('EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY is not set');
}

// Backend API URL
const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:5001';

/**
 * Initialize Stripe with your publishable key
 * Call this once in your app's root component (e.g., _layout.tsx)
 */
export const initializeStripe = async (): Promise<void> => {
  try {
    await initStripe({
      publishableKey: STRIPE_PUBLISHABLE_KEY,
    });
    console.log('Stripe initialized successfully');
  } catch (error) {
    console.error('Error initializing Stripe:', error);
    throw error;
  }
};

/**
 * Create a payment intent on the backend
 * 
 * @param amount - Amount in cents (e.g., 1000 = $10.00)
 * @param currency - Currency code (default: 'usd')
 * @param metadata - Optional metadata to attach to the payment
 * @returns Payment intent client secret
 */
export const createPaymentIntent = async (
  amount: number,
  currency: string = 'cad',
  metadata?: Record<string, string>
): Promise<string> => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/create-payment-intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        amount,
        currency,
        metadata,
      }),
    });

    if (!response.ok) {
      const errorData = (await response.json().catch(() => ({}))) as {
        message?: string;
      };
      throw new Error(
        errorData.message || `Failed to create payment intent: ${response.statusText}`
      );
    }

    const data = (await response.json()) as {
        clientSecret: string;
        paymentIntentId: string;
        amount: number;
        currency: string;
      };
      

    if (!data.clientSecret) {
      throw new Error('Payment intent was created but clientSecret is missing from the response');
    }

    return data.clientSecret;
  } catch (error) {
    console.error('Error creating payment intent:', error);
    throw error;
  }
};


/**
 * Process payment using Stripe Payment Sheet
 * 
 * Use this function in your React components where you have access to useStripe() hook.
 * 
 * @example
 * ```tsx
 * import { useStripe } from '@stripe/stripe-react-native';
 * import { processPaymentWithSheet } from '@/services/stripe';
 * 
 * const { initPaymentSheet, presentPaymentSheet } = useStripe();
 * 
 * const handlePay = async () => {
 *   const result = await processPaymentWithSheet(
 *     { initPaymentSheet, presentPaymentSheet },
 *     1000 // $10.00 in cents
 *   );
 * };
 * ```
 */
export const processPaymentWithSheet = async (
  stripe: Pick<StripeInstance, 'initPaymentSheet' | 'presentPaymentSheet'>,
  amount: number,
  currency: string = 'cad',
  merchantDisplayName: string = 'deltahacks'
): Promise<{ success: boolean; paymentIntentId?: string; error?: string }> => {
  try {
    const clientSecret = await createPaymentIntent(amount, currency);

    const { error: initError } = await stripe.initPaymentSheet({
      merchantDisplayName,
      paymentIntentClientSecret: clientSecret,
    });

    if (initError) {
      return {
        success: false,
        error: initError.message || 'Failed to initialize payment sheet',
      };
    }


    const { error: presentError } = await stripe.presentPaymentSheet();

    if (presentError) {
      return {
        success: false,
        error: presentError.message || 'Payment was cancelled or failed',
      };
    }

    const paymentIntentId = clientSecret.split('_secret_')[0];

    return {
      success: true,
      paymentIntentId,
    };
  } catch (error) {
    console.error('Error processing payment:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'An unexpected error occurred',
    };
  }
};

export const dollarsToCents = (dollars: number): number => {
  return Math.round(dollars * 100);
};

export const centsToDollars = (cents: number): number => {
  return cents / 100;
};