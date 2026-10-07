import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { PropsWithChildren } from "react";
import { describe, expect, it } from "vitest";
import { ApiClientProvider } from "@/shared/api";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { FakeApiClient } from "@/test/FakeApiClient";
import { useExchangeRateHistory } from "./useExchangeRateHistory";

const WORKSPACE_ID = "10000000-0000-4000-8000-000000000001";
const CURRENCY_ID = "20000000-0000-4000-8000-000000000001";

function setup() {
  const api = new FakeApiClient(() =>
    Promise.resolve({ base_currency_id: CURRENCY_ID, quote_currency_id: "rub", points: [] }),
  );
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function wrapper({ children }: PropsWithChildren) {
    return (
      <ApiClientProvider client={api}>
        <QueryClientProvider client={queryClient}>
          <WorkspaceContext.Provider value={WORKSPACE_ID}>{children}</WorkspaceContext.Provider>
        </QueryClientProvider>
      </ApiClientProvider>
    );
  }
  return { api, wrapper };
}

describe("useExchangeRateHistory", () => {
  it("передаёт валюту и диапазон", async () => {
    const { api, wrapper } = setup();
    const { result } = renderHook(
      () =>
        useExchangeRateHistory(CURRENCY_ID, {
          dateFrom: "2026-01-01T00:00:00",
          dateTo: "2026-01-31T23:59:59",
        }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      path: `/api/workspaces/${WORKSPACE_ID}/analytics/rates`,
      query: {
        currency_id: CURRENCY_ID,
        date_from: "2026-01-01T00:00:00",
        date_to: "2026-01-31T23:59:59",
      },
    });
  });

  it("не отправляет запрос без выбранной валюты", () => {
    const { api, wrapper } = setup();
    renderHook(() => useExchangeRateHistory(undefined, {}), { wrapper });
    expect(api.requests).toEqual([]);
  });
});
