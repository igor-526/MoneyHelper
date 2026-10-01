import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { categoriesQueryKey } from "./useCategories";
import { useUpdateCategory } from "./useUpdateCategory";

const TEST_WORKSPACE_ID = "workspace-1";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const invalidateSpy = vi.spyOn(client, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, {
        client: api,
        children: createElement(WorkspaceContext.Provider, { value: TEST_WORKSPACE_ID, children }),
      }),
    );
  return { api, toast, invalidateSpy, wrapper };
}

const VALUES = { type: "expense" as const, name: "Продукты", icon: "coins" };
const UPDATED = { id: "1", ...VALUES, created_at: "2026-01-01T00:00:00Z", updated_at: null };

describe("useUpdateCategory", () => {
  it("успех вызывает PUT и инвалидирует список категорий по префиксу", async () => {
    const { api, invalidateSpy, wrapper } = setup(() => UPDATED);

    const { result } = renderHook(() => useUpdateCategory(), { wrapper });
    act(() => {
      result.current.mutate({ id: "1", values: VALUES });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "PUT",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/categories/1`,
      body: VALUES,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: categoriesQueryKey(TEST_WORKSPACE_ID) });
  });

  it("ошибка не вызывает глобальный toast сама по себе (silent)", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { name: ["обязательно"] },
      });
    });

    const { result } = renderHook(() => useUpdateCategory(), { wrapper });
    act(() => {
      result.current.mutate({ id: "1", values: VALUES });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).not.toHaveBeenCalled();
  });
});
