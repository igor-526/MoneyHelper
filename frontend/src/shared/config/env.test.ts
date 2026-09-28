import { describe, expect, it } from "vitest";
import { DEFAULT_API_URL, resolveApiUrl } from "./env";

describe("resolveApiUrl", () => {
  it("возвращает значение по умолчанию, если адрес не задан", () => {
    expect(resolveApiUrl(undefined)).toBe(DEFAULT_API_URL);
    expect(resolveApiUrl("  ")).toBe(DEFAULT_API_URL);
  });

  it("убирает завершающий слэш", () => {
    expect(resolveApiUrl("https://api.example.com/")).toBe("https://api.example.com");
  });
});
