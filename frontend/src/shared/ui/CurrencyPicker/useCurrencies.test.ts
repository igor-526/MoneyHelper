import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useCurrencies } from "./useCurrencies";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, { client: api, children }),
    );
  return { api, wrapper };
}

const CURRENCIES_PAGE = {
  items: [
    { id: "1", code: "USD", name: "Доллар США", decimal_places: 2 },
    { id: "2", code: "RUB", name: "Российский рубль", decimal_places: 2 },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

describe("useCurrencies", () => {
  it("успешная загрузка: ответ маппится в Currency[]", async () => {
    const { api, wrapper } = setup(() => CURRENCIES_PAGE);

    const { result } = renderHook(() => useCurrencies(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([
      { id: "1", code: "USD", name: "Доллар США", decimalPlaces: 2 },
      { id: "2", code: "RUB", name: "Российский рубль", decimalPlaces: 2 },
    ]);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: "/api/currencies",
      query: { limit: 100, offset: 0 },
    });
  });

  it("состояние ошибки", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    const { result } = renderHook(() => useCurrencies(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
