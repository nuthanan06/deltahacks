import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { API_BASE_URL } from '@/config/api';

// Product type definition
export interface Product {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

// Cart context type
interface CartContextType {
  products: Product[];
  sessionId: string | null;
  setSessionId: (sessionId: string | null) => void;
  addProduct: (product: Product) => void;
  updateProductQuantity: (id: string, quantity: number) => void;
  removeProduct: (id: string) => void;
  clearCart: () => void;
  refreshCart: () => Promise<void>;
  getTotal: () => number;
  getSubtotal: () => number;
  getTax: () => number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

// Tax rate constant (mock - would come from backend/config)
const TAX_RATE = 0.13; // 13% tax

export function CartProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Function to fetch cart items from Firebase
  const fetchCartItems = useCallback(async () => {
    if (!sessionId) {
      setProducts([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/carts/${sessionId}/items`);
      if (!response.ok) {
        throw new Error(`Failed to fetch cart items: ${response.statusText}`);
      }

      const data = await response.json() as { items?: any[] };
      const items = data.items || [];

      // Transform Firebase items to Product format
      // Group items by product_name and count quantity
      const productMap = new Map<string, Product>();

      items.forEach((item: any) => {
        // Use product_name or label as the key
        const productKey = item.product_name || item.label || 'Unknown Product';
        
        if (productMap.has(productKey)) {
          // Increment quantity if product already exists
          const existing = productMap.get(productKey)!;
          existing.quantity += 1;
        } else {
          // Create new product entry
          productMap.set(productKey, {
            id: item.item_id || `${productKey}_${Date.now()}`,
            name: productKey,
            price: item.price || 0,
            quantity: 1,
          });
        }
      });

      // Convert map to array
      const productsArray = Array.from(productMap.values());
      setProducts(productsArray);
    } catch (error) {
      console.error('Error fetching cart items:', error);
      // Don't clear products on error, keep existing state
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  // Fetch cart items from Firebase when sessionId changes
  useEffect(() => {
    fetchCartItems();
  }, [fetchCartItems]);

  // Refresh function to manually reload cart items
  const refreshCart = useCallback(async () => {
    await fetchCartItems();
  }, [fetchCartItems]);

  const addProduct = (product: Product) => {
    setProducts((prev: Product[]) => {
      const existingProduct = prev.find((p: Product) => p.id === product.id);
      if (existingProduct) {
        // If product already exists, update quantity
        return prev.map((p: Product) =>
          p.id === product.id
            ? { ...p, quantity: p.quantity + product.quantity }
            : p
        );
      }
      // Add new product
      return [...prev, product];
    });
  };

  const updateProductQuantity = (id: string, quantity: number) => {
    if (quantity <= 0) {
      removeProduct(id);
      return;
    }
    setProducts((prev: Product[]) =>
      prev.map((p: Product) => (p.id === id ? { ...p, quantity } : p))
    );
  };

  const removeProduct = (id: string) => {
    setProducts((prev: Product[]) => prev.filter((p: Product) => p.id !== id));
  };

  const clearCart = () => {
    setProducts([]);
  };

  const getSubtotal = () => {
    return products.reduce((sum: number, product: Product) => sum + product.price * product.quantity, 0);
  };

  const getTax = () => {
    return getSubtotal() * TAX_RATE;
  };

  const getTotal = () => {
    return getSubtotal() + getTax();
  };

  return (
    <CartContext.Provider
      value={{
        products,
        sessionId,
        setSessionId,
        addProduct,
        updateProductQuantity,
        removeProduct,
        clearCart,
        refreshCart,
        getTotal,
        getSubtotal,
        getTax,
      }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}

