import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/lib/auth/provider";
import "@/styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  </StrictMode>,
);
