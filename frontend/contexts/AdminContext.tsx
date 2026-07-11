"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getCurrentUser } from "@/lib/api";
import type { UserResponse } from "@/lib/types";

interface AdminContextValue {
  user: UserResponse | null;
  isAdmin: boolean;
  isLoading: boolean;
}

const AdminContext = createContext<AdminContextValue>({
  user: null,
  isAdmin: false,
  isLoading: true,
});

export function AdminProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getCurrentUser()
      .then((u) => {
        setUser(u);
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const isAdmin = user?.is_admin ?? false;
  const value = useMemo(() => ({ user, isAdmin, isLoading }), [user, isAdmin, isLoading]);

  return (
    <AdminContext.Provider value={value}>
      {children}
    </AdminContext.Provider>
  );
}

export function useAdmin(): AdminContextValue {
  return useContext(AdminContext);
}
