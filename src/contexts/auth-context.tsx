"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

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
  login: (email: string, password: string, role?: Role) => Promise<boolean>;
  logout: () => void;
  loginError: string | null;
  clearLoginError: () => void;
  isAdmin: boolean;
  isCompliance: boolean;
  isViewer: boolean;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

// Authentication is disabled — all users get admin access automatically
const DEFAULT_USER: User = {
  name: "Admin User",
  role: "admin",
  email: "admin@company.com",
  department: "IT",
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = React.useState(false);
  const router = useRouter();

  // Always logged in as default admin — no login required
  const user: User = DEFAULT_USER;

  const login = React.useCallback(
    async (_email: string, _password: string, _role?: Role): Promise<boolean> => {
      router.replace("/dashboard");
      return true;
    },
    [router]
  );

  const logout = React.useCallback(() => {
    router.replace("/dashboard");
  }, [router]);

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    loginError: null,
    clearLoginError: () => {},
    isAdmin: true,
    isCompliance: true,
    isViewer: true,
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
