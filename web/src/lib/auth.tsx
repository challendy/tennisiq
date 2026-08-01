"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { me, type AuthUser } from "./api";

const KEY = "tennisiq.auth";

type AuthCtx = {
  user: AuthUser | null;
  setUser: (u: AuthUser | null) => void;
  logout: () => void;
  ready: boolean;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  const setUser = useCallback((u: AuthUser | null) => {
    setUserState(u);
    if (u) localStorage.setItem(KEY, JSON.stringify(u));
    else localStorage.removeItem(KEY);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const raw = localStorage.getItem(KEY);
        if (!raw) {
          if (!cancelled) setReady(true);
          return;
        }
        const stored = JSON.parse(raw) as AuthUser;
        if (!cancelled) setUserState(stored);
        try {
          const profile = await me(stored.token);
          if (!cancelled) {
            const next: AuthUser = {
              ...stored,
              email: profile.email,
              displayName: profile.displayName,
              plan: profile.plan,
              isAdmin: Boolean(profile.isAdmin),
            };
            setUserState(next);
            localStorage.setItem(KEY, JSON.stringify(next));
          }
        } catch {
          /* keep stored session if /me fails */
        }
      } catch {
        /* ignore */
      }
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const logout = useCallback(() => setUser(null), [setUser]);

  const value = useMemo(
    () => ({ user, setUser, logout, ready }),
    [user, setUser, logout, ready],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth outside provider");
  return ctx;
}
