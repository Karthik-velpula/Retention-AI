import { createContext, ReactNode, useContext, useEffect, useState } from "react";

import { logoutSession } from "../api/endpoints";
import { UserRole, LoginResponse } from "../types";

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  role: UserRole | null;
  name: string | null;
  lastLoginAt: string | null;
  acceptLogin: (response: LoginResponse) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("retention-token"));
  const [refreshToken, setRefreshToken] = useState<string | null>(localStorage.getItem("retention-refresh-token"));
  const [role, setRole] = useState<UserRole | null>((localStorage.getItem("retention-role") as UserRole | null) ?? null);
  const [name, setName] = useState<string | null>(localStorage.getItem("retention-name"));
  const [lastLoginAt, setLastLoginAt] = useState<string | null>(localStorage.getItem("retention-last-login"));

  useEffect(() => {
    if (!token) {
      localStorage.removeItem("retention-token");
      localStorage.removeItem("retention-refresh-token");
      localStorage.removeItem("retention-role");
      localStorage.removeItem("retention-name");
      localStorage.removeItem("retention-last-login");
      return;
    }
    localStorage.setItem("retention-token", token);
    if (refreshToken) {
      localStorage.setItem("retention-refresh-token", refreshToken);
    } else {
      localStorage.removeItem("retention-refresh-token");
    }
    if (role) localStorage.setItem("retention-role", role);
    if (name) localStorage.setItem("retention-name", name);
    if (lastLoginAt) {
      localStorage.setItem("retention-last-login", lastLoginAt);
    } else {
      localStorage.removeItem("retention-last-login");
    }
  }, [lastLoginAt, name, refreshToken, role, token]);

  const acceptLogin = (response: LoginResponse) => {
    setToken(response.access_token);
    setRefreshToken(response.refresh_token);
    setRole(response.role);
    setName(response.name);
    setLastLoginAt(response.last_login_at ?? null);
  };

  const logout = () => {
    if (token) {
      void logoutSession().catch(() => undefined);
    }
    setToken(null);
    setRefreshToken(null);
    setRole(null);
    setName(null);
    setLastLoginAt(null);
  };

  return <AuthContext.Provider value={{ token, refreshToken, role, name, lastLoginAt, acceptLogin, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
