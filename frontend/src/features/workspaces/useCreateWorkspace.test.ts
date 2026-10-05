import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { WORKSPACES_QUERY_KEY } from "./useWorkspaces";
import { useCreateWorkspace } from "./useCreateWorkspace";

function setup(handler: FakeHandler) {
  const api = new FakeApiClient(handler);
  const toast = createToastSpy();
  const client = createQueryClient(toast);
  const invalidateSpy = vi.spyOn(client, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(ApiClientProvider, { client: api, children }),
    );
  return { api, toast, invalidateSpy, wrapper };
}

const VALUES = { name: "Поездка в Китай", currency_id: "cur-1" };
const CREATED = { id: "1", ...VALUES, created_at: "2026-01-01T00:00:00Z", updated_at: null };

describe("useCreateWorkspace", () => {
  it("успех вызывает POST и инвалидирует список воркспейсов", async () => {
    const { api, invalidateSpy, wrapper } = setup(() => CREATED);

    const { result } = renderHook(() => useCreateWorkspace(), { wrapper });
    act(() => {
      result.current.mutate(VALUES);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "POST",
      path: "/api/workspaces",
      body: VALUES,
    });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: WORKSPACES_QUERY_KEY });
  });

  it("ошибка не вызывает глобальный toast сама по себе (silent)", async () => {
    const { toast, wrapper } = setup(() => {
      throw new ApiError({
        kind: "validation",
        status: 400,
        fieldErrors: { name: ["обязательно"] },
      });
    });

    const { result } = renderHook(() => useCreateWorkspace(), { wrapper });
    act(() => {
      result.current.mutate(VALUES);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).not.toHaveBeenCalled();
  });
});
