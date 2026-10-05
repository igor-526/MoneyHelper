import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useWorkspaceHasWallets } from "./useWorkspaceHasWallets";

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

describe("useWorkspaceHasWallets", () => {
  it("true, если у воркспейса есть кошельки; запрашивает одну запись", async () => {
    const { api, wrapper } = setup(() => ({ items: [{}], total: 3, limit: 1, offset: 0 }));
    const { result } = renderHook(() => useWorkspaceHasWallets("w1"), { wrapper });

    await waitFor(() => expect(result.current.data).toBe(true));
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: "/api/workspaces/w1/wallets",
      query: { limit: 1, offset: 0 },
    });
  });

  it("false, если кошельков нет", async () => {
    const { wrapper } = setup(() => ({ items: [], total: 0, limit: 1, offset: 0 }));
    const { result } = renderHook(() => useWorkspaceHasWallets("w1"), { wrapper });

    await waitFor(() => expect(result.current.data).toBe(false));
  });

  it("без id воркспейса запрос не выполняется", () => {
    const { api, wrapper } = setup(() => ({}));
    renderHook(() => useWorkspaceHasWallets(undefined), { wrapper });

    expect(api.requests).toHaveLength(0);
  });
});
