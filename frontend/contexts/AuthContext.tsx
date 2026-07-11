"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
} from "react";
import type { UserResponse } from "@/lib/types";
import { getCurrentUser, logout as apiLogout } from "@/lib/api";
import { validateRedirectPath } from "@/lib/validateRedirectPath";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

// --- State ---

interface AuthState {
  user: UserResponse | null;
  isLoading: boolean;
  error: string | null;
}

const INITIAL_STATE: AuthState = {
  user: null,
  isLoading: true,
  error: null,
};

// --- Actions ---

type AuthAction =
  | { type: "HYDRATE_START" }
  | { type: "HYDRATE_SUCCESS"; user: UserResponse }
  | { type: "HYDRATE_FAILURE"; error: string }
  | { type: "LOGIN_COMPLETE"; user: UserResponse }
  | { type: "LOGOUT_START" }
  | { type: "LOGOUT_SUCCESS" }
  | { type: "LOGOUT_FAILURE"; error: string }
  | { type: "SESSION_REFRESH"; user: UserResponse | null }
  | { type: "CLEAR_ERROR" };

// --- Reducer ---

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "HYDRATE_START":
      return { ...state, isLoading: true, error: null };

    case "HYDRATE_SUCCESS":
      return { user: action.user, isLoading: false, error: null };

    case "HYDRATE_FAILURE":
      return { user: null, isLoading: false, error: action.error };

    case "LOGIN_COMPLETE":
      return { user: action.user, isLoading: false, error: null };

    case "LOGOUT_START":
      return { ...state, error: null };

    case "LOGOUT_SUCCESS":
      return { user: null, isLoading: false, error: null };

    case "LOGOUT_FAILURE":
      return { ...state, error: action.error };

    case "SESSION_REFRESH":
      return { ...state, user: action.user };

    case "CLEAR_ERROR":
      return { ...state, error: null };

    default:
      return state;
  }
}

// --- Context ---

interface AuthContextValue {
  user: UserResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  login: () => void;
  logout: () => Promise<void>;
  loginComplete: (user: UserResponse) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// --- Provider ---

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getAuthCheckFailedMessage(): string {
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/bg")) {
    return bgMessages.auth.authCheckFailed;
  }
  return enMessages.auth.authCheckFailed;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, INITIAL_STATE);
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
        const user = await getCurrentUser();
        if (!cancelled) {
          if (user) {
            dispatch({ type: "HYDRATE_SUCCESS", user });
          } else {
            dispatch({ type: "HYDRATE_FAILURE", error: "" });
          }
        }
      } catch {
        if (!cancelled) {
          dispatch({
            type: "HYDRATE_FAILURE",
            error: getAuthCheckFailedMessage(),
          });
        }
      }
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  // Listen for session-rotated events to re-fetch auth state
  useEffect(() => {
    async function handleSessionRotated() {
      try {
        const user = await getCurrentUser();
        dispatch({ type: "SESSION_REFRESH", user });
      } catch {
        dispatch({ type: "SESSION_REFRESH", user: null });
      }
    }

    window.addEventListener("session-rotated", handleSessionRotated);
    return () => {
      window.removeEventListener("session-rotated", handleSessionRotated);
    };
  }, []);

  const login = useCallback(() => {
    const currentPath = window.location.pathname + window.location.search;
    const validatedPath = validateRedirectPath(currentPath);
    sessionStorage.setItem("auth_redirect_to", validatedPath);
    window.location.href = `${API_URL}/v1/auth/login?redirect_to=${encodeURIComponent(validatedPath)}`;
  }, []);

  const logout = useCallback(async () => {
    dispatch({ type: "LOGOUT_START" });
    try {
      await apiLogout();
      dispatch({ type: "LOGOUT_SUCCESS" });
    } catch (error) {
      // User intent is to log out regardless of server response
      dispatch({ type: "LOGOUT_SUCCESS" });
      console.error("Logout API call failed:", error);
    }
  }, []);

  const loginComplete = useCallback((user: UserResponse) => {
    dispatch({ type: "LOGIN_COMPLETE", user });
  }, []);

  const value: AuthContextValue = {
    user: state.user,
    isLoading: state.isLoading,
    isAuthenticated: state.user !== null,
    error: state.error,
    login,
    logout,
    loginComplete,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// --- Hook ---

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
