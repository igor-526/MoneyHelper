import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useWallets } from "./useWallets";

const TEST_WORKSPACE_ID = "workspace-1";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const client = createQueryClient(createToastSpy());
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, {
        client: api,
        children: createElement(WorkspaceContext.Provider, { value: TEST_WORKSPACE_ID, children }),
      }),
    );
  return { api, wrapper };
}

const WALLETS_PAGE = {
  items: [
    {
      id: "1",
      name: "Наличные",
      icon: "wallet",
      currency_ids: ["10"],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: null,
    },
    {
      id: "2",
      name: "Карта",
      icon: "credit-card",
      currency_ids: ["10", "20"],
      created_at: "2026-01-02T00:00:00Z",
      updated_at: null,
    },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

describe("useWallets", () => {
  it("успешная загрузка: возвращает items без маппинга", async () => {
    const { api, wrapper } = setup(() => WALLETS_PAGE);

    const { result } = renderHook(() => useWallets(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(WALLETS_PAGE.items);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/wallets`,
      query: { limit: 100, offset: 0 },
    });
  });

  it("состояние ошибки", async () => {
    // kind не из RETRYABLE_KINDS — ошибка наступает сразу, без ожидания retryDelay.
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    const { result } = renderHook(() => useWallets(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
