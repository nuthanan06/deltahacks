# Stripe Integration Setup Guide

This guide will help you complete the Stripe integration setup for your application.

## Backend Setup

### 1. Install Stripe Python Package

```bash
cd backend
pip install -r requirements.txt
```

The `stripe` package has already been added to `requirements.txt`.

### 2. Get Your Stripe API Keys

1. Sign up for a Stripe account at https://stripe.com
2. Go to the [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys)
3. Copy your **Secret Key** (starts with `sk_test_` for test mode)
4. Copy your **Publishable Key** (starts with `pk_test_` for test mode)

### 3. Add Stripe Keys to Environment Variables

Add these to your `.env` file in the backend directory:

```env
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
```

⚠️ **Important:** Never commit your secret key to version control! Keep it in `.env` only.

### 4. Test Backend API

Start your Flask backend:

```bash
cd backend
python app.py
```

Test the payment intent creation endpoint:

```bash
curl -X POST http://localhost:5001/api/create-payment-intent \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "currency": "usd",
    "metadata": {"test": "true"}
  }'
```

You should receive a response with `clientSecret`.

## Frontend Setup

### 1. Install Stripe React Native SDK

```bash
cd frontend
npm install @stripe/stripe-react-native
```

For iOS, you'll also need to install pods:

```bash
cd ios
pod install
cd ..
```

### 2. Configure Stripe Publishable Key

You have two options:

#### Option A: Environment Variables (Recommended)

Create a `.env` file in the frontend directory:

```env
EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
EXPO_PUBLIC_BACKEND_URL=http://localhost:5001
```

Then update `frontend/services/stripe.ts` to read from environment variables (already configured).

#### Option B: Direct Configuration

Edit `frontend/services/stripe.ts` and replace:

```typescript
const STRIPE_PUBLISHABLE_KEY = process.env.EXPO_PUBLIC_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_publishable_key_here';
```

With your actual publishable key:

```typescript
const STRIPE_PUBLISHABLE_KEY = 'pk_test_your_actual_key_here';
```

### 3. Configure Backend URL

Make sure `EXPO_PUBLIC_BACKEND_URL` in your `.env` matches your Flask backend URL. 

If running on a physical device or emulator, use:
- iOS Simulator: `http://localhost:5001`
- Android Emulator: `http://10.0.2.2:5001`
- Physical Device: `http://YOUR_COMPUTER_IP:5001` (e.g., `http://192.168.1.100:5001`)

### 4. Start the App

```bash
cd frontend
npm start
```

## Testing the Integration

1. **Add items to cart** - Use your app to scan/add products
2. **Go to checkout** - Navigate to the checkout screen
3. **Test Payment** - Tap "Proceed with Payment"
   - In test mode, use test card numbers:
     - **Success:** `4242 4242 4242 4242`
     - **Decline:** `4000 0000 0000 0002`
     - Use any future expiry date, any 3-digit CVC, and any ZIP code

## API Endpoints Created

### Backend Endpoints

- `POST /api/create-payment-intent` - Creates a Stripe payment intent
  - Request: `{ "amount": 1000, "currency": "usd", "metadata": {} }`
  - Response: `{ "clientSecret": "...", "paymentIntentId": "..." }`

- `POST /api/confirm-payment` - Confirms/checks payment status
  - Request: `{ "paymentIntentId": "pi_xxx" }`
  - Response: `{ "status": "succeeded", ... }`

- `GET /api/retrieve-payment-intent/<id>` - Retrieves payment intent details

## Files Modified/Created

### Backend
- ✅ `backend/stripe.py` - Stripe API endpoints
- ✅ `backend/config.py` - Added Stripe key configuration
- ✅ `backend/app.py` - Registered Stripe blueprint
- ✅ `backend/requirements.txt` - Added stripe package

### Frontend
- ✅ `frontend/services/stripe.ts` - Stripe service functions
- ✅ `frontend/app/_layout.tsx` - Stripe initialization
- ✅ `frontend/app/(tabs)/checkout.tsx` - Payment integration

## Troubleshooting

### "Stripe is not initialized" error
- Make sure `initializeStripe()` is called in `_layout.tsx`
- Check that your publishable key is correct

### "Failed to create payment intent" error
- Verify your backend is running
- Check `STRIPE_SECRET_KEY` is set in backend `.env`
- Check backend logs for errors
- Verify backend URL in frontend `.env`

### Payment sheet doesn't appear
- Check that Stripe React Native SDK is properly installed
- For iOS: Make sure pods are installed (`cd ios && pod install`)
- Check device logs for errors

### Network errors
- Verify `EXPO_PUBLIC_BACKEND_URL` is correct
- Check CORS is enabled in Flask (already done)
- For physical devices, ensure backend is accessible on your network

## Next Steps

1. ✅ Complete the setup steps above
2. Test with Stripe test cards
3. Set up webhook endpoints (optional, for production)
4. Switch to production keys when ready
5. Handle payment confirmation webhooks
6. Add order saving to your database after successful payment

## Security Notes

- ⚠️ Never expose your Stripe secret key in the frontend
- ✅ Always create payment intents on the backend
- ✅ Validate amounts on the backend before creating payment intents
- ✅ Use webhooks to confirm payments in production
- ✅ Keep your secret keys in environment variables, not in code

## Resources

- [Stripe React Native Documentation](https://stripe.dev/stripe-react-native/)
- [Stripe Testing Cards](https://stripe.com/docs/testing)
- [Stripe Dashboard](https://dashboard.stripe.com)
