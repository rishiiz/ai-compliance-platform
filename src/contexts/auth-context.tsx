"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { loginApi, logoutApi, clearStoredToken } from "@/api";
import { config } from "@/lib/env";

export type Role = "admin" | "compliance" | "viewer";

export interface User {
  name: string;
  role: Role;
  email: string;
  department: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  /** Login with email and password. Role is determined by the backend from the user record. */
  login: (email: string, password: string, role?: Role) => Promise<boolean>;
  logout: () => void;
  loginError: string | null;
  clearLoginError: () => void;
  isAdmin: boolean;
  isCompliance: boolean;
  isViewer: boolean;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

const MOCK_USERS: Record<Role, User> = {
  admin: {
    name: "Admin User",
    role: "admin",
    email: "admin@company.com",
    department: "IT",
  },
  compliance: {
    name: "Sarah Chen",
    role: "compliance",
    email: "sarah@company.com",
    department: "Legal",
  },
  viewer: {
    name: "Viewer User",
    role: "viewer",
    email: "viewer@company.com",
    department: "Operations",
  },
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [loginError, setLoginError] = React.useState<string | null>(null);
  const router = useRouter();

  React.useEffect(() => {
    try {
      const stored = localStorage.getItem("auth_user");
      if (stored) {
        const u = JSON.parse(stored) as { name: string; role: string; email: string; department: string };
        const role = u.role === "Admin" ? "admin" : u.role === "Compliance Officer" ? "compliance" : u.role === "Viewer" ? "viewer" : (u.role as Role);
        setUser({ ...u, role: role as Role });
      }
    } catch {
      localStorage.removeItem("auth_user");
    }
    setIsLoading(false);
  }, []);

  const login = React.useCallback(
    async (email: string, password: string, role?: Role): Promise<boolean> => {
      setLoginError(null);
      setIsLoading(true);
      try {
        const res = await loginApi({ email, password });
        if (res?.user) {
          const u = res.user as { name: string; role: string; email: string; department: string };
          const normalized = { ...u, role: (u.role === "Admin" ? "admin" : u.role === "Compliance Officer" ? "compliance" : "viewer") as Role };
          setUser(normalized);
          if (typeof window !== "undefined") {
            localStorage.setItem("auth_user", JSON.stringify(normalized));
          }
          setIsLoading(false);
          router.replace("/dashboard");
          return true;
        }
        setLoginError("Login failed. Please check your credentials and try again.");
      } catch (e) {
        const message = e instanceof Error ? e.message : "Login failed";
        setLoginError(message);
        setIsLoading(false);
        return false;
      }
      if (config.useMock) {
        if (!email.trim() || !password.trim()) {
          setLoginError("Email and password required");
          setIsLoading(false);
          return false;
        }
        await new Promise((r) => setTimeout(r, 120));
        const mockRole = role ?? "viewer";
        const mockUser = { ...MOCK_USERS[mockRole], email: email.trim() || MOCK_USERS[mockRole].email };
        setUser(mockUser);
        if (typeof window !== "undefined") {
          localStorage.setItem("auth_user", JSON.stringify(mockUser));
        }
        setIsLoading(false);
        router.replace("/dashboard");
        return true;
      }
      setIsLoading(false);
      return false;
    },
    [router]
  );

  const logout = React.useCallback(() => {
    setUser(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_user");
      logoutApi().finally(() => clearStoredToken());
    } else {
      clearStoredToken();
    }
    router.replace("/");
  }, [router]);

  React.useEffect(() => {
    const onSessionExpired = () => {
      setUser(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem("auth_user");
        clearStoredToken();
      }
      router.replace("/login");
    };
    window.addEventListener("session-expired", onSessionExpired);
    return () => window.removeEventListener("session-expired", onSessionExpired);
  }, [router]);

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    loginError,
    clearLoginError: () => setLoginError(null),
    isAdmin: user?.role === "admin",
    isCompliance: user?.role === "compliance",
    isViewer: user?.role === "viewer",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
