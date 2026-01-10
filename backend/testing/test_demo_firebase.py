"""
Demo script to create a cart, add items, and display the database state.
"""

import json
from firebase import FirebaseCartManager


def print_separator(title=""):
    """Print a formatted separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'-'*60}\n")


def demo():
    """Run the demo."""
    try:
        # Initialize Firebase manager
        print("Initializing Firebase Cart Manager...")
        manager = FirebaseCartManager(credentials_path="credentials.json")
        
        # Create a new cart
        print_separator("CREATING CART")
        cart_id = "demo_cart_001"
        cart = manager.create_cart(
            cart_id=cart_id,
            metadata={"store_id": "store_demo", "location": "aisle_5"}
        )
        print(f"✓ Cart created: {cart_id}")
        print(json.dumps(cart, indent=2, default=str))
        
        # Add first item
        print_separator("ADDING FIRST ITEM (BANANA)")
        item_id_1 = manager.add_item(
            cart_id=cart_id,
            label="banana",
            price=0.50,
            product_name="Organic Banana",
            confidence=0.95
        )
        print(f"✓ Item added: {item_id_1}")
        print(f"  Label: banana | Price: $0.50")
        
        # Add second item
        print_separator("ADDING SECOND ITEM (APPLE)")
        item_id_2 = manager.add_item(
            cart_id=cart_id,
            label="apple",
            price=0.99,
            product_name="Red Apple",
            confidence=0.92
        )
        print(f"✓ Item added: {item_id_2}")
        print(f"  Label: apple | Price: $0.99")
        
        # Retrieve and display updated cart
        print_separator("UPDATED CART DATA")
        updated_cart = manager.get_cart(cart_id)
        print(json.dumps(updated_cart, indent=2, default=str))
        
        # Display all items in cart
        print_separator("ALL ITEMS IN CART")
        items = manager.get_cart_items(cart_id)
        print(f"Total items in cart: {len(items)}\n")
        for i, item in enumerate(items, 1):
            print(f"Item {i}:")
            print(json.dumps(item, indent=2, default=str))
            print()
        
        # Summary
        print_separator("SUMMARY")
        print(f"Cart ID: {cart_id}")
        print(f"Total Items: {updated_cart.get('total_items', 0)}")
        print(f"Total Price: ${updated_cart.get('total_price', 0):.2f}")
        print(f"Status: {updated_cart.get('status', 'N/A')}")
        print(f"Created At: {updated_cart.get('created_at', 'N/A')}")
        
        print_separator()
        print("✓ Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Firebase credentials.json exists")
        print("  2. MongoDB is running")
        print("  3. All dependencies are installed: pip install firebase-admin pymongo")


if __name__ == "__main__":
    demo()
