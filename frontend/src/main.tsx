import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router-dom";
import { App } from "./app/App";
import { routes } from "./app/routes";
import { createSingleFlightRefresh, FetchApiClient } from "./shared/api";
import { API_URL } from "./shared/config/env";
import { startInstallPromptCapture } from "./shared/pwa/installPrompt";
import "./index.css";

// Событие установки PWA приходит один раз и рано: перехватываем его при старте
startInstallPromptCapture();

const router = createBrowserRouter(routes);
const apiClient = new FetchApiClient({
  baseUrl: API_URL,
  onUnauthorized: createSingleFlightRefresh(API_URL),
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App apiClient={apiClient} router={router} />
  </StrictMode>,
);
