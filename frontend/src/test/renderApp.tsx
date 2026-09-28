import { render } from "@testing-library/react";
import { createMemoryRouter } from "react-router-dom";
import { App } from "@/app/App";
import { routes } from "@/app/routes";
import type { ApiClient } from "@/shared/api";
import { DESKTOP_QUERY } from "@/shared/ui/useIsMobile";
import { setMedia } from "./matchMedia";

interface Options {
  apiClient: ApiClient;
  path?: string;
  /** Телефон (по умолчанию) или широкий экран. */
  mobile?: boolean;
}

/** Рендерит приложение целиком с фейковым `ApiClient` и памятью вместо адресной строки. */
export function renderApp({ apiClient, path = "/", mobile = true }: Options) {
  setMedia(DESKTOP_QUERY, !mobile);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return { router, ...render(<App apiClient={apiClient} router={router} />) };
}
