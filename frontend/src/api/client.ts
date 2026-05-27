import axios from "axios";

import { API_URL } from "../config";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? API_URL,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("retention-token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
