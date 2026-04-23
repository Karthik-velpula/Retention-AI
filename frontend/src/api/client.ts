import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/Retention-AI/api/v1"
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("retention-token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
