// Minimal auth state backed by localStorage + a React context.
import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import type { AuthResponse, Tokens, User } from "@/lib/api-client";

const STORAGE_KEY = "maa.auth";

interface StoredAuth {
  user: User;
  tokens: Tokens;
}

function load(): StoredAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredAuth) : null;
  } catch {
    return null;
  }
}

interface AuthContextValue {
  user: User | null;
  tokens: Tokens | null;
  isAuthenticated: boolean;
  setAuth: (data: AuthResponse) => void;
  clearAuth: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuthState] = useState<StoredAuth | null>(load);

  const setAuth = useCallback((data: AuthResponse) => {
    const next = { user: data.user, tokens: data.tokens };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setAuthState(next);
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setAuthState(null);
  }, []);

  const value: AuthContextValue = {
    user: auth?.user ?? null,
    tokens: auth?.tokens ?? null,
    isAuthenticated: Boolean(auth?.tokens?.access_token),
    setAuth,
    clearAuth,
  };

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
