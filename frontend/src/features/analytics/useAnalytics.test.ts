import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import type { AnalyticsFilters } from "./Analytics";
import { useAnalytics } from "./useAnalytics";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, { client: api, children }),
    );
  return { api, toast, wrapper };
}

const RESULT = {
  display_currency_id: "cur1",
  buckets: [{ group_key: "w1", income: "100.00", expense: "0" }],
  unconverted_currencies: [],
};

const BASE_FILTERS: AnalyticsFilters = {
  displayCurrencyId: "cur1",
  dateFrom: "2026-01-01T00:00:00.000Z",
  dateTo: "2026-01-31T23:59:59.999Z",
  groupBy: "wallet",
};

describe("useAnalytics", () => {
  it("filters === null: запрос не выполняется", async () => {
    const { api, wrapper } = setup(() => RESULT);

    const { result } = renderHook(() => useAnalytics(null), { wrapper });

    expect(result.current.isPending).toBe(true);
    expect(result.current.fetchStatus).toBe("idle");
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.requests).toHaveLength(0);
  });

  it("заполнены все обязательные поля: запрос выполняется с корректными query-параметрами", async () => {
    const { api, wrapper } = setup(() => RESULT);

    const { result } = renderHook(() => useAnalytics(BASE_FILTERS), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(RESULT);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: "/api/analytics",
      query: {
        display_currency: "cur1",
        date_from: "2026-01-01T00:00:00.000Z",
        date_to: "2026-01-31T23:59:59.999Z",
        group_by: "wallet",
        wallet_id: undefined,
        category_id: undefined,
        currency_id: undefined,
        type: undefined,
      },
    });
  });

  it("каждый сужающий фильтр по отдельности передаётся в query", async () => {
    const { api: walletApi, wrapper: walletWrapper } = setup(() => RESULT);
    renderHook(() => useAnalytics({ ...BASE_FILTERS, walletId: "w1" }), {
      wrapper: walletWrapper,
    });
    await waitFor(() => expect(walletApi.requests).toHaveLength(1));
    expect(walletApi.requests[0]).toMatchObject({ query: { wallet_id: "w1" } });

    const { api: categoryApi, wrapper: categoryWrapper } = setup(() => RESULT);
    renderHook(() => useAnalytics({ ...BASE_FILTERS, categoryId: "c1" }), {
      wrapper: categoryWrapper,
    });
    await waitFor(() => expect(categoryApi.requests).toHaveLength(1));
    expect(categoryApi.requests[0]).toMatchObject({ query: { category_id: "c1" } });

    const { api: currencyApi, wrapper: currencyWrapper } = setup(() => RESULT);
    renderHook(() => useAnalytics({ ...BASE_FILTERS, currencyId: "cur2" }), {
      wrapper: currencyWrapper,
    });
    await waitFor(() => expect(currencyApi.requests).toHaveLength(1));
    expect(currencyApi.requests[0]).toMatchObject({ query: { currency_id: "cur2" } });

    const { api: typeApi, wrapper: typeWrapper } = setup(() => RESULT);
    renderHook(() => useAnalytics({ ...BASE_FILTERS, type: "income" }), { wrapper: typeWrapper });
    await waitFor(() => expect(typeApi.requests).toHaveLength(1));
    expect(typeApi.requests[0]).toMatchObject({ query: { type: "income" } });
  });

  it("комбинация сужающих фильтров: все параметры передаются одновременно", async () => {
    const { api, wrapper } = setup(() => RESULT);

    renderHook(
      () =>
        useAnalytics({
          ...BASE_FILTERS,
          walletId: "w1",
          categoryId: "c1",
          currencyId: "cur2",
          type: "expense",
        }),
      { wrapper },
    );

    await waitFor(() => expect(api.requests).toHaveLength(1));
    expect(api.requests[0]).toMatchObject({
      query: {
        wallet_id: "w1",
        category_id: "c1",
        currency_id: "cur2",
        type: "expense",
      },
    });
  });

  it("отсутствующий сужающий фильтр не передаётся (undefined)", async () => {
    const { api, wrapper } = setup(() => RESULT);

    renderHook(() => useAnalytics(BASE_FILTERS), { wrapper });

    await waitFor(() => expect(api.requests).toHaveLength(1));
    expect(api.requests[0]?.query).toMatchObject({
      wallet_id: undefined,
      category_id: undefined,
      currency_id: undefined,
      type: undefined,
    });
  });

  it("ошибка запроса не подавляется (без meta.silent)", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
    });

    const { result } = renderHook(() => useAnalytics(BASE_FILTERS), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не найдено"));
  });
});
