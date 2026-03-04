import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      {
        find: /^react-native$/,
        replacement: "react-native-web",
      },
    ],
  },
  server: {
    proxy: {
      "/api": {
        target: "http://dashboard-api:8121",
        changeOrigin: true,
      },
      "/health": {
        target: "http://dashboard-api:8121",
        changeOrigin: true,
      },
    },
  },
});
