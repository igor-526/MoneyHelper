import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useAnalytics } from "./useAnalytics";

const TEST_WORKSPACE_ID = "workspace-1";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, {
        client: api,
        children: createElement(WorkspaceContext.Provider, { value: TEST_WORKSPACE_ID, children }),
      }),
    );
  return { api, toast, wrapper };
}

const RESULT = {
  display_currency_id: "cur1",
  buckets: [{ group_key: "c1", income: "0", expense: "100.00" }],
  unconverted_currencies: [],
};

describe("useAnalytics", () => {
  it("без диапазона запрос идёт без date_from/date_to и без display_currency", async () => {
    const { api, wrapper } = setup(() => RESULT);

    const { result } = renderHook(() => useAnalytics({ groupBy: "category", type: "expense" }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(RESULT);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/analytics`,
      query: { group_by: "category", type: "expense" },
    });
    expect(api.requests[0]?.query?.display_currency).toBeUndefined();
  });

  it("диапазон передаётся как date_from/date_to", async () => {
    const { api, wrapper } = setup(() => RESULT);

    const { result } = renderHook(
      () =>
        useAnalytics({
          groupBy: "category",
          type: "expense",
          dateFrom: "2026-01-01T00:00:00.000Z",
          dateTo: "2026-01-31T23:59:59.999Z",
        }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]?.query).toMatchObject({
      date_from: "2026-01-01T00:00:00.000Z",
      date_to: "2026-01-31T23:59:59.999Z",
    });
  });

  it("ошибка показывается toast общим обработчиком", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404, detail: "Не найдено" });
    });

    renderHook(() => useAnalytics({ groupBy: "category", type: "expense" }), { wrapper });

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Не найдено"));
  });
});
