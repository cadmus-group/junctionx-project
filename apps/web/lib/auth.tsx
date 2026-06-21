"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { DEMO_MSW_TOKEN, setToken, TOKEN_KEY } from "./client";
import { getPublicEnv } from "./env";
import { resolveRole, type Role } from "./roles";

export interface AuthUser {
  id: string;
  name: string;
  email?: string;
  role: Role;
}

const USER_KEY = "gridtrace.user";

interface AuthState {
  user: AuthUser | null;
  /** False until localStorage has been read on the client (avoids a hydration flash). */
  ready: boolean;
  login: (user: AuthUser, token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function readStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthUser;
    return { ...parsed, role: resolveRole(parsed.role) };
  } catch {
    return null;
  }
}

function clearStoredSession(): void {
  setToken(null);
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(USER_KEY);
  }
}

/** Require both user and a token that works with the current runtime mode. */
function readStoredSession(): AuthUser | null {
  const user = readStoredUser();
  const token =
    typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  if (!user || !token) return null;

  const { NEXT_PUBLIC_DEMO_MODE } = getPublicEnv();
  if (!NEXT_PUBLIC_DEMO_MODE && token === DEMO_MSW_TOKEN) return null;

  return user;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  // Hydrate from localStorage once on the client.
  useEffect(() => {
    const session = readStoredSession();
    if (!session) clearStoredSession();
    setUser(session);
    setReady(true);
  }, []);

  const login = useCallback((nextUser: AuthUser, token: string) => {
    setToken(token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    setUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    clearStoredSession();
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, ready, login, logout }),
    [user, ready, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

/**
 * Gates the platform shell: unauthenticated visitors are redirected to the
 * login screen. This is what makes login appear when the web app starts.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) {
    return (
      <div className="flex h-screen w-full items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }
  return <>{children}</>;
}
