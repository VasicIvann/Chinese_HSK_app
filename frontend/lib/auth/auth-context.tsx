"use client";

import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { TokenResponse, UserPublic } from "@/lib/api/types";
import {
  clearSession,
  getStoredToken,
  getStoredUser,
  setStoredToken,
  setStoredUser,
} from "@/lib/auth/storage";

type AuthState = {
  user: UserPublic | null;
  token: string | null;
  isAuthenticated: boolean;
  isHydrating: boolean;
  setSession: (payload: TokenResponse) => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isHydrating, setIsHydrating] = useState(true);

  useEffect(() => {
    setUser(getStoredUser());
    setToken(getStoredToken());
    setIsHydrating(false);
  }, []);

  const setSession = useCallback((payload: TokenResponse) => {
    setStoredToken(payload.access_token);
    setStoredUser(payload.user);
    setToken(payload.access_token);
    setUser(payload.user);
  }, []);

  const signOut = useCallback(() => {
    clearSession();
    setUser(null);
    setToken(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      token,
      isAuthenticated: !!user && !!token,
      isHydrating,
      setSession,
      signOut,
    }),
    [user, token, isHydrating, setSession, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }
  return ctx;
}
