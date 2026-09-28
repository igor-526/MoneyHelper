export const DEFAULT_API_URL = "http://localhost:8201";

/** Адрес backend без завершающего слэша; пустое значение заменяется адресом по умолчанию. */
export function resolveApiUrl(value: string | undefined): string {
  const trimmed = value?.trim();
  return (trimmed ? trimmed : DEFAULT_API_URL).replace(/\/+$/, "");
}

export const API_URL = resolveApiUrl(import.meta.env.VITE_API_URL);
