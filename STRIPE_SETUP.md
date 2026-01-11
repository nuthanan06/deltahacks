# Stripe Payment Integration Setup

## Backend Setup

1. **Install Stripe SDK:**
```bash
cd backend
pip install stripe
```

2. **Get Stripe API Keys:**
   - Go to https://dashboard.stripe.com/test/apikeys
   - Copy your **Secret key** (starts with `sk_test_`)
   - Copy your **Publishable key** (starts with `pk_test_`)

3. **Add to .env file:**
```bash
# backend/.env
STRIPE_SECRET_KEY=sk_test_YOUR_SECRET_KEY_HERE
```

4. **Restart backend:**
```bash
python3 app.py
```

## Frontend Setup (Optional - For Full Stripe Integration)

To integrate the actual Stripe Payment Sheet (instead of the mock confirmation):

1. **Install Stripe React Native:**
```bash
cd frontend
npx expo install @stripe/stripe-react-native
```

2. **Update checkout.tsx** to use StripeProvider and PaymentSheet:
```typescript
import { StripeProvider, useStripe } from '@stripe/stripe-react-native';

// Wrap your app with StripeProvider in _layout.tsx:
<StripeProvider publishableKey="pk_test_YOUR_PUBLISHABLE_KEY">
  {/* Your app */}
</StripeProvider>

// In checkout.tsx, use:
const { initPaymentSheet, presentPaymentSheet } = useStripe();

// Initialize payment sheet with clientSecret
await initPaymentSheet({
  paymentIntentClientSecret: clientSecret,
  merchantDisplayName: 'DeltaHacks Store',
});

// Present the payment sheet
const { error } = await presentPaymentSheet();
```

## Current Implementation

The current setup:
- ✅ Backend creates real Stripe PaymentIntents
- ✅ Amount is calculated correctly (in cents)
- ✅ Session ID is attached to payment metadata
- ⚠️ Frontend shows mock confirmation dialog (easily replaceable with real Stripe Payment Sheet)

## Testing

Use Stripe test cards:
- **Success:** 4242 4242 4242 4242
- **Requires authentication:** 4000 0025 0000 3155
- **Declined:** 4000 0000 0000 9995

Any future expiry date and any 3-digit CVC.

## Production Checklist

Before going live:
1. Replace test keys with live keys
2. Implement actual Stripe Payment Sheet in frontend
3. Add webhook handler for payment confirmation
4. Add proper error handling and retry logic
5. Store payment records in MongoDB
6. Test with real payment methods
