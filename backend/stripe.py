from flask import Blueprint, request, jsonify
from config import STRIPE_SECRET_KEY
import stripe

stripe.api_key = STRIPE_SECRET_KEY

# Create a Blueprint for Stripe routes
stripe_bp = Blueprint('stripe', __name__)


@stripe_bp.route('/api/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """
    Create a Stripe Payment Intent
    
    Request body:
    {
        "amount": 1000,  # Amount in cents (e.g., 1000 = $10.00)
        "currency": "cad",
        "metadata": {  # Optional
            "session_id": "session_123",
            "order_id": "order_456"
        }
    }
    
    Returns:
    {
        "clientSecret": "pi_xxx_secret_yyy",
        "paymentIntentId": "pi_xxx"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        amount = data.get('amount')
        currency = data.get('currency', 'cad')
        metadata = data.get('metadata', {})

        if not amount:
            return jsonify({"error": "amount is required"}), 400

        if amount <= 0:
            return jsonify({"error": "amount must be greater than 0"}), 400

        # Create Payment Intent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount),  # Stripe expects integer cents
            currency=currency.lower(),
            metadata=metadata,
            automatic_payment_methods={
                'enabled': True,
            },
        )

        return jsonify({
            "clientSecret": payment_intent.client_secret,
            "paymentIntentId": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({
            "error": "Stripe error",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500


@stripe_bp.route('/api/confirm-payment', methods=['POST'])
def confirm_payment():
    """
    Confirm a payment intent (check payment status)
    
    Request body:
    {
        "paymentIntentId": "pi_xxx"
    }
    
    Returns:
    {
        "status": "succeeded" | "processing" | "requires_payment_method" | etc.,
        "paymentIntentId": "pi_xxx"
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "Request body is required"}), 400

        payment_intent_id = data.get('paymentIntentId')

        if not payment_intent_id:
            return jsonify({"error": "paymentIntentId is required"}), 400

        # Retrieve the Payment Intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        return jsonify({
            "status": payment_intent.status,
            "paymentIntentId": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({
            "error": "Stripe error",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500


@stripe_bp.route('/api/retrieve-payment-intent/<payment_intent_id>', methods=['GET'])
def retrieve_payment_intent(payment_intent_id):
    """
    Retrieve payment intent details
    
    Returns:
    {
        "status": "succeeded",
        "amount": 1000,
        "currency": "cad",
        ...
    }
    """
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        return jsonify({
            "id": payment_intent.id,
            "status": payment_intent.status,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "metadata": payment_intent.metadata,
        }), 200

    except stripe.error.StripeError as e:
        return jsonify({
            "error": "Stripe error",
            "message": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "error": "Server error",
            "message": str(e)
        }), 500