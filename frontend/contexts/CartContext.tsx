"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
} from "react";
import type { Locale } from "@/i18n/routing";
import type { CartItemResponse, CartResponse } from "@/lib/types";
import { addToCart, getCart, removeFromCart, updateCartItem } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";

// --- State ---

interface CartState {
  items: CartItemResponse[];
  total_cents: number;
  item_count: number;
  isLoading: boolean;
  error: string | null;
  isDrawerOpen: boolean;
}

const INITIAL_STATE: CartState = {
  items: [],
  total_cents: 0,
  item_count: 0,
  isLoading: true,
  error: null,
  isDrawerOpen: false,
};

// --- Actions ---

type CartAction =
  | { type: "HYDRATE_START" }
  | { type: "HYDRATE_SUCCESS"; payload: CartResponse }
  | { type: "HYDRATE_FAILURE"; payload: string }
  | { type: "OPTIMISTIC_ADD"; payload: { productId: string; quantity: number } }
  | { type: "OPTIMISTIC_UPDATE"; payload: { productId: string; quantity: number } }
  | { type: "OPTIMISTIC_REMOVE"; payload: { productId: string } }
  | { type: "API_SUCCESS"; payload: CartResponse }
  | { type: "API_FAILURE"; payload: { previousState: CartState; error: string } }
  | { type: "CLEAR_ERROR" }
  | { type: "OPEN_DRAWER" }
  | { type: "CLOSE_DRAWER" };

// --- Reducer ---

function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "HYDRATE_START":
      return { ...state, isLoading: true, error: null };

    case "HYDRATE_SUCCESS":
      return {
        ...state,
        items: action.payload.items,
        total_cents: action.payload.total_cents,
        item_count: action.payload.item_count,
        isLoading: false,
        error: null,
      };

    case "HYDRATE_FAILURE":
      return { ...state, isLoading: false, error: action.payload };

    case "OPTIMISTIC_ADD": {
      return {
        ...state,
        item_count: state.item_count + action.payload.quantity,
      };
    }

    case "OPTIMISTIC_UPDATE": {
      const updatedItems = state.items.map((item) =>
        item.product_id === action.payload.productId
          ? { ...item, quantity: action.payload.quantity }
          : item
      );
      return {
        ...state,
        items: updatedItems,
        item_count: updatedItems.reduce((sum, item) => sum + item.quantity, 0),
      };
    }

    case "OPTIMISTIC_REMOVE": {
      const filteredItems = state.items.filter(
        (item) => item.product_id !== action.payload.productId
      );
      return {
        ...state,
        items: filteredItems,
        item_count: filteredItems.reduce((sum, item) => sum + item.quantity, 0),
        total_cents: filteredItems.reduce(
          (sum, item) => sum + item.product.price_cents * item.quantity,
          0
        ),
      };
    }

    case "API_SUCCESS":
      return {
        ...state,
        items: action.payload.items,
        total_cents: action.payload.total_cents,
        item_count: action.payload.item_count,
        error: null,
      };

    case "API_FAILURE":
      return {
        ...action.payload.previousState,
        error: action.payload.error,
      };

    case "CLEAR_ERROR":
      return { ...state, error: null };

    case "OPEN_DRAWER":
      return { ...state, isDrawerOpen: true };

    case "CLOSE_DRAWER":
      return { ...state, isDrawerOpen: false };

    default:
      return state;
  }
}

// --- Context ---

interface CartContextValue {
  items: CartItemResponse[];
  total_cents: number;
  item_count: number;
  isLoading: boolean;
  error: string | null;
  isDrawerOpen: boolean;
  addToCart: (productId: string, quantity?: number) => Promise<void>;
  updateQuantity: (productId: string, quantity: number) => Promise<void>;
  removeItem: (productId: string) => Promise<void>;
  openDrawer: () => void;
  closeDrawer: () => void;
  refreshCart: () => Promise<void>;
  dismissError: () => void;
}

const CartContext = createContext<CartContextValue | null>(null);

// --- Provider ---

function getPathLocale(): Locale {
  if (typeof window === "undefined") return "en";
  return window.location.pathname.startsWith("/bg") ? "bg" : "en";
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  const locale = getPathLocale();
  const getLocalizedError = useLocalizedError();
  const [state, dispatch] = useReducer(cartReducer, INITIAL_STATE);
  const stateRef = useRef(state);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep ref in sync so async callbacks capture latest state for rollback
  stateRef.current = state;

  // Auto-clear error after 5 seconds
  useEffect(() => {
    if (state.error) {
      if (errorTimerRef.current) {
        clearTimeout(errorTimerRef.current);
      }
      errorTimerRef.current = setTimeout(() => {
        dispatch({ type: "CLEAR_ERROR" });
        errorTimerRef.current = null;
      }, 5000);
    }
    return () => {
      if (errorTimerRef.current) {
        clearTimeout(errorTimerRef.current);
        errorTimerRef.current = null;
      }
    };
  }, [state.error]);

  // Hydrate on mount
  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      dispatch({ type: "HYDRATE_START" });
      try {
        const cart = await getCart(locale);
        if (!cancelled) {
          dispatch({ type: "HYDRATE_SUCCESS", payload: cart });
        }
      } catch (error) {
        if (!cancelled) {
          dispatch({
            type: "HYDRATE_FAILURE",
            payload: error instanceof ApiError ? getLocalizedError(error.code) : getLocalizedError("UNKNOWN"),
          });
        }
      }
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, [getLocalizedError, locale]);

  const handleAddToCart = useCallback(
    async (productId: string, quantity = 1) => {
      const previousState = structuredClone(stateRef.current);
      dispatch({ type: "OPTIMISTIC_ADD", payload: { productId, quantity } });

      try {
        const cart = await addToCart(productId, quantity, locale);
        dispatch({ type: "API_SUCCESS", payload: cart });
      } catch (error) {
        dispatch({
          type: "API_FAILURE",
          payload: {
            previousState,
            error: error instanceof ApiError ? getLocalizedError(error.code) : getLocalizedError("UNKNOWN"),
          },
        });
      }
    },
    [getLocalizedError, locale]
  );

  const handleUpdateQuantity = useCallback(
    async (productId: string, quantity: number) => {
      const previousState = structuredClone(stateRef.current);
      dispatch({ type: "OPTIMISTIC_UPDATE", payload: { productId, quantity } });

      try {
        const cart = await updateCartItem(productId, quantity, locale);
        dispatch({ type: "API_SUCCESS", payload: cart });
      } catch (error) {
        dispatch({
          type: "API_FAILURE",
          payload: {
            previousState,
            error: error instanceof ApiError ? getLocalizedError(error.code) : getLocalizedError("UNKNOWN"),
          },
        });
      }
    },
    [getLocalizedError, locale]
  );

  const handleRemoveItem = useCallback(async (productId: string) => {
    const previousState = structuredClone(stateRef.current);
    dispatch({ type: "OPTIMISTIC_REMOVE", payload: { productId } });

    try {
      const cart = await removeFromCart(productId, locale);
      dispatch({ type: "API_SUCCESS", payload: cart });
    } catch (error) {
      dispatch({
        type: "API_FAILURE",
        payload: {
          previousState,
          error: error instanceof ApiError ? getLocalizedError(error.code) : getLocalizedError("UNKNOWN"),
        },
      });
    }
  }, [getLocalizedError, locale]);

  const refreshCart = useCallback(async () => {
    dispatch({ type: "HYDRATE_START" });
    try {
      const cart = await getCart(locale);
      dispatch({ type: "HYDRATE_SUCCESS", payload: cart });
    } catch (error) {
      dispatch({
        type: "HYDRATE_FAILURE",
        payload: error instanceof ApiError ? getLocalizedError(error.code) : getLocalizedError("UNKNOWN"),
      });
    }
  }, [getLocalizedError, locale]);

  // Refresh cart when session is rotated (login/logout)
  useEffect(() => {
    window.addEventListener("session-rotated", refreshCart);
    return () => {
      window.removeEventListener("session-rotated", refreshCart);
    };
  }, [refreshCart]);

  const openDrawer = useCallback(() => {
    dispatch({ type: "OPEN_DRAWER" });
  }, []);

  const closeDrawer = useCallback(() => {
    dispatch({ type: "CLOSE_DRAWER" });
  }, []);

  const dismissError = useCallback(() => {
    dispatch({ type: "CLEAR_ERROR" });
  }, []);

  const value: CartContextValue = {
    items: state.items,
    total_cents: state.total_cents,
    item_count: state.item_count,
    isLoading: state.isLoading,
    error: state.error,
    isDrawerOpen: state.isDrawerOpen,
    addToCart: handleAddToCart,
    updateQuantity: handleUpdateQuantity,
    removeItem: handleRemoveItem,
    openDrawer,
    closeDrawer,
    refreshCart,
    dismissError,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

// --- Hook ---

export function useCart(): CartContextValue {
  const context = useContext(CartContext);
  if (context === null) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}
