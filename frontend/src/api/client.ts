import axios from "axios";
import { jwtDecode } from "jwt-decode";

import { API_URL } from "../config";
import type { LoginResponse } from "../types";

const isVercelHost = () =>
  typeof window !== "undefined" && window.location.hostname.endsWith(".vercel.app");

const client = axios.create({
  baseURL: isVercelHost() ? API_URL : import.meta.env.VITE_API_BASE_URL ?? API_URL,
});

const AUTH_PREFIX = "/auth";
const REFRESH_PATH = "/auth/refresh";
let refreshPromise: Promise<string | null> | null = null;

const buildUrl = (baseURL: string | undefined, path: string) => {
  const base = baseURL ?? "";
  return `${base.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
};

const shouldSkipRefresh = (url?: string) => {
  if (!url) {
    return false;
  }
  return (
    url.includes(REFRESH_PATH) ||
    url.includes(`${AUTH_PREFIX}/login`) ||
    url.includes(`${AUTH_PREFIX}/forgot-password`) ||
    url.includes(`${AUTH_PREFIX}/security-grid-preview`) ||
    url.includes(`${AUTH_PREFIX}/security-grid-reset`)
  );
};

const clearStoredSession = () => {
  localStorage.removeItem("retention-token");
  localStorage.removeItem("retention-refresh-token");
  localStorage.removeItem("retention-role");
  localStorage.removeItem("retention-name");
  localStorage.removeItem("retention-last-login");
};

const storeSession = (response: LoginResponse) => {
  localStorage.setItem("retention-token", response.access_token);
  localStorage.setItem("retention-refresh-token", response.refresh_token);
  localStorage.setItem("retention-role", response.role);
  localStorage.setItem("retention-name", response.name);
  if (response.last_login_at) {
    localStorage.setItem("retention-last-login", response.last_login_at);
  }
};

const isTokenNearExpiry = (token: string | null) => {
  if (!token) return true;
  try {
    const payload = jwtDecode<{ exp?: number }>(token);
    if (!payload.exp) return true;
    return payload.exp * 1000 <= Date.now() + 10000;
  } catch {
    return true;
  }
};

const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem("retention-refresh-token");
  if (!refreshToken) {
    clearStoredSession();
    return null;
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post<LoginResponse>(buildUrl(client.defaults.baseURL, REFRESH_PATH), { refresh_token: refreshToken })
      .then(({ data }) => {
        storeSession(data);
        return data.access_token;
      })
      .catch(() => {
        clearStoredSession();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
};

client.interceptors.request.use(async (config) => {
  if (!shouldSkipRefresh(config.url)) {
    const currentToken = localStorage.getItem("retention-token");
    if (isTokenNearExpiry(currentToken)) {
      await refreshAccessToken();
    }
  }
  const token = localStorage.getItem("retention-token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean };
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !shouldSkipRefresh(originalRequest.url)
    ) {
      originalRequest._retry = true;
      const token = await refreshAccessToken();
      if (token) {
        originalRequest.headers = originalRequest.headers ?? {};
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return client(originalRequest);
      }
    }
    return Promise.reject(error);
  }
);

export default client;
