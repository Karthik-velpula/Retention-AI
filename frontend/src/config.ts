export const BASE_URL = "https://160.187.169.41/aistudent/";

const SERVER_APP_BASENAME = new URL(BASE_URL).pathname.replace(/\/$/, "") || "/";
const VERCEL_APP_BASENAME = "/Retention-AI";
const LOCAL_API_URL = "http://127.0.0.1:8000/ren";
const SERVER_API_URL = "/aistudent/ren/ren";
const PUBLIC_BACKEND_API_URL = "https://retention-ai-backend-z21q.onrender.com/aistudent/ren";

const isVercelHost = () =>
  typeof window !== "undefined" && window.location.hostname.endsWith(".vercel.app");

const isLocalHost = () =>
  typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

export const API_URL = isVercelHost() ? PUBLIC_BACKEND_API_URL : isLocalHost() ? LOCAL_API_URL : SERVER_API_URL;

export const APP_BASENAME =
  typeof window !== "undefined" && window.location.pathname.startsWith(VERCEL_APP_BASENAME)
    ? VERCEL_APP_BASENAME
    : SERVER_APP_BASENAME;
