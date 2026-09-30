import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { DEFAULT_PAGE_SIZE, useTransfers } from "./useTransfers";

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

function transfersPage(items: unknown[] = [], overrides: Partial<{ total: number }> = {}) {
  return { items, total: overrides.total ?? items.length, limit: DEFAULT_PAGE_SIZE, offset: 0 };
}

const TRANSFER = {
  id: "1",
  from_wallet_id: "w1",
  to_wallet_id: "w2",
  currency_id: "cur1",
  amount: "10.00",
  occurred_at: "2026-01-01T00:00:00Z",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: null,
};

describe("useTransfers", () => {
  it("загрузка без фильтров: возвращает весь Page<Transfer>", async () => {
    const page = transfersPage([TRANSFER]);
    const { api, wrapper } = setup(() => page);

    const { result } = renderHook(() => useTransfers({}, { offset: 0, limit: DEFAULT_PAGE_SIZE }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(page);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: "/api/transfers",
      query: {
        wallet_id: undefined,
        date_from: undefined,
        date_to: undefined,
        limit: DEFAULT_PAGE_SIZE,
        offset: 0,
      },
    });
  });

  it("каждый фильтр по отдельности передаётся в query", async () => {
    const { api: walletApi, wrapper: walletWrapper } = setup(() => transfersPage());
    renderHook(() => useTransfers({ walletId: "w1" }, { offset: 0, limit: DEFAULT_PAGE_SIZE }), {
      wrapper: walletWrapper,
    });
    await waitFor(() => expect(walletApi.requests).toHaveLength(1));
    expect(walletApi.requests[0]).toMatchObject({ query: { wallet_id: "w1" } });

    const { api: dateApi, wrapper: dateWrapper } = setup(() => transfersPage());
    renderHook(
      () =>
        useTransfers(
          { dateFrom: "2026-01-01T00:00:00.000Z", dateTo: "2026-01-31T23:59:59.999Z" },
          { offset: 0, limit: DEFAULT_PAGE_SIZE },
        ),
      { wrapper: dateWrapper },
    );
    await waitFor(() => expect(dateApi.requests).toHaveLength(1));
    expect(dateApi.requests[0]).toMatchObject({
      query: { date_from: "2026-01-01T00:00:00.000Z", date_to: "2026-01-31T23:59:59.999Z" },
    });
  });

  it("комбинация фильтров: все параметры передаются одновременно", async () => {
    const { api, wrapper } = setup(() => transfersPage());

    renderHook(
      () =>
        useTransfers(
          {
            walletId: "w1",
            dateFrom: "2026-01-01T00:00:00.000Z",
            dateTo: "2026-01-31T23:59:59.999Z",
          },
          { offset: 0, limit: DEFAULT_PAGE_SIZE },
        ),
      { wrapper },
    );

    await waitFor(() => expect(api.requests).toHaveLength(1));
    expect(api.requests[0]).toMatchObject({
      query: {
        wallet_id: "w1",
        date_from: "2026-01-01T00:00:00.000Z",
        date_to: "2026-01-31T23:59:59.999Z",
      },
    });
  });

  it("разные offset/limit кешируются раздельными ключами (оба запроса выполняются)", async () => {
    const { api, wrapper } = setup(() => transfersPage());
    const { rerender, result } = renderHook(
      ({ offset }: { offset: number }) => useTransfers({}, { offset, limit: DEFAULT_PAGE_SIZE }),
      { wrapper, initialProps: { offset: 0 } },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    rerender({ offset: DEFAULT_PAGE_SIZE });
    await waitFor(() => expect(api.requests).toHaveLength(2));

    expect(api.requests[0]).toMatchObject({ query: { offset: 0 } });
    expect(api.requests[1]).toMatchObject({ query: { offset: DEFAULT_PAGE_SIZE } });
  });

  it("состояние ошибки", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    const { result } = renderHook(() => useTransfers({}, { offset: 0, limit: DEFAULT_PAGE_SIZE }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
