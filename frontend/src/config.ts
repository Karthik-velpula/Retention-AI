export const BASE_URL = "https://160.187.169.41/aistudent/";

const SERVER_APP_BASENAME = new URL(BASE_URL).pathname.replace(/\/$/, "") || "/";
const VERCEL_APP_BASENAME = "/Retention-AI";
const SERVER_API_URL = "/aistudent/ren/ren";
const PUBLIC_BACKEND_API_URL = "https://160.187.169.41/aistudent/ren/ren";

const isVercelHost = () =>
  typeof window !== "undefined" && window.location.hostname.endsWith(".vercel.app");

export const API_URL = isVercelHost() ? PUBLIC_BACKEND_API_URL : SERVER_API_URL;

export const APP_BASENAME =
  typeof window !== "undefined" && window.location.pathname.startsWith(VERCEL_APP_BASENAME)
    ? VERCEL_APP_BASENAME
    : SERVER_APP_BASENAME;
