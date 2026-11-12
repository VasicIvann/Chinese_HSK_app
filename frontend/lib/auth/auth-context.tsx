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
import { toast } from "sonner";

import type { TokenResponse, UserPublic } from "@/lib/api/types";
import { onUnauthorized } from "@/lib/auth/session-events";
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

  // Expired/invalid token on any API call: drop the session. The protected
  // layout then redirects to /signin instead of showing empty pages.
  useEffect(
    () =>
      onUnauthorized(() => {
        if (!getStoredToken()) return; // already signed out (several calls may 401 at once)
        signOut();
        toast.info("Ta session a expiré, reconnecte-toi.");
      }),
    [signOut]
  );

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
