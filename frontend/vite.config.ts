import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/Retention-AI/",
  plugins: [react()],
  server: {
    port: 5173
  }
});
