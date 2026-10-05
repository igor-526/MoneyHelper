import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { DEFAULT_PAGE_SIZE } from "./useTransactions";
import { useTopups } from "./useTopups";

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

describe("useTopups", () => {
  it("запрашивает /topups с фильтрами и пагинацией, без параметра type", async () => {
    const { api, wrapper } = setup(() => ({ items: [], total: 0, limit: 20, offset: 0 }));

    const { result } = renderHook(
      () =>
        useTopups(
          {
            walletId: "w1",
            categoryId: "c1",
            dateFrom: "2026-01-01T00:00:00.000Z",
            dateTo: "2026-01-31T23:59:59.999Z",
          },
          { offset: 20, limit: DEFAULT_PAGE_SIZE },
        ),
      { wrapper },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/topups`,
      query: {
        wallet_id: "w1",
        category_id: "c1",
        date_from: "2026-01-01T00:00:00.000Z",
        date_to: "2026-01-31T23:59:59.999Z",
        limit: DEFAULT_PAGE_SIZE,
        offset: 20,
      },
    });
    expect(api.requests[0]?.query).not.toHaveProperty("type");
  });
});
