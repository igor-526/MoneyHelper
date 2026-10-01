import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { WorkspaceContext } from "@/features/workspaces/WorkspaceContext";
import { ApiError, ApiClientProvider } from "@/shared/api";
import { createQueryClient } from "@/shared/errors";
import { type FakeHandler, FakeApiClient } from "@/test/FakeApiClient";
import { createToastSpy } from "@/test/toastSpy";
import { useWalletBalances } from "./useWalletBalances";

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

const BALANCES = [
  { currency_id: "cur1", balance: "100.00" },
  { currency_id: "cur2", balance: "0.00" },
];

describe("useWalletBalances", () => {
  it("запрос не выполняется при walletId === undefined", async () => {
    const { api, wrapper } = setup(() => BALANCES);

    const { result } = renderHook(() => useWalletBalances(undefined), { wrapper });

    await waitFor(() => expect(result.current.isPending).toBe(true));
    expect(result.current.fetchStatus).toBe("idle");
    expect(api.requests).toHaveLength(0);
  });

  it("успешная загрузка возвращает список балансов", async () => {
    const { api, wrapper } = setup(() => BALANCES);

    const { result } = renderHook(() => useWalletBalances("w1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(BALANCES);
    expect(api.requests[0]).toMatchObject({
      method: "GET",
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/wallets/w1/balances`,
    });
  });

  it("разные walletId кешируются раздельными ключами", async () => {
    const { api, wrapper } = setup(() => BALANCES);
    const { rerender, result } = renderHook(
      ({ walletId }: { walletId: string }) => useWalletBalances(walletId),
      { wrapper, initialProps: { walletId: "w1" } },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    rerender({ walletId: "w2" });
    await waitFor(() => expect(api.requests).toHaveLength(2));

    expect(api.requests[0]).toMatchObject({
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/wallets/w1/balances`,
    });
    expect(api.requests[1]).toMatchObject({
      path: `/api/workspaces/${TEST_WORKSPACE_ID}/wallets/w2/balances`,
    });
  });

  it("состояние ошибки", async () => {
    const { wrapper } = setup(() => {
      throw new ApiError({ kind: "not_found", status: 404 });
    });

    const { result } = renderHook(() => useWalletBalances("w1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
