import React, { createContext, useContext, useState, ReactNode } from 'react';

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

