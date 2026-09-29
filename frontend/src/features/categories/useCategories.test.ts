import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useCategories } from "./useCategories";

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

const CATEGORIES_PAGE = {
  items: [
    {
      id: "1",
      type: "income",
      name: "Зарплата",
      icon: "banknote",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "2",
      type: "expense",
      name: "Продукты",
      icon: "coins",
      created_at: "2026-01-02T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

describe("useCategories", () => {
  it("успешная загрузка без фильтра: возвращает items без маппинга", async () => {
    const { api, wrapper } = setup(() => CATEGORIES_PAGE);

    const { result } = renderHook(() => useCategories(undefined), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(CATEGORIES_PAGE.items);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: "/api/categories",
      query: { type: undefined, limit: 100, offset: 0 },
    });
  });

  it("загрузка с фильтром type передаёт его в query", async () => {
    const { api, wrapper } = setup(() => CATEGORIES_PAGE);

    const { result } = renderHook(() => useCategories("income"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: "/api/categories",
      query: { type: "income", limit: 100, offset: 0 },
    });
  });

  it("разные значения type кешируются раздельными ключами", async () => {
    const { api, wrapper } = setup(() => CATEGORIES_PAGE);

    const { result: allResult } = renderHook(() => useCategories(undefined), { wrapper });
    const { result: incomeResult } = renderHook(() => useCategories("income"), { wrapper });

    await waitFor(() => expect(allResult.current.isSuccess).toBe(true));
    await waitFor(() => expect(incomeResult.current.isSuccess).toBe(true));

    expect(api.requests).toHaveLength(2);
  });

  it("состояние ошибки", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    const { result } = renderHook(() => useCategories(undefined), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
