import { existsSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [
    tailwindcss(),
    viteReact(),
    {
      name: "trim-native-public",
      closeBundle() {
        const www = resolve(root, "native/android/app/src/main/assets/www");
        for (const extra of ["__grok", "releases"]) {
          const p = resolve(www, extra);
          if (existsSync(p)) rmSync(p, { recursive: true, force: true });
        }
      },
    },
  ],
  resolve: {
    alias: { "@": resolve(root, "src") },
  },
  base: "./",
  publicDir: "public",
  build: {
    outDir: "native/android/app/src/main/assets/www",
    emptyOutDir: true,
    assetsDir: "assets",
    rollupOptions: {
      input: resolve(root, "native.html"),
    },
  },
});
