"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useLocale } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { getSavedProducts, saveProduct, unsaveProduct } from "@/lib/api";
import type { Locale } from "@/i18n/routing";
import type { ProductResponse } from "@/lib/types";

interface SavedProductsContextValue {
  savedProducts: ProductResponse[];
  savedProductIds: Set<string>;
  savedCount: number;
  isLoading: boolean;
  isSaved: (productId: string) => boolean;
  toggleSaved: (productId: string) => Promise<void>;
  refreshSavedProducts: () => Promise<void>;
}

const SavedProductsContext = createContext<SavedProductsContextValue | null>(
  null,
);

export function SavedProductsProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = useLocale() as Locale;
  const { isAuthenticated, isLoading: authLoading, login } = useAuth();
  const [savedProducts, setSavedProducts] = useState<ProductResponse[]>([]);
  const [savedProductIds, setSavedProductIds] = useState<Set<string>>(
    new Set(),
  );
  const [isLoading, setIsLoading] = useState(false);

  const refreshSavedProducts = useCallback(async () => {
    if (!isAuthenticated) {
      setSavedProducts([]);
      setSavedProductIds(new Set());
      return;
    }

    setIsLoading(true);
    try {
      const data = await getSavedProducts(locale, 1, 100);
      setSavedProducts(data.products);
      setSavedProductIds(new Set(data.product_ids));
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, locale]);

  useEffect(() => {
    if (authLoading) return;
    void refreshSavedProducts();
  }, [authLoading, refreshSavedProducts]);

  const isSaved = useCallback(
    (productId: string) => savedProductIds.has(productId),
    [savedProductIds],
  );

  const toggleSaved = useCallback(
    async (productId: string) => {
      if (!isAuthenticated) {
        login();
        return;
      }

      const wasSaved = savedProductIds.has(productId);
      const previousIds = new Set(savedProductIds);
      setSavedProductIds((current) => {
        const next = new Set(current);
        if (wasSaved) next.delete(productId);
        else next.add(productId);
        return next;
      });

      try {
        if (wasSaved) await unsaveProduct(productId);
        else await saveProduct(productId);
        await refreshSavedProducts();
      } catch {
        setSavedProductIds(previousIds);
      }
    },
    [isAuthenticated, login, refreshSavedProducts, savedProductIds],
  );

  const value = useMemo<SavedProductsContextValue>(
    () => ({
      savedProducts,
      savedProductIds,
      savedCount: savedProductIds.size,
      isLoading,
      isSaved,
      toggleSaved,
      refreshSavedProducts,
    }),
    [
      isLoading,
      isSaved,
      refreshSavedProducts,
      savedProductIds,
      savedProducts,
      toggleSaved,
    ],
  );

  return (
    <SavedProductsContext.Provider value={value}>
      {children}
    </SavedProductsContext.Provider>
  );
}

export function useSavedProducts(): SavedProductsContextValue {
  const context = useContext(SavedProductsContext);
  if (context === null) {
    throw new Error(
      "useSavedProducts must be used within a SavedProductsProvider",
    );
  }
  return context;
}

export function useOptionalSavedProducts(): SavedProductsContextValue | null {
  return useContext(SavedProductsContext);
}
