import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useWorkspaces } from "./useWorkspaces";

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

const WORKSPACES_PAGE = {
  items: [
    { id: "1", name: "Личное", created_at: "2026-01-01T00:00:00Z", updated_at: null },
    { id: "2", name: "Поездка в Китай", created_at: "2026-01-02T00:00:00Z", updated_at: null },
  ],
  total: 2,
  limit: 100,
  offset: 0,
};

describe("useWorkspaces", () => {
  it("успешная загрузка: возвращает items без маппинга", async () => {
    const { api, wrapper } = setup(() => WORKSPACES_PAGE);

    const { result } = renderHook(() => useWorkspaces(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(WORKSPACES_PAGE.items);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: "/api/workspaces",
      query: { limit: 100, offset: 0 },
    });
  });

  it("состояние ошибки", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    const { result } = renderHook(() => useWorkspaces(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
